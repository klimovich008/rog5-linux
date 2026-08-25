#!/bin/sh
set -eu

export PATH=/sbin:/bin:/usr/sbin:/usr/bin
input=/run/arch-local-a.ext4.gz
userdata_record=/run/rog5-userdata-device
status=/run/rog5-local-image-stage.status
reboot_helper=/usr/libexec/rog5-reboot-bootloader
expected_input_size=649960943
expected_input_sha256=41f75ab6c9c74e3f511fcac4a85b1c4da93695bc56bf85ab954a42f70d83ba88
expected_image_size=17179869184
expected_image_sha256=533973be0e0ca76c5db8645fdef9aeb64d20b8c9c98b70124a2561700f119153
expected_uuid=598a876b-a8db-4859-a01a-1b864b0a87f4
expected_label=ROG5_ARCH_A
mountpoint=/mnt/userdata
mounted=0
userdata=
userdata_disk=

return_bootloader() {
	sync || true
	"$reboot_helper" || true
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
	trap - EXIT HUP INT TERM
	[ "$mounted" -eq 0 ] || umount "$mountpoint" || true
	relock || true
	printf 'state=FAIL\nreason=%s\n' "$reason" >"$status" 2>/dev/null || true
	cat "$status" 2>/dev/null || true
	sleep 1
	return_bootloader
}
trap 'fail interrupted' HUP INT TERM

[ "$(id -u)" -eq 0 ] || fail not-root
[ -f "$input" ] && [ ! -L "$input" ] &&
	[ "$(stat -c '%u:%g:%a:%s:%h' "$input")" = "0:0:600:$expected_input_size:1" ] ||
	fail input-metadata
[ "$(sha256sum "$input" | awk '{print $1}')" = "$expected_input_sha256" ] ||
	fail input-hash
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

blockdev --setrw "$userdata" || fail partition-rw
blockdev --setrw "$userdata_disk" || fail disk-rw
[ "$(blockdev --getro "$userdata")" = 0 ] &&
	[ "$(blockdev --getro "$userdata_disk")" = 0 ] || fail write-window
mkdir -p "$mountpoint"
mount -t ext4 -o rw,nodev,nosuid,noatime "$userdata" "$mountpoint" || fail mount
mounted=1
set -- "$mountpoint"/*
[ "$#" -eq 1 ] && [ "${1##*/}" = lost+found ] || fail userdata-content
mkdir -m 0700 "$mountpoint/rog5" "$mountpoint/rog5/images"
partial=$mountpoint/rog5/images/arch-local-a.ext4.partial
final=$mountpoint/rog5/images/arch-local-a.ext4
[ ! -e "$partial" ] && [ ! -e "$final" ] || fail image-exists
gzip -dc "$input" >"$partial" || fail decompress
chmod 0600 "$partial"
[ "$(stat -c %s "$partial")" -eq "$expected_image_size" ] || fail image-size
[ "$(sha256sum "$partial" | awk '{print $1}')" = "$expected_image_sha256" ] ||
	fail image-hash
e2fsck -fn "$partial" >/dev/null || fail image-fsck
identity=$(blkid "$partial") || fail image-blkid
printf '%s\n' "$identity" | grep -Fq " UUID=\"$expected_uuid\"" || fail image-uuid
printf '%s\n' "$identity" | grep -Fq " LABEL=\"$expected_label\"" || fail image-label
sync -f "$partial"
mv -T "$partial" "$final"
sync -f "$mountpoint/rog5/images"
umount "$mountpoint" || fail unmount
mounted=0
relock || fail relock
[ "$(blockdev --getro "$userdata")" = 1 ] &&
	[ "$(blockdev --getro "$userdata_disk")" = 1 ] || fail relock-state
printf 'state=PASS\nimage_sha256=%s\nimage_size=%s\nfilesystem_uuid=%s\nfilesystem_label=%s\n' \
	"$expected_image_sha256" "$expected_image_size" "$expected_uuid" "$expected_label" >"$status"
sync
cat "$status"
sleep 1
return_bootloader
