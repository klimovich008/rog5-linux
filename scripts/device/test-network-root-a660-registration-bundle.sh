#!/bin/sh
set -eu

repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)
verifier=$repo/scripts/device/verify-network-root-a660-registration-bundle.sh

[ -x "$verifier" ] || {
	echo 'FAIL missing executable A660 registration bundle verifier' >&2
	exit 1
}
sh -n "$verifier"

for contract in \
	'verify-network-root-adreno-smmu-bundle.sh' \
	'verify-mainline-a660-registration-build.sh' \
	'test-mainline-a660-registration-build-contract.sh' \
	'test-a660-registration-candidate-dtb.sh' \
	'test-a660-registration-kexec-stage-initramfs.sh' \
	'test-a660-registration-asus-kexec-stage-build-contract.sh' \
	'test-probe-network-root-a660-registration.sh' \
	'test-a660-registration-export.sh' \
	'disarm-network-root-a660-watchdog.sh' \
	'test-disarm-network-root-a660-watchdog.sh' \
	'run-network-root-a660-registration-gate.sh' \
	'test-run-network-root-a660-registration-gate.sh' \
	'run-a660-registration-live-gate.sh' \
	'test-run-a660-registration-live-gate.sh' \
	'verify-a660-registration-v3-live-acceptance.sh' \
	'test-a660-registration-v3-live-acceptance.sh' \
	'verify-adreno-smmu-v21-live-acceptance.sh' \
	'test-adreno-smmu-v21-live-acceptance.sh' \
	c4b9a2ec5afdd73a555031425a5eaedf5ab97a36a69eeefdcfede279ad7ffcd0 \
	e433a95b3cfeeeabd8dd97b4321da3082f934e5bbbca5cb0bfd4f71074355d73 \
	a739f975f87ac30918625178007b4cd7302449ae96c26e5c42185e9e1a0425cc \
	52624d3fc8d51234ff4f4d4c31f302d2e031c736997dd9645e96e89b4fcd00db \
	b96f4350b35ff3bfc987ce97828e22bd7136100323752c2ac68c537580bd35d6 \
	8275e22dc5e2894c5bb73bcf25c989c475b6a7e28a6da13b5aa0741e5eb75722 \
	763aae44f04840d6c151baa068bb83e874f9d32aea0023fc6a7eb8c89f975276 \
	1f98e136913a924e6338c6b7bfc3fb925146f00efd3c77e1192f4e25c0be26bb \
	c1eabc572c27fdd6ba5944526d563907fc9c250ab7a9cc6696685ca16b630f9c \
	c5c97d92266088cb0ced1eda556faecc5c27c1e241ce3bc1ba6020431c7e9875 \
	0c7bb22301b8203531a7e8f098e8a719fd7f29d7de2cdf3c63730ecb792e9bbc \
	8d350d51d8f35583f6ba32f005fc9b9fc035c6f24186c5b1786b2f60a90a0f6f \
	2af09c087c917b7d1325c0b8a361c7ec3594779983034be0736acac841f8da79 \
	5a8d18f6c4a85c7828d3a9f87fe6d5a5d75b703d \
	'smmu_acceptance_sha=c5c97d92266088cb0ced1eda556faecc5c27c1e241ce3bc1ba6020431c7e9875' \
	'check-adreno-smmu-driver-override-state.sh' \
	'EXACT_PLATFORM_DEVICE_AT_MOST_ONCE' \
	'3da0000.iommu' \
	733a2ba85e192e982883de1afee04e9fee0d137d737a611ad0914f185885fbbc \
	13224d8ac0a6eafddac6554a77d08d381312ead2730268859b3a375b778b3364 \
	512ab814fdc17d25ff8ee555b4b515059695ab95052be85c76a10d26470d7315 \
	'CONFIG_DRM_MSM=m' \
	'DRM_MSM_KMS' \
	'qcom/sm8350/a660_zap.mbn' \
	'/soc@0/clock-controller@3d90000' \
	'/soc@0/iommu@3da0000' \
	'/soc@0/gpu@3d00000' \
	'/soc@0/gmu@3d6a000' \
	'a660_sqe[.]fw|a660_gmu[.]bin|a660_zap[.]mbn' \
	'Algorithm:' \
	'verify_image'
do
	grep -Fq "$contract" "$verifier" || {
		echo "FAIL A660 registration bundle verifier omits: $contract" >&2
		exit 1
	}
done

if grep -Eq 'fastboot|dd[[:space:]].*of=/dev/|mount[[:space:]].*/dev/' \
	"$verifier"
then
	echo 'FAIL A660 registration bundle verifier controls a device or storage' >&2
	exit 1
fi

if "$verifier" /nonexistent /nonexistent /nonexistent /nonexistent \
	0000000000000000000000000000000000000000000000000000000000000000 \
	/nonexistent /nonexistent \
	0000000000000000000000000000000000000000000000000000000000000000 \
	/nonexistent /nonexistent /nonexistent /nonexistent /nonexistent \
	0000000000000000000000000000000000000000000000000000000000000000 \
	>/dev/null 2>&1
then
	echo 'FAIL A660 registration bundle verifier accepted wrong manifests' >&2
	exit 1
fi

if [ -n "${ARTIFACT_DIR:-}" ] || [ -n "${MKBOOTIMG_DIR:-}" ] ||
	[ -n "${AVBTOOL:-}" ] || [ -n "${BASE_ARTIFACT_DIR:-}" ] ||
	[ -n "${SOURCE_DIR:-}" ] || [ -n "${FIRMWARE_ROOT:-}" ] ||
	[ -n "${REGISTRATION_BUILD_DIR:-}" ] ||
	[ -n "${V15_ARTIFACT_DIR:-}" ]
then
	[ -d "${ARTIFACT_DIR:-}" ]
	[ -d "${MKBOOTIMG_DIR:-}" ]
	[ -f "${AVBTOOL:-}" ]
	[ -d "${BASE_ARTIFACT_DIR:-}" ]
	[ -d "${SOURCE_DIR:-}" ]
	[ -d "${FIRMWARE_ROOT:-}" ]
	[ -d "${REGISTRATION_BUILD_DIR:-}" ]
	[ -d "${V15_ARTIFACT_DIR:-}" ]
	"$verifier" "$ARTIFACT_DIR" "$MKBOOTIMG_DIR" "$AVBTOOL" \
		"$ARTIFACT_DIR/SHA256SUMS" \
		c4b9a2ec5afdd73a555031425a5eaedf5ab97a36a69eeefdcfede279ad7ffcd0 \
		"$BASE_ARTIFACT_DIR" "$BASE_ARTIFACT_DIR/SHA256SUMS" \
		e433a95b3cfeeeabd8dd97b4321da3082f934e5bbbca5cb0bfd4f71074355d73 \
		"$SOURCE_DIR" "$FIRMWARE_ROOT" "$REGISTRATION_BUILD_DIR" \
		"$V15_ARTIFACT_DIR" "$V15_ARTIFACT_DIR/SHA256SUMS" \
		a739f975f87ac30918625178007b4cd7302449ae96c26e5c42185e9e1a0425cc
fi

echo 'PASS A660 registration bundle contract pins predecessor, source, DT, modules, wrappers, package, and source lock'
