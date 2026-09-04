#!/usr/bin/env python3
"""Capture or verify one read-only ROG5 host-state receipt."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import time
from typing import NoReturn

import generated_power_usb_active as POWER_USB


REPO = Path(__file__).resolve().parents[2]
SERIAL = str(POWER_USB.HOST["fastboot_serial"])
USB_LOCATION = str(POWER_USB.HOST["usb_location"])
USB_ROOT = Path("/sys/bus/usb/devices")
MOUNT_TARGET = "/var/lib/rog5-recovery-bundles"
NMCLI = Path("/usr/bin/nmcli")
FIREWALL = Path("/usr/bin/firewall-cmd")
IP = Path("/usr/bin/ip")
INSTALLED = (
    Path("/usr/libexec/rog5-recovery-bundle-controller"),
    Path("/usr/libexec/rog5-recovery-host/host_bundle_server.py"),
    Path("/usr/libexec/rog5-recovery-host/rog5-recovery-host-client.py"),
    Path("/usr/libexec/rog5-recovery-host/serve-network-root.sh"),
    Path("/usr/libexec/rog5-recovery-host/headless-network-root.py"),
)


class DoctorError(RuntimeError):
    pass


def fail(message: str) -> NoReturn:
    raise DoctorError(message)


def sha256(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        while block := stream.read(1024 * 1024):
            value.update(block)
    return value.hexdigest()


def command(path: Path, *arguments: str) -> str:
    result = subprocess.run(
        [str(path), *arguments],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        timeout=10,
        check=False,
        env={"LC_ALL": "C", "PATH": "/usr/sbin:/usr/bin:/sbin:/bin"},
    )
    if result.returncode != 0:
        fail(f"host command failed: {path.name}")
    return result.stdout


def disk_snapshot() -> dict[str, int]:
    value = os.statvfs(REPO)
    return {
        "available_bytes": value.f_bavail * value.f_frsize,
        "available_inodes": value.f_favail,
    }


def build_processes() -> list[str]:
    found = []
    own = os.getpid()
    for child in Path("/proc").iterdir():
        if not child.name.isdecimal() or int(child.name) == own:
            continue
        try:
            payload = (child / "cmdline").read_bytes().replace(b"\0", b" ").decode(
                "utf-8", errors="replace"
            )
        except OSError:
            continue
        if str(REPO) in payload and re.search(
            r"(?:build-corrected|build-mainline|test-stable-recovery-wrapper|make(?: |$)|ninja(?: |$))",
            payload,
        ):
            found.append(f"{child.name}:{payload.strip()[:300]}")
    return sorted(found)


def mount_snapshot() -> dict[str, str]:
    for line in Path("/proc/self/mountinfo").read_text(encoding="ascii").splitlines():
        left, separator, right = line.partition(" - ")
        if not separator:
            continue
        fields = left.split()
        if len(fields) >= 6 and fields[4] == MOUNT_TARGET:
            return {
                "target": MOUNT_TARGET,
                "root": fields[3],
                "mount_options": fields[5],
                "source": right.split()[1],
            }
    return {"target": MOUNT_TARGET, "root": "absent", "mount_options": "absent", "source": "absent"}


def served_bundle_snapshot() -> dict[str, object]:
    root = Path(MOUNT_TARGET)
    try:
        names = sorted(path.name for path in root.iterdir())
    except OSError:
        return {"inventory": [], "manifest_sha256": "absent"}
    manifest_sha = "absent"
    if len(names) == 1:
        manifest = root / names[0] / "manifest"
        if manifest.is_file() and not manifest.is_symlink():
            manifest_sha = sha256(manifest)
    return {"inventory": names, "manifest_sha256": manifest_sha}


def installed_snapshot() -> dict[str, str]:
    result = {}
    for path in INSTALLED:
        if path.is_file() and not path.is_symlink():
            result[str(path)] = sha256(path)
        else:
            result[str(path)] = "absent"
    return result


def listeners() -> list[str]:
    found = []
    wanted = set(int(value) for value in POWER_USB.HOST["project_tcp_ports"])
    for name in ("tcp", "tcp6"):
        path = Path("/proc/net") / name
        for line in path.read_text(encoding="ascii").splitlines()[1:]:
            fields = line.split()
            if len(fields) < 4 or fields[3] != "0A":
                continue
            address, port_hex = fields[1].split(":")
            port = int(port_hex, 16)
            if port in wanted:
                found.append(f"{name}:{address}:{port}")
    return sorted(found)


def binfmt_snapshot() -> dict[str, object]:
    root = Path("/proc/sys/fs/binfmt_misc")
    entries = {}
    if root.is_dir():
        for path in sorted(root.iterdir()):
            if path.name in {"register", "status"} or not path.is_file():
                continue
            lines = path.read_text(encoding="ascii").splitlines()
            entries[path.name] = lines[:3]
    payload = json.dumps(entries, sort_keys=True, separators=(",", ":")).encode()
    return {"entries": entries, "sha256": hashlib.sha256(payload).hexdigest()}


def network_snapshot() -> dict[str, object]:
    profile = str(POWER_USB.HOST["networkmanager_profile"])
    nm = command(
        NMCLI,
        "-g",
        "connection.id,connection.interface-name,connection.autoconnect,ipv4.method,ipv4.addresses,ipv4.never-default",
        "connection",
        "show",
        profile,
    ).splitlines()
    zones = command(FIREWALL, "--get-active-zones").splitlines()
    routes = command(IP, "-4", "route", "show").splitlines()
    rog_routes = [line for line in routes if "169.254.77." in line]
    return {
        "networkmanager": nm,
        "firewalld_active_zones": zones,
        "rog5_routes": rog_routes,
    }


def usb_snapshot() -> dict[str, str]:
    device = USB_ROOT / USB_LOCATION
    if not device.is_dir():
        return {"mode": "absent", "location": USB_LOCATION, "serial": "absent"}
    def value(name: str) -> str:
        try:
            return (device / name).read_text(encoding="ascii").strip()
        except OSError:
            return "absent"
    vendor, product = value("idVendor"), value("idProduct")
    modes = {
        ("0b05", "4daf"): "fastboot",
        ("0b05", "7770"): "android",
        ("1d6b", "0104"): "rog5-gadget",
    }
    return {
        "mode": modes.get((vendor, product), "unexpected"),
        "location": USB_LOCATION,
        "vendor": vendor,
        "product_id": product,
        "product": value("product"),
        "serial": value("serial"),
    }


def snapshot(mode: str, deployment_receipt: Path | None) -> dict[str, object]:
    if mode not in {"build", "cycle"}:
        fail("host-doctor mode must be build or cycle")
    deployment_sha = "none"
    if mode == "cycle":
        if deployment_receipt is None or not deployment_receipt.is_file():
            fail("cycle mode requires a deployment receipt")
        deployment_sha = sha256(deployment_receipt)
    return {
        "format": "rog5-host-doctor-receipt-v1",
        "mode": mode,
        "host_boot_id": Path("/proc/sys/kernel/random/boot_id").read_text(encoding="ascii").strip(),
        "captured_unix": int(time.time()),
        "git_head": subprocess.run(
            ["git", "-C", str(REPO), "rev-parse", "HEAD"],
            check=True,
            stdout=subprocess.PIPE,
            text=True,
        ).stdout.strip(),
        "active_lock_sha256": sha256(REPO / "manifests/power-usb-active.lock.json"),
        "deployment_receipt_sha256": deployment_sha,
        "disk": disk_snapshot(),
        "build_processes": build_processes(),
        "mount": mount_snapshot(),
        "served_bundle": served_bundle_snapshot(),
        "installed": installed_snapshot(),
        "listeners": listeners(),
        "binfmt": binfmt_snapshot(),
        "network": network_snapshot(),
        "usb": usb_snapshot(),
    }


def validate(value: dict[str, object], *, current: dict[str, object] | None = None) -> None:
    # Disk headroom and active processes are live gates, not immutable identity
    # fields. A valid captured receipt must not hide subsequent ENOSPC or a
    # concurrent builder merely because those fields are excluded from equality.
    if current is not None:
        validate(current)
    disk = value.get("disk")
    network = value.get("network")
    if (
        value.get("format") != "rog5-host-doctor-receipt-v1"
        or value.get("mode") not in {"build", "cycle"}
        or not isinstance(disk, dict)
        or int(disk.get("available_bytes", 0)) < int(POWER_USB.HOST["minimum_free_bytes"])
        or int(disk.get("available_inodes", 0)) < int(POWER_USB.HOST["minimum_free_inodes"])
        or value.get("build_processes") != []
        or not isinstance(network, dict)
        or network.get("rog5_routes") != []
    ):
        fail("host-doctor receipt is not clean")
    nm = network.get("networkmanager")
    expected_nm = [
        str(POWER_USB.HOST["networkmanager_profile"]),
        "enp4s0f3u1u2",
        str(POWER_USB.HOST["networkmanager_autoconnect"]),
        "manual",
        "169.254.77.1/30",
        "yes",
    ]
    if nm != expected_nm:
        fail("host-doctor NetworkManager profile is not exact")
    for listener in value.get("listeners", []):
        # A user's unrelated loopback web process may own 8080. Project
        # listeners on 2049/8081 or non-loopback 8080 are never accepted.
        if listener.endswith(":2049") or listener.endswith(":8081"):
            fail("host-doctor found a stale project listener")
        if listener.endswith(":8080") and not listener.startswith("tcp:0100007F:"):
            fail("host-doctor found a non-loopback 8080 listener")
    if current is not None:
        for name in (
            "host_boot_id",
            "git_head",
            "active_lock_sha256",
            "deployment_receipt_sha256",
            "mount",
            "served_bundle",
            "installed",
            "listeners",
            "binfmt",
            "network",
            "usb",
        ):
            if current.get(name) != value.get(name):
                fail(f"host-doctor state drifted: {name}")


def publish(path: Path, value: dict[str, object]) -> None:
    path = Path(os.path.abspath(path))
    parent = path.parent
    metadata = parent.lstat()
    if (
        not stat.S_ISDIR(metadata.st_mode)
        or metadata.st_uid != os.geteuid()
        or stat.S_IMODE(metadata.st_mode) != 0o700
        or os.path.lexists(path)
    ):
        fail("host-doctor output path is unsafe")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(path, flags, 0o600)
    try:
        payload = (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode("ascii")
        os.write(descriptor, payload)
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def read_receipt(path: Path) -> dict[str, object]:
    metadata = path.lstat()
    if (
        not stat.S_ISREG(metadata.st_mode)
        or metadata.st_uid != os.geteuid()
        or stat.S_IMODE(metadata.st_mode) not in {0o400, 0o600}
        or metadata.st_nlink != 1
    ):
        fail("host-doctor receipt metadata is unsafe")
    return json.loads(path.read_text(encoding="ascii"))


def main(arguments: list[str]) -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="action", required=True)
    capture = sub.add_parser("capture")
    capture.add_argument("--mode", choices=("build", "cycle"), required=True)
    capture.add_argument("--deployment-receipt", type=Path)
    capture.add_argument("output", type=Path)
    verify = sub.add_parser("verify")
    verify.add_argument("receipt", type=Path)
    verify.add_argument("--deployment-receipt", type=Path)
    values = parser.parse_args(arguments)
    if values.action == "capture":
        result = snapshot(values.mode, values.deployment_receipt)
        validate(result)
        publish(values.output, result)
        print(f"PASS host-doctor captured clean {values.mode} receipt")
        return 0
    expected = read_receipt(values.receipt)
    current = snapshot(str(expected["mode"]), values.deployment_receipt)
    validate(expected, current=current)
    print(f"PASS host-doctor verified immutable {expected['mode']} receipt")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv[1:]))
    except (DoctorError, OSError, ValueError, json.JSONDecodeError, subprocess.SubprocessError) as error:
        print(f"FAIL {error}", file=sys.stderr)
        raise SystemExit(1)
