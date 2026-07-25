#!/bin/sh
set -eu

repo=$(CDPATH= cd -- "$(dirname "$0")/../.." && pwd)
verifier=$repo/scripts/device/verify-network-root-gpucc-runtime-pm-candidate-bundle.sh
base=$repo/scripts/device/verify-network-root-bundle.sh
model=$repo/scripts/device/test-clk-orphan-runtime-pm-lock-model.py

for file in "$verifier" "$base" "$model"; do
	[ -x "$file" ]
done
sh -n "$verifier" "$base"

for contract in \
	'verify-network-root-bundle.sh' \
	'test-clk-orphan-runtime-pm-lock-model.py' \
	'EXPECTED_MANIFEST_SHA256' \
	'd9ac316489f4258d389d6298659d5e9c22183400' \
	'c796deb1cc54e942f8bb46a2c76a7199e19e5c92' \
	'a309fe55dc6221f4475c22beb43018dde0f2eb107fa60e84f8e43f28e17a4a25' \
	'd30df38804750ded48607135a7d23d4f95e0947c49b68395a8f6818c4a27c54b' \
	'9350e5a010c0af11fe4bde48527d056701c83a0072be4ad29cce2565a75204a1' \
	'9ac07151490fe4844462945014e0a74674b43841e4cea1cfc4c3560231067d2a' \
	'runtime-get-all-begin' \
	'runtime-put-all-complete' \
	'parent-read-begin' \
	'disp_cc_mdss_pclk0_clk_src' \
	'/soc@0/gpu@3d00000' \
	'/soc@0/remoteproc@3000000' \
	'gpucc-sm8350[.]ko|a660_sqe[.]fw|a660_gmu[.]bin|a660_zap[.]mbn'
do
	grep -Fq "$contract" "$verifier" || {
		echo "FAIL v15 bundle verifier omits: $contract" >&2
		exit 1
	}
done

if grep -Eq 'fastboot[[:space:]]+flash|dd[[:space:]].*of=/dev/|mount[[:space:]].*/dev/' \
	"$verifier"
then
	echo 'FAIL v15 bundle verifier contains a persistent-write path' >&2
	exit 1
fi

echo 'PASS v15 bundle contract pins exact artifacts, lock model, triple trace opt-in, disabled consumers, and no persistent-write path'
