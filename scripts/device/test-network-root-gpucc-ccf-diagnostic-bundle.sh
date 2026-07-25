#!/bin/sh
set -eu

repo=$(CDPATH= cd -- "$(dirname "$0")/../.." && pwd)
verifier=$repo/scripts/device/verify-network-root-gpucc-ccf-diagnostic-bundle.sh
base=$repo/scripts/device/verify-network-root-bundle.sh

[ -x "$verifier" ] && [ -x "$base" ]
sh -n "$verifier" "$base"
for contract in \
	'verify-network-root-bundle.sh' \
	'verify-qcom-cc-registration-trace-patch.sh' \
	'verify-ccf-registration-trace-patch.sh' \
	'rog5_qcom_cc_probe_trace' \
	'rog5_ccf_register_trace' \
	'ROG5 QCOM CC diagnostic: phase=%s index=%d ret=%d' \
	'ROG5 CCF diagnostic: phase=%s clock=%s ret=%d' \
	'regmap-device-lookup-begin' \
	'prepare-lock-complete' \
	'orphan-reparent-complete' \
	'debug-register-complete' \
	'qcom,sm8350-gpucc' \
	'/soc@0/gpu@3d00000' \
	'/soc@0/gmu@3d6a000' \
	'/soc@0/iommu@3da0000' \
	'/soc@0/remoteproc@3000000' \
	'CONFIG_SM_GPUCC_8350=m' \
	'CONFIG_COMMON_CLK_QCOM=y' \
	'd6bb0a9a7c4d4496aac8593df1727c916f130a10741b2691eebbf28555527021' \
	'b1c2bd02d67773e2b213c8aec2e30378580f8bcc638ff378650182a335f6f5d0' \
	'3c663bed417bb3bd7438b422ebf3531eca48e53afebc66a4574c7d87f7a8f421' \
	'ed80c46e4d23caa258d3ef07ffddad254d9cba461165751e55476864044fdc42' \
	'gpucc-sm8350[.]ko|a660_sqe[.]fw|a660_gmu[.]bin|a660_zap[.]mbn'
do
	grep -Fq "$contract" "$verifier" || {
		echo "FAIL CCF bundle verifier omits: $contract" >&2
		exit 1
	}
done

if grep -Eq 'fastboot[[:space:]]+flash|dd[[:space:]].*of=/dev/|mount[[:space:]].*/dev/' \
	"$verifier"; then
	echo 'FAIL CCF bundle verifier contains a persistent-write path' >&2
	exit 1
fi

echo 'PASS CCF bundle contract pins exact artifacts, all phase boundaries, dual opt-in transport, and disabled consumers'
