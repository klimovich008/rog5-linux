#!/bin/sh
set -eu

output_dir=${1:?usage: verify-mainline-gpucc-parent-diagnostic-build.sh BUILD_DIR ACCEPTED_V12_IMAGE ACCEPTED_V12_MODULES}
accepted_image=${2:?missing accepted v12 diagnostic Image}
accepted_modules=${3:?missing accepted v12 diagnostic module archive}
repo=$(CDPATH= cd -- "$(dirname "$0")/../.." && pwd)
meta=$output_dir/build-meta.txt
config=$output_dir/.config
image=$output_dir/arch/arm64/boot/Image
image_gz=$output_dir/arch/arm64/boot/Image.gz
module=$output_dir/drivers/clk/qcom/gpucc-sm8350.ko
archive=$output_dir/modules.tar.gz
symvers=$output_dir/Module.symvers
clk_object=$output_dir/drivers/clk/clk.o
expected_base=7a5cef0db4795d9d453a12e0f61b5b7634fc4d40
expected_gpucc=86f3c68a666446d9bbcb9bd9f90df50f989ba8ea
expected_common=d4bb00313e92514f89bc0a9e7a7dffcb4884834f
expected_ccf=6eef0ab56609f5a5ee6d2de9807178daf1065fa7
expected_orphan=b2059b161861d6d7d1aeb9b7d93ad86b13d85048
expected_parent=f7c0a9d067db77f05a40a5bc242c1e14ac297ac5
expected_tree=adec6b40ce25145e3e18cd82a788aa458514017d
expected_release=7.1.4-g7a5cef0db479
accepted_image_sha=49318395c5ed4850d492e4f29ea841885692bd96b6a5b0982925769282b687d9
accepted_modules_sha=2c246d8ceed3c37cc2afefa56710ac5bbca2bc1bce0ca0409a361f8f5923a2e8

"$repo/scripts/device/verify-mainline-network-root-build.sh" "$output_dir"
for file in "$module" "$symvers" "$clk_object" "$accepted_image" \
	"$accepted_modules"
do
	[ -s "$file" ]
done

grep -qx "kernel_commit=$expected_base" "$meta"
grep -qx "gpucc_patched_commit=$expected_gpucc" "$meta"
grep -qx "common_patched_commit=$expected_common" "$meta"
grep -qx "ccf_patched_commit=$expected_ccf" "$meta"
grep -qx "orphan_patched_commit=$expected_orphan" "$meta"
grep -qx "parent_patched_commit=$expected_parent" "$meta"
grep -qx "patched_tree=$expected_tree" "$meta"
grep -qx "kernel_release=$expected_release" "$meta"
grep -qx "gpucc_trace_patch_sha256=$(sha256sum \
	"$repo/patches/linux-7.1.4/0005-gpucc-sm8350-add-attended-probe-trace.patch" |
	cut -d ' ' -f 1)" "$meta"
grep -qx "common_trace_patch_sha256=$(sha256sum \
	"$repo/patches/linux-7.1.4/0006-qcom-cc-add-attended-registration-trace.patch" |
	cut -d ' ' -f 1)" "$meta"
grep -qx "ccf_trace_patch_sha256=$(sha256sum \
	"$repo/patches/linux-7.1.4/0007-clk-trace-attended-SM8350-GPUCC-CCF-registration.patch" |
	cut -d ' ' -f 1)" "$meta"
grep -qx "orphan_trace_patch_sha256=$(sha256sum \
	"$repo/patches/linux-7.1.4/0008-clk-trace-attended-SM8350-GPUCC-orphan-reparent.patch" |
	cut -d ' ' -f 1)" "$meta"
grep -qx "parent_trace_patch_sha256=$(sha256sum \
	"$repo/patches/linux-7.1.4/0009-clk-trace-attended-SM8350-GPUCC-orphan-parent-lookup.patch" |
	cut -d ' ' -f 1)" "$meta"

check_exact_hash() {
	label=$1
	file=$2
	expected=$3
	actual=$(sha256sum "$file" | cut -d ' ' -f 1)
	[ "$actual" = "$expected" ] || {
		echo "FAIL $label does not match the reviewed clean builds" >&2
		exit 1
	}
}
check_exact_hash config "$config" \
	68fb3025f3677a7dc8607396af9fcb17c75398b3285d624f1588d564e03c513f
check_exact_hash Image "$image" \
	1c5c1bd3841c6fdc2f0ebc29fb19f43099e4d5e70d63d9a183cd9646f6c35c28
check_exact_hash Image.gz "$image_gz" \
	217f66c1370600542fe6a6b1349ae7e449bceade5ee64d56504e259ee76e0049
check_exact_hash modules "$archive" \
	22d069c6d8bea928f5fac6ab3107bb007b2cb76fd95fc85541780cb5d315f199
check_exact_hash GPUCC-module "$module" \
	574fefd282fbff6577c921a116a5485546e788ca338802b960b26b9ad9fc6d9c
check_exact_hash exported-symbol-table "$symvers" \
	008919805fa413eefe4bb42675bcf6467a0a5bcef87158af05deec5e4cf75365
check_exact_hash CCF-object "$clk_object" \
	53b960685d79f558f866674ff62325d2a0a20c28f2a39e9f104f5023c2087ddd
check_exact_hash build-metadata "$meta" \
	81d0aec7670f0127113d455fcae562a61d3d8750634f06fa126e4fc05ac951bd
check_exact_hash accepted-v12-Image "$accepted_image" "$accepted_image_sha"
check_exact_hash accepted-v12-modules "$accepted_modules" \
	"$accepted_modules_sha"

! cmp -s "$image" "$accepted_image"
! cmp -s "$archive" "$accepted_modules"
[ "$(cat "$output_dir/include/config/kernel.release")" = "$expected_release" ]
for symbol in \
	CONFIG_COMMON_CLK_QCOM=y \
	CONFIG_QCOM_GDSC=y \
	CONFIG_SM_GPUCC_8350=m
do
	grep -qx "$symbol" "$config"
done

strings "$image" | grep -Fxq 'rog5_qcom_cc_probe_trace'
strings "$image" |
	grep -Fxq 'ROG5 QCOM CC diagnostic: phase=%s index=%d ret=%d'
strings "$image" | grep -Fxq 'rog5_ccf_register_trace'
strings "$image" |
	grep -Fxq 'ROG5 CCF diagnostic: phase=%s clock=%s ret=%d'
for phase in \
	managed-entry \
	devres-allocation-begin \
	devres-allocation-complete \
	hw-register-begin \
	hw-register-complete \
	devres-commit-begin \
	devres-commit-complete \
	devres-release-begin \
	devres-release-complete \
	managed-exit \
	register-entry \
	init-detach-complete \
	core-allocation-begin \
	core-allocation-complete \
	name-copy-begin \
	name-copy-complete \
	runtime-init-begin \
	runtime-init-complete \
	parent-map-begin \
	parent-map-complete \
	consumer-allocation-begin \
	consumer-allocation-complete \
	consumer-link-begin \
	consumer-link-complete \
	core-init-begin \
	core-init-complete \
	register-exit \
	core-init-entry \
	prepare-lock-begin \
	prepare-lock-complete \
	hw-core-link-complete \
	runtime-get-begin \
	runtime-get-complete \
	duplicate-lookup-begin \
	duplicate-lookup-complete \
	ops-validation-begin \
	ops-validation-complete \
	driver-init-begin \
	driver-init-complete \
	parent-init-begin \
	parent-init-complete \
	topology-insert-begin \
	topology-insert-complete \
	accuracy-begin \
	accuracy-complete \
	phase-begin \
	phase-complete \
	duty-begin \
	duty-complete \
	rate-begin \
	rate-complete \
	critical-begin \
	critical-complete \
	orphan-reparent-begin \
	orphan-reparent-complete \
	runtime-put-begin \
	runtime-put-complete \
	prepare-unlock-begin \
	prepare-unlock-complete \
	debug-register-begin \
	debug-register-complete \
	core-init-exit \
	regmap-device-lookup-begin \
	regmap-device-lookup-complete \
	regmap-device-assign-begin \
	regmap-device-assign-complete \
	regmap-parent-assign-begin \
	regmap-parent-assign-complete \
	regmap-lookup-complete \
	ccf-managed-register-begin \
	ccf-managed-register-complete \
	orphan-scan-entry \
	orphan-parent-lookup-begin \
	orphan-parent-lookup-complete \
	orphan-parent-resolved \
	orphan-set-parent-before-begin \
	orphan-set-parent-before-complete \
	orphan-set-parent-after-begin \
	orphan-set-parent-after-complete \
	orphan-accuracy-begin \
	orphan-accuracy-complete \
	orphan-rates-begin \
	orphan-rates-complete \
	orphan-req-rate-complete \
	orphan-scan-complete \
	orphan-parent-shape \
	orphan-runtime-state \
	orphan-get-parent-begin \
	orphan-get-parent-complete \
	orphan-parent-cache-begin \
	orphan-parent-cache-complete
do
	strings "$image" | grep -Fxq "$phase"
done

[ "$(modinfo -F name "$module")" = gpucc_sm8350 ]
[ -z "$(modinfo -F depends "$module")" ]
[ "$(modinfo -F vermagic "$module")" = \
	"$expected_release SMP preempt mod_unload aarch64" ]
modinfo -p "$module" |
	grep -Fxq \
	'probe_trace:Emit progress notices for attended SM8350 GPUCC diagnostics (bool)'
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

module_path=$(tar -tzf "$archive" | grep -E '/gpucc-sm8350[.]ko$')
[ "$(printf '%s\n' "$module_path" | wc -l)" -eq 1 ]
[ "$(tar -xOzf "$archive" "$module_path" | sha256sum |
	cut -d ' ' -f 1)" = "$(sha256sum "$module" | cut -d ' ' -f 1)" ]
[ "$(tar -tzf "$archive")" = "$(tar -tzf "$accepted_modules")" ]

echo 'PASS exact v13 Image/modules, bounded inner-parent phases, unchanged exported ABI, matching split BTF, and accepted archive topology'
