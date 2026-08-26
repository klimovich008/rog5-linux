#!/bin/sh
set -eu

repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd -P)
target=$repo/scripts/device/inspect-native-arch-root.sh

sh -n "$target"
for contract in \
	'24:arch_root_a)' \
	'[ "$count" -eq 117 ]' \
	'verify_mount_count 0' \
	'blockdev --getro' \
	'bs=1048576 count=4' \
	'bs=1 skip=1080 count=2' \
	'od -An -tx1 -v' \
	'disposition=non-ext4' \
	'disposition=source-clone' \
	'disposition=grown-target' \
	'disposition=partial-ext4' \
	'ro,noload,nodev,nosuid,noexec,noatime' \
	'"$verifier" "$target_mount" "$native_seal"' \
	'ROG5_NATIVE_POSTMORTEM_V1 stage=terminal status=PASS'; do
	grep -Fq "$contract" "$target" || {
		echo "FAIL missing native-root postmortem contract: $contract" >&2
		exit 1
	}
done
! grep -Eq 'blockdev --setrw|mount .*-o rw|e2fsck|resize2fs|tune2fs|e2image|mkfs|sgdisk|fastboot|sha256sum "\$arch_root"' "$target"

echo 'PASS native-root postmortem is exact-geometry, read-only, bounded, and disposition-complete'
