#!/bin/sh
# shellcheck disable=SC2016
set -eu

repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)
builder=$repo/scripts/device/build-a660-ucode-allocation-v6-runtime.sh
verifier=$repo/scripts/device/verify-a660-ucode-allocation-v6-runtime-sources.sh
baseline_patch=$repo/patches/runtime/a660-ucode-allocation-v6-baseline.patch
probe_patch=$repo/patches/runtime/a660-ucode-allocation-v6-probe.patch

for input in "$builder" "$verifier"; do
	[ -x "$input" ] || {
		echo "FAIL missing executable A660 v6 runtime tool: $input" >&2
		exit 1
	}
	sh -n "$input"
done
for input in "$baseline_patch" "$probe_patch"; do
	[ -f "$input" ] && [ ! -L "$input" ] || {
		echo "FAIL missing A660 v6 runtime patch: $input" >&2
		exit 1
	}
done

for contract in \
	4f2e50fd492c9fff06198396c1fd80fa877b1447f18920d9895ad82c4034e041 \
	63adc85bdd3b4f5b08130722d30615fad1a439eb3aa2a43a4b161e826c36c3ef \
	02a61e41b20ae9974fa50f7bd602b4ebc4665d66c435a90a0edbfb81cf3ca5f8 \
	f6458d465873a6d69c84f2bd12ae12bf482f342e6abd006bf10f3e1b898f2812 \
	5ad24829bd347fcc22239d761029f3c0f8064efa1b16e9f01b6cf745902df854 \
	b90e33524da2558659a733c48d5670d2136208a9186d5abb3ecd79f1e28f2725 \
	'patch --batch --fuzz=0 --no-backup-if-mismatch' \
	'msm_gem_kernel_new' \
	'msm_gem_kernel_put' \
	'logical_gets=4' \
	'logical_puts=4' \
	'gem_snapshot=equal' \
	'v6 retained the rejected public-wrapper oracle'
do
	grep -Fq "$contract" "$builder" "$verifier" "$baseline_patch" \
		"$probe_patch" || {
		echo "FAIL A660 v6 runtime path omits: $contract" >&2
		exit 1
	}
done

if grep -Eq \
	'(^|[;&|[:space:]])(fastboot|adb|ssh|scp)([[:space:]]|$)|dd[[:space:]].*of=/dev/|mount[[:space:]].*/dev/' \
	"$builder" "$verifier"
then
	echo 'FAIL A660 v6 runtime tooling controls a device or storage' >&2
	exit 1
fi

stage=$(mktemp -d)
trap 'rm -rf -- "$stage"' EXIT HUP INT TERM
install -d "$stage/a" "$stage/b" "$stage/mutations"
"$builder" "$stage/a/baseline" "$stage/a/probe" >/dev/null
"$builder" "$stage/b/baseline" "$stage/b/probe" >/dev/null
cmp "$stage/a/baseline" "$stage/b/baseline"
cmp "$stage/a/probe" "$stage/b/probe"
"$verifier" "$stage/a/baseline" "$stage/a/probe" >/dev/null
"$verifier" "$stage/b/baseline" "$stage/b/probe" >/dev/null

set +e
"$builder" "$stage/a/baseline" "$stage/a/probe" >/dev/null 2>&1
existing_output=$?
"$builder" "$stage/missing/baseline" "$stage/missing/probe" \
	>/dev/null 2>&1
missing_parent=$?
set -e
[ "$existing_output" -ne 0 ]
[ "$missing_parent" -ne 0 ]

mutation=0
for replacement in \
	"s/rog5_ucode_get_vaddr 1 'public CPU vmap wrapper'/rog5_ucode_get_vaddr 4 'public CPU vmap wrapper'/" \
	's/cmp "$state_dir\/gem.before" "$state_dir\/gem.after"/test -s "$state_dir\/gem.after"/' \
	"s/rog5_ucode_kernel_new 3 'kernel GEM new'/rog5_ucode_kernel_new 2 'kernel GEM new'/"
do
	mutation=$((mutation + 1))
	cp "$stage/a/probe" "$stage/mutations/probe.$mutation"
	sed -i "$replacement" "$stage/mutations/probe.$mutation"
	set +e
	"$verifier" "$stage/a/baseline" \
		"$stage/mutations/probe.$mutation" >/dev/null 2>&1
	result=$?
	set -e
	[ "$result" -ne 0 ] || {
		echo "FAIL v6 runtime verifier accepts mutation $mutation" >&2
		exit 1
	}
done

echo 'PASS A660 ucode-allocation v6 runtime is reproducibly generated and rejects wrapper-count, snapshot, and kernel-new mutations'
