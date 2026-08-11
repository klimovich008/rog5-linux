#!/usr/bin/env bash
set -euo pipefail

fail() {
	echo "FAIL $*" >&2
	exit 1
}

repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
builder=$repo/scripts/host/rebuild-headless-network-root-initramfs.sh
publisher=$repo/scripts/host/publish-noreplace.py
test_root=$(mktemp -d)
trap 'rm -rf -- "$test_root"' EXIT HUP INT TERM

[[ -f $builder && ! -L $builder && -x $builder ]] ||
	fail 'missing executable diagnostic-initramfs builder'
[[ -f $publisher && ! -L $publisher && -x $publisher ]] ||
	fail 'missing executable no-replace publisher'
bash -n "$builder"

for token in \
	'mode=${3:-normal}' \
	'diagnostic)' \
	'rog5-early-target-diagnostic-initramfs.cpio.gz' \
	'artifacts/early-target-diagnostic-v7' \
	'6014751' \
	'635e641c62f894d4bc150cd3fec9ae965f0f9a769ff7b856ad5ca2432530ed2b' \
	'rog5-early-target-diagnostic-initramfs-rebuild-v7' \
	'6a87ffa7bcbef1dcef9353d2ada3b34888f6bcb881fe38d417c3ae97e6767d01' \
	'build-early-target-diag.sh' \
	'rog5-early-target-diag.c' \
	'--pull=never' \
	'--network=none' \
	'--platform linux/arm64' \
	'two qualified early-target reporter builds differ' \
	'NETWORK_ROOT_DIAGNOSTIC_REPORTER="$reporter"' \
	'NETWORK_ROOT_DIAGNOSTIC_REPORTER="$reporter_a"' \
	'early_target_reporter_sha256=$reporter_sha' \
	'publish-noreplace.py' \
	'headless initramfs output publication collided' \
	'twin-verifier-reporter-and-twin-initramfs-builds' \
	'PASS reproduced exact early-target diagnostic initramfs'; do
	grep -Fq -- "$token" "$builder" ||
		fail "diagnostic-initramfs builder omits contract token: $token"
done

[[ $(grep -Fc 'build_reporter "$work/reporter-' "$builder") == 2 ]] ||
	fail 'diagnostic-initramfs builder does not build exactly two reporters'
reporter_function=$(
	sed -n '/^[[:space:]]*build_reporter() {/,/^[[:space:]]*}/p' "$builder"
)
grep -Fq -- '--network=none' <<<"$reporter_function" ||
	fail 'diagnostic reporter builder is not network-isolated'
grep -Fq -- '--pull=never' <<<"$reporter_function" ||
	fail 'diagnostic reporter builder permits an image pull'
[[ $(grep -Fc 'build_archive "$verifier_' "$builder") == 2 ]] ||
	fail 'diagnostic-initramfs builder does not build exactly two archives'

if "$builder" "$test_root/missing-base" "$test_root/output" invalid \
	>"$test_root/invalid.out" 2>"$test_root/invalid.err"; then
	fail 'diagnostic-initramfs builder accepted an unknown mode'
fi
grep -Fq 'mode must be normal or diagnostic' "$test_root/invalid.err" ||
	fail 'diagnostic-initramfs builder did not reject mode first'
[[ ! -e $test_root/output ]] ||
	fail 'invalid diagnostic mode created output state'

mkdir "$test_root/publication-source" "$test_root/publication-destination"
: >"$test_root/publication-source/source-marker"
if "$publisher" "$test_root/publication-source" \
	"$test_root/publication-destination" \
	>"$test_root/collision.out" 2>"$test_root/collision.err"; then
	fail 'no-replace publisher replaced a competing destination'
fi
[[ -f $test_root/publication-source/source-marker &&
	-d $test_root/publication-destination &&
	-z $(find "$test_root/publication-destination" -mindepth 1 \
		-maxdepth 1 -print -quit) ]] ||
	fail 'publication collision changed source or destination'
grep -Fq 'FAIL no-replace publication:' "$test_root/collision.err" ||
	fail 'publication collision did not fail explicitly'
mkdir "$test_root/publication-positive"
: >"$test_root/publication-positive/source-marker"
"$publisher" "$test_root/publication-positive" \
	"$test_root/publication-final"
[[ ! -e $test_root/publication-positive &&
	-f $test_root/publication-final/source-marker ]] ||
	fail 'no-replace publisher did not atomically publish an absent destination'

if grep -Eq \
	'\b(fastboot|adb|sudo|pkexec|ssh|scp|systemctl)\b|/dev/(sd|nvme|ufs)' \
	"$builder"; then
	fail 'diagnostic-initramfs builder contains live, privilege, or storage transport'
fi

echo 'PASS diagnostic initramfs is twin-built, exact-identity, rootless, and host-isolated'
