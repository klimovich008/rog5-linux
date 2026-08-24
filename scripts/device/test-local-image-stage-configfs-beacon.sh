#!/bin/sh
set -eu

repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd -P)
init=$repo/initramfs/local-image-stage-configfs-beacon-init

sh -n "$init"
for contract in \
	'expected_release=@EXPECTED_KERNEL_RELEASE@' \
	'expected_bundle=@EXPECTED_BUNDLE@' \
	'mount -t configfs configfs /sys/kernel/config || delayed_return 5' \
	'|| delayed_return 10' \
	'} || delayed_return 15' \
	'|| delayed_return 20' \
	'} || delayed_return 25' \
	'[ -e "/sys/class/udc/$expected_udc" ] || delayed_return 15' \
	'delayed_return 45' \
	'echo "$expected_udc" >"$gadget/UDC" || delayed_return 55' \
	'sleep 30' \
	'sleep 120'; do
	grep -Fq "$contract" "$init" || {
		echo "FAIL missing ConfigFS beacon contract: $contract" >&2
		exit 1
	}
done
for forbidden in '/sys/class/block' '/dev/sd' blockdev ext4 ssh kexec insmod modprobe; do
	! grep -Fq "$forbidden" "$init" || {
		echo "FAIL ConfigFS beacon contains forbidden surface: $forbidden" >&2
		exit 1
	}
done
echo 'PASS ConfigFS beacon classifies every pre-bind group without storage'
