#!/usr/bin/env python3
"""Irreversibly enter the exact Generation-11 temporary-boot claim."""

from __future__ import annotations

import os
from pathlib import Path
import stat
import sys


PROFILE = "headless-diagnostic-generation11-live-v1"
RECORD_NAME = f"{PROFILE}.record"
ENTERED_NAME = f"{RECORD_NAME}.entered"
EXPECTED = (
    "format=rog5-temporary-boot-consumption-v1\n"
    f"recovery_profile={PROFILE}\n"
    "candidate=headless-netroot-early-diag-v1\n"
    "manifest_sha256="
    "4eacb90f08a80af1bdfed704c4a5e0d8eff600e94191c18c066b23b1228f7e76\n"
    "state=BOOT_CLAIMED\n"
).encode("ascii")


class ClaimError(RuntimeError):
    """The durable claim cannot be safely entered."""


def fail(message: str) -> None:
    raise ClaimError(message)


def claim_root() -> Path:
    value = os.environ.get("XDG_STATE_HOME")
    base = Path(value) if value else Path.home() / ".local" / "state"
    if not base.is_absolute():
        fail("lifecycle claim state root must be absolute")
    root = base / "rog5-temporary-boot-consumption"
    try:
        resolved = root.resolve(strict=True)
        metadata = root.lstat()
    except OSError as error:
        raise ClaimError(
            "generation-11 lifecycle claim root is unsafe or absent"
        ) from error
    if (
        resolved != root
        or not stat.S_ISDIR(metadata.st_mode)
        or metadata.st_uid != os.geteuid()
        or stat.S_IMODE(metadata.st_mode) != 0o700
    ):
        fail("generation-11 lifecycle claim root is unsafe or absent")
    return root


def consume() -> None:
    root = claim_root()
    source = root / RECORD_NAME
    entered = root / ENTERED_NAME
    if os.path.lexists(entered):
        fail("generation-11 durable BOOT_CLAIMED record is already entered")

    flags = os.O_RDONLY | os.O_CLOEXEC
    directory_flags = flags | os.O_DIRECTORY
    nofollow = getattr(os, "O_NOFOLLOW", 0)
    directory_fd = os.open(root, directory_flags | nofollow)
    source_fd = -1
    entered_fd = -1
    try:
        try:
            source_fd = os.open(
                RECORD_NAME,
                flags | nofollow,
                dir_fd=directory_fd,
            )
        except OSError as error:
            raise ClaimError(
                "generation-11 durable BOOT_CLAIMED record is unsafe or absent"
            ) from error
        metadata = os.fstat(source_fd)
        if (
            not stat.S_ISREG(metadata.st_mode)
            or metadata.st_uid != os.geteuid()
            or stat.S_IMODE(metadata.st_mode) != 0o600
            or metadata.st_nlink != 1
        ):
            fail(
                "generation-11 durable BOOT_CLAIMED record is unsafe or absent"
            )
        content = os.read(source_fd, len(EXPECTED) + 1)
        if content != EXPECTED or os.read(source_fd, 1):
            fail("generation-11 durable BOOT_CLAIMED record is not exact")
        try:
            os.link(
                RECORD_NAME,
                ENTERED_NAME,
                src_dir_fd=directory_fd,
                dst_dir_fd=directory_fd,
                follow_symlinks=False,
            )
        except FileExistsError as error:
            raise ClaimError(
                "generation-11 durable BOOT_CLAIMED record is already entered"
            ) from error
        except OSError as error:
            raise ClaimError(
                "cannot enter generation-11 durable BOOT_CLAIMED record"
            ) from error
        try:
            entered_fd = os.open(
                ENTERED_NAME,
                flags | nofollow,
                dir_fd=directory_fd,
            )
        except OSError as error:
            raise ClaimError(
                "generation-11 entered BOOT_CLAIMED record cannot be verified"
            ) from error
        entered_metadata = os.fstat(entered_fd)
        entered_content = os.read(entered_fd, len(EXPECTED) + 1)
        if (
            entered_metadata.st_dev != metadata.st_dev
            or entered_metadata.st_ino != metadata.st_ino
            or entered_content != EXPECTED
            or os.read(entered_fd, 1)
        ):
            fail(
                "generation-11 entered BOOT_CLAIMED record does not match "
                "the validated claim"
            )
        os.fsync(directory_fd)
        current_source = os.stat(
            RECORD_NAME,
            dir_fd=directory_fd,
            follow_symlinks=False,
        )
        if (
            current_source.st_dev != metadata.st_dev
            or current_source.st_ino != metadata.st_ino
        ):
            fail(
                "generation-11 source BOOT_CLAIMED record changed during entry"
            )
        try:
            os.unlink(RECORD_NAME, dir_fd=directory_fd)
        except OSError as error:
            raise ClaimError(
                "generation-11 durable BOOT_CLAIMED record entered but source cleanup failed"
            ) from error
        os.fsync(directory_fd)
    finally:
        if entered_fd >= 0:
            os.close(entered_fd)
        if source_fd >= 0:
            os.close(source_fd)
        os.close(directory_fd)


def main() -> int:
    if len(sys.argv) != 1:
        fail("generation-11 claim consumer accepts no arguments")
    consume()
    print("PASS generation-11 durable BOOT_CLAIMED record entered")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ClaimError, OSError, ValueError) as error:
        print(f"FAIL {error}", file=sys.stderr)
        raise SystemExit(1)
