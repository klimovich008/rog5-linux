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
kernel_contract=$repo/scripts/device/kernel-build-contract.sh
expected_commit=7a5cef0db4795d9d453a12e0f61b5b7634fc4d40

[[ -d $source_root && ! -L $source_root ]] ||
	fail 'Linux source is not a regular directory'
[[ -f $kernel_contract && ! -L $kernel_contract &&
	$(stat -c '%u' "$kernel_contract") == "$(id -u)" &&
	$(stat -c '%a' "$kernel_contract") == 755 ]] ||
	fail 'kernel build contract is unavailable or unsafe'
kernel_contract_sha256=$(sha256sum "$kernel_contract" | cut -d ' ' -f 1)
# shellcheck disable=SC1090,SC1091
. "$kernel_contract"
[[ $(git -C "$source_root" rev-parse HEAD) == "$expected_commit" ]] ||
	fail 'Linux source is not the pinned v7.1.4 commit'
[[ -z $(git -C "$source_root" status --porcelain) ]] ||
	fail 'Linux source has uncommitted changes'
case $output_root in
	"$repo"/build/*) ;;
	*) fail 'output must be below the ignored repository build directory' ;;
esac
case $output_root in
	"$source_root"|"$source_root"/*)
		fail 'QEMU kernel output must be outside the source tree'
		;;
esac
git -C "$repo" check-ignore -q "$output_root" ||
	fail 'QEMU kernel output is not ignored by Git'
for command in bc clang git make realpath; do
	command -v "$command" >/dev/null ||
		fail "missing QEMU kernel build command: $command"
done

mkdir -p "$output_root"
export ARCH=arm64
export KBUILD_BUILD_TIMESTAMP='2026-07-18 00:00:00 UTC'
export KBUILD_BUILD_USER=rog5
export KBUILD_BUILD_HOST=qemu-smoke
cache_identity=$(rog5_kernel_cache_identity)
toolchain_identity=$(rog5_kernel_toolchain_identity \
	make bc clang clang++ ld.lld llvm-ar llvm-nm llvm-objcopy llvm-strip)
build_state=$(
	printf 'format=rog5-kbuild-inputs-v1\n'
	printf 'profile=qemu-system-arm64-tiny-v1\n'
	printf 'source_path=%s\n' "$source_root"
	printf 'output_path=%s\n' "$output_root"
	printf 'source_commit=%s\n' "$expected_commit"
	printf 'source_tree=%s\n' \
		"$(git -C "$source_root" rev-parse 'HEAD^{tree}')"
	printf 'builder_sha256=%s\n' \
		"$(sha256sum "${BASH_SOURCE[0]}" | cut -d ' ' -f 1)"
	printf 'contract_sha256=%s\n' "$kernel_contract_sha256"
	printf 'arch=arm64\nllvm=1\n'
	printf 'kbuild_timestamp=%s\n' "$KBUILD_BUILD_TIMESTAMP"
	printf 'kbuild_user=%s\n' "$KBUILD_BUILD_USER"
	printf 'kbuild_host=%s\n' "$KBUILD_BUILD_HOST"
	printf '%s\n' "$cache_identity" "$toolchain_identity"
)
rog5_kernel_prepare_output "$output_root" "$build_state"
rog5_kernel_cache_stats

rog5_kernel_make -s -C "$source_root" O="$output_root" LLVM=1 tinyconfig
config=$source_root/scripts/config
[[ -x $config ]] || fail 'Linux scripts/config is unavailable'
required_runtime_options=(
	BLK_DEV_INITRD BINFMT_ELF CGROUPS DEVTMPFS DEVTMPFS_MOUNT EPOLL
	FHANDLE FILE_LOCKING FUTEX INET INOTIFY_USER IP_PNP MEMFD_CREATE MULTIUSER NET
	NETDEVICES NFS_FS NFS_V4 NFS_V4_2 POSIX_TIMERS PRINTK PROC_FS RD_GZIP
	OVERLAY_FS ROOT_NFS SECCOMP SECCOMP_FILTER SUNRPC
	SERIAL_AMBA_PL011 SERIAL_AMBA_PL011_CONSOLE SHMEM SIGNALFD SYSFS TIMERFD TMPFS TMPFS_XATTR TTY UNIX
	VIRTIO VIRTIO_CONSOLE VIRTIO_MENU VIRTIO_MMIO VIRTIO_NET
)
config_arguments=()
for required_runtime_option in "${required_runtime_options[@]}"; do
	config_arguments+=(--enable "$required_runtime_option")
done
"$config" --file "$output_root/.config" \
	"${config_arguments[@]}" --disable DEBUG_INFO
rog5_kernel_make -s -C "$source_root" O="$output_root" LLVM=1 olddefconfig
required_runtime_options+=(HVC_DRIVER)
for required_runtime_option in "${required_runtime_options[@]}"; do
	grep -Fqx "CONFIG_${required_runtime_option}=y" "$output_root/.config" ||
		fail "QEMU kernel lost $required_runtime_option after olddefconfig"
done
rog5_kernel_make -s -C "$source_root" O="$output_root" LLVM=1 \
	-j"${JOBS:-$(nproc)}" Image
rog5_kernel_cache_stats

image=$output_root/arch/arm64/boot/Image
[[ -f $image && ! -L $image && $(stat -c %s "$image") -gt 1048576 ]] ||
	fail 'QEMU kernel Image is missing or implausibly small'
sha256sum "$output_root/.config" "$image"
echo 'PASS built minimal ARM64 QEMU virt kernel'
