#!/bin/sh
set -eu

output_dir=${1:?usage: verify-mainline-gpucc-ccf-diagnostic-build.sh BUILD_DIR ACCEPTED_IMAGE ACCEPTED_MODULES}
accepted_image=${2:?missing accepted common-clock diagnostic Image}
accepted_modules=${3:?missing accepted common-clock diagnostic module archive}
repo=$(CDPATH= cd -- "$(dirname "$0")/../.." && pwd)
meta=$output_dir/build-meta.txt
config=$output_dir/.config
image=$output_dir/arch/arm64/boot/Image
image_gz=$output_dir/arch/arm64/boot/Image.gz
module=$output_dir/drivers/clk/qcom/gpucc-sm8350.ko
archive=$output_dir/modules.tar.gz
symvers=$output_dir/Module.symvers
expected_base=7a5cef0db4795d9d453a12e0f61b5b7634fc4d40
expected_gpucc=86f3c68a666446d9bbcb9bd9f90df50f989ba8ea
expected_common=d4bb00313e92514f89bc0a9e7a7dffcb4884834f
expected_ccf=6eef0ab56609f5a5ee6d2de9807178daf1065fa7
expected_tree=743a976fd13c1a5c30d93c7dac9b9b4d1cbc3b11
expected_release=7.1.4-g7a5cef0db479
accepted_image_sha=c0127c338b6af50a51e51c1e4837961d9806d0be969cd7337c3e597583e2dd62
accepted_modules_sha=7c49c648c076326a6f008082f0d38e389bd8bb7c8a867ee0935d83e6a4195224

"$repo/scripts/device/verify-mainline-network-root-build.sh" "$output_dir"
for file in "$module" "$symvers" "$accepted_image" "$accepted_modules"; do
	[ -s "$file" ]
done

grep -qx "kernel_commit=$expected_base" "$meta"
grep -qx "gpucc_patched_commit=$expected_gpucc" "$meta"
grep -qx "common_patched_commit=$expected_common" "$meta"
grep -qx "ccf_patched_commit=$expected_ccf" "$meta"
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
	d6bb0a9a7c4d4496aac8593df1727c916f130a10741b2691eebbf28555527021
check_exact_hash Image.gz "$image_gz" \
	f4138e28b224423eaf0de334344fead6204ac9a0f141dbd8d8f0652d493c73ac
check_exact_hash modules "$archive" \
	b1c2bd02d67773e2b213c8aec2e30378580f8bcc638ff378650182a335f6f5d0
check_exact_hash GPUCC-module "$module" \
	3c663bed417bb3bd7438b422ebf3531eca48e53afebc66a4574c7d87f7a8f421
check_exact_hash exported-symbol-table "$symvers" \
	008919805fa413eefe4bb42675bcf6467a0a5bcef87158af05deec5e4cf75365
check_exact_hash build-metadata "$meta" \
	f0bce6e0a4611c7a7de328fc687bc7453dcf669da8782ef50bfdde05809ded6c
check_exact_hash accepted-Image "$accepted_image" "$accepted_image_sha"
check_exact_hash accepted-modules "$accepted_modules" "$accepted_modules_sha"

! cmp -s "$image" "$accepted_image"
! cmp -s "$archive" "$accepted_modules"
[ "$(cat "$output_dir/include/config/kernel.release")" = "$expected_release" ]
for symbol in \
	CONFIG_COMMON_CLK_QCOM=y \
	CONFIG_QCOM_GDSC=y \
	CONFIG_SM_GPUCC_8350=m; do
	grep -qx "$symbol" "$config"
done

strings "$image" | grep -Fxq 'rog5_qcom_cc_probe_trace'
strings "$image" |
	grep -Fxq 'ROG5 QCOM CC diagnostic: phase=%s index=%d ret=%d'
for phase in \
	entry \
	allocation-complete \
	power-domain-attach-begin \
	power-domain-attach-complete \
	reset-register-begin \
	reset-register-complete \
	gdsc-allocation-begin \
	gdsc-allocation-complete \
	gdsc-register-begin \
	gdsc-register-complete \
	gdsc-action-begin \
	gdsc-action-complete \
	drop-protected-begin \
	drop-protected-complete \
	clock-hw-register-begin \
	clock-hw-register-complete \
	clock-regmap-register-begin \
	clock-regmap-register-complete \
	provider-register-begin \
	provider-register-complete \
	interconnect-register-begin \
	interconnect-register-complete \
	exit
do
	strings "$image" | grep -Fxq "$phase"
done

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
	ccf-managed-register-complete
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

echo 'PASS exact CCF diagnostic Image/modules, 72 CCF boundaries, unchanged exported ABI, matching split BTF, and accepted archive topology'
