#!/usr/bin/env bash
set -euo pipefail

fail() {
	echo "FAIL $*" >&2
	exit 1
}

[[ $# == 1 ]] ||
	fail 'usage: test-qemu-network-root-nfs.sh ARM64_KERNEL_IMAGE'
kernel=$(realpath -e -- "$1") || fail 'cannot resolve ARM64 kernel Image'
repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
source_file=$repo/tools/qemu-network-root-nfs/init.c
config_template=$repo/tools/qemu-network-root-nfs/ganesha.conf.in
compiler=${CROSS_CC:-aarch64-linux-gnu-gcc}
for command in cp cpio find ganesha.nfsd grep gzip mkdir mktemp python3 \
	qemu-system-aarch64 realpath sed sort tail timeout "$compiler"; do
	command -v "$command" >/dev/null ||
		fail "missing QEMU NFS command: $command"
done
for source in "$source_file" "$config_template"; do
	[[ -f $source && ! -L $source ]] ||
		fail "missing QEMU NFS source: $source"
done
[[ -f $kernel && ! -L $kernel && $(stat -c %s "$kernel") -gt 1048576 ]] ||
	fail 'unsafe or implausibly small kernel Image'

test_root=$(mktemp -d)
ganesha_pid=
cleanup() {
	if [[ -n $ganesha_pid ]]; then
		kill -TERM "$ganesha_pid" 2>/dev/null || true
		wait "$ganesha_pid" 2>/dev/null || true
	fi
	find "$test_root" -depth -delete 2>/dev/null || true
}
trap cleanup EXIT HUP INT TERM
stage=$test_root/stage
mkdir -p "$stage/proc" "$stage/mnt/root-ro"
cp -- "$config_template" "$test_root/ganesha.conf"

"$compiler" -std=c11 -O2 -static -fPIE -pie \
	-fstack-protector-strong -Wall -Wextra -Werror \
	-Wl,-z,relro,-z,now,-z,noexecstack,--build-id=none -s \
	"$source_file" -o "$stage/init"
chmod 0755 "$stage/init"
(
	cd "$stage"
	find . -mindepth 1 -print0 | sort -z |
		cpio --null -o --quiet --format=newc --owner=0:0
) | gzip -n >"$test_root/initramfs.cpio.gz"

ganesha.nfsd -F -N "${GANESHA_LOG_LEVEL:-NIV_EVENT}" \
	-L "$test_root/ganesha.log" \
	-f "$test_root/ganesha.conf" -p "$test_root/ganesha.pid" \
	>"$test_root/ganesha.console" 2>&1 &
ganesha_pid=$!
ready=0
for _attempt in {1..100}; do
	if ! kill -0 "$ganesha_pid" 2>/dev/null; then
		tail -n 240 "$test_root/ganesha.log" >&2
		tail -n 80 "$test_root/ganesha.console" >&2
		fail 'NFS-Ganesha exited before readiness'
	fi
	if python3 - <<'PY'
import socket

try:
    with socket.create_connection(("127.0.0.1", 2049), timeout=0.1):
        pass
except OSError:
    raise SystemExit(1)
PY
	then
		ready=1
		break
	fi
	sleep 0.05
done
[[ $ready == 1 ]] || fail 'NFS-Ganesha did not bind TCP port 2049'

set +e
timeout --signal=TERM --kill-after=2 45 \
	qemu-system-aarch64 \
		-M virt \
		-cpu cortex-a57 \
		-m 256M \
		-accel tcg,thread=multi \
		-display none \
		-monitor none \
		-serial stdio \
		-no-reboot \
		-netdev user,id=nfsnet,net=169.254.77.0/24,\
host=169.254.77.3,dns=169.254.77.4,restrict=on,\
guestfwd=tcp:169.254.77.1:2049-tcp:127.0.0.1:2049 \
		-device virtio-net-device,netdev=nfsnet \
		-kernel "$kernel" \
		-initrd "$test_root/initramfs.cpio.gz" \
		-append 'console=ttyAMA0 rdinit=/init panic=-1 ip=169.254.77.2::169.254.77.1:255.255.255.252:rog5-qemu:eth0:off' \
		>"$test_root/qemu.log" 2>&1
qemu_status=$?
set -e
if ! grep -Fq \
	'PASS Linux 7.1.4 mounted exact NFSv4.2 root read-only' \
	"$test_root/qemu.log"; then
	sed -n '1,320p' "$test_root/qemu.log" >&2
	tail -n 240 "$test_root/ganesha.log" >&2
	tail -n 80 "$test_root/ganesha.console" >&2
	fail "QEMU did not mount the NFS root; status=$qemu_status"
fi

echo 'PASS full-system ARM64 exact NFSv4.2 read-only mount'
