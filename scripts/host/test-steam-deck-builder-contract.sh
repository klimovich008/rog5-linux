#!/usr/bin/env bash
set -euo pipefail

fail() {
	echo "FAIL $*" >&2
	exit 1
}

repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
verifier=$repo/scripts/host/verify-steam-deck-builder.sh
profile=$repo/configs/kernel-builder/steam-deck-asus-5.4-v1.json
artifact=$repo/artifacts/kernel-builder-steamdeck-v1/rootfs-manifest.tsv.gz

for path in "$verifier" "$profile" "$artifact"; do
	[[ -f $path && ! -L $path ]] ||
		fail "missing regular Steam Deck builder contract input: ${path#"$repo"/}"
done
[[ -x $verifier ]] ||
	fail 'Steam Deck builder verifier is not executable'
bash -n "$verifier"
python3 -m json.tool "$profile" >/dev/null

for token in \
	'"status": "qualified"' \
	'"authority": "host-build-only"' \
	'"rootless": true' \
	'"independent_builds": 2' \
	'"clean_network_disabled_builds": 2' \
	'"oci_ids_are_diagnostic": true' \
	'"historical_oracle_match": "byte-for-byte"' \
	'592aefb37589f9f9483b43677e29702ed927fc56a251616e33e81f2645e9c35a' \
	'df28224e6e8d2dfc825ac49dc9f6bdeb12bbcdae2dff92cbbf14a8a94177578f' \
	'438aaf1c99455e23ff27f758738e779b0fd318e68c58467eeae7b77c55a87520' \
	'cfd65186afd75435d34cb33a36c76c4a80a861d0360bec13495c0b445836b7c2'; do
	grep -Fq -- "$token" "$profile" ||
		fail "Steam Deck builder profile lost contract token: $token"
done
for token in \
	'1bc7ee578bb59ce53c92ccf8e666b84ba2560c573d1f9392061b88831deb904b' \
	'6b6aed304febe0c595bfe379d7a48e0f1216d58dd858cd785e931a708fc136d2' \
	'7680447aa94ed11de4313347face7b7b2168d73c92b243f733eeb656cf6bd94b' \
	'a82749a50365d864714594cc40ce27a28af4f132ef0e540946338b4681bf1fda' \
	'bootstrap-kernel-builder.sh' \
	'rootfs-manifest.tsv.gz' \
	'PASS qualified Steam Deck ASUS 5.4 kernel builder'; do
	grep -Fq -- "$token" "$verifier" ||
		fail "Steam Deck builder verifier lost contract token: $token"
done
if grep -Eq '\bsudo\b|fastboot|adb|/dev/(sd|nvme|ufs)' \
	"$verifier" "$profile"; then
	fail 'Steam Deck builder profile contains privilege, phone, or raw-storage actions'
fi
if "$verifier" localhost/untagged >/dev/null 2>&1; then
	fail 'Steam Deck builder verifier accepted an untagged image reference'
fi

echo 'PASS qualified Steam Deck builder profile contract'
