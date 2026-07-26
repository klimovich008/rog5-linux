#!/bin/sh
set -eu

repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)
verifier=$repo/scripts/device/verify-a660-full-dependency-contract.sh

[ -x "$verifier" ] || {
	echo 'FAIL missing executable A660 full dependency verifier' >&2
	exit 1
}
sh -n "$verifier"

for contract in \
	d9ac316489f4258d389d6298659d5e9c22183400 \
	c796deb1cc54e942f8bb46a2c76a7199e19e5c92 \
	'qcom,adreno-660.1' \
	'qcom,adreno-gmu-660.1' \
	'reg = <0 0x03d00000 0 0x40000>,' \
	'reg = <0 0x03d6a000 0 0x34000>,' \
	'reg = <0x0 0x8b51a000 0x0 0x2000>;' \
	'iommus = <&adreno_smmu 0 0x400>, <&adreno_smmu 1 0x400>;' \
	'iommus = <&adreno_smmu 5 0x400>;' \
	'power-domains = <&gpucc GPU_CX_GDSC>,' \
	'a660_sqe.fw' \
	'a660_gmu.bin' \
	'qcom/sm8350/a660_zap.mbn' \
	'd222f3fe290ef0516ee0ec43082596bad2df0fcbc2e0bbb26987623cef90cf76' \
	'8acab7b417d9ebde89a1de9ae1e2c261d352fcab122e31ecd580cec9fe2ae5e7' \
	'5dbe91cb3fc9655ea2f2a9e1e169a0e30877bec84215899136a519444ca62a3d' \
	'module_param(separate_gpu_kms, bool, 0400);' \
	'msm.separate_gpu_kms=1' \
	'priv->gpu = adreno_load_gpu(dev);' \
	'ret = adreno_load_fw(adreno_gpu);' \
	'ret = a6xx_gmu_resume(a6xx_gpu);' \
	'ret = adreno_zap_shader_load(gpu, GPU_PAS_ID);' \
	'a6xx_gmu_rpmh_init(gmu);' \
	'iommu_attach_device(iommu->domain, dev);' \
	'CONFIG_DRM_MSM=y' \
	'CONFIG_QCOM_MDT_LOADER=y' \
	'CONFIG_ARM_SMMU_QCOM=y'
do
	grep -Fq "$contract" "$verifier" || {
		echo "FAIL full dependency verifier omits: $contract" >&2
		exit 1
	}
done

if grep -Eq 'fastboot|adb|/dev/(block|disk)|[[:space:]]mount[[:space:]]|[[:space:]]dd[[:space:]]' \
	"$verifier"
then
	echo 'FAIL full dependency verifier contains a device-control path' >&2
	exit 1
fi

if [ -n "${SOURCE_DIR:-}" ] || [ -n "${FIRMWARE_ROOT:-}" ] ||
	[ -n "${KERNEL_CONFIG:-}" ]
then
	[ -n "${SOURCE_DIR:-}" ]
	[ -n "${FIRMWARE_ROOT:-}" ]
	[ -n "${KERNEL_CONFIG:-}" ]
	"$verifier" "$SOURCE_DIR" "$FIRMWARE_ROOT" "$KERNEL_CONFIG"
fi

echo 'PASS exact Linux 7.1.4 A660 GPU, GMU, IOMMU, power, firmware, and deferred-open graph is source-audited'
