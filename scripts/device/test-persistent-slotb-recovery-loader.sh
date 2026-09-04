#!/bin/sh
set -eu

repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)
init=$repo/initramfs/recovery-init
executor=$repo/initramfs/persistent-slotb-local-loader
selector_loader=$repo/initramfs/persistent-slotb-loader-init
trial_helper=$repo/$(cat "$repo/configs/persistent-trial-helper.path")
builder=$repo/scripts/device/build-persistent-slotb-recovery-initramfs.sh
base=$repo/build/persistent-native-root-v8-generation233-20260828-r1/wrapper-a/rog5-kexec-stage-initramfs.cpio.gz

for path in "$init" "$executor" "$selector_loader" "$builder"; do
	[ -x "$path" ]
	sh -n "$path"
done
[ -x "$trial_helper" ]

for contract in \
	'persistent-slotb-loader-v1)' \
	'/usr/libexec/rog5-persistent-slotb-local-loader' \
	"if [ \"\$recovery_mode\" = persistent-slotb-loader-v1 ]; then"; do
	grep -Fq "$contract" "$init"
done
grep -Fq 'storage-layout-stage1-v1|storage-layout-stage2-v1|persistent-slotb-loader-v1)' "$init"

for contract in \
	'exec /usr/libexec/rog5-selector-v2-loader existing-recovery'; do
	grep -Fq "$contract" "$executor"
done
! grep -Eq 'usb_gadget|a600000[.]ssusb|/sys/class/udc|blockdev|mount|kexec|mkfs|sgdisk' "$executor"
for contract in \
	'existing-recovery' \
	'format=rog5-slotb-selector-v1' \
	'format=rog5-slotb-selector-v2' \
	'23:userdata' \
	'verify_trial_write_window' \
	'relock_all_storage' \
	'/usr/libexec/rog5-persistent-trial-state' \
	'/usr/libexec/rog5-bundle-verify' \
	'/usr/sbin/kexec -c -l' \
	'disable_haven_watchdog' \
	'set_stage S90 PASS execute'; do
	grep -Fq "$contract" "$selector_loader"
done

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
	cmp "$work/root/usr/libexec/rog5-selector-v2-loader" "$selector_loader"
	cmp "$work/root/usr/libexec/rog5-persistent-trial-state" "$trial_helper"
	[ "$(cat "$work/root/etc/rog5/recovery-mode")" = persistent-slotb-loader-v1 ]
	[ -x "$work/root/usr/libexec/rog5-reboot-bootloader" ]
	[ -x "$work/root/usr/libexec/rog5-bundle-verify" ]
	[ -x "$work/root/usr/sbin/kexec" ]
	[ ! -e "$work/root/usr/libexec/rog5-recovery-control" ]
	[ ! -e "$work/root/usr/libexec/rog5-bundle-fetch" ]
fi

echo 'PASS canonical recovery owns USB/watchdog setup and executes one local signed read-only p24 bundle loader'
