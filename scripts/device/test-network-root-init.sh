#!/bin/sh
set -eu

repo=$(CDPATH= cd -- "$(dirname "$0")/../.." && pwd)
init=$repo/initramfs/network-root-init

[ -x "$init" ] || {
	echo 'FAIL missing executable network-root init' >&2
	exit 1
}
sh -n "$init"

for text in \
	'rog5.netroot=1' \
	'169.254.77.2/30' \
	'169.254.77.1:/' \
	'/run/rog5-network-root-watchdog.pid' \
	'exec 9>/proc/sysrq-trigger' \
	'echo b >&9' \
	'physical block device appeared with UFS-disabled DTB' \
	'mount -t nfs4' \
	'vers=4.2,proto=tcp,port=2049,ro,nolock' \
	'mount -t tmpfs -o nodev,nosuid' \
	'mount -t overlay overlay' \
	'exec switch_root /newroot /sbin/init'; do
	grep -Fq "$text" "$init" || {
		echo "FAIL network-root init contract missing: $text" >&2
		exit 1
	}
done

! grep -Eq 'blkid|fsck|mount[[:space:]].*/dev/|/dev/sd[a-z]' "$init"
! grep -Eq 'fastboot|flash|partition|mkfs|wipefs' "$init"

mode_line=$(grep -n 'invalid network-root command line' "$init" |
	head -n1 | cut -d: -f1)
storage_line=$(grep -n 'physical block device appeared with UFS-disabled DTB' \
	"$init" | tail -n1 | cut -d: -f1)
watchdog_line=$(grep -n '^[[:space:]]*arm_watchdog$' "$init" |
	head -n1 | cut -d: -f1)
usb_line=$(grep -n '^[[:space:]]*configure_usb$' "$init" |
	head -n1 | cut -d: -f1)
nfs_line=$(grep -n '^[[:space:]]*mount_network_root$' "$init" |
	head -n1 | cut -d: -f1)
switch_line=$(grep -n 'exec switch_root /newroot /sbin/init' "$init" |
	tail -n1 | cut -d: -f1)

[ "$mode_line" -lt "$storage_line" ]
[ "$storage_line" -lt "$watchdog_line" ]
[ "$watchdog_line" -lt "$usb_line" ]
[ "$usb_line" -lt "$nfs_line" ]
[ "$nfs_line" -lt "$switch_line" ]

[ "$(grep -Fc 'rog5.netroot=1' "$init")" -eq 1 ]
grep -Fq '[ "$physical_count" -eq 0 ]' "$init"
grep -Fq '[ -x /newroot/sbin/init ]' "$init"
grep -Fq 'mount --move /dev /newroot/dev' "$init"
grep -Fq 'mount --move /proc /newroot/proc' "$init"
grep -Fq 'mount --move /sys /newroot/sys' "$init"
grep -Fq 'mount --move /run /newroot/run' "$init"

echo 'PASS network-root init keeps UFS absent, mounts read-only NFS plus tmpfs overlay, and preserves rollback'
