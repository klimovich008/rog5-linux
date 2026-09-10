#!/bin/sh
set -eu

output_dir=${1:?usage: verify-mainline-a660-registration-build.sh BUILD_DIR PINNED_SOURCE FIRMWARE_ROOT ACCEPTED_V18_CONFIG}
source_dir=${2:?missing pinned source}
firmware_root=${3:?missing firmware root}
accepted_config=${4:?missing accepted v18 config}
repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)
meta=$output_dir/build-meta.txt
config=$output_dir/.config
image=$output_dir/arch/arm64/boot/Image
image_gz=$output_dir/arch/arm64/boot/Image.gz
archive=$output_dir/modules.tar.gz
symvers=$output_dir/Module.symvers
msm_module=$output_dir/drivers/gpu/drm/msm/msm.ko
gpucc_module=$output_dir/drivers/clk/qcom/gpucc-sm8350.ko
mdt_module=$output_dir/drivers/soc/qcom/mdt_loader.ko
expected_release=7.1.4-rog5-a660reg1
kms_state=CONFIG_DRM_MSM_KMS=n

"$repo/scripts/device/verify-mainline-network-root-build.sh" "$output_dir"
"$repo/scripts/device/verify-a660-full-dependency-contract.sh" \
	"$source_dir" "$firmware_root" "$accepted_config" >/dev/null
"$repo/scripts/device/verify-a660-gmu-pwrlevels-patch.sh" \
	"$source_dir" >/dev/null

for file in "$meta" "$config" "$image" "$image_gz" "$archive" "$symvers" \
	"$msm_module" "$gpucc_module" "$mdt_module"
do
	[ -s "$file" ]
done
[ "$kms_state" = CONFIG_DRM_MSM_KMS=n ]

for identity in \
	'kernel_commit=7a5cef0db4795d9d453a12e0f61b5b7634fc4d40' \
	'source_commit=d9ac316489f4258d389d6298659d5e9c22183400' \
	'source_tree=c796deb1cc54e942f8bb46a2c76a7199e19e5c92' \
	"kernel_release=$expected_release" \
	'gmu_patch_sha256=0d223284805217246efaefa2fc8ad431d94d05e4fa9269f2ef86e3fb29378637' \
	'patched_a6xx_gmu_sha256=126d1011942083ad63516de0bee1d62f18db4752199a1cbc6cfb5be3230e4ace' \
	'python_hash_seed=0' \
	'pahole_jobs=1'
do
	grep -Fqx "$identity" "$meta"
done

check_meta_hash() {
	label=$1
	file=$2
	expected=$(sed -n "s/^${label}=//p" "$meta")
	[ "$(printf '%s\n' "$expected" |
		awk 'NF { count++ } END { print count + 0 }')" -eq 1 ]
	[ "$(sha256sum "$file" | cut -d ' ' -f 1)" = "$expected" ]
}

check_meta_hash base_fragment_sha256 \
	"$repo/configs/kernel/rog5-mainline.fragment"
check_meta_hash network_fragment_sha256 \
	"$repo/configs/kernel/rog5-network-root.fragment"
check_meta_hash registration_fragment_sha256 \
	"$repo/configs/kernel/rog5-a660-registration.fragment"
check_meta_hash gmu_patch_sha256 \
	"$repo/patches/linux-7.1.4/0012-drm-msm-a6xx-propagate-gmu-pwrlevels-error.patch"
check_meta_hash config_sha256 "$config"
check_meta_hash image_sha256 "$image"
check_meta_hash image_gz_sha256 "$image_gz"
check_meta_hash modules_sha256 "$archive"
check_meta_hash module_symvers_sha256 "$symvers"
check_meta_hash gpucc_module_sha256 "$gpucc_module"
check_meta_hash msm_module_sha256 "$msm_module"

[ "$(sha256sum "$accepted_config" | cut -d ' ' -f 1)" = \
	68fb3025f3677a7dc8607396af9fcb17c75398b3285d624f1588d564e03c513f ]
[ "$(cat "$output_dir/include/config/kernel.release")" = \
	"$expected_release" ]

for symbol in \
	CONFIG_DRM=y \
	CONFIG_DRM_MSM=m \
	CONFIG_DRM_MSM_GPU_STATE=y \
	CONFIG_SM_GPUCC_8350=m \
	CONFIG_QCOM_SCM=y \
	CONFIG_QCOM_MDT_LOADER=m \
	CONFIG_QCOM_RPMH=y \
	CONFIG_QCOM_RPMHPD=y \
	CONFIG_QCOM_RPMPD=y \
	CONFIG_QCOM_COMMAND_DB=y \
	CONFIG_QCOM_AOSS_QMP=y \
	CONFIG_QCOM_LLCC=y \
	CONFIG_REGULATOR_QCOM_RPMH=y \
	CONFIG_ARM_SMMU=y \
	CONFIG_ARM_SMMU_QCOM=y \
	CONFIG_INTERCONNECT_QCOM_SM8350=y \
	CONFIG_PM_GENERIC_DOMAINS=y \
	CONFIG_PM_GENERIC_DOMAINS_OF=y
do
	grep -qx "$symbol" "$config"
done

for symbol in DRM_MSM_KMS DRM_MSM_KMS_FBDEV DRM_MSM_MDSS DRM_MSM_MDP4 \
	DRM_MSM_MDP5 DRM_MSM_DPU DRM_MSM_DP DRM_MSM_DSI DRM_MSM_HDMI \
	SCSI SCSI_UFSHCD SCSI_UFS_QCOM BLK_DEV_SD RPMB
do
	if grep -Eq "^CONFIG_$symbol=(y|m)$" "$config"; then
		echo "FAIL registration config enables CONFIG_$symbol" >&2
		exit 1
	fi
done

[ "$(modinfo -F name "$msm_module")" = msm ]
[ "$(modinfo -F name "$gpucc_module")" = gpucc_sm8350 ]
[ "$(modinfo -F name "$mdt_module")" = mdt_loader ]
expected_vermagic="$expected_release SMP preempt mod_unload aarch64"
[ "$(modinfo -F vermagic "$msm_module")" = "$expected_vermagic" ]
[ "$(modinfo -F vermagic "$gpucc_module")" = "$expected_vermagic" ]
[ "$(modinfo -F vermagic "$mdt_module")" = "$expected_vermagic" ]
printf ',%s,\n' "$(modinfo -F depends "$msm_module")" |
	grep -Fq ',mdt_loader,'
modinfo -p "$msm_module" |
	grep -Fxq 'separate_gpu_kms: (bool)'
modinfo -p "$gpucc_module" |
	grep -Fxq \
	'probe_trace:Emit progress notices for attended SM8350 GPUCC diagnostics (bool)'
readelf -S "$msm_module" | grep -Eq '[[:space:]][.]BTF[[:space:]]'
readelf -S "$gpucc_module" | grep -Eq '[[:space:]][.]BTF[[:space:]]'
readelf -S "$mdt_module" | grep -Eq '[[:space:]][.]BTF[[:space:]]'

msm_path=$(tar -tzf "$archive" |
	grep -E "/$expected_release/kernel/drivers/gpu/drm/msm/msm[.]ko$")
gpucc_path=$(tar -tzf "$archive" |
	grep -E "/$expected_release/kernel/drivers/clk/qcom/gpucc-sm8350[.]ko$")
mdt_path=$(tar -tzf "$archive" |
	grep -E "/$expected_release/kernel/drivers/soc/qcom/mdt_loader[.]ko$")
[ "$(printf '%s\n' "$msm_path" | wc -l)" -eq 1 ]
[ "$(printf '%s\n' "$gpucc_path" | wc -l)" -eq 1 ]
[ "$(printf '%s\n' "$mdt_path" | wc -l)" -eq 1 ]
[ "$(tar -xOzf "$archive" "$msm_path" | sha256sum |
	cut -d ' ' -f 1)" = "$(sha256sum "$msm_module" |
	cut -d ' ' -f 1)" ]
[ "$(tar -xOzf "$archive" "$gpucc_path" | sha256sum |
	cut -d ' ' -f 1)" = "$(sha256sum "$gpucc_module" |
	cut -d ' ' -f 1)" ]
[ "$(tar -xOzf "$archive" "$mdt_path" | sha256sum |
	cut -d ' ' -f 1)" = "$(sha256sum "$mdt_module" |
	cut -d ' ' -f 1)" ]

firmware_pattern='a660_sqe[.]fw|a660_gmu[.]bin|a660_zap[.]mbn'
if tar -tzf "$archive" | grep -Eq "$firmware_pattern"; then
	echo 'FAIL A660 firmware exists in the registration module archive' >&2
	exit 1
fi
if find "$output_dir" -type f -printf '%f\n' |
	grep -Eq "$firmware_pattern"
then
	echo 'FAIL A660 firmware exists in the registration build' >&2
	exit 1
fi

if strings "$image" | grep -Fq separate_gpu_kms; then
	echo 'FAIL MSM DRM remains built into the registration Image' >&2
	exit 1
fi
strings "$msm_module" | grep -Fq separate_gpu_kms

echo 'PASS modular headless A660 registration Image/modules; exact source patch, unique ABI, zero UFS, and zero firmware'
