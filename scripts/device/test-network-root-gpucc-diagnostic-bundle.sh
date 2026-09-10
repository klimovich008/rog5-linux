#!/bin/sh
set -eu

repo=$(CDPATH= cd -- "$(dirname "$0")/../.." && pwd)
verifier=$repo/scripts/device/verify-network-root-gpucc-diagnostic-bundle.sh
base=$repo/scripts/device/verify-network-root-bundle.sh

[ -x "$verifier" ] && [ -x "$base" ]
sh -n "$verifier" "$base"
for contract in \
	'verify-network-root-bundle.sh' \
	'"$expected_sums" okay' \
	'qcom,sm8350-gpucc' \
	'/soc@0/gpu@3d00000' \
	'/soc@0/gmu@3d6a000' \
	'/soc@0/iommu@3da0000' \
	'/soc@0/remoteproc@3000000' \
	'CONFIG_SM_GPUCC_8350=m' \
	'CONFIG_DRM_MSM=y' \
	'CONFIG_ARM_SMMU=y' \
	'probe_trace:Emit progress notices for attended SM8350 GPUCC diagnostics (bool)' \
	'5f7018e53eb576579fe8d199171ae6e17c4e9d31ad099a330d21e050c0ad4454' \
	'GPUCC module hash is not the reviewed diagnostic build' \
	'73b419cc0b2adee00a0d2da8caa0d1292c629804b91ca629a973438653ad6717' \
	'gpucc-sm8350[.]ko|a660_sqe[.]fw|a660_gmu[.]bin|a660_zap[.]mbn'
do
	grep -Fq "$contract" "$verifier" || {
		echo "FAIL GPUCC bundle verifier omits: $contract" >&2
		exit 1
	}
done

if grep -Eq 'fastboot[[:space:]]+flash|dd[[:space:]].*of=/dev/|mount[[:space:]].*/dev/' \
	"$verifier"; then
	echo 'FAIL GPUCC bundle verifier contains a persistent-write path' >&2
	exit 1
fi

echo 'PASS GPUCC bundle contract pins the external module and excludes every consumer and firmware payload'
