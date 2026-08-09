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
reporter_source_sha256=93d09cca8ad8dc573b1aa25c2fba5cc027d1ba901adb6c9e2643f97287387f9a
parser=$repo/scripts/host/early-target-diagnostics.py
network_init=$repo/initramfs/network-root-init
systemd_runtime=$repo/artifacts/qemu-systemd-arm64-v1/runtime.cpio.gz
systemd_runtime_verifier=$repo/scripts/host/verify-qemu-systemd-runtime.sh
compiler=${CROSS_CC:-aarch64-linux-gnu-gcc}
qemu_timeout=${QEMU_TIMEOUT:-60}
[[ $qemu_timeout =~ ^[1-9][0-9]?$ && $qemu_timeout -le 60 ]] ||
	fail 'QEMU_TIMEOUT must be an integer from 1 through 60'
for command in awk cat chmod cp cpio find grep gzip install ln mkdir mktemp python3 \
	qemu-system-aarch64 realpath readelf sed sha256sum sort stat strings \
	ssh-keygen timeout "$compiler"; do
	command -v "$command" >/dev/null ||
		fail "missing QEMU diagnostic handoff command: $command"
done
[[ $(sha256sum "$reporter_source" | cut -d ' ' -f 1) == \
	"$reporter_source_sha256" ]] || fail 'QEMU reporter source seal changed'
for source in "$harness_source" "$reporter_source" "$parser" \
	"$network_init" "$systemd_runtime" "$systemd_runtime_verifier"; do
	[[ -f $source && ! -L $source ]] || fail "missing handoff source: $source"
done
[[ -x $systemd_runtime_verifier ]] ||
	fail 'systemd runtime verifier is not executable'
"$systemd_runtime_verifier" "$systemd_runtime" >/dev/null
[[ -f $kernel && ! -L $kernel && $(stat -c %s "$kernel") -gt 1048576 ]] ||
	fail 'unsafe or implausibly small kernel Image'

test_root=$(mktemp -d)
trap 'find "$test_root" -depth -delete 2>/dev/null || true' EXIT HUP INT TERM
ssh-keygen -q -t ed25519 -N '' -C qemu-client \
	-f "$test_root/client_ed25519_key"
ssh-keygen -q -t ed25519 -N '' -C qemu-host \
	-f "$test_root/ssh_host_ed25519_key"
stage=$test_root/stage
systemd_root=$stage/systemd-root
mkdir -p "$stage/dev" "$stage/sbin" "$systemd_root"
gzip -dc "$systemd_runtime" |
	(cd "$systemd_root" && cpio -idm --quiet --no-absolute-filenames)
"$compiler" -std=c11 -O2 -static -fPIE -pie \
	-fstack-protector-strong -Wall -Wextra -Werror \
	-Wl,-z,relro,-z,now,-z,noexecstack,--build-id=none -s \
	"$reporter_source" -o "$stage/sbin/rog5-early-target-diag"
"$compiler" -std=c11 -O2 -static -fPIE -pie \
	-fstack-protector-strong -Wall -Wextra -Werror \
	-Wl,-z,relro,-z,now,-z,noexecstack,--build-id=none -s \
	"$harness_source" -o "$stage/qemu-diagnostic-handoff"
cp "$stage/qemu-diagnostic-handoff" "$stage/init"
mkdir -p "$systemd_root/usr/bin" "$systemd_root/etc/systemd/system" \
	"$systemd_root/etc/ssh" "$systemd_root/root/.ssh" \
	"$systemd_root/dev" "$systemd_root/proc" "$systemd_root/run" \
	"$systemd_root/run/sshd" "$systemd_root/sys" "$systemd_root/tmp" \
	"$systemd_root/usr/share/empty.sshd"
cp "$stage/qemu-diagnostic-handoff" \
	"$systemd_root/usr/bin/rog5-qemu-diagnostic-handoff"
chmod 0755 "$stage/init" "$stage/qemu-diagnostic-handoff" \
	"$stage/sbin/rog5-early-target-diag" \
	"$systemd_root/usr/bin/rog5-qemu-diagnostic-handoff"
install -m 0600 "$test_root/client_ed25519_key" \
	"$systemd_root/etc/ssh/client_ed25519_key"
install -m 0600 "$test_root/ssh_host_ed25519_key" \
	"$systemd_root/etc/ssh/ssh_host_ed25519_key"
install -m 0600 "$test_root/client_ed25519_key.pub" \
	"$systemd_root/root/.ssh/authorized_keys"
awk '{print "[127.0.0.1]:2222 " $1 " " $2}' \
	"$test_root/ssh_host_ed25519_key.pub" \
	>"$systemd_root/etc/ssh/ssh_known_hosts"
chmod 0644 "$systemd_root/etc/ssh/ssh_known_hosts"
chmod 1777 "$systemd_root/tmp"
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

unit_functions=$test_root/diagnostic-unit-functions.sh
awk '
	/^install_diagnostic_units\(\) \{/ { copy=1 }
	copy {
		print
		if (/^}$/)
			exit
	}
' "$network_init" >"$unit_functions"
grep -Fqx 'install_diagnostic_units() {' "$unit_functions" ||
	fail 'production diagnostic-unit function was not extracted'
[[ $(grep -Fxc '}' "$unit_functions") == 1 ]] ||
	fail 'production diagnostic-unit extraction crossed its boundary'
# shellcheck disable=SC1090
. "$unit_functions"
handoff_newroot=$systemd_root
diagnostic_mode=1
install_diagnostic_units || fail 'cannot install production diagnostic units'
unit_root=$systemd_root/etc/systemd/system

cat >"$unit_root/sysinit.target" <<'EOF'
[Unit]
Description=ROG5 QEMU minimal sysinit target
DefaultDependencies=no
EOF
cat >"$unit_root/basic.target" <<'EOF'
[Unit]
Description=ROG5 QEMU minimal basic target
DefaultDependencies=no
Requires=rog5-early-target-new-init.service
After=rog5-early-target-new-init.service
EOF
cat >"$systemd_root/etc/ssh/sshd_config" <<'EOF'
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
cat >"$unit_root/sshd.service" <<'EOF'
[Unit]
Description=ROG5 QEMU real OpenSSH daemon
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
cat >"$unit_root/rog5-qemu-openssh-proof.service" <<'EOF'
[Unit]
Description=ROG5 QEMU key-only OpenSSH login proof
DefaultDependencies=no
Requires=sshd.service rog5-early-target-sshd.service
After=sshd.service rog5-early-target-sshd.service

[Service]
Type=oneshot
ExecStart=/usr/bin/rog5-qemu-diagnostic-handoff ssh-proof
RemainAfterExit=yes
EOF
cat >"$unit_root/multi-user.target" <<'EOF'
[Unit]
Description=ROG5 QEMU diagnostic acceptance target
DefaultDependencies=no
Requires=basic.target sshd.service rog5-early-target-sshd.service rog5-qemu-openssh-proof.service
After=basic.target sshd.service rog5-early-target-sshd.service rog5-qemu-openssh-proof.service
AllowIsolate=yes
EOF
cat >"$unit_root/rog5-qemu-systemd-success.service" <<'EOF'
[Unit]
Description=ROG5 QEMU systemd diagnostic acceptance
DefaultDependencies=no
Requires=rog5-qemu-openssh-proof.service
After=rog5-qemu-openssh-proof.service
Before=multi-user.target

[Service]
Type=oneshot
ExecStart=/usr/bin/rog5-qemu-diagnostic-handoff systemd-success
EOF
ln -s ../rog5-qemu-systemd-success.service \
	"$unit_root/multi-user.target.wants/rog5-qemu-systemd-success.service"
ln -s multi-user.target "$unit_root/default.target"
printf '%s\n' 0123456789abcdef0123456789abcdef \
	>"$systemd_root/etc/machine-id"
cat >"$systemd_root/etc/os-release" <<'EOF'
NAME="ROG5 QEMU systemd gate"
ID=rog5-qemu-systemd
EOF
cat >"$systemd_root/etc/passwd" <<'EOF'
root:x:0:0:root:/root:/usr/bin/rog5-qemu-diagnostic-handoff
nobody:x:65534:65534:Nobody:/:/usr/bin/nologin
EOF
cat >"$systemd_root/etc/group" <<'EOF'
root:x:0:
nobody:x:65534:
EOF
cat >"$systemd_root/etc/shadow" <<'EOF'
root::19793:0:99999:7:::
nobody:!*:19793::::::
EOF
chmod 0600 "$systemd_root/etc/shadow"
cat >"$systemd_root/etc/nsswitch.conf" <<'EOF'
passwd: files
group: files
shadow: files
hosts: files dns
EOF

grep -Fqx 'ExecStart=/run/initramfs/sbin/rog5-early-target-diag emit 130' \
	"$unit_root/rog5-early-target-new-init.service"
grep -Fqx 'ExecStart=/run/initramfs/sbin/rog5-early-target-diag emit 140' \
	"$unit_root/rog5-early-target-sshd.service"
if strings "$stage/qemu-diagnostic-handoff" |
	grep -qxE '130|140'; then
	fail 'QEMU harness can emit a post-handoff diagnostic stage directly'
fi
(
	cd "$stage"
	find . -mindepth 1 -print0 | sort -z |
		cpio --null -o --quiet --format=newc --owner=0:0
) | gzip -n >"$test_root/initramfs.cpio.gz"

set +e
timeout --signal=TERM --kill-after=2 "$qemu_timeout" \
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
		-append 'console=ttyAMA0 rdinit=/init panic=-1 quiet systemd.unit=multi-user.target systemd.show_status=yes systemd.log_target=console' \
		>/dev/null 2>"$test_root/qemu.stderr"
qemu_status=$?
set -e
if ((qemu_status != 0)) ||
	! grep -Fq 'PASS generated diagnostic units ran under ARM64 systemd' \
	"$test_root/console.log"; then
	tail -n 300 "$test_root/console.log" >&2
	sed -n '1,120p' "$test_root/qemu.stderr" >&2
	fail "QEMU did not complete diagnostic root handoff; status=$qemu_status"
fi
grep -Fq 'PASS OpenSSH executed the authenticated command' \
	"$test_root/console.log" || fail 'OpenSSH never executed the key-authenticated command'
grep -Fq 'PASS real key-only OpenSSH login completed' \
	"$test_root/console.log" || fail 'real OpenSSH key-only login proof did not pass'

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
stream = module.DiagnosticStream("headless-netroot-early-diag-v2")
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
    "PASS canonical reporter stream crossed real systemd units "
    f"frames={len(records)} boot_id={stream.boot_id}"
)
PY

echo 'PASS generated diagnostic units executed under ARM64 systemd'
