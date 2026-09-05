#!/bin/sh
set -eu

baseline_out=${1:?usage: build-a660-ucode-allocation-v6-runtime.sh BASELINE_OUT PROBE_OUT}
probe_out=${2:?missing probe output}
repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)
baseline_v5=$repo/scripts/device/check-network-root-a660-ucode-allocation-baseline.sh
probe_v5=$repo/scripts/device/probe-network-root-a660-ucode-allocation.sh
baseline_patch=$repo/patches/runtime/a660-ucode-allocation-v6-baseline.patch
probe_patch=$repo/patches/runtime/a660-ucode-allocation-v6-probe.patch

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

for command in chmod cp cut dirname patch sha256sum; do
	command -v "$command" >/dev/null || fail "missing command: $command"
done
[ "$baseline_out" != "$probe_out" ] ||
	fail 'baseline and probe output paths alias'
[ -d "$(dirname "$baseline_out")" ] && [ -d "$(dirname "$probe_out")" ] ||
	fail 'output parent directory is absent'
[ ! -e "$baseline_out" ] && [ ! -e "$probe_out" ] ||
	fail 'runtime output already exists'

check_hash "$baseline_v5" \
	4f2e50fd492c9fff06198396c1fd80fa877b1447f18920d9895ad82c4034e041 \
	'accepted v5 baseline'
check_hash "$probe_v5" \
	63adc85bdd3b4f5b08130722d30615fad1a439eb3aa2a43a4b161e826c36c3ef \
	'accepted v5 probe'
check_hash "$baseline_patch" \
	02a61e41b20ae9974fa50f7bd602b4ebc4665d66c435a90a0edbfb81cf3ca5f8 \
	'v6 baseline patch'
check_hash "$probe_patch" \
	f6458d465873a6d69c84f2bd12ae12bf482f342e6abd006bf10f3e1b898f2812 \
	'v6 probe patch'

cp "$baseline_v5" "$baseline_out"
cp "$probe_v5" "$probe_out"
patch --batch --fuzz=0 --no-backup-if-mismatch \
	"$baseline_out" "$baseline_patch" >/dev/null ||
	fail 'v6 baseline patch did not apply exactly'
patch --batch --fuzz=0 --no-backup-if-mismatch \
	"$probe_out" "$probe_patch" >/dev/null ||
	fail 'v6 probe patch did not apply exactly'
chmod 0755 "$baseline_out" "$probe_out"
sh -n "$baseline_out"
sh -n "$probe_out"

check_hash "$baseline_out" \
	5ad24829bd347fcc22239d761029f3c0f8064efa1b16e9f01b6cf745902df854 \
	'generated v6 baseline'
check_hash "$probe_out" \
	b90e33524da2558659a733c48d5670d2136208a9186d5abb3ecd79f1e28f2725 \
	'generated v6 probe'

echo 'PASS built exact A660 ucode-allocation v6 runtime from immutable v5 evidence plus two pinned zero-fuzz patches'
