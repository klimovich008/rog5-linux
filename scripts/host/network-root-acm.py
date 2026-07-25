#!/usr/bin/env python3
"""Run fixed ROG5 network-root staging actions without a controlling terminal."""

from __future__ import annotations

import errno
import glob
import os
import re
import select
import shutil
import stat
import subprocess
import sys
import termios
import time
import tty
from typing import NoReturn


LOAD_MARKER = b"PASS mainline network-root payload loaded"
ACTIONS = {
    "load-normal": (
        "ROG5_SYSTEMD_DIAGNOSTIC=0 ROG5_RECOVERY_TIMEOUT=900 "
        "/usr/local/sbin/rog5-load-mainline-recovery",
        LOAD_MARKER,
        False,
        60,
    ),
    "load-diagnostic": (
        "ROG5_SYSTEMD_DIAGNOSTIC=1 ROG5_RECOVERY_TIMEOUT=900 "
        "/usr/local/sbin/rog5-load-mainline-recovery",
        LOAD_MARKER,
        False,
        60,
    ),
    "load-gpucc-diagnostic": (
        "ROG5_SYSTEMD_DIAGNOSTIC=1 ROG5_QCOM_CC_PROBE_TRACE=1 "
        "ROG5_CCF_REGISTER_TRACE=1 "
        "ROG5_RECOVERY_TIMEOUT=900 "
        "/usr/local/sbin/rog5-load-mainline-recovery",
        LOAD_MARKER,
        False,
        60,
    ),
    "execute": ("kexec -e", None, True, 20),
}
CSI = re.compile(rb"\x1b\[[0-9;?]*[ -/]*[@-~]")


class MissingLoadMarkerError(RuntimeError):
    """The fixed load command completed without its success marker."""


def fail(message: str) -> NoReturn:
    raise RuntimeError(message)


def sanitize_console(data: bytes) -> str:
    clean = CSI.sub(b"", data).replace(b"\x1b", b"")
    return clean.decode(errors="replace").replace("\r", "")


def write_all(fd: int, data: bytes) -> None:
    view = memoryview(data)
    while view:
        written = os.write(fd, view)
        view = view[written:]


def run_serial(
    path: str,
    command: str,
    marker: bytes | None,
    expect_disconnect: bool,
    timeout_seconds: int,
    *,
    settle_seconds: float = 1.0,
) -> str:
    fd = os.open(path, os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
    output = bytearray()
    disconnected = False
    marker_seen_at: float | None = None
    try:
        tty.setraw(fd, termios.TCSANOW)
        attributes = termios.tcgetattr(fd)
        attributes[4] = termios.B115200
        attributes[5] = termios.B115200
        termios.tcsetattr(fd, termios.TCSANOW, attributes)
        termios.tcflush(fd, termios.TCIFLUSH)
        write_all(fd, (command + "\n").encode())

        deadline = time.monotonic() + timeout_seconds
        while time.monotonic() < deadline:
            ready, _, _ = select.select([fd], [], [], 0.5)
            if ready:
                try:
                    chunk = os.read(fd, 4096)
                except OSError as error:
                    if error.errno != errno.EIO:
                        raise
                    disconnected = True
                    break
                if not chunk:
                    disconnected = True
                    break
                output.extend(chunk)
                if marker is not None and marker in output and marker_seen_at is None:
                    marker_seen_at = time.monotonic()
            if marker_seen_at is not None and time.monotonic() - marker_seen_at >= settle_seconds:
                break
    finally:
        os.close(fd)

    if marker is not None and marker not in output:
        raise MissingLoadMarkerError("expected staging PASS marker was not observed")
    if expect_disconnect and not disconnected:
        fail("staging ACM did not depart after kexec execute")
    return sanitize_console(bytes(output))


def udev_properties(device: str) -> dict[str, str]:
    result = subprocess.run(
        ["udevadm", "info", "--query=property", f"--name={device}"],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
    )
    properties: dict[str, str] = {}
    for line in result.stdout.splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            properties[key] = value
    return properties


def find_recovery_acm() -> str:
    expected = {
        "ID_VENDOR_ID": "1d6b",
        "ID_MODEL_ID": "0104",
        "ID_MODEL": "ROG5_recovery",
    }
    matches: list[str] = []
    for device in glob.glob("/dev/ttyACM*"):
        try:
            properties = udev_properties(device)
            mode = os.stat(device, follow_symlinks=False).st_mode
        except (OSError, subprocess.CalledProcessError):
            continue
        if not stat.S_ISCHR(mode):
            continue
        if all(properties.get(key) == value for key, value in expected.items()):
            matches.append(device)
    if len(matches) != 1:
        fail(f"expected exactly one ROG5 recovery ACM device, found {len(matches)}")
    if not os.access(matches[0], os.R_OK | os.W_OK):
        fail("recovery ACM is not readable and writable")
    return matches[0]


def recovery_acm_identity(path: str) -> tuple[str, int, str, str, str]:
    properties = udev_properties(path)
    device = os.stat(path, follow_symlinks=False)
    return (
        path,
        device.st_rdev,
        properties.get("DEVPATH", ""),
        properties.get("ID_PATH", ""),
        properties.get("ID_SERIAL", ""),
    )


def wait_for_stable_recovery_acm(
    *,
    settle_seconds: float = 2.0,
    timeout_seconds: float = 12.0,
    poll_seconds: float = 0.2,
) -> str:
    deadline = time.monotonic() + timeout_seconds
    candidate: tuple[str, int, str, str, str] | None = None
    stable_since = 0.0
    while True:
        now = time.monotonic()
        if now >= deadline:
            fail("recovery ACM identity did not remain stable")
        try:
            path = find_recovery_acm()
            identity = recovery_acm_identity(path)
        except (OSError, RuntimeError, subprocess.CalledProcessError):
            candidate = None
            stable_since = 0.0
        else:
            if identity != candidate:
                candidate = identity
                stable_since = now
            elif now - stable_since >= settle_seconds:
                final_path = find_recovery_acm()
                if recovery_acm_identity(final_path) == candidate:
                    return final_path
                candidate = None
                stable_since = 0.0
        time.sleep(poll_seconds)


def run_fixed_action(action: str) -> str:
    command, marker, expect_disconnect, timeout_seconds = ACTIONS[action]
    path = wait_for_stable_recovery_acm()
    try:
        return run_serial(path, command, marker, expect_disconnect, timeout_seconds)
    except MissingLoadMarkerError:
        if action == "execute":
            raise
        print(
            "INFO staging marker missing; rediscovering ACM and retrying "
            f"action={action} once",
            file=sys.stderr,
        )
        path = wait_for_stable_recovery_acm()
        return run_serial(path, command, marker, expect_disconnect, timeout_seconds)


def main(arguments: list[str]) -> int:
    if os.environ.get("ALLOW_NETWORK_ROOT_ACM") != "1":
        fail("set ALLOW_NETWORK_ROOT_ACM=1 for one fixed staging action")
    if len(arguments) != 1 or arguments[0] not in ACTIONS:
        fail(
            "usage: network-root-acm.py "
            "load-normal|load-diagnostic|load-gpucc-diagnostic|execute"
        )
    action = arguments[0]
    if action == "execute" and os.environ.get("ALLOW_ATTENDED_KEXEC") != "1":
        fail("set ALLOW_ATTENDED_KEXEC=1 after the loader PASS marker")
    if os.uname().sysname != "Linux":
        fail("this host workflow requires Linux")
    for command in ("systemctl", "udevadm"):
        if shutil.which(command) is None:
            fail(f"missing host command: {command}")
    if subprocess.run(
        ["systemctl", "is-active", "--quiet", "ModemManager.service"],
        check=False,
    ).returncode == 0:
        fail("stop ModemManager before using the recovery ACM")

    output = run_fixed_action(action)
    if output:
        print(output, end="" if output.endswith("\n") else "\n")
    print(f"PASS control-safe network-root ACM action={action}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv[1:]))
    except (OSError, RuntimeError, subprocess.SubprocessError) as error:
        print(f"FAIL {error}", file=sys.stderr)
        raise SystemExit(1)
