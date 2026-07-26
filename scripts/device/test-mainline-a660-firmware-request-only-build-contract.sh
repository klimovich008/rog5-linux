#!/bin/sh
set -eu

repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)
builder=$repo/scripts/device/build-mainline-a660-firmware-request-only-candidate.sh
verifier=$repo/scripts/device/verify-mainline-a660-firmware-request-only-build.sh
comparator=$repo/scripts/device/compare-mainline-a660-firmware-request-only-builds.sh

for input in "$builder" "$verifier" "$comparator"; do
	[ -x "$input" ] || {
		echo "FAIL missing executable A660 firmware-only build tool: $input" >&2
		exit 1
	}
	sh -n "$input"
done

for contract in \
	'verify-mainline-a660-registration-build.sh' \
	'verify-a660-firmware-request-only-patch.sh' \
	'0012-drm-msm-a6xx-propagate-gmu-pwrlevels-error.patch' \
	'0013-drm-msm-add-a660-firmware-request-only-diagnostic.patch' \
	0d223284805217246efaefa2fc8ad431d94d05e4fa9269f2ef86e3fb29378637 \
	3413678758f97ea16d8e53e7a24a2bc62a871b333851c32bd8242687bbdc1054 \
	d9ac316489f4258d389d6298659d5e9c22183400 \
	c796deb1cc54e942f8bb46a2c76a7199e19e5c92 \
	'7.1.4-rog5-a660reg1' \
	'/root/build/rog5-linux-7.1.4-a660-firmware-only' \
	'CONFIG_DRM_MSM=m' \
	'CONFIG_DRM_MSM_KMS=n' \
	'CONFIG_SM_GPUCC_8350=m' \
	'firmware_request_only:Request exact A660 firmware once and reject DRM open before GPU power (bool)' \
	'A660 firmware-only passed; reject open' \
	'A660 firmware-only failed: %d' \
	'drivers/gpu/drm/msm/msm.ko' \
	'drivers/clk/qcom/gpucc-sm8350.ko' \
	'drivers/soc/qcom/mdt_loader.ko' \
	'Module.symvers' \
	'modules.tar.gz' \
	'a660_sqe[.]fw|a660_gmu[.]bin|a660_zap[.]mbn' \
	'accepted registration Image is unchanged' \
	'firmware-only MSM module differs'
do
	if ! grep -Fq "$contract" "$builder" "$verifier" "$comparator"; then
		echo "FAIL A660 firmware-only build tools omit: $contract" >&2
		exit 1
	fi
done

if grep -Eq \
	'fastboot[[:space:]]+flash|dd[[:space:]].*of=/dev/|mount[[:space:]].*/dev/' \
	"$builder" "$verifier" "$comparator"
then
	echo 'FAIL A660 firmware-only build path contains a persistent-write path' >&2
	exit 1
fi

if [ -n "${BUILD_DIR:-}" ] || [ -n "${SOURCE_DIR:-}" ] ||
	[ -n "${FIRMWARE_ROOT:-}" ] || [ -n "${KERNEL_CONFIG:-}" ] ||
	[ -n "${REGISTRATION_BUILD:-}" ]
then
	[ -n "${BUILD_DIR:-}" ]
	[ -n "${SOURCE_DIR:-}" ]
	[ -n "${FIRMWARE_ROOT:-}" ]
	[ -n "${KERNEL_CONFIG:-}" ]
	[ -n "${REGISTRATION_BUILD:-}" ]
	"$verifier" "$BUILD_DIR" "$SOURCE_DIR" "$FIRMWARE_ROOT" \
		"$KERNEL_CONFIG" "$REGISTRATION_BUILD"
fi

if [ -n "${BUILD_A:-}" ] || [ -n "${BUILD_B:-}" ]; then
	[ -n "${BUILD_A:-}" ]
	[ -n "${BUILD_B:-}" ]
	"$comparator" "$BUILD_A" "$BUILD_B"
fi

echo 'PASS A660 firmware-request-only kernel build is exact-patch, unchanged-Image, modular, firmware-clean, and reproducible by contract'
