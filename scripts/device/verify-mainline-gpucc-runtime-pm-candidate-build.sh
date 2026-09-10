#!/bin/sh
set -eu

output_dir=${1:?usage: verify-mainline-gpucc-runtime-pm-candidate-build.sh BUILD_DIR ACCEPTED_V14_IMAGE ACCEPTED_V14_MODULES ACCEPTED_V14_SYMVERS PINNED_V14_SOURCE}
accepted_image=${2:?missing accepted v14 Image}
accepted_modules=${3:?missing accepted v14 module archive}
accepted_symvers=${4:?missing accepted v14 symbol table}
source_dir=${5:?missing pinned v14 source}
repo=$(CDPATH= cd -- "$(dirname "$0")/../.." && pwd)
meta=$output_dir/build-meta.txt
config=$output_dir/.config
image=$output_dir/arch/arm64/boot/Image
image_gz=$output_dir/arch/arm64/boot/Image.gz
module=$output_dir/drivers/clk/qcom/gpucc-sm8350.ko
archive=$output_dir/modules.tar.gz
symvers=$output_dir/Module.symvers
clk_object=$output_dir/drivers/clk/clk.o
rcg2_object=$output_dir/drivers/clk/qcom/clk-rcg2.o
expected_release=7.1.4-g7a5cef0db479

"$repo/scripts/device/verify-mainline-network-root-build.sh" "$output_dir"
"$repo/scripts/device/verify-qcom-cc-registration-trace-patch.sh" \
	"$repo/patches/linux-7.1.4/0006-qcom-cc-add-attended-registration-trace.patch" \
	"$repo/patches/linux-7.1.4/0005-gpucc-sm8350-add-attended-probe-trace.patch" \
	>/dev/null
"$repo/scripts/device/verify-ccf-registration-trace-patch.sh" \
	"$repo/patches/linux-7.1.4/0007-clk-trace-attended-SM8350-GPUCC-CCF-registration.patch" \
	>/dev/null
"$repo/scripts/device/verify-ccf-orphan-reparent-trace-patch.sh" \
	"$repo/patches/linux-7.1.4/0008-clk-trace-attended-SM8350-GPUCC-orphan-reparent.patch" \
	>/dev/null
"$repo/scripts/device/verify-ccf-orphan-parent-trace-patch.sh" \
	"$repo/patches/linux-7.1.4/0009-clk-trace-attended-SM8350-GPUCC-orphan-parent-lookup.patch" \
	>/dev/null
"$repo/scripts/device/verify-rcg2-parent-read-trace-patch.sh" \
	"$repo/patches/linux-7.1.4/0010-clk-qcom-trace-attended-SM8350-DISPCC-RCG-parent-read.patch" \
	>/dev/null
"$repo/scripts/device/verify-clk-orphan-runtime-pm-patch.sh" \
	"$repo/patches/linux-7.1.4/0011-clk-guard-orphan-reparent-with-runtime-PM.patch" \
	"$source_dir" >/dev/null
python3 "$repo/scripts/device/test-clk-orphan-runtime-pm-lock-model.py" \
	>/dev/null

for file in "$meta" "$config" "$image" "$image_gz" "$module" "$archive" \
	"$symvers" "$clk_object" "$rcg2_object" "$accepted_image" \
	"$accepted_modules" "$accepted_symvers"
do
	[ -s "$file" ]
done

for identity in \
	'kernel_commit=7a5cef0db4795d9d453a12e0f61b5b7634fc4d40' \
	'gpucc_patched_commit=86f3c68a666446d9bbcb9bd9f90df50f989ba8ea' \
	'common_patched_commit=d4bb00313e92514f89bc0a9e7a7dffcb4884834f' \
	'ccf_patched_commit=6eef0ab56609f5a5ee6d2de9807178daf1065fa7' \
	'orphan_patched_commit=b2059b161861d6d7d1aeb9b7d93ad86b13d85048' \
	'parent_patched_commit=f7c0a9d067db77f05a40a5bc242c1e14ac297ac5' \
	'rcg2_patched_commit=6e40861cc51c067f9989c4513003e8fbd046c22f' \
	'orphan_runtime_pm_patched_commit=d9ac316489f4258d389d6298659d5e9c22183400' \
	'patched_tree=c796deb1cc54e942f8bb46a2c76a7199e19e5c92' \
	'rcg2_trace_patch_sha256=ac7975bf5f4cb2791f45a2fe8b5b811c7e60fd4692f8aff4cd71a2f2150fa3c6' \
	'orphan_runtime_pm_patch_sha256=a309fe55dc6221f4475c22beb43018dde0f2eb107fa60e84f8e43f28e17a4a25' \
	"kernel_release=$expected_release"
do
	grep -Fqx "$identity" "$meta"
done

check_exact_hash() {
	label=$1
	file=$2
	expected=$3
	actual=$(sha256sum "$file" | cut -d ' ' -f 1)
	[ "$actual" = "$expected" ] || {
		echo "FAIL $label does not match the reviewed v15 clean build" >&2
		exit 1
	}
}

check_exact_hash config "$config" \
	68fb3025f3677a7dc8607396af9fcb17c75398b3285d624f1588d564e03c513f
check_exact_hash Image "$image" \
	d30df38804750ded48607135a7d23d4f95e0947c49b68395a8f6818c4a27c54b
check_exact_hash Image.gz "$image_gz" \
	a620dd40df6d495e00a8f7f84e707c9ceb7483f0828afb2372792985e69f008e
check_exact_hash modules "$archive" \
	9350e5a010c0af11fe4bde48527d056701c83a0072be4ad29cce2565a75204a1
check_exact_hash GPUCC-module "$module" \
	9ac07151490fe4844462945014e0a74674b43841e4cea1cfc4c3560231067d2a
check_exact_hash exported-symbol-table "$symvers" \
	008919805fa413eefe4bb42675bcf6467a0a5bcef87158af05deec5e4cf75365
check_exact_hash CCF-object "$clk_object" \
	96b4831bbaabe996c950a31907039e5374547069ec502ce08a8056b9a5bdf193
check_exact_hash RCG2-object "$rcg2_object" \
	28cf32faa79b9832337e036471b86b12b29a68d198a285fb88f6c6b6f2c4df48
check_exact_hash build-metadata "$meta" \
	21deef91a5fc0864b9c43389cec6ea0f326e1f68e47265f2514986f2f13712f1
check_exact_hash accepted-v14-Image "$accepted_image" \
	5759d3d15ca60f260aa89731aa78c94acd5d183eca67dc24c3723f8877f213e3
check_exact_hash accepted-v14-modules "$accepted_modules" \
	9350e5a010c0af11fe4bde48527d056701c83a0072be4ad29cce2565a75204a1
check_exact_hash accepted-v14-symbols "$accepted_symvers" \
	008919805fa413eefe4bb42675bcf6467a0a5bcef87158af05deec5e4cf75365

cmp "$symvers" "$accepted_symvers"
cmp "$archive" "$accepted_modules"
! cmp -s "$image" "$accepted_image"
[ "$(cat "$output_dir/include/config/kernel.release")" = "$expected_release" ]

for symbol in \
	CONFIG_COMMON_CLK_QCOM=y \
	CONFIG_QCOM_GDSC=y \
	CONFIG_SM_GPUCC_8350=m
do
	grep -qx "$symbol" "$config"
done

strings "$image" | grep -Fxq 'rog5_qcom_cc_probe_trace'
strings "$image" | grep -Fxq 'rog5_ccf_register_trace'
strings "$image" | grep -Fxq 'rog5_rcg2_parent_trace'
for marker in \
	runtime-get-all-begin \
	runtime-get-all-complete \
	runtime-put-all-begin \
	runtime-put-all-complete \
	orphan-parent-lookup-begin \
	parent-read-begin \
	parent-read-complete \
	disp_cc_mdss_pclk0_clk_src
do
	strings "$image" | grep -Fxq "$marker"
done

[ "$(modinfo -F name "$module")" = gpucc_sm8350 ]
[ -z "$(modinfo -F depends "$module")" ]
[ "$(modinfo -F vermagic "$module")" = \
	"$expected_release SMP preempt mod_unload aarch64" ]
readelf -S "$module" | grep -Eq '[[:space:]][.]BTF[[:space:]]'

module_path=$(tar -tzf "$archive" | grep -E '/gpucc-sm8350[.]ko$')
[ "$(printf '%s\n' "$module_path" | wc -l)" -eq 1 ]
[ "$(tar -xOzf "$archive" "$module_path" | sha256sum |
	cut -d ' ' -f 1)" = "$(sha256sum "$module" | cut -d ' ' -f 1)" ]

echo 'PASS exact v15 Image, two-build reproducibility contract, unchanged ABI/modules/RCG2, and tested CCF runtime-PM ordering'
