#!/bin/sh
set -eu

repo=$(CDPATH= cd -- "$(dirname "$0")/../.." && pwd)
init=$repo/initramfs/recovery-init

sh -n "$init"
grep -Fq 'reboot -f &' "$init"
grep -Fq 'orderly forced reboot still active; using emergency reset' "$init"
! grep -Eq '^[[:space:]]*reboot -f$' "$init"
fallback_line=$(grep -n 'orderly forced reboot still active; using emergency reset' \
	"$init" | cut -d: -f1)
reboot_line=$(grep -n '^[[:space:]]*reboot -f &$' "$init" | cut -d: -f1)
[ "$fallback_line" -lt "$reboot_line" ]
grep -Fq 'rog5.ufs_discovery=1' "$init"
grep -Fq 'UFS discovery did not enumerate a physical disk' "$init"
grep -Fq '/run/rog5-ufs-inventory.tsv' "$init"
grep -Fq 'physical_topology_count' "$init"
grep -Fq 'verify_ufs_power_containment' "$init"
grep -Fq 'ROG5 UFS discovery: auto-hibern8 disabled; link remains active' "$init"
grep -Fq 'ROG5 UFS discovery: host runtime PM forbidden; active reference retained' "$init"
grep -Fq 'ROG5 UFS discovery: WLUN runtime PM forbidden' "$init"
grep -Fq '/run/rog5-ufs-blocked-query-count' "$init"
grep -Fq '/run/rog5-ufs-blocked-scsi-count' "$init"
grep -Fq 'UFS power containment ready; blocked queries=0 blocked SCSI=0' "$init"
[ "$(grep -Fc '! verify_ufs_power_containment; then' "$init")" -eq 2 ]
grep -Fq 'partition_number\tpartition_name' "$init"
grep -Fq 'PARTNAME=' "$init"
grep -Fq '[ ! -e "$sys_disk/partition" ] || continue' "$init"
! grep -Eq 'blkid|fsck|mount[[:space:]].*/dev/' "$init"

mode_line=$(grep -n 'rog5\.ufs_discovery=1' "$init" | head -n1 | cut -d: -f1)
wait_line=$(grep -n '^if \[ "\$ufs_discovery" = 1 \]; then$' "$init" | head -n1 | cut -d: -f1)
power_line=$(grep -n '^[[:space:]]*if ! verify_ufs_power_containment; then$' \
	"$init" | cut -d: -f1)
storage_line=$(grep -n '^if ! isolate_storage; then$' "$init" | head -n1 | cut -d: -f1)
usb_line=$(grep -n '^usb_mode=' "$init" | cut -d: -f1)
[ "$mode_line" -lt "$wait_line" ]
[ "$wait_line" -lt "$power_line" ]
[ "$power_line" -lt "$storage_line" ]
[ "$storage_line" -lt "$usb_line" ]

echo 'PASS discovery init waits for UFS, records sysfs-only inventory, then isolates before USB'
