#!/bin/sh
set -eu

export PATH=/sbin:/bin:/usr/sbin:/usr/bin
status=/run/rog5-local-image-stage.status
userdata_record=/run/rog5-userdata-device
reboot_helper=/usr/libexec/rog5-reboot-bootloader
source_mount=/mnt/userdata
source_verify_mount=/mnt/source-root
target_mount=/mnt/native-root
source_image=$source_mount/rog5/images/arch-local-a.ext4
native_seal=/etc/rog5/native-root-v1.seal
hardware_watchdog=/run/rog5-hardware-watchdog.status
verifier=/usr/local/sbin/persistent-root-verify
source_bytes=17179869184
source_blocks=4194304
source_uuid=598a876b-a8db-4859-a01a-1b864b0a87f4
target_blocks=8388603
target_uuid=8b03827a-cc2d-4408-8558-e9b61195f96b
native_seal_sha256=02231e86746fbc656090f52c96d7e0c968c7ca86ba7449c306f611ea20c6a876
userdata_mounted=0
source_mounted=0
source_loop_attached=0
target_mounted=0
source_loop=
disk=
userdata=
arch_root=

log() { echo "rog5-native-clone: $*" >/dev/kmsg 2>/dev/null || true; }
emit() { printf 'ROG5_NATIVE_CLONE_V1 stage=%s status=%s\n' "$1" "$2"; }

relock() {
	result=0
	for sys_block in /sys/class/block/*; do
		[ -e "$sys_block/dev" ] || continue
		device=/dev/$(basename "$sys_block")
		[ -b "$device" ] || continue
		blockdev --setro "$device" >/dev/null 2>&1 || result=1
	done
	return "$result"
}

cleanup() {
	result=0
	if [ "$source_mounted" -eq 1 ]; then
		umount "$source_verify_mount" >/dev/null 2>&1 || result=1
		source_mounted=0
	fi
	if [ "$source_loop_attached" -eq 1 ]; then
		losetup -d "$source_loop" >/dev/null 2>&1 || result=1
		source_loop_attached=0
	fi
	if [ "$target_mounted" -eq 1 ]; then
		umount "$target_mount" >/dev/null 2>&1 || result=1
		target_mounted=0
	fi
	if [ "$userdata_mounted" -eq 1 ]; then
		umount "$source_mount" >/dev/null 2>&1 || result=1
		userdata_mounted=0
	fi
	relock || result=1
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
	printf 'ROG5_NATIVE_CLONE_V1 stage=terminal status=FAIL reason=%s\n' "$reason"
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
	[ -r "$battery/type" ] && [ "$(cat "$battery/type")" = Battery ] || return 1
	for property in temp voltage_now; do
		value=$(cat "$battery/$property") || return 1
		is_integer "$value" || return 1
		case $property in
			temp) [ "$value" -ge 0 ] && [ "$value" -lt 550 ] || return 1 ;;
			voltage_now) [ "$value" -ge 7400000 ] && [ "$value" -lt 9000000 ] || return 1 ;;
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
		[ -e "$sys_disk/device" ] && [ ! -e "$sys_disk/partition" ] || continue
		[ "$(cat "$sys_disk/size")" = 494927872 ] || continue
		[ "$(cat "$sys_disk/queue/logical_block_size")" = 4096 ] || continue
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

verify_lock_state() {
	expected_writable=$1
	count=0
	writable=0
	for sys_disk in /sys/class/block/*; do
		[ -e "$sys_disk/device" ] && [ ! -e "$sys_disk/partition" ] || continue
		name=$(basename "$sys_disk")
		for sys_block in "$sys_disk" "$sys_disk"/"$name"*; do
			[ -e "$sys_block/dev" ] || continue
			[ "$sys_block" = "$sys_disk" ] || [ -e "$sys_block/partition" ] || continue
			device=/dev/$(basename "$sys_block")
			ro=$(blockdev --getro "$device") || return 1
			if [ "$ro" -eq 0 ]; then
				case $device in "$disk"|"$arch_root") writable=$((writable + 1)) ;; *) return 1 ;; esac
			fi
			count=$((count + 1))
		done
	done
	[ "$count" -eq 117 ] && [ "$writable" -eq "$expected_writable" ]
}

fs_value() { sed -n "s/^$1:[[:space:]]*//p" "$2" | sed -n '1p'; }
verify_ext4() {
	device=$1 uuid=$2 blocks=$3 output=$4
	dumpe2fs -h "$device" >"$output" 2>&1 || return 1
	[ "$(fs_value 'Filesystem state' "$output")" = clean ] &&
		[ "$(fs_value 'Block size' "$output")" = 4096 ] &&
		[ "$(fs_value 'Block count' "$output")" = "$blocks" ] &&
		[ "$(fs_value 'Filesystem UUID' "$output" | tr A-F a-f)" = "$uuid" ] &&
		[ "$(fs_value 'Filesystem volume name' "$output")" = ROG5_ARCH_A ]
}

[ "$#" -eq 0 ] || fail arguments
[ "$(id -u)" -eq 0 ] || fail not-root
[ "$(cat "$status")" = "$(printf 'state=READY\nuserdata=%s\nstorage=read-only\nssh=key-only' "$(cat "$userdata_record")")" ] || fail readiness
resolve_storage || fail storage-identity
[ "$(cat "$userdata_record")" = "$userdata" ] || fail userdata-record
verify_mount_count 0 || fail prewrite-mounts
verify_lock_state 0 || fail prewrite-locks
verify_power_thermal || fail power-thermal
[ -x "$verifier" ] && [ ! -L "$verifier" ] || fail verifier
[ -f "$hardware_watchdog" ] && [ ! -L "$hardware_watchdog" ] || fail hardware-watchdog
for marker in \
	'format=rog5-hardware-watchdog-v1' \
	'state=ARMED' \
	'driver=qcom_wdt' \
	'compatible=qcom,kpss-wdt' \
	'timeout_seconds=30'; do
	[ "$(grep -Fxc "$marker" "$hardware_watchdog")" -eq 1 ] || fail hardware-watchdog
done
hardware_watchdog_pid=$(sed -n 's/^pid=//p' "$hardware_watchdog")
case $hardware_watchdog_pid in ''|*[!0-9]*) fail hardware-watchdog ;; esac
kill -0 "$hardware_watchdog_pid" 2>/dev/null || fail hardware-watchdog
[ -f "$native_seal" ] && [ ! -L "$native_seal" ] &&
	[ "$(sha256sum "$native_seal" | awk '{print $1}')" = "$native_seal_sha256" ] || fail native-seal

emit source VERIFY
mkdir -p "$source_mount" "$source_verify_mount" "$target_mount"
mount -t ext4 -o ro,noload,nodev,nosuid,noexec,noatime "$userdata" "$source_mount" || fail userdata-mount
userdata_mounted=1
verify_mount_count 1 || fail userdata-mount-scope
[ -f "$source_image" ] && [ ! -L "$source_image" ] &&
	[ "$(stat -c '%u:%g:%a:%s:%h' "$source_image")" = "0:0:600:$source_bytes:1" ] || fail source-metadata
source_loop=$(losetup -f) || fail source-loop
case $source_loop in /dev/loop[0-9]*) ;; *) fail source-loop ;; esac
losetup -r "$source_loop" "$source_image" || fail source-loop-attach
source_loop_attached=1
[ "$(blockdev --getro "$source_loop")" = 1 ] &&
	[ "$(blockdev --getsize64 "$source_loop")" = "$source_bytes" ] || fail source-loop-identity
verify_ext4 "$source_loop" "$source_uuid" "$source_blocks" /run/rog5-native-clone-source-fs.log || fail source-filesystem
mount -t ext4 -o ro,noload,nodev,nosuid,noexec,noatime "$source_loop" "$source_verify_mount" || fail source-mount
source_mounted=1
verify_mount_count 2 || fail source-mount-scope
"$verifier" "$source_verify_mount" "$native_seal" "$native_seal_sha256" >/run/rog5-native-clone-source-tree.log 2>&1 || fail source-tree
umount "$source_verify_mount" || fail source-unmount
source_mounted=0
losetup -d "$source_loop" || fail source-loop-detach
source_loop_attached=0
verify_mount_count 1 || fail source-cleanup

emit clone WRITE
verify_power_thermal || fail power-thermal-prewrite
blockdev --setrw "$disk" || fail disk-write-window
blockdev --setrw "$arch_root" || fail target-write-window
verify_lock_state 2 || fail write-window
timeout -k 5 420 e2image -ra -p "$source_image" "$arch_root" > /run/rog5-native-clone-e2image.log 2>&1 || fail clone
sync || fail clone-sync
e2fsck -f -p "$arch_root" >/run/rog5-native-clone-fsck.log 2>&1 || fail clone-fsck
verify_ext4 "$arch_root" "$source_uuid" "$source_blocks" /run/rog5-native-clone-source-fs.log || fail clone-identity

emit filesystem GROW
tune2fs -U "$target_uuid" "$arch_root" >/run/rog5-native-clone-uuid.log 2>&1 || fail target-uuid
e2fsck -f -p "$arch_root" >/run/rog5-native-clone-pre-grow-fsck.log 2>&1 || fail pre-grow-fsck
resize2fs "$arch_root" >/run/rog5-native-clone-grow.log 2>&1 || fail grow
e2fsck -f -p "$arch_root" >/run/rog5-native-clone-post-grow-fsck.log 2>&1 || fail post-grow-fsck
verify_ext4 "$arch_root" "$target_uuid" "$target_blocks" /run/rog5-native-clone-grown-fs.log || fail grown-identity

emit seal WRITE
mount -t ext4 -o rw,nodev,nosuid,noexec,noatime "$arch_root" "$target_mount" || fail target-mount-rw
target_mounted=1
verify_mount_count 2 || fail target-mount-scope
"$verifier" "$target_mount" "$native_seal" "$native_seal_sha256" >/run/rog5-native-clone-preseal.log 2>&1 || fail cloned-tree
seal=$target_mount/.rog5-persistent-seal
next=$target_mount/.rog5-persistent-seal.next
[ -f "$seal" ] && [ ! -L "$seal" ] && [ ! -e "$next" ] || fail seal-path
cp "$native_seal" "$next" || fail seal-copy
chown 0:0 "$next" && chmod 0444 "$next" || fail seal-metadata
sync -f "$next" || fail seal-sync
mv -f "$next" "$seal" || fail seal-publish
touch -d @1681862400 "$target_mount" || fail root-mtime
sync -f "$target_mount" || fail root-sync
"$verifier" "$target_mount" "$seal" "$native_seal_sha256" >/run/rog5-native-clone-sealed.log 2>&1 || fail native-tree
umount "$target_mount" || fail target-unmount
target_mounted=0
e2fsck -f -p "$arch_root" >/run/rog5-native-clone-final-fsck.log 2>&1 || fail final-fsck

emit readonly VERIFY
blockdev --setro "$arch_root" || fail target-relock
blockdev --setro "$disk" || fail disk-relock
verify_lock_state 0 || fail relock-state
mount -t ext4 -o ro,noload,nodev,nosuid,noexec,noatime "$arch_root" "$target_mount" || fail target-mount-ro
target_mounted=1
verify_mount_count 2 || fail target-ro-scope
"$verifier" "$target_mount" "$target_mount/.rog5-persistent-seal" "$native_seal_sha256" >/run/rog5-native-clone-readonly.log 2>&1 || fail readonly-tree
umount "$target_mount" || fail target-ro-unmount
target_mounted=0
umount "$source_mount" || fail userdata-unmount
userdata_mounted=0
relock || fail final-relock
verify_mount_count 0 || fail residual-mount
resolve_storage && verify_lock_state 0 || fail final-identity
verify_power_thermal || fail final-power-thermal

printf 'ROG5_NATIVE_CLONE_V1 stage=terminal status=PASS target_uuid=%s target_blocks=%s\n' "$target_uuid" "$target_blocks"
log 'native p24 clone complete; returning to fastboot'
return_bootloader
