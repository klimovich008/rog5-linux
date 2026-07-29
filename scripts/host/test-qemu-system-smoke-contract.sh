#!/usr/bin/env bash
# shellcheck disable=SC2016
set -euo pipefail

fail() {
	echo "FAIL $*" >&2
	exit 1
}

repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
source_file=$repo/tools/qemu-smoke/init.c
builder=$repo/scripts/host/build-qemu-smoke-kernel.sh
cache_integration=$repo/scripts/host/test-kernel-build-cache-integration.sh
runner=$repo/scripts/host/test-qemu-system-smoke.sh
workflow=$repo/.github/workflows/offline-smoke.yml
for path in "$source_file" "$builder" "$cache_integration" "$runner" "$workflow"; do
	[[ -f $path && ! -L $path ]] || fail "missing QEMU smoke source: $path"
done
for command in clang ld.lld readelf strings; do
	command -v "$command" >/dev/null ||
		fail "missing QEMU smoke contract command: $command"
done

test_root=$(mktemp -d)
trap 'rm -rf -- "$test_root"' EXIT HUP INT TERM
clang --target=aarch64-none-elf -fuse-ld=lld -nostdlib -static -fno-pic \
	-fno-stack-protector -Werror -Wall -Wextra \
	-Wl,--build-id=none,--entry=_start \
	"$source_file" -o "$test_root/init"
readelf -h "$test_root/init" | grep -q 'Machine:.*AArch64'
if readelf -l "$test_root/init" | grep -q INTERP; then
	fail 'QEMU smoke init has a dynamic interpreter'
fi
strings "$test_root/init" |
	grep -qx 'PASS qemu-system arm64 initramfs boot'
grep -Fq '7a5cef0db4795d9d453a12e0f61b5b7634fc4d40' "$builder"
grep -Fq 'LLVM=1 tinyconfig' "$builder"
grep -Fq 'rog5_kernel_prepare_output "$output_root" "$build_state"' "$builder"
grep -Fq 'rog5_kernel_make -s -C "$source_root"' "$builder"
grep -Fq 'KBUILD_BUILD_TIMESTAMP=' "$builder"
grep -Fq 'fresh cached and uncached Images differ' "$cache_integration"
grep -Fq 'INCREMENTAL_BUILD=1' "$cache_integration"
grep -Fq "hashFiles('scripts/host/build-qemu-smoke-kernel.sh', 'scripts/device/kernel-build-contract.sh')" \
	"$workflow" ||
	fail 'QEMU cache key does not bind the shared kernel build contract'
for option in BLK_DEV_INITRD BINFMT_ELF PRINTK RD_GZIP \
	SERIAL_AMBA_PL011_CONSOLE; do
	grep -Fq -- "--enable $option" "$builder" ||
		fail "minimal QEMU kernel is missing $option"
done
grep -Fq -- '-M virt' "$runner"
grep -Fq -- '-nic none' "$runner"
grep -Fq -- '-fuse-ld=lld' "$runner"
grep -Fq "rdinit=/init" "$runner"
if grep -Eq 'fastboot|/dev/(sd|nvme|ufs)|mount[[:space:]].*root=' \
	"$runner"; then
	fail 'board-neutral QEMU smoke contains a phone or storage action'
fi

echo 'PASS board-neutral full-system QEMU smoke contract'
