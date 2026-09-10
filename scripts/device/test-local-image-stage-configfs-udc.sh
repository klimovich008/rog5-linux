#!/bin/sh
set -eu

repo=$(CDPATH='' cd -- "$(dirname -- "$0")/../.." && pwd -P)
init=$repo/initramfs/local-image-stage-configfs-udc-init

sh -n "$init"
for contract in \
	'mkdir -p "$gadget/functions/ncm.usb0"' \
	'ln -s "$gadget/functions/ncm.usb0"' \
	'a800000.usb) delayed_return 15' \
	'a600000.dwc3) delayed_return 20' \
	'a800000.dwc3) delayed_return 25' \
	'dummy_udc.*) delayed_return 45' \
	'*.usb) delayed_return 50' \
	'*.dwc3) delayed_return 55' \
	'*) delayed_return 60' \
	'*) delayed_return 70' \
	'[ "$seen_zero" -eq 0 ] || delayed_return 75' \
	'delayed_return 80'; do
	grep -Fq "$contract" "$init"
done
for forbidden in \
	'echo "$expected_udc" >"$gadget/UDC"' \
	'/sys/class/block' '/dev/sd' blockdev ext4 ssh kexec insmod modprobe; do
	! grep -Fq "$forbidden" "$init"
done

echo 'PASS post-ConfigFS UDC inventory classifier binds nothing and has no storage surface'
