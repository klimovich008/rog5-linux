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
	'45916e12f97887e1f3b6c6d3e4137167465ef48d2479d0811444a8880be22643' \
	'9b175a6837b542713358f65d828ef2278209581c57db981174d83e74a06cd93e' \
	'cf08ada160359b7f193b6d4d0d8eb721a95788195432a488d383c1db498771db' \
	'c18df0160c6c91a0a38fcbe50b09cd9dfdf8598dd30b697e8e7044e50aa9b49a' \
	'220b40676269cf36c5159a8c5fcda99512bc910c56fb2bbd28b24f745b7cb985' \
	'129f5bcf18821bc3be105ae2c3473eb176bf718eb2a78d80b00d85172f6bdce5' \
	'ba2d81c3e7f3d4ffc1a873e235f7e35dab5ce56a6c90c0de011ce06a0bae6cfe' \
	'44b1e31e26cdfe90de626544129e7e0044ef1086108459ab2269f05894e577cd' \
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
