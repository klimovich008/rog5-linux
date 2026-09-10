#!/bin/sh
set -eu

repo=$(CDPATH= cd -- "$(dirname "$0")/../.." && pwd)
patch=$repo/patches/linux-7.1.4/0006-qcom-cc-add-attended-registration-trace.patch
gpucc_patch=$repo/patches/linux-7.1.4/0005-gpucc-sm8350-add-attended-probe-trace.patch
verifier=$repo/scripts/device/verify-qcom-cc-registration-trace-patch.sh
source_dir=${SOURCE_DIR:-}
stage=$(mktemp -d)
trap 'rm -rf "$stage"' EXIT INT TERM

[ -r "$patch" ] && [ -r "$gpucc_patch" ] && [ -x "$verifier" ]
"$verifier" "$patch" "$gpucc_patch" "$source_dir" >/dev/null

reject_mutation() {
	label=$1
	mutant=$2
	if "$verifier" "$mutant" "$gpucc_patch" "$source_dir" \
		>"$stage/$label.output" 2>&1; then
		echo "FAIL common-clock verifier accepted $label mutation" >&2
		exit 1
	fi
}

sed 's/bool, 0400);/bool, 0600);/' "$patch" >"$stage/writable.patch"
reject_mutation writable "$stage/writable.patch"

sed 's/qcom,sm8350-gpucc/qcom,sm8450-gpucc/' "$patch" \
	>"$stage/wrong-device.patch"
reject_mutation wrong-device "$stage/wrong-device.patch"

sed 's/msleep(100);/msleep(0);/' "$patch" >"$stage/no-settle.patch"
reject_mutation no-settle "$stage/no-settle.patch"

sed '/gdsc-register-begin/d' "$patch" >"$stage/incomplete.patch"
reject_mutation incomplete "$stage/incomplete.patch"

sed 's/msleep(100);/regmap_write(NULL, 0, 0);/' "$patch" \
	>"$stage/hardware-write.patch"
reject_mutation hardware-write "$stage/hardware-write.patch"

echo 'PASS common-clock trace verifier rejects writable, broad, unflushed, incomplete, and hardware-writing mutations'
