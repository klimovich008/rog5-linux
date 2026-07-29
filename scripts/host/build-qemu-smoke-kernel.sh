#!/usr/bin/env bash
set -euo pipefail

fail() {
	echo "FAIL $*" >&2
	exit 1
}

[[ $# == 2 ]] ||
	fail 'usage: build-qemu-smoke-kernel.sh LINUX_SOURCE OUTPUT_DIRECTORY'
source_root=$(realpath -e -- "$1") ||
	fail 'cannot resolve Linux source'
output_root=$(realpath -m -- "$2") ||
	fail 'cannot resolve output directory'
repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
expected_commit=7a5cef0db4795d9d453a12e0f61b5b7634fc4d40

[[ -d $source_root && ! -L $source_root ]] ||
	fail 'Linux source is not a regular directory'
[[ $(git -C "$source_root" rev-parse HEAD) == "$expected_commit" ]] ||
	fail 'Linux source is not the pinned v7.1.4 commit'
case $output_root in
	"$repo"/build/*) ;;
	*) fail 'output must be below the ignored repository build directory' ;;
esac
git -C "$repo" check-ignore -q "$output_root" ||
	fail 'QEMU kernel output is not ignored by Git'
for command in clang git make realpath; do
	command -v "$command" >/dev/null ||
		fail "missing QEMU kernel build command: $command"
done

mkdir -p "$output_root"
export ARCH=arm64
export KBUILD_BUILD_TIMESTAMP='2026-07-18 00:00:00 UTC'
export KBUILD_BUILD_USER=rog5
export KBUILD_BUILD_HOST=qemu-smoke
make -s -C "$source_root" O="$output_root" LLVM=1 defconfig
config=$source_root/scripts/config
[[ -x $config ]] || fail 'Linux scripts/config is unavailable'
"$config" --file "$output_root/.config" \
	--enable BLK_DEV_INITRD \
	--enable DEVTMPFS \
	--enable DEVTMPFS_MOUNT \
	--enable SERIAL_AMBA_PL011 \
	--enable SERIAL_AMBA_PL011_CONSOLE \
	--enable TTY \
	--disable DEBUG_INFO
make -s -C "$source_root" O="$output_root" LLVM=1 olddefconfig
make -s -C "$source_root" O="$output_root" LLVM=1 \
	-j"${JOBS:-$(nproc)}" Image

image=$output_root/arch/arm64/boot/Image
[[ -f $image && ! -L $image && $(stat -c %s "$image") -gt 1048576 ]] ||
	fail 'QEMU kernel Image is missing or implausibly small'
sha256sum "$output_root/.config" "$image"
echo 'PASS built incremental ARM64 QEMU virt kernel'
