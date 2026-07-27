#!/bin/sh
set -eu

repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)
builder=$repo/scripts/device/build-a660-gmu-resume-entry-v9-runtime.sh
verifier=$repo/scripts/device/verify-a660-gmu-resume-entry-v9-runtime-sources.sh
baseline_patch=$repo/patches/runtime/a660-gmu-resume-entry-v9-baseline.patch
probe_patch=$repo/patches/runtime/a660-gmu-resume-entry-v9-probe.patch

for input in "$builder" "$verifier"; do
	[ -x "$input" ] || {
		echo "FAIL missing executable A660 GMU resume-entry v9 runtime tool: $input" >&2
		exit 1
	}
	sh -n "$input"
done
for input in "$baseline_patch" "$probe_patch"; do
	[ -f "$input" ] && [ ! -L "$input" ] || {
		echo "FAIL missing A660 GMU resume-entry v9 runtime patch: $input" >&2
		exit 1
	}
done

echo 'PASS A660 GMU resume-entry v9 runtime tooling is present'
