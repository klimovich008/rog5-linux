#!/bin/sh
set -eu

repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)
init=$repo/initramfs/recovery-init
executor=$repo/initramfs/persistent-slotb-local-loader
builder=$repo/scripts/device/build-persistent-slotb-recovery-initramfs.sh
base=$repo/build/persistent-native-root-v8-generation233-20260828-r1/wrapper-a/rog5-kexec-stage-initramfs.cpio.gz

for path in "$init" "$executor" "$builder"; do
	[ -x "$path" ]
	sh -n "$path"
done

for contract in \
	'persistent-slotb-loader-v1)' \
	'/usr/libexec/rog5-persistent-slotb-local-loader' \
	"if [ \"\$recovery_mode\" = persistent-slotb-loader-v1 ]; then"; do
	grep -Fq "$contract" "$init"
done
grep -Fq 'storage-layout-stage1-v1|storage-layout-stage2-v1|persistent-slotb-loader-v1)' "$init"

for contract in \
	'format=rog5-slotb-loader-progress-v1' \
	'24:arch_root_a' \
	'427819008' \
	'67108824' \
	'mount -t ext4 -o ro,noload' \
	'format=rog5-slotb-selector-v1' \
	'/usr/libexec/rog5-bundle-verify' \
	'/usr/sbin/kexec -c -l' \
	'disable_haven_watchdog' \
	'Failed to deactivate secure wdog' \
	'set_stage S90 PASS execute'; do
	grep -Fq "$contract" "$executor"
done
! grep -Eq 'usb_gadget|a600000[.]ssusb|/sys/class/udc|ip address|169[.]254[.]77|ssh|adb|fastboot|--setrw|mkfs|sgdisk' "$executor"

if [ -f "$base" ]; then
	work=$(mktemp -d)
	trap 'rm -rf -- "$work"' EXIT HUP INT TERM
	"$builder" "$base" "$init" "$executor" "$work/a.cpio.gz"
	"$builder" "$base" "$init" "$executor" "$work/b.cpio.gz"
	cmp "$work/a.cpio.gz" "$work/b.cpio.gz"
	mkdir "$work/root"
	gzip -dc "$work/a.cpio.gz" |
		(cd "$work/root" && cpio -idm --quiet --no-absolute-filenames)
	cmp "$work/root/init" "$init"
	cmp "$work/root/usr/libexec/rog5-persistent-slotb-local-loader" "$executor"
	[ "$(cat "$work/root/etc/rog5/recovery-mode")" = persistent-slotb-loader-v1 ]
	[ -x "$work/root/usr/libexec/rog5-reboot-bootloader" ]
	[ -x "$work/root/usr/libexec/rog5-bundle-verify" ]
	[ -x "$work/root/usr/sbin/kexec" ]
	[ ! -e "$work/root/usr/libexec/rog5-recovery-control" ]
	[ ! -e "$work/root/usr/libexec/rog5-bundle-fetch" ]
fi

echo 'PASS canonical recovery owns USB/watchdog setup and executes one local signed read-only p24 bundle loader'
