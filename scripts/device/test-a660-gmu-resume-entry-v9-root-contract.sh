#!/bin/sh
set -eu

repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)
prepare=$repo/scripts/host/prepare-a660-gmu-resume-entry-v9-export.sh
verify=$repo/scripts/host/verify-a660-gmu-resume-entry-v9-export.sh
gate=$repo/scripts/device/run-network-root-a660-gmu-resume-entry-v9-gate.sh
gate_test=$repo/scripts/device/test-run-network-root-a660-gmu-resume-entry-v9-gate.sh

for input in "$prepare" "$verify" "$gate" "$gate_test"; do
	[ -x "$input" ] || {
		echo "FAIL missing executable A660 GMU resume-entry v9 root tool: $input" >&2
		exit 1
	}
done

echo 'PASS A660 GMU resume-entry v9 root tooling is present'
