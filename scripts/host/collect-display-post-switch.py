#!/usr/bin/env python3
"""Collect one exact signed post-switch display record over ROG5 NCM."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
import re
import socket
import stat
import sys
import time
from typing import NoReturn


HOST_ADDRESS = "169.254.77.1"
TARGET_ADDRESS = "169.254.77.2"
PORT = 8077
MAX_RECORD_BYTES = 16384
FIELDS = (
    "format",
    "candidate",
    "target_release",
    "boot_id",
    "sample_seconds",
    "refgen_status",
    "refgen_hex",
    "dsi_status",
    "dsi_hex",
    "drm_status",
    "drm_hex",
    "fb_status",
    "fb_hex",
    "backlight_status",
    "backlight_hex",
    "status_screen_status",
    "status_screen_hex",
    "dmesg_status",
    "dmesg_sha256",
    "dmesg_tail_hex",
    "result",
)
OBSERVATIONS = (
    "refgen",
    "dsi",
    "drm",
    "fb",
    "backlight",
    "status_screen",
)
STATUSES = frozenset({"present", "absent", "unsupported", "error"})
CANDIDATE = re.compile(r"[a-z0-9][a-z0-9.-]{0,63}\Z")
RELEASE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._+-]{0,95}\Z")
BOOT_ID = re.compile(
    r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-"
    r"[0-9a-f]{4}-[0-9a-f]{12}\Z"
)
SHA256 = re.compile(r"[0-9a-f]{64}\Z")
HEX = re.compile(r"(?:[0-9a-f]{2})*\Z")


class DisplayReportError(RuntimeError):
    """The target display record is not exact or trustworthy."""


def fail(message: str) -> NoReturn:
    raise DisplayReportError(message)


def parse_record(
    payload: bytes, expected_candidate: str, expected_release: str
) -> dict[str, str]:
    if not 1 <= len(payload) <= MAX_RECORD_BYTES:
        fail("display record size is outside policy")
    try:
        text = payload.decode("ascii")
    except UnicodeDecodeError as error:
        raise DisplayReportError("display record is not ASCII") from error
    if not text.endswith("\n") or "\r" in text or "\x00" in text:
        fail("display record framing changed")
    lines = text.splitlines()
    if len(lines) != len(FIELDS):
        fail("display record field count changed")
    values: dict[str, str] = {}
    for field, line in zip(FIELDS, lines, strict=True):
        prefix = f"{field}="
        if not line.startswith(prefix):
            fail("display record field order changed")
        values[field] = line[len(prefix) :]
    if values["format"] != "rog5-display-post-switch-v1":
        fail("display record format changed")
    if (
        not CANDIDATE.fullmatch(values["candidate"])
        or ".." in values["candidate"]
        or values["candidate"] != expected_candidate
    ):
        fail("display candidate identity changed")
    if (
        not RELEASE.fullmatch(values["target_release"])
        or values["target_release"] != expected_release
    ):
        fail("display target release changed")
    if not BOOT_ID.fullmatch(values["boot_id"]):
        fail("display boot identity is invalid")
    if (
        not values["sample_seconds"].isdecimal()
        or int(values["sample_seconds"]) > 60
    ):
        fail("display sampling duration is invalid")
    for name in OBSERVATIONS:
        status = values[f"{name}_status"]
        encoded = values[f"{name}_hex"]
        if status not in STATUSES or not HEX.fullmatch(encoded) or len(encoded) > 2048:
            fail(f"{name} observation is invalid")
        if status == "present" and not encoded:
            fail(f"{name} present observation is empty")
        if status in {"absent", "unsupported"} and encoded:
            fail(f"{name} absent observation carries a value")
    dmesg_status = values["dmesg_status"]
    dmesg_hex = values["dmesg_tail_hex"]
    dmesg_sha256 = values["dmesg_sha256"]
    if dmesg_status not in STATUSES or not HEX.fullmatch(dmesg_hex):
        fail("dmesg observation is invalid")
    if len(dmesg_hex) > 8192:
        fail("dmesg observation exceeds its fixed bound")
    if dmesg_status == "present":
        if not dmesg_hex or not SHA256.fullmatch(dmesg_sha256):
            fail("present dmesg observation is incomplete")
        raw = bytes.fromhex(dmesg_hex)
        if hashlib.sha256(raw).hexdigest() != dmesg_sha256:
            fail("dmesg observation hash changed")
    elif dmesg_sha256 != "none" or dmesg_hex:
        fail("non-present dmesg observation carries data")
    if values["result"] != "PASS":
        fail("display record lacks its terminal marker")
    return values


def write_record(path: Path, payload: bytes) -> None:
    descriptor = os.open(
        path,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC,
        0o600,
    )
    try:
        os.fchmod(descriptor, 0o600)
        written = 0
        while written < len(payload):
            count = os.write(descriptor, payload[written:])
            if count <= 0:
                fail("cannot write display record")
            written += count
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    metadata = path.lstat()
    if (
        not stat.S_ISREG(metadata.st_mode)
        or metadata.st_uid != os.geteuid()
        or stat.S_IMODE(metadata.st_mode) != 0o600
        or metadata.st_nlink != 1
    ):
        fail("display record output metadata is unsafe")


def receive(listener: socket.socket) -> bytes:
    connection, peer = listener.accept()
    with connection:
        connection.settimeout(5.0)
        payload = bytearray()
        while len(payload) <= MAX_RECORD_BYTES:
            block = connection.recv(MAX_RECORD_BYTES + 1 - len(payload))
            if not block:
                break
            payload.extend(block)
        local = connection.getsockname()
    if peer[0] != TARGET_ADDRESS or local[0] != HOST_ADDRESS:
        fail("display record used the wrong NCM endpoint")
    return bytes(payload)


def collect(
    expected_candidate: str,
    expected_release: str,
    output: Path,
    timeout_seconds: int,
) -> dict[str, str]:
    if timeout_seconds < 1 or timeout_seconds > 180:
        fail("collector timeout is outside policy")
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        listener.bind((HOST_ADDRESS, PORT))
        listener.listen(2)
        listener.settimeout(float(timeout_seconds))
        print(
            f"READY display post-switch collector on {HOST_ADDRESS}:{PORT}",
            flush=True,
        )
        started = time.monotonic()
        payload = receive(listener)
        if time.monotonic() - started > timeout_seconds:
            fail("display record escaped its fixed deadline")
    values = parse_record(payload, expected_candidate, expected_release)
    write_record(output, payload)
    return values


def main(arguments: list[str]) -> int:
    if len(arguments) != 5 or arguments[0] != "collect":
        fail("usage: collect-display-post-switch.py collect CANDIDATE RELEASE OUTPUT TIMEOUT")
    timeout = arguments[4]
    if not timeout.isdecimal():
        fail("collector timeout is invalid")
    values = collect(
        arguments[1], arguments[2], Path(arguments[3]), int(timeout)
    )
    print(
        "PASS display post-switch record "
        f"boot_id={values['boot_id']} drm={values['drm_status']} "
        f"backlight={values['backlight_status']}",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv[1:]))
    except (DisplayReportError, OSError, TimeoutError) as error:
        print(f"FAIL {error}", file=sys.stderr)
        raise SystemExit(1)
