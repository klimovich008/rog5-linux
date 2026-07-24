#!/bin/sh
set -eu

repo=$(CDPATH= cd -- "$(dirname "$0")/../.." && pwd)
init=$repo/initramfs/recovery-init

sh -n "$init"
grep -Fq 'rog5.ufs_discovery=1' "$init"
grep -Fq 'UFS discovery did not enumerate a physical disk' "$init"
grep -Fq '/run/rog5-ufs-inventory.tsv' "$init"
grep -Fq 'physical_topology_count' "$init"
grep -Fq 'partition_number\tpartition_name' "$init"
grep -Fq 'PARTNAME=' "$init"
grep -Fq '[ ! -e "$sys_disk/partition" ] || continue' "$init"
! grep -Eq 'blkid|fsck|mount[[:space:]].*/dev/' "$init"

mode_line=$(grep -n 'rog5\.ufs_discovery=1' "$init" | head -n1 | cut -d: -f1)
wait_line=$(grep -n '^if \[ "\$ufs_discovery" = 1 \]; then$' "$init" | head -n1 | cut -d: -f1)
storage_line=$(grep -n '^if ! isolate_storage; then$' "$init" | head -n1 | cut -d: -f1)
usb_line=$(grep -n '^usb_mode=' "$init" | cut -d: -f1)
[ "$mode_line" -lt "$wait_line" ]
[ "$wait_line" -lt "$storage_line" ]
[ "$storage_line" -lt "$usb_line" ]

echo 'PASS discovery init waits for UFS, records sysfs-only inventory, then isolates before USB'
