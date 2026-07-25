#!/bin/sh
set -eu

output_dir=${1:?usage: verify-mainline-gpucc-orphan-diagnostic-build.sh BUILD_DIR ACCEPTED_V11_IMAGE ACCEPTED_V11_MODULES}
accepted_image=${2:?missing accepted v11 diagnostic Image}
accepted_modules=${3:?missing accepted v11 diagnostic module archive}
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
expected_tree=040d5f9b7be022489079b2ea9cab20a04934d85f
expected_release=7.1.4-g7a5cef0db479
accepted_image_sha=d6bb0a9a7c4d4496aac8593df1727c916f130a10741b2691eebbf28555527021
accepted_modules_sha=b1c2bd02d67773e2b213c8aec2e30378580f8bcc638ff378650182a335f6f5d0

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
	49318395c5ed4850d492e4f29ea841885692bd96b6a5b0982925769282b687d9
check_exact_hash Image.gz "$image_gz" \
	193fc0cafc285bab4ff065c0be624aa11b768ad43685b4605e2a0bcfb96b0bf4
check_exact_hash modules "$archive" \
	2c246d8ceed3c37cc2afefa56710ac5bbca2bc1bce0ca0409a361f8f5923a2e8
check_exact_hash GPUCC-module "$module" \
	79a7d3b7d81c28821dd5199cdbcfe9b2cea5b8bc59b6d6e983a61a15f05424ba
check_exact_hash exported-symbol-table "$symvers" \
	008919805fa413eefe4bb42675bcf6467a0a5bcef87158af05deec5e4cf75365
check_exact_hash CCF-object "$clk_object" \
	222139326edb85a0dcd3fbf5cdb2c48dabc7b655db0cb1de5ff0c0b292f17d0b
check_exact_hash build-metadata "$meta" \
	cec539df7e467df74703cde7514649d45e13b7a903d97bd4300cace2da3decb4
check_exact_hash accepted-v11-Image "$accepted_image" "$accepted_image_sha"
check_exact_hash accepted-v11-modules "$accepted_modules" \
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
	orphan-scan-complete
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

echo 'PASS exact v12 Image/modules, bounded per-orphan phases, unchanged exported ABI, matching split BTF, and accepted archive topology'
