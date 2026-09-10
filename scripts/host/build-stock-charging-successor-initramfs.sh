#!/usr/bin/env bash
set -euo pipefail

fail() {
	echo "FAIL $*" >&2
	exit 1
}

[[ $# -eq 2 ]] || fail 'usage: build-stock-charging-successor-initramfs.sh SOURCE_ROOT OUTPUT'
source_root=$(realpath -e -- "$1")
output=$2
[[ $output = /* ]] || fail 'output must be absolute'
[[ -d $source_root && ! -L $source_root ]] || fail 'source root is not one real directory'
[[ ! -e $output && ! -L $output ]] || fail 'output already exists'
[[ -d $(dirname -- "$output") ]] || fail 'output parent is absent'
[[ $(readlink -- "$source_root/init") == /system/bin/init ]] ||
	fail 'source /init is not the exact stock init link'
for executable in \
	system/bin/charger \
	system/bin/init \
	system/bin/sh \
	system/bin/reboot \
	system/bin/toybox; do
	[[ -f $source_root/$executable && -x $source_root/$executable ]] ||
		fail "source lacks executable $executable"
done
for fstab in \
	first_stage_ramdisk/fstab.emmc \
	first_stage_ramdisk/fstab.default \
	system/etc/recovery.fstab; do
	[[ -f $source_root/$fstab && ! -L $source_root/$fstab ]] ||
		fail "source lacks regular $fstab"
done

epoch=${SOURCE_DATE_EPOCH:-1786856400}
[[ $epoch =~ ^[0-9]+$ ]] || fail 'SOURCE_DATE_EPOCH is not decimal'
rollback=${ROLLBACK_SECONDS:-900}
[[ $rollback =~ ^[1-9][0-9]{1,3}$ && $rollback -le 3600 ]] ||
	fail 'ROLLBACK_SECONDS is outside 10..3600'

work=$(mktemp -d "$(dirname -- "$output")/.stock-charging-successor.XXXXXX")
cleanup() {
	rm -rf -- "$work"
}
trap cleanup EXIT
mkdir "$work/root"
cp -a --reflink=auto "$source_root/." "$work/root/"

sanitize_fstab() {
	local path=$1
	awk '
		!NF || /^[[:space:]]*#/ { print; next }
		{ print "# ROG5 RAM-only charging successor disabled: " $0 }
	' "$path" >"$path.new"
	mv -T -- "$path.new" "$path"
}

sanitize_fstab "$work/root/first_stage_ramdisk/fstab.emmc"
sanitize_fstab "$work/root/first_stage_ramdisk/fstab.default"
sanitize_fstab "$work/root/system/etc/recovery.fstab"

cat >"$work/root/rog5-init" <<EOF
#!/system/bin/sh
export PATH=/system/bin
export ANDROID_ROOT=/system
mkdir -p /dev /proc /sys
[ -e /dev/kmsg ] || mount -t devtmpfs devtmpfs /dev 2>/dev/null || true
mountpoint -q /proc 2>/dev/null || mount -t proc proc /proc 2>/dev/null || true
mountpoint -q /sys 2>/dev/null || mount -t sysfs sysfs /sys 2>/dev/null || true
echo 'rog5-stock-charging-explicit-dtb-v2: init-enter' >/dev/kmsg 2>/dev/null || true
(
	sleep $rollback
	echo 'rog5-stock-charging-explicit-dtb-v2: rollback' >/dev/kmsg 2>/dev/null || true
	/system/bin/reboot bootloader 2>/dev/null || true
	echo b >/proc/sysrq-trigger 2>/dev/null || true
) &
exec /system/bin/charger
EOF
chmod 0755 "$work/root/rog5-init"
rm -- "$work/root/init"
mv -T -- "$work/root/rog5-init" "$work/root/init"

for fstab in \
	first_stage_ramdisk/fstab.emmc \
	first_stage_ramdisk/fstab.default \
	system/etc/recovery.fstab; do
	awk 'NF && $1 !~ /^#/ { exit 1 }' "$work/root/$fstab" ||
		fail "active storage entry survived in $fstab"
done

find "$work/root" -exec touch -h -d "@$epoch" -- {} +
tmp_output=$output.tmp
[[ ! -e $tmp_output && ! -L $tmp_output ]] || fail 'temporary output already exists'
(
	cd "$work/root"
	find . -print0 | LC_ALL=C sort -z |
		cpio --null -o --format=newc --reproducible --owner=0:0 2>/dev/null |
		gzip -n -9
) >"$tmp_output"
gzip -t "$tmp_output"
mv -T -- "$tmp_output" "$output"
trap - EXIT
cleanup
sha256sum "$output"
