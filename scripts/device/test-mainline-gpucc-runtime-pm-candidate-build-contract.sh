#!/bin/sh
set -eu

repo=$(CDPATH= cd -- "$(dirname "$0")/../.." && pwd)
verifier=$repo/scripts/device/verify-mainline-gpucc-runtime-pm-candidate-build.sh

[ -x "$verifier" ]
sh -n "$verifier"

for contract in \
	'verify-mainline-network-root-build.sh' \
	'verify-clk-orphan-runtime-pm-patch.sh' \
	'test-clk-orphan-runtime-pm-lock-model.py' \
	'd9ac316489f4258d389d6298659d5e9c22183400' \
	'c796deb1cc54e942f8bb46a2c76a7199e19e5c92' \
	'a309fe55dc6221f4475c22beb43018dde0f2eb107fa60e84f8e43f28e17a4a25' \
	'd30df38804750ded48607135a7d23d4f95e0947c49b68395a8f6818c4a27c54b' \
	'9350e5a010c0af11fe4bde48527d056701c83a0072be4ad29cce2565a75204a1' \
	'008919805fa413eefe4bb42675bcf6467a0a5bcef87158af05deec5e4cf75365' \
	'96b4831bbaabe996c950a31907039e5374547069ec502ce08a8056b9a5bdf193' \
	'runtime-get-all-begin' \
	'runtime-put-all-complete' \
	'disp_cc_mdss_pclk0_clk_src' \
	'gpucc-sm8350[.]ko'
do
	grep -Fq "$contract" "$verifier" || {
		echo "FAIL v15 build verifier omits: $contract" >&2
		exit 1
	}
done

if grep -Eq 'fastboot[[:space:]]+flash|dd[[:space:]].*of=/dev/|mount[[:space:]].*/dev/' \
	"$verifier"
then
	echo 'FAIL v15 build verifier contains a persistent-write path' >&2
	exit 1
fi

echo 'PASS v15 build-verifier contract pins candidate source, binaries, ABI, lock model, markers, and no persistent-write path'
