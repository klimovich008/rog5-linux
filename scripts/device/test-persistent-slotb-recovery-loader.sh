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

	# Packaging-only fixture: not a signed/admissible candidate. Runtime crypto
	# remains covered by the exact bundle verifier suite, never mocked as PASS.
	mkdir "$work/ram-fixture"
	for file in Image board.dtb initramfs.cpio.gz manifest; do
		printf 'unsigned fixture %s\n' "$file" >"$work/ram-fixture/$file"
	done
	printf '%064d' 0 >"$work/ram-fixture/manifest.sig"
	"$builder" "$base" "$init" embedded-ram "$work/ram-a.cpio.gz" "$work/ram-fixture"
	"$builder" "$base" "$init" embedded-ram "$work/ram-b.cpio.gz" "$work/ram-fixture"
	cmp "$work/ram-a.cpio.gz" "$work/ram-b.cpio.gz"
	mkdir "$work/ram-root"
	gzip -dc "$work/ram-a.cpio.gz" |
		(cd "$work/ram-root" && cpio -idm --quiet --no-absolute-filenames)
	hash=$(sha256sum "$work/ram-fixture/manifest" | cut -d ' ' -f 1)
	printf '#!/bin/sh\nset -eu\nexec /usr/libexec/rog5-selector-v2-loader existing-recovery-ram ram-fixture %s\n' "$hash" >"$work/expected-executor"
	cmp "$work/expected-executor" "$work/ram-root/usr/libexec/rog5-persistent-slotb-local-loader"
	[ ! -e "$work/ram-root/run/rog5-bundles/ram-fixture" ]
	for file in Image board.dtb initramfs.cpio.gz manifest manifest.sig; do
		cmp "$work/ram-fixture/$file" "$work/ram-root/usr/share/rog5/ram-bundles/ram-fixture/$file"
		[ "$(stat -c '%a:%h' "$work/ram-root/usr/share/rog5/ram-bundles/ram-fixture/$file")" = 600:1 ]
	done
	printf extra >"$work/ram-fixture/extra"
	if "$builder" "$base" "$init" embedded-ram "$work/bad.cpio.gz" "$work/ram-fixture"; then
		echo 'FAIL accepted extra embedded payload' >&2; exit 1
	fi
	[ ! -e "$work/bad.cpio.gz" ]
fi

echo 'PASS canonical recovery owns USB/watchdog setup and executes one local signed read-only p24 bundle loader'
