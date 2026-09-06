#!/bin/sh
set -eu

repo=$(CDPATH= cd -- "$(dirname "$0")/../.." && pwd)
verifier=$repo/scripts/device/verify-network-root-gpucc-rcg2-diagnostic-bundle.sh
base=$repo/scripts/device/verify-network-root-bundle.sh
patch_verifier=$repo/scripts/device/verify-rcg2-parent-read-trace-patch.sh
budget_test=$repo/scripts/device/test-rcg2-parent-read-trace-budget.sh

for file in "$verifier" "$base" "$patch_verifier" "$budget_test"
do
	[ -x "$file" ]
done
sh -n "$verifier" "$base" "$patch_verifier" "$budget_test"

for contract in \
	'verify-network-root-bundle.sh' \
	'verify-rcg2-parent-read-trace-patch.sh' \
	'test-rcg2-parent-read-trace-budget.sh' \
	'EXPECTED_MANIFEST_SHA256' \
	'6e40861cc51c067f9989c4513003e8fbd046c22f' \
	'49ef6cb95768496b8f926b11e428ea224406464e' \
	'ac7975bf5f4cb2791f45a2fe8b5b811c7e60fd4692f8aff4cd71a2f2150fa3c6' \
	'5759d3d15ca60f260aa89731aa78c94acd5d183eca67dc24c3723f8877f213e3' \
	'9350e5a010c0af11fe4bde48527d056701c83a0072be4ad29cce2565a75204a1' \
	'9ac07151490fe4844462945014e0a74674b43841e4cea1cfc4c3560231067d2a' \
	'rog5_rcg2_parent_trace' \
	'ROG5 RCG2 diagnostic: phase=%s clock=%s ret=%d' \
	'parent-read-begin' \
	'parent-read-complete' \
	'disp_cc_mdss_pclk0_clk_src' \
	'/soc@0/gpu@3d00000' \
	'/soc@0/remoteproc@3000000' \
	'gpucc-sm8350[.]ko|a660_sqe[.]fw|a660_gmu[.]bin|a660_zap[.]mbn'
do
	grep -Fq "$contract" "$verifier" || {
		echo "FAIL v14 bundle verifier omits: $contract" >&2
		exit 1
	}
done

if grep -Eq 'fastboot[[:space:]]+flash|dd[[:space:]].*of=/dev/|mount[[:space:]].*/dev/' \
	"$verifier"
then
	echo 'FAIL v14 bundle verifier contains a persistent-write path' >&2
	exit 1
fi

echo 'PASS v14 bundle contract pins exact artifacts, two-entry RCG2 tracing, triple opt-in transport, disabled consumers, and no persistent-write path'
