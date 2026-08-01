#!/usr/bin/env bash
set -euo pipefail

fail() {
	echo "FAIL $*" >&2
	exit 1
}

[[ $# == 1 ]] ||
	fail 'usage: test-qemu-diagnostic-handoff.sh ARM64_KERNEL_IMAGE'
kernel=$(realpath -e -- "$1") || fail 'cannot resolve ARM64 kernel Image'
repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
harness_source=$repo/tools/qemu-diagnostic-handoff/init.c
reporter_source=$repo/tools/early_target_diag/rog5-early-target-diag.c
reporter_source_sha256=f8f35865d2c1918c6514c651705bf825a678d2e1084743ad1191306123986361
parser=$repo/scripts/host/early-target-diagnostics.py
compiler=${CROSS_CC:-aarch64-linux-gnu-gcc}
for command in cpio find gzip python3 qemu-system-aarch64 realpath \
	readelf sha256sum sort strings timeout "$compiler"; do
	command -v "$command" >/dev/null ||
		fail "missing QEMU diagnostic handoff command: $command"
done
[[ $(sha256sum "$reporter_source" | cut -d ' ' -f 1) == \
	"$reporter_source_sha256" ]] || fail 'QEMU reporter source seal changed'
for source in "$harness_source" "$reporter_source" "$parser"; do
	[[ -f $source && ! -L $source ]] || fail "missing handoff source: $source"
done
[[ -f $kernel && ! -L $kernel && $(stat -c %s "$kernel") -gt 1048576 ]] ||
	fail 'unsafe or implausibly small kernel Image'

test_root=$(mktemp -d)
trap 'rm -rf -- "$test_root"' EXIT HUP INT TERM
stage=$test_root/stage
mkdir -p "$stage/dev" "$stage/sbin"
"$compiler" -std=c11 -O2 -static -fPIE -pie \
	-fstack-protector-strong -Wall -Wextra -Werror \
	-Wl,-z,relro,-z,now,-z,noexecstack,--build-id=none -s \
	"$reporter_source" -o "$stage/sbin/rog5-early-target-diag"
"$compiler" -std=c11 -O2 -static -fPIE -pie \
	-fstack-protector-strong -Wall -Wextra -Werror \
	-Wl,-z,relro,-z,now,-z,noexecstack,--build-id=none -s \
	"$harness_source" -o "$stage/qemu-diagnostic-handoff"
cp "$stage/qemu-diagnostic-handoff" "$stage/init"
chmod 0755 "$stage/init" "$stage/qemu-diagnostic-handoff" \
	"$stage/sbin/rog5-early-target-diag"
for binary in "$stage/init" "$stage/sbin/rog5-early-target-diag"; do
	readelf -h "$binary" | grep -q 'Machine:.*AArch64' ||
		fail 'QEMU handoff binary is not AArch64'
	if readelf -l "$binary" | grep -q 'Requesting program interpreter'; then
		fail 'QEMU handoff binary is dynamically linked'
	fi
done
if strings "$stage/sbin/rog5-early-target-diag" |
	grep -q 'ROG5_DIAG_TEST_'; then
	fail 'QEMU handoff reporter contains a test-hook interface'
fi
(
	cd "$stage"
	find . -mindepth 1 -print0 | sort -z |
		cpio --null -o --quiet --format=newc --owner=0:0
) | gzip -n >"$test_root/initramfs.cpio.gz"

set +e
timeout --signal=TERM --kill-after=2 60 \
	qemu-system-aarch64 \
		-M virt \
		-cpu cortex-a57 \
		-m 256M \
		-accel tcg,thread=multi \
		-display none \
		-monitor none \
		-nic none \
		-serial "file:$test_root/console.log" \
		-chardev "file,id=diagnostic,path=$test_root/diagnostic.frames" \
		-device virtio-serial-device \
		-device virtconsole,chardev=diagnostic,name=rog5-diagnostic \
		-no-reboot \
		-kernel "$kernel" \
		-initrd "$test_root/initramfs.cpio.gz" \
		-append 'console=ttyAMA0 rdinit=/init panic=-1 quiet' \
		>/dev/null 2>"$test_root/qemu.stderr"
qemu_status=$?
set -e
if ((qemu_status != 0)) ||
	! grep -Fq 'PASS qemu diagnostic reporter survived root handoff' \
	"$test_root/console.log"; then
	sed -n '1,240p' "$test_root/console.log" >&2
	sed -n '1,120p' "$test_root/qemu.stderr" >&2
	fail "QEMU did not complete diagnostic root handoff; status=$qemu_status"
fi

python3 - "$parser" "$test_root/diagnostic.frames" <<'PY'
import importlib.util
from pathlib import Path
import sys

parser_source = Path(sys.argv[1])
frames = Path(sys.argv[2]).read_bytes()
spec = importlib.util.spec_from_file_location(
    "rog5_early_target_diagnostics", parser_source
)
assert spec is not None and spec.loader is not None
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)
stream = module.DiagnosticStream("headless-netroot-early-diag-v1")
records = stream.feed(frames)
stream.finalize()
codes = [record.stage_code for record in records]
positions = []
for required in (10, 120, 130, 140):
    try:
        positions.append(codes.index(required))
    except ValueError as error:
        raise SystemExit(f"missing diagnostic handoff stage {required}") from error
if positions != sorted(positions) or len(set(positions)) != len(positions):
    raise SystemExit("diagnostic handoff stages are out of order")
if any(code in (200, 210) for code in codes):
    raise SystemExit("diagnostic handoff emitted a terminal stage")
if stream.maximum_progress != 140 or stream.terminal is not None:
    raise SystemExit("diagnostic handoff did not end at sshd-active")
print(
    "PASS canonical reporter stream crossed root handoff "
    f"frames={len(records)} boot_id={stream.boot_id}"
)
PY

echo 'PASS ARM64 diagnostic reporter root-handoff continuity'
