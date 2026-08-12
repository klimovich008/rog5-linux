#!/bin/sh
set -eu

output_dir=${1:?usage: verify-mainline-persistent-root-build.sh BUILD_DIR}
repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)
meta=$output_dir/build-meta.txt
config=$output_dir/.config
image=$output_dir/arch/arm64/boot/Image
root_fragment=$repo/configs/kernel/rog5-persistent-root.fragment
verify_meta=$repo/scripts/device/verify-build-meta-hash.sh

"$repo/scripts/device/verify-mainline-discovery-build.sh" "$output_dir" \
	>/dev/null

"$verify_meta" "$meta" /configs/kernel/rog5-persistent-root.fragment \
	"$root_fragment"

for symbol in \
	CONFIG_EXT4_FS=y \
	CONFIG_EXT4_FS_POSIX_ACL=y \
	CONFIG_EXT4_FS_SECURITY=y \
	CONFIG_OVERLAY_FS=y \
	CONFIG_TMPFS=y \
	CONFIG_TMPFS_XATTR=y; do
	grep -qx "$symbol" "$config" || {
		echo "FAIL final P2 config: $symbol" >&2
		exit 1
	}
done
! grep -qx 'CONFIG_OVERLAY_FS=m' "$config"
strings "$image" |
	grep -Fq "overlayfs: overlay with incompat feature '%s' cannot be mounted"

echo 'PASS dedicated read-only persistent-root config, UFS guards, hashes, and Image.gz'
