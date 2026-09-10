#!/bin/sh
set -eu

baseline_out=${1:?usage: build-a660-ucode-allocation-v7-runtime.sh BASELINE_OUT PROBE_OUT}
probe_out=${2:?missing probe output}
repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)
v6_builder=$repo/scripts/device/build-a660-ucode-allocation-v6-runtime.sh
baseline_patch=$repo/patches/runtime/a660-ucode-allocation-v7-baseline.patch
probe_patch=$repo/patches/runtime/a660-ucode-allocation-v7-probe.patch

fail() {
	echo "FAIL $*" >&2
	exit 1
}

check_hash() {
	file=$1
	expected=$2
	label=$3
	[ -f "$file" ] && [ ! -L "$file" ] && [ -r "$file" ] ||
		fail "$label is missing, linked, or unreadable"
	actual=$(sha256sum "$file" | cut -d ' ' -f 1)
	[ "$actual" = "$expected" ] ||
		fail "$label hash mismatch: expected $expected, got $actual"
}

for command in chmod cp cut dirname mktemp patch rm sha256sum; do
	command -v "$command" >/dev/null || fail "missing command: $command"
done
[ "$baseline_out" != "$probe_out" ] ||
	fail 'baseline and probe output paths alias'
[ -d "$(dirname "$baseline_out")" ] && [ -d "$(dirname "$probe_out")" ] ||
	fail 'output parent directory is absent'
[ ! -e "$baseline_out" ] && [ ! -e "$probe_out" ] ||
	fail 'runtime output already exists'

check_hash "$v6_builder" \
	b8a94596c02f2954024e90ef24d1ae524239b6f7406b1cfb9f0b8d2affa82b38 \
	'immutable v6 runtime builder'
check_hash "$baseline_patch" \
	6a2e3d5d5d54fc18cc6422052aeee25c9533f219bf2b6b2e5b14eace21d8aeb9 \
	'v7 baseline patch'
check_hash "$probe_patch" \
	605f88b8f34eed6018a97d063fb496212fe04cb11c029d02424060318336c9a5 \
	'v7 probe patch'

work=$(mktemp -d)
trap 'rm -rf -- "$work"' EXIT HUP INT TERM
"$v6_builder" "$work/baseline-v6" "$work/probe-v6" >/dev/null
check_hash "$work/baseline-v6" \
	5ad24829bd347fcc22239d761029f3c0f8064efa1b16e9f01b6cf745902df854 \
	'generated v6 baseline'
check_hash "$work/probe-v6" \
	b90e33524da2558659a733c48d5670d2136208a9186d5abb3ecd79f1e28f2725 \
	'generated v6 probe'

cp "$work/baseline-v6" "$baseline_out"
cp "$work/probe-v6" "$probe_out"
patch --batch --fuzz=0 --no-backup-if-mismatch \
	"$baseline_out" "$baseline_patch" >/dev/null ||
	fail 'v7 baseline patch did not apply exactly'
patch --batch --fuzz=0 --no-backup-if-mismatch \
	"$probe_out" "$probe_patch" >/dev/null ||
	fail 'v7 probe patch did not apply exactly'
chmod 0755 "$baseline_out" "$probe_out"
sh -n "$baseline_out"
sh -n "$probe_out"

check_hash "$baseline_out" \
	d8c2d697d20c213f3528d6a4cf99ca7d0243bf83222a34ff6f665ab22fc27386 \
	'generated v7 baseline'
check_hash "$probe_out" \
	01a681bdf9fc17b3c676797cafadc43338eee49f2a5e3b7c6789edc1c7056cf0 \
	'generated v7 probe'

echo 'PASS built exact A660 ucode-allocation v7 runtime from immutable v6 evidence plus two pinned zero-fuzz patches'
