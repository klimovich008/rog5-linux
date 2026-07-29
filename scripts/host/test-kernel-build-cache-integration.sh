#!/usr/bin/env bash
set -euo pipefail

fail() {
	echo "FAIL $*" >&2
	exit 1
}

[[ $# == 2 ]] ||
	fail 'usage: test-kernel-build-cache-integration.sh LINUX_SOURCE EMPTY_PROOF_DIRECTORY'
repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
builder=$repo/scripts/host/build-qemu-smoke-kernel.sh
source_root=$(realpath -e -- "$1") ||
	fail 'cannot resolve Linux source'
proof_root=$(realpath -m -- "$2") ||
	fail 'cannot resolve proof directory'
case $proof_root in
	"$repo"/build/*) ;;
	*) fail 'proof directory must be below the ignored repository build directory' ;;
esac
git -C "$repo" check-ignore -q "$proof_root" ||
	fail 'proof directory is not ignored by Git'
[[ ! -e $proof_root ]] ||
	[[ -d $proof_root && ! -L $proof_root &&
		-z $(find "$proof_root" -mindepth 1 -maxdepth 1 -print -quit) ]] ||
	fail 'proof directory must not exist or must be empty'
[[ -x $builder && ! -L $builder ]] ||
	fail 'QEMU kernel builder is unavailable'
command -v ccache >/dev/null ||
	fail 'ccache is unavailable'

mkdir -p "$proof_root"
uncached=$proof_root/uncached
cached=$proof_root/cached
export CCACHE_DIR=$proof_root/ccache
jobs=${JOBS:-$(nproc)}
ccache --zero-stats >/dev/null

JOBS=$jobs KBUILD_CCACHE=0 \
	"$builder" "$source_root" "$uncached"
JOBS=$jobs KBUILD_CCACHE=1 \
	"$builder" "$source_root" "$cached"

cmp "$uncached/.config" "$cached/.config" ||
	fail 'fresh cached and uncached configs differ'
cmp "$uncached/arch/arm64/boot/Image" \
	"$cached/arch/arm64/boot/Image" ||
	fail 'fresh cached and uncached Images differ'
uncached_sha=$(sha256sum "$uncached/arch/arm64/boot/Image" |
	cut -d ' ' -f 1)
cached_sha=$(sha256sum "$cached/arch/arm64/boot/Image" |
	cut -d ' ' -f 1)

JOBS=$jobs KBUILD_CCACHE=1 INCREMENTAL_BUILD=1 \
	"$builder" "$source_root" "$cached"
incremental_sha=$(sha256sum "$cached/arch/arm64/boot/Image" |
	cut -d ' ' -f 1)
[[ $uncached_sha == "$cached_sha" &&
	$cached_sha == "$incremental_sha" ]] ||
	fail 'fresh/cached/incremental Image identities differ'
direct_hits=$(ccache --print-stats |
	awk '$1 == "direct_cache_hit" { print $2 }')
[[ $direct_hits =~ ^[0-9]+$ && $direct_hits -gt 0 ]] ||
	fail 'real cached build recorded no direct ccache hit'

printf 'source_commit=%s\n' "$(git -C "$source_root" rev-parse HEAD)"
printf 'uncached_image_sha256=%s\n' "$uncached_sha"
printf 'cached_image_sha256=%s\n' "$cached_sha"
printf 'incremental_image_sha256=%s\n' "$incremental_sha"
printf 'image_size=%s\n' \
	"$(stat -c %s "$cached/arch/arm64/boot/Image")"
printf 'direct_cache_hits=%s\n' "$direct_hits"
ccache --show-stats
echo 'PASS real ARM64 QEMU Images match across fresh uncached, fresh cached, and repeated incremental builds'
