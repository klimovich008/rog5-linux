#!/bin/sh
# shellcheck disable=SC2016
set -eu

repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)
serve=$repo/scripts/host/serve-arch-successor-v2.sh
verify=$repo/scripts/host/verify-arch-successor-v2-export.sh

for script in "$serve" "$verify"; do
	[ -x "$script" ] || {
		echo "FAIL missing successor v2 NFS control: $script" >&2
		exit 1
	}
	bash -n "$script"
done

for contract in \
	'/var/lib/rog5-network-root-arch-successor-v2' \
	'ALLOW_ARCH_SUCCESSOR_V2_NFS' \
	'[[ ${ALLOW_ARCH_SUCCESSOR_V2_NFS:-} == 1 ]]' \
	'verify-arch-successor-v2-export.sh' \
	'for the attended Arch successor v2 window'
do
	grep -Fq "$contract" "$serve" || {
		echo "FAIL successor v2 NFS window omits: $contract" >&2
		exit 1
	}
done

root_line=$(grep -n \
	'root == /var/lib/rog5-network-root-arch-successor-v2' "$serve" |
	head -n 1 | cut -d: -f1)
guard_line=$(grep -n 'ALLOW_ARCH_SUCCESSOR_V2_NFS:-' "$serve" |
	head -n 1 | cut -d: -f1)
verify_line=$(grep -n 'verify-arch-successor-v2-export.sh' "$serve" |
	head -n 1 | cut -d: -f1)
state_line=$(grep -n '^etab=' "$serve" | head -n 1 | cut -d: -f1)

[ "$root_line" -lt "$guard_line" ]
[ "$guard_line" -lt "$verify_line" ]
[ "$verify_line" -lt "$state_line" ]
[ "$(grep -Fc 'ALLOW_ARCH_SUCCESSOR_V2_NFS:-' "$serve")" -eq 1 ]
[ "$(grep -Fc 'verify-arch-successor-v2-export.sh' "$serve")" -eq 1 ]

if grep -Fq '/var/lib/rog5-network-root-arch-successor-v1' "$serve"; then
	echo 'FAIL successor v2 NFS window references the accepted v1 root' >&2
	exit 1
fi
if grep -Eq \
	'(^|[[:space:]])(fastboot|adb)([[:space:]]|$)|dd[[:space:]].*of=/dev/' \
	"$serve"
then
	echo 'FAIL successor v2 NFS window gained boot or storage control' >&2
	exit 1
fi

echo 'PASS Arch successor v2 NFS window is exact-root, one-token, verifier-first, bounded, v1-independent, and non-flashing'
