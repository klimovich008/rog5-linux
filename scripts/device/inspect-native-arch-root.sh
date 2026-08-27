#!/bin/sh
set -eu

export PATH=/sbin:/bin:/usr/sbin:/usr/bin
status=/run/rog5-local-image-stage.status
userdata_record=/run/rog5-userdata-device
reboot_helper=/usr/libexec/rog5-reboot-bootloader
target_mount=/mnt/native-root
native_seal=/etc/rog5/native-root-v1.seal
source_uuid=598a876b-a8db-4859-a01a-1b864b0a87f4
source_blocks=4194304
target_uuid=8b03827a-cc2d-4408-8558-e9b61195f96b
target_blocks=8388603
native_seal_sha256=02231e86746fbc656090f52c96d7e0c968c7ca86ba7449c306f611ea20c6a876
target_mounted=0
disk=
userdata=
arch_root=

log() { echo "rog5-native-postmortem: $*" >/dev/kmsg 2>/dev/null || true; }

cleanup() {
	[ "$target_mounted" -eq 0 ] || umount "$target_mount" >/dev/null 2>&1 || true
}

return_bootloader() {
	trap - EXIT HUP INT TERM
	cleanup
	"$reboot_helper" >/dev/null 2>&1 &
	sleep 3
	printf b >/proc/sysrq-trigger
	while :; do sleep 3600; done
}

fail() {
	log "FAIL $1"
	printf 'ROG5_NATIVE_POSTMORTEM_V1 stage=terminal status=FAIL reason=%s\n' "$1"
	return_bootloader
}
trap 'fail interrupted' HUP INT TERM

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

verify_read_only() {
	count=0
	for sys_disk in /sys/class/block/*; do
		[ -e "$sys_disk/device" ] && [ ! -e "$sys_disk/partition" ] || continue
		name=$(basename "$sys_disk")
		for sys_block in "$sys_disk" "$sys_disk"/"$name"*; do
			[ -e "$sys_block/dev" ] || continue
			[ "$sys_block" = "$sys_disk" ] || [ -e "$sys_block/partition" ] || continue
			[ "$(blockdev --getro "/dev/$(basename "$sys_block")")" = 1 ] || return 1
			count=$((count + 1))
		done
	done
	[ "$count" -eq 117 ]
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

fs_value() { sed -n "s/^$1:[[:space:]]*//p" "$2" | sed -n '1p'; }

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
		dad2b1339d6b9178f83ef96791e5c020604e16ec7921e6eaf89d3b38eec478d0 ||
		return 1
	verify_exact_regular "$root/usr/bin/sshd" 0 0 755 527008 \
		6a88a601266f5775291e394106e97fa0c1c38ac10a1715c56156cda7e8812932 ||
		return 1
	verify_exact_regular "$root/usr/bin/ssh-keygen" 0 0 755 526688 \
		e238ce08e1a4fa0d9d8fe5022e47bf9a841de23370b043c457e13f45e9d90d4e ||
		return 1
	verify_exact_regular "$root/root/.ssh/authorized_keys" 0 0 600 81 \
		04f39d5949c813450e201b7e579256b1afcd5c7fcea077d36ae445aa53519b61 ||
		return 1
	verify_exact_regular "$root/etc/ssh/sshd_config.d/10-rog5-server.conf" \
		0 0 644 201 c6b01ef801333ee11bb8805a250df2c4f02f38f0015df1449dadb66490e43693
}

[ "$#" -eq 0 ] || fail arguments
[ "$(id -u)" -eq 0 ] || fail not-root
[ "$(cat "$status")" = "$(printf 'state=READY\nuserdata=%s\nstorage=read-only\nssh=key-only' "$(cat "$userdata_record")")" ] || fail readiness
resolve_storage || fail storage-identity
[ "$(cat "$userdata_record")" = "$userdata" ] || fail userdata-record
verify_mount_count 0 || fail preinspect-mounts
verify_read_only || fail preinspect-locks
[ -f "$native_seal" ] && [ ! -L "$native_seal" ] &&
	[ "$(sha256sum "$native_seal" | awk '{print $1}')" = "$native_seal_sha256" ] || fail native-seal

printf '%s\n' 'ROG5_NATIVE_POSTMORTEM_V1 stage=inspect status=READ'
prefix_sha256=$(dd if="$arch_root" bs=1048576 count=4 2>/dev/null | sha256sum | awk '{print $1}') || fail prefix-read
magic=$(dd if="$arch_root" bs=1 skip=1080 count=2 2>/dev/null |
	od -An -tx1 -v | tr -d ' \n') || fail magic-read
case $magic in
	53ef) ;;
	*)
		printf 'ROG5_NATIVE_POSTMORTEM_V1 stage=terminal status=PASS disposition=non-ext4 prefix_sha256=%s\n' "$prefix_sha256"
		return_bootloader
		;;
esac

dumpe2fs -h "$arch_root" >/run/rog5-native-postmortem-fs.txt 2>&1 || fail dumpe2fs
uuid=$(fs_value 'Filesystem UUID' /run/rog5-native-postmortem-fs.txt | tr A-F a-f)
blocks=$(fs_value 'Block count' /run/rog5-native-postmortem-fs.txt)
state=$(fs_value 'Filesystem state' /run/rog5-native-postmortem-fs.txt)
label=$(fs_value 'Filesystem volume name' /run/rog5-native-postmortem-fs.txt)
case "$uuid:$blocks:$state:$label" in
	"$source_uuid:$source_blocks:clean:ROG5_ARCH_A") disposition=source-clone ;;
	"$target_uuid:$target_blocks:clean:ROG5_ARCH_A") disposition=grown-target ;;
	*) disposition=partial-ext4 ;;
esac

tree=SKIP
if [ "$disposition" != partial-ext4 ]; then
	mkdir -p "$target_mount"
	mount -t ext4 -o ro,noload,nodev,nosuid,noexec,noatime "$arch_root" "$target_mount" || fail target-mount
	target_mounted=1
	verify_mount_count 1 || fail target-mount-scope
	verify_boot_critical_root "$target_mount" || fail target-tree
	tree=BOOT_CRITICAL_PASS
	umount "$target_mount" || fail target-unmount
	target_mounted=0
fi
verify_mount_count 0 || fail residual-mount
resolve_storage && verify_read_only || fail final-identity

printf 'ROG5_NATIVE_POSTMORTEM_V1 stage=terminal status=PASS disposition=%s uuid=%s blocks=%s state=%s label=%s tree=%s prefix_sha256=%s\n' \
	"$disposition" "$uuid" "$blocks" "$state" "$label" "$tree" "$prefix_sha256"
return_bootloader
