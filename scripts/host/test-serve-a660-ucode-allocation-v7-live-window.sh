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
	'/var/lib/rog5-network-root-a660-ucode-allocation-v7)' \
	'ALLOW_MAINLINE_A660_UCODE_ALLOCATION_V7_NFS' \
	'[[ ${ALLOW_MAINLINE_A660_UCODE_ALLOCATION_V7_NFS:-} == 1 ]]' \
	'verify-a660-ucode-allocation-v7-export.sh' \
	'/var/lib/rog5-network-root-a660-ucode-allocation-v6' \
	'for the attended v7 window'
do
	grep -Fq "$contract" "$serve" || {
		echo "FAIL bounded NFS server omits v7 live-window contract: $contract" >&2
		exit 1
	}
done

case_line=$(grep -n \
	'/var/lib/rog5-network-root-a660-ucode-allocation-v7)' "$serve" |
	head -n 1 | cut -d: -f1)
guard_line=$(grep -n \
	'ALLOW_MAINLINE_A660_UCODE_ALLOCATION_V7_NFS:-' "$serve" |
	head -n 1 | cut -d: -f1)
verify_line=$(grep -n \
	'verify-a660-ucode-allocation-v7-export.sh' "$serve" |
	head -n 1 | cut -d: -f1)
state_line=$(grep -n '^etab=' "$serve" | head -n 1 | cut -d: -f1)

[ "$case_line" -lt "$guard_line" ]
[ "$guard_line" -lt "$verify_line" ]
[ "$verify_line" -lt "$state_line" ]
[ "$(grep -Fc 'ALLOW_MAINLINE_A660_UCODE_ALLOCATION_V7_NFS:-' \
	"$serve")" -eq 1 ]

for consumed in \
	/var/lib/rog5-network-root-adreno-smmu-v20 \
	/var/lib/rog5-network-root-adreno-smmu-v21 \
	/var/lib/rog5-network-root-a660-registration \
	/var/lib/rog5-network-root-a660-registration-v2 \
	/var/lib/rog5-network-root-a660-registration-v3 \
	/var/lib/rog5-network-root-a660-firmware-request-only-v4 \
	/var/lib/rog5-network-root-a660-ucode-allocation-v5 \
	/var/lib/rog5-network-root-a660-ucode-allocation-v6
do
	if grep -Fq "$consumed)" "$serve"; then
		echo "FAIL bounded NFS server re-allows consumed root: $consumed" >&2
		exit 1
	fi
done

if grep -Eq '(^|[[:space:]])(fastboot|adb)([[:space:]]|$)' "$serve"; then
	echo 'FAIL bounded NFS server gained phone boot control' >&2
	exit 1
fi

echo 'PASS A660 ucode-allocation v7 NFS window is exact-root, opt-in, verifier-first, bounded, and non-flashing'
