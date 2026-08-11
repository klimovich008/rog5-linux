#!/usr/bin/env python3
"""Irreversibly enter one repository-owned exact temporary-boot claim."""

from __future__ import annotations

import os
from pathlib import Path
import pwd
import stat
import sys


# This is the repository-owned lookup. A caller selects a reviewed identifier;
# it cannot supply a pathname, candidate, manifest, or expected record bytes.
CLAIMS = {
    "headless-diagnostic-generation11-live-v1": (
        b"format=rog5-temporary-boot-consumption-v1\n"
        b"recovery_profile=headless-diagnostic-generation11-live-v1\n"
        b"candidate=headless-netroot-early-diag-v1\n"
        b"manifest_sha256="
        b"4eacb90f08a80af1bdfed704c4a5e0d8eff600e94191c18c066b23b1228f7e76\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "headless-diagnostic-generation12-live-v1": (
        b"format=rog5-temporary-boot-consumption-v1\n"
        b"recovery_profile=headless-diagnostic-generation12-live-v1\n"
        b"candidate=headless-netroot-early-diag-v1\n"
        b"manifest_sha256="
        b"4eacb90f08a80af1bdfed704c4a5e0d8eff600e94191c18c066b23b1228f7e76\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "headless-diagnostic-host-rendezvous-v3-live-v2": (
        b"format=rog5-temporary-boot-consumption-v1\n"
        b"recovery_profile=headless-diagnostic-host-rendezvous-v3-live-v2\n"
        b"candidate=headless-netroot-early-diag-v2\n"
        b"manifest_sha256="
        b"54f534203fe3efbb95713eaef861b1bdb6ae6c56dad2f1b2b77dd09efed36efc\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "headless-diagnostic-host-rendezvous-v3-live-v3": (
        b"format=rog5-temporary-boot-consumption-v1\n"
        b"recovery_profile=headless-diagnostic-host-rendezvous-v3-live-v3\n"
        b"candidate=headless-netroot-early-diag-v2\n"
        b"manifest_sha256="
        b"54f534203fe3efbb95713eaef861b1bdb6ae6c56dad2f1b2b77dd09efed36efc\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "headless-diagnostic-host-rendezvous-v3-live-v4": (
        b"format=rog5-temporary-boot-consumption-v1\n"
        b"recovery_profile=headless-diagnostic-host-rendezvous-v3-live-v4\n"
        b"candidate=headless-netroot-early-diag-v2\n"
        b"manifest_sha256="
        b"54f534203fe3efbb95713eaef861b1bdb6ae6c56dad2f1b2b77dd09efed36efc\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "headless-diagnostic-host-rendezvous-v3-live-v5": (
        b"format=rog5-temporary-boot-consumption-v1\n"
        b"recovery_profile=headless-diagnostic-host-rendezvous-v3-live-v5\n"
        b"candidate=headless-netroot-early-diag-v2\n"
        b"manifest_sha256="
        b"54f534203fe3efbb95713eaef861b1bdb6ae6c56dad2f1b2b77dd09efed36efc\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "headless-diagnostic-host-rendezvous-v3-live-v6": (
        b"format=rog5-temporary-boot-consumption-v1\n"
        b"recovery_profile=headless-diagnostic-host-rendezvous-v3-live-v6\n"
        b"candidate=headless-netroot-early-diag-v2\n"
        b"manifest_sha256="
        b"54f534203fe3efbb95713eaef861b1bdb6ae6c56dad2f1b2b77dd09efed36efc\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "headless-diagnostic-host-rendezvous-v3-live-v7": (
        b"format=rog5-temporary-boot-consumption-v1\n"
        b"recovery_profile=headless-diagnostic-host-rendezvous-v3-live-v7\n"
        b"candidate=headless-netroot-early-diag-v2\n"
        b"manifest_sha256="
        b"54f534203fe3efbb95713eaef861b1bdb6ae6c56dad2f1b2b77dd09efed36efc\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "headless-diagnostic-host-rendezvous-v3-live-v8": (
        b"format=rog5-temporary-boot-consumption-v1\n"
        b"recovery_profile=headless-diagnostic-host-rendezvous-v3-live-v8\n"
        b"candidate=headless-netroot-early-diag-v2\n"
        b"manifest_sha256="
        b"54f534203fe3efbb95713eaef861b1bdb6ae6c56dad2f1b2b77dd09efed36efc\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "headless-diagnostic-host-rendezvous-v3-live-v9": (
        b"format=rog5-temporary-boot-consumption-v1\n"
        b"recovery_profile=headless-diagnostic-host-rendezvous-v3-live-v9\n"
        b"candidate=headless-netroot-early-diag-v2\n"
        b"manifest_sha256="
        b"54f534203fe3efbb95713eaef861b1bdb6ae6c56dad2f1b2b77dd09efed36efc\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "headless-diagnostic-host-rendezvous-v3-live-v10": (
        b"format=rog5-temporary-boot-consumption-v1\n"
        b"recovery_profile=headless-diagnostic-host-rendezvous-v3-live-v10\n"
        b"candidate=headless-netroot-early-diag-v2\n"
        b"manifest_sha256="
        b"54f534203fe3efbb95713eaef861b1bdb6ae6c56dad2f1b2b77dd09efed36efc\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "retention-host-rendezvous-v3-execution-v1": (
        b"format=rog5-retention-boot-consumption-v1\n"
        b"retention_profile=host-rendezvous-v3-observer-v1\n"
        b"cycle_sha256="
        b"d8a3a085d2dfb474728d16cdf568547e529f026239a37a40881183c04ed8a078\n"
        b"claim_role=execution\n"
        b"recovery_profile=retention-host-rendezvous-v3-execution-v1\n"
        b"recovery_sha256="
        b"cba4e6e858c46a431eaa96a72af65e72ba601fa3169a63aad07864cc5122370d\n"
        b"peer_recovery_sha256="
        b"3c9b282090691b169cf96b6e6b8c458d8b592d1d1420138ef0d327cb2b9ae73b\n"
        b"candidate=headless-netroot-early-diag-v2\n"
        b"manifest_sha256="
        b"54f534203fe3efbb95713eaef861b1bdb6ae6c56dad2f1b2b77dd09efed36efc\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "retention-host-rendezvous-v3-observer-v1": (
        b"format=rog5-retention-boot-consumption-v1\n"
        b"retention_profile=host-rendezvous-v3-observer-v1\n"
        b"cycle_sha256="
        b"d8a3a085d2dfb474728d16cdf568547e529f026239a37a40881183c04ed8a078\n"
        b"claim_role=observer\n"
        b"recovery_profile=retention-host-rendezvous-v3-observer-v1\n"
        b"recovery_sha256="
        b"3c9b282090691b169cf96b6e6b8c458d8b592d1d1420138ef0d327cb2b9ae73b\n"
        b"peer_recovery_sha256="
        b"cba4e6e858c46a431eaa96a72af65e72ba601fa3169a63aad07864cc5122370d\n"
        b"candidate=headless-netroot-early-diag-v2\n"
        b"manifest_sha256="
        b"54f534203fe3efbb95713eaef861b1bdb6ae6c56dad2f1b2b77dd09efed36efc\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "retention-host-rendezvous-v3-observer-v2": (
        b"format=rog5-temporary-boot-consumption-v1\n"
        b"recovery_profile=retention-host-rendezvous-v3-observer-v2\n"
        b"candidate=headless-netroot-early-diag-v2\n"
        b"manifest_sha256="
        b"54f534203fe3efbb95713eaef861b1bdb6ae6c56dad2f1b2b77dd09efed36efc\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "retention-host-rendezvous-v11-mainline-udc-execution-v2": (
        b"format=rog5-retention-boot-consumption-v1\n"
        b"retention_profile=host-rendezvous-v11-mainline-udc-observer-v2\n"
        b"cycle_sha256="
        b"c8f21939d83777ed7cc56782441f1a2f35261dd3746b9aa41d07ce5e1f99e405\n"
        b"claim_role=execution\n"
        b"recovery_profile="
        b"retention-host-rendezvous-v11-mainline-udc-execution-v2\n"
        b"recovery_sha256="
        b"2fa17df6ac83daa767bbe35220ff48062c43cdbc6f3945e7c2d0018608130ffb\n"
        b"peer_recovery_sha256="
        b"c416e39445495bb99a8da50da6e5f59d8297779b69f5eada37983f12c735a47e\n"
        b"candidate=headless-netroot-early-diag-v2\n"
        b"manifest_sha256="
        b"ddccf8025190097219f5a7bd8ef32f2b8ad9feed024ae00ecd07e0f446520034\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "retention-host-rendezvous-v11-mainline-udc-observer-v2": (
        b"format=rog5-retention-boot-consumption-v1\n"
        b"retention_profile=host-rendezvous-v11-mainline-udc-observer-v2\n"
        b"cycle_sha256="
        b"c8f21939d83777ed7cc56782441f1a2f35261dd3746b9aa41d07ce5e1f99e405\n"
        b"claim_role=observer\n"
        b"recovery_profile="
        b"retention-host-rendezvous-v11-mainline-udc-observer-v2\n"
        b"recovery_sha256="
        b"c416e39445495bb99a8da50da6e5f59d8297779b69f5eada37983f12c735a47e\n"
        b"peer_recovery_sha256="
        b"2fa17df6ac83daa767bbe35220ff48062c43cdbc6f3945e7c2d0018608130ffb\n"
        b"candidate=headless-netroot-early-diag-v2\n"
        b"manifest_sha256="
        b"ddccf8025190097219f5a7bd8ef32f2b8ad9feed024ae00ecd07e0f446520034\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "retention-host-rendezvous-v12-nfs-xattr-execution-v1": (
        b"format=rog5-retention-boot-consumption-v1\n"
        b"retention_profile=host-rendezvous-v12-nfs-xattr-observer-v1\n"
        b"cycle_sha256="
        b"e8195fccf25370f1fa28f015b66f08786df4b7d3f2e0758363c12e396750e53c\n"
        b"claim_role=execution\n"
        b"recovery_profile="
        b"retention-host-rendezvous-v12-nfs-xattr-execution-v1\n"
        b"recovery_sha256="
        b"f53418cbca5c79c65f63ca24e838ec299eb47ee0d5593286bbbebdb98529bab2\n"
        b"peer_recovery_sha256="
        b"9cf1163d1fce5a0c3c8858c5d961d4ad072e83995e0ffe836e987513fb528f69\n"
        b"candidate=headless-netroot-early-diag-v2\n"
        b"manifest_sha256="
        b"325aa8fb76444b5c01bc517a22ad2483c016837cc1fcb46c203ab5288b916854\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "retention-host-rendezvous-v12-nfs-xattr-observer-v1": (
        b"format=rog5-retention-boot-consumption-v1\n"
        b"retention_profile=host-rendezvous-v12-nfs-xattr-observer-v1\n"
        b"cycle_sha256="
        b"e8195fccf25370f1fa28f015b66f08786df4b7d3f2e0758363c12e396750e53c\n"
        b"claim_role=observer\n"
        b"recovery_profile="
        b"retention-host-rendezvous-v12-nfs-xattr-observer-v1\n"
        b"recovery_sha256="
        b"9cf1163d1fce5a0c3c8858c5d961d4ad072e83995e0ffe836e987513fb528f69\n"
        b"peer_recovery_sha256="
        b"f53418cbca5c79c65f63ca24e838ec299eb47ee0d5593286bbbebdb98529bab2\n"
        b"candidate=headless-netroot-early-diag-v2\n"
        b"manifest_sha256="
        b"325aa8fb76444b5c01bc517a22ad2483c016837cc1fcb46c203ab5288b916854\n"
        b"state=BOOT_CLAIMED\n"
    ),
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


def canonical_claim_anchor() -> Path:
    try:
        return Path(pwd.getpwuid(os.geteuid()).pw_dir).resolve(strict=True)
    except OSError as error:
        raise ClaimError("lifecycle claim anchor is unsafe or absent") from error


def anchor_parent_is_replace_protected(
    parent_fd: int,
    metadata: os.stat_result,
) -> bool:
    if metadata.st_uid == os.geteuid():
        return False
    mode = stat.S_IMODE(metadata.st_mode)
    groups = {os.getegid(), *os.getgroups()}
    if metadata.st_gid in groups:
        mode_protected = not mode & stat.S_IWGRP
    else:
        mode_protected = not mode & stat.S_IWOTH
    return mode_protected and not os.access(
        f"/proc/self/fd/{parent_fd}",
        os.W_OK,
        effective_ids=True,
    )


def open_claim_anchor(anchor: Path) -> tuple[int, int]:
    if not anchor.is_absolute():
        fail("lifecycle claim anchor must be absolute")
    flags = os.O_RDONLY | os.O_CLOEXEC | os.O_DIRECTORY
    nofollow = getattr(os, "O_NOFOLLOW", 0)
    parent = anchor.parent
    if parent == anchor:
        fail("lifecycle claim anchor parent is unsafe")
    try:
        parent_fd = os.open(parent, flags | nofollow)
    except OSError as error:
        raise ClaimError("lifecycle claim anchor parent is unsafe") from error
    try:
        parent_metadata = os.fstat(parent_fd)
        opened_parent = Path(f"/proc/self/fd/{parent_fd}").resolve(strict=True)
        if (
            opened_parent != parent
            or not stat.S_ISDIR(parent_metadata.st_mode)
            or not anchor_parent_is_replace_protected(
                parent_fd,
                parent_metadata,
            )
        ):
            fail("lifecycle claim anchor parent is replaceable")
        anchor_fd = os.open(anchor.name, flags | nofollow, dir_fd=parent_fd)
        metadata = os.fstat(anchor_fd)
        opened_path = Path(f"/proc/self/fd/{anchor_fd}").resolve(strict=True)
        if (
            opened_path != anchor
            or not stat.S_ISDIR(metadata.st_mode)
            or metadata.st_uid != os.geteuid()
            or stat.S_IMODE(metadata.st_mode) & 0o022
        ):
            fail("lifecycle claim anchor is unsafe or absent")
    except (ClaimError, OSError):
        if "anchor_fd" in locals():
            os.close(anchor_fd)
        os.close(parent_fd)
        raise
    return anchor_fd, parent_fd


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


def verify_claim_anchor_path(
    anchor: Path,
    anchor_fd: int,
    parent_fd: int,
) -> None:
    opened = os.fstat(anchor_fd)
    opened_parent = os.fstat(parent_fd)
    try:
        current_parent = os.stat(anchor.parent, follow_symlinks=False)
        current = os.stat(
            anchor.name,
            dir_fd=parent_fd,
            follow_symlinks=False,
        )
    except OSError as error:
        raise ClaimError("lifecycle claim anchor changed during entry") from error
    if (
        current_parent.st_dev != opened_parent.st_dev
        or current_parent.st_ino != opened_parent.st_ino
        or not stat.S_ISDIR(current_parent.st_mode)
        or not anchor_parent_is_replace_protected(parent_fd, current_parent)
        or current.st_dev != opened.st_dev
        or current.st_ino != opened.st_ino
        or not stat.S_ISDIR(current.st_mode)
        or current.st_uid != os.geteuid()
        or stat.S_IMODE(current.st_mode) & 0o022
    ):
        fail("lifecycle claim anchor changed during entry")


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


def existing_guard_is_exact(
    guard_name: str,
    anchor_fd: int,
    expected: bytes,
) -> bool:
    flags = os.O_RDONLY | os.O_CLOEXEC
    nofollow = getattr(os, "O_NOFOLLOW", 0)
    try:
        guard_fd = os.open(guard_name, flags | nofollow, dir_fd=anchor_fd)
    except FileNotFoundError:
        return False
    except OSError as error:
        raise ClaimError("global BOOT_CLAIMED guard is unsafe") from error
    try:
        opened = os.fstat(guard_fd)
        named = os.stat(guard_name, dir_fd=anchor_fd, follow_symlinks=False)
        content = os.read(guard_fd, len(expected) + 1)
        if (
            not stat.S_ISREG(opened.st_mode)
            or opened.st_uid != os.geteuid()
            or stat.S_IMODE(opened.st_mode) != 0o600
            or opened.st_nlink != 1
            or named.st_dev != opened.st_dev
            or named.st_ino != opened.st_ino
            or content != expected
            or os.read(guard_fd, 1)
        ):
            fail("global BOOT_CLAIMED guard is unsafe")
    finally:
        os.close(guard_fd)
    return True


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


def verify_entered_file(
    name: str,
    directory_fd: int,
    expected: bytes,
    label: str,
) -> None:
    flags = os.O_RDONLY | os.O_CLOEXEC
    flags |= getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(name, flags, dir_fd=directory_fd)
    except OSError as error:
        raise ClaimError(f"{label} is unsafe or absent") from error
    try:
        opened = os.fstat(descriptor)
        named = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
        content = os.read(descriptor, len(expected) + 1)
        if (
            not stat.S_ISREG(opened.st_mode)
            or opened.st_uid != os.geteuid()
            or stat.S_IMODE(opened.st_mode) != 0o600
            or opened.st_nlink != 1
            or named.st_dev != opened.st_dev
            or named.st_ino != opened.st_ino
            or content != expected
            or os.read(descriptor, 1)
        ):
            fail(f"{label} is not exact")
    finally:
        os.close(descriptor)


def verify_entered(profile: str, root: Path | None = None) -> None:
    expected = expected_record(profile)
    record_name = f"{profile}.record"
    entered_name = f"{record_name}.entered"
    if root is None:
        root = canonical_claim_root()
        anchor = canonical_claim_anchor()
    else:
        anchor = root.parent
    guard_name = f".rog5-temporary-boot-consumption.{profile}.entered"
    anchor_fd, anchor_parent_fd = open_claim_anchor(anchor)
    try:
        directory_fd = open_claim_root(root)
    except Exception:
        os.close(anchor_fd)
        os.close(anchor_parent_fd)
        raise
    try:
        try:
            os.stat(record_name, dir_fd=directory_fd, follow_symlinks=False)
        except FileNotFoundError:
            pass
        except OSError as error:
            raise ClaimError("source BOOT_CLAIMED record is unsafe") from error
        else:
            fail("source BOOT_CLAIMED record still exists")
        verify_entered_file(
            entered_name,
            directory_fd,
            expected,
            "entered BOOT_CLAIMED record",
        )
        if not existing_guard_is_exact(guard_name, anchor_fd, expected):
            fail("global BOOT_CLAIMED guard is absent")
        verify_claim_root_path(root, directory_fd)
        verify_claim_anchor_path(anchor, anchor_fd, anchor_parent_fd)
    finally:
        os.close(directory_fd)
        os.close(anchor_fd)
        os.close(anchor_parent_fd)


def consume(profile: str, root: Path | None = None) -> None:
    expected = expected_record(profile)
    record_name = f"{profile}.record"
    entered_name = f"{record_name}.entered"
    if root is None:
        root = canonical_claim_root()
        anchor = canonical_claim_anchor()
    else:
        anchor = root.parent
    guard_name = f".rog5-temporary-boot-consumption.{profile}.entered"
    anchor_fd, anchor_parent_fd = open_claim_anchor(anchor)
    try:
        directory_fd = open_claim_root(root)
    except Exception:
        os.close(anchor_fd)
        os.close(anchor_parent_fd)
        raise
    flags = os.O_RDONLY | os.O_CLOEXEC
    nofollow = getattr(os, "O_NOFOLLOW", 0)
    source_fd = -1
    entered_fd = -1
    guard_fd = -1
    try:
        if existing_guard_is_exact(guard_name, anchor_fd, expected):
            fail("durable BOOT_CLAIMED record is already entered")

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
        verify_claim_root_path(root, directory_fd)
        verify_claim_anchor_path(anchor, anchor_fd, anchor_parent_fd)
        guard_fd = create_entered_record(
            guard_name,
            anchor_fd,
            expected,
        )
        os.fsync(anchor_fd)
        verify_claim_anchor_path(anchor, anchor_fd, anchor_parent_fd)
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
        verify_claim_anchor_path(anchor, anchor_fd, anchor_parent_fd)
    finally:
        if entered_fd >= 0:
            os.close(entered_fd)
        if guard_fd >= 0:
            os.close(guard_fd)
        if source_fd >= 0:
            os.close(source_fd)
        os.close(directory_fd)
        os.close(anchor_fd)
        os.close(anchor_parent_fd)


def main() -> int:
    if len(sys.argv) == 2:
        profile = sys.argv[1]
        consume(profile)
        print(f"PASS exact durable BOOT_CLAIMED record entered: {profile}")
        return 0
    if len(sys.argv) == 3 and sys.argv[1] == "--verify-entered":
        profile = sys.argv[2]
        verify_entered(profile)
        print(f"PASS exact durable BOOT_CLAIMED record verified: {profile}")
        return 0
    fail(
        "exact-record claim consumer requires a repository-owned profile "
        "or --verify-entered PROFILE"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ClaimError, OSError, ValueError) as error:
        print(f"FAIL {error}", file=sys.stderr)
        raise SystemExit(1)
