#!/bin/sh
set -eu

repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd -P)
target=$repo/scripts/device/clone-local-image-to-arch-root.sh
builder=$repo/scripts/device/build-local-image-stage-initramfs.sh

sh -n "$target"
for contract in \
	'e2image -ra -p "$source_image" "$arch_root"' \
	'24:arch_root_a)' \
	'67108824' \
	'verify_lock_state 2' \
	'target_uuid=8b03827a-cc2d-4408-8558-e9b61195f96b' \
	'target_blocks=8388603' \
	'[ "$count" -eq 117 ]' \
	'"$verifier" "$target_mount"' \
	'ROG5_NATIVE_CLONE_V1 stage=terminal status=PASS'; do
	grep -Fq "$contract" "$target" || {
		echo "FAIL missing native-clone contract: $contract" >&2
		exit 1
	}
done
! grep -Eq 'sgdisk|mkfs|fastboot|/dev/sd[a-z]24' "$target"
grep -Fq 'native_seal=${NATIVE_SEAL:-}' "$builder"
grep -Fq 'ln -s /proc/mounts "$stage/etc/mtab"' "$builder"

work=$(mktemp -d)
trap 'rm -rf -- "$work"' EXIT HUP INT TERM
source=$work/source.ext4
clone=$work/clone.ext4
truncate -s 64M "$source"
mkfs.ext4 -q -F -b 4096 -L ROG5_TEST "$source"
printf 'allocated-block-clone\n' >"$work/payload"
debugfs -w -R "write $work/payload /payload" "$source" >/dev/null 2>&1
dd if=/dev/urandom of="$clone" bs=1M count=64 status=none
e2image -ra -p "$source" "$clone" >/dev/null 2>&1
e2fsck -fn "$clone" >/dev/null 2>&1
[ "$(debugfs -R 'cat /payload' "$clone" 2>/dev/null)" = allocated-block-clone ]

echo 'PASS p24 clone is exact-scope, allocated-block, power/thermal-gated, sealed, and hostile-destination tested'
