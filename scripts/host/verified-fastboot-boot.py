#!/usr/bin/env python3
"""Boot one verified, write-sealed in-memory snapshot with fixed fastboot."""

from __future__ import annotations

import fcntl
import hashlib
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
from typing import NoReturn


FASTBOOT = Path("/usr/bin/fastboot")
PARTITION_SIZE = 100_663_296
SHA256 = re.compile(r"[0-9a-f]{64}\Z")
SERIAL = re.compile(r"[A-Za-z0-9._:-]{1,128}\Z")


def fail(message: str) -> NoReturn:
    raise RuntimeError(message)


def file_identity(metadata: os.stat_result) -> tuple[int, ...]:
    return (
        metadata.st_dev,
        metadata.st_ino,
        metadata.st_mode,
        metadata.st_uid,
        metadata.st_gid,
        metadata.st_nlink,
        metadata.st_size,
        metadata.st_mtime_ns,
        metadata.st_ctime_ns,
    )


def validate_fastboot() -> None:
    for path in (*FASTBOOT.parents, FASTBOOT):
        metadata = path.lstat()
        if path == FASTBOOT:
            valid_type = stat.S_ISREG(metadata.st_mode)
        else:
            valid_type = stat.S_ISDIR(metadata.st_mode)
        if (
            not valid_type
            or metadata.st_uid != 0
            or stat.S_IMODE(metadata.st_mode) & 0o022
        ):
            fail("fixed fastboot path is not root-controlled")
    metadata = FASTBOOT.lstat()
    if metadata.st_nlink != 1 or not os.access(FASTBOOT, os.X_OK):
        fail("fixed fastboot executable metadata is unsafe")


def sealed_snapshot(image: Path, expected_sha256: str) -> int:
    flags = os.O_RDONLY | os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    source = os.open(image, flags)
    snapshot = -1
    try:
        before = os.fstat(source)
        if (
            not stat.S_ISREG(before.st_mode)
            or before.st_uid != os.geteuid()
            or before.st_nlink != 1
            or stat.S_IMODE(before.st_mode) & 0o022
            or before.st_size != PARTITION_SIZE
        ):
            fail("temporary boot image metadata is unsafe")
        snapshot = os.memfd_create(
            "rog5-stable-recovery-boot",
            os.MFD_ALLOW_SEALING | os.MFD_CLOEXEC,
        )
        digest = hashlib.sha256()
        observed = 0
        while block := os.read(source, 1024 * 1024):
            digest.update(block)
            observed += len(block)
            view = memoryview(block)
            while view:
                written = os.write(snapshot, view)
                if written < 1:
                    fail("sealed snapshot write made no progress")
                view = view[written:]
        after = os.fstat(source)
        if (
            observed != before.st_size
            or file_identity(before) != file_identity(after)
            or digest.hexdigest() != expected_sha256
        ):
            fail("temporary boot image changed or has the wrong identity")
        os.fchmod(snapshot, 0o400)
        seals = (
            fcntl.F_SEAL_SEAL
            | fcntl.F_SEAL_SHRINK
            | fcntl.F_SEAL_GROW
            | fcntl.F_SEAL_WRITE
        )
        fcntl.fcntl(snapshot, fcntl.F_ADD_SEALS, seals)
        if fcntl.fcntl(snapshot, fcntl.F_GET_SEALS) != seals:
            fail("temporary boot snapshot is not fully sealed")
        os.lseek(snapshot, 0, os.SEEK_SET)
        return snapshot
    except BaseException:
        if snapshot >= 0:
            os.close(snapshot)
        raise
    finally:
        os.close(source)


def boot(image: Path, expected_sha256: str, serial: str) -> None:
    if os.environ.get("ALLOW_TEMPORARY_BOOT") != "1":
        fail("set ALLOW_TEMPORARY_BOOT=1 for one non-flashing boot")
    if os.environ.get("ALLOW_HEADLESS_LIVE_GATE") != "1":
        fail("set ALLOW_HEADLESS_LIVE_GATE=1 for this attended candidate")
    if not SHA256.fullmatch(expected_sha256) or expected_sha256 == "0" * 64:
        fail("invalid expected temporary boot image SHA-256")
    if not SERIAL.fullmatch(serial):
        fail("invalid fastboot serial")
    validate_fastboot()
    snapshot = sealed_snapshot(image, expected_sha256)
    try:
        subprocess.run(
            [
                str(FASTBOOT),
                "-s",
                serial,
                "boot",
                f"/proc/self/fd/{snapshot}",
            ],
            check=True,
            stdin=subprocess.DEVNULL,
            pass_fds=(snapshot,),
        )
    finally:
        os.close(snapshot)


def main(arguments: list[str]) -> int:
    if len(arguments) != 3:
        fail(
            "usage: verified-fastboot-boot.py "
            "IMAGE EXPECTED_SHA256 FASTBOOT_SERIAL"
        )
    boot(Path(arguments[0]), arguments[1], arguments[2])
    print("PASS fixed fastboot accepted one sealed temporary boot snapshot")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv[1:]))
    except (OSError, RuntimeError, subprocess.SubprocessError) as error:
        print(f"FAIL {error}", file=sys.stderr)
        raise SystemExit(1)
