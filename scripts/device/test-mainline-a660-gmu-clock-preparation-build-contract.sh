#!/bin/sh
set -eu

repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)
builder=$repo/scripts/device/build-mainline-a660-gmu-clock-preparation-candidate.sh
verifier=$repo/scripts/device/verify-mainline-a660-gmu-clock-preparation-build.sh
comparator=$repo/scripts/device/compare-mainline-a660-gmu-clock-preparation-builds.sh

for input in "$builder" "$verifier" "$comparator"; do
	[ -x "$input" ] || {
		echo "FAIL missing executable A660 GMU clock-preparation build tool: $input" >&2
		exit 1
	}
	sh -n "$input"
done

for contract in \
	'verify-mainline-a660-gmu-cx-runtime-pm-build.sh' \
	'verify-a660-gmu-clock-preparation-patch.sh' \
	'SKIP_V9_UMBRELLA_RUN=1' \
	'0012-drm-msm-a6xx-propagate-gmu-pwrlevels-error.patch' \
	'0013-drm-msm-add-a660-firmware-request-only-diagnostic.patch' \
	'0014-drm-msm-add-a660-ucode-allocation-diagnostic.patch' \
	'0015-drm-msm-add-a660-gmu-resume-entry-diagnostic.patch' \
	'0016-drm-msm-add-a660-gmu-cx-runtime-pm-diagnostic.patch' \
	'0017-drm-msm-add-a660-gmu-clock-preparation-diagnostic.patch' \
	e7512f8e0589187bddb93f53d83a31b415ce779b3093623fad5515210cf1258b \
	44b9d1281819a3812711786d488fac8ac727dc24f079c6d0e886ee2cb5a60c14 \
	9065053f0ed68a0a200270aa42548cb021e6e26c035dcb0c4ce53341d3c0bfca \
	176391492beacf6b08a0e5d9f45bec7147809779da3a1a2f511cccaebf548c17 \
	d9ac316489f4258d389d6298659d5e9c22183400 \
	c796deb1cc54e942f8bb46a2c76a7199e19e5c92 \
	'7.1.4-rog5-a660reg1' \
	'CONFIG_DRM_MSM=m' \
	'CONFIG_DRM_MSM_KMS=n' \
	'CONFIG_SM_GPUCC_8350=m' \
	'gmu_clock_preparation_only:Prepare and synchronously roll back exact A660 GMU clocks once before secure init (bool)' \
	'A660 GMU GX bookkeeping and seven-clock preparation synchronously rolled back; reject resume' \
	'A660 GMU clock preparation passed and GPU load rolled back; reject open' \
	'drivers/gpu/drm/msm/msm.ko' \
	'drivers/clk/qcom/gpucc-sm8350.ko' \
	'drivers/soc/qcom/mdt_loader.ko' \
	'Module.symvers' \
	'modules.tar.gz' \
	dbc7270338b3c0589863db84fa9bc2abc63a1dfcfb42f83c1394f48122c298cb \
	87e5c3bae7d5034b64aea7212be8372506bf8b28cbdca7fb1b79bb20db50b9d0 \
	c36fd352c48d624eff9f17fb8200c8f151209eae066d1f276ab3bff67c5d465d \
	'accepted_v10_meta_sha256' \
	'accepted_v10_archive_sha256' \
	'accepted_v10_msm_sha256' \
	'ALLOW_UNPINNED_BUILD' \
	'a660_sqe[.]fw|a660_gmu[.]bin|a660_zap[.]mbn' \
	'accepted v10 Image is unchanged' \
	'clock-preparation MSM module differs only' \
	'clean-build mismatch'
do
	if ! grep -Fq "$contract" "$builder" "$verifier" "$comparator"; then
		echo "FAIL A660 GMU clock-preparation build tools omit: $contract" >&2
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
	echo 'FAIL A660 GMU clock-preparation build path contains a persistent-write path' >&2
	exit 1
fi

if [ -n "${BUILD_DIR:-}" ] || [ -n "${SOURCE_DIR:-}" ] ||
	[ -n "${FIRMWARE_ROOT:-}" ] || [ -n "${KERNEL_CONFIG:-}" ] ||
	[ -n "${REGISTRATION_BUILD:-}" ] ||
	[ -n "${FIRMWARE_ONLY_BUILD:-}" ] ||
	[ -n "${UCODE_BUILD:-}" ] || [ -n "${RESUME_BUILD:-}" ] ||
	[ -n "${V10_BUILD:-}" ]
then
	[ -n "${BUILD_DIR:-}" ]
	[ -n "${SOURCE_DIR:-}" ]
	[ -n "${FIRMWARE_ROOT:-}" ]
	[ -n "${KERNEL_CONFIG:-}" ]
	[ -n "${REGISTRATION_BUILD:-}" ]
	[ -n "${FIRMWARE_ONLY_BUILD:-}" ]
	[ -n "${UCODE_BUILD:-}" ]
	[ -n "${RESUME_BUILD:-}" ]
	[ -n "${V10_BUILD:-}" ]
	"$verifier" "$BUILD_DIR" "$SOURCE_DIR" "$FIRMWARE_ROOT" \
		"$KERNEL_CONFIG" "$REGISTRATION_BUILD" \
		"$FIRMWARE_ONLY_BUILD" "$UCODE_BUILD" "$RESUME_BUILD" \
		"$V10_BUILD"
fi

if [ -n "${BUILD_A:-}" ] || [ -n "${BUILD_B:-}" ]; then
	[ -n "${BUILD_A:-}" ]
	[ -n "${BUILD_B:-}" ]
	"$comparator" "$BUILD_A" "$BUILD_B"
fi

echo 'PASS A660 GMU clock-preparation kernel build is exact-stack, unchanged-Image, modular, firmware-clean, rollback-safe, offline-only, and reproducible by contract'
