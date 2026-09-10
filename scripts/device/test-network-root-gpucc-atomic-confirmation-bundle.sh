#!/bin/sh
set -eu

repo=$(CDPATH= cd -- "$(dirname "$0")/../.." && pwd)
verifier=$repo/scripts/device/verify-network-root-gpucc-atomic-confirmation-bundle.sh

[ -x "$verifier" ]
sh -n "$verifier"

for contract in \
	'verify-network-root-gpucc-runtime-pm-candidate-bundle.sh' \
	'verify-gpucc-trace-free-confirmation.sh' \
	'test-gpucc-trace-free-confirmation.sh' \
	'check-network-root-gpucc-confirmation-baseline.sh' \
	'test-network-root-gpucc-confirmation-baseline.sh' \
	'verify-network-root-gpucc-atomic-confirmation.py' \
	'test-network-root-gpucc-atomic-confirmation.sh' \
	'test-network-root-acm.py' \
	'recovery-linux.sh' \
	'a739f975f87ac30918625178007b4cd7302449ae96c26e5c42185e9e1a0425cc' \
	'105bc5f7ca91693b0ed42c70686162c93fe84a56c6a9643189e43a49c2759176' \
	'08aee76f4505d9e27dc435eac25d080584c175116f0ae3f6d93f36e520ef8e6d' \
	'2c4e95537bf796a942f9e73e2a5eb3db71abf8e5bf9aae1f0617ecb08e9290ca' \
	'435c84b7ed990aaa6f27b959977cebbc0fc978dad928063af5ed6a1644964bce' \
	'23311b66521a18fbb1645dfd7cb9ae91b7fdefa2df486c96882a94db44844095' \
	'cbbbce7149ea35c67cfefac6b312c86a88ecf81dc34b0f77d124d6d0007267a6' \
	'b745eabbfdd7a19d49f178b9100b6b12bc47e73f07eef26da6f965bd6c731a5b' \
	'7fbc01a2308ea258c51e2f88c01346bd8397dcb545f8f7cab7e13b6f23fba33e' \
	'confirm-gpucc' \
	'load-gpucc-confirmation' \
	'execute'
do
	grep -Fq "$contract" "$verifier" || {
		echo "FAIL v17 bundle verifier omits: $contract" >&2
		exit 1
	}
done

if grep -Eq 'fastboot[[:space:]]+flash|dd[[:space:]].*of=/dev/|mount[[:space:]].*/dev/' \
	"$verifier"
then
	echo 'FAIL v17 bundle verifier contains a persistent-write path' >&2
	exit 1
fi

echo 'PASS v17 bundle contract pins exact v15 artifacts, v16 target gates, and atomic transport'
