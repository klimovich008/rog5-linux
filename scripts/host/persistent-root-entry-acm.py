#!/usr/bin/env python3
"""Receive the fixed RAM-only P2 early-entry marker without transmitting."""

from __future__ import annotations

import errno
import glob
import importlib.util
import os
from pathlib import Path
import select
import shutil
import stat
import subprocess
import sys
import termios
import time
import tty
from typing import NoReturn


sys.dont_write_bytecode = True
TRANSPORT_PATH = Path(__file__).with_name("network-root-acm.py")
SPEC = importlib.util.spec_from_file_location("rog5_network_root_acm", TRANSPORT_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("cannot load the accepted ACM identity transport")
TRANSPORT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(TRANSPORT)

PASS_LINE = (
    b"PASS P2 early-entry oracle init=entered "
    b"storage=untouched watchdog=armed"
)
FAIL_LINE = b"FAIL P2 early-entry oracle contract mismatch"
EXPECTED_LINES = (
    b"status=PASS",
    b"mode=early-entry",
    b"init=entered",
    b"kernel_release_read_status=0",
    b"kernel_release=7.1.4-gcfd385a1c754",
    b"kernel_expected=7.1.4-gcfd385a1c754",
    b"persistent_tokens=1",
    b"persistent_invalid_tokens=0",
    b"discovery_tokens=1",
    b"discovery_invalid_tokens=0",
    b"entry_tokens=1",
    b"entry_invalid_tokens=0",
    b"block_backed_mounts=0",
    b"watchdog_seconds=120",
    PASS_LINE,
)
EXPECTED_MARKER = b"\n".join(EXPECTED_LINES) + b"\n"


class MissingEntryMarkerError(RuntimeError):
    """No complete early-entry marker arrived before the bounded timeout."""


class EntryMarkerRejectedError(RuntimeError):
    """The target exposed a complete marker that did not pass its contract."""


def fail(message: str) -> NoReturn:
    raise RuntimeError(message)


def clean_lines(data: bytes) -> list[bytes]:
    clean = TRANSPORT.CSI.sub(b"", data).replace(b"\x1b", b"")
    return clean.replace(b"\r", b"").splitlines()


def extract_entry_marker(data: bytes) -> bytes | None:
    lines = clean_lines(data)
    width = len(EXPECTED_LINES)
    rejected = False
    for index, line in enumerate(lines):
        if line not in (b"status=PASS", b"status=FAIL"):
            continue
        candidate = tuple(lines[index : index + width])
        if len(candidate) != width:
            continue
        if candidate == EXPECTED_LINES:
            return EXPECTED_MARKER
        if candidate[-1] in (PASS_LINE, FAIL_LINE):
            rejected = True
    if rejected:
        raise EntryMarkerRejectedError(
            "complete P2 early-entry marker failed its exact contract"
        )
    return None


def read_entry_marker(path: str, *, timeout_seconds: float = 20.0) -> str:
    fd = os.open(path, os.O_RDONLY | os.O_NOCTTY | os.O_NONBLOCK)
    output = bytearray()
    try:
        tty.setraw(fd, termios.TCSANOW)
        attributes = termios.tcgetattr(fd)
        attributes[4] = termios.B115200
        attributes[5] = termios.B115200
        termios.tcsetattr(fd, termios.TCSANOW, attributes)

        deadline = time.monotonic() + timeout_seconds
        while time.monotonic() < deadline:
            ready, _, _ = select.select([fd], [], [], 0.2)
            if not ready:
                continue
            try:
                chunk = os.read(fd, 4096)
            except OSError as error:
                if error.errno != errno.EIO:
                    raise
                break
            if not chunk:
                break
            output.extend(chunk)
            if len(output) > 65536:
                del output[:-32768]
            marker = extract_entry_marker(bytes(output))
            if marker is not None:
                return marker.decode()
    finally:
        os.close(fd)
    raise MissingEntryMarkerError(
        "complete P2 early-entry marker was not received"
    )


def find_entry_acm() -> str:
    expected = {
        "ID_VENDOR_ID": "1d6b",
        "ID_MODEL_ID": "0104",
        "ID_MODEL": "ROG5_P2_entry_oracle",
    }
    matches: list[str] = []
    for device in glob.glob("/dev/ttyACM*"):
        try:
            properties = TRANSPORT.udev_properties(device)
            mode = os.stat(device, follow_symlinks=False).st_mode
        except (OSError, subprocess.CalledProcessError):
            continue
        if not stat.S_ISCHR(mode):
            continue
        if all(properties.get(key) == value for key, value in expected.items()):
            matches.append(device)
    if len(matches) != 1:
        fail(f"expected exactly one ROG5 P2 entry ACM device, found {len(matches)}")
    if not os.access(matches[0], os.R_OK):
        fail("P2 entry ACM is not readable")
    return matches[0]


def entry_acm_identity(path: str) -> tuple[str, int, str, str, str]:
    properties = TRANSPORT.udev_properties(path)
    device = os.stat(path, follow_symlinks=False)
    return (
        path,
        device.st_rdev,
        properties.get("DEVPATH", ""),
        properties.get("ID_PATH", ""),
        properties.get("ID_SERIAL", ""),
    )


def wait_for_stable_entry_acm(
    *,
    settle_seconds: float = 2.0,
    timeout_seconds: float = 80.0,
    poll_seconds: float = 0.2,
) -> str:
    deadline = time.monotonic() + timeout_seconds
    candidate: tuple[str, int, str, str, str] | None = None
    stable_since = 0.0
    while True:
        now = time.monotonic()
        if now >= deadline:
            fail("P2 entry ACM identity did not remain stable")
        try:
            path = find_entry_acm()
            identity = entry_acm_identity(path)
        except (OSError, RuntimeError, subprocess.CalledProcessError):
            candidate = None
            stable_since = 0.0
        else:
            if identity != candidate:
                candidate = identity
                stable_since = now
            elif now - stable_since >= settle_seconds:
                final_path = find_entry_acm()
                if entry_acm_identity(final_path) == candidate:
                    return final_path
                candidate = None
                stable_since = 0.0
        time.sleep(poll_seconds)


def main(arguments: list[str]) -> int:
    if os.environ.get("ALLOW_PERSISTENT_ROOT_ENTRY_ACM") != "1":
        fail(
            "set ALLOW_PERSISTENT_ROOT_ENTRY_ACM=1 "
            "for one receive-only marker read"
        )
    if arguments != ["read"]:
        fail("usage: persistent-root-entry-acm.py read")
    if os.uname().sysname != "Linux":
        fail("this host workflow requires Linux")
    for command in ("systemctl", "udevadm"):
        if shutil.which(command) is None:
            fail(f"missing host command: {command}")
    if subprocess.run(
        ["systemctl", "is-active", "--quiet", "ModemManager.service"],
        check=False,
    ).returncode == 0:
        fail("stop ModemManager before reading the P2 entry ACM")

    path = wait_for_stable_entry_acm()
    marker = read_entry_marker(path)
    print(marker, end="")
    print("PASS receive-only P2 early-entry ACM marker")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv[1:]))
    except (OSError, RuntimeError, subprocess.SubprocessError) as error:
        print(f"FAIL {error}", file=sys.stderr)
        raise SystemExit(1)
