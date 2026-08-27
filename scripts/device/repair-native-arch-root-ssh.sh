#!/bin/sh
set -eu

export PATH=/sbin:/bin:/usr/sbin:/usr/bin
status=/run/rog5-local-image-stage.status
userdata_record=/run/rog5-userdata-device
reboot_helper=/usr/libexec/rog5-reboot-bootloader
target_mount=/mnt/native-root
repair_root=/etc/rog5-native-repair
softdog_module=/rog5-softdog-modules/softdog.ko
target_uuid=8b03827a-cc2d-4408-8558-e9b61195f96b
target_blocks=8388603
old_sshd=cfcf0874754fe466ddc6fbb5e8ff185ae7083bbd2684b84f1c0bbfcb0b9676ac
old_keygen=535ad8b0ad28bcc2a75cd1bdd03c30518f49e61d7bb39c840276b14b58c4abd4
new_sshd=6a88a601266f5775291e394106e97fa0c1c38ac10a1715c56156cda7e8812932
new_keygen=e238ce08e1a4fa0d9d8fe5022e47bf9a841de23370b043c457e13f45e9d90d4e
target_mounted=0
disk=
userdata=
arch_root=

log() { echo "rog5-native-repair: $*" >/dev/kmsg 2>/dev/null || true; }
emit() { printf 'ROG5_NATIVE_REPAIR_V1 stage=%s status=%s\n' "$1" "$2"; }

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
	if [ "$target_mounted" -eq 1 ]; then
		umount "$target_mount" >/dev/null 2>&1 || result=1
		target_mounted=0
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
	printf 'ROG5_NATIVE_REPAIR_V1 stage=terminal status=FAIL reason=%s\n' "$reason"
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
	dumpe2fs -h "$arch_root" >/run/rog5-native-repair-fs.log 2>&1 || return 1
	[ "$(fs_value 'Filesystem state' /run/rog5-native-repair-fs.log)" = clean ] &&
		[ "$(fs_value 'Block size' /run/rog5-native-repair-fs.log)" = 4096 ] &&
		[ "$(fs_value 'Block count' /run/rog5-native-repair-fs.log)" = "$target_blocks" ] &&
		[ "$(fs_value 'Filesystem UUID' /run/rog5-native-repair-fs.log | tr A-F a-f)" = "$target_uuid" ] &&
		[ "$(fs_value 'Filesystem volume name' /run/rog5-native-repair-fs.log)" = ROG5_ARCH_A ]
}

exact_file() {
	path=$1 metadata=$2 hash=$3
	[ -f "$path" ] && [ ! -L "$path" ] &&
		[ "$(stat -c '%u:%g:%a:%s:%h' "$path")" = "$metadata" ] &&
		[ "$(sha256sum "$path" | awk '{print $1}')" = "$hash" ]
}

verify_common_tree() {
	root=$1
	exact_file "$root/.rog5-persistent-seal" 0:0:444:430:1 \
		02231e86746fbc656090f52c96d7e0c968c7ca86ba7449c306f611ea20c6a876 &&
		[ -L "$root/sbin/init" ] &&
		[ "$(readlink "$root/sbin/init")" = ../lib/systemd/systemd ] &&
		exact_file "$root/usr/lib/systemd/systemd" 0:0:755:198968:1 \
		dad2b1339d6b9178f83ef96791e5c020604e16ec7921e6eaf89d3b38eec478d0 &&
		exact_file "$root/root/.ssh/authorized_keys" 0:0:600:81:1 \
		04f39d5949c813450e201b7e579256b1afcd5c7fcea077d36ae445aa53519b61 &&
		exact_file "$root/etc/ssh/sshd_config.d/10-rog5-server.conf" 0:0:644:201:1 \
		c6b01ef801333ee11bb8805a250df2c4f02f38f0015df1449dadb66490e43693
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
exact_file "$repair_root/sshd" 0:0:444:527008:1 "$new_sshd" || fail repair-sshd
exact_file "$repair_root/ssh-keygen" 0:0:444:526688:1 "$new_keygen" || fail repair-keygen

mkdir -p "$target_mount"
mount -t ext4 -o ro,noload,nodev,nosuid,noexec,noatime "$arch_root" "$target_mount" || fail target-mount-ro
target_mounted=1
verify_mount_count 1 || fail target-mount-scope
verify_common_tree "$target_mount" || fail target-common-tree
exact_file "$target_mount/usr/bin/sshd" 0:0:755:527008:1 "$old_sshd" || fail target-old-sshd
exact_file "$target_mount/usr/bin/ssh-keygen" 0:0:755:526688:1 "$old_keygen" || fail target-old-keygen
umount "$target_mount" || fail target-unmount-ro
target_mounted=0
verify_mount_count 0 || fail target-ro-cleanup

emit repair BEGIN
verify_power_thermal || fail power-thermal-prewrite
[ "$(find /sys/class/watchdog -mindepth 1 -maxdepth 1 -name 'watchdog*' | wc -l)" -eq 0 ] || fail softdog-preexisting
insmod "$softdog_module" soft_margin=120 soft_reboot_cmd=bootloader nowayout=0 soft_noboot=0 soft_panic=0 || fail softdog-insmod
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
mount -t ext4 -o rw,nodev,nosuid,noexec,noatime "$arch_root" "$target_mount" || fail target-mount-rw
target_mounted=1
verify_mount_count 1 || fail target-rw-scope
exact_file "$target_mount/usr/bin/sshd" 0:0:755:527008:1 "$old_sshd" || fail prewrite-sshd
exact_file "$target_mount/usr/bin/ssh-keygen" 0:0:755:526688:1 "$old_keygen" || fail prewrite-keygen
cp "$repair_root/sshd" "$target_mount/usr/bin/sshd" || fail write-sshd
cp "$repair_root/ssh-keygen" "$target_mount/usr/bin/ssh-keygen" || fail write-keygen
chmod 0755 "$target_mount/usr/bin/sshd" "$target_mount/usr/bin/ssh-keygen" || fail write-mode
sync || fail repair-sync
exact_file "$target_mount/usr/bin/sshd" 0:0:755:527008:1 "$new_sshd" || fail verify-sshd
exact_file "$target_mount/usr/bin/ssh-keygen" 0:0:755:526688:1 "$new_keygen" || fail verify-keygen
umount "$target_mount" || fail target-unmount-rw
target_mounted=0
blockdev --setro "$arch_root" || fail target-relock
blockdev --setro "$disk" || fail disk-relock
verify_lock_state 0 || fail relock-state
verify_ext4 || fail filesystem-clean

mount -t ext4 -o ro,noload,nodev,nosuid,noexec,noatime "$arch_root" "$target_mount" || fail target-remount-ro
target_mounted=1
verify_common_tree "$target_mount" || fail final-common-tree
exact_file "$target_mount/usr/bin/sshd" 0:0:755:527008:1 "$new_sshd" || fail final-sshd
exact_file "$target_mount/usr/bin/ssh-keygen" 0:0:755:526688:1 "$new_keygen" || fail final-keygen
umount "$target_mount" || fail final-unmount
target_mounted=0
verify_mount_count 0 && verify_lock_state 0 || fail final-cleanup
printf V >&9 || fail softdog-disarm
exec 9>&-
emit watchdog DISARMED
printf '%s\n' 'ROG5_NATIVE_REPAIR_V1 stage=terminal status=PASS files=sshd,ssh-keygen bytes=1053696 storage=RELOCKED'
return_bootloader
