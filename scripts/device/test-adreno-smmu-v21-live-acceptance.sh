#!/bin/sh
set -eu

repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)
verifier=$repo/scripts/device/verify-adreno-smmu-v21-live-acceptance.sh
report=$repo/test-results/2026-07-26-network-root-adreno-smmu-v21-live-accepted.md
marker=$repo/manifests/acceptance/adreno-smmu-v21-live.accepted

[ -x "$verifier" ] || {
	echo 'FAIL missing v21 live-acceptance verifier' >&2
	exit 1
}
[ -f "$report" ] && [ ! -L "$report" ] || {
	echo 'FAIL missing exact v21 live report' >&2
	exit 1
}
[ -f "$marker" ] && [ ! -L "$marker" ] || {
	echo 'FAIL missing exact v21 acceptance marker' >&2
	exit 1
}
sh -n "$verifier"

for contract in \
	0c7bb22301b8203531a7e8f098e8a719fd7f29d7de2cdf3c63730ecb792e9bbc \
	327dfb12142fabb616ffa91fdcf84dc74654e4ba \
	8b4bad817686a690a5aeb6ca27b043aee119a14c \
	37e607795794713472d6944cfbc691211365184a2b674118a17c5d9763b893bf \
	'PASS Adreno-SMMU probe GPUCC=1 SMMU=1 runtime=suspended' \
	'exact_reprobe=1' \
	'driver_override=unset-null-representation' \
	'firmware=0' \
	'render=0' \
	'storage=0' \
	'mounts=0' \
	'failed_units=0' \
	'fallback=PASSED' \
	'host_cleanup=PASSED' \
	'v21_reuse=FORBIDDEN' \
	'flash=NONE'
do
	grep -Fq "$contract" "$verifier" "$marker" || {
		echo "FAIL v21 acceptance contract omits: $contract" >&2
		exit 1
	}
done

"$verifier" "$report" "$marker" >/dev/null

stage=$(mktemp -d)
trap 'rm -rf "$stage"' EXIT INT TERM
cp "$report" "$stage/report"
cp "$marker" "$stage/marker"

printf '\nmutation\n' >>"$stage/report"
if "$verifier" "$stage/report" "$marker" >/dev/null 2>&1; then
	echo 'FAIL v21 acceptance verifier accepted a modified live report' >&2
	exit 1
fi

cp "$report" "$stage/report"
printf 'render=1\n' >>"$stage/marker"
if "$verifier" "$report" "$stage/marker" >/dev/null 2>&1; then
	echo 'FAIL v21 acceptance verifier accepted a modified marker' >&2
	exit 1
fi

rm "$stage/marker"
ln -s "$marker" "$stage/marker"
if "$verifier" "$report" "$stage/marker" >/dev/null 2>&1; then
	echo 'FAIL v21 acceptance verifier accepted a linked marker' >&2
	exit 1
fi

echo 'PASS v21 live acceptance is exact-report pinned, mutation-tested, consumed, and non-flashing'
