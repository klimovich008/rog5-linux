#!/bin/sh
set -eu

repo=$(CDPATH= cd -- "$(dirname "$0")/../.." && pwd)
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
	'test-network-root-adreno-smmu-baseline.sh' \
	'test-probe-network-root-adreno-smmu.sh' \
	'sm8350-asus-rog-phone5-adreno-smmu-diagnostic.dtso' \
	'build-adreno-smmu-diagnostic-candidate-dtb.sh' \
	'check-network-root-adreno-smmu-baseline.sh' \
	'probe-network-root-adreno-smmu.sh' \
	'd9ac316489f4258d389d6298659d5e9c22183400' \
	'c796deb1cc54e942f8bb46a2c76a7199e19e5c92' \
	'd30df38804750ded48607135a7d23d4f95e0947c49b68395a8f6818c4a27c54b' \
	'9350e5a010c0af11fe4bde48527d056701c83a0072be4ad29cce2565a75204a1' \
	'9ac07151490fe4844462945014e0a74674b43841e4cea1cfc4c3560231067d2a' \
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
