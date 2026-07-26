#!/bin/sh
set -eu

artifact_dir=${1:?usage: verify-network-root-a660-registration-bundle.sh ARTIFACT_DIR MKBOOTIMG_DIR AVBTOOL EXPECTED_SHA256 EXPECTED_MANIFEST_SHA256 BASE_ARTIFACT_DIR BASE_SHA256 BASE_MANIFEST_SHA256 SOURCE_DIR FIRMWARE_ROOT REGISTRATION_BUILD_DIR V15_ARTIFACT_DIR V15_SHA256 V15_MANIFEST_SHA256}
mkbootimg_dir=${2:?missing mkbootimg directory}
avbtool=${3:?missing avbtool}
expected_sums=${4:?missing candidate SHA-256 manifest}
expected_manifest=${5:?missing candidate manifest SHA-256}
base_artifact_dir=${6:?missing accepted v18 artifact directory}
base_sums=${7:?missing accepted v18 SHA-256 manifest}
base_manifest=${8:?missing accepted v18 manifest SHA-256}
source_dir=${9:?missing pinned Linux 7.1.4 source}
firmware_root=${10:?missing firmware root}
registration_build=${11:?missing accepted A660 registration build}
v15_artifact_dir=${12:?missing accepted v15 artifact directory}
v15_sums=${13:?missing accepted v15 SHA-256 manifest}
v15_manifest=${14:?missing accepted v15 manifest SHA-256}
repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)

accepted_manifest=c4b9a2ec5afdd73a555031425a5eaedf5ab97a36a69eeefdcfede279ad7ffcd0
accepted_base_manifest=e433a95b3cfeeeabd8dd97b4321da3082f934e5bbbca5cb0bfd4f71074355d73
accepted_v15_manifest=a739f975f87ac30918625178007b4cd7302449ae96c26e5c42185e9e1a0425cc
accepted_source=d9ac316489f4258d389d6298659d5e9c22183400
accepted_tree=c796deb1cc54e942f8bb46a2c76a7199e19e5c92
base_verifier=$repo/scripts/device/verify-network-root-adreno-smmu-bundle.sh
build_verifier=$repo/scripts/device/verify-mainline-a660-registration-build.sh
build_test=$repo/scripts/device/test-mainline-a660-registration-build-contract.sh
dt_test=$repo/scripts/device/test-a660-registration-candidate-dtb.sh
stage_test=$repo/scripts/device/test-a660-registration-kexec-stage-initramfs.sh
wrapper_test=$repo/scripts/device/test-a660-registration-asus-kexec-stage-build-contract.sh
probe_test=$repo/scripts/device/test-probe-network-root-a660-registration.sh
export_test=$repo/scripts/host/test-a660-registration-export.sh
acceptance_verifier=$repo/scripts/device/verify-adreno-smmu-v21-live-acceptance.sh
acceptance_test=$repo/scripts/device/test-adreno-smmu-v21-live-acceptance.sh
acceptance_report=$repo/test-results/2026-07-26-network-root-adreno-smmu-v21-live-accepted.md
acceptance_marker=$repo/manifests/acceptance/adreno-smmu-v21-live.accepted

check_hash() {
	file=$1
	expected=$2
	[ -f "$file" ] && [ ! -L "$file" ]
	[ "$(sha256sum "$file" | cut -d ' ' -f 1)" = "$expected" ]
}

check_manifest_hash() {
	file=$1
	expected=$(awk -v file="$file" '$2 == file { print $1 }' "$expected_sums")
	[ "$(printf '%s\n' "$expected" |
		awk 'NF { count++ } END { print count + 0 }')" -eq 1 ]
	check_hash "$artifact_dir/$file" "$expected"
}

[ "$expected_manifest" = "$accepted_manifest" ]
[ "$base_manifest" = "$accepted_base_manifest" ]
[ "$v15_manifest" = "$accepted_v15_manifest" ]
check_hash "$expected_sums" "$accepted_manifest"
check_hash "$base_sums" "$accepted_base_manifest"
check_hash "$v15_sums" "$accepted_v15_manifest"
[ "$(git -C "$source_dir" rev-parse HEAD)" = "$accepted_source" ]
[ "$(git -C "$source_dir" rev-parse 'HEAD^{tree}')" = "$accepted_tree" ]
check_hash "$mkbootimg_dir/mkbootimg.py" \
	d99136f30bda966e8820c8ae53a82c659ca36e6d1aaf49a4cd63ae4795a6845a
check_hash "$mkbootimg_dir/unpack_bootimg.py" \
	7012fe91c4032446f23f3bd6f86fe1bc274517eb4e7aef923ed8396a5b619aef
check_hash "$avbtool" \
	6418646bb5bf3c57c3c702bfd1e157917e59f9ce25c3c81bcce79d85655e56ff
check_hash "$acceptance_report" \
	0c7bb22301b8203531a7e8f098e8a719fd7f29d7de2cdf3c63730ecb792e9bbc
check_hash "$acceptance_marker" \
	c5c97d92266088cb0ced1eda556faecc5c27c1e241ce3bc1ba6020431c7e9875
"$acceptance_verifier" "$acceptance_report" "$acceptance_marker" >/dev/null
"$acceptance_test" >/dev/null

required_files='
Image-5.4.210-network-root-stage
config-5.4.210-network-root-stage
embedded-kexec-stage-initramfs.cpio.gz
build-meta-5.4.210-network-root-stage.txt
Image-7.1.4-network-root
Image.gz-7.1.4-network-root
config-7.1.4-network-root
modules-7.1.4-network-root.tar.gz
build-meta-7.1.4-network-root.txt
sm8350-asus-rog-phone5-recovery.dtb
rog5-network-root-initramfs.cpio.gz
rog5-network-root-kexec-stage-initramfs.cpio.gz
boot-5.4.210-network-root-stage.raw.img
boot-5.4.210-network-root-stage.avb.img
'
[ "$(awk 'NF { count++ } END { print count + 0 }' "$expected_sums")" -eq 14 ]
for file in $required_files; do
	check_manifest_hash "$file"
done

check_hash "$artifact_dir/Image-5.4.210-network-root-stage" \
	763aae44f04840d6c151baa068bb83e874f9d32aea0023fc6a7eb8c89f975276
check_hash "$artifact_dir/config-5.4.210-network-root-stage" \
	df28224e6e8d2dfc825ac49dc9f6bdeb12bbcdae2dff92cbbf14a8a94177578f
check_hash "$artifact_dir/embedded-kexec-stage-initramfs.cpio.gz" \
	8275e22dc5e2894c5bb73bcf25c989c475b6a7e28a6da13b5aa0741e5eb75722
check_hash "$artifact_dir/build-meta-5.4.210-network-root-stage.txt" \
	1dd98e43cd7aabbd46745033477744365b2cd925e9b788f7800517620785e513
check_hash "$artifact_dir/Image-7.1.4-network-root" \
	52624d3fc8d51234ff4f4d4c31f302d2e031c736997dd9645e96e89b4fcd00db
check_hash "$artifact_dir/Image.gz-7.1.4-network-root" \
	9d735cac93cf5720e885a4151e3eb8c1257aa52167dd40b439252adb31fbe307
check_hash "$artifact_dir/config-7.1.4-network-root" \
	d2f3a6f919c3e1abf3d10d99a77165e43de0fc4888fda338f0625bae57cb35e0
check_hash "$artifact_dir/modules-7.1.4-network-root.tar.gz" \
	e3cb1ef31b6c1c803bee98748660f92b3b192d460cb41d5d4691f9953a91a42b
check_hash "$artifact_dir/build-meta-7.1.4-network-root.txt" \
	6b7e0cd2d93b9671a11b19039e7df7426b86fea0b5e56dbd9267ebda1d6a5bfc
check_hash "$artifact_dir/sm8350-asus-rog-phone5-recovery.dtb" \
	b96f4350b35ff3bfc987ce97828e22bd7136100323752c2ac68c537580bd35d6
check_hash "$artifact_dir/rog5-network-root-initramfs.cpio.gz" \
	4f3077d02c40b5d27ab602562534cacf11324554ae75b0246fd4429bced9bbac
check_hash "$artifact_dir/rog5-network-root-kexec-stage-initramfs.cpio.gz" \
	8275e22dc5e2894c5bb73bcf25c989c475b6a7e28a6da13b5aa0741e5eb75722
check_hash "$artifact_dir/boot-5.4.210-network-root-stage.raw.img" \
	1f98e136913a924e6338c6b7bfc3fb925146f00efd3c77e1192f4e25c0be26bb
check_hash "$artifact_dir/boot-5.4.210-network-root-stage.avb.img" \
	c1eabc572c27fdd6ba5944526d563907fc9c250ab7a9cc6696685ca16b630f9c

"$base_verifier" "$base_artifact_dir" "$mkbootimg_dir" "$avbtool" \
	"$base_sums" "$base_manifest" "$v15_artifact_dir" "$v15_sums" \
	"$v15_manifest" "$source_dir" >/dev/null
"$build_verifier" "$registration_build" "$source_dir" "$firmware_root" \
	"$base_artifact_dir/config-7.1.4-network-root" >/dev/null
BUILD_DIR=$registration_build SOURCE_DIR=$source_dir \
	FIRMWARE_ROOT=$firmware_root \
	KERNEL_CONFIG=$base_artifact_dir/config-7.1.4-network-root \
	"$build_test" >/dev/null
BASE_DTB=$base_artifact_dir/sm8350-asus-rog-phone5-recovery.dtb \
	CANDIDATE_DTB=$artifact_dir/sm8350-asus-rog-phone5-recovery.dtb \
	"$dt_test" >/dev/null
BASE_STAGE=$base_artifact_dir/rog5-network-root-kexec-stage-initramfs.cpio.gz \
	IMAGE=$artifact_dir/Image-7.1.4-network-root \
	CANDIDATE_DTB=$artifact_dir/sm8350-asus-rog-phone5-recovery.dtb \
	"$stage_test" >/dev/null
"$wrapper_test" >/dev/null
BUILD_DIR=$registration_build "$probe_test" >/dev/null
"$export_test" >/dev/null

cmp "$artifact_dir/Image-7.1.4-network-root" \
	"$registration_build/arch/arm64/boot/Image"
cmp "$artifact_dir/Image.gz-7.1.4-network-root" \
	"$registration_build/arch/arm64/boot/Image.gz"
cmp "$artifact_dir/config-7.1.4-network-root" "$registration_build/.config"
cmp "$artifact_dir/modules-7.1.4-network-root.tar.gz" \
	"$registration_build/modules.tar.gz"
cmp "$artifact_dir/build-meta-7.1.4-network-root.txt" \
	"$registration_build/build-meta.txt"
cmp "$artifact_dir/rog5-network-root-initramfs.cpio.gz" \
	"$base_artifact_dir/rog5-network-root-initramfs.cpio.gz"

config=$artifact_dir/config-7.1.4-network-root
for symbol in \
	CONFIG_DRM_MSM=m \
	CONFIG_SM_GPUCC_8350=m \
	CONFIG_QCOM_MDT_LOADER=m \
	CONFIG_ARM_SMMU=y \
	CONFIG_ARM_SMMU_QCOM=y
do
	grep -qx "$symbol" "$config"
done
for symbol in DRM_MSM_KMS DRM_MSM_DPU SCSI SCSI_UFSHCD SCSI_UFS_QCOM \
	BLK_DEV_SD RPMB
do
	if grep -Eq "^CONFIG_$symbol=(y|m)$" "$config"; then
		echo "FAIL registration bundle enables CONFIG_$symbol" >&2
		exit 1
	fi
done

dtb=$artifact_dir/sm8350-asus-rog-phone5-recovery.dtb
for node in \
	/soc@0/clock-controller@3d90000 \
	/soc@0/iommu@3da0000 \
	/soc@0/gpu@3d00000 \
	/soc@0/gmu@3d6a000
do
	[ "$(fdtget -t s "$dtb" "$node" status)" = okay ]
done
[ "$(fdtget -t s "$dtb" \
	/soc@0/gpu@3d00000/zap-shader firmware-name)" = \
	qcom/sm8350/a660_zap.mbn ]
for node in \
	/soc@0/ufshc@1d84000 \
	/soc@0/phy@1d87000 \
	/soc@0/usb@a8f8800 \
	/reserved-memory/memory@9b800000
do
	[ "$(fdtget -t s "$dtb" "$node" status)" = disabled ]
done

wrapper_config=$artifact_dir/config-5.4.210-network-root-stage
wrapper_image=$artifact_dir/Image-5.4.210-network-root-stage
wrapper_meta=$artifact_dir/build-meta-5.4.210-network-root-stage.txt
staging_initramfs=$artifact_dir/rog5-network-root-kexec-stage-initramfs.cpio.gz
cmp "$artifact_dir/embedded-kexec-stage-initramfs.cpio.gz" \
	"$staging_initramfs"
grep -qx 'CONFIG_KEXEC=y' "$wrapper_config"
grep -qx '# CONFIG_KEXEC_FILE is not set' "$wrapper_config"
grep -qx \
	'CONFIG_INITRAMFS_SOURCE="/root/build/rog5-kexec-stage-initramfs.cpio.gz"' \
	"$wrapper_config"
grep -qx 'source_sha256=3bfe58a00bfdd3839f9b626c2d34f0cc6778945458f1eef93cbfdea90bf2e5a8' \
	"$wrapper_meta"
grep -qx 'kexec_file=0' "$wrapper_meta"
grep -qx \
	'initramfs_sha256=8275e22dc5e2894c5bb73bcf25c989c475b6a7e28a6da13b5aa0741e5eb75722' \
	"$wrapper_meta"
strings "$wrapper_image" |
	grep -q 'Linux version 5.4.210.*-qgki-perf-kexec-stage-builtin-recovery'
python3 - "$wrapper_image" "$staging_initramfs" <<'PY'
import sys

image = open(sys.argv[1], "rb").read()
initramfs = open(sys.argv[2], "rb").read()
if image.count(initramfs) != 1:
    raise SystemExit("embedded A660 registration initramfs count is not one")
PY

stage=$(mktemp -d)
trap 'rm -rf "$stage"' EXIT INT TERM
mkdir -p "$stage/staging" "$stage/target" "$stage/boot" "$stage/boot-args"
gzip -dc "$staging_initramfs" |
	(cd "$stage/staging" && cpio -idm --quiet --no-absolute-filenames)
gzip -dc "$artifact_dir/rog5-network-root-initramfs.cpio.gz" |
	(cd "$stage/target" && cpio -idm --quiet --no-absolute-filenames)
payload=$stage/staging/opt/rog5-recovery
cmp "$payload/Image" "$artifact_dir/Image-7.1.4-network-root"
cmp "$payload/board.dtb" "$dtb"
cmp "$payload/initramfs.cpio.gz" \
	"$artifact_dir/rog5-network-root-initramfs.cpio.gz"
(cd "$payload" && sha256sum -c SHA256SUMS >/dev/null)

firmware_pattern='a660_sqe[.]fw|a660_gmu[.]bin|a660_zap[.]mbn'
for root in "$stage/staging" "$stage/target"; do
	if find "$root" -type f -printf '%f\n' | grep -Eq "$firmware_pattern"; then
		echo 'FAIL A660 firmware exists in a registration initramfs' >&2
		exit 1
	fi
	if find "$root" -type f -exec grep -Il 'BEGIN .*PRIVATE KEY' {} + |
		grep -q .
	then
		echo 'FAIL private key exists in a registration initramfs' >&2
		exit 1
	fi
done
if find "$stage/staging" -type f -name '*.ko' | grep -q .; then
	echo 'FAIL registration staging initramfs embeds a module' >&2
	exit 1
fi
if tar -tzf "$artifact_dir/modules-7.1.4-network-root.tar.gz" |
	grep -Eq "$firmware_pattern"
then
	echo 'FAIL A660 firmware exists in the registration module archive' >&2
	exit 1
fi
grep -qx \
	'smmu_acceptance_sha=c5c97d92266088cb0ced1eda556faecc5c27c1e241ce3bc1ba6020431c7e9875' \
	"$repo/scripts/device/probe-network-root-a660-registration.sh"
if grep -Fq NOT_ACCEPTED \
	"$repo/scripts/device/probe-network-root-a660-registration.sh"
then
	echo 'FAIL A660 registration probe retains the pre-v21 source lock' >&2
	exit 1
fi

raw=$artifact_dir/boot-5.4.210-network-root-stage.raw.img
avb=$artifact_dir/boot-5.4.210-network-root-stage.avb.img
boot_info=$(python3 "$mkbootimg_dir/unpack_bootimg.py" \
	--boot_img "$raw" --out "$stage/boot")
printf '%s\n' "$boot_info" | grep -qx 'boot image header version: 3'
python3 "$mkbootimg_dir/unpack_bootimg.py" \
	--boot_img "$raw" --out "$stage/boot-args" \
	--format=mkbootimg --null >"$stage/boot.args"
tr '\000' '\n' <"$stage/boot.args" >"$stage/boot.args.lines"
[ "$(awk '$0 == "--header_version" { getline; print; exit }' \
	"$stage/boot.args.lines")" = 3 ]
command_line=$(awk '$0 == "--cmdline" { getline; print; exit }' \
	"$stage/boot.args.lines")
[ "$(printf '%s\n' "$command_line" | tr ' ' '\n' |
	grep -c '^rog5\.recovery_timeout=180$')" -eq 1 ]
if printf '%s\n' "$command_line" | tr ' ' '\n' |
	grep -q '^rog5\.netroot='
then
	echo 'FAIL Android staging command line enables network root' >&2
	exit 1
fi
cmp "$stage/boot/kernel" "$wrapper_image"
cmp "$stage/boot/ramdisk" "$staging_initramfs"
[ "$(stat -c %s "$avb")" -eq 100663296 ]
head -c "$(stat -c %s "$raw")" "$avb" | cmp - "$raw"
python3 "$avbtool" info_image --image "$avb" >"$stage/avb-info"
grep -q '^Algorithm:[[:space:]]*NONE$' "$stage/avb-info"
grep -q 'Partition Name:[[:space:]]*boot$' "$stage/avb-info"
ln -s "$(realpath "$avb")" "$stage/boot.img"
python3 "$avbtool" verify_image --image "$stage/boot.img" >/dev/null

echo 'PASS exact v21-accepted A660 registration bundle; four nodes, seven modules, zero firmware/storage/display, reproducible and offline-only'
