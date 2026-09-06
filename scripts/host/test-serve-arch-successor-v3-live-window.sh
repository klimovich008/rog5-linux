#!/bin/sh
# shellcheck disable=SC2016
set -eu

repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)
serve=$repo/scripts/host/serve-arch-successor-v3.sh
verify=$repo/scripts/host/verify-arch-successor-v3-export.sh
accepted_serve=$repo/scripts/host/serve-network-root.sh
accepted_test=$repo/scripts/host/test-network-root-host.sh

for script in "$serve" "$verify" "$accepted_serve" "$accepted_test"; do
	[ -x "$script" ] || {
		echo "FAIL missing successor v3 NFS control: $script" >&2
		exit 1
	}
	bash -n "$script"
done
"$accepted_test" >/dev/null

for contract in \
	'/var/lib/rog5-network-root-arch-successor-v3' \
	'ALLOW_ARCH_SUCCESSOR_V3_NFS' \
	'[[ ${ALLOW_ARCH_SUCCESSOR_V3_NFS:-} == 1 ]]' \
	'verify-arch-successor-v3-export.sh' \
	'for the attended Arch successor v3 window'
do
	grep -Fq "$contract" "$serve" || {
		echo "FAIL successor v3 NFS window omits: $contract" >&2
		exit 1
	}
done

root_line=$(grep -n \
	'root == /var/lib/rog5-network-root-arch-successor-v3' "$serve" |
	head -n 1 | cut -d: -f1)
guard_line=$(grep -n 'ALLOW_ARCH_SUCCESSOR_V3_NFS:-' "$serve" |
	head -n 1 | cut -d: -f1)
verify_line=$(grep -n 'verify-arch-successor-v3-export.sh' "$serve" |
	head -n 1 | cut -d: -f1)
state_line=$(grep -n '^etab=' "$serve" | head -n 1 | cut -d: -f1)

[ "$root_line" -lt "$guard_line" ]
[ "$guard_line" -lt "$verify_line" ]
[ "$verify_line" -lt "$state_line" ]
[ "$(grep -Fc 'ALLOW_ARCH_SUCCESSOR_V3_NFS:-' "$serve")" -eq 1 ]
[ "$(grep -Fc 'verify-arch-successor-v3-export.sh' "$serve")" -eq 1 ]
accepted_runtime=$(sed -n '/^etab=/,$p' "$accepted_serve" | sha256sum |
	cut -d ' ' -f 1)
v3_runtime=$(sed -n '/^etab=/,$p' "$serve" | sha256sum |
	cut -d ' ' -f 1)
[ "$v3_runtime" = "$accepted_runtime" ]

if grep -Eq '/var/lib/rog5-network-root-arch-successor-v[12]([^0-9]|$)' \
	"$serve"
then
	echo 'FAIL successor v3 NFS window references an earlier root' >&2
	exit 1
fi
if grep -Eq \
	'(^|[[:space:]])(fastboot|adb)([[:space:]]|$)|dd[[:space:]].*of=/dev/' \
	"$serve"
then
	echo 'FAIL successor v3 NFS window gained boot or storage control' >&2
	exit 1
fi

echo 'PASS Arch successor v3 NFS window is exact-root, one-token, verifier-first, bounded, predecessor-independent, and non-flashing'
