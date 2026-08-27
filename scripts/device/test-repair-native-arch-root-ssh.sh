#!/bin/sh
set -eu

repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd -P)
target=$repo/scripts/device/repair-native-arch-root-ssh.sh
builder=$repo/scripts/device/build-local-image-stage-initramfs.sh

sh -n "$target" "$builder"
for contract in \
	'24:arch_root_a)' \
	'verify_lock_state 0' \
	'verify_power_thermal' \
	'target-old-sshd' \
	'target-old-keygen' \
	'soft_margin=120' \
	'blockdev --setrw "$disk"' \
	'blockdev --setrw "$arch_root"' \
	'cp "$repair_root/sshd"' \
	'cp "$repair_root/ssh-keygen"' \
	'blockdev --setro "$arch_root"' \
	'blockdev --setro "$disk"' \
	'filesystem-clean' \
	"verify_ext4_state 'clean with errors'" \
	'e2fsck -p "$arch_root"' \
	'case $fsck_status in 0|1|2)' \
	'operation=fsck status_code=%s storage=RELOCKED tree=PASS' \
	'ROG5_NATIVE_REPAIR_V1 stage=terminal status=PASS files=sshd,ssh-keygen bytes=1053696 storage=RELOCKED'; do
	grep -Fq "$contract" "$target" || {
		echo "FAIL missing native repair contract: $contract" >&2
		exit 1
	}
done
for contract in \
	'NATIVE_REPAIR_ROOT' \
	'native repair inventory changed' \
	'native repair sshd changed' \
	'native repair ssh-keygen changed' \
	'NATIVE_FSCK_ONLY' \
	'native fsck and binary repair modes are mutually exclusive' \
	'$stage/etc/rog5-native-fsck-only' \
	'$stage/etc/rog5-native-repair/sshd' \
	'$stage/etc/rog5-native-repair/ssh-keygen'; do
	grep -Fq "$contract" "$builder" || {
		echo "FAIL missing native repair packaging contract: $contract" >&2
		exit 1
	}
done
! grep -Eq 'fastboot|sgdisk|parted|mkfs|userdata.*setrw|/dev/sd[a-z][0-9]*.*of=' "$target"
[ "$(grep -Fc 'blockdev --setrw' "$target")" -eq 4 ]
[ "$(grep -Fc 'cp "$repair_root/' "$target")" -eq 2 ]
[ "$(grep -Fc 'blockdev --setro' "$target")" -eq 5 ]

echo 'PASS native Arch SSH repair is exact-two-file, power-gated, watchdog-bounded, relocked, and fallback-safe'
