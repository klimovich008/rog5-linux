#!/bin/sh
set -eu

repo=$(CDPATH= cd -- "$(dirname "$0")/../.." && pwd)
verifier=$repo/scripts/device/verify-network-root-gpucc-parent-diagnostic-bundle.sh
base=$repo/scripts/device/verify-network-root-bundle.sh
patch_verifier=$repo/scripts/device/verify-ccf-orphan-parent-trace-patch.sh
budget_test=$repo/scripts/device/test-ccf-orphan-parent-trace-budget.sh

for file in "$verifier" "$base" "$patch_verifier" "$budget_test"; do
	[ -x "$file" ]
done
sh -n "$verifier" "$base" "$patch_verifier" "$budget_test"

for contract in \
	'verify-network-root-bundle.sh' \
	'verify-ccf-orphan-parent-trace-patch.sh' \
	'test-ccf-orphan-parent-trace-budget.sh' \
	'ROG5 CCF diagnostic: phase=%s clock=%s ret=%d' \
	'orphan-scan-entry' \
	'orphan-parent-lookup-begin' \
	'orphan-parent-shape' \
	'orphan-runtime-state' \
	'orphan-get-parent-begin' \
	'orphan-get-parent-complete' \
	'orphan-parent-cache-begin' \
	'orphan-parent-cache-complete' \
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
	'f7c0a9d067db77f05a40a5bc242c1e14ac297ac5' \
	'adec6b40ce25145e3e18cd82a788aa458514017d' \
	'6531645c80d9e07e40baf7d8af8ba6732f5ddfc75a3255a6dd75c8c3b8f7b5b5' \
	'1c5c1bd3841c6fdc2f0ebc29fb19f43099e4d5e70d63d9a183cd9646f6c35c28' \
	'22d069c6d8bea928f5fac6ab3107bb007b2cb76fd95fc85541780cb5d315f199' \
	'574fefd282fbff6577c921a116a5485546e788ca338802b960b26b9ad9fc6d9c' \
	'4b332cb739dee1e4d3cb605f47fcf4dfae6978d25f70c329514b4093d1a14db7' \
	'rog5_qcom_cc_probe_trace' \
	'rog5_ccf_register_trace' \
	'/soc@0/gpu@3d00000' \
	'/soc@0/remoteproc@3000000' \
	'gpucc-sm8350[.]ko|a660_sqe[.]fw|a660_gmu[.]bin|a660_zap[.]mbn'
do
	grep -Fq "$contract" "$verifier" || {
		echo "FAIL parent bundle verifier omits: $contract" >&2
		exit 1
	}
done

if grep -Eq 'fastboot[[:space:]]+flash|dd[[:space:]].*of=/dev/|mount[[:space:]].*/dev/' \
	"$verifier"; then
	echo 'FAIL parent bundle verifier contains a persistent-write path' >&2
	exit 1
fi

echo 'PASS parent bundle contract pins exact artifacts, all bounded phases, dual opt-in transport, and disabled consumers'
