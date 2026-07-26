#!/bin/sh
set -eu

repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)
verifier=$repo/scripts/device/verify-network-root-adreno-smmu-bundle.sh

[ -x "$verifier" ] || {
	echo 'FAIL missing executable Adreno SMMU bundle verifier' >&2
	exit 1
}
sh -n "$verifier"

for contract in \
	'verify-network-root-gpucc-runtime-pm-candidate-bundle.sh' \
	'verify-adreno-smmu-dependency-contract.sh' \
	'test-adreno-smmu-dependency-contract.sh' \
	'test-adreno-smmu-diagnostic-candidate-dtb.sh' \
	'test-adreno-smmu-kexec-stage-initramfs.sh' \
	'test-adreno-smmu-asus-kexec-stage-build-contract.sh' \
	'test-network-root-adreno-smmu-baseline.sh' \
	'test-probe-network-root-adreno-smmu.sh' \
	'sm8350-asus-rog-phone5-adreno-smmu-diagnostic.dtso' \
	'build-adreno-smmu-diagnostic-candidate-dtb.sh' \
	'build-adreno-smmu-kexec-stage-initramfs.sh' \
	'build-adreno-smmu-asus-kexec-stage.sh' \
	'check-network-root-adreno-smmu-baseline.sh' \
	'probe-network-root-adreno-smmu.sh' \
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
	'2385fbed96a59362cfb7d34cf1970362fcf2937eb7a238aa6628158141b4a592' \
	'14ef5916fdecc6ac412f8f5f7deb8121eb7c668614e4bd5b7b91ac6df96597bb' \
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

echo 'PASS Adreno SMMU bundle contract pins source, DT, target gates, artifacts, and offline safety'
