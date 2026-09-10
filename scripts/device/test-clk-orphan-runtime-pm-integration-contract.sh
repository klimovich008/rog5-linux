#!/bin/sh
set -eu

repo=$(CDPATH= cd -- "$(dirname "$0")/../.." && pwd)
prepare=$repo/scripts/device/prepare-mainline-gpucc-runtime-pm-candidate.sh
build=$repo/scripts/device/build-mainline-gpucc-runtime-pm-candidate.sh
generic_build=$repo/scripts/device/build-mainline-gpucc-parent-diagnostic.sh
patch=$repo/patches/linux-7.1.4/0011-clk-guard-orphan-reparent-with-runtime-PM.patch

for file in "$prepare" "$build" "$generic_build"; do
	[ -x "$file" ]
	sh -n "$file"
done
[ -r "$patch" ]

grep -Fq '0011-clk-guard-orphan-reparent-with-runtime-PM.patch' "$prepare"
grep -Fq '0011-clk-guard-orphan-reparent-with-runtime-PM.patch' "$build"
for contract in \
	'd9ac316489f4258d389d6298659d5e9c22183400' \
	'c796deb1cc54e942f8bb46a2c76a7199e19e5c92'
do
	grep -Fq "$contract" "$prepare"
	grep -Fq "$contract" "$generic_build"
done

grep -Fq 'ORPHAN_RUNTIME_PM_PATCH=' "$build"
grep -Fq 'RCG2_TRACE_PATCH=' "$build"
grep -Fq 'orphan_runtime_pm_patched_commit=' "$generic_build"
grep -Fq 'orphan_runtime_pm_patch_sha256=' "$generic_build"

if grep -Eq 'fastboot[[:space:]]+flash|dd[[:space:]].*of=/dev/|mount[[:space:]].*/dev/|(^|[^_])pm_runtime_(get|put|resume|suspend)' \
	"$prepare" "$build" "$generic_build"
then
	echo 'FAIL runtime-PM integration adds flashing, storage, or direct PM control' >&2
	exit 1
fi

echo 'PASS v15 source/build integration is deterministic, v14-based, generic, and persistent-write-free'
