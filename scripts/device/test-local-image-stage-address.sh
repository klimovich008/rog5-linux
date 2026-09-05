#!/bin/sh
set -eu

repo=$(CDPATH='' cd -- "$(dirname -- "$0")/../.." && pwd -P)
init=$repo/initramfs/local-image-stage-address-init

[ -f "$init" ] && [ -x "$init" ]
for contract in \
	'address-show-failed:70' \
	'address-exact-present:75' \
	'address-conflict:80' \
	'address-add-failed:85' \
	'address-add-pass:90'; do
	grep -Fq "${contract%%:*}) delay=${contract#*:}" "$init"
done
grep -Fq "address_output=\$(ip -4 -o address show dev usb0 2>/dev/null) ||" "$init"
grep -Fq 'address_total=$(printf' "$init"
grep -Fq 'address_exact=$(printf' "$init"
grep -Fq '0:0)' "$init"
grep -Fq '1:1) fail address-exact-present ;;' "$init"
! grep -Fq 'rog5-load-persistent-power-usb' "$init"
! grep -Fq '/rog5-ufs-modules/' "$init"
! grep -Fq 'blockdev ' "$init"
! grep -Fq '/usr/sbin/sshd' "$init"

echo 'PASS address discriminator isolates exact usb0 IPv4 state before power or storage'
