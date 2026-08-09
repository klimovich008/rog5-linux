#!/bin/sh
set -eu

fail() {
	echo "FAIL $*" >&2
	exit 1
}

repo=$(CDPATH= cd -- "$(dirname "$0")/../.." && pwd)
base=$repo/artifacts/network-root-v3/sm8350-asus-rog-phone5-recovery.dtb
adsp_overlay=$repo/dts/qcom/sm8350-asus-rog-phone5-adsp.dtso
pmic_overlay=$repo/dts/qcom/sm8350-asus-rog-phone5-pmic-glink.dtso
overlay=$repo/dts/qcom/sm8350-asus-rog-phone5-dual-cell-readonly.dtso
builder=$repo/scripts/device/build-dual-cell-readonly-candidate-dtb.sh
verifier=$repo/scripts/device/verify-dual-cell-readonly-dtb-delta.py
stage=$(mktemp -d)
trap 'rm -rf "$stage"' EXIT INT TERM

for input in "$base" "$adsp_overlay" "$pmic_overlay" "$overlay" \
	"$builder" "$verifier"; do
	[ -f "$input" ] && [ ! -L "$input" ] && [ -r "$input" ] ||
		fail "missing readable ordinary test input: $input"
done
for script in "$builder" "$verifier"; do
	[ -x "$script" ] || fail "test input is not executable: $script"
done
for command in cmp dtc fdtget fdtoverlay fdtput python3 sha256sum; do
	command -v "$command" >/dev/null ||
		fail "missing dual-cell DTB test command: $command"
done

dtc -q -@ -I dts -O dtb -o "$stage/adsp.dtbo" "$adsp_overlay"
dtc -q -@ -I dts -O dtb -o "$stage/pmic-glink.dtbo" "$pmic_overlay"
fdtoverlay -i "$base" -o "$stage/telemetry.dtb" \
	"$stage/adsp.dtbo" "$stage/pmic-glink.dtbo"
"$builder" "$stage/telemetry.dtb" "$overlay" "$stage/one.dtb" >/dev/null
"$builder" "$stage/telemetry.dtb" "$overlay" "$stage/two.dtb" >/dev/null
cmp "$stage/one.dtb" "$stage/two.dtb"
"$verifier" "$stage/telemetry.dtb" "$stage/one.dtb" >/dev/null
fdtget "$stage/one.dtb" /pmic-glink asus,cell-voltage-readonly >/dev/null

reject_delta() {
	mutant=$1
	expected=$2
	if "$verifier" "$stage/telemetry.dtb" "$mutant" \
		>"$mutant.log" 2>&1; then
		fail "verifier accepted $(basename "$mutant")"
	fi
	grep -Fq "$expected" "$mutant.log" || {
		echo "FAIL verifier rejected $(basename "$mutant") incorrectly" >&2
		cat "$mutant.log" >&2
		exit 1
	}
}

cp "$stage/one.dtb" "$stage/property-removed.dtb"
fdtput -d "$stage/property-removed.dtb" /pmic-glink \
	asus,cell-voltage-readonly
reject_delta "$stage/property-removed.dtb" \
	'FAIL candidate ASUS cell-voltage opt-in is absent or non-empty'

cp "$stage/one.dtb" "$stage/unapproved-property.dtb"
fdtput -t s "$stage/unapproved-property.dtb" / model rog5-mutant
reject_delta "$stage/unapproved-property.dtb" \
	'FAIL candidate changed an unapproved property:'

cp "$stage/one.dtb" "$stage/extra-node.dtb"
fdtput -c "$stage/extra-node.dtb" /pmic-glink/hostile-control
reject_delta "$stage/extra-node.dtb" \
	'FAIL candidate changed the DTB node set:'

cp "$stage/telemetry.dtb" "$stage/wrong-base.dtb"
fdtput -t s "$stage/wrong-base.dtb" / model rog5-mutant
if "$verifier" "$stage/wrong-base.dtb" "$stage/one.dtb" \
	>"$stage/wrong-base.log" 2>&1; then
	fail 'verifier accepted an unpinned telemetry base DTB'
fi
grep -Fq 'FAIL base DTB identity is not accepted:' "$stage/wrong-base.log"

dd if="$stage/one.dtb" of="$stage/truncated.dtb" \
	bs=1 count=128 status=none
reject_delta "$stage/truncated.dtb" \
	'FAIL DTB total size does not equal its file size:'

ln -s "$stage/one.dtb" "$stage/linked.dtb"
reject_delta "$stage/linked.dtb" 'FAIL DTB is not an ordinary file:'

cat >"$stage/wrong-overlay.dtso" <<'EOF'
/dts-v1/;
/plugin/;

&{/pmic-glink} {
	asus,cell-voltage-readonly;
	asus,charge-limit = <80>;
};
EOF
if "$builder" "$stage/telemetry.dtb" "$stage/wrong-overlay.dtso" \
	"$stage/wrong-overlay.dtb" >"$stage/wrong-overlay.log" 2>&1; then
	fail 'builder accepted an overlay that added a charging control'
fi
grep -Fq 'FAIL candidate changed an unapproved property:' \
	"$stage/wrong-overlay.log"
[ ! -e "$stage/wrong-overlay.dtb" ]

printf 'preserve\n' >"$stage/output-target"
ln -s "$stage/output-target" "$stage/linked-output"
if "$builder" "$stage/telemetry.dtb" "$overlay" "$stage/linked-output" \
	>"$stage/linked-output.log" 2>&1; then
	fail 'builder accepted a linked output'
fi
grep -Fq 'FAIL output is a link or directory:' "$stage/linked-output.log"
grep -Fxq preserve "$stage/output-target"

echo 'PASS hostile read-only dual-cell DTB candidate contract'
