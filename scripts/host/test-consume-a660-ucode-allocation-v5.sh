#!/bin/sh
set -eu

repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)
serve=$repo/scripts/host/serve-network-root.sh

[ -x "$serve" ] || {
	echo 'FAIL missing bounded network-root server' >&2
	exit 1
}
bash -n "$serve"

for forbidden in \
	'/var/lib/rog5-network-root-a660-ucode-allocation-v5)' \
	'ALLOW_MAINLINE_A660_UCODE_ALLOCATION_NFS'
do
	if grep -Fq "$forbidden" "$serve"; then
		echo "FAIL consumed v5 remains server-runnable: $forbidden" >&2
		exit 1
	fi
done

echo 'PASS A660 ucode-allocation v5 is consumed and absent from the bounded NFS server'
