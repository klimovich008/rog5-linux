#!/bin/sh
set -eu

repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)
verifier=$repo/scripts/device/verify-a660-registration-v3-live-acceptance.sh
report=$repo/test-results/2026-07-26-a660-registration-v3-live-accepted.md
marker=$repo/manifests/acceptance/a660-registration-v3-live.accepted

[ -x "$verifier" ] || {
	echo 'FAIL missing A660 v3 live-acceptance verifier' >&2
	exit 1
}
[ -f "$report" ] && [ ! -L "$report" ] || {
	echo 'FAIL missing exact A660 v3 live report' >&2
	exit 1
}
[ -f "$marker" ] && [ ! -L "$marker" ] || {
	echo 'FAIL missing exact A660 v3 acceptance marker' >&2
	exit 1
}
sh -n "$verifier"

for contract in \
	2af09c087c917b7d1325c0b8a361c7ec3594779983034be0736acac841f8da79 \
	8b633fba764093071a829946858da02445606d14 \
	5a8d18f6c4a85c7828d3a9f87fe6d5a5d75b703d \
	c1eabc572c27fdd6ba5944526d563907fc9c250ab7a9cc6696685ca16b630f9c \
	'PASS A660 registration GPUCC=1 SMMU=1 GPU=1 GMU=1 iommu=2 render=1' \
	'exact_reprobe=1' \
	'driver_override=unset-null-representation' \
	'module_count=7' \
	'iommu_attachments=2' \
	'render_nodes=1' \
	'drm_fds=0' \
	'display_connectors=0' \
	'firmware=0' \
	'storage=0' \
	'mounts=0' \
	'failed_units=0' \
	'fallback=PASSED' \
	'host_cleanup=PASSED' \
	'v3_reuse=FORBIDDEN' \
	'flash=NONE'
do
	grep -Fq "$contract" "$verifier" "$marker" || {
		echo "FAIL A660 v3 acceptance contract omits: $contract" >&2
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
	echo 'FAIL A660 v3 verifier accepted a modified live report' >&2
	exit 1
fi

cp "$report" "$stage/report"
printf 'drm_fds=1\n' >>"$stage/marker"
if "$verifier" "$report" "$stage/marker" >/dev/null 2>&1; then
	echo 'FAIL A660 v3 verifier accepted a modified marker' >&2
	exit 1
fi

rm "$stage/marker"
ln -s "$marker" "$stage/marker"
if "$verifier" "$report" "$stage/marker" >/dev/null 2>&1; then
	echo 'FAIL A660 v3 verifier accepted a linked marker' >&2
	exit 1
fi

echo 'PASS A660 v3 live acceptance is exact-report pinned, mutation-tested, consumed, unopened, firmware-free, and non-flashing'
