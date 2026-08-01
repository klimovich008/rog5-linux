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
handoff_source=$repo/tools/qemu-diagnostic-handoff/init.c
handoff_runner=$repo/scripts/host/test-qemu-diagnostic-handoff.sh
workflow=$repo/.github/workflows/offline-smoke.yml
for path in "$source_file" "$builder" "$cache_integration" "$runner" \
	"$handoff_source" "$handoff_runner" "$workflow"; do
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
for option in BLK_DEV_INITRD BINFMT_ELF FILE_LOCKING PRINTK PROC_FS RD_GZIP \
	SERIAL_AMBA_PL011_CONSOLE TMPFS UNIX VIRTIO VIRTIO_CONSOLE VIRTIO_MMIO; do
	grep -Fq -- "--enable $option" "$builder" ||
		fail "minimal QEMU kernel is missing $option"
done
grep -Fq -- '-M virt' "$runner"
grep -Fq -- '-nic none' "$runner"
grep -Fq -- '-fuse-ld=lld' "$runner"
grep -Fq "rdinit=/init" "$runner"
for token in \
	'tools/early_target_diag/rog5-early-target-diag.c' \
	'-device virtio-serial-device' \
	'-device virtconsole,chardev=diagnostic' \
	'PASS qemu diagnostic reporter survived root handoff' \
	'DiagnosticStream("headless-netroot-early-diag-v1")' \
	'reporter_source_sha256=f8f35865d2c1918c6514c651705bf825a678d2e1084743ad1191306123986361' \
	'for required in (10, 120, 130, 140)'; do
	grep -Fq -- "$token" "$handoff_runner" ||
		fail "QEMU diagnostic handoff contract is missing: $token"
done
grep -Fq 'enter_new_root("/newroot", "/sbin/init")' "$handoff_source"
grep -Fq 'require_emit("130")' "$handoff_source"
grep -Fq 'require_emit("140")' "$handoff_source"
reporter_start_line=$(grep -n 'reporter_pid = start_reporter();' \
	"$handoff_source" | cut -d: -f1)
tty_alias_line=$(grep -n 'symlink("/dev/hvc0", "/dev/ttyGS0")' \
	"$handoff_source" | cut -d: -f1)
[[ $reporter_start_line -lt $tty_alias_line ]] ||
	fail 'QEMU reporter no longer starts before its transport exists'
grep -Fq 'test-qemu-diagnostic-handoff.sh' "$workflow"
if grep -Eq 'fastboot|/dev/(sd|nvme|ufs)|mount[[:space:]].*root=' \
	"$runner" "$handoff_runner"; then
	fail 'board-neutral QEMU smoke contains a phone or storage action'
fi

echo 'PASS board-neutral full-system QEMU smoke contract'
