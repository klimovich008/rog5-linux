#!/bin/sh
set -eu

repo=$(CDPATH= cd -- "$(dirname "$0")/../.." && pwd)
patch=$repo/patches/linux-7.1.4/0007-clk-trace-attended-SM8350-GPUCC-CCF-registration.patch
verifier=$repo/scripts/device/verify-ccf-registration-trace-patch.sh
source_dir=${SOURCE_DIR:-}
stage=$(mktemp -d)
trap 'rm -rf "$stage"' EXIT INT TERM

[ -r "$patch" ] && [ -x "$verifier" ]
"$verifier" "$patch" "$source_dir" >/dev/null

reject_mutation() {
	label=$1
	mutant=$2
	if "$verifier" "$mutant" "$source_dir" >"$stage/$label.output" 2>&1; then
		echo "FAIL CCF trace verifier accepted $label mutation" >&2
		exit 1
	fi
}

sed 's/bool, 0400);/bool, 0600);/' "$patch" >"$stage/writable.patch"
reject_mutation writable "$stage/writable.patch"

sed 's/qcom,sm8350-gpucc/qcom,sm8450-gpucc/g' "$patch" \
	>"$stage/wrong-device.patch"
reject_mutation wrong-device "$stage/wrong-device.patch"

sed 's/msleep(100);/msleep(0);/' "$patch" >"$stage/no-settle.patch"
reject_mutation no-settle "$stage/no-settle.patch"

sed '/orphan-reparent-begin/d' "$patch" >"$stage/incomplete.patch"
reject_mutation incomplete "$stage/incomplete.patch"

sed 's/msleep(100);/regmap_write(NULL, 0, 0);/' "$patch" \
	>"$stage/hardware-write.patch"
reject_mutation hardware-write "$stage/hardware-write.patch"

sed 's/return rog5_ccf_register_trace && np &&/return true \&\& np \&\&/' \
	"$patch" >"$stage/broad.patch"
reject_mutation broad "$stage/broad.patch"

sed '/^[+ ]	ret = __clk_core_init(core);$/p' "$patch" \
	>"$stage/duplicate-core-init.patch"
reject_mutation duplicate-core-init "$stage/duplicate-core-init.patch"

echo 'PASS CCF trace verifier rejects writable, broad, wrong-device, unflushed, incomplete, duplicate-call, and hardware-writing mutations'
