#!/bin/sh
set -eu

repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)
init=$repo/initramfs/persistent-slotb-loader-init
shutdown=$repo/initramfs/persistent-root-shutdown-standalone
loader_builder=$repo/scripts/device/build-persistent-slotb-loader-initramfs.sh
target_builder=$repo/scripts/device/build-persistent-root-standalone-initramfs.sh
base=$repo/build/persistent-native-root-v8-generation233-20260828-r1/wrapper-a/rog5-kexec-stage-initramfs.cpio.gz
target_base=$repo/artifacts/persistent-native-root-v4/initramfs.cpio.gz

for path in "$init" "$shutdown" "$loader_builder" "$target_builder"; do
	[ -x "$path" ]
	sh -n "$path"
done

for contract in \
	'24:arch_root_a' \
	'427819008' \
	'67108824' \
	'253403070464' \
	'34359717888' \
	'mount -t ext4 -o ro,noload' \
	'format=rog5-slotb-selector-v1' \
	'/usr/libexec/rog5-bundle-verify' \
	'/usr/sbin/kexec -c -l' \
	'disable_haven_watchdog' \
	'Failed to deactivate secure wdog' \
	'"$reboot_helper"' \
	'watchdog_seconds=180'; do
	grep -Fq "$contract" "$init"
done
! grep -Eq 'curl|wget|169[.]254[.]77|ssh|scp|fastboot|adb' "$init"
for contract in \
	'format=rog5-slotb-loader-progress-v1' \
	'ROG5 slot B loader' \
	'*a600000*' \
	'[ "$matches" -eq 1 ]' \
	'set_stage S20 PASS storage_resolved' \
	'set_stage S40 PASS selector_verified' \
	'set_stage S60 PASS bundle_verified' \
	'set_stage S70 PASS kexec_loaded' \
	'set_stage S80 PASS haven_disabled' \
	'set_stage S90 PASS execute' \
	'set_stage terminal FAIL "$1"'; do
	grep -Fq "$contract" "$init"
done
grep -Fq '"$bb" reboot -f' "$shutdown"
! grep -Fq 'rog5-reboot-bootloader' "$shutdown"

if [ -f "$base" ] && [ -f "$target_base" ]; then
	work=$(mktemp -d)
	trap 'rm -rf -- "$work"' EXIT HUP INT TERM
	awk '
		/^read_selector\(\) \{/ { copy=1 }
		copy { print }
		copy && /^}/ { exit }
	' "$init" >"$work/read-selector.sh"
	# shellcheck disable=SC1090
	. "$work/read-selector.sh"
	selector=$work/selector
	stat() {
		if [ "$1" = -c ] && [ "$2" = '%u:%g:%a:%h' ] &&
			[ "$3" = "$selector" ]; then
			mode=$(command stat -c %a "$3")
			printf '0:0:%s:1\n' "$mode"
		else
			command stat "$@"
		fi
	}
	write_selector() {
		printf '%s\n' \
			'format=rog5-slotb-selector-v1' \
			'bundle=persistent-native-root-release-v1' \
			'manifest_sha256=2b259a6e5912549dc2210d12c5f3b4da5422817720addc85e660bf9d3edf75ec' \
			>"$selector"
		chmod 0600 "$selector"
	}
	write_selector
	read_selector
	[ "$bundle" = persistent-native-root-release-v1 ]
	[ "$manifest_hash" = 2b259a6e5912549dc2210d12c5f3b4da5422817720addc85e660bf9d3edf75ec ]
	for mutation in traversal zero duplicate writable; do
		write_selector
		case $mutation in
			traversal) sed -i 's/^bundle=.*/bundle=..\/escape/' "$selector" ;;
			zero) sed -i 's/^manifest_sha256=.*/manifest_sha256=0000000000000000000000000000000000000000000000000000000000000000/' "$selector" ;;
			duplicate) printf '%s\n' 'bundle=second' >>"$selector" ;;
			writable) chmod 0644 "$selector" ;;
		esac
		if read_selector; then
			echo "FAIL hostile selector accepted: $mutation" >&2
			exit 1
		fi
	done

	"$loader_builder" "$base" "$work/loader.cpio.gz" >/dev/null
	"$target_builder" "$target_base" "$work/target.cpio.gz" >/dev/null
	mkdir "$work/loader" "$work/target"
	gzip -dc "$work/loader.cpio.gz" | (cd "$work/loader" && cpio -idm --quiet --no-absolute-filenames)
	gzip -dc "$work/target.cpio.gz" | (cd "$work/target" && cpio -idm --quiet --no-absolute-filenames)
	cmp "$work/loader/init" "$init"
	cmp "$work/target/shutdown" "$shutdown"
	[ -x "$work/loader/usr/libexec/rog5-reboot-bootloader" ]
	[ "$(stat -c %s "$work/loader.cpio.gz")" -lt 8388608 ]
fi

echo 'PASS persistent slot-B loader is local, signed-bundle-only, p24-read-only, watchdog-bounded, and standalone-reboot capable'
