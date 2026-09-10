#!/bin/sh
set -eu

repo=$(CDPATH= cd -- "$(dirname "$0")/../.." && pwd)
verifier=$repo/scripts/device/verify-network-root-gpucc-confirmation-bundle.sh

[ -x "$verifier" ]
sh -n "$verifier"

for contract in \
	'verify-network-root-gpucc-runtime-pm-candidate-bundle.sh' \
	'verify-gpucc-trace-free-confirmation.sh' \
	'test-gpucc-trace-free-confirmation.sh' \
	'check-network-root-gpucc-confirmation-baseline.sh' \
	'test-network-root-gpucc-confirmation-baseline.sh' \
	'test-probe-mainline-coldplug-module.sh' \
	'test-network-root-acm.py' \
	'a739f975f87ac30918625178007b4cd7302449ae96c26e5c42185e9e1a0425cc' \
	'7fbc01a2308ea258c51e2f88c01346bd8397dcb545f8f7cab7e13b6f23fba33e' \
	'cd5cfabca51a4709e87e268ac93d3f37eb61e5c3100d1406bfdf46941834ec33' \
	'50ec8d394583951ab00e65c38686775031d0abadc6a3faf1730edda13eb7be94' \
	'cbbbce7149ea35c67cfefac6b312c86a88ecf81dc34b0f77d124d6d0007267a6' \
	'b745eabbfdd7a19d49f178b9100b6b12bc47e73f07eef26da6f965bd6c731a5b' \
	'load-gpucc-confirmation' \
	'load-gpucc-diagnostic' \
	'trace_expected_count=0' \
	'trace_expected_state=N' \
	'trace_prefix=$parameter=' \
	'probe_trace=1' \
	'ROG5_PROBE_TIMEOUT:-75' \
	'ROG5_PROBE_SETTLE:-30'
do
	grep -Fq "$contract" "$verifier" || {
		echo "FAIL v16 bundle verifier omits: $contract" >&2
		exit 1
	}
done

if grep -Eq 'fastboot[[:space:]]+flash|dd[[:space:]].*of=/dev/|mount[[:space:]].*/dev/' \
	"$verifier"
then
	echo 'FAIL v16 bundle verifier contains a persistent-write path' >&2
	exit 1
fi

echo 'PASS v16 bundle contract pins exact v15 artifacts, trace-free transport/probe sources, tests, and rollback'
