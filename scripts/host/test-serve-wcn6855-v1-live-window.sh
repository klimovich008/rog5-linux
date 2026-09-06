#!/bin/sh
# shellcheck disable=SC2016
set -eu

repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)
serve=$repo/scripts/host/serve-wcn6855-v1.sh
verify=$repo/scripts/host/verify-wcn6855-v1-export.sh
accepted_serve=$repo/scripts/host/serve-network-root.sh
accepted_test=$repo/scripts/host/test-network-root-host.sh

for script in "$serve" "$verify" "$accepted_serve" "$accepted_test"; do
	[ -x "$script" ] || {
		echo "FAIL missing WCN6855 v1 NFS control: $script" >&2
		exit 1
	}
	bash -n "$script"
done
"$accepted_test" >/dev/null

for contract in \
	'/var/lib/rog5-network-root-wcn6855-v1' \
	'ALLOW_WCN6855_V1_NFS' \
	'[[ ${ALLOW_WCN6855_V1_NFS:-} == 1 ]]' \
	'verify-wcn6855-v1-export.sh' \
	'e3961cc441ae6cb75f1a3dcbbd5e4ccc99b31c67018159ac10f61c11f1548769' \
	"source <(sed -n '/^etab=/,\$p' \"\$accepted_serve\")" \
	'for the attended WCN6855 enumeration-only window'
do
	grep -Fq "$contract" "$serve" || {
		echo "FAIL WCN6855 v1 NFS window omits: $contract" >&2
		exit 1
	}
done

root_line=$(grep -n \
	'root == /var/lib/rog5-network-root-wcn6855-v1' "$serve" |
	head -n 1 | cut -d: -f1)
guard_line=$(grep -n 'ALLOW_WCN6855_V1_NFS:-' "$serve" |
	head -n 1 | cut -d: -f1)
verify_line=$(grep -n 'verify-wcn6855-v1-export.sh' "$serve" |
	head -n 1 | cut -d: -f1)
runtime_line=$(grep -n '^source <(sed' "$serve" | head -n 1 | cut -d: -f1)

[ "$root_line" -lt "$guard_line" ]
[ "$guard_line" -lt "$verify_line" ]
[ "$verify_line" -lt "$runtime_line" ]
[ "$(grep -Fc 'ALLOW_WCN6855_V1_NFS:-' "$serve")" -eq 1 ]
[ "$(grep -Fc 'verify-wcn6855-v1-export.sh' "$serve")" -eq 1 ]
[ "$(sha256sum "$accepted_serve" | cut -d ' ' -f 1)" = \
	e3961cc441ae6cb75f1a3dcbbd5e4ccc99b31c67018159ac10f61c11f1548769 ]

if grep -Eq \
	'(^|[[:space:]])(fastboot|adb)([[:space:]]|$)|dd[[:space:]].*of=/dev/' \
	"$serve"
then
	echo 'FAIL WCN6855 v1 NFS window gained boot or storage control' >&2
	exit 1
fi

echo 'PASS WCN6855 v1 NFS window is exact-root, one-token, verifier-first, bounded, byte-identical-runtime, and non-flashing'
