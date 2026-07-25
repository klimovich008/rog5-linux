#!/bin/sh
set -eu

repo=$(CDPATH= cd -- "$(dirname "$0")/../.." && pwd)
verifier=$repo/scripts/device/verify-network-root-gpucc-orphan-diagnostic-bundle.sh
base=$repo/scripts/device/verify-network-root-bundle.sh
patch_verifier=$repo/scripts/device/verify-ccf-orphan-reparent-trace-patch.sh
budget_test=$repo/scripts/device/test-ccf-orphan-reparent-trace-budget.sh

for file in "$verifier" "$base" "$patch_verifier" "$budget_test"; do
	[ -x "$file" ]
done
sh -n "$verifier" "$base" "$patch_verifier" "$budget_test"

for contract in \
	'verify-network-root-bundle.sh' \
	'verify-ccf-orphan-reparent-trace-patch.sh' \
	'test-ccf-orphan-reparent-trace-budget.sh' \
	'ROG5 CCF diagnostic: phase=%s clock=%s ret=%d' \
	'orphan-scan-entry' \
	'orphan-parent-lookup-begin' \
	'orphan-parent-lookup-complete' \
	'orphan-parent-resolved' \
	'orphan-set-parent-before-begin' \
	'orphan-set-parent-before-complete' \
	'orphan-set-parent-after-begin' \
	'orphan-set-parent-after-complete' \
	'orphan-accuracy-begin' \
	'orphan-accuracy-complete' \
	'orphan-rates-begin' \
	'orphan-rates-complete' \
	'orphan-req-rate-complete' \
	'orphan-scan-complete' \
	'040d5f9b7be022489079b2ea9cab20a04934d85f' \
	'bc026e783fe3b7f1f15cb0e3ac6ca914d4b45897da07db0f887565b1722172e6' \
	'49318395c5ed4850d492e4f29ea841885692bd96b6a5b0982925769282b687d9' \
	'2c246d8ceed3c37cc2afefa56710ac5bbca2bc1bce0ca0409a361f8f5923a2e8' \
	'79a7d3b7d81c28821dd5199cdbcfe9b2cea5b8bc59b6d6e983a61a15f05424ba' \
	'234f8ab909fd8804cf400a3aa1fb8a88e6633047b7680ba331ac308019a3ec04' \
	'rog5_qcom_cc_probe_trace' \
	'rog5_ccf_register_trace' \
	'/soc@0/gpu@3d00000' \
	'/soc@0/remoteproc@3000000' \
	'gpucc-sm8350[.]ko|a660_sqe[.]fw|a660_gmu[.]bin|a660_zap[.]mbn'
do
	grep -Fq "$contract" "$verifier" || {
		echo "FAIL orphan bundle verifier omits: $contract" >&2
		exit 1
	}
done

if grep -Eq 'fastboot[[:space:]]+flash|dd[[:space:]].*of=/dev/|mount[[:space:]].*/dev/' \
	"$verifier"; then
	echo 'FAIL orphan bundle verifier contains a persistent-write path' >&2
	exit 1
fi

echo 'PASS orphan bundle contract pins exact artifacts, all bounded phases, dual opt-in transport, and disabled consumers'
