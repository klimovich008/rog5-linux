#!/bin/sh
set -eu

repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)
verifier=$repo/scripts/device/verify-network-root-adreno-smmu-bundle.sh
manifest=$repo/manifests/artifacts.tsv
boot_name=artifacts/network-root-v18-adreno-smmu-diagnostic/boot-5.4.210-network-root-stage.avb.img

[ -x "$verifier" ] || {
	echo 'FAIL missing executable Adreno SMMU bundle verifier' >&2
	exit 1
}
sh -n "$verifier"

manifest_entry=$(awk -F '\t' -v name="$boot_name" \
	'$1 == name { print $2 "\t" $3 "\t" $5 }' "$manifest")
[ "$manifest_entry" = "$(printf '%s\t%s\t%s' \
	100663296 \
	37e607795794713472d6944cfbc691211365184a2b674118a17c5d9763b893bf \
	no)" ] || {
	echo 'FAIL v18 temporary-boot image is not pinned for Linux preflight' >&2
	exit 1
}

for contract in \
	'verify-network-root-gpucc-runtime-pm-candidate-bundle.sh' \
	'verify-adreno-smmu-dependency-contract.sh' \
	'test-adreno-smmu-dependency-contract.sh' \
	'verify-adreno-smmu-platform-reprobe-contract.sh' \
	'test-adreno-smmu-platform-reprobe-contract.sh' \
	'check-adreno-smmu-driver-override-state.sh' \
	'test-adreno-smmu-driver-override-state.sh' \
	'test-adreno-smmu-diagnostic-candidate-dtb.sh' \
	'test-adreno-smmu-kexec-stage-initramfs.sh' \
	'test-adreno-smmu-asus-kexec-stage-build-contract.sh' \
	'test-network-root-adreno-smmu-baseline.sh' \
	'test-probe-network-root-adreno-smmu.sh' \
	'test-run-network-root-adreno-smmu-gate.sh' \
	'sm8350-asus-rog-phone5-adreno-smmu-diagnostic.dtso' \
	'build-adreno-smmu-diagnostic-candidate-dtb.sh' \
	'build-adreno-smmu-kexec-stage-initramfs.sh' \
	'build-adreno-smmu-asus-kexec-stage.sh' \
	'check-network-root-adreno-smmu-baseline.sh' \
	'probe-network-root-adreno-smmu.sh' \
	'run-network-root-adreno-smmu-gate.sh' \
	'd9ac316489f4258d389d6298659d5e9c22183400' \
	'c796deb1cc54e942f8bb46a2c76a7199e19e5c92' \
	'e433a95b3cfeeeabd8dd97b4321da3082f934e5bbbca5cb0bfd4f71074355d73' \
	'd30df38804750ded48607135a7d23d4f95e0947c49b68395a8f6818c4a27c54b' \
	'9350e5a010c0af11fe4bde48527d056701c83a0072be4ad29cce2565a75204a1' \
	'9ac07151490fe4844462945014e0a74674b43841e4cea1cfc4c3560231067d2a' \
	'da471966073cfb26581b4a5224218904162c5925155b0aa8c24a2b3e4ad0526f' \
	'85f764dd206afd3a2b652c7119eb266f62d687a02b1c32a5d303a51d012157b4' \
	'9b953088c3da1a757f07b219572cd3409dc8bba3698207833259822ef8bc0aac' \
	'ce730ff01f76b455a751c9f5d7204e722cc62ee56e77dcd632fd9aaa2d692613' \
	'37e607795794713472d6944cfbc691211365184a2b674118a17c5d9763b893bf' \
	'94ae43da4033daec9e6d80cdb0b0c3d0ff9436e6e873241ac97cf7884c86eff4' \
	'9dfdd5b553ff3569d5a3177ca667b92d38f7e5ee51e3775df9565f9f5853d833' \
	'884dfcd287dd892ec0698bedaa4475045967459282811da640e48f5f7d503e45' \
	'5348d98000865dd52a47ac5eacd4d04d16d2a92da719776e79971a2b040e2703' \
	'c1967f53f66da20c515d32ca3242bd6f365b31f2678f7125bf71cc16ed56a258' \
	'68ad17f3670b7fcedbfa70e8cab1b2044dff1e7525697efc953527fec2825fbe' \
	'314241c733f99bf8b45e64c173d78b1449b4da3fdad90a63500166376d2774eb' \
	'821937acef295d986caa4470166571b0d18cef2a2f9d1a730e1d0cb4cec70131' \
	'a2eb74c66815a38e2ad3476a80d1fe5ffbc5de2f32a50429a84f2d4c9f3f4e51' \
	'79540031bc10ab9c284bcf2db86e6bdbbcef11b8e8ee294094f43c63704e76c9' \
	'ae5d3f57d8411cd35b0c6265ec7a3f53b826cf1bb96ba651743c694b79c64c07' \
	'28d58f249027775b4bb1688a9421bdaccad38c94ce2a2ffd2d96b77992223c0c' \
	'7d15f897fd7e0beef6089bd20b3de0bce3fc68b6fdc5b832644ccf3bb583fb62' \
	'd82a08d85082df97a3015f67c668bc0648d2c11f56779b9086db4953d8b8f18b' \
	'CONFIG_ARM_SMMU=y' \
	'CONFIG_ARM_SMMU_QCOM=y' \
	'a660_sqe[.]fw|a660_gmu[.]bin|a660_zap[.]mbn' \
	'/soc@0/iommu@3da0000' \
	'/soc@0/gpu@3d00000' \
	'/soc@0/gmu@3d6a000'
do
	grep -Fq "$contract" "$verifier" || {
		echo "FAIL Adreno SMMU bundle verifier omits: $contract" >&2
		exit 1
	}
done

if grep -Eq 'fastboot[[:space:]]+flash|dd[[:space:]].*of=/dev/|mount[[:space:]].*/dev/' \
	"$verifier"
then
	echo 'FAIL Adreno SMMU bundle verifier contains a persistent-write path' >&2
	exit 1
fi

echo 'PASS v21 Adreno SMMU bundle contract pins source, NULL override state, target gates, artifacts, and offline safety'
