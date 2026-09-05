#!/usr/bin/env python3
"""Offline switch_root experiment; no phone, credentials, networking or disks.

This executes the exact supplied archive's init watchdog functions through real
systemd/switch_root, not the complete deployed init or physical phone reset
effectiveness. BusyBox, its interpreter and the exact static reboot helper are
copied from that same archive. Missing/legacy watchdogs are refused; there is no
repository-source fallback.
The guest's new root is tmpfs; systemd comes from the public test closure.
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
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kernel", type=Path, required=True)
    parser.add_argument("--target-archive", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
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
    args.output.mkdir(mode=0o700)  # Never replace an earlier experiment.
    output = args.output.resolve()
    runtime = REPO / "artifacts/qemu-systemd-arm64-v1/runtime.cpio.gz"
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
        add("systemd-root/etc/os-release", b'ID=rog5-qemu\nNAME="ROG5 handoff test"\n')
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
    (output / "result.json").write_text(json.dumps(record, indent=2) + "\n")
    return 0 if all(case["passed"] for case in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
