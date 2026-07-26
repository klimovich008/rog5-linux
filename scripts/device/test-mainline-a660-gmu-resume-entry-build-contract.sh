#!/bin/sh
set -eu

repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)
builder=$repo/scripts/device/build-mainline-a660-gmu-resume-entry-candidate.sh
verifier=$repo/scripts/device/verify-mainline-a660-gmu-resume-entry-build.sh
comparator=$repo/scripts/device/compare-mainline-a660-gmu-resume-entry-builds.sh

for input in "$builder" "$verifier" "$comparator"; do
	[ -x "$input" ] || {
		echo "FAIL missing executable A660 GMU resume-entry build tool: $input" >&2
		exit 1
	}
	sh -n "$input"
done

for contract in \
	'verify-mainline-a660-ucode-allocation-build.sh' \
	'verify-a660-gmu-resume-entry-patch.sh' \
	'SKIP_V7_UMBRELLA_RUN=1' \
	'0012-drm-msm-a6xx-propagate-gmu-pwrlevels-error.patch' \
	'0013-drm-msm-add-a660-firmware-request-only-diagnostic.patch' \
	'0014-drm-msm-add-a660-ucode-allocation-diagnostic.patch' \
	'0015-drm-msm-add-a660-gmu-resume-entry-diagnostic.patch' \
	0d223284805217246efaefa2fc8ad431d94d05e4fa9269f2ef86e3fb29378637 \
	3413678758f97ea16d8e53e7a24a2bc62a871b333851c32bd8242687bbdc1054 \
	6966d868585e11c5f614598368eb70595025c9543653582e0234aa313edfa3f2 \
	a179ff9e31792238a3bd254297008d805e6a37b5d08125712c0151b1f39b3051 \
	5d6a982bea8fca55959cbc0cdd1b5ba7a6b64e884c8efd619adbba6490319ea5 \
	d9ac316489f4258d389d6298659d5e9c22183400 \
	c796deb1cc54e942f8bb46a2c76a7199e19e5c92 \
	'7.1.4-rog5-a660reg1' \
	'CONFIG_DRM_MSM=m' \
	'CONFIG_DRM_MSM_KMS=n' \
	'CONFIG_SM_GPUCC_8350=m' \
	'firmware_request_only:Request exact A660 firmware once and reject DRM open before GPU power (bool)' \
	'ucode_allocation_only:Allocate and roll back exact A660 ucode once before GPU power (bool)' \
	'gmu_resume_entry_only:Stop one exact A660 open at GMU resume entry before resource activation (bool)' \
	'A660 firmware-only passed; reject open' \
	'A660 ucode-allocation-only passed and rolled back; reject open' \
	'A660 GMU resume entry reached before resource activation; reject resume' \
	'A660 GMU resume entry passed and rolled back; reject open' \
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
	fe5d59675e4f7d490c38cc7e9c02cadb7bbf89047ceb8056aa0a3e13353bcc45 \
	b485e8719d6ddf80542a5dc2fdf5bba795d40c69fa220b44571323a8a1d7d861 \
	116f702a4605363c153cb35a908b1b1031f4e430478993394fe0fdc230db42bc \
	38045b4c68d85d32dadf7d8db28f6ce1665fa2718ded3a9777dc0429035da6e7 \
	'accepted_resume_meta_sha256' \
	'accepted_resume_archive_sha256' \
	'accepted_resume_msm_sha256' \
	'ALLOW_UNPINNED_BUILD' \
	'a660_sqe[.]fw|a660_gmu[.]bin|a660_zap[.]mbn' \
	'accepted v7 Image is unchanged' \
	'resume-entry MSM module differs' \
	'clean-build mismatch'
do
	if ! grep -Fq "$contract" "$builder" "$verifier" "$comparator"; then
		echo "FAIL A660 GMU resume-entry build tools omit: $contract" >&2
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
	echo 'FAIL A660 GMU resume-entry build path contains a persistent-write path' >&2
	exit 1
fi

if [ -n "${BUILD_DIR:-}" ] || [ -n "${SOURCE_DIR:-}" ] ||
	[ -n "${FIRMWARE_ROOT:-}" ] || [ -n "${KERNEL_CONFIG:-}" ] ||
	[ -n "${REGISTRATION_BUILD:-}" ] ||
	[ -n "${FIRMWARE_ONLY_BUILD:-}" ] ||
	[ -n "${UCODE_BUILD:-}" ]
then
	[ -n "${BUILD_DIR:-}" ]
	[ -n "${SOURCE_DIR:-}" ]
	[ -n "${FIRMWARE_ROOT:-}" ]
	[ -n "${KERNEL_CONFIG:-}" ]
	[ -n "${REGISTRATION_BUILD:-}" ]
	[ -n "${FIRMWARE_ONLY_BUILD:-}" ]
	[ -n "${UCODE_BUILD:-}" ]
	"$verifier" "$BUILD_DIR" "$SOURCE_DIR" "$FIRMWARE_ROOT" \
		"$KERNEL_CONFIG" "$REGISTRATION_BUILD" \
		"$FIRMWARE_ONLY_BUILD" "$UCODE_BUILD"
fi

if [ -n "${BUILD_A:-}" ] || [ -n "${BUILD_B:-}" ]; then
	[ -n "${BUILD_A:-}" ]
	[ -n "${BUILD_B:-}" ]
	"$comparator" "$BUILD_A" "$BUILD_B"
fi

echo 'PASS A660 GMU resume-entry kernel build is exact-stack, unchanged-Image, modular, firmware-clean, rollback-safe, and reproducible by contract'
