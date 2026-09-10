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
handoff_source=$repo/tools/qemu-diagnostic-handoff/init.c
network_init=$repo/initramfs/network-root-init
config_template=$repo/tools/qemu-network-root-nfs/ganesha.conf.in
runtime=$repo/artifacts/network-root-v3/rog5-network-root-initramfs.cpio.gz
runtime_sha256=4f3077d02c40b5d27ab602562534cacf11324554ae75b0246fd4429bced9bbac
systemd_runtime=$repo/artifacts/qemu-systemd-arm64-v1/runtime.cpio.gz
systemd_runtime_verifier=$repo/scripts/host/verify-qemu-systemd-runtime.sh
compiler=${CROSS_CC:-aarch64-linux-gnu-gcc}
for command in awk chmod cp cpio find ganesha.nfsd grep gzip install ln mkdir \
	mktemp python3 qemu-system-aarch64 readelf realpath sed sha256sum sort ss \
	ssh-keygen stat tail timeout "$compiler"; do
	command -v "$command" >/dev/null ||
		fail "missing QEMU NFS command: $command"
done
for source in "$source_file" "$production_harness" "$handoff_source" \
	"$network_init" "$config_template" "$runtime" \
	"$systemd_runtime" "$systemd_runtime_verifier"; do
	[[ -f $source && ! -L $source ]] ||
		fail "missing QEMU NFS source: $source"
done
[[ -x $systemd_runtime_verifier ]] ||
	fail 'QEMU systemd runtime verifier is not executable'
"$systemd_runtime_verifier" "$systemd_runtime" >/dev/null
[[ $(sha256sum "$runtime" | cut -d ' ' -f 1) == "$runtime_sha256" ]] ||
	fail 'pinned network-root QEMU runtime hash changed'
[[ -f $kernel && ! -L $kernel && $(stat -c %s "$kernel") -gt 1048576 ]] ||
	fail 'unsafe or implausibly small kernel Image'
if ss -H -ltn 'sport = :2049' | grep -q .; then
	fail 'TCP port 2049 is already in use'
fi

test_root=$(mktemp -d /dev/shm/rog5-qemu-network-root.XXXXXX)
[[ $(stat -f -c %T "$test_root") == tmpfs ]] ||
	fail 'QEMU NFS export root is not backed by tmpfs'
[[ $(stat -c %a "$test_root") == 700 ]] ||
	fail 'QEMU NFS temporary root is not mode-private'
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
export_root=$test_root/export-root
mkdir -p "$stage" "$export_root"
gzip -dc "$runtime" |
	(cd "$stage" && cpio -idm --quiet --no-absolute-filenames)
gzip -dc "$systemd_runtime" |
	(cd "$export_root" && cpio -idm --quiet --no-absolute-filenames)
mkdir -p "$stage/proc" "$stage/sys" "$stage/run" "$stage/mnt/root-ro"
sed "s|@EXPORT_ROOT@|$export_root|" "$config_template" \
	>"$test_root/ganesha.conf"
grep -Fq "Path = $export_root;" "$test_root/ganesha.conf" ||
	fail 'QEMU NFS private tmpfs export path was not resolved'

ssh-keygen -q -t ed25519 -N '' -C qemu-network-root-client \
	-f "$test_root/client_ed25519_key"
ssh-keygen -q -t ed25519 -N '' -C qemu-network-root-host \
	-f "$test_root/ssh_host_ed25519_key"
mkdir -p "$export_root/sbin" "$export_root/usr/bin" \
	"$export_root/etc/systemd/system/multi-user.target.wants" \
	"$export_root/etc/ssh" "$export_root/root/.ssh" "$export_root/dev" \
	"$export_root/proc" "$export_root/run/sshd" "$export_root/sys" \
	"$export_root/tmp" "$export_root/usr/share/empty.sshd"
"$compiler" -std=c11 -O2 -static -fPIE -pie \
	-fstack-protector-strong -Wall -Wextra -Werror \
	-Wl,-z,relro,-z,now,-z,noexecstack,--build-id=none -s \
	"$handoff_source" \
	-o "$export_root/usr/bin/rog5-qemu-diagnostic-handoff"
chmod 0755 "$export_root/usr/bin/rog5-qemu-diagnostic-handoff"
readelf -h "$export_root/usr/bin/rog5-qemu-diagnostic-handoff" |
	grep -q 'Machine:.*AArch64' || fail 'QEMU systemd helper is not AArch64'
if readelf -l "$export_root/usr/bin/rog5-qemu-diagnostic-handoff" |
	grep -q 'Requesting program interpreter'; then
	fail 'QEMU systemd helper is dynamically linked'
fi
ln -s ../usr/lib/systemd/systemd "$export_root/sbin/init"
ln -s rog5-qemu-diagnostic-handoff \
	"$export_root/usr/bin/rog5-qemu-password-askpass"
install -m 0600 "$test_root/client_ed25519_key" \
	"$export_root/etc/ssh/client_ed25519_key"
install -m 0600 "$test_root/ssh_host_ed25519_key" \
	"$export_root/etc/ssh/ssh_host_ed25519_key"
install -m 0600 "$test_root/client_ed25519_key.pub" \
	"$export_root/root/.ssh/authorized_keys"
awk '{print "[127.0.0.1]:2222 " $1 " " $2}' \
	"$test_root/ssh_host_ed25519_key.pub" \
	>"$export_root/etc/ssh/ssh_known_hosts"
chmod 0644 "$export_root/etc/ssh/ssh_known_hosts"
chmod 1777 "$export_root/tmp"

cat >"$export_root/etc/systemd/system/sysinit.target" <<'EOF'
[Unit]
Description=ROG5 QEMU network-root sysinit target
DefaultDependencies=no
EOF
cat >"$export_root/etc/systemd/system/basic.target" <<'EOF'
[Unit]
Description=ROG5 QEMU network-root basic target
DefaultDependencies=no
EOF
cat >"$export_root/etc/ssh/sshd_config" <<'EOF'
HostKey /etc/ssh/ssh_host_ed25519_key
ListenAddress 127.0.0.1
Port 2222
AuthorizedKeysFile /root/.ssh/authorized_keys
PasswordAuthentication no
KbdInteractiveAuthentication no
PermitRootLogin prohibit-password
PubkeyAuthentication yes
StrictModes yes
UseDNS no
UsePAM no
EOF
cat >"$export_root/etc/systemd/system/sshd.service" <<'EOF'
[Unit]
Description=ROG5 QEMU network-root OpenSSH daemon
DefaultDependencies=no
After=basic.target

[Service]
Type=notify-reload
ExecStartPre=/usr/bin/rog5-qemu-diagnostic-handoff sshd-check
ExecStart=/usr/bin/rog5-qemu-diagnostic-handoff sshd-server
NotifyAccess=main
KillMode=process
StandardOutput=journal+console
StandardError=journal+console
EOF
cat >"$export_root/etc/systemd/system/rog5-qemu-openssh-proof.service" <<'EOF'
[Unit]
Description=ROG5 QEMU network-root key-only OpenSSH proof
DefaultDependencies=no
Requires=sshd.service
After=sshd.service

[Service]
Type=oneshot
ExecStart=/usr/bin/rog5-qemu-diagnostic-handoff ssh-proof
RemainAfterExit=yes
EOF
cat >"$export_root/etc/systemd/system/multi-user.target" <<'EOF'
[Unit]
Description=ROG5 QEMU production network-root target
DefaultDependencies=no
Requires=basic.target sshd.service rog5-qemu-openssh-proof.service
After=basic.target sshd.service rog5-qemu-openssh-proof.service
AllowIsolate=yes
EOF
cat >"$export_root/etc/systemd/system/rog5-qemu-network-root-success.service" <<'EOF'
[Unit]
Description=ROG5 QEMU production network-root acceptance
DefaultDependencies=no
Requires=rog5-qemu-openssh-proof.service
After=rog5-qemu-openssh-proof.service
Before=multi-user.target

[Service]
Type=oneshot
ExecStart=/usr/bin/rog5-qemu-diagnostic-handoff network-root-success
EOF
ln -s ../rog5-qemu-network-root-success.service \
	"$export_root/etc/systemd/system/multi-user.target.wants/rog5-qemu-network-root-success.service"
ln -s multi-user.target "$export_root/etc/systemd/system/default.target"
printf '%s\n' 0123456789abcdef0123456789abcdef \
	>"$export_root/etc/machine-id"
cat >"$export_root/etc/os-release" <<'EOF'
NAME="ROG5 QEMU production network-root gate"
ID=rog5-qemu-network-root
EOF
cat >"$export_root/etc/passwd" <<'EOF'
root:x:0:0:root:/root:/usr/bin/rog5-qemu-diagnostic-handoff
password-probe:x:1000:1000:Password probe:/:/usr/bin/rog5-qemu-diagnostic-handoff
nobody:x:65534:65534:Nobody:/:/usr/bin/nologin
EOF
cat >"$export_root/etc/group" <<'EOF'
root:x:0:
password-probe:x:1000:
nobody:x:65534:
EOF
cat >"$export_root/etc/shadow" <<'EOF'
root::19793:0:99999:7:::
password-probe:$6$rog5qemu$si5D3nVIXjRY6vgQ5sicm.L4wGeLnYhy0tzKrf9hoxfcmenLNxqhiuCqurKFu1AMCga2OcAZM9vE52RzDxk240:19793:0:99999:7:::
nobody:!*:19793::::::
EOF
chmod 0600 "$export_root/etc/shadow"
cat >"$export_root/etc/nsswitch.conf" <<'EOF'
passwd: files
group: files
shadow: files
hosts: files dns
EOF

network_functions=$stage/network-functions.sh
awk '
	/^host_port_probe_(attempts|timeout|interval|output)=/ { print }
	/^host_port_timeout_floor_ms=/ { print }
	/^udc_candidate_count\(\) \{/ { copy=1 }
	/^if ! parse_network_root_command_line; then/ { copy=0 }
	copy { print }
' "$network_init" >"$network_functions"
for extracted_variable in host_port_probe_attempts host_port_probe_timeout \
	host_port_probe_interval host_port_timeout_floor_ms \
	host_port_probe_output; do
	[[ $(grep -Ec "^${extracted_variable}=" "$network_functions") == 1 ]] ||
		fail "production readiness variable extraction is ambiguous: $extracted_variable"
done
grep -Fqx 'mount_network_root() {' "$network_functions" ||
	fail 'production network-root mount function was not extracted'
[[ $(grep -Fxc 'mount_network_root() {' "$network_functions") == 1 ]] ||
	fail 'production network-root mount function extraction is ambiguous'
for handoff_function in prepare_shutdown_root handoff_network_root; do
	[[ $(grep -Fxc "$handoff_function() {" "$network_functions") == 1 ]] ||
		fail "production handoff function extraction is ambiguous: $handoff_function"
done
cp -- "$production_harness" "$stage/production-init"

"$compiler" -std=c11 -O2 -static -fPIE -pie \
	-fstack-protector-strong -Wall -Wextra -Werror \
	-Wl,-z,relro,-z,now,-z,noexecstack,--build-id=none -s \
	"$source_file" -o "$stage/init"
chmod 0755 "$stage/init" "$stage/production-init"
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

	timeout --signal=TERM --kill-after=2 60 qemu-system-aarch64 \
		-M virt \
		-cpu cortex-a57 \
		-m 512M \
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
	"$test_root/initramfs.cpio.gz" \
	'console=ttyAMA0 rdinit=/init panic=-1 nfsv4.directory_delegations=0 nfs.nfs4_disable_idmapping=1 ip=169.254.77.2::169.254.77.1:255.255.255.252:rog5-qemu:eth0:off' \
	"$test_root/qemu.log"
qemu_status=$?
set -e
require_qemu_marker() {
	local marker=$1
	local failure=$2

	grep -Fq "$marker" "$test_root/qemu.log" && return 0
	sed -n '1,320p' "$test_root/qemu.log" >&2
	grep -Ei 'export|fsal|warn|crit|major' "$test_root/ganesha.log" |
		sed -n '1,240p' >&2 || true
	tail -n 240 "$test_root/ganesha.log" >&2
	tail -n 80 "$test_root/ganesha.console" >&2
	fail "$failure; status=$qemu_status"
}

require_qemu_marker \
	'PASS production network-root shell assembled NFSv4.2 plus OverlayFS root' \
	'QEMU did not mount the NFS root'
require_qemu_marker 'PASS Linux 7.1.4 mounted exact NFSv4.2 root read-only' \
	'direct kernel NFS probe did not complete'
require_qemu_marker 'PASS QEMU NFS server rejected an RW client write' \
	'server-side read-only probe did not complete'
require_qemu_marker 'PASS OpenSSH executed the authenticated command' \
	'OpenSSH never executed the authenticated command'
require_qemu_marker 'PASS real key-only OpenSSH login completed' \
	'real OpenSSH key-only login proof did not pass'
require_qemu_marker \
	'PASS production NFS/OverlayFS root reached ARM64 systemd and key-only OpenSSH' \
	'production network root did not reach systemd'
[[ $qemu_status -eq 0 ]] ||
	fail "QEMU failed after terminal proof; status=$qemu_status"
[[ $(grep -Fc 'ROG5_QEMU_PRODUCTION_STAGE 70' "$test_root/qemu.log") == 1 ]] ||
	fail 'production diagnostic path did not make exactly one stage-70 attempt'
for exact_stage in 75 80 90 100; do
	[[ $(grep -Fc "ROG5_QEMU_PRODUCTION_STAGE $exact_stage" \
		"$test_root/qemu.log") == 1 ]] ||
		fail "production diagnostic path lost stage $exact_stage"
done

echo 'PASS full-system ARM64 production NFS/OverlayFS root, systemd, and key-only OpenSSH'
