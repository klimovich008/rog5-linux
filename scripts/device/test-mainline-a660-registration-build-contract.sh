#!/bin/sh
set -eu

repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)
fragment=$repo/configs/kernel/rog5-a660-registration.fragment
builder=$repo/scripts/device/build-mainline-a660-registration-candidate.sh
verifier=$repo/scripts/device/verify-mainline-a660-registration-build.sh

[ -r "$fragment" ] || {
	echo 'FAIL missing A660 registration kernel fragment' >&2
	exit 1
}
[ -x "$builder" ] || {
	echo 'FAIL missing executable A660 registration kernel builder' >&2
	exit 1
}
[ -x "$verifier" ] || {
	echo 'FAIL missing executable A660 registration build verifier' >&2
	exit 1
}
sh -n "$builder"
sh -n "$verifier"

for symbol in \
	CONFIG_DRM_MSM=m \
	CONFIG_SM_GPUCC_8350=m \
	'# CONFIG_DRM_MSM_MDP4 is not set' \
	'# CONFIG_DRM_MSM_MDP5 is not set' \
	'# CONFIG_DRM_MSM_DPU is not set' \
	'# CONFIG_DRM_MSM_DP is not set' \
	'# CONFIG_DRM_MSM_DSI is not set' \
	'# CONFIG_DRM_MSM_HDMI is not set'
do
	grep -Fxq "$symbol" "$fragment" || {
		echo "FAIL A660 registration fragment omits: $symbol" >&2
		exit 1
	}
done

for contract in \
	'verify-mainline-network-root-build.sh' \
	'verify-a660-full-dependency-contract.sh' \
	'verify-a660-gmu-pwrlevels-patch.sh' \
	'0012-drm-msm-a6xx-propagate-gmu-pwrlevels-error.patch' \
	d9ac316489f4258d389d6298659d5e9c22183400 \
	c796deb1cc54e942f8bb46a2c76a7199e19e5c92 \
	'CONFIG_DRM_MSM=m' \
	'CONFIG_DRM_MSM_KMS=n' \
	'CONFIG_SM_GPUCC_8350=m' \
	'drivers/gpu/drm/msm/msm.ko' \
	'drivers/clk/qcom/gpucc-sm8350.ko' \
	'separate_gpu_kms:Use separate DRM device for the GPU' \
	'a660_sqe[.]fw|a660_gmu[.]bin|a660_zap[.]mbn' \
	'Module.symvers' \
	'modules.tar.gz' \
	'readelf -S'
do
	grep -Fq "$contract" "$verifier" || {
		echo "FAIL A660 registration build verifier omits: $contract" >&2
		exit 1
	}
done

if grep -Eq 'fastboot[[:space:]]+flash|dd[[:space:]].*of=/dev/|mount[[:space:]].*/dev/' \
	"$builder" "$verifier"
then
	echo 'FAIL A660 registration build path contains a persistent-write path' >&2
	exit 1
fi

if [ -n "${BUILD_DIR:-}" ] || [ -n "${SOURCE_DIR:-}" ] ||
	[ -n "${FIRMWARE_ROOT:-}" ] || [ -n "${KERNEL_CONFIG:-}" ]
then
	[ -n "${BUILD_DIR:-}" ]
	[ -n "${SOURCE_DIR:-}" ]
	[ -n "${FIRMWARE_ROOT:-}" ]
	[ -n "${KERNEL_CONFIG:-}" ]
	"$verifier" "$BUILD_DIR" "$SOURCE_DIR" "$FIRMWARE_ROOT" \
		"$KERNEL_CONFIG"
fi

echo 'PASS A660 registration kernel is modular, headless, source-pinned, firmware-clean, and build-verifiable'
