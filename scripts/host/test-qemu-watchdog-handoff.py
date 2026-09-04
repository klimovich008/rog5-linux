#!/usr/bin/env python3
"""Offline switch_root experiment; no phone, credentials, networking or disks.

This tests watchdog process/path survival, not hardware reset effectiveness.
Only BusyBox and its interpreter are copied from the supplied target archive.
The guest's new root is tmpfs; systemd comes from the public test closure.
"""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import runpy
import stat
import subprocess
import time

REPO = Path(__file__).resolve().parents[2]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kernel", type=Path, required=True)
    parser.add_argument("--target-archive", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if not __debug__:
        raise SystemExit("archive parser requires assertions enabled")
    args.output.mkdir(mode=0o700)  # Never replace an earlier experiment.
    output = args.output.resolve()
    kernel = args.kernel.resolve(strict=True)
    runtime = REPO / "artifacts/qemu-systemd-arm64-v1/runtime.cpio.gz"
    subprocess.run([str(REPO / "scripts/host/verify-qemu-systemd-runtime.sh"),
                    str(runtime)], check=True)
    archive = runpy.run_path(str(REPO / "scripts/device/build-native-wifi-boot-initramfs.py"))
    target_blob = args.target_archive.read_bytes()
    target = archive["entries"](gzip.decompress(target_blob))
    base = archive["entries"](gzip.decompress(runtime.read_bytes()))
    image = subprocess.check_output([
        "podman", "image", "inspect", "--format", "{{.Id}}",
        "localhost/rog5-qemu-gate:ubuntu-24.04"], text=True).strip()
    results = []
    for mode in ("systemd", "hang-init", "failed-init"):
        members = {}

        def add(name, data=b"", mode=stat.S_IFREG | 0o644):
            archive["add"](members, name, data, mode)

        for name in ("bin/busybox", "lib/ld-musl-aarch64.so.1"):
            fields, data = target[name]
            if not stat.S_ISREG(fields[1]):
                raise ValueError("expected regular sealed BusyBox/interpreter")
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
pid=$($BB cat /run/watchdog.pid)
$BB readlink /proc/$pid/cwd || true
$BB cat /proc/$pid/cgroup || true
$BB ls -l /proc/$pid/fd/9 || true
$BB sleep 11
echo HANDOFF_OBSERVATION_END
$BB poweroff -f
""")
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
printf '#!/usr/bin/busybox sh\necho HANDOFF_RELATIVE_HELPER\n' >/run/helper
chmod 755 /run/helper
(
    exec 9>/dev/console
    cd /run
    sleep 8
    printf 'HANDOFF_WATCHDOG_EXPIRED\n' >&9
    if [ -x /bin/busybox ]; then
        printf 'HANDOFF_OLD_PATH_PRESENT\n' >&9
    else
        printf 'HANDOFF_OLD_PATH_GONE\n' >&9
    fi
    # The old process root is not changed by PID 1's switch_root. A relative
    # path remains visible through cwd, but its shebang may no longer resolve.
    if [ -x helper ]; then printf 'HANDOFF_RELATIVE_PATH_PRESENT\n' >&9; fi
) &
printf '%s\n' "$!" >/run/watchdog.pid
sleep 0.3
for name in dev proc sys run; do mount --move /$name /newroot/$name; done
echo HANDOFF_SWITCH_ROOT
"""
        if mode == "systemd":
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
        required = ["HANDOFF_SWITCH_ROOT"]
        if mode == "failed-init":
            required += ["can't execute '/missing-init'", "Kernel panic"]
        else:
            required += ["HANDOFF_WATCHDOG_EXPIRED", "HANDOFF_OLD_PATH_GONE", "HANDOFF_RELATIVE_PATH_PRESENT"]
            if mode == "systemd":
                required += ["HANDOFF_NEW_INIT", "HANDOFF_OBSERVATION_END"]
        passed = result.returncode == 0 and all(marker in log for marker in required)
        if mode == "failed-init" and "HANDOFF_WATCHDOG_EXPIRED" in log:
            passed = False
        results.append(dict(mode=mode, passed=passed, exit_code=result.returncode,
                            seconds=time.monotonic()-started))
        print(json.dumps(results[-1]), flush=True)
    record = dict(scope="QEMU process/path survival only; no hardware watchdog/phone proof",
                  kernel_sha256=hashlib.sha256(kernel.read_bytes()).hexdigest(),
                  target_archive_sha256=hashlib.sha256(target_blob).hexdigest(),
                  container=image, cases=results)
    (output / "result.json").write_text(json.dumps(record, indent=2) + "\n")
    return 0 if all(case["passed"] for case in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
