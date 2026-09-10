#!/bin/sh
set -eu

fail() {
	echo "FAIL $*" >&2
	exit 1
}

repo=$(CDPATH= cd -- "$(dirname "$0")/../.." && pwd)
patch=$repo/patches/linux-7.1.4/0018-power-supply-qcom-battmgr-add-rog5-cell-voltage.patch
verifier=$repo/scripts/device/verify-qcom-battmgr-asus-cell-voltage-patch.sh
stage=$(mktemp -d)
trap 'rm -rf "$stage"' EXIT INT TERM

[ -x "$verifier" ] || fail "missing executable verifier: $verifier"

reject_mutant() {
	name=$1
	expected=$2
	if PATCH_FILE="$stage/$name.patch" "$verifier" \
		>"$stage/$name.log" 2>&1; then
		fail "verifier accepted hostile mutation: $name"
	fi
	grep -Fq "$expected" "$stage/$name.log" || {
		echo "FAIL verifier misclassified hostile mutation: $name" >&2
		cat "$stage/$name.log" >&2
		exit 1
	}
}

[ -f "$patch" ] && [ ! -L "$patch" ] && [ -r "$patch" ] ||
	fail "missing implementation patch: $patch"

sed 's/32782/32781/' "$patch" >"$stage/wrong-owner.patch"
reject_mutant wrong-owner 'patch lacks the exact ASUS OEM owner'

sed 's/0x3005/0x3006/' "$patch" >"$stage/wrong-opcode.patch"
reject_mutant wrong-opcode 'patch lacks the exact ASUS cell-voltage opcode'

sed 's/asus,cell-voltage-readonly/asus,cell-voltage-writeable/' \
	"$patch" >"$stage/wrong-opt-in.patch"
reject_mutant wrong-opt-in 'asus,cell-voltage-readonly'

sed 's/len != sizeof(\*resp)/len < sizeof(*resp)/' \
	"$patch" >"$stage/nonexact-length.patch"
reject_mutant nonexact-length 'len != sizeof(*resp)'

sed 's/DEVICE_ATTR_RO(cell_voltages)/DEVICE_ATTR_RW(cell_voltages)/' \
	"$patch" >"$stage/writeable-attribute.patch"
reject_mutant writeable-attribute 'DEVICE_ATTR_RO(cell_voltages)'

sed 's/mutex_lock(&battmgr->lock);/mutex_lock(\&battmgr->oem_lock);/' \
	"$patch" >"$stage/private-lock.patch"
reject_mutant private-lock 'mutex_lock(&battmgr->lock);'

sed 's/READ_ONCE(battmgr->oem_service_generation) != generation/READ_ONCE(battmgr->oem_service_generation) == generation/' \
	"$patch" >"$stage/no-generation-refusal.patch"
reject_mutant no-generation-refusal \
	'READ_ONCE(battmgr->oem_service_generation) != generation'

sed 's/WRITE_ONCE(battmgr->oem_request_poisoned, true);/WRITE_ONCE(battmgr->oem_request_poisoned, false);/' \
	"$patch" >"$stage/no-timeout-poison.patch"
reject_mutant no-timeout-poison \
	'WRITE_ONCE(battmgr->oem_request_poisoned, true);'

cp "$patch" "$stage/extra-file.patch"
cat >>"$stage/extra-file.patch" <<'EOF'
diff --git a/rog5-hostile-extra b/rog5-hostile-extra
new file mode 100644
index 000000000000..9a7ef1971477
--- /dev/null
+++ b/rog5-hostile-extra
@@ -0,0 +1 @@
+hostile
EOF
reject_mutant extra-file 'patch must modify exactly one file'

SOURCE_DIR=${SOURCE_DIR:-} "$verifier" >/dev/null
echo 'PASS hostile ROG5 cell-voltage patch contract'
