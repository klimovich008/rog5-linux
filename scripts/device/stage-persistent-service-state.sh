#!/bin/sh
set -eu

export PATH=/sbin:/bin:/usr/sbin:/usr/bin

fail() {
	echo "FAIL $*" >&2
	exit 1
}

case ${1:-} in
	preflight|stage) action=$1 ;;
	*) fail 'usage: stage-persistent-service-state.sh preflight|stage' ;;
esac
[ "$#" -eq 1 ] || fail 'unexpected service-state staging arguments'

image_bytes=4294967296
image_uuid=52037413-561a-48f4-92c4-8ad45b748a6f
image_label=ROG5_STATE_V1
userdata_uuid=0892bacf-3e02-41b0-84a4-5f05c2df7ce5
userdata_partuuid=8d82ef11-4d42-60e9-24e8-4d6ebf20491b
userdata_label=rog5-linux
userdata_start=18821440
userdata_size=408997568
disk_size=494927872
mountpoint=/run/rog5-service-state-userdata
state_mount=/run/rog5-service-state-image
relative_partial=rog5/state/server-state-v1.ext4.partial
relative_final=rog5/state/server-state-v1.ext4
manifest_text='format=rog5-persistent-service-state-v1
image_bytes=4294967296
image_uuid=52037413-561a-48f4-92c4-8ad45b748a6f
layout=home,root,var-lib,var-log,etc-ssh,secrets'

[ "$(id -u)" -eq 0 ] || fail 'service-state staging requires root'
for command in awk basename blkid blockdev cat chmod chown cut \
	dumpe2fs e2fsck find flock grep id losetup mkdir mkfs.ext4 mount \
	mountpoint mv readlink rmdir sed sha256sum stat sync timeout \
	truncate umount wc; do
	command -v "$command" >/dev/null ||
		fail "missing service-state command: $command"
done

resolve_userdata() {
	userdata_count=0
	exact_count=0
	userdata=
	userdata_disk=
	for sys_disk in /sys/class/block/*; do
		[ -e "$sys_disk/device" ] || continue
		[ ! -e "$sys_disk/partition" ] || continue
		disk=$(basename "$sys_disk")
		case $disk in sd[a-z]) ;; *) continue ;; esac
		for sys_block in "$sys_disk"/"$disk"*; do
			[ -e "$sys_block/partition" ] || continue
			name=$(sed -n 's/^PARTNAME=//p' "$sys_block/uevent" |
				sed -n '1p')
			[ "$name" = userdata ] || continue
			userdata_count=$((userdata_count + 1))
			block=$(basename "$sys_block")
			[ "$block" = "${disk}23" ] || continue
			[ "$(cat "$sys_disk/size")" = "$disk_size" ] || continue
			[ "$(cat "$sys_disk/queue/logical_block_size")" = 4096 ] ||
				continue
			[ "$(cat "$sys_block/partition")" = 23 ] || continue
			[ "$(cat "$sys_block/start")" = "$userdata_start" ] || continue
			[ "$(cat "$sys_block/size")" = "$userdata_size" ] || continue
			partuuid=$(sed -n 's/^PARTUUID=//p' "$sys_block/uevent" |
				sed -n '1p')
			[ "$partuuid" = "$userdata_partuuid" ] || continue
			exact_count=$((exact_count + 1))
			userdata=/dev/$block
			userdata_disk=/dev/$disk
		done
	done
	[ "$userdata_count" -eq 1 ] && [ "$exact_count" -eq 1 ] || return 1
	[ -b "$userdata" ] && [ -b "$userdata_disk" ]
}

all_storage_read_only() {
	found=0
	for sys_block in /sys/class/block/sd*; do
		[ -e "$sys_block/dev" ] || continue
		device=/dev/$(basename "$sys_block")
		[ -b "$device" ] || return 1
		[ "$(blockdev --getro "$device")" = 1 ] || return 1
		found=$((found + 1))
	done
	[ "$found" -eq 117 ]
}

verify_existing_root_mount() {
	root_device=${userdata_disk}24
	[ -b "$root_device" ] || return 1
	awk -v expected="$root_device" '
	$1 ~ "^/dev/sd" {
		count++
		if ($1 != expected || $2 != "/.rog5/root-ro" || $3 != "ext4" ||
		    $4 !~ /(^|,)ro(,|$)/ || $4 !~ /(^|,)norecovery(,|$)/)
			exit 1
	}
	END { exit count != 1 }' /proc/mounts
}

relock_storage() {
	status=0
	for sys_block in /sys/class/block/sd*; do
		[ -e "$sys_block/dev" ] || continue
		device=/dev/$(basename "$sys_block")
		[ -b "$device" ] || { status=1; continue; }
		blockdev --setro "$device" || status=1
	done
	return "$status"
}

verify_power() {
	battery=/sys/class/power_supply/qcom-battmgr-bat
	usb=/sys/class/power_supply/qcom-battmgr-usb
	[ -d "$battery" ] && [ -d "$usb" ] || return 1
	case $(cat "$battery/status") in Full|Charging) ;; *) return 1 ;; esac
	[ "$(cat "$usb/online")" = 1 ] || return 1
	for path in "$battery/temp" "$battery/voltage_now" "$usb/current_now"; do
		value=$(cat "$path") || return 1
		case $value in ''|*[!0-9-]*) return 1 ;; esac
	done
	temperature=$(cat "$battery/temp")
	voltage=$(cat "$battery/voltage_now")
	current=$(cat "$usb/current_now")
	[ "$temperature" -ge 0 ] && [ "$temperature" -lt 450 ] &&
		[ "$voltage" -ge 8400000 ] && [ "$current" -ge 0 ] || return 1
	thermal_max=0
	for path in /sys/class/thermal/thermal_zone*/temp; do
		[ -r "$path" ] || continue
		value=$(cat "$path")
		case $value in ''|*[!0-9-]*) continue ;; esac
		[ "$value" -gt "$thermal_max" ] && thermal_max=$value
	done
	[ "$thermal_max" -lt 65000 ]
}

verify_userdata_filesystem() {
	record=$(blkid -p -o export "$userdata") || return 1
	type=$(printf '%s\n' "$record" | sed -n 's/^TYPE=//p')
	uuid=$(printf '%s\n' "$record" | sed -n 's/^UUID=//p')
	label=$(printf '%s\n' "$record" | sed -n 's/^LABEL=//p')
	[ "$type" = ext4 ] && [ "$uuid" = "$userdata_uuid" ] &&
		[ "$label" = "$userdata_label" ] || return 1
	header=$(dumpe2fs -h "$userdata" 2>/dev/null) || return 1
	[ "$(printf '%s\n' "$header" |
		sed -n 's/^Filesystem state:[[:space:]]*//p')" = clean ] &&
		[ "$(printf '%s\n' "$header" |
		sed -n 's/^Block count:[[:space:]]*//p')" = 51124000 ] &&
		[ "$(printf '%s\n' "$header" |
		sed -n 's/^Block size:[[:space:]]*//p')" = 4096 ] || return 1
	free=$(printf '%s\n' "$header" |
		sed -n 's/^Free blocks:[[:space:]]*//p')
	case $free in ''|*[!0-9]*) return 1 ;; esac
	[ "$free" -ge 2097152 ]
}

resolve_userdata || fail 'exact userdata partition is unavailable'
verify_existing_root_mount || fail 'physical root mount identity changed'
all_storage_read_only || fail 'storage is not fully read-only before staging'
verify_userdata_filesystem || fail 'userdata ext4 identity changed'
verify_power || fail 'power or thermal gate failed'

if [ "$action" = preflight ]; then
	printf 'format=rog5-persistent-service-state-preflight-v1\nuserdata=%s\nimage=%s\nimage_bytes=%s\nresult=PASS\n' \
		"$userdata" "$relative_final" "$image_bytes"
	exit 0
fi

[ "${ALLOW_ROG5_SERVICE_STATE_STAGE:-}" = 1 ] ||
	fail 'service-state staging is not armed'
exec 9>/run/rog5-service-state-stage.lock
flock -n 9 || fail 'another service-state staging operation holds the lock'

userdata_mounted=0
state_mounted=0
loop_device=
cleanup() {
	status=$?
	trap - EXIT HUP INT TERM
	if [ "$state_mounted" -eq 1 ]; then
		umount "$state_mount" || status=1
	fi
	if [ -n "$loop_device" ]; then
		losetup -d "$loop_device" || status=1
	fi
	if [ "$userdata_mounted" -eq 1 ]; then
		sync -f "$mountpoint" 2>/dev/null || status=1
		umount "$mountpoint" || status=1
	fi
	relock_storage || status=1
	rmdir "$state_mount" "$mountpoint" 2>/dev/null || true
	exit "$status"
}
trap cleanup EXIT HUP INT TERM

blockdev --setrw "$userdata_disk"
for sys_block in /sys/class/block/sd*; do
	[ -e "$sys_block/dev" ] || continue
	device=/dev/$(basename "$sys_block")
	[ "$device" = "$userdata_disk" ] && continue
	blockdev --setro "$device"
done
blockdev --setrw "$userdata"
[ "$(blockdev --getro "$userdata_disk")" = 0 ] &&
	[ "$(blockdev --getro "$userdata")" = 0 ] ||
	fail 'userdata write window did not open'
for sys_block in /sys/class/block/sd*; do
	[ -e "$sys_block/dev" ] || continue
	device=/dev/$(basename "$sys_block")
	[ "$device" = "$userdata_disk" ] && continue
	[ "$device" = "$userdata" ] && continue
	[ "$(blockdev --getro "$device")" = 1 ] ||
		fail 'write window exposed another partition'
done

mkdir -m 0700 "$mountpoint"
mount -t ext4 -o rw,nodev,nosuid,noexec,noatime "$userdata" "$mountpoint"
userdata_mounted=1
awk -v device="$userdata" -v target="$mountpoint" '
$1 == device && $2 == target && $3 == "ext4" &&
$4 ~ /(^|,)rw(,|$)/ && $4 ~ /(^|,)nodev(,|$)/ &&
$4 ~ /(^|,)nosuid(,|$)/ && $4 ~ /(^|,)noexec(,|$)/ { count++ }
END { exit count != 1 }' /proc/mounts || fail 'userdata mount identity changed'
[ "$(stat -c '%u:%g:%a' "$mountpoint/rog5")" = 0:0:700 ] ||
	fail 'userdata rog5 directory metadata changed'
[ -d "$mountpoint/rog5/images" ] &&
	[ ! -L "$mountpoint/rog5/images" ] || fail 'userdata image store changed'
[ ! -e "$mountpoint/$relative_final" ] &&
	[ ! -L "$mountpoint/$relative_final" ] || fail 'state image already exists'
state_dir=$mountpoint/rog5/state
if [ -e "$state_dir" ] || [ -L "$state_dir" ]; then
	[ -d "$state_dir" ] && [ ! -L "$state_dir" ] &&
		[ "$(stat -c '%u:%g:%a' "$state_dir")" = 0:0:700 ] ||
		fail 'state directory metadata changed'
	inventory=$(find "$state_dir" -mindepth 1 -maxdepth 1 -printf '%f\n')
	case $inventory in ''|server-state-v1.ext4.partial) ;;
		*) fail 'state directory inventory changed' ;;
	esac
else
	mkdir -m 0700 "$state_dir"
fi
if [ -e "$mountpoint/$relative_partial" ] ||
	[ -L "$mountpoint/$relative_partial" ]; then
	metadata=$(stat -c '%u:%g:%a:%h:%s:%b' \
		"$mountpoint/$relative_partial") || fail 'partial metadata unavailable'
	[ "$metadata" = "0:0:600:1:$image_bytes:0" ] ||
		fail 'existing partial state image is not empty'
	if blkid -p "$mountpoint/$relative_partial" >/dev/null 2>&1; then
		fail 'existing partial state image has a filesystem'
	fi
	partial_mode=resume
	truncate -s 0 "$mountpoint/$relative_partial"
else
	set -C
	: >"$mountpoint/$relative_partial"
	set +C
	partial_mode=new
fi
chmod 0600 "$mountpoint/$relative_partial"
truncate -s "$image_bytes" "$mountpoint/$relative_partial"
metadata=$(stat -c '%u:%g:%a:%h:%s' "$mountpoint/$relative_partial") ||
	fail 'partial state image metadata unavailable'
[ "$metadata" = "0:0:600:1:$image_bytes" ] ||
	fail 'partial state image metadata changed'
mkfs.ext4 -q -F -m 1 -L "$image_label" -U "$image_uuid" \
	-E "hash_seed=$image_uuid,lazy_itable_init=0,lazy_journal_init=0" \
	"$mountpoint/$relative_partial"

loop_device=$(losetup -f)
case $loop_device in /dev/loop[0-9]*) ;; *) fail 'unsafe loop device' ;; esac
losetup "$loop_device" "$mountpoint/$relative_partial"
[ "$(blockdev --getsize64 "$loop_device")" = "$image_bytes" ] ||
	fail 'state loop size changed'
loop_name=${loop_device##*/}
backing=$(cat "/sys/class/block/$loop_name/loop/backing_file") ||
	fail 'state loop backing file is unavailable'
case $backing in
	/rog5/state/server-state-v1.ext4.partial|\
	rog5/state/server-state-v1.ext4.partial|\
	/run/rog5-service-state-userdata/rog5/state/server-state-v1.ext4.partial|\
	run/rog5-service-state-userdata/rog5/state/server-state-v1.ext4.partial) ;;
	*) fail 'state loop backing file changed' ;;
esac
mkdir -m 0700 "$state_mount"
mount -t ext4 -o rw,nodev,nosuid,noexec,noatime "$loop_device" "$state_mount"
state_mounted=1
mkdir -m 0755 "$state_mount/home" "$state_mount/var" \
	"$state_mount/var/lib" "$state_mount/var/log" "$state_mount/etc"
mkdir -m 0700 "$state_mount/root" "$state_mount/etc/ssh" \
	"$state_mount/secrets"
mkdir -m 2755 "$state_mount/var/log/journal"
printf '%s\n' "$manifest_text" >"$state_mount/rog5-state.manifest"
chown 0:0 "$state_mount/rog5-state.manifest"
chmod 0444 "$state_mount/rog5-state.manifest"
sync -f "$state_mount/rog5-state.manifest"
umount "$state_mount"
state_mounted=0
losetup -d "$loop_device"
loop_device=
timeout -k 5 180 e2fsck -fn "$mountpoint/$relative_partial" \
	>/run/rog5-service-state-e2fsck.log 2>&1 || fail 'state image is not clean'
mv -T "$mountpoint/$relative_partial" "$mountpoint/$relative_final"
sync -f "$mountpoint/rog5/state"
umount "$mountpoint"
userdata_mounted=0
relock_storage || fail 'storage relock failed'
all_storage_read_only || fail 'storage did not return read-only'

printf 'format=rog5-persistent-service-state-stage-v1\nuserdata=%s\nimage=%s\nimage_bytes=%s\nimage_uuid=%s\npartial_mode=%s\nresult=PASS\n' \
	"$userdata" "$relative_final" "$image_bytes" "$image_uuid" \
	"$partial_mode"
