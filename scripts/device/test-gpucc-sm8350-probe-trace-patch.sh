#!/bin/sh
set -eu

repo=$(CDPATH= cd -- "$(dirname "$0")/../.." && pwd)
patch=$repo/patches/linux-7.1.4/0005-gpucc-sm8350-add-attended-probe-trace.patch
verifier=$repo/scripts/device/verify-gpucc-sm8350-probe-trace-patch.sh
source_dir=${SOURCE_DIR:-}
stage=$(mktemp -d)
trap 'rm -rf "$stage"' EXIT INT TERM

[ -r "$patch" ] && [ -x "$verifier" ]
"$verifier" "$patch" "$source_dir" >/dev/null

sed 's/module_param(probe_trace, bool, 0400);/module_param(probe_trace, bool, 0600);/' \
	"$patch" >"$stage/writable.patch"
if "$verifier" "$stage/writable.patch" "$source_dir" >/dev/null 2>&1; then
	echo 'FAIL trace verifier accepted a writable module parameter' >&2
	exit 1
fi

sed '/ROG5 GPUCC diagnostic: pll1-complete/d' "$patch" \
	>"$stage/incomplete.patch"
if "$verifier" "$stage/incomplete.patch" "$source_dir" >/dev/null 2>&1; then
	echo 'FAIL trace verifier accepted a missing probe phase' >&2
	exit 1
fi

echo 'PASS GPUCC trace patch verifier rejects writable and incomplete mutations'
