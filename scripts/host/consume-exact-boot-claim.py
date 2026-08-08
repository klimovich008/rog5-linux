#!/usr/bin/env python3
"""Irreversibly enter one repository-owned exact temporary-boot claim."""

from __future__ import annotations

import os
from pathlib import Path
import pwd
import stat
import sys


MANIFEST_SHA256 = (
    "4eacb90f08a80af1bdfed704c4a5e0d8eff600e94191c18c066b23b1228f7e76"
)


def exact_record(profile: str) -> bytes:
    return (
        "format=rog5-temporary-boot-consumption-v1\n"
        f"recovery_profile={profile}\n"
        "candidate=headless-netroot-early-diag-v1\n"
        f"manifest_sha256={MANIFEST_SHA256}\n"
        "state=BOOT_CLAIMED\n"
    ).encode("ascii")


# This is the repository-owned lookup. A caller selects a reviewed identifier;
# it cannot supply a pathname, candidate, manifest, or expected record bytes.
CLAIMS = {
    profile: exact_record(profile)
    for profile in (
        "headless-diagnostic-generation11-live-v1",
        "headless-diagnostic-generation12-live-v1",
    )
}


class ClaimError(RuntimeError):
    """The durable claim cannot be safely entered."""


def fail(message: str) -> None:
    raise ClaimError(message)


def expected_record(profile: str) -> bytes:
    try:
        return CLAIMS[profile]
    except KeyError as error:
        raise ClaimError("claim profile is not repository-owned") from error


def canonical_claim_root() -> Path:
    account_home = Path(pwd.getpwuid(os.geteuid()).pw_dir)
    if not account_home.is_absolute():
        fail("lifecycle account home must be absolute")
    try:
        account_home = account_home.resolve(strict=True)
    except OSError as error:
        raise ClaimError("lifecycle account home is unsafe or absent") from error
    return account_home / ".local/state/rog5-temporary-boot-consumption"


def open_claim_root(root: Path) -> int:
    if not root.is_absolute():
        fail("lifecycle claim state root must be absolute")
    flags = os.O_RDONLY | os.O_CLOEXEC | os.O_DIRECTORY
    nofollow = getattr(os, "O_NOFOLLOW", 0)
    try:
        directory_fd = os.open(root, flags | nofollow)
    except OSError as error:
        raise ClaimError("lifecycle claim root is unsafe or absent") from error
    try:
        metadata = os.fstat(directory_fd)
        opened_path = Path(f"/proc/self/fd/{directory_fd}").resolve(strict=True)
        if (
            opened_path != root
            or not stat.S_ISDIR(metadata.st_mode)
            or metadata.st_uid != os.geteuid()
            or stat.S_IMODE(metadata.st_mode) != 0o700
        ):
            fail("lifecycle claim root is unsafe or absent")
    except (ClaimError, OSError):
        os.close(directory_fd)
        raise
    return directory_fd


def verify_claim_root_path(root: Path, directory_fd: int) -> None:
    opened = os.fstat(directory_fd)
    try:
        current = os.stat(root, follow_symlinks=False)
    except OSError as error:
        raise ClaimError("lifecycle claim root changed during entry") from error
    if (
        current.st_dev != opened.st_dev
        or current.st_ino != opened.st_ino
        or not stat.S_ISDIR(current.st_mode)
        or current.st_uid != os.geteuid()
        or stat.S_IMODE(current.st_mode) != 0o700
    ):
        fail("lifecycle claim root changed during entry")


def verify_source_path(
    record_name: str,
    directory_fd: int,
    source_fd: int,
    expected: bytes,
) -> None:
    try:
        named = os.stat(
            record_name,
            dir_fd=directory_fd,
            follow_symlinks=False,
        )
    except OSError as error:
        raise ClaimError(
            "source BOOT_CLAIMED record changed during entry"
        ) from error
    opened = os.fstat(source_fd)
    if (
        named.st_dev != opened.st_dev
        or named.st_ino != opened.st_ino
        or not stat.S_ISREG(opened.st_mode)
        or opened.st_uid != os.geteuid()
        or stat.S_IMODE(opened.st_mode) != 0o600
        or opened.st_nlink != 1
    ):
        fail("source BOOT_CLAIMED record changed during entry")
    os.lseek(source_fd, 0, os.SEEK_SET)
    content = os.read(source_fd, len(expected) + 1)
    if content != expected or os.read(source_fd, 1):
        fail("source BOOT_CLAIMED record changed during entry")


def create_entered_record(
    entered_name: str,
    directory_fd: int,
    expected: bytes,
) -> int:
    flags = os.O_RDWR | os.O_CLOEXEC | os.O_CREAT | os.O_EXCL
    nofollow = getattr(os, "O_NOFOLLOW", 0)
    try:
        entered_fd = os.open(
            entered_name,
            flags | nofollow,
            0o600,
            dir_fd=directory_fd,
        )
    except FileExistsError as error:
        raise ClaimError(
            "durable BOOT_CLAIMED record is already entered"
        ) from error
    except OSError as error:
        raise ClaimError("cannot enter durable BOOT_CLAIMED record") from error
    try:
        os.fchmod(entered_fd, 0o600)
        remaining = memoryview(expected)
        while remaining:
            written = os.write(entered_fd, remaining)
            if written <= 0:
                fail("cannot write entered BOOT_CLAIMED record")
            remaining = remaining[written:]
        os.fsync(entered_fd)
        os.lseek(entered_fd, 0, os.SEEK_SET)
        metadata = os.fstat(entered_fd)
        content = os.read(entered_fd, len(expected) + 1)
        named = os.stat(
            entered_name,
            dir_fd=directory_fd,
            follow_symlinks=False,
        )
        if (
            not stat.S_ISREG(metadata.st_mode)
            or metadata.st_uid != os.geteuid()
            or stat.S_IMODE(metadata.st_mode) != 0o600
            or metadata.st_nlink != 1
            or named.st_dev != metadata.st_dev
            or named.st_ino != metadata.st_ino
            or content != expected
            or os.read(entered_fd, 1)
        ):
            fail("entered BOOT_CLAIMED record is not exact")
    except Exception:
        os.close(entered_fd)
        raise
    return entered_fd


def consume(profile: str, root: Path | None = None) -> None:
    expected = expected_record(profile)
    record_name = f"{profile}.record"
    entered_name = f"{record_name}.entered"
    if root is None:
        root = canonical_claim_root()
    directory_fd = open_claim_root(root)
    flags = os.O_RDONLY | os.O_CLOEXEC
    nofollow = getattr(os, "O_NOFOLLOW", 0)
    source_fd = -1
    entered_fd = -1
    try:
        try:
            os.stat(entered_name, dir_fd=directory_fd, follow_symlinks=False)
        except FileNotFoundError:
            pass
        except OSError as error:
            raise ClaimError("entered BOOT_CLAIMED record is unsafe") from error
        else:
            fail("durable BOOT_CLAIMED record is already entered")

        try:
            source_fd = os.open(
                record_name,
                flags | nofollow,
                dir_fd=directory_fd,
            )
        except OSError as error:
            raise ClaimError(
                "durable BOOT_CLAIMED record is unsafe or absent"
            ) from error
        metadata = os.fstat(source_fd)
        if (
            not stat.S_ISREG(metadata.st_mode)
            or metadata.st_uid != os.geteuid()
            or stat.S_IMODE(metadata.st_mode) != 0o600
            or metadata.st_nlink != 1
        ):
            fail("durable BOOT_CLAIMED record is unsafe or absent")
        content = os.read(source_fd, len(expected) + 1)
        if content != expected or os.read(source_fd, 1):
            fail("durable BOOT_CLAIMED record is not exact")

        verify_source_path(record_name, directory_fd, source_fd, expected)
        entered_fd = create_entered_record(
            entered_name,
            directory_fd,
            expected,
        )
        os.fsync(directory_fd)

        verify_source_path(
            record_name,
            directory_fd,
            source_fd,
            expected,
        )
        try:
            os.unlink(record_name, dir_fd=directory_fd)
        except OSError as error:
            raise ClaimError(
                "durable BOOT_CLAIMED record entered but source cleanup failed"
            ) from error
        if os.fstat(source_fd).st_nlink != 0:
            fail("source BOOT_CLAIMED record changed during entry")
        os.fsync(directory_fd)
        verify_claim_root_path(root, directory_fd)
    finally:
        if entered_fd >= 0:
            os.close(entered_fd)
        if source_fd >= 0:
            os.close(source_fd)
        os.close(directory_fd)


def main() -> int:
    if len(sys.argv) != 2:
        fail("exact-record claim consumer requires one repository-owned profile")
    profile = sys.argv[1]
    consume(profile)
    print(f"PASS exact durable BOOT_CLAIMED record entered: {profile}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ClaimError, OSError, ValueError) as error:
        print(f"FAIL {error}", file=sys.stderr)
        raise SystemExit(1)
