#!/bin/sh
# shellcheck disable=SC2016
set -eu

repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)
builder=$repo/scripts/device/build-a660-ucode-allocation-v7-runtime.sh
verifier=$repo/scripts/device/verify-a660-ucode-allocation-v7-runtime-sources.sh
baseline_patch=$repo/patches/runtime/a660-ucode-allocation-v7-baseline.patch
probe_patch=$repo/patches/runtime/a660-ucode-allocation-v7-probe.patch

for input in "$builder" "$verifier"; do
	[ -x "$input" ] || {
		echo "FAIL missing executable A660 v7 runtime tool: $input" >&2
		exit 1
	}
	sh -n "$input"
done
for input in "$baseline_patch" "$probe_patch"; do
	[ -f "$input" ] && [ ! -L "$input" ] || {
		echo "FAIL missing A660 v7 runtime patch: $input" >&2
		exit 1
	}
done

[ "$(sha256sum "$baseline_patch" | cut -d ' ' -f 1)" = \
	6a2e3d5d5d54fc18cc6422052aeee25c9533f219bf2b6b2e5b14eace21d8aeb9 ]
[ "$(sha256sum "$probe_patch" | cut -d ' ' -f 1)" = \
	605f88b8f34eed6018a97d063fb496212fe04cb11c029d02424060318336c9a5 ]

for contract in \
	5ad24829bd347fcc22239d761029f3c0f8064efa1b16e9f01b6cf745902df854 \
	b90e33524da2558659a733c48d5670d2136208a9186d5abb3ecd79f1e28f2725 \
	6a2e3d5d5d54fc18cc6422052aeee25c9533f219bf2b6b2e5b14eace21d8aeb9 \
	605f88b8f34eed6018a97d063fb496212fe04cb11c029d02424060318336c9a5 \
	d8c2d697d20c213f3528d6a4cf99ca7d0243bf83222a34ff6f665ab22fc27386 \
	01a681bdf9fc17b3c676797cafadc43338eee49f2a5e3b7c6789edc1c7056cf0 \
	'patch --batch --fuzz=0 --no-backup-if-mismatch' \
	'size_policy=RAW_KERNEL_NEW_ENTRY_ARGUMENTS' \
	'object_size_policy=SOURCE_PINNED_PAGE_ALIGN' \
	'4\n4096\n43288\n' \
	'logical_gets=4' \
	'logical_puts=4' \
	'gem_snapshot=equal' \
	'v7 retained rejected v6 runtime state'
do
	grep -Fq "$contract" "$builder" "$verifier" "$baseline_patch" \
		"$probe_patch" || {
		echo "FAIL A660 v7 runtime path omits: $contract" >&2
		exit 1
	}
done

if grep -Eq \
	'(^|[;&|[:space:]])(fastboot|adb|ssh|scp)([[:space:]]|$)|dd[[:space:]].*of=/dev/|mount[[:space:]].*/dev/' \
	"$builder" "$verifier"
then
	echo 'FAIL A660 v7 runtime tooling controls a device or storage' >&2
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

expect_rejected() {
	name=$1
	mutated_baseline=$2
	mutated_probe=$3
	if ALLOW_UNPINNED_A660_UCODE_V7_RUNTIME=1 \
		"$verifier" "$mutated_baseline" "$mutated_probe" \
		>"$stage/mutations/$name.log" 2>&1
	then
		echo "FAIL v7 runtime verifier accepts mutation: $name" >&2
		exit 1
	fi
}

mutation=0
mutate_probe() {
	name=$1
	expression=$2
	mutation=$((mutation + 1))
	output=$stage/mutations/probe.$mutation
	sed "$expression" "$stage/a/probe" >"$output"
	expect_rejected "$name" "$stage/a/baseline" "$output"
}

mutate_baseline() {
	name=$1
	expression=$2
	mutation=$((mutation + 1))
	output=$stage/mutations/baseline.$mutation
	sed "$expression" "$stage/a/baseline" >"$output"
	expect_rejected "$name" "$output" "$stage/a/probe"
}

mutate_probe page-rounded-oracle \
	"s/printf '4\\\\n4096\\\\n43288\\\\n'/printf '4096\\\\n4096\\\\n45056\\\\n'/"
mutate_probe wrong-sqe-raw-size \
	"s/printf '4\\\\n4096\\\\n43288\\\\n'/printf '4\\\\n4096\\\\n43292\\\\n'/"
mutate_probe missing-snapshot \
	'/cmp "$state_dir\/gem.before" "$state_dir\/gem.after"/d'
mutate_probe two-kernel-news \
	"s/rog5_ucode_kernel_new 3 'kernel GEM new'/rog5_ucode_kernel_new 2 'kernel GEM new'/"
mutate_probe old-trace-namespace 's/rog5_ucode_v7/rog5_ucode_v6/g'
mutate_probe missing-logical-object-set \
	'/cmp "$state_dir\/logical-objects" "$state_dir\/unpins"/d'
mutate_baseline wrong-size-policy \
	's/size_policy=RAW_KERNEL_NEW_ENTRY_ARGUMENTS/size_policy=PAGE_ROUNDED_OBJECTS/'
mutate_baseline wrong-object-size-contract \
	's/object_size_contract=4096,4096,45056/object_size_contract=4,4096,43288/'
mutate_baseline wrong-predecessor \
	's/predecessor=v6_live_rejected_consumed/predecessor=v6_live_pending/'
mutate_baseline wrong-report \
	's/cfdd0837e6da7d06ba74e0557c6abeea396f12f02e345d9ab87ba1a47ade89e6/0fdd0837e6da7d06ba74e0557c6abeea396f12f02e345d9ab87ba1a47ade89e6/'

echo 'PASS A660 ucode-allocation v7 runtime is reproducibly generated and rejects raw/page-size, snapshot, trace, logical, predecessor, and report mutations'
