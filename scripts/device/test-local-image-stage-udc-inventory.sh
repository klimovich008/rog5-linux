#!/bin/sh
set -eu

repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd -P)
init=$repo/initramfs/local-image-stage-udc-inventory-init

sh -n "$init"
for contract in \
	'expected_release=@EXPECTED_KERNEL_RELEASE@' \
	'expected_bundle=@EXPECTED_BUNDLE@' \
	'[ -e "/sys/class/udc/$expected_udc" ] || delayed_return 5' \
	'[ "$extra_count" -ne 0 ] || delayed_return 10' \
	'[ "$extra_count" -eq 1 ] || delayed_return 70' \
	'a800000.usb) delayed_return 15' \
	'a600000.dwc3) delayed_return 20' \
	'a800000.dwc3) delayed_return 25' \
	'ci_hdrc.*) delayed_return 30' \
	'musb*|*.musb) delayed_return 35' \
	'dwc2*|*.dwc2) delayed_return 40' \
	'dummy_udc.*) delayed_return 45' \
	'*.usb) delayed_return 50' \
	'*.dwc3) delayed_return 55' \
	'*) delayed_return 60' \
	'sleep 120'; do
	grep -Fq "$contract" "$init" || {
		echo "FAIL missing UDC inventory contract: $contract" >&2
		exit 1
	}
done
for forbidden in usb_gadget '/sys/class/block' '/dev/sd' blockdev ext4 ssh kexec insmod modprobe; do
	! grep -Fq "$forbidden" "$init" || {
		echo "FAIL UDC inventory contains forbidden surface: $forbidden" >&2
		exit 1
	}
done
echo 'PASS UDC inventory classifies one extra basename without binding or storage'
