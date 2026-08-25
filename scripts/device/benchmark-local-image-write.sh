#!/bin/sh
set -eu

export PATH=/sbin:/bin:/usr/sbin:/usr/bin
userdata_record=/run/rog5-userdata-device
status=/run/rog5-local-image-stage.status
reboot_helper=/usr/libexec/rog5-reboot-bootloader
mountpoint=/mnt/userdata
partial=$mountpoint/rog5/images/arch-local-a.ext4.partial
final=$mountpoint/rog5/images/arch-local-a.ext4
benchmark=$mountpoint/rog5/images/write-benchmark
expected_partial_size=825884672
test_size=33554432
mounted=0

log() {
	echo "rog5-write-benchmark: $*" >/dev/kmsg 2>/dev/null || true
}

emergency_bootloader() {
	trap - EXIT HUP INT TERM
	"$reboot_helper" >/dev/null 2>&1 &
	sleep 3
	printf b >/proc/sysrq-trigger
	while :; do sleep 3600; done
}

relock() {
	for sys_block in /sys/class/block/*; do
		[ -e "$sys_block/dev" ] || continue
		device=/dev/$(basename "$sys_block")
		[ -b "$device" ] || continue
		blockdev --setro "$device" || return 1
	done
}

fail() {
	reason=$1
	log "FAIL $reason"
	printf 'state=FAIL\nreason=%s\n' "$reason"
	emergency_bootloader
}
trap 'fail interrupted' HUP INT TERM

(
	sleep 420
	log 'emergency deadline reached'
	emergency_bootloader
) &
watchdog=$!

[ "$(id -u)" -eq 0 ] || fail not-root
[ "$(cat "$status")" = "$(printf 'state=READY\nuserdata=%s\nstorage=read-only\nssh=key-only' "$(cat "$userdata_record")")" ] ||
	fail readiness
userdata=$(cat "$userdata_record")
case $userdata in /dev/sd[a-z]23) ;; *) fail userdata-path ;; esac
userdata_disk=${userdata%23}
[ -b "$userdata" ] && [ -b "$userdata_disk" ] || fail userdata-device
[ "$(blockdev --getro "$userdata")" = 1 ] &&
	[ "$(blockdev --getro "$userdata_disk")" = 1 ] || fail prewrite-lock
[ -z "$(awk '$1 ~ "^/dev/sd" { print }' /proc/mounts)" ] || fail prewrite-mount

battery=/sys/class/power_supply/qcom-battmgr-bat
usb=/sys/class/power_supply/qcom-battmgr-usb
[ "$(cat "$usb/online")" = 1 ] || fail usb-offline
temperature=$(cat "$battery/temp")
case $temperature in ''|*[!0-9]*) fail temperature ;; esac
[ "$temperature" -ge 0 ] && [ "$temperature" -lt 550 ] || fail temperature

blockdev --setrw "$userdata_disk" || fail disk-rw
[ "$(blockdev --getro "$userdata_disk")" = 0 ] || fail disk-rw-state
blockdev --setrw "$userdata" || fail partition-rw
[ "$(blockdev --getro "$userdata")" = 0 ] || fail partition-rw-state
mkdir -p "$mountpoint"
mount -t ext4 -o rw,nodev,nosuid,noatime "$userdata" "$mountpoint" || fail mount
mounted=1

[ "$(stat -c '%u:%g:%a:%h' "$mountpoint/rog5")" = 0:0:700:3 ] || fail rog5-metadata
[ "$(stat -c '%u:%g:%a:%h' "$mountpoint/rog5/images")" = 0:0:700:2 ] || fail images-metadata
partial_size=0
partial_mode=absent
if [ -e "$partial" ] || [ -L "$partial" ]; then
	[ -f "$partial" ] && [ ! -L "$partial" ] || fail partial-identity
	metadata=$(stat -c '%u:%g:%a:%h:%s' "$partial") || fail partial-identity
	IFS=: read -r partial_uid partial_gid partial_mode partial_links partial_size <<EOF
$metadata
EOF
	[ "$partial_uid:$partial_gid:$partial_links" = 0:0:1 ] || fail partial-identity
	case $partial_mode in 600|644) ;; *) fail partial-identity ;; esac
	case $partial_size in ''|*[!0-9]*) fail partial-identity ;; esac
	[ "$partial_size" -gt 0 ] && [ "$partial_size" -le "$expected_partial_size" ] ||
		fail partial-identity
fi
[ ! -e "$final" ] && [ ! -L "$final" ] || fail final-present
[ ! -e "$benchmark" ] && [ ! -L "$benchmark" ] || fail benchmark-present
mkdir -m 0700 "$benchmark"

printf '%s\n' 'format=rog5-local-image-write-benchmark-v1'
printf 'partial_size=%s\n' "$partial_size"
printf 'partial_mode=%s\n' "$partial_mode"
if ! /usr/bin/time -f 'direct_seconds=%e' -o /run/rog5-direct.time \
	timeout -k 5 180 dd if=/dev/zero of="$benchmark/direct.bin" \
		bs=1048576 count=32 oflag=direct conv=fsync status=none; then
	fail direct-write
fi
cat /run/rog5-direct.time
[ "$(stat -c '%u:%g:%a:%h:%s' "$benchmark/direct.bin")" = "0:0:644:1:$test_size" ] ||
	fail direct-metadata
printf 'direct_size=%s\n' "$test_size"
rm "$benchmark/direct.bin" || fail direct-remove
sync -f "$benchmark" || fail direct-directory-sync

if ! /usr/bin/time -f 'buffered_seconds=%e' -o /run/rog5-buffered.time \
	timeout -k 5 180 dd if=/dev/zero of="$benchmark/buffered.bin" \
		bs=1048576 count=32 conv=fsync status=none; then
	fail buffered-write
fi
cat /run/rog5-buffered.time
[ "$(stat -c '%u:%g:%a:%h:%s' "$benchmark/buffered.bin")" = "0:0:644:1:$test_size" ] ||
	fail buffered-metadata
printf 'buffered_size=%s\n' "$test_size"
rm "$benchmark/buffered.bin" || fail buffered-remove
sync -f "$benchmark" || fail buffered-directory-sync
rmdir "$benchmark" || fail benchmark-remove
sync -f "$mountpoint/rog5/images" || fail images-directory-sync

ufs_errors=$(dmesg | grep -Eic 'ufshcd.*(error|failed|timeout)|ufs.*(fatal|reset.*failed)' || true)
printf 'ufs_error_lines=%s\n' "$ufs_errors"
[ "$ufs_errors" -eq 0 ] || fail ufs-errors
printf 'temperature_decic=%s\n' "$(cat "$battery/temp")"
umount "$mountpoint" || fail unmount
mounted=0
relock || fail relock
[ "$(blockdev --getro "$userdata")" = 1 ] &&
	[ "$(blockdev --getro "$userdata_disk")" = 1 ] || fail relock-state
printf '%s\n' 'result=PASS'
kill "$watchdog" 2>/dev/null || true
emergency_bootloader
