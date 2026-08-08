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
production_harness=$repo/tools/qemu-network-root-nfs/production-init.sh
seed_init=$repo/tools/qemu-network-root-nfs/seed-init.sh
network_init=$repo/initramfs/network-root-init
config_template=$repo/tools/qemu-network-root-nfs/ganesha.conf.in
runtime=$repo/artifacts/network-root-v3/rog5-network-root-initramfs.cpio.gz
runtime_sha256=4f3077d02c40b5d27ab602562534cacf11324554ae75b0246fd4429bced9bbac
compiler=${CROSS_CC:-aarch64-linux-gnu-gcc}
for command in awk chmod cp cpio find ganesha.nfsd grep gzip mkdir mktemp \
	python3 qemu-system-aarch64 realpath sed sha256sum sort ss tail timeout \
	"$compiler"; do
	command -v "$command" >/dev/null ||
		fail "missing QEMU NFS command: $command"
done
for source in "$source_file" "$production_harness" "$seed_init" "$network_init" \
	"$config_template" "$runtime"; do
	[[ -f $source && ! -L $source ]] ||
		fail "missing QEMU NFS source: $source"
done
[[ $(sha256sum "$runtime" | cut -d ' ' -f 1) == "$runtime_sha256" ]] ||
	fail 'pinned network-root QEMU runtime hash changed'
[[ -f $kernel && ! -L $kernel && $(stat -c %s "$kernel") -gt 1048576 ]] ||
	fail 'unsafe or implausibly small kernel Image'
if ss -H -ltn 'sport = :2049' | grep -q .; then
	fail 'TCP port 2049 is already in use'
fi

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
seed_stage=$test_root/seed-stage
mkdir -p "$stage" "$seed_stage"
gzip -dc "$runtime" |
	(cd "$stage" && cpio -idm --quiet --no-absolute-filenames)
gzip -dc "$runtime" |
	(cd "$seed_stage" && cpio -idm --quiet --no-absolute-filenames)
mkdir -p "$stage/proc" "$stage/sys" "$stage/run" "$stage/mnt/root-ro"
cp -- "$seed_init" "$seed_stage/seed-init.sh"
chmod 0755 "$seed_stage/seed-init.sh"
sed 's/Access_Type = RO/Access_Type = RW/' "$config_template" \
	>"$test_root/ganesha.conf"
grep -Fq 'Access_Type = RW' "$test_root/ganesha.conf" ||
	fail 'QEMU NFS seed export did not become writable'

network_functions=$stage/network-functions.sh
awk '
	/^udc_candidate_count\(\) \{/ { copy=1 }
	/^install_diagnostic_units\(\) \{/ { copy=0 }
	copy { print }
' "$network_init" >"$network_functions"
grep -Fqx 'mount_network_root() {' "$network_functions" ||
	fail 'production network-root mount function was not extracted'
[[ $(grep -Fxc 'mount_network_root() {' "$network_functions") == 1 ]] ||
	fail 'production network-root mount function extraction is ambiguous'
cp -- "$production_harness" "$stage/production-init"

"$compiler" -std=c11 -O2 -static -fPIE -pie \
	-fstack-protector-strong -Wall -Wextra -Werror \
	-Wl,-z,relro,-z,now,-z,noexecstack,--build-id=none -s \
	"$source_file" -o "$stage/init"
chmod 0755 "$stage/init" "$stage/production-init"
cp -- "$stage/init" "$seed_stage/init"
(
	cd "$stage"
	find . -mindepth 1 -print0 | sort -z |
		cpio --null -o --quiet --format=newc --owner=0:0
) | gzip -n >"$test_root/initramfs.cpio.gz"
(
	cd "$seed_stage"
	find . -mindepth 1 -print0 | sort -z |
		cpio --null -o --quiet --format=newc --owner=0:0
) | gzip -n >"$test_root/seed-initramfs.cpio.gz"

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
grep -Fq 'NFS SERVER INITIALIZED' "$test_root/ganesha.log" ||
	fail 'NFS-Ganesha did not report successful initialization'
listener_owner=$(ss -H -ltnp 'sport = :2049')
if ! grep -Fq "pid=$ganesha_pid," <<<"$listener_owner"; then
	fail 'NFS-Ganesha did not own the NFSv4 TCP listener'
fi

run_qemu_guest() {
	local initramfs=$1
	local command_line=$2
	local output=$3

	timeout --signal=TERM --kill-after=2 45 qemu-system-aarch64 \
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
		-initrd "$initramfs" \
		-append "$command_line" \
		>"$output" 2>&1
}

set +e
run_qemu_guest \
	"$test_root/seed-initramfs.cpio.gz" \
	'console=ttyAMA0 rdinit=/init panic=-1 rog5.qemu_nfs_seed=1 ip=169.254.77.2::169.254.77.1:255.255.255.252:rog5-qemu-seed:eth0:off' \
	"$test_root/seed-qemu.log"
seed_status=$?
set -e
if ! grep -Fq 'PASS QEMU NFS fixture seeded over NFSv4.2' \
	"$test_root/seed-qemu.log"; then
	sed -n '1,320p' "$test_root/seed-qemu.log" >&2
	fail "QEMU did not seed the NFS fixture; status=$seed_status"
fi

cp -- "$config_template" "$test_root/ganesha.conf"
kill -HUP "$ganesha_pid"
reloaded=0
for _attempt in {1..100}; do
	if ! kill -0 "$ganesha_pid" 2>/dev/null; then
		fail 'NFS-Ganesha exited while making the fixture read-only'
	fi
	if grep -Fq 'Reread exports complete' "$test_root/ganesha.log"; then
		reloaded=1
		break
	fi
	sleep 0.05
done
[[ $reloaded == 1 ]] || fail 'NFS-Ganesha did not reload the read-only export'

set +e
run_qemu_guest \
	"$test_root/initramfs.cpio.gz" \
	'console=ttyAMA0 rdinit=/init panic=-1 ip=169.254.77.2::169.254.77.1:255.255.255.252:rog5-qemu:eth0:off' \
	"$test_root/qemu.log"
qemu_status=$?
set -e
if ! grep -Fq \
	'PASS production network-root shell assembled NFSv4.2 plus OverlayFS root' \
	"$test_root/qemu.log"; then
	sed -n '1,320p' "$test_root/qemu.log" >&2
	grep -Ei 'export|fsal|warn|crit|major' "$test_root/ganesha.log" |
		sed -n '1,240p' >&2 || true
	tail -n 240 "$test_root/ganesha.log" >&2
	tail -n 80 "$test_root/ganesha.console" >&2
	fail "QEMU did not mount the NFS root; status=$qemu_status"
fi
grep -Fq 'PASS Linux 7.1.4 mounted exact NFSv4.2 root read-only' \
	"$test_root/qemu.log" || fail 'direct kernel NFS probe did not complete'
grep -Fq 'PASS QEMU NFS server rejected an RW client write' \
	"$test_root/qemu.log" || fail 'server-side read-only probe did not complete'
[[ $(grep -Fc 'ROG5_QEMU_PRODUCTION_STAGE 70' "$test_root/qemu.log") == 1 ]] ||
	fail 'production diagnostic path did not make exactly one stage-70 attempt'
for exact_stage in 75 80 90 100; do
	[[ $(grep -Fc "ROG5_QEMU_PRODUCTION_STAGE $exact_stage" \
		"$test_root/qemu.log") == 1 ]] ||
		fail "production diagnostic path lost stage $exact_stage"
done

echo 'PASS full-system ARM64 server-RO NFSv4.2 and production OverlayFS root'
