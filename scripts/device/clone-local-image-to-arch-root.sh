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
softdog_module=/rog5-softdog-modules/softdog.ko
extent_map=/etc/rog5-local-image-direct-extents.tsv
source_bytes=17179869184
source_blocks=4194304
source_uuid=598a876b-a8db-4859-a01a-1b864b0a87f4
target_blocks=8388603
target_uuid=8b03827a-cc2d-4408-8558-e9b61195f96b
native_seal_sha256=02231e86746fbc656090f52c96d7e0c968c7ca86ba7449c306f611ea20c6a876
extent_map_sha256=e21b9453662d5f24536144e322ed0ef6bde7038efb44fdf1afcb80ee823ccd94
extent_count=37
extent_bytes=1850654720
chunk_first=20
chunk_last=20
chunk_segment=2
chunk_offset_blocks=1436877
chunk_block_count=27204
chunk_bytes=111427584
extent20_offset_blocks=1355264
extent20_block_count=217633
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

verify_exact_regular() {
	path=$1 owner=$2 group=$3 mode=$4 size=$5 hash=$6
	[ -f "$path" ] && [ ! -L "$path" ] || return 1
	[ "$(stat -c '%u:%g:%a:%s:%h' "$path")" = \
		"$owner:$group:$mode:$size:1" ] || return 1
	[ "$(sha256sum "$path" | awk '{print $1}')" = "$hash" ]
}

verify_boot_critical_root() {
	root=$1
	seal=$root/.rog5-persistent-seal
	verify_exact_regular "$seal" 0 0 444 430 "$native_seal_sha256" || return 1
	[ "$(wc -l <"$seal")" -eq 13 ] &&
		grep -Fxq 'seal_format=rog5-persistent-root-v1' "$seal" &&
		grep -Fxq 'generation=arch-a' "$seal" &&
		grep -Fxq 'promotion_state=UNBOOTED' "$seal" || return 1
	[ -L "$root/sbin/init" ] &&
		[ "$(readlink "$root/sbin/init")" = ../lib/systemd/systemd ] || return 1
	verify_exact_regular "$root/usr/lib/systemd/systemd" 0 0 755 198968 \
		dad2b1339d6b9178f83ef96791e5c020604e16ec7921e6eaf89d3b38eec478d0 || return 1
	verify_exact_regular "$root/usr/bin/sshd" 0 0 755 527008 \
		6a88a601266f5775291e394106e97fa0c1c38ac10a1715c56156cda7e8812932 || return 1
	verify_exact_regular "$root/usr/bin/ssh-keygen" 0 0 755 526688 \
		e238ce08e1a4fa0d9d8fe5022e47bf9a841de23370b043c457e13f45e9d90d4e || return 1
	verify_exact_regular "$root/root/.ssh/authorized_keys" 0 0 600 81 \
		04f39d5949c813450e201b7e579256b1afcd5c7fcea077d36ae445aa53519b61 || return 1
	verify_exact_regular "$root/etc/ssh/sshd_config.d/10-rog5-server.conf" \
		0 0 644 201 c6b01ef801333ee11bb8805a250df2c4f02f38f0015df1449dadb66490e43693
}

[ "$#" -eq 0 ] || fail arguments
[ "$(id -u)" -eq 0 ] || fail not-root
[ "$(cat "$status")" = "$(printf 'state=READY\nuserdata=%s\nstorage=read-only\nssh=key-only' "$(cat "$userdata_record")")" ] || fail readiness
resolve_storage || fail storage-identity
[ "$(cat "$userdata_record")" = "$userdata" ] || fail userdata-record
verify_mount_count 0 || fail prewrite-mounts
verify_lock_state 0 || fail prewrite-locks
verify_power_thermal || fail power-thermal
[ -f "$softdog_module" ] && [ ! -L "$softdog_module" ] || fail softdog-module
[ -f "$native_seal" ] && [ ! -L "$native_seal" ] &&
	[ "$(sha256sum "$native_seal" | awk '{print $1}')" = "$native_seal_sha256" ] || fail native-seal
[ -f "$extent_map" ] && [ ! -L "$extent_map" ] &&
	[ "$(sha256sum "$extent_map" | awk '{print $1}')" = "$extent_map_sha256" ] &&
	grep -Fxq "extent_count=$extent_count" "$extent_map" &&
	grep -Fxq "data_bytes=$extent_bytes" "$extent_map" || fail extent-map

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
verify_boot_critical_root "$source_verify_mount" || fail source-tree
umount "$source_verify_mount" || fail source-unmount
source_mounted=0
losetup -d "$source_loop" || fail source-loop-detach
source_loop_attached=0
verify_mount_count 1 || fail source-cleanup

emit clone WRITE
verify_power_thermal || fail power-thermal-prewrite
[ "$(find /sys/class/watchdog -mindepth 1 -maxdepth 1 -name 'watchdog*' | wc -l)" -eq 0 ] ||
	fail softdog-preexisting
insmod "$softdog_module" soft_margin=840 soft_reboot_cmd=bootloader \
	nowayout=0 soft_noboot=0 soft_panic=0 || fail softdog-insmod
grep -q '^softdog ' /proc/modules || fail softdog-module-state
attempt=0
while [ "$attempt" -lt 50 ]; do
	[ -c /dev/watchdog0 ] && break
	attempt=$((attempt + 1)); sleep 0.1
done
[ -c /dev/watchdog0 ] || fail softdog-device
exec 9>/dev/watchdog0 || fail softdog-open
printf '\0' >&9 || fail softdog-arm
emit watchdog ARMED
blockdev --setrw "$disk" || fail disk-write-window
blockdev --setrw "$arch_root" || fail target-write-window
verify_lock_state 2 || fail write-window
written_extents=$((chunk_first - 1))
direct_bytes=0
[ "$chunk_first" -eq 20 ] && [ "$chunk_last" -eq 20 ] &&
	[ "$chunk_segment" -ge 1 ] && [ "$chunk_segment" -le 4 ] &&
	[ "$chunk_block_count" -gt 0 ] &&
	[ "$chunk_bytes" -eq "$((chunk_block_count * 4096))" ] &&
	[ "$chunk_offset_blocks" -ge "$extent20_offset_blocks" ] &&
	[ "$((chunk_offset_blocks + chunk_block_count))" -le \
		"$((extent20_offset_blocks + extent20_block_count))" ] ||
	fail chunk-contract
tab=$(printf '\t')
while IFS="$tab" read -r index offset count; do
	case $index in ''|*[!0-9]*) continue ;; esac
	[ "$index" -ge "$chunk_first" ] || continue
	[ "$index" -le "$chunk_last" ] || break
	[ "$index" -eq "$((written_extents + 1))" ] || fail extent-order
	case $offset in ''|*[!0-9]*) fail extent-map ;; esac
	case $count in ''|*[!0-9]*) fail extent-map ;; esac
	[ "$offset" -eq "$extent20_offset_blocks" ] &&
		[ "$count" -eq "$extent20_block_count" ] || fail extent20-map
	offset=$chunk_offset_blocks
	count=$chunk_block_count
	offset_bytes=$((offset * 4096))
	count_bytes=$((count * 4096))
	stats=/run/rog5-native-clone-dd-$index.stats
	printf 'ROG5_NATIVE_CLONE_V1 stage=extent status=BEGIN index=%s segment=%s offset=%s blocks=%s\n' \
		"$index" "$chunk_segment" "$offset" "$count"
	dd if="$source_image" of="$arch_root" ibs=1048576 obs=1048576 \
		skip="$offset_bytes" seek="$offset_bytes" count="$count_bytes" \
		iflag=skip_bytes,count_bytes,fullblock \
		oflag=seek_bytes,direct conv=notrunc status=noxfer 2>"$stats" ||
		fail direct-clone
	printf 'ROG5_NATIVE_CLONE_V1 stage=extent status=PASS index=%s segment=%s offset=%s blocks=%s\n' \
		"$index" "$chunk_segment" "$offset" "$count"
	written_extents=$index
	direct_bytes=$((direct_bytes + count_bytes))
done <"$extent_map"
[ "$written_extents" -eq "$chunk_last" ] &&
	[ "$direct_bytes" -eq "$chunk_bytes" ] || fail extent-incomplete
sync || fail clone-sync
[ "$chunk_last" -eq "$extent_count" ] || {
	blockdev --setro "$arch_root" || fail target-relock
	blockdev --setro "$disk" || fail disk-relock
	verify_lock_state 0 || fail relock-state
	printf V >&9 || fail softdog-disarm
	exec 9>&-
	emit watchdog DISARMED
	printf 'ROG5_NATIVE_CLONE_V1 stage=terminal status=CHUNK_PASS first=%s last=%s segment=%s offset=%s blocks=%s bytes=%s\n' \
		"$chunk_first" "$chunk_last" "$chunk_segment" \
		"$chunk_offset_blocks" "$chunk_block_count" "$chunk_bytes"
	return_bootloader
}
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
verify_boot_critical_root "$target_mount" || fail cloned-tree
seal=$target_mount/.rog5-persistent-seal
next=$target_mount/.rog5-persistent-seal.next
[ -f "$seal" ] && [ ! -L "$seal" ] && [ ! -e "$next" ] || fail seal-path
cp "$native_seal" "$next" || fail seal-copy
chown 0:0 "$next" && chmod 0444 "$next" || fail seal-metadata
sync -f "$next" || fail seal-sync
mv -f "$next" "$seal" || fail seal-publish
touch -d @1681862400 "$target_mount" || fail root-mtime
sync -f "$target_mount" || fail root-sync
verify_boot_critical_root "$target_mount" || fail native-tree
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
verify_boot_critical_root "$target_mount" || fail readonly-tree
umount "$target_mount" || fail target-ro-unmount
target_mounted=0
umount "$source_mount" || fail userdata-unmount
userdata_mounted=0
relock || fail final-relock
verify_mount_count 0 || fail residual-mount
resolve_storage && verify_lock_state 0 || fail final-identity
verify_power_thermal || fail final-power-thermal
printf V >&9 || fail softdog-disarm
exec 9>&-
emit watchdog DISARMED

printf 'ROG5_NATIVE_CLONE_V1 stage=terminal status=PASS target_uuid=%s target_blocks=%s\n' "$target_uuid" "$target_blocks"
log 'native p24 clone complete; returning to fastboot'
return_bootloader
