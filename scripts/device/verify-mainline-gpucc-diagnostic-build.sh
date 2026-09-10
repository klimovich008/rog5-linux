#!/bin/sh
set -eu

output_dir=${1:?usage: verify-mainline-gpucc-diagnostic-build.sh BUILD_DIR BASE_MODULES}
base_modules=${2:?missing accepted network-root module archive}
repo=$(CDPATH= cd -- "$(dirname "$0")/../.." && pwd)
meta=$output_dir/build-meta.txt
module=$output_dir/drivers/clk/qcom/gpucc-sm8350.ko
archive=$output_dir/modules.tar.gz
expected_patched=86f3c68a666446d9bbcb9bd9f90df50f989ba8ea
expected_tree=e22549ee4d4d788b6898f374e8edecfc714797ac
expected_release=7.1.4-g7a5cef0db479

"$repo/scripts/device/verify-mainline-network-root-build.sh" "$output_dir"
[ -s "$module" ] && [ -s "$base_modules" ]
grep -qx "patched_commit=$expected_patched" "$meta"
grep -qx "patched_tree=$expected_tree" "$meta"
grep -qx "kernel_release=$expected_release" "$meta"
[ "$(cat "$output_dir/include/config/kernel.release")" = "$expected_release" ]
grep -qx "trace_patch_sha256=$(sha256sum \
	"$repo/patches/linux-7.1.4/0005-gpucc-sm8350-add-attended-probe-trace.patch" |
	cut -d ' ' -f 1)" "$meta"
check_exact_hash() {
	label=$1
	file=$2
	expected=$3
	actual=$(sha256sum "$file" | cut -d ' ' -f 1)
	[ "$actual" = "$expected" ] || {
		echo "FAIL $label drifted from the accepted network-root build" >&2
		exit 1
	}
}
check_exact_hash config "$output_dir/.config" \
	68fb3025f3677a7dc8607396af9fcb17c75398b3285d624f1588d564e03c513f
check_exact_hash Image "$output_dir/arch/arm64/boot/Image" \
	349c41d660a7eaa695098ce3734d8fea584447fd34849503f9a855269b425daf
check_exact_hash Image.gz "$output_dir/arch/arm64/boot/Image.gz" \
	a1756e36f42a57c90bd85ef33d68aa1424768a45f272cc0514c2992ace0ae6e5

[ "$(modinfo -F name "$module")" = gpucc_sm8350 ]
[ -z "$(modinfo -F depends "$module")" ]
[ "$(modinfo -F vermagic "$module")" = \
	"$expected_release SMP preempt mod_unload aarch64" ]
modinfo -p "$module" |
	grep -Fxq 'probe_trace:Emit progress notices for attended SM8350 GPUCC diagnostics (bool)'
for marker in \
	'ROG5 GPUCC diagnostic: begin' \
	'ROG5 GPUCC diagnostic: map-complete' \
	'ROG5 GPUCC diagnostic: pll0-begin' \
	'ROG5 GPUCC diagnostic: pll0-complete' \
	'ROG5 GPUCC diagnostic: pll1-begin' \
	'ROG5 GPUCC diagnostic: pll1-complete' \
	'ROG5 GPUCC diagnostic: registration-begin' \
	'ROG5 GPUCC diagnostic: registration-complete ret=%d'
do
	strings "$module" | grep -Fq "$marker"
done

module_path=$(tar -tzf "$archive" |
	grep -E '/gpucc-sm8350[.]ko$')
[ "$(printf '%s\n' "$module_path" | wc -l)" -eq 1 ]
[ "$(tar -xOzf "$archive" "$module_path" | sha256sum |
	cut -d ' ' -f 1)" = "$(sha256sum "$module" | cut -d ' ' -f 1)" ]
[ "$(sha256sum "$module" | cut -d ' ' -f 1)" = \
	"$(sed -n 's/^gpucc_module_sha256=//p' "$meta")" ]

base_path=$(tar -tzf "$base_modules" |
	grep -E '/gpucc-sm8350[.]ko$')
[ "$(printf '%s\n' "$base_path" | wc -l)" -eq 1 ]
[ "$(tar -xOzf "$base_modules" "$base_path" | sha256sum |
	cut -d ' ' -f 1)" != "$(sha256sum "$module" | cut -d ' ' -f 1)" ]
[ "$(tar -tzf "$archive")" = "$(tar -tzf "$base_modules")" ]

echo 'PASS reproducible GPUCC diagnostic module, unchanged kernel Image/config, exact ABI, and archive topology'
