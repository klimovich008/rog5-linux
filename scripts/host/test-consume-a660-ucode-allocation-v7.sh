#!/bin/sh
set -eu

repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)
serve=$repo/scripts/host/serve-network-root.sh
live_window_test=$repo/scripts/host/test-serve-a660-ucode-allocation-v7-live-window.sh

[ -x "$serve" ] || {
	echo 'FAIL missing bounded network-root server' >&2
	exit 1
}
bash -n "$serve"

for forbidden in \
	'/var/lib/rog5-network-root-a660-ucode-allocation-v7)' \
	'ALLOW_MAINLINE_A660_UCODE_ALLOCATION_V7_NFS' \
	'verify-a660-ucode-allocation-v7-export.sh' \
	'for the attended v7 window'
do
	if grep -Fq "$forbidden" "$serve"; then
		echo "FAIL consumed v7 remains server-runnable: $forbidden" >&2
		exit 1
	fi
done

[ ! -e "$live_window_test" ] || {
	echo 'FAIL consumed v7 live-window test remains present' >&2
	exit 1
}

echo 'PASS A660 ucode-allocation v7 is consumed and absent from the bounded NFS server'
