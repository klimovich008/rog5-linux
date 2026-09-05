#!/bin/sh
set -eu

repo=$(CDPATH= cd -- "$(dirname "$0")/../.." && pwd)
verifier=$repo/scripts/device/verify-network-root-gpucc-common-diagnostic-bundle.sh
base=$repo/scripts/device/verify-network-root-bundle.sh

[ -x "$verifier" ] && [ -x "$base" ]
sh -n "$verifier" "$base"
for contract in \
	'verify-network-root-bundle.sh' \
	'verify-qcom-cc-registration-trace-patch.sh' \
	'rog5_qcom_cc_probe_trace' \
	'ROG5 QCOM CC diagnostic: phase=%s index=%d ret=%d' \
	'qcom,sm8350-gpucc' \
	'/soc@0/gpu@3d00000' \
	'/soc@0/gmu@3d6a000' \
	'/soc@0/iommu@3da0000' \
	'/soc@0/remoteproc@3000000' \
	'CONFIG_SM_GPUCC_8350=m' \
	'CONFIG_COMMON_CLK_QCOM=y' \
	'0ccb0059ec1960becb3676903aaccb623f105dbc8df08984cbd13a7d1ea6e73c' \
	'7c49c648c076326a6f008082f0d38e389bd8bb7c8a867ee0935d83e6a4195224' \
	'gpucc-sm8350[.]ko|a660_sqe[.]fw|a660_gmu[.]bin|a660_zap[.]mbn'
do
	grep -Fq "$contract" "$verifier" || {
		echo "FAIL common-clock bundle verifier omits: $contract" >&2
		exit 1
	}
done

if grep -Eq 'fastboot[[:space:]]+flash|dd[[:space:]].*of=/dev/|mount[[:space:]].*/dev/' \
	"$verifier"; then
	echo 'FAIL common-clock bundle verifier contains a persistent-write path' >&2
	exit 1
fi

echo 'PASS common-clock bundle contract pins built-in phases, matching module/BTF artifacts, opt-in transport, and disabled consumers'
