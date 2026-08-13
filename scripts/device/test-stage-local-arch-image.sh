#!/bin/sh
set -eu

repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)
stage=$repo/scripts/device/stage-local-arch-image.sh

fail() {
	echo "FAIL $*" >&2
	exit 1
}

[ -x "$stage" ] || fail 'local-image stager is missing or not executable'
sh -n "$stage"
for contract in \
	'partial=$store/arch-local-a.ext4.partial' \
	'final=$store/arch-local-a.ext4' \
	'image_bytes=17179869184' \
	'image_label=ROG5_ARCH_A' \
	'expected_root_tool_sha256=0b2a3a9a8ad330dd427427ac8deb79ca18cb2f8575d46cdc9b354594dce27057' \
	'bsdtar_loader=$bsdtar_runtime/lib/ld-musl-aarch64.so.1' \
	'0:0:755:4' \
	'"$bsdtar_loader" --library-path "$bsdtar_runtime/lib" "$bsdtar" "$@"' \
	'bsdtar runtime inventory changed' \
	'resolve_userdata_root' \
	'[ "$userdata_count" -eq 1 ] && [ "$exact_count" -eq 1 ]' \
	'less than 18 GiB is free on userdata' \
	'local-image staging is unarmed' \
	'fallocate -l "$image_bytes" "$partial"' \
	'hash_seed="$image_uuid",lazy_itable_init=0,lazy_journal_init=0 "$partial"' \
	'loop_device=$(losetup -f)' \
	'losetup "$loop_device" "$partial"' \
	'backing_file=$(cat "/sys/class/block/$loop_name/loop/backing_file")' \
	'--strip-components 1' \
	'mv "$mountpoint/.rog5-persistent-seal" "$mountpoint/.rog5-source-seal"' \
	'touch -d @1681862400 "$mountpoint"' \
	'tree_entries=37736' \
	'tree_sha256=$expected_local_tree_sha256' \
	'"$root_tool" verify "$mountpoint"' \
	'rmdir "$mountpoint/lost+found"' \
	'e2fsck -fn "$partial"' \
	'image_sha256=$(sha256sum "$partial"' \
	'mv -T -- "$partial" "$final"'; do
	grep -Fq -- "$contract" "$stage" ||
		fail "local-image staging contract is absent: $contract"
done
if grep -Eq 'mkfs[^\n]*(/dev/|\$userdata|\$loop_device)|dd[^\n]*of=/dev/|wipefs|sgdisk|parted|fastboot|flash|erase' "$stage"; then
	fail 'local-image stager contains a raw-device or partition mutation path'
fi
[ "$(grep -Ec '^[[:space:]]*mkfs[.]ext4 ' "$stage")" -eq 1 ] ||
	fail 'local-image stager must contain one exact mkfs call'
[ "$(grep -Ec '^[[:space:]]*mount -t ext4 ' "$stage")" -eq 1 ] ||
	fail 'local-image stager must contain one exact image mount'
grep -Fq 'mkfs.ext4 -q -F -m 1 -L "$image_label" -U "$image_uuid"' "$stage" ||
	fail 'mkfs target is not the fixed new image file'
grep -Fq '"$loop_device" "$mountpoint"' "$stage" ||
	fail 'image mount does not use the validated loop device'
if grep -Eq 'losetup[[:space:]]+--find|losetup[[:space:]]+-n|blkid[[:space:]]+-p' \
	"$stage"; then
	fail 'local-image stager uses a non-BusyBox fallback dialect'
fi

echo 'PASS local-image stager is fixed to one new 16 GiB file and has no raw-device mutation path'
