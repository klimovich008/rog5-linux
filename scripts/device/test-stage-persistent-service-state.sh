#!/bin/sh
set -eu

repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)
script=$repo/scripts/device/stage-persistent-service-state.sh

fail() { echo "FAIL $*" >&2; exit 1; }

[ -x "$script" ]
sh -n "$script"

for contract in \
	'image_bytes=4294967296' \
	'image_uuid=52037413-561a-48f4-92c4-8ad45b748a6f' \
	'relative_final=rog5/state/server-state-v1.ext4' \
	'userdata_partuuid=8d82ef11-4d42-60e9-24e8-4d6ebf20491b' \
	'userdata_start=18821440' \
	'userdata_size=408997568' \
	'disk_size=494927872' \
	'ALLOW_ROG5_SERVICE_STATE_STAGE' \
	'blockdev --setrw "$userdata_disk"' \
	'blockdev --setrw "$userdata"' \
	'write window exposed another partition' \
	'verify_existing_root_mount' \
	'/.rog5/root-ro' \
	'layout=home,root,var-lib,var-log,etc-ssh,secrets' \
	'timeout -k 5 180 e2fsck -fn' \
	'all_storage_read_only || fail'; do
	grep -Fq "$contract" "$script" || fail "missing contract: $contract"
done

for forbidden in \
	'fastboot' 'adb ' 'sgdisk' 'parted' 'fdisk' 'mkfs.f2fs' \
	'/dev/sda23' 'rm -rf' 'blkdiscard' 'wipefs'; do
	! grep -Fq "$forbidden" "$script" || fail "forbidden surface: $forbidden"
done

[ "$(grep -Ec '^mkfs[.]ext4 ' "$script")" -eq 1 ]
[ "$(grep -Fc 'truncate -s "$image_bytes"' "$script")" -eq 1 ]
[ "$(grep -Fc 'mv -T "$mountpoint/$relative_partial"' "$script")" -eq 1 ]
[ "$(grep -Fc 'trap cleanup EXIT HUP INT TERM' "$script")" -eq 1 ]

if "$script" invalid >/dev/null 2>&1; then
	fail 'stager accepted an invalid action'
fi
if "$script" >/dev/null 2>&1; then
	fail 'stager accepted missing arguments'
fi

echo 'PASS persistent service-state stager is exact-scope, power-gated, bounded, no-replace, and relock-safe'
