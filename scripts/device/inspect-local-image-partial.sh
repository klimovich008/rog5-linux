#!/bin/sh
set -eu

export PATH=/sbin:/bin:/usr/sbin:/usr/bin
userdata_record=/run/rog5-userdata-device
status=/run/rog5-local-image-stage.status
reboot_helper=/usr/libexec/rog5-reboot-bootloader
mountpoint=/mnt/userdata
partial=$mountpoint/rog5/images/arch-local-a.ext4.partial
final=$mountpoint/rog5/images/arch-local-a.ext4

emergency_bootloader() {
	trap - EXIT HUP INT TERM
	"$reboot_helper" >/dev/null 2>&1 &
	sleep 3
	printf b >/proc/sysrq-trigger
	while :; do sleep 3600; done
}

fail() {
	printf 'state=FAIL\nreason=%s\n' "$1"
	emergency_bootloader
}
trap 'fail interrupted' HUP INT TERM

(
	sleep 120
	emergency_bootloader
) &
watchdog=$!

[ "$(id -u)" -eq 0 ] || fail not-root
[ "$(cat "$status")" = "$(printf 'state=READY\nuserdata=%s\nstorage=read-only\nssh=key-only' "$(cat "$userdata_record")")" ] ||
	fail readiness
userdata=$(cat "$userdata_record")
case $userdata in /dev/sd[a-z]23) ;; *) fail userdata-path ;; esac
userdata_disk=${userdata%23}
[ "$(blockdev --getro "$userdata")" = 1 ] &&
	[ "$(blockdev --getro "$userdata_disk")" = 1 ] || fail storage-not-read-only
[ -z "$(awk '$1 ~ "^/dev/sd" { print }' /proc/mounts)" ] || fail storage-mounted

mkdir -p "$mountpoint"
mount -t ext4 -o ro,noload,nodev,nosuid,noexec,noatime "$userdata" "$mountpoint" ||
	fail mount

partial_type=absent
partial_uid=0
partial_gid=0
partial_mode=none
partial_links=0
partial_size=0
partial_blocks=0
if [ -L "$partial" ]; then
	partial_type=symlink
elif [ -f "$partial" ]; then
	partial_type=regular
elif [ -e "$partial" ]; then
	partial_type=other
fi
if [ "$partial_type" != absent ]; then
	metadata=$(stat -c '%u:%g:%a:%h:%s:%b' "$partial") || fail partial-stat
	IFS=: read -r partial_uid partial_gid partial_mode partial_links partial_size partial_blocks <<EOF
$metadata
EOF
fi

if [ -L "$final" ]; then
	final_type=symlink
elif [ -f "$final" ]; then
	final_type=regular
elif [ -e "$final" ]; then
	final_type=other
else
	final_type=absent
fi

printf '%s\n' \
	'format=rog5-local-image-partial-inspection-v1' \
	"partial_type=$partial_type" \
	"partial_uid=$partial_uid" \
	"partial_gid=$partial_gid" \
	"partial_mode=$partial_mode" \
	"partial_links=$partial_links" \
	"partial_size=$partial_size" \
	"partial_blocks_512=$partial_blocks" \
	"final_type=$final_type" \
	"rog5_stat=$(stat -c '%u:%g:%a:%h' "$mountpoint/rog5")" \
	"images_stat=$(stat -c '%u:%g:%a:%h' "$mountpoint/rog5/images")" \
	'result=PASS'

umount "$mountpoint" || fail unmount
kill "$watchdog" 2>/dev/null || true
emergency_bootloader
