#!/usr/bin/env python3
"""Offline switch_root experiment; no phone, real credentials or external network.

This executes the exact supplied archive's init watchdog functions through real
systemd/switch_root, not the complete deployed init or physical phone reset
effectiveness. BusyBox, its interpreter and the exact static reboot helper are
copied from that same archive. Missing/legacy watchdogs are refused; there is no
repository-source fallback.
By default the guest root is tmpfs with the public systemd test closure.
--root-image instead uses retained Arch ext4 read-only with a RAM overlay,
its systemd/sshd and the sealed SSH units. Keys and ACKs are guest fixtures;
this mode does not qualify optional Wi-Fi rollback or all of C02 by itself.
"""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import re
import runpy
import stat
import subprocess
import time
import zlib

REPO = Path(__file__).resolve().parents[2]


def sha_file(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def arch_ssh_units(target):
    source = target['init'][1].decode()
    result = {}
    for variable, name in (('early_sshd_unit', 'rog5-early-sshd.service'),
                           ('ed25519_unit', 'rog5-sshd-ed25519-key.service')):
        units = re.findall(r'cat >"\$'+variable+r'" <<\'EOF\'\n(.*?)\nEOF', source, re.S)
        if variable == 'early_sshd_unit':
            units = [unit for unit in units if '\nExecStart=/usr/bin/sshd -D\n' in unit]
        if len(units) != 1:
            raise ValueError('missing or ambiguous normal SSH unit: '+variable)
        result[name] = (units[0]+'\n').encode()
    return result


# Guest-only fixtures: fresh ephemeral keys, loopback SSH, no phone credential.
# The unit bytes and systemd/sshd executables are NOT replaced by these fixtures.
ARCH_SSH_SETUP = r'''
export PATH=/usr/bin:/bin
ip link set lo up
# Only the guest RAM overlay: retain real system accounts (Arch sshd uses
# nobody) and unlock root for this ephemeral, key-only loopback fixture.
sed -i 's/^root:[^:]*/root:x/' /etc/shadow
ssh-keygen -q -t ed25519 -N '' -f /etc/ssh/ssh_host_ed25519_key
ssh-keygen -q -t ed25519 -N '' -f /run/c02-client
printf '127.0.0.1 %s\n' "$(cat /etc/ssh/ssh_host_ed25519_key.pub)" >/run/c02-hosts
ssh_proof() {
    test "$(timeout 5 ssh -F /dev/null -o BatchMode=yes -o IdentitiesOnly=yes \
        -o IdentityAgent=none -o StrictHostKeyChecking=yes -o UpdateHostKeys=no \
        -o UserKnownHostsFile=/run/c02-hosts -o ConnectTimeout=2 \
        -i /run/c02-client root@127.0.0.1 /usr/bin/cat /proc/sys/kernel/random/boot_id)" \
        = "$(cat /proc/sys/kernel/random/boot_id)"
}
systemctl --version
stat -c 'ARCH_SSH_PATH %a %u %g %n' /run /run/c02-client.pub /etc/shadow
mkdir -p /run/sshd
/usr/bin/sshd -t -e
systemctl start rog5-early-sshd.service
# Type=simple acknowledges exec setup, not the listening socket. Bound the
# guest-only readiness wait without changing the sealed unit or watchdog.
ready=0
for attempt in 1 2 3 4 5; do
    if ssh_proof; then ready=1; break; fi
    sleep .2
done
test "$ready" = 1
old_pid=$(systemctl show -p MainPID --value rog5-early-sshd.service)
test "$old_pid" -gt 1
echo ARCH_SSH_INITIAL_PASS
'''
ARCH_SSH_RESTART = r'''
systemctl restart rog5-early-sshd.service
ready=0
for attempt in 1 2 3 4 5; do
    if ssh_proof; then ready=1; break; fi
    sleep .2
done
test "$ready" = 1
new_pid=$(systemctl show -p MainPID --value rog5-early-sshd.service)
test "$new_pid" -gt 1
test "$old_pid" != "$new_pid"
echo "ARCH_SSH_PID_CHANGE $old_pid $new_pid"
sleep 3
ssh_proof
echo ARCH_SSH_RESTART_PASS
'''
ARCH_WAIT_ACK = r'''
# Wait for the real watchdog child, not a new full delay after SSH setup.
watchdog_done=0
for attempt in $(seq 1 30); do
    if [ ! -e /proc/$pid/stat ] ||
       $BB awk '$3 == "Z" { ok=1 } END { exit !ok }' /proc/$pid/stat; then
        watchdog_done=1
        break
    fi
    sleep 1
done
test "$watchdog_done" = 1
'''


def watchdog_functions(target):
    """Extract exact archive bytes, validating the harness ABI without executing init.

    These structural checks are not composition or behavioral acceptance: the
    real guest cases still have to pass, and deployed call sites/ACK producers
    need separate composition checks.
    """
    if "init" not in target:
        raise ValueError("target archive: missing init; no repository-source fallback")
    fields, data = target["init"]
    if not stat.S_ISREG(fields[1]) or fields[4] != 1 or not fields[1] & 0o111:
        raise ValueError("target archive init must be a single-link executable regular file")
    try:
        source = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("target archive init: invalid UTF-8") from exc
    if "\0" in source or "\r" in source:
        raise ValueError("target archive init: malformed shell text")
    if re.search(r"\bdisarm_watchdog\b", source):
        raise ValueError("target archive init: legacy disarm-style watchdog unsupported; "
                         "no repository-source fallback")
    names = ("watchdog_bb", "watchdog_acknowledged", "watchdog_expired",
             "arm_watchdog", "physical_topology_count")
    positions = []
    for name in names:
        marker = name + "() {\n"
        definitions = re.findall(r"(?m)^\s*" + name + r"\s*\(\s*\)\s*\{", source)
        if len(definitions) != 1 or source.count("\n" + marker) != 1:
            raise ValueError(f"target archive init: missing, duplicate or malformed {name}; "
                             "requires current-boot ACK watchdog, no repository-source fallback")
        positions.append(source.index("\n" + marker) + 1)
    if positions != sorted(positions):
        raise ValueError("target archive init: malformed watchdog function order")
    block = source[positions[0]:positions[-1]]
    for label, text in (("init", source), ("watchdog block", block)):
        # Syntax only; do not run any command from the supplied archive on host.
        checked = subprocess.run(["/bin/sh", "-n"], input=text, text=True,
                                 capture_output=True, timeout=5)
        if checked.returncode:
            raise ValueError(f"target archive {label}: malformed shell syntax")
    return block


def main():
    all_started = time.monotonic()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kernel", type=Path, required=True)
    parser.add_argument("--target-archive", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--root-image", type=Path,
                        help="RO retained Arch ext4: two exact-systemd/SSH cases instead of public-runtime matrix")
    args = parser.parse_args()
    if not __debug__:
        raise SystemExit("archive parser requires assertions enabled")
    archive = runpy.run_path(str(REPO / "scripts/device/build-native-wifi-boot-initramfs.py"))
    try:
        target_blob = args.target_archive.read_bytes()
        target = archive["entries"](gzip.decompress(target_blob))
        watchdog_source = watchdog_functions(target)
    except (OSError, EOFError, ValueError, AssertionError, zlib.error) as exc:
        parser.error(f"target archive refused: {exc}")
    # Refuse incompatible archives before creating evidence or invoking QEMU.
    kernel = args.kernel.resolve(strict=True)
    runner_hash = sha_file(Path(__file__))
    root_image = args.root_image
    root_hash = None
    ssh_units = {}
    if root_image:
        if not root_image.is_absolute() or root_image.is_symlink() or not root_image.is_file():
            parser.error('root image must be an absolute ordinary retained file')
        ssh_units = arch_ssh_units(target)
        root_hash = sha_file(root_image)
    source_revision = subprocess.check_output(['git', '-C', str(REPO), 'rev-parse', 'HEAD'], text=True).strip()
    args.output.mkdir(mode=0o700)  # Never replace an earlier experiment.
    output = args.output.resolve()
    runtime = REPO / "artifacts/qemu-systemd-arm64-v1/runtime.cpio.gz"
    base = {}
    if not root_image:
        subprocess.run([str(REPO / "scripts/host/verify-qemu-systemd-runtime.sh"),
                        str(runtime)], check=True)
        base = archive["entries"](gzip.decompress(runtime.read_bytes()))
    image = subprocess.check_output([
        "podman", "image", "inspect", "--format", "{{.Id}}",
        "localhost/rog5-qemu-gate:ubuntu-24.04"], text=True).strip()
    results = []
    modes = ("systemd-ack", "systemd-no-ack", "systemd-stale-ack",
             "systemd-p2-only", "systemd-stale-identity",
             "helper-unexecutable", "hang-init", "failed-init", "fd-open-failure")
    if root_image:
        modes = ('systemd-ack', 'systemd-stale-identity')
    for mode in modes:
        members = {}

        def add(name, data=b"", mode=stat.S_IFREG | 0o644):
            archive["add"](members, name, data, mode)

        for name in ("bin/busybox", "lib/ld-musl-aarch64.so.1",
                     "usr/libexec/rog5-reboot-bootloader"):
            fields, data = target[name]
            if not stat.S_ISREG(fields[1]):
                raise ValueError("expected regular sealed runtime member")
            add(name, data, fields[1])
        for name, (fields, data) in sorted(base.items(), key=lambda item: item[0].count("/")):
            add("systemd-root/" + name, data, fields[1])
        add("systemd-root/usr/bin/busybox", target["bin/busybox"][1], stat.S_IFREG | 0o755)
        add("systemd-root/usr/lib/ld-musl-aarch64.so.1",
            target["lib/ld-musl-aarch64.so.1"][1], stat.S_IFREG | 0o755)
        add("systemd-root/etc/machine-id", b"0123456789abcdef0123456789abcdef\n")
        if not root_image:
            add("systemd-root/etc/os-release", b'ID=rog5-qemu\nNAME="ROG5 handoff test"\n')
        if not root_image:
            add("systemd-root/etc/passwd", b"root:x:0:0:root:/:/usr/bin/busybox\n")
            add("systemd-root/etc/group", b"root:x:0:\n")
            add("systemd-root/etc/nsswitch.conf", b"passwd: files\ngroup: files\n")
        add("systemd-root/etc/systemd/system/default.target", b"""[Unit]
DefaultDependencies=no
Requires=observe.service
After=observe.service
""")
        add("systemd-root/etc/systemd/system/observe.service", b"""[Unit]
DefaultDependencies=no
[Service]
Type=oneshot
ExecStart=/usr/bin/busybox sh /observe
StandardOutput=tty
StandardError=tty
TTYPath=/dev/console
""")
        add("systemd-root/observe", b"""set -eu
BB=/usr/bin/busybox
echo HANDOFF_NEW_INIT
pid=$($BB cat /run/rog5-p2-watchdog.pid)
$BB readlink /proc/$pid/cwd || true
$BB cat /proc/$pid/cgroup || true
$BB ls -l /proc/$pid/fd/9 || true
$BB test ! -e /proc/$pid/root/bin/busybox
echo HANDOFF_OLD_PATH_GONE
case MODE in
systemd-ack|systemd-stale-ack|systemd-p2-only|systemd-stale-identity)
    boot=$($BB cat /proc/sys/kernel/random/boot_id)
    [ MODE != systemd-stale-ack ] || boot=00000000-0000-0000-0000-000000000000
    printf 'status=PASS\nattested_boot_id=%s\n' "$boot" >/run/rog5-p2-ready.next
    $BB chmod 0444 /run/rog5-p2-ready.next
    $BB mv /run/rog5-p2-ready.next /run/rog5-p2-ready
    ;;
esac
case MODE in
systemd-ack|systemd-stale-ack|systemd-stale-identity)
    boot=$($BB cat /proc/sys/kernel/random/boot_id)
    [ MODE != systemd-stale-identity ] || boot=00000000-0000-0000-0000-000000000000
    printf 'format=rog5-persistent-ssh-identity-v1\nmode=load\nfingerprint=SHA256:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA\nidentity_boot_id=%s\n' "$boot" >/run/rog5-persistent-ssh-identity.record.next
    $BB chmod 0444 /run/rog5-persistent-ssh-identity.record.next
    $BB mv /run/rog5-persistent-ssh-identity.record.next /run/rog5-persistent-ssh-identity.record
    ;;
esac
# No SSH listener runs in this handoff fixture: once initial identity readiness
# is latched, later listener absence is not a reason for boot rollback. Actual
# service restart behavior is the separate C02 integration contract.
$BB sleep 11
# A valid acknowledgement must end the watchdog, not merely postpone reset.
if $BB test -e /proc/$pid/stat; then
    $BB awk '$3 == "Z" { ok=1 } END { exit !ok }' /proc/$pid/stat
fi
echo HANDOFF_OBSERVATION_END
$BB poweroff -f
""".replace(b"MODE", mode.encode()))
        if root_image:
            for name, unit in ssh_units.items():
                add('systemd-root/etc/systemd/system/'+name, unit)
            add('systemd-root/etc/ssh/sshd_config', b'''ListenAddress 127.0.0.1
HostKey /etc/ssh/ssh_host_ed25519_key
AuthorizedKeysFile /run/c02-client.pub
PasswordAuthentication no
KbdInteractiveAuthentication no
PermitRootLogin prohibit-password
UsePAM no
''')
            fields, observe = members['systemd-root/observe']
            observe = observe.replace(b'echo HANDOFF_OLD_PATH_GONE\n',
                                      b'echo HANDOFF_OLD_PATH_GONE\n'+ARCH_SSH_SETUP.encode())
            observe = observe.replace(b'$BB sleep 11', ARCH_WAIT_ACK.encode())
            observe = observe.replace(b'echo HANDOFF_OBSERVATION_END',
                                      ARCH_SSH_RESTART.encode()+b'\necho HANDOFF_OBSERVATION_END')
            archive['replace'](members, 'systemd-root/observe', observe)
        init = r"""#!/bin/busybox sh
set -eu
export PATH=/bin
/bin/busybox --install -s /bin
mkdir -p /dev /proc /sys /run /newroot
mount -t devtmpfs devtmpfs /dev
exec </dev/console >/dev/console 2>&1
mount -t proc proc /proc
mount -t sysfs sysfs /sys
mount -t tmpfs tmpfs /run
mount -t tmpfs tmpfs /newroot
cp -a /systemd-root/. /newroot/
mkdir -p /newroot/dev /newroot/proc /newroot/sys /newroot/run /newroot/tmp
chmod 1777 /newroot/tmp
""" + watchdog_source + r"""
log() { echo "$*"; }
reboot_helper=/usr/libexec/rog5-reboot-bootloader
watchdog_kmsg=/dev/console
watchdog_sysrq=/proc/sysrq-trigger
watchdog_pid_file=/run/rog5-p2-watchdog.pid
recovery_timeout=8
"""
        if root_image:
            init = init.replace('mount -t tmpfs tmpfs /run\n',
                                'mount -t tmpfs -o mode=0755 tmpfs /run\n')
            init = init.replace('mount -t tmpfs tmpfs /newroot\n', '''
mkdir -p /lower /upper
for attempt in 1 2 3 4 5; do
    [ -b /dev/vda ] && break
    sleep 1
done
[ "$(blockdev --getro /dev/vda)" = 1 ]
mount -t ext4 -o ro,noload /dev/vda /lower
mount -t tmpfs -o size=256m tmpfs /upper
mkdir /upper/upper /upper/work
mount -t overlay -o lowerdir=/lower,upperdir=/upper/upper,workdir=/upper/work overlay /newroot
echo ARCH_ROOT_READ_ONLY_OVERLAY
''').replace('recovery_timeout=8\n', 'recovery_timeout=20\n')
        if mode == "fd-open-failure":
            init += "watchdog_kmsg=/missing/kmsg\n"
        init += r"""
arm_watchdog || { echo HANDOFF_ARM_FAILED_ROLLBACK; "$reboot_helper"; exit 1; }
mkdir -p /run/initramfs/bin /run/initramfs/lib /run/initramfs/usr/libexec
cp /bin/busybox /run/initramfs/bin/
cp /lib/ld-musl-aarch64.so.1 /run/initramfs/lib/
cp "$reboot_helper" "/run/initramfs$reboot_helper"
"""
        if mode == "helper-unexecutable":
            # Existing executable with an unavailable interpreter: the exact
            # production fallback must reach its retained SysRq FD on ENOENT.
            init += "printf '#!/missing-loader\\n' >/run/initramfs/usr/libexec/rog5-reboot-bootloader\n"
        init += r"""
sleep 0.3
for name in dev proc sys run; do mount --move /$name /newroot/$name; done
echo HANDOFF_SWITCH_ROOT
"""
        if mode.startswith("systemd-") or mode == "helper-unexecutable":
            init += "exec switch_root /newroot /usr/lib/systemd/systemd\n"
        elif mode == "hang-init":
            add("systemd-root/hang", b"#!/usr/bin/busybox sh\n/usr/bin/busybox sleep 11\n/usr/bin/busybox poweroff -f\n", stat.S_IFREG | 0o755)
            init += "exec switch_root /newroot /hang\n"
        else:
            # The BusyBox exec succeeds; the subsequent init exec fails.
            init += "exec switch_root /newroot /missing-init\n"
        add("init", init.encode(), stat.S_IFREG | 0o755)
        initrd = output / (mode + ".cpio.gz")
        initrd.write_bytes(gzip.compress(archive["encode"](members), mtime=0))
        command = ["podman", "run", "--rm", "--pull=never", "--network=none",
                   "--cap-drop=ALL", "--security-opt=no-new-privileges", "--cpus=2", "--memory=1g",
                   "-v", str(kernel) + ":/Image:ro", "-v", str(initrd) + ":/initramfs:ro", image,
                   "timeout", "40", "qemu-system-aarch64", "-M", "virt", "-cpu", "cortex-a72",
                   "-m", "512", "-smp", "2", "-nographic", "-monitor", "none", "-nic", "none",
                   "-no-reboot", "-kernel", "/Image", "-initrd", "/initramfs", "-append",
                   "console=ttyAMA0 rdinit=/init panic=2 systemd.log_target=console systemd.show_status=yes"]
        if root_image:
            command[command.index(image):command.index(image)] = ['-v', str(root_image)+':/arch.ext4:ro']
            command += ['-drive', 'file=/arch.ext4,format=raw,if=none,id=root,readonly=on',
                        '-device', 'virtio-blk-device,drive=root']
        started = time.monotonic()
        with (output / (mode + ".log")).open("xb") as log:
            result = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, timeout=50)
        log = (output / (mode + ".log")).read_text(errors="replace")
        required = [] if mode == "fd-open-failure" else ["HANDOFF_SWITCH_ROOT"]
        if mode == "fd-open-failure":
            required += ["HANDOFF_ARM_FAILED_ROLLBACK", "reboot: Restarting system with command 'bootloader'"]
        elif mode == "failed-init":
            required += ["can't execute '/missing-init'", "Kernel panic"]
        elif mode == "systemd-ack":
            required += ["HANDOFF_NEW_INIT", "HANDOFF_OLD_PATH_GONE",
                         "watchdog acknowledged by current-boot P2 and SSH identity readiness",
                         "HANDOFF_OBSERVATION_END"]
        elif mode == "helper-unexecutable":
            required += ["HANDOFF_NEW_INIT", "HANDOFF_OLD_PATH_GONE", "sysrq: Resetting"]
        else:
            required += ["reboot: Restarting system with command 'bootloader'"]
            if mode.startswith("systemd-"):
                required += ["HANDOFF_NEW_INIT", "HANDOFF_OLD_PATH_GONE"]
        passed = result.returncode == 0 and all(marker in log for marker in required)
        if mode != "systemd-ack" and "HANDOFF_OBSERVATION_END" in log:
            passed = False
        if mode == "failed-init" and "command 'bootloader'" in log:
            passed = False
        if root_image:
            passed = passed and 'ARCH_ROOT_READ_ONLY_OVERLAY' in log and 'ARCH_SSH_INITIAL_PASS' in log
            if mode == 'systemd-ack':
                passed = passed and 'ARCH_SSH_RESTART_PASS' in log and "Restarting system" not in log
            elif 'ARCH_SSH_RESTART_PASS' in log:
                passed = False
        results.append(dict(mode=mode, passed=passed, exit_code=result.returncode,
                            seconds=time.monotonic()-started))
        print(json.dumps(results[-1]), flush=True)
    record = dict(scope="QEMU exact archive watchdog functions; harness init/ACK producer fixtures, "
                        "not full deployed composition or phone/storage proof",
                  watchdog_source_origin="target-archive:init",
                  target_init_sha256=hashlib.sha256(target["init"][1]).hexdigest(),
                  watchdog_source_sha256=hashlib.sha256(watchdog_source.encode()).hexdigest(),
                  kernel_sha256=hashlib.sha256(kernel.read_bytes()).hexdigest(),
                  target_archive_sha256=hashlib.sha256(target_blob).hexdigest(),
                  container=image, cases=results)
    record.update(source_revision=source_revision, runner_sha256=runner_hash)
    if root_image:
        unchanged = sha_file(root_image) == root_hash
        record.update(root_image_sha256=root_hash, root_image_unchanged=unchanged,
                      c02_qualified=False, release_qualified=False,
                      ssh_units_sha256={name: hashlib.sha256(data).hexdigest()
                                        for name, data in ssh_units.items()},
                      scope='Exact retained Arch systemd/sshd and sealed SSH units/watchdog; '
                            'RO virtual root with RAM overlay, loopback keys and ACK fixtures; '
                            '20-second test timer, not physical storage or optional Wi-Fi rollback qualification')
        if not unchanged:
            results.append(dict(mode='root-unchanged', passed=False))
    if sha_file(Path(__file__)) != runner_hash:
        results.append(dict(mode='runner-unchanged', passed=False))
    record.update(status='PASS' if all(case['passed'] for case in results) else 'FAIL',
                  duration_seconds=time.monotonic()-all_started)
    (output / "result.json").write_text(json.dumps(record, indent=2) + "\n")
    return 0 if all(case["passed"] for case in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
