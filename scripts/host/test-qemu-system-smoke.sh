#!/usr/bin/env bash
set -euo pipefail

fail() {
	echo "FAIL $*" >&2
	exit 1
}

[[ $# == 1 ]] ||
	fail 'usage: test-qemu-system-smoke.sh ARM64_KERNEL_IMAGE'
kernel=$(realpath -e -- "$1") || fail 'cannot resolve ARM64 kernel Image'
repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
source_file=$repo/tools/qemu-smoke/init.c
for command in clang cpio find gzip ld.lld qemu-system-aarch64 readelf \
	realpath sort timeout; do
	command -v "$command" >/dev/null ||
		fail "missing QEMU smoke command: $command"
done
[[ -f $kernel && ! -L $kernel && $(stat -c %s "$kernel") -gt 1048576 ]] ||
	fail 'unsafe or implausibly small kernel Image'
[[ -f $source_file && ! -L $source_file ]] ||
	fail 'missing QEMU smoke init source'

test_root=$(mktemp -d)
trap 'rm -rf -- "$test_root"' EXIT HUP INT TERM
stage=$test_root/stage
mkdir -p "$stage/dev"
clang --target=aarch64-none-elf -fuse-ld=lld -nostdlib -static -fno-pic \
	-fno-stack-protector -Werror -Wall -Wextra \
	-Wl,--build-id=none,--entry=_start \
	"$source_file" -o "$stage/init"
chmod 0755 "$stage/init"
readelf -h "$stage/init" | grep -q 'Machine:.*AArch64'
(
	cd "$stage"
	find . -mindepth 1 -print0 | sort -z |
		cpio --null -o --quiet --format=newc --owner=0:0
) | gzip -n >"$test_root/initramfs.cpio.gz"

set +e
timeout --signal=TERM --kill-after=2 30 \
	qemu-system-aarch64 \
		-M virt \
		-cpu cortex-a57 \
		-m 256M \
		-accel tcg,thread=multi \
		-display none \
		-monitor none \
		-nic none \
		-serial stdio \
		-no-reboot \
		-kernel "$kernel" \
		-initrd "$test_root/initramfs.cpio.gz" \
		-append 'console=ttyAMA0 rdinit=/init panic=-1' \
		>"$test_root/qemu.log" 2>&1
qemu_status=$?
set -e
if ! grep -Fq 'PASS qemu-system arm64 initramfs boot' \
	"$test_root/qemu.log"; then
	sed -n '1,240p' "$test_root/qemu.log" >&2
	fail "QEMU did not reach PID 1; status=$qemu_status"
fi

echo 'PASS full-system ARM64 kernel-to-initramfs handoff'
