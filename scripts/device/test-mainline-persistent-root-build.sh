#!/bin/sh
set -eu

repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)
fragment=$repo/configs/kernel/rog5-persistent-root.fragment
builder=$repo/scripts/device/build-mainline-persistent-root.sh
verifier=$repo/scripts/device/verify-mainline-persistent-root-build.sh
meta_verifier=$repo/scripts/device/verify-build-meta-hash.sh

for path in "$fragment" "$builder" "$verifier" "$meta_verifier"; do
	[ -f "$path" ] || {
		echo "FAIL missing P2 kernel build input: $path" >&2
		exit 1
	}
done
[ -x "$builder" ] && [ -x "$verifier" ] && [ -x "$meta_verifier" ]
sh -n "$builder"
sh -n "$verifier"
sh -n "$meta_verifier"

for symbol in \
	CONFIG_EXT4_FS=y \
	CONFIG_EXT4_FS_POSIX_ACL=y \
	CONFIG_EXT4_FS_SECURITY=y \
	CONFIG_OVERLAY_FS=y \
	CONFIG_TMPFS=y \
	CONFIG_TMPFS_XATTR=y; do
	grep -qx "$symbol" "$fragment"
done

grep -Fq 'rog5-mainline.fragment' "$builder"
grep -Fq 'rog5-ufs-discovery.fragment' "$builder"
grep -Fq 'rog5-persistent-root.fragment' "$builder"
grep -Fq 'expected_tree=d2f03d2055227b8b72ab41be949847a066924c5a' \
	"$builder"
grep -Fq 'CONFIG_OVERLAY_FS=y' "$verifier"
grep -Fq 'verify-mainline-discovery-build.sh' "$verifier"

tmp=$(mktemp -d)
trap 'rm -rf -- "$tmp"' EXIT HUP INT TERM
printf 'exact input\n' >"$tmp/actual"
hash=$(sha256sum "$tmp/actual" | cut -d ' ' -f 1)
printf '%s  /workspace/configs/kernel/rog5-persistent-root.fragment\n' \
	"$hash" >"$tmp/meta"
"$meta_verifier" "$tmp/meta" \
	/configs/kernel/rog5-persistent-root.fragment "$tmp/actual"
printf '%s  /repo/configs/kernel/rog5-persistent-root.fragment\n' \
	"$hash" >"$tmp/meta"
"$meta_verifier" "$tmp/meta" \
	/configs/kernel/rog5-persistent-root.fragment "$tmp/actual"
printf '%s  /workspace/configs/kernel/rog5-persistent-root.fragment\n' \
	"$hash" >>"$tmp/meta"
if "$meta_verifier" "$tmp/meta" \
	/configs/kernel/rog5-persistent-root.fragment "$tmp/actual" \
	>"$tmp/out" 2>"$tmp/err"; then
	echo 'FAIL metadata verifier accepted duplicate suffix records' >&2
	exit 1
fi
printf '%064d  /workspace/configs/kernel/rog5-persistent-root.fragment\n' \
	0 >"$tmp/meta"
if "$meta_verifier" "$tmp/meta" \
	/configs/kernel/rog5-persistent-root.fragment "$tmp/actual" \
	>"$tmp/out" 2>"$tmp/err"; then
	echo 'FAIL metadata verifier accepted the wrong hash' >&2
	exit 1
fi

case $# in
	0) ;;
	2)
		"$verifier" "$1"
		"$verifier" "$2"
		"$repo/scripts/device/compare-mainline-discovery-builds.sh" \
			"$1" "$2"
		;;
	*)
		echo 'usage: test-mainline-persistent-root-build.sh [BUILD_A BUILD_B]' >&2
		exit 1
		;;
esac

echo 'PASS P2 kernel contract reuses the accepted UFS guards and builds ext4, OverlayFS, and tmpfs into the image'
