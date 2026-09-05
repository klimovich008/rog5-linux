#!/bin/sh
set -eu

export PATH=/sbin:/bin:/usr/sbin:/usr/bin
status=/run/rog5-local-image-stage.status
userdata_record=/run/rog5-userdata-device
reboot_helper=/usr/libexec/rog5-reboot-bootloader
source_mount=/mnt/userdata
source_image=$source_mount/rog5/images/arch-local-a.ext4
softdog_module=/rog5-softdog-modules/softdog.ko
source_bytes=17179869184
probe_offset_blocks=1464081
probe_block_count=27204
probe_chunk_blocks=1024
block_bytes=4096
source_segment=/run/rog5-native-progress-source.segment
source_chunk=/run/rog5-native-progress-source.chunk
target_chunk=/run/rog5-native-progress-target.chunk
userdata_mounted=0
disk=
userdata=
arch_root=

log() {
	echo "rog5-native-progress: $*" >/dev/kmsg 2>/dev/null || true
}

cleanup() {
	result=0
	if [ "$userdata_mounted" -eq 1 ]; then
		umount "$source_mount" >/dev/null 2>&1 || result=1
		userdata_mounted=0
	fi
	rm -f "$source_segment" "$source_chunk" "$target_chunk"
	return "$result"
}

return_bootloader() {
	trap - EXIT HUP INT TERM
	cleanup || true
	"$reboot_helper" >/dev/null 2>&1 &
	sleep 3
	printf b >/proc/sysrq-trigger
	while :; do sleep 3600; done
}

fail() {
	reason=$1
	log "FAIL $reason"
	printf 'ROG5_NATIVE_PROGRESS_V1 stage=terminal status=FAIL reason=%s\n' \
		"$reason"
	return_bootloader
}
trap 'fail interrupted' HUP INT TERM

is_integer() {
	value=$1
	case $value in ''|-) return 1 ;; -*) value=${value#-} ;; esac
	case $value in ''|*[!0-9]*) return 1 ;; esac
}

verify_power_thermal() {
	battery=/sys/class/power_supply/qcom-battmgr-bat
	usb=/sys/class/power_supply/qcom-battmgr-usb
	[ -r "$battery/type" ] && [ "$(cat "$battery/type")" = Battery ] ||
		return 1
	for property in temp voltage_now; do
		value=$(cat "$battery/$property") || return 1
		is_integer "$value" || return 1
		case $property in
			temp) [ "$value" -ge 0 ] && [ "$value" -lt 550 ] || return 1 ;;
			voltage_now)
				[ "$value" -ge 7400000 ] && [ "$value" -lt 9000000 ] ||
					return 1
				;;
		esac
	done
	[ "$(cat "$usb/online")" = 1 ] || return 1
	usb_current=$(cat "$usb/current_now") || return 1
	is_integer "$usb_current" && [ "$usb_current" -gt 0 ] || return 1
	thermal_count=0
	for path in /sys/class/thermal/thermal_zone*/temp; do
		[ -r "$path" ] || continue
		value=$(cat "$path") || return 1
		is_integer "$value" || return 1
		[ "$value" -ge -40000 ] && [ "$value" -lt 65000 ] || return 1
		thermal_count=$((thermal_count + 1))
	done
	[ "$thermal_count" -eq 30 ]
}

resolve_storage() {
	matches=0
	for sys_disk in /sys/class/block/sd[a-z]; do
		[ -e "$sys_disk/device" ] && [ ! -e "$sys_disk/partition" ] ||
			continue
		[ "$(cat "$sys_disk/size")" = 494927872 ] || continue
		[ "$(cat "$sys_disk/queue/logical_block_size")" = 4096 ] ||
			continue
		name=$(basename "$sys_disk")
		candidate_userdata=
		candidate_root=
		for part in "$sys_disk"/"$name"*; do
			[ -e "$part/partition" ] || continue
			partname=$(sed -n 's/^PARTNAME=//p' "$part/uevent" | sed -n '1p')
			case $(cat "$part/partition"):$partname in
				23:userdata)
					[ "$(cat "$part/start")" = 18821440 ] || continue
					[ "$(cat "$part/size")" = 408997568 ] || continue
					candidate_userdata=/dev/$(basename "$part")
					;;
				24:arch_root_a)
					[ "$(cat "$part/start")" = 427819008 ] || continue
					[ "$(cat "$part/size")" = 67108824 ] || continue
					candidate_root=/dev/$(basename "$part")
					;;
			esac
		done
		[ -n "$candidate_userdata" ] && [ -n "$candidate_root" ] || continue
		disk=/dev/$name
		userdata=$candidate_userdata
		arch_root=$candidate_root
		matches=$((matches + 1))
	done
	[ "$matches" -eq 1 ] && [ -b "$disk" ] && [ -b "$userdata" ] &&
		[ -b "$arch_root" ] || return 1
	[ "$(blockdev --getsize64 "$disk")" = 253403070464 ] &&
		[ "$(blockdev --getsize64 "$userdata")" = 209406754816 ] &&
		[ "$(blockdev --getsize64 "$arch_root")" = 34359717888 ]
}

verify_mount_count() {
	expected=$1
	count=0
	while read -r _ _ device _ _ _ rest; do
		[ -e "/sys/dev/block/$device" ] || continue
		count=$((count + 1))
	done </proc/self/mountinfo
	[ "$count" -eq "$expected" ]
}

verify_read_only() {
	count=0
	for sys_disk in /sys/class/block/*; do
		[ -e "$sys_disk/device" ] && [ ! -e "$sys_disk/partition" ] ||
			continue
		name=$(basename "$sys_disk")
		for sys_block in "$sys_disk" "$sys_disk"/"$name"*; do
			[ -e "$sys_block/dev" ] || continue
			[ "$sys_block" = "$sys_disk" ] ||
				[ -e "$sys_block/partition" ] || continue
			[ "$(blockdev --getro "/dev/$(basename "$sys_block")")" = 1 ] ||
				return 1
			count=$((count + 1))
		done
	done
	[ "$count" -eq 117 ]
}

read_range() {
	input=$1 output=$2 offset_blocks=$3 count_blocks=$4 stats=$5
	offset_bytes=$((offset_blocks * block_bytes))
	count_bytes=$((count_blocks * block_bytes))
	rm -f "$output" "$stats"
	dd if="$input" of="$output" ibs=1048576 obs=1048576 \
		skip="$offset_bytes" count="$count_bytes" \
		iflag=skip_bytes,count_bytes,fullblock conv=notrunc \
		status=noxfer 2>"$stats" || return 1
	[ -f "$output" ] && [ ! -L "$output" ] &&
		[ "$(stat -c %s "$output")" -eq "$count_bytes" ]
}

[ "$#" -eq 0 ] || fail arguments
[ "$(id -u)" -eq 0 ] || fail not-root
[ "$(cat "$status")" = "$(printf 'state=READY\nuserdata=%s\nstorage=read-only\nssh=key-only' "$(cat "$userdata_record")")" ] ||
	fail readiness
resolve_storage || fail storage-identity
[ "$(cat "$userdata_record")" = "$userdata" ] || fail userdata-record
verify_mount_count 0 || fail preinspect-mounts
verify_read_only || fail preinspect-locks
verify_power_thermal || fail power-thermal
[ -f "$softdog_module" ] && [ ! -L "$softdog_module" ] ||
	fail softdog-module

mkdir -p "$source_mount"
mount -t ext4 -o ro,noload,nodev,nosuid,noexec,noatime \
	"$userdata" "$source_mount" || fail userdata-mount
userdata_mounted=1
verify_mount_count 1 || fail userdata-mount-scope
[ -f "$source_image" ] && [ ! -L "$source_image" ] &&
	[ "$(stat -c '%u:%g:%a:%s:%h' "$source_image")" = \
		"0:0:600:$source_bytes:1" ] || fail source-metadata

[ "$(find /sys/class/watchdog -mindepth 1 -maxdepth 1 -name 'watchdog*' |
	wc -l)" -eq 0 ] || fail softdog-preexisting
insmod "$softdog_module" soft_margin=840 soft_reboot_cmd=bootloader \
	nowayout=0 soft_noboot=0 soft_panic=0 || fail softdog-insmod
grep -q '^softdog ' /proc/modules || fail softdog-module-state
attempt=0
while [ "$attempt" -lt 50 ]; do
	[ -c /dev/watchdog0 ] && break
	attempt=$((attempt + 1))
	sleep 0.1
done
[ -c /dev/watchdog0 ] || fail softdog-device
exec 9>/dev/watchdog0 || fail softdog-open
printf '\0' >&9 || fail softdog-arm
printf '%s\n' 'ROG5_NATIVE_PROGRESS_V1 stage=watchdog status=ARMED'

printf 'ROG5_NATIVE_PROGRESS_V1 stage=source status=BEGIN offset=%s blocks=%s\n' \
	"$probe_offset_blocks" "$probe_block_count"
read_range "$source_image" "$source_segment" "$probe_offset_blocks" \
	"$probe_block_count" /run/rog5-native-progress-source.stats ||
	fail source-read
source_sha=$(sha256sum "$source_segment" | awk '{print $1}') ||
	fail source-hash
printf 'ROG5_NATIVE_PROGRESS_V1 stage=source status=PASS offset=%s blocks=%s sha256=%s\n' \
	"$probe_offset_blocks" "$probe_block_count" "$source_sha"

printf 'ROG5_NATIVE_PROGRESS_V1 stage=target status=BEGIN offset=%s blocks=%s\n' \
	"$probe_offset_blocks" "$probe_block_count"
relative=0
matched=0
chunk=0
mismatch_offset=none
mismatch_blocks=0
while [ "$relative" -lt "$probe_block_count" ]; do
	blocks=$probe_chunk_blocks
	remaining=$((probe_block_count - relative))
	[ "$remaining" -ge "$blocks" ] || blocks=$remaining
	offset=$((probe_offset_blocks + relative))
	read_range "$arch_root" "$target_chunk" "$offset" "$blocks" \
		/run/rog5-native-progress-target.stats || fail target-read
	read_range "$source_segment" "$source_chunk" "$relative" "$blocks" \
		/run/rog5-native-progress-source-chunk.stats || fail source-chunk-read
	source_chunk_sha=$(sha256sum "$source_chunk" | awk '{print $1}') ||
		fail source-chunk-hash
	target_sha=$(sha256sum "$target_chunk" | awk '{print $1}') ||
		fail target-hash
	if cmp "$source_chunk" "$target_chunk" >/dev/null 2>&1; then
		matched=$((matched + blocks))
		printf 'ROG5_NATIVE_PROGRESS_V1 stage=target status=MATCH chunk=%s offset=%s blocks=%s sha256=%s\n' \
			"$chunk" "$offset" "$blocks" "$target_sha"
	else
		mismatch_offset=$offset
		mismatch_blocks=$blocks
		printf 'ROG5_NATIVE_PROGRESS_V1 stage=target status=MISMATCH chunk=%s offset=%s blocks=%s matched_blocks=%s source_sha256=%s target_sha256=%s\n' \
			"$chunk" "$offset" "$blocks" "$matched" \
			"$source_chunk_sha" "$target_sha"
		break
	fi
	relative=$((relative + blocks))
	chunk=$((chunk + 1))
done

verify_power_thermal || fail final-power-thermal
verify_mount_count 1 || fail final-mount-scope
resolve_storage && verify_read_only || fail final-identity
printf V >&9 || fail softdog-disarm
exec 9>&-
printf '%s\n' 'ROG5_NATIVE_PROGRESS_V1 stage=watchdog status=DISARMED'

disposition=partial
[ "$matched" -eq "$probe_block_count" ] && disposition=all-matched
printf 'ROG5_NATIVE_PROGRESS_V1 stage=terminal status=PASS disposition=%s source_sha256=%s matched_blocks=%s mismatch_offset=%s mismatch_blocks=%s all_read_only=1\n' \
	"$disposition" "$source_sha" "$matched" "$mismatch_offset" \
	"$mismatch_blocks"
return_bootloader
