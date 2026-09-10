#!/bin/sh
set -eu

fail() {
	echo "FAIL $*" >&2
	exit 1
}

output_dir=${1:?usage: verify-mainline-network-root-dual-cell-readonly-build.sh BUILD_DIR}
repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd -P)
base_verifier=$repo/scripts/device/verify-mainline-network-root-build.sh
state=$output_dir/.rog5-kbuild-inputs-v1
modules=$output_dir/modules.tar.gz
symvers=$output_dir/Module.symvers
expected_commit=7ee91d34b5458efa0ac45d979bab82bbd2cb7ea5
expected_tree=ef7703ecc0aad3d625cfbbef296e586d861deefe
expected_release=7.1.4-00001-g7ee91d34b545
module_member=lib/modules/$expected_release/kernel/drivers/power/supply/qcom_battmgr.ko
work=$(mktemp -d)
trap 'find "$work" -depth -delete' EXIT HUP INT TERM

for input in "$base_verifier" "$state" "$modules" "$symvers"; do
	[ -f "$input" ] && [ ! -L "$input" ] && [ -r "$input" ] &&
		[ -s "$input" ] || fail "unsafe or missing candidate build input: $input"
done
[ -x "$base_verifier" ] || fail 'base network-root verifier is not executable'

"$base_verifier" "$output_dir" dual-cell-readonly
for field in \
	"source_commit=$expected_commit" \
	"source_tree=$expected_tree" \
	"expected_release=$expected_release" \
	'compiler_cache=disabled'; do
	grep -Fxq "$field" "$state" ||
		fail "candidate build state changed: $field"
done

[ "$(tar -tzf "$modules" | grep -Fxc "$module_member")" -eq 1 ] ||
	fail 'candidate module archive lacks exactly one qcom_battmgr.ko'
tar --warning=no-timestamp -xzf "$modules" -C "$work" "$module_member"
module=$work/$module_member
[ -f "$module" ] && [ ! -L "$module" ] && [ -s "$module" ] ||
	fail 'candidate qcom_battmgr.ko is not an ordinary non-empty file'
for string in \
	'asus,cell-voltage-readonly' \
	'cell1_voltage_mv=%u cell2_voltage_mv=%u' \
	'cell_voltages'; do
	strings "$module" | grep -Fq "$string" ||
		fail "candidate qcom_battmgr.ko omits read-only ABI: $string"
done
llvm-nm "$module" | grep -Eq '[[:space:]]cell_voltages_show$' ||
	fail 'candidate qcom_battmgr.ko omits the read-only show callback'
if llvm-nm "$module" | grep -Eq '[[:space:]]cell_voltages_store$'; then
	fail 'candidate qcom_battmgr.ko unexpectedly contains a write callback'
fi

printf '%s\n' \
	'status=compile-only-dual-cell-readonly-candidate' \
	'hardware_acceptance=unproven' \
	'authority=none'
echo 'PASS linked network-root kernel contains only the reviewed dual-cell read ABI'
