#!/bin/sh
set -eu

repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd -P)
init=$repo/initramfs/local-image-stage-preusb-diagnostic-init

sh -n "$init"
for contract in \
	'expected_release=@EXPECTED_KERNEL_RELEASE@' \
	'expected_bundle=@EXPECTED_BUNDLE@' \
	'echo /sbin/mdev >/proc/sys/kernel/hotplug 2>/dev/null || :' \
	'log kernel-release' \
	'sleep 5' \
	'log command-line' \
	'sleep 15' \
	'log preusb-checks-pass' \
	'sleep 25' \
	'sleep 60' \
	'"$reboot_helper" || true'; do
	grep -Fq "$contract" "$init" || {
		echo "FAIL missing pre-USB diagnostic contract: $contract" >&2
		exit 1
	}
done

for forbidden in \
	'/sys/class/block' '/dev/sd' 'blockdev' 'mount -t ext4' 'ssh' \
	'usb_gadget' 'insmod' 'modprobe' 'kexec'; do
	! grep -Fq "$forbidden" "$init" || {
		echo "FAIL pre-USB diagnostic contains forbidden surface: $forbidden" >&2
		exit 1
	}
done

echo 'PASS pre-USB diagnostic distinguishes release, cmdline, and success without USB or storage'
