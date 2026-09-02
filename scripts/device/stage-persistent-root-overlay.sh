#!/bin/sh
set -eu

export PATH=/usr/sbin:/usr/bin:/sbin:/bin

fail() {
	echo "FAIL $*" >&2
	exit 1
}

case ${1:-} in
	preflight|stage) action=$1 ;;
	*) fail 'usage: stage-persistent-root-overlay.sh preflight|stage' ;;
esac
[ "$#" -eq 1 ] || fail 'unexpected overlay staging arguments'

expected_boot_id=${EXPECTED_ROG5_BOOT_ID:-}
expected_bundle=${EXPECTED_ROG5_BUNDLE:-}
image_bytes=17179869184
image_uuid=f4834541-6e7a-4214-80d5-818fcc5cc252
image_label=ROG5_ROOT_RW_V1
userdata_uuid=0892bacf-3e02-41b0-84a4-5f05c2df7ce5
userdata_partuuid=8d82ef11-4d42-60e9-24e8-4d6ebf20491b
userdata_label=rog5-linux
userdata_start=18821440
userdata_size=408997568
disk_size=494927872
mountpoint=/.rog5/userdata-rw
image_mount=/run/rog5-root-overlay-stage
relative_partial=rog5/root/root-overlay-v1.ext4.partial
relative_final=rog5/root/root-overlay-v1.ext4
manifest_text='format=rog5-persistent-root-overlay-v1
image_bytes=17179869184
image_uuid=f4834541-6e7a-4214-80d5-818fcc5cc252
layout=upper,work'

[ "$(id -u)" -eq 0 ] || fail 'overlay staging requires root'
printf '%s\n' "$expected_boot_id" |
	grep -Eq '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$' ||
	fail 'EXPECTED_ROG5_BOOT_ID is invalid'
printf '%s\n' "$expected_bundle" |
	grep -Eq '^persistent-native-root-[a-z0-9]([a-z0-9-]*[a-z0-9])?$' ||
	fail 'EXPECTED_ROG5_BUNDLE is invalid'

for command in awk basename blkid blockdev cat chmod chown cut \
	dumpe2fs e2fsck find findmnt flock grep id losetup mkdir mkfs.ext4 \
	mount mountpoint mv readlink rmdir sed sha256sum stat sync systemctl \
	timeout truncate umount wc; do
	command -v "$command" >/dev/null || fail "missing staging command: $command"
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
			[ "$(cat "$sys_disk/queue/logical_block_size")" = 4096 ] || continue
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
	[ "$userdata_count" -eq 1 ] && [ "$exact_count" -eq 1 ] &&
		[ -b "$userdata" ] && [ -b "$userdata_disk" ]
}

verify_write_scope() {
	count=0
	writable=0
	for sys_block in /sys/class/block/sd*; do
		[ -e "$sys_block/dev" ] || continue
		device=/dev/$(basename "$sys_block")
		[ -b "$device" ] || return 1
		expected=1
		case $device in
			"$userdata_disk"|"$userdata") expected=0; writable=$((writable + 1)) ;;
		esac
		[ "$(blockdev --getro "$device")" = "$expected" ] &&
			[ "$(cat "$sys_block/ro")" = "$expected" ] || return 1
		count=$((count + 1))
	done
	[ "$count:$writable" = 117:2 ]
}

verify_power() {
	battery=/sys/class/power_supply/qcom-battmgr-bat
	usb=/sys/class/power_supply/qcom-battmgr-usb
	[ -d "$battery" ] && [ -d "$usb" ] || return 1
	case $(cat "$battery/status") in Full|Charging) ;; *) return 1 ;; esac
	[ "$(cat "$battery/health")" = Good ] && [ "$(cat "$usb/online")" = 1 ] ||
		return 1
	temperature=$(cat "$battery/temp") || return 1
	voltage=$(cat "$battery/voltage_now") || return 1
	case $temperature:$voltage in *[!0-9:]*) return 1 ;; esac
	[ "$temperature" -ge 0 ] && [ "$temperature" -lt 450 ] &&
		[ "$voltage" -ge 7600000 ] || return 1
	for path in /sys/class/thermal/thermal_zone*/temp; do
		[ -r "$path" ] || continue
		value=$(cat "$path") || continue
		case $value in ''|*[!0-9-]*) continue ;; esac
		[ "$value" -lt 65000 ] || return 1
	done
}

verify_userdata_filesystem() {
	record=$(blkid -p -o export "$userdata") || return 1
	[ "$(printf '%s\n' "$record" | sed -n 's/^TYPE=//p')" = ext4 ] &&
		[ "$(printf '%s\n' "$record" | sed -n 's/^UUID=//p')" = \
			"$userdata_uuid" ] &&
		[ "$(printf '%s\n' "$record" | sed -n 's/^LABEL=//p')" = \
			"$userdata_label" ]
}

verify_runtime_identity() {
	[ "$(cat /proc/sys/kernel/random/boot_id)" = "$expected_boot_id" ] || return 1
	running_bundle=$(sed -n 's/.*\<rog5.bundle=\([^ ]*\).*/\1/p' /proc/cmdline)
	[ "$running_bundle" = "$expected_bundle" ] || return 1
	systemctl is-system-running | grep -Fxq running || return 1
	systemctl is-active --quiet rog5-persistent-state.service || return 1
	[ "$(findmnt -n -o SOURCE --target "$mountpoint")" = "$userdata" ] &&
		[ "$(findmnt -n -o TARGET --target "$mountpoint")" = "$mountpoint" ] &&
		[ "$(findmnt -n -o FSTYPE --target "$mountpoint")" = ext4 ] || return 1
	findmnt -n -o OPTIONS --target "$mountpoint" |
		grep -Eq '(^|,)rw(,|$)' || return 1
	root_device=${userdata_disk}24
	[ "$(findmnt -n -o SOURCE --target /.rog5/root-ro)" = "$root_device" ] &&
		[ "$(findmnt -n -o FSTYPE --target /.rog5/root-ro)" = ext4 ] || return 1
	findmnt -n -o OPTIONS --target /.rog5/root-ro |
		grep -Eq '(^|,)ro(,|$)' || return 1
}

resolve_userdata || fail 'exact p23 userdata is unavailable'
verify_userdata_filesystem || fail 'p23 filesystem identity changed'
verify_write_scope || fail 'runtime storage write scope changed'
verify_runtime_identity || fail 'accepted runtime identity changed'
verify_power || fail 'power or thermal gate failed'

if [ "$action" = preflight ]; then
	printf 'format=rog5-persistent-root-overlay-preflight-v1\nuserdata=%s\nimage=%s\nimage_bytes=%s\nresult=PASS\n' \
		"$userdata" "$relative_final" "$image_bytes"
	exit 0
fi

[ "${ALLOW_ROG5_ROOT_OVERLAY_STAGE:-}" = 1 ] || fail 'overlay staging is not armed'
exec 9>/run/rog5-root-overlay-stage.lock
flock -n 9 || fail 'another overlay staging operation holds the lock'
[ ! -e "$mountpoint/$relative_final" ] &&
	[ ! -L "$mountpoint/$relative_final" ] || fail 'overlay image already exists'
[ "$(stat -c '%u:%g:%a' "$mountpoint/rog5")" = 0:0:700 ] ||
	fail 'rog5 directory metadata changed'

root_dir=$mountpoint/rog5/root
if [ -e "$root_dir" ] || [ -L "$root_dir" ]; then
	[ -d "$root_dir" ] && [ ! -L "$root_dir" ] &&
		[ "$(stat -c '%u:%g:%a' "$root_dir")" = 0:0:700 ] ||
		fail 'root overlay directory metadata changed'
	inventory=$(find "$root_dir" -mindepth 1 -maxdepth 1 -print |
		sed 's#.*/##')
	case $inventory in ''|root-overlay-v1.ext4.partial) ;; *) fail 'root overlay inventory changed' ;; esac
else
	mkdir -m 0700 "$root_dir"
fi

if [ -e "$mountpoint/$relative_partial" ] || [ -L "$mountpoint/$relative_partial" ]; then
	metadata=$(stat -c '%u:%g:%a:%h:%s:%b' "$mountpoint/$relative_partial") ||
		fail 'partial overlay metadata unavailable'
	[ "$metadata" = "0:0:600:1:$image_bytes:0" ] ||
		fail 'existing partial overlay is not empty'
	blkid -p "$mountpoint/$relative_partial" >/dev/null 2>&1 &&
		fail 'existing partial overlay has a filesystem'
	truncate -s 0 "$mountpoint/$relative_partial"
	partial_mode=resume
else
	set -C
	: >"$mountpoint/$relative_partial"
	set +C
	partial_mode=new
fi
chmod 0600 "$mountpoint/$relative_partial"
truncate -s "$image_bytes" "$mountpoint/$relative_partial"
[ "$(stat -c '%u:%g:%a:%h:%s' "$mountpoint/$relative_partial")" = \
	"0:0:600:1:$image_bytes" ] || fail 'partial overlay metadata changed'

mkfs.ext4 -q -F -m 1 -L "$image_label" -U "$image_uuid" \
	-E "hash_seed=$image_uuid,lazy_itable_init=0,lazy_journal_init=0" \
	"$mountpoint/$relative_partial"

loop_device=$(losetup -f)
case $loop_device in /dev/loop[0-9]*) ;; *) fail 'unsafe loop device' ;; esac
mounted=0
cleanup() {
	status=$?
	trap - EXIT HUP INT TERM
	[ "$mounted" -eq 0 ] || umount "$image_mount" || status=1
	[ -z "$loop_device" ] || losetup -d "$loop_device" 2>/dev/null || status=1
	rmdir "$image_mount" 2>/dev/null || true
	exit "$status"
}
trap cleanup EXIT HUP INT TERM
losetup "$loop_device" "$mountpoint/$relative_partial"
[ "$(blockdev --getsize64 "$loop_device")" = "$image_bytes" ] ||
	fail 'overlay loop size changed'
mkdir -m 0700 "$image_mount"
mount -t ext4 -o rw,nodev,nosuid,noexec,noatime "$loop_device" "$image_mount"
mounted=1
mkdir -m 0700 "$image_mount/upper" "$image_mount/work"
printf '%s\n' "$manifest_text" >"$image_mount/rog5-root-overlay.manifest"
chown 0:0 "$image_mount/rog5-root-overlay.manifest"
chmod 0444 "$image_mount/rog5-root-overlay.manifest"
[ "$(stat -c %s "$image_mount/rog5-root-overlay.manifest")" = 129 ] &&
	[ "$(sha256sum "$image_mount/rog5-root-overlay.manifest" | cut -d ' ' -f 1)" = \
		e894abd56cccdfce9ce3292438df022aa9672a8655cac6493b94cfd19d6bad5f ] ||
	fail 'overlay manifest identity changed'
sync -f "$image_mount/rog5-root-overlay.manifest"
umount "$image_mount"
mounted=0
losetup -d "$loop_device"
loop_device=
timeout -k 5 180 e2fsck -fn "$mountpoint/$relative_partial" \
	>/run/rog5-root-overlay-e2fsck.log 2>&1 || fail 'overlay image is not clean'
mv -T "$mountpoint/$relative_partial" "$mountpoint/$relative_final"
sync -f "$root_dir"
verify_write_scope || fail 'write scope changed after overlay staging'

trap - EXIT HUP INT TERM
rmdir "$image_mount" 2>/dev/null || true
printf 'format=rog5-persistent-root-overlay-stage-v1\nuserdata=%s\nimage=%s\nimage_bytes=%s\nimage_uuid=%s\npartial_mode=%s\nresult=PASS\n' \
	"$userdata" "$relative_final" "$image_bytes" "$image_uuid" "$partial_mode"
