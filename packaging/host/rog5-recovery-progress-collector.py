#!/usr/bin/env python3
"""Open one privileged NCM listener, drop privilege, and capture progress."""

from __future__ import annotations

import ctypes
import errno
import hashlib
import os
from pathlib import Path
import re
import signal
import socket
import stat
import sys
import time


INSTALLED_ROOT = Path("/usr/libexec/rog5-recovery-host")
OUTPUT_NAME = "recovery-progress.capture"
STOP_NAME = "recovery-progress.stop"
READY_PREFIX = "READY receive-only recovery progress collector"
PATH_PATTERN = re.compile(r"/[A-Za-z0-9._/+-]{1,399}\Z")
INTERFACE = re.compile(r"[A-Za-z0-9_.:-]{1,15}\Z")
IDENTITY = re.compile(r"[a-z0-9][a-z0-9._-]{0,63}\Z")
SHA256 = re.compile(r"[0-9a-f]{64}\Z")
PR_CAPBSET_DROP = 24
PR_SET_PDEATHSIG = 1
PR_SET_NO_NEW_PRIVS = 38
PR_CAP_AMBIENT = 47
PR_CAP_AMBIENT_CLEAR_ALL = 4


class CollectorError(RuntimeError):
    """A fail-closed progress-collector condition."""


def fail(message: str) -> "NoReturn":
    raise CollectorError(message)


def module_root() -> Path:
    script = Path(__file__).resolve(strict=True)
    if script.parent == INSTALLED_ROOT:
        root = script.parent / "python"
    else:
        root = script.parents[2]
    if not root.is_dir() or root.is_symlink():
        fail("progress collector module root is unsafe")
    return root


sys.path.insert(0, str(module_root()))

from tools.recovery_control import ZERO_ID  # noqa: E402
from tools.recovery_control.host_progress_collector import (  # noqa: E402
    CollectorRefusal,
    ProgressCapture,
    collect_listener,
    open_fixed_listener,
)


def parse_decimal(value: str, name: str, minimum: int, maximum: int) -> int:
    if (
        not value.isascii()
        or not value.isdecimal()
        or value.startswith("0")
        or not minimum <= int(value) <= maximum
    ):
        fail(f"invalid {name}")
    return int(value)


def validate_arguments(
    arguments: list[str],
) -> tuple[str, str, str, Path, int, int, int, Path, int]:
    if len(arguments) != 9:
        fail(
            "usage: rog5-recovery-progress-collector.py "
            "INTERFACE BUNDLE MANIFEST_SHA256 OUTPUT_DIRECTORY UID GID "
            "TIMEOUT BUNDLE_EOF_MARKER CONTROLLER_PID"
        )
    (
        interface,
        bundle,
        manifest,
        output_value,
        uid_value,
        gid_value,
        timeout_value,
        eof_value,
        parent_value,
    ) = arguments
    if not INTERFACE.fullmatch(interface):
        fail("invalid progress interface")
    if (
        not IDENTITY.fullmatch(bundle)
        or ".." in bundle
        or bundle == "none"
    ):
        fail("invalid progress bundle")
    if not SHA256.fullmatch(manifest) or manifest == "0" * 64:
        fail("invalid progress manifest SHA-256")
    if (
        not PATH_PATTERN.fullmatch(output_value)
        or output_value.endswith("/")
        or "//" in output_value
        or ".." in output_value.split("/")
    ):
        fail("invalid progress output directory")
    uid = parse_decimal(uid_value, "progress operator UID", 1, 2**31 - 1)
    gid = parse_decimal(gid_value, "progress operator GID", 1, 2**31 - 1)
    timeout = parse_decimal(timeout_value, "progress timeout", 30, 300)
    if (
        not PATH_PATTERN.fullmatch(eof_value)
        or eof_value.endswith("/")
        or "//" in eof_value
        or ".." in eof_value.split("/")
    ):
        fail("invalid progress bundle-EOF marker")
    parent_pid = parse_decimal(
        parent_value,
        "progress controller PID",
        2,
        2**31 - 1,
    )
    return (
        interface,
        bundle,
        manifest,
        Path(output_value),
        uid,
        gid,
        timeout,
        Path(eof_value),
        parent_pid,
    )


def open_output_directory(path: Path, uid: int, gid: int) -> tuple[int, os.stat_result]:
    try:
        if path.resolve(strict=True) != path:
            fail("progress output directory path is not canonical")
        descriptor = os.open(
            path,
            os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
        )
    except OSError as error:
        raise CollectorError("progress output directory cannot be opened") from error
    try:
        metadata = os.fstat(descriptor)
        named = path.lstat()
        if (
            not stat.S_ISDIR(metadata.st_mode)
            or metadata.st_uid != uid
            or metadata.st_gid != gid
            or stat.S_IMODE(metadata.st_mode) != 0o700
            or (
                metadata.st_dev,
                metadata.st_ino,
                metadata.st_uid,
                metadata.st_gid,
                stat.S_IFMT(metadata.st_mode),
            )
            != (
                named.st_dev,
                named.st_ino,
                named.st_uid,
                named.st_gid,
                stat.S_IFMT(named.st_mode),
            )
        ):
            fail("progress output directory metadata is unsafe")
        try:
            os.stat(OUTPUT_NAME, dir_fd=descriptor, follow_symlinks=False)
        except FileNotFoundError:
            pass
        else:
            fail("progress output already exists")
        return descriptor, metadata
    except BaseException:
        os.close(descriptor)
        raise


def prctl(option: int, argument: int = 0) -> None:
    libc = ctypes.CDLL(None, use_errno=True)
    operation = libc.prctl
    operation.argtypes = (
        ctypes.c_int,
        ctypes.c_ulong,
        ctypes.c_ulong,
        ctypes.c_ulong,
        ctypes.c_ulong,
    )
    operation.restype = ctypes.c_int
    if operation(option, argument, 0, 0, 0) != 0:
        error = ctypes.get_errno()
        raise CollectorError("progress privilege control failed") from OSError(
            error, os.strerror(error)
        )


def arm_parent_death(expected_parent: int) -> None:
    """Terminate with the exact controller, including across UID changes."""
    prctl(PR_SET_PDEATHSIG, signal.SIGTERM)
    if os.getppid() != expected_parent:
        fail("progress collector parent changed")


def process_status() -> dict[str, str]:
    try:
        lines = Path("/proc/self/status").read_text(encoding="ascii").splitlines()
    except (OSError, UnicodeDecodeError) as error:
        raise CollectorError("progress privilege status is unavailable") from error
    values: dict[str, str] = {}
    for line in lines:
        name, separator, value = line.partition(":")
        if separator and name not in values:
            values[name] = value.strip()
    return values


def drop_privileges(uid: int, gid: int) -> None:
    if os.geteuid() != 0 or uid == 0 or gid == 0:
        fail("progress collector requires a distinct root-to-operator drop")
    prctl(PR_SET_NO_NEW_PRIVS, 1)
    try:
        cap_last = int(
            Path("/proc/sys/kernel/cap_last_cap").read_text(encoding="ascii").strip()
        )
    except (OSError, UnicodeError, ValueError) as error:
        raise CollectorError("kernel capability bound is unavailable") from error
    if not 0 <= cap_last <= 255:
        fail("kernel capability bound is unsafe")
    for capability in range(cap_last + 1):
        prctl(PR_CAPBSET_DROP, capability)
    prctl(PR_CAP_AMBIENT, PR_CAP_AMBIENT_CLEAR_ALL)
    os.setgroups([])
    os.setresgid(gid, gid, gid)
    os.setresuid(uid, uid, uid)
    values = process_status()
    expected_uid = f"{uid}\t{uid}\t{uid}\t{uid}"
    expected_gid = f"{gid}\t{gid}\t{gid}\t{gid}"
    if (
        values.get("Uid") != expected_uid
        or values.get("Gid") != expected_gid
        or values.get("Groups", "")
        or values.get("NoNewPrivs") != "1"
        or any(
            values.get(name) != "0000000000000000"
            for name in ("CapInh", "CapPrm", "CapEff", "CapBnd", "CapAmb")
        )
    ):
        fail("progress collector privilege drop is incomplete")
    try:
        os.setresuid(0, 0, 0)
    except PermissionError:
        pass
    else:
        fail("progress collector could regain root")


def open_output(descriptor: int, directory: os.stat_result, uid: int, gid: int) -> int:
    current = os.fstat(descriptor)
    if (
        current.st_dev,
        current.st_ino,
        current.st_uid,
        current.st_gid,
        stat.S_IFMT(current.st_mode),
        stat.S_IMODE(current.st_mode),
    ) != (
        directory.st_dev,
        directory.st_ino,
        uid,
        gid,
        stat.S_IFDIR,
        0o700,
    ):
        fail("progress output directory changed before publication")
    try:
        output = os.open(
            OUTPUT_NAME,
            os.O_WRONLY
            | os.O_CREAT
            | os.O_EXCL
            | os.O_NOFOLLOW
            | os.O_CLOEXEC,
            0o600,
            dir_fd=descriptor,
        )
    except OSError as error:
        raise CollectorError("progress output cannot be created") from error
    metadata = os.fstat(output)
    if (
        not stat.S_ISREG(metadata.st_mode)
        or metadata.st_uid != uid
        or metadata.st_gid != gid
        or stat.S_IMODE(metadata.st_mode) != 0o600
        or metadata.st_nlink != 1
        or metadata.st_size != 0
    ):
        os.close(output)
        fail("progress output metadata is unsafe")
    return output


def partial_capture(bundle: str, manifest: str, reason: str) -> ProgressCapture:
    return ProgressCapture(
        session=ZERO_ID,
        request=ZERO_ID,
        bundle=bundle,
        manifest_sha256=manifest,
        phases=(),
        wire_bytes=0,
        wire_sha256=hashlib.sha256(b"").hexdigest(),
        result="PARTIAL",
        truncated=True,
        reason=reason,
    )


def publish_capture(output: int, directory: int, capture: ProgressCapture) -> None:
    payload = capture.record()
    written = 0
    while written < len(payload):
        count = os.write(output, payload[written:])
        if count <= 0:
            fail("progress output write made no progress")
        written += count
    os.fsync(output)
    if os.fstat(output).st_size != len(payload):
        fail("progress output size changed during publication")
    os.fsync(directory)


def run(arguments: list[str]) -> int:
    (
        interface,
        bundle,
        manifest,
        output_path,
        uid,
        gid,
        timeout,
        eof_marker,
        parent_pid,
    ) = validate_arguments(arguments)
    listener: socket.socket | None = None
    directory = -1
    output = -1
    interrupted = False

    def stop(_signum: int, _frame: object) -> None:
        nonlocal interrupted
        interrupted = True

    previous = {
        signum: signal.signal(signum, stop)
        for signum in (signal.SIGHUP, signal.SIGINT, signal.SIGTERM)
    }
    try:
        arm_parent_death(parent_pid)
        listener = open_fixed_listener(interface)
        directory, directory_identity = open_output_directory(
            output_path,
            uid,
            gid,
        )
        drop_privileges(uid, gid)
        # Linux clears PDEATHSIG when credentials change; re-arm and then
        # recheck the parent to close the change-of-credentials race.
        arm_parent_death(parent_pid)
        output = open_output(directory, directory_identity, uid, gid)
        stop_path = output_path / STOP_NAME
        deadline = time.monotonic() + timeout
        print(
            f"{READY_PREFIX} on 169.254.77.1:8081 via {interface}",
            flush=True,
        )
        try:
            capture = collect_listener(
                listener,
                bundle=bundle,
                manifest_sha256=manifest,
                deadline=deadline,
                admission_stop_requested=lambda: (
                    interrupted or eof_marker.exists()
                ),
                stream_stop_requested=lambda: (
                    interrupted or stop_path.exists()
                ),
            )
        except CollectorRefusal as error:
            if error.capture is not None:
                capture = error.capture
            else:
                detail = str(error)
                if detail == "progress admission stopped":
                    reason = "NO_ADMISSION"
                elif detail == "progress listener timed out":
                    reason = "LISTENER_TIMEOUT"
                else:
                    reason = "REFUSED"
                capture = partial_capture(bundle, manifest, reason)
        publish_capture(output, directory, capture)
        print(
            "PASS recovery progress capture "
            f"result={capture.result} reason={capture.reason} "
            f"records={len(capture.phases)} authority=NONE",
            flush=True,
        )
        return 0
    finally:
        for signum, handler in previous.items():
            signal.signal(signum, handler)
        if listener is not None:
            listener.close()
        if output >= 0:
            os.close(output)
        if directory >= 0:
            os.close(directory)


def main() -> int:
    try:
        return run(sys.argv[1:])
    except (CollectorError, CollectorRefusal, OSError, UnicodeError, ValueError) as error:
        print(f"FAIL {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
