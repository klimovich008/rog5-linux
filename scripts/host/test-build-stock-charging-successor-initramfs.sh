#!/usr/bin/env bash
set -euo pipefail

repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
builder=$repo/scripts/host/build-stock-charging-successor-initramfs.sh
root=$(mktemp -d)
trap 'rm -rf -- "$root"' EXIT

fixture=$root/fixture
mkdir -p "$fixture/first_stage_ramdisk" "$fixture/system/bin" "$fixture/system/etc"
ln -s /system/bin/init "$fixture/init"
for executable in charger init sh reboot toybox; do
	printf '#!/bin/sh\nexit 0\n' >"$fixture/system/bin/$executable"
	chmod 0755 "$fixture/system/bin/$executable"
done
fstab='system /system ext4 ro wait
/dev/block/by-name/metadata /metadata ext4 rw wait,check,formattable
/dev/block/by-name/userdata /data f2fs rw wait,check,formattable
/dev/block/by-name/misc /misc emmc defaults defaults
/dev/block/by-name/persist /mnt/vendor/persist ext4 rw wait
/dev/block/by-name/dsp /vendor/dsp ext4 ro wait,slotselect
'
printf '%s' "$fstab" >"$fixture/first_stage_ramdisk/fstab.emmc"
printf '%s' "$fstab" >"$fixture/first_stage_ramdisk/fstab.default"
printf '%s' "$fstab" >"$fixture/system/etc/recovery.fstab"

SOURCE_DATE_EPOCH=1 ROLLBACK_SECONDS=600 "$builder" "$fixture" "$root/a.cpio.gz" >/dev/null
SOURCE_DATE_EPOCH=1 ROLLBACK_SECONDS=600 "$builder" "$fixture" "$root/b.cpio.gz" >/dev/null
cmp -s "$root/a.cpio.gz" "$root/b.cpio.gz"

mkdir "$root/unpacked"
(
	cd "$root/unpacked"
	gzip -dc "$root/a.cpio.gz" | cpio -id --quiet
)
[[ -f $root/unpacked/init && ! -L $root/unpacked/init ]]
grep -Fqx "echo 'rog5-stock-charging-explicit-dtb-v2: init-enter' >/dev/kmsg 2>/dev/null || true" "$root/unpacked/init"
grep -Fqx $'\tsleep 600' "$root/unpacked/init"
grep -Fqx 'export ANDROID_ROOT=/system' "$root/unpacked/init"
grep -Fqx 'exec /system/bin/charger' "$root/unpacked/init"
for fstab_path in \
	"$root/unpacked/first_stage_ramdisk/fstab.emmc" \
	"$root/unpacked/first_stage_ramdisk/fstab.default" \
	"$root/unpacked/system/etc/recovery.fstab"; do
	! awk 'NF && $1 !~ /^#/ { found=1 } END { exit found ? 0 : 1 }' "$fstab_path"
	grep -Fq '# ROG5 RAM-only charging successor disabled: system /system ext4 ro wait' "$fstab_path"
	grep -Fq '# ROG5 RAM-only charging successor disabled: /dev/block/by-name/dsp /vendor/dsp ext4 ro wait,slotselect' "$fstab_path"
done

if "$builder" "$fixture" "$root/a.cpio.gz" >/dev/null 2>&1; then
	echo 'FAIL builder replaced an existing output' >&2
	exit 1
fi
ln -sfn /wrong-init "$fixture/init"
if "$builder" "$fixture" "$root/c.cpio.gz" >/dev/null 2>&1; then
	echo 'FAIL builder accepted a wrong stock init link' >&2
	exit 1
fi

echo 'PASS stock charging successor is deterministic, storage-isolated, early-marked, and rollback-bounded'
