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
systemd_runtime=$repo/artifacts/qemu-systemd-arm64-v1/runtime.cpio.gz
systemd_runtime_builder=$repo/scripts/host/build-qemu-systemd-runtime.sh
systemd_runtime_verifier=$repo/scripts/host/verify-qemu-systemd-runtime.sh
workflow=$repo/.github/workflows/offline-smoke.yml
for path in "$source_file" "$builder" "$cache_integration" "$runner" \
	"$handoff_source" "$handoff_runner" "$systemd_runtime" \
	"$systemd_runtime_builder" "$systemd_runtime_verifier" "$workflow"; do
	[[ -f $path && ! -L $path ]] || fail "missing QEMU smoke source: $path"
done
for command in clang ld.lld readelf strings; do
	command -v "$command" >/dev/null ||
		fail "missing QEMU smoke contract command: $command"
done

test_root=$(mktemp -d)
trap 'find "$test_root" -depth -delete 2>/dev/null || true' EXIT HUP INT TERM
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
[[ $(grep -Fc "key: qemu-linux-arm64-v7.1.4-7a5cef0-\${{ runner.os }}-\${{ hashFiles('scripts/host/build-qemu-smoke-kernel.sh', 'scripts/device/kernel-build-contract.sh') }}" \
	"$workflow") == 2 ]] ||
	fail 'QEMU restore and immediate-save cache keys differ'
grep -Fq 'uses: actions/cache/save@v4' "$workflow" ||
	fail 'QEMU kernel is not cached immediately after a successful build'
for option in BLK_DEV_INITRD BINFMT_ELF CGROUPS EPOLL FHANDLE FILE_LOCKING \
	FUTEX INOTIFY_USER MEMFD_CREATE NET PRINTK PROC_FS RD_GZIP \
	SERIAL_AMBA_PL011_CONSOLE SHMEM SIGNALFD SYSFS TIMERFD TMPFS UNIX \
	VIRTIO VIRTIO_CONSOLE VIRTIO_MENU VIRTIO_MMIO; do
	grep -Eq "(^|[[:space:]])$option([[:space:]]|$)" "$builder" ||
		fail "minimal QEMU kernel is missing $option"
done
grep -Fq 'config_arguments+=(--enable "$required_runtime_option")' "$builder" ||
	fail 'minimal QEMU kernel does not derive enable arguments from its required list'
[[ $(grep -Fc 'for required_runtime_option in "${required_runtime_options[@]}"; do' \
	"$builder") == 2 ]] ||
	fail 'minimal QEMU kernel does not verify the same resolved option list'
grep -Fq 'QEMU kernel lost $required_runtime_option after olddefconfig' \
	"$builder" || fail 'QEMU runtime prerequisites are not checked after resolution'
grep -Fq -- '-M virt' "$runner"
grep -Fq -- '-nic none' "$runner"
grep -Fq -- '-fuse-ld=lld' "$runner"
grep -Fq "rdinit=/init" "$runner"
for token in \
	'tools/early_target_diag/rog5-early-target-diag.c' \
	'verify-qemu-systemd-runtime.sh' \
	'install_diagnostic_units' \
	'-device virtio-serial-device' \
	'-device virtconsole,chardev=diagnostic' \
	'PASS generated diagnostic units ran under ARM64 systemd' \
	'DiagnosticStream("headless-netroot-early-diag-v1")' \
	'reporter_source_sha256=2f8a3bc21a43b415f08a341d01179603401842df25da0b3ce17a67f5cdbd8a65' \
	'for required in (10, 120, 130, 140)'; do
	grep -Fq -- "$token" "$handoff_runner" ||
		fail "QEMU diagnostic handoff contract is missing: $token"
done
grep -Fq 'enter_new_root("/newroot", SYSTEMD)' "$handoff_source"
grep -Fq 'strcmp(pid_one, SYSTEMD)' "$handoff_source"
grep -Fq 'bind_file(REPORTER, RETAINED_REPORTER)' "$handoff_source"
grep -Fq '#define PUBLICATION_SETTLE_MS 500' "$handoff_source"
[[ $(grep -Fc 'sleep_milliseconds(PUBLICATION_SETTLE_MS);' \
	"$handoff_source") == 2 ]] ||
	fail 'QEMU harness does not preserve both reporter publication windows'
if grep -Eq 'require_emit\("(130|140)"\)' "$handoff_source"; then
	fail 'QEMU harness directly emits a systemd-owned diagnostic stage'
fi
reporter_start_line=$(grep -n 'reporter_pid = start_reporter();' \
	"$handoff_source" | cut -d: -f1)
tty_alias_line=$(grep -n 'symlink("/dev/hvc0", "/dev/ttyGS0")' \
	"$handoff_source" | cut -d: -f1)
[[ $reporter_start_line -lt $tty_alias_line ]] ||
	fail 'QEMU reporter no longer starts before its transport exists'
grep -Fq 'test-qemu-diagnostic-handoff.sh' "$workflow"
grep -Fq 'libc6-dev-arm64-cross' "$workflow" ||
	fail 'QEMU workflow lacks the ARM64 static libc development package'
if grep -Eq 'fastboot|/dev/(sd|nvme|ufs)|mount[[:space:]].*root=' \
	"$runner" "$handoff_runner"; then
	fail 'board-neutral QEMU smoke contains a phone or storage action'
fi

echo 'PASS board-neutral full-system QEMU smoke contract'
