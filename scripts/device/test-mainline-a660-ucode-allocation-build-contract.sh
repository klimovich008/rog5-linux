#!/bin/sh
set -eu

repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)
builder=$repo/scripts/device/build-mainline-a660-ucode-allocation-candidate.sh
verifier=$repo/scripts/device/verify-mainline-a660-ucode-allocation-build.sh
comparator=$repo/scripts/device/compare-mainline-a660-ucode-allocation-builds.sh

for input in "$builder" "$verifier" "$comparator"; do
	[ -x "$input" ] || {
		echo "FAIL missing executable A660 ucode-allocation build tool: $input" >&2
		exit 1
	}
	sh -n "$input"
done

for contract in \
	'verify-mainline-a660-firmware-request-only-build.sh' \
	'verify-a660-ucode-allocation-patch.sh' \
	'0012-drm-msm-a6xx-propagate-gmu-pwrlevels-error.patch' \
	'0013-drm-msm-add-a660-firmware-request-only-diagnostic.patch' \
	'0014-drm-msm-add-a660-ucode-allocation-diagnostic.patch' \
	0d223284805217246efaefa2fc8ad431d94d05e4fa9269f2ef86e3fb29378637 \
	3413678758f97ea16d8e53e7a24a2bc62a871b333851c32bd8242687bbdc1054 \
	6966d868585e11c5f614598368eb70595025c9543653582e0234aa313edfa3f2 \
	d9ac316489f4258d389d6298659d5e9c22183400 \
	c796deb1cc54e942f8bb46a2c76a7199e19e5c92 \
	'7.1.4-rog5-a660reg1' \
	'work_source=/tmp/rog5-a660-registration-source' \
	'/root/build/rog5-linux-7.1.4-a660-registration' \
	'CONFIG_DRM_MSM=m' \
	'CONFIG_DRM_MSM_KMS=n' \
	'CONFIG_SM_GPUCC_8350=m' \
	'firmware_request_only:Request exact A660 firmware once and reject DRM open before GPU power (bool)' \
	'ucode_allocation_only:Allocate and roll back exact A660 ucode once before GPU power (bool)' \
	'A660 firmware-only passed; reject open' \
	'A660 firmware-only failed: %d' \
	'A660 ucode-allocation-only passed and rolled back; reject open' \
	'A660 ucode-allocation-only failed: %d' \
	'drivers/gpu/drm/msm/msm.ko' \
	'drivers/clk/qcom/gpucc-sm8350.ko' \
	'drivers/soc/qcom/mdt_loader.ko' \
	'Module.symvers' \
	'modules.tar.gz' \
	d2f3a6f919c3e1abf3d10d99a77165e43de0fc4888fda338f0625bae57cb35e0 \
	52624d3fc8d51234ff4f4d4c31f302d2e031c736997dd9645e96e89b4fcd00db \
	9d735cac93cf5720e885a4151e3eb8c1257aa52167dd40b439252adb31fbe307 \
	a26677921a28fc0744fe8976c3f7c9dae4257617a92a0a2f18c21ad6d03a4477 \
	c4ec64279bc72ac9d524717512c94a8f5c47eba6a4cf7cadbfbc620012dac563 \
	001c1526eef5526b35663e9d3d16621e07949e3adc0ca4aa4ddd5f1f7a4e4be3 \
	eb2df946472603d932d63a25f5350535b104303e5db6ac8dc66273647460b082 \
	04149f41648f12925a6f04261eed96bfecdd6174a10462c82c36213fef0d1bc9 \
	9fced0679b2fa0a4a434fba7ff4b6e33ded021d7376e19c08dd09926689b8654 \
	ad3c4b441db6d2701e0e6bb945c1a4bf52d284e209873cb4b9250014386da680 \
	fe5d59675e4f7d490c38cc7e9c02cadb7bbf89047ceb8056aa0a3e13353bcc45 \
	'accepted ucode-allocation build metadata' \
	'ALLOW_UNPINNED_BUILD' \
	'a660_sqe[.]fw|a660_gmu[.]bin|a660_zap[.]mbn' \
	'accepted firmware-only Image is unchanged' \
	'ucode-allocation MSM module differs' \
	'module archive build links differ'
do
	if ! grep -Fq "$contract" "$builder" "$verifier" "$comparator"; then
		echo "FAIL A660 ucode-allocation build tools omit: $contract" >&2
		exit 1
	fi
done

for signal_contract in \
	"trap 'exit 130' INT" \
	"trap 'exit 143' TERM"
do
	grep -Fq "$signal_contract" "$builder" || {
		echo "FAIL builder signal handling omits: $signal_contract" >&2
		exit 1
	}
done

if grep -Eq \
	'fastboot[[:space:]]+flash|dd[[:space:]].*of=/dev/|mount[[:space:]].*/dev/' \
	"$builder" "$verifier" "$comparator"
then
	echo 'FAIL A660 ucode-allocation build path contains a persistent-write path' >&2
	exit 1
fi

if [ -n "${BUILD_DIR:-}" ] || [ -n "${SOURCE_DIR:-}" ] ||
	[ -n "${FIRMWARE_ROOT:-}" ] || [ -n "${KERNEL_CONFIG:-}" ] ||
	[ -n "${REGISTRATION_BUILD:-}" ] ||
	[ -n "${FIRMWARE_ONLY_BUILD:-}" ]
then
	[ -n "${BUILD_DIR:-}" ]
	[ -n "${SOURCE_DIR:-}" ]
	[ -n "${FIRMWARE_ROOT:-}" ]
	[ -n "${KERNEL_CONFIG:-}" ]
	[ -n "${REGISTRATION_BUILD:-}" ]
	[ -n "${FIRMWARE_ONLY_BUILD:-}" ]
	"$verifier" "$BUILD_DIR" "$SOURCE_DIR" "$FIRMWARE_ROOT" \
		"$KERNEL_CONFIG" "$REGISTRATION_BUILD" "$FIRMWARE_ONLY_BUILD"
fi

if [ -n "${BUILD_A:-}" ] || [ -n "${BUILD_B:-}" ]; then
	[ -n "${BUILD_A:-}" ]
	[ -n "${BUILD_B:-}" ]
	"$comparator" "$BUILD_A" "$BUILD_B"
fi

echo 'PASS A660 ucode-allocation kernel build is exact-stack, unchanged-Image, modular, firmware-clean, rollback-safe, and reproducible by contract'
