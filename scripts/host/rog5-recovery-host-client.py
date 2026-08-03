#!/usr/bin/env python3
"""Connect one validated request to the fixed recovery-host socket."""

from __future__ import annotations

import os
from pathlib import Path
import re
import socket
import stat
import struct
import sys


SOCKET_PATH = Path("/run/rog5-recovery-host.sock")
STATUS_PREFIX = b"__ROG5_HOST_CONTROL_STATUS__="
RESPONSE_TIMEOUT_SECONDS = 1020
SHA256 = re.compile(r"[0-9a-f]{64}")
IDENTITY = re.compile(r"[a-z0-9][a-z0-9._-]{0,63}")
ANCHOR_PATH = re.compile(r"/[A-Za-z0-9._/+-]{1,399}")
TOKEN = SHA256


class ClientError(RuntimeError):
    pass


def fail(message: str) -> "NoReturn":
    raise ClientError(message)


def request(arguments: list[str]) -> bytes:
    action = arguments[0] if arguments else ""
    if action in {"bundle", "bundle-deferred"} and len(arguments) == 3:
        bundle, digest = arguments[1:]
        if (
            not IDENTITY.fullmatch(bundle)
            or ".." in bundle
            or bundle == "none"
        ):
            fail("invalid bundle identity")
        if not SHA256.fullmatch(digest) or digest == "0" * 64:
            fail("invalid manifest SHA-256")
    elif action == "fallback-profile-restore" and len(arguments) == 3:
        anchor, timeout = arguments[1:]
        if (
            not ANCHOR_PATH.fullmatch(anchor)
            or anchor.endswith("/")
            or "//" in anchor
            or ".." in anchor.split("/")
        ):
            fail("invalid recovery anchor path")
        if (
            not timeout.isascii()
            or not timeout.isdecimal()
            or not 1 <= int(timeout) <= 900
        ):
            fail("invalid fallback-profile timeout")
    elif action == "network-preflight-v1" and len(arguments) == 1:
        pass
    elif action == "network-preflight-v3" and len(arguments) == 2:
        if not SHA256.fullmatch(arguments[1]) or arguments[1] == "0" * 64:
            fail("invalid deployment package SHA-256")
    elif action == "network-serve-v1" and len(arguments) == 3:
        if not TOKEN.fullmatch(arguments[1]) or arguments[1] == "0" * 64:
            fail("invalid handoff token")
        if not arguments[2].isascii() or not arguments[2].isdecimal():
            fail("invalid server timeout")
        if not 600 <= int(arguments[2]) <= 900:
            fail("invalid server timeout")
    elif action == "network-serve-v3" and len(arguments) == 4:
        if not SHA256.fullmatch(arguments[1]) or arguments[1] == "0" * 64:
            fail("invalid deployment package SHA-256")
        if not TOKEN.fullmatch(arguments[2]) or arguments[2] == "0" * 64:
            fail("invalid handoff token")
        if not arguments[3].isascii() or not arguments[3].isdecimal():
            fail("invalid server timeout")
        if not 600 <= int(arguments[3]) <= 900:
            fail("invalid server timeout")
    elif action == "network-cancel" and len(arguments) == 2:
        if not TOKEN.fullmatch(arguments[1]) or arguments[1] == "0" * 64:
            fail("invalid handoff token")
    elif action == "network-export-state" and len(arguments) == 1:
        pass
    else:
        fail(
            "usage: rog5-recovery-host-client.py bundle BUNDLE SHA256 | "
            "bundle-deferred BUNDLE SHA256 | "
            "fallback-profile-restore ANCHOR TIMEOUT | "
            "network-preflight-v1 | network-preflight-v3 PACKAGE_SHA256 | "
            "network-serve-v1 TOKEN TIMEOUT | "
            "network-serve-v3 PACKAGE_SHA256 TOKEN TIMEOUT | "
            "network-cancel TOKEN | network-export-state"
        )
    payload = " ".join(arguments).encode("ascii") + b"\n"
    if len(payload) > 512:
        fail("request exceeds the fixed protocol bound")
    return payload


def socket_path() -> tuple[Path, bool]:
    offline = os.environ.get("ROG5_HOST_CONTROL_OFFLINE_TEST") == "1"
    override = os.environ.get("ROG5_HOST_CONTROL_SOCKET")
    if offline:
        if os.geteuid() == 0 or not override:
            fail("unsafe offline client mode")
        return Path(override), True
    if override is not None:
        fail("socket override is forbidden outside offline tests")
    return SOCKET_PATH, False


def verify_socket(path: Path, offline: bool) -> None:
    try:
        metadata = path.lstat()
    except OSError as error:
        raise ClientError(f"fixed host-control socket is unavailable: {path}") from error
    expected_uid = os.geteuid()
    expected_gid = os.getegid()
    if (
        not stat.S_ISSOCK(metadata.st_mode)
        or metadata.st_uid != expected_uid
        or metadata.st_gid != expected_gid
        or stat.S_IMODE(metadata.st_mode) != 0o600
        or metadata.st_nlink != 1
    ):
        fail("fixed host-control socket metadata is unsafe")
    if not offline:
        parent = path.parent.lstat()
        if (
            path != SOCKET_PATH
            or not stat.S_ISDIR(parent.st_mode)
            or parent.st_uid != 0
            or parent.st_gid != 0
            or stat.S_IMODE(parent.st_mode) != 0o755
        ):
            fail("fixed host-control socket ancestry is unsafe")


def run(arguments: list[str]) -> int:
    payload = request(arguments)
    path, offline = socket_path()
    verify_socket(path, offline)
    connection = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    connection.settimeout(10)
    try:
        connection.connect(str(path))
        peer_pid, peer_uid, peer_gid = struct.unpack(
            "3i", connection.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, 12)
        )
        expected_peer_uid = os.geteuid() if offline else 0
        expected_peer_gid = os.getegid() if offline else 0
        if peer_pid <= 0 or peer_uid != expected_peer_uid or peer_gid != expected_peer_gid:
            fail("host-control socket peer identity is unsafe")
        connection.sendall(payload)
        connection.shutdown(socket.SHUT_WR)
        connection.settimeout(RESPONSE_TIMEOUT_SECONDS)
        pending = b""
        status: int | None = None
        status_seen = False
        while True:
            chunk = connection.recv(65536)
            if not chunk:
                break
            pending += chunk
            while b"\n" in pending:
                line, pending = pending.split(b"\n", 1)
                if line.startswith(STATUS_PREFIX):
                    if status_seen or pending:
                        fail("host-control status framing is ambiguous")
                    value = line[len(STATUS_PREFIX) :]
                    if not value.isascii() or not value.isdigit():
                        fail("host-control status is malformed")
                    status = int(value)
                    if not 0 <= status <= 255:
                        fail("host-control status is out of range")
                    status_seen = True
                else:
                    if status_seen:
                        fail("host-control output followed its final status")
                    sys.stdout.buffer.write(line + b"\n")
                    sys.stdout.buffer.flush()
        if pending:
            fail("host-control response is not newline terminated")
        if status is None:
            fail("host-control response lacks its final status")
        return status
    finally:
        connection.close()


def main() -> int:
    try:
        return run(sys.argv[1:])
    except (ClientError, OSError, UnicodeError) as error:
        print(f"FAIL {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
