#!/bin/sh
# shellcheck disable=SC2016
set -eu

repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)
serve=$repo/scripts/host/serve-network-root.sh

[ -x "$serve" ] || {
	echo 'FAIL missing bounded network-root server' >&2
	exit 1
}
bash -n "$serve"

for contract in \
	'/var/lib/rog5-network-root-a660-ucode-allocation-v5)' \
	'ALLOW_MAINLINE_A660_UCODE_ALLOCATION_NFS' \
	'[[ ${ALLOW_MAINLINE_A660_UCODE_ALLOCATION_NFS:-} == 1 ]]' \
	'verify-a660-ucode-allocation-export.sh' \
	'/var/lib/rog5-network-root-a660-registration-v3'
do
	grep -Fq "$contract" "$serve" || {
		echo "FAIL bounded NFS server omits v5 live-window contract: $contract" >&2
		exit 1
	}
done

case_line=$(grep -n \
	'/var/lib/rog5-network-root-a660-ucode-allocation-v5)' "$serve" |
	head -n 1 | cut -d: -f1)
guard_line=$(grep -n \
	'ALLOW_MAINLINE_A660_UCODE_ALLOCATION_NFS:-' "$serve" |
	head -n 1 | cut -d: -f1)
verify_line=$(grep -n \
	'verify-a660-ucode-allocation-export.sh' "$serve" |
	head -n 1 | cut -d: -f1)
state_line=$(grep -n '^etab=' "$serve" | head -n 1 | cut -d: -f1)

[ "$case_line" -lt "$guard_line" ]
[ "$guard_line" -lt "$verify_line" ]
[ "$verify_line" -lt "$state_line" ]

for consumed in \
	/var/lib/rog5-network-root-adreno-smmu-v20 \
	/var/lib/rog5-network-root-adreno-smmu-v21 \
	/var/lib/rog5-network-root-a660-registration \
	/var/lib/rog5-network-root-a660-registration-v2 \
	/var/lib/rog5-network-root-a660-registration-v3 \
	/var/lib/rog5-network-root-a660-firmware-request-only-v4
do
	if grep -Fq "$consumed)" "$serve"; then
		echo "FAIL bounded NFS server re-allows consumed root: $consumed" >&2
		exit 1
	fi
done

echo 'PASS A660 ucode-allocation v5 NFS window is exact-root, opt-in, verifier-first, bounded, and non-flashing'
