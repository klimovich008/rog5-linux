#!/bin/sh
set -eu

artifact_dir=${1:?usage: verify-network-root-adreno-smmu-bundle.sh ARTIFACT_DIR MKBOOTIMG_DIR AVBTOOL EXPECTED_SHA256 EXPECTED_MANIFEST_SHA256 BASE_ARTIFACT_DIR BASE_SHA256 BASE_MANIFEST_SHA256 SOURCE_DIR}
mkbootimg_dir=${2:?missing mkbootimg directory}
avbtool=${3:?missing avbtool}
expected_sums=${4:?missing candidate SHA-256 manifest}
expected_manifest=${5:?missing candidate manifest SHA-256}
base_artifact_dir=${6:?missing accepted v15 artifact directory}
base_sums=${7:?missing accepted v15 SHA-256 manifest}
base_manifest=${8:?missing accepted v15 manifest SHA-256}
source_dir=${9:?missing pinned Linux 7.1.4 source}
repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)

accepted_manifest=e433a95b3cfeeeabd8dd97b4321da3082f934e5bbbca5cb0bfd4f71074355d73
accepted_base_manifest=a739f975f87ac30918625178007b4cd7302449ae96c26e5c42185e9e1a0425cc
accepted_source=d9ac316489f4258d389d6298659d5e9c22183400
accepted_tree=c796deb1cc54e942f8bb46a2c76a7199e19e5c92
v15_verifier=$repo/scripts/device/verify-network-root-gpucc-runtime-pm-candidate-bundle.sh
base_verifier=$repo/scripts/device/verify-network-root-bundle.sh
base_test=$repo/scripts/device/test-network-root-bundle-contract.sh
dependency_verifier=$repo/scripts/device/verify-adreno-smmu-dependency-contract.sh
dependency_test=$repo/scripts/device/test-adreno-smmu-dependency-contract.sh
reprobe_verifier=$repo/scripts/device/verify-adreno-smmu-platform-reprobe-contract.sh
reprobe_test=$repo/scripts/device/test-adreno-smmu-platform-reprobe-contract.sh
driver_override_check=$repo/scripts/device/check-adreno-smmu-driver-override-state.sh
driver_override_test=$repo/scripts/device/test-adreno-smmu-driver-override-state.sh
dt_builder=$repo/scripts/device/build-adreno-smmu-diagnostic-candidate-dtb.sh
dt_test=$repo/scripts/device/test-adreno-smmu-diagnostic-candidate-dtb.sh
stage_builder=$repo/scripts/device/build-adreno-smmu-kexec-stage-initramfs.sh
stage_test=$repo/scripts/device/test-adreno-smmu-kexec-stage-initramfs.sh
wrapper_builder=$repo/scripts/device/build-adreno-smmu-asus-kexec-stage.sh
wrapper_test=$repo/scripts/device/test-adreno-smmu-asus-kexec-stage-build-contract.sh
baseline=$repo/scripts/device/check-network-root-adreno-smmu-baseline.sh
baseline_test=$repo/scripts/device/test-network-root-adreno-smmu-baseline.sh
probe=$repo/scripts/device/probe-network-root-adreno-smmu.sh
probe_test=$repo/scripts/device/test-probe-network-root-adreno-smmu.sh
gate=$repo/scripts/device/run-network-root-adreno-smmu-gate.sh
gate_test=$repo/scripts/device/test-run-network-root-adreno-smmu-gate.sh
bundle_test=$repo/scripts/device/test-network-root-adreno-smmu-bundle.sh
overlay=$repo/dts/qcom/sm8350-asus-rog-phone5-adreno-smmu-diagnostic.dtso
disarm=$repo/scripts/device/disarm-network-root-watchdog.sh

check_hash() {
	file=$1
	expected=$2
	[ -f "$file" ] && [ ! -L "$file" ]
	[ "$(sha256sum "$file" | cut -d ' ' -f 1)" = "$expected" ]
}

[ "$expected_manifest" = "$accepted_manifest" ]
[ "$base_manifest" = "$accepted_base_manifest" ]
[ "$(git -C "$source_dir" rev-parse HEAD)" = "$accepted_source" ]
[ "$(git -C "$source_dir" rev-parse 'HEAD^{tree}')" = "$accepted_tree" ]
check_hash "$expected_sums" "$accepted_manifest"
check_hash "$base_sums" "$accepted_base_manifest"
check_hash "$source_dir/drivers/base/platform.c" \
	c1967f53f66da20c515d32ca3242bd6f365b31f2678f7125bf71cc16ed56a258
check_hash "$source_dir/include/linux/device.h" \
	68ad17f3670b7fcedbfa70e8cab1b2044dff1e7525697efc953527fec2825fbe
check_hash "$source_dir/lib/vsprintf.c" \
	314241c733f99bf8b45e64c173d78b1449b4da3fdad90a63500166376d2774eb
check_hash "$source_dir/drivers/of/platform.c" \
	821937acef295d986caa4470166571b0d18cef2a2f9d1a730e1d0cb4cec70131
check_hash "$mkbootimg_dir/mkbootimg.py" \
	d99136f30bda966e8820c8ae53a82c659ca36e6d1aaf49a4cd63ae4795a6845a
check_hash "$mkbootimg_dir/unpack_bootimg.py" \
	7012fe91c4032446f23f3bd6f86fe1bc274517eb4e7aef923ed8396a5b619aef
check_hash "$avbtool" \
	6418646bb5bf3c57c3c702bfd1e157917e59f9ce25c3c81bcce79d85655e56ff

check_hash "$v15_verifier" \
	f6d173999e96e133f83ac0c043e45a13797b643df605863fd42176d20d89b8ea
check_hash "$base_verifier" \
	8433eb8dc2b3bf1e0e875bab5cd6ba6a6e43cbc890c3d77a050edfc687608558
check_hash "$base_test" \
	bfab340ce79b725a53c9a76c3dd60478af17297aeba7b41a90ddbb3626412732
check_hash "$overlay" \
	98fe535c6fc019b996835a333525c7b490c7f36e733d5dafeb99edf6e9b24c09
check_hash "$dependency_verifier" \
	d02d84c6c7f1d7569c76ea4d366feda3b5c1f73c66b0166080dbcb3e92cccdea
check_hash "$dependency_test" \
	ca497af7896341972ce9bc63ae77c9809a131628cb290734524ced6d369e7153
check_hash "$reprobe_verifier" \
	94ae43da4033daec9e6d80cdb0b0c3d0ff9436e6e873241ac97cf7884c86eff4
check_hash "$reprobe_test" \
	9dfdd5b553ff3569d5a3177ca667b92d38f7e5ee51e3775df9565f9f5853d833
check_hash "$driver_override_check" \
	884dfcd287dd892ec0698bedaa4475045967459282811da640e48f5f7d503e45
check_hash "$driver_override_test" \
	5348d98000865dd52a47ac5eacd4d04d16d2a92da719776e79971a2b040e2703
check_hash "$dt_builder" \
	16b0f34e2d03625e39036c5cb96879dbb6db24ce7f0ffa816611ee7d09322fa4
check_hash "$dt_test" \
	7cbdacf2fc5bacf8e4373c364aef9ce0ebf1846baa043ce413d825e2eacceb20
check_hash "$stage_builder" \
	efd5b79a620ac43f7bc29050186b3d217d2ce167b05cbf1568f7a1ec248c7464
check_hash "$stage_test" \
	eb5d14a5ff778d69bb32975fbd515738196330269c0011744b1f57a81fc63872
check_hash "$wrapper_builder" \
	ffcabd0e46eb18961d56e62d8d6c514db4d5efac0b62e042a74cb7016c526337
check_hash "$wrapper_test" \
	3d6ffbb9cdae7a24b1ade96eeeb281d63b725570bbbde65ad910e64acfab2d43
check_hash "$baseline" \
	a2eb74c66815a38e2ad3476a80d1fe5ffbc5de2f32a50429a84f2d4c9f3f4e51
check_hash "$baseline_test" \
	79540031bc10ab9c284bcf2db86e6bdbbcef11b8e8ee294094f43c63704e76c9
check_hash "$probe" \
	ae5d3f57d8411cd35b0c6265ec7a3f53b826cf1bb96ba651743c694b79c64c07
check_hash "$probe_test" \
	28d58f249027775b4bb1688a9421bdaccad38c94ce2a2ffd2d96b77992223c0c
check_hash "$gate" \
	7d15f897fd7e0beef6089bd20b3de0bce3fc68b6fdc5b832644ccf3bb583fb62
check_hash "$gate_test" \
	d82a08d85082df97a3015f67c668bc0648d2c11f56779b9086db4953d8b8f18b
check_hash "$disarm" \
	b126182b615831e6f39784e4a2657cc60096ff906c26f1458be7d9a0d3ea065a

"$v15_verifier" "$base_artifact_dir" "$mkbootimg_dir" "$avbtool" \
	"$base_sums" "$base_manifest" >/dev/null
"$dependency_verifier" "$source_dir" >/dev/null
SOURCE_DIR=$source_dir "$dependency_test" >/dev/null
"$reprobe_verifier" "$source_dir" \
	"$artifact_dir/config-7.1.4-network-root" >/dev/null
SOURCE_DIR=$source_dir \
	KERNEL_CONFIG=$artifact_dir/config-7.1.4-network-root \
	"$reprobe_test" >/dev/null
"$driver_override_test" >/dev/null
BASE_DTB=$base_artifact_dir/sm8350-asus-rog-phone5-recovery.dtb \
	"$dt_test" >/dev/null
BASE_STAGE=$base_artifact_dir/rog5-network-root-kexec-stage-initramfs.cpio.gz \
	CANDIDATE_DTB=$artifact_dir/sm8350-asus-rog-phone5-recovery.dtb \
	"$stage_test" >/dev/null
"$wrapper_test" >/dev/null
"$baseline_test" >/dev/null
"$probe_test" >/dev/null
"$gate_test" >/dev/null
"$base_test" >/dev/null

"$base_verifier" "$artifact_dir" "$mkbootimg_dir" "$avbtool" \
	"$expected_sums" okay okay >/dev/null

for file in \
	Image-7.1.4-network-root \
	Image.gz-7.1.4-network-root \
	config-7.1.4-network-root \
	modules-7.1.4-network-root.tar.gz \
	build-meta-7.1.4-network-root.txt \
	rog5-network-root-initramfs.cpio.gz \
	gpucc-sm8350.ko
do
	cmp "$artifact_dir/$file" "$base_artifact_dir/$file"
done

check_hash "$artifact_dir/Image-7.1.4-network-root" \
	d30df38804750ded48607135a7d23d4f95e0947c49b68395a8f6818c4a27c54b
check_hash "$artifact_dir/modules-7.1.4-network-root.tar.gz" \
	9350e5a010c0af11fe4bde48527d056701c83a0072be4ad29cce2565a75204a1
check_hash "$artifact_dir/gpucc-sm8350.ko" \
	9ac07151490fe4844462945014e0a74674b43841e4cea1cfc4c3560231067d2a
check_hash "$artifact_dir/sm8350-asus-rog-phone5-recovery.dtb" \
	da471966073cfb26581b4a5224218904162c5925155b0aa8c24a2b3e4ad0526f
check_hash "$artifact_dir/rog5-network-root-initramfs.cpio.gz" \
	4f3077d02c40b5d27ab602562534cacf11324554ae75b0246fd4429bced9bbac
check_hash "$artifact_dir/rog5-network-root-kexec-stage-initramfs.cpio.gz" \
	85f764dd206afd3a2b652c7119eb266f62d687a02b1c32a5d303a51d012157b4
check_hash "$artifact_dir/embedded-kexec-stage-initramfs.cpio.gz" \
	85f764dd206afd3a2b652c7119eb266f62d687a02b1c32a5d303a51d012157b4
check_hash "$artifact_dir/config-5.4.210-network-root-stage" \
	df28224e6e8d2dfc825ac49dc9f6bdeb12bbcdae2dff92cbbf14a8a94177578f
check_hash "$artifact_dir/Image-5.4.210-network-root-stage" \
	9b953088c3da1a757f07b219572cd3409dc8bba3698207833259822ef8bc0aac
check_hash "$artifact_dir/build-meta-5.4.210-network-root-stage.txt" \
	9378a4687f433aed63f3cc57f33772526fd186126e7c0825f8bdaf618bcb10cd
check_hash "$artifact_dir/boot-5.4.210-network-root-stage.raw.img" \
	ce730ff01f76b455a751c9f5d7204e722cc62ee56e77dcd632fd9aaa2d692613
check_hash "$artifact_dir/boot-5.4.210-network-root-stage.avb.img" \
	37e607795794713472d6944cfbc691211365184a2b674118a17c5d9763b893bf

config=$artifact_dir/config-7.1.4-network-root
for symbol in \
	CONFIG_COMMON_CLK_QCOM=y \
	CONFIG_QCOM_GDSC=y \
	CONFIG_SM_GPUCC_8350=m \
	CONFIG_ARM_SMMU=y \
	CONFIG_ARM_SMMU_QCOM=y \
	CONFIG_DRM_MSM=y
do
	grep -qx "$symbol" "$config"
done

dtb=$artifact_dir/sm8350-asus-rog-phone5-recovery.dtb
[ "$(fdtget -t s "$dtb" /soc@0/clock-controller@3d90000 status)" = okay ]
smmu=/soc@0/iommu@3da0000
[ "$(fdtget -t s "$dtb" "$smmu" status)" = okay ]
[ "$(fdtget -t s "$dtb" "$smmu" compatible)" = \
	'qcom,sm8350-smmu-500 qcom,adreno-smmu qcom,smmu-500 arm,mmu-500' ]
[ "$(fdtget -t s "$dtb" "$smmu" clock-names)" = \
	'bus iface ahb hlos1_vote_gpu_smmu cx_gmu hub_cx_int hub_aon' ]
[ "$(fdtget -t x "$dtb" "$smmu" clocks | wc -w)" -eq 14 ]
[ "$(fdtget -t x "$dtb" "$smmu" power-domains | wc -w)" -eq 2 ]
[ "$(fdtget -t x "$dtb" "$smmu" interrupts | wc -w)" -eq 36 ]
fdtget -p "$dtb" "$smmu" | grep -qx dma-coherent
for node in /soc@0/gpu@3d00000 /soc@0/gmu@3d6a000; do
	[ "$(fdtget -t s "$dtb" "$node" status)" = disabled ]
done

wrapper_meta=$artifact_dir/build-meta-5.4.210-network-root-stage.txt
grep -qx \
	'source_sha256=3bfe58a00bfdd3839f9b626c2d34f0cc6778945458f1eef93cbfdea90bf2e5a8' \
	"$wrapper_meta"
grep -qx 'kexec_file=0' "$wrapper_meta"
grep -qx \
	'initramfs_sha256=85f764dd206afd3a2b652c7119eb266f62d687a02b1c32a5d303a51d012157b4' \
	"$wrapper_meta"

stage=$(mktemp -d)
trap 'rm -rf "$stage"' EXIT INT TERM
mkdir -p "$stage/target" "$stage/staging"
gzip -dc "$artifact_dir/rog5-network-root-initramfs.cpio.gz" |
	(cd "$stage/target" && cpio -idm --quiet --no-absolute-filenames)
gzip -dc "$artifact_dir/rog5-network-root-kexec-stage-initramfs.cpio.gz" |
	(cd "$stage/staging" && cpio -idm --quiet --no-absolute-filenames)

payload=$stage/staging/opt/rog5-recovery
cmp "$payload/Image" "$artifact_dir/Image-7.1.4-network-root"
cmp "$payload/board.dtb" "$dtb"
cmp "$payload/initramfs.cpio.gz" \
	"$artifact_dir/rog5-network-root-initramfs.cpio.gz"
(cd "$payload" && sha256sum -c SHA256SUMS >/dev/null)

python3 - "$artifact_dir/Image-5.4.210-network-root-stage" \
	"$artifact_dir/rog5-network-root-kexec-stage-initramfs.cpio.gz" <<'PY'
import sys

image = open(sys.argv[1], "rb").read()
initramfs = open(sys.argv[2], "rb").read()
if image.count(initramfs) != 1:
    raise SystemExit("embedded candidate initramfs count is not one")
PY

firmware_pattern='a660_sqe[.]fw|a660_gmu[.]bin|a660_zap[.]mbn'
for root in "$stage/target" "$stage/staging"; do
	if find "$root" -type f -printf '%f\n' | grep -Eq "$firmware_pattern"; then
		echo 'FAIL A660 firmware exists in a candidate initramfs' >&2
		exit 1
	fi
	if find "$root" -type f -exec grep -Il 'BEGIN .*PRIVATE KEY' {} + |
		grep -q .
	then
		echo 'FAIL private key exists in a candidate initramfs' >&2
		exit 1
	fi
	if find "$root" -type f -name 'gpucc-sm8350.ko' | grep -q .; then
		echo 'FAIL external GPUCC diagnostic module is embedded' >&2
		exit 1
	fi
done
if tar -tzf "$artifact_dir/modules-7.1.4-network-root.tar.gz" |
	grep -Eq "$firmware_pattern"
then
	echo 'FAIL A660 firmware exists in the module archive' >&2
	exit 1
fi

"$bundle_test" >/dev/null
echo 'PASS exact v18 binary with v21 GPUCC plus exact-device Adreno SMMU control plane; NULL-override exact, consumer-disabled, firmware-free, zero-storage, reproducible, and offline-only'
