#!/bin/sh
set -eu

repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)
verifier=$repo/scripts/device/verify-persistent-root-entry-bundle.sh

[ -x "$verifier" ] || {
	echo 'FAIL missing executable P2 early-entry bundle verifier' >&2
	exit 1
}
sh -n "$verifier"

for contract in \
	'artifacts/persistent-root-entry-v1' \
	'09f7e69daf270c584b1947f41872a9af512c47e26fb2e8a30d3cdfb2fcc5d7a5' \
	'3360abb8b47cdc5ffd5be59664b979fad186611442bd8224ced225084a4ecc73' \
	'5171ab75e55dc2de330f126dbffc42fc380a4fc04f623368e775375d48cc8fbc' \
	'36ef17a26a65f9a78a72469f7b44391da0d3a1b77491c5dcb96f662ba5a1f0c6' \
	'36455b88ac36bc88b449893096bba839ac12fe229065b4a23d55687a3b9c8079' \
	'5489638517ebd83684702e6197ea459d890c6274b328cc6a3373b65a05442b3e' \
	'rog5.p2_entry_diag=1' \
	'ROG5 P2 entry oracle' \
	'Algorithm:[[:space:]]*NONE' \
	'head -c "$(stat -c %s "$raw")" "$avb" | cmp - "$raw"' \
	'PASS reproducible credential-free RAM-only P2 early-entry bundle'; do
	grep -Fq "$contract" "$verifier" || {
		echo "FAIL P2 entry bundle verifier omits: $contract" >&2
		exit 1
	}
done

if grep -Eq \
	'^[[:space:]]*(fastboot[[:space:]]+(flash|erase)|adb[[:space:]]|dd[[:space:]].*of=/dev/|mkfs([.][^[:space:]]*)?[[:space:]]|fsck([.][^[:space:]]*)?[[:space:]]|parted[[:space:]]|sgdisk[[:space:]])' \
	"$verifier"; then
	echo 'FAIL P2 entry bundle verifier has a device or storage mutation path' >&2
	exit 1
fi

"$verifier" >/dev/null

echo 'PASS P2 early-entry bundle verifier pins duplicate builds, nested payloads, wrapper command line, and unsigned AVB'
