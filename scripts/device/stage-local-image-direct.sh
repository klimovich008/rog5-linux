#!/bin/sh
set -eu

export PATH=/sbin:/bin:/usr/sbin:/usr/bin
userdata_record=/run/rog5-userdata-device
status=/run/rog5-local-image-stage.status
reboot_helper=/usr/libexec/rog5-reboot-bootloader
mountpoint=/mnt/userdata
partial=$mountpoint/rog5/images/arch-local-a.ext4.partial
final=$mountpoint/rog5/images/arch-local-a.ext4
residual=$mountpoint/rog5/images/write-benchmark
extent_map=/etc/rog5-local-image-direct-extents.tsv
next_record=/run/rog5-local-image-direct-next
image_size=17179869184
extent_count=37
extent_map_sha256=e21b9453662d5f24536144e322ed0ef6bde7038efb44fdf1afcb80ee823ccd94

log() { echo "rog5-direct-stage: $*" >/dev/kmsg 2>/dev/null || true; }

emergency_bootloader() {
	trap - EXIT HUP INT TERM
	"$reboot_helper" >/dev/null 2>&1 &
	sleep 3
	printf b >/proc/sysrq-trigger
	while :; do sleep 3600; done
}

fail() {
	log "FAIL $1"
	printf 'state=FAIL\nreason=%s\n' "$1"
	emergency_bootloader
}
trap 'fail interrupted' HUP INT TERM

relock() {
	for sys_block in /sys/class/block/*; do
		[ -e "$sys_block/dev" ] || continue
		device=/dev/$(basename "$sys_block")
		[ -b "$device" ] || continue
		blockdev --setro "$device" || return 1
	done
}

readiness() {
	[ "$(id -u)" -eq 0 ] || fail not-root
	[ "$(cat "$status")" = "$(printf 'state=READY\nuserdata=%s\nstorage=read-only\nssh=key-only' "$(cat "$userdata_record")")" ] ||
		fail readiness
	userdata=$(cat "$userdata_record")
	case $userdata in /dev/sd[a-z]23) ;; *) fail userdata-path ;; esac
	userdata_disk=${userdata%23}
	[ -b "$userdata" ] && [ -b "$userdata_disk" ] || fail userdata-device
	[ "$(sha256sum "$extent_map" | awk '{ print $1 }')" = "$extent_map_sha256" ] ||
		fail extent-map
	grep -Fxq "image_size=$image_size" "$extent_map" || fail extent-map
	grep -Fxq "extent_count=$extent_count" "$extent_map" || fail extent-map
	battery=/sys/class/power_supply/qcom-battmgr-bat
	usb=/sys/class/power_supply/qcom-battmgr-usb
	[ "$(cat "$usb/online")" = 1 ] || fail usb-offline
	temperature=$(cat "$battery/temp")
	case $temperature in ''|*[!0-9]*) fail temperature ;; esac
	[ "$temperature" -ge 0 ] && [ "$temperature" -lt 550 ] || fail temperature
}

mounted_state() {
	[ "$(blockdev --getro "$userdata_disk")" = 0 ] &&
		[ "$(blockdev --getro "$userdata")" = 0 ] || fail write-lock
	awk -v device="$userdata" -v target="$mountpoint" '
	$1 == device && $2 == target && $3 == "ext4" &&
	$4 ~ /(^|,)rw(,|$)/ && $4 ~ /(^|,)nodev(,|$)/ &&
	$4 ~ /(^|,)nosuid(,|$)/ { count++ }
	END { exit count != 1 }' /proc/mounts || fail mount-identity
	[ -f "$partial" ] && [ ! -L "$partial" ] &&
		[ "$(stat -c '%u:%g:%a:%h:%s' "$partial")" = "0:0:600:1:$image_size" ] ||
		fail partial-identity
	[ ! -e "$final" ] && [ ! -L "$final" ] || fail final-present
}

prepare() {
	[ "$(blockdev --getro "$userdata_disk")" = 1 ] &&
		[ "$(blockdev --getro "$userdata")" = 1 ] || fail prewrite-lock
	[ -z "$(awk '$1 ~ "^/dev/sd" { print }' /proc/mounts)" ] || fail prewrite-mount
	blockdev --setrw "$userdata_disk" || fail disk-rw
	blockdev --setrw "$userdata" || fail partition-rw
	mkdir -p "$mountpoint"
	mount -t ext4 -o rw,nodev,nosuid,noatime "$userdata" "$mountpoint" || fail mount
	[ "$(stat -c '%u:%g:%a:%h' "$mountpoint/rog5")" = 0:0:700:3 ] || fail rog5-metadata
	[ -d "$mountpoint/rog5/images" ] && [ ! -L "$mountpoint/rog5/images" ] ||
		fail images-metadata
	if [ -e "$residual" ] || [ -L "$residual" ]; then
		[ -d "$residual" ] && [ ! -L "$residual" ] || fail residual-identity
		inventory=$(find "$residual" -mindepth 1 -maxdepth 1)
		case $inventory in
		'') ;;
		"$residual/buffered.bin")
			[ -f "$residual/buffered.bin" ] && [ ! -L "$residual/buffered.bin" ] ||
				fail residual-identity
			metadata=$(stat -c '%u:%g:%a:%h:%s' "$residual/buffered.bin") ||
				fail residual-identity
			case $metadata in 0:0:600:1:*|0:0:644:1:*) ;; *) fail residual-identity ;; esac
			size=${metadata##*:}
			case $size in ''|*[!0-9]*) fail residual-size ;; esac
			[ "$size" -ge 0 ] && [ "$size" -le 33554432 ] || fail residual-size
			rm "$residual/buffered.bin" || fail residual-remove
			;;
		*) fail residual-inventory ;;
		esac
		rmdir "$residual" || fail residual-remove
	fi
	[ -f "$partial" ] && [ ! -L "$partial" ] || fail partial-identity
	metadata=$(stat -c '%u:%g:%a:%h:%s' "$partial") || fail partial-identity
	case $metadata in
	0:0:600:1:0|0:0:644:1:0|0:0:600:1:$image_size|0:0:644:1:$image_size) ;;
	*) fail partial-identity ;;
	esac
	truncate -s 0 "$partial" || fail partial-truncate
	truncate -s "$image_size" "$partial" || fail partial-truncate
	chmod 0600 "$partial"
	printf '%s\n' 1 >"$next_record"
	printf 'format=rog5-local-image-direct-stage-v1\nstate=READY\nextents=%s\n' "$extent_count"
}

write_extent() {
	index=$1
	case $index in ''|*[!0-9]*) fail extent-index ;; esac
	[ "$index" -ge 1 ] && [ "$index" -le "$extent_count" ] || fail extent-index
	[ "$(cat "$next_record")" = "$index" ] || fail extent-order
	record=$(awk -F '\t' -v wanted="$index" '
	$1 == wanted { count++; line=$0 }
	END { if (count != 1) exit 1; print line }' "$extent_map") || fail extent-map
	tab=$(printf '\t')
	IFS=$tab read -r found offset count <<EOF
$record
EOF
	[ "$found" = "$index" ] || fail extent-map
	stats=/run/rog5-local-image-direct-dd.stats
	offset_bytes=$((offset * 4096))
	count_bytes=$((count * 4096))
	full_records=$((count_bytes / 1048576))
	partial_records=0
	[ "$((count_bytes % 1048576))" -eq 0 ] || partial_records=1
	dd of="$partial" ibs=1048576 obs=1048576 seek="$offset_bytes" \
		count="$count_bytes" iflag=count_bytes,fullblock \
		oflag=seek_bytes,direct conv=notrunc status=noxfer 2>"$stats" ||
		fail direct-write
	[ "$(cat "$stats")" = "$(printf '%s+%s records in\n%s+%s records out' \
		"$full_records" "$partial_records" "$full_records" "$partial_records")" ] ||
		fail direct-count
	printf '%s\n' "$((index + 1))" >"$next_record"
	printf 'format=rog5-local-image-direct-extent-v1\nindex=%s\nblocks=%s\nresult=PASS\n' \
		"$index" "$count"
}

finalize() {
	[ "$(cat "$next_record")" = "$((extent_count + 1))" ] || fail extent-incomplete
	timeout -k 5 180 sync -f "$partial" || fail direct-sync
	timeout -k 5 180 e2fsck -fn "$partial" >/run/rog5-direct-e2fsck.log 2>&1 ||
		fail e2fsck
	mv -T "$partial" "$final" || fail publish
	timeout -k 5 180 sync -f "$mountpoint/rog5/images" || fail publish-sync
	umount "$mountpoint" || fail unmount
	relock || fail relock
	[ "$(blockdev --getro "$userdata")" = 1 ] &&
		[ "$(blockdev --getro "$userdata_disk")" = 1 ] || fail relock-state
	printf 'format=rog5-local-image-direct-final-v1\nimage_size=%s\nextents=%s\nresult=PASS\n' \
		"$image_size" "$extent_count"
	emergency_bootloader
}

readiness
case ${1:-} in
	prepare) [ "$#" -eq 1 ] || fail arguments; prepare ;;
	write) [ "$#" -eq 2 ] || fail arguments; mounted_state; write_extent "$2" ;;
	finalize) [ "$#" -eq 1 ] || fail arguments; mounted_state; finalize ;;
	*) fail arguments ;;
esac
