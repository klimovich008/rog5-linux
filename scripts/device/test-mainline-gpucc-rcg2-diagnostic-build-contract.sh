#!/bin/sh
set -eu

repo=$(CDPATH= cd -- "$(dirname "$0")/../.." && pwd)
verifier=$repo/scripts/device/verify-mainline-gpucc-rcg2-diagnostic-build.sh

[ -x "$verifier" ]
sh -n "$verifier"

for contract in \
	'verify-mainline-network-root-build.sh' \
	'verify-rcg2-parent-read-trace-patch.sh' \
	'test-rcg2-parent-read-trace-budget.sh' \
	'6e40861cc51c067f9989c4513003e8fbd046c22f' \
	'49ef6cb95768496b8f926b11e428ea224406464e' \
	'ac7975bf5f4cb2791f45a2fe8b5b811c7e60fd4692f8aff4cd71a2f2150fa3c6' \
	'5759d3d15ca60f260aa89731aa78c94acd5d183eca67dc24c3723f8877f213e3' \
	'9350e5a010c0af11fe4bde48527d056701c83a0072be4ad29cce2565a75204a1' \
	'008919805fa413eefe4bb42675bcf6467a0a5bcef87158af05deec5e4cf75365' \
	'rog5_rcg2_parent_trace' \
	'ROG5 RCG2 diagnostic: phase=%s clock=%s ret=%d' \
	'parent-read-begin' \
	'parent-read-complete' \
	'disp_cc_mdss_pclk0_clk_src' \
	'gpucc-sm8350[.]ko'
do
	grep -Fq "$contract" "$verifier" || {
		echo "FAIL v14 build verifier omits: $contract" >&2
		exit 1
	}
done

if grep -Eq 'fastboot[[:space:]]+flash|dd[[:space:]].*of=/dev/|mount[[:space:]].*/dev/' \
	"$verifier"
then
	echo 'FAIL v14 build verifier contains a persistent-write path' >&2
	exit 1
fi

echo 'PASS v14 build-verifier contract pins source, binaries, ABI, markers, timing, and no persistent-write path'
