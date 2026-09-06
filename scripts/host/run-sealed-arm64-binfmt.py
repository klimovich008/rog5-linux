#!/usr/bin/env python3
"""Register one hash-pinned, sealed QEMU image in a private binfmt mount."""

from __future__ import annotations

import errno
import fcntl
import hashlib
import os
import stat
import sys


F_ADD_SEALS = getattr(fcntl, "F_ADD_SEALS", 1033)
F_GET_SEALS = getattr(fcntl, "F_GET_SEALS", 1034)
F_SEAL_SEAL = getattr(fcntl, "F_SEAL_SEAL", 0x0001)
F_SEAL_SHRINK = getattr(fcntl, "F_SEAL_SHRINK", 0x0002)
F_SEAL_GROW = getattr(fcntl, "F_SEAL_GROW", 0x0004)
F_SEAL_WRITE = getattr(fcntl, "F_SEAL_WRITE", 0x0008)
REQUIRED_SEALS = F_SEAL_SEAL | F_SEAL_SHRINK | F_SEAL_GROW | F_SEAL_WRITE
MAGIC = bytes.fromhex("7f454c460201010000000000000000000200b700")
MASK = bytes.fromhex("ffffffffffffff00fffffffffffffffffeffffff")


def fail(message: str) -> "NoReturn":
    raise SystemExit(f"FAIL {message}")


def write_all(fd: int, data: bytes) -> None:
    offset = 0
    while offset < len(data):
        written = os.write(fd, data[offset:])
        if written <= 0:
            fail("short write while sealing or registering ARM64 emulator")
        offset += written


def copy_and_seal(path: str, expected_size: int, expected_sha: str) -> int:
    source_flags = os.O_RDONLY | os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        source_flags |= os.O_NOFOLLOW
    try:
        source_fd = os.open(path, source_flags)
    except OSError as error:
        fail(f"could not open qualified ARM64 emulator: {error}")

    sealed_fd = -1
    try:
        before = os.fstat(source_fd)
        if not stat.S_ISREG(before.st_mode):
            fail("qualified ARM64 emulator is not a regular file")
        sealed_fd = os.memfd_create(
            "rog5-qemu-aarch64",
            os.MFD_CLOEXEC | os.MFD_ALLOW_SEALING,
        )
        digest = hashlib.sha256()
        copied = 0
        while True:
            chunk = os.read(source_fd, 1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
            copied += len(chunk)
            write_all(sealed_fd, chunk)
        after = os.fstat(source_fd)
        if (
            before.st_dev != after.st_dev
            or before.st_ino != after.st_ino
            or before.st_size != after.st_size
        ):
            fail("qualified ARM64 emulator changed while it was copied")
        if copied != expected_size or digest.hexdigest() != expected_sha:
            fail("qualified ARM64 emulator bytes changed")

        os.fchmod(sealed_fd, 0o555)
        fcntl.fcntl(sealed_fd, F_ADD_SEALS, REQUIRED_SEALS)
        active_seals = fcntl.fcntl(sealed_fd, F_GET_SEALS)
        if active_seals & REQUIRED_SEALS != REQUIRED_SEALS:
            fail("ARM64 emulator memfd did not acquire every required seal")
        return sealed_fd
    except BaseException:
        if sealed_fd >= 0:
            os.close(sealed_fd)
        raise
    finally:
        os.close(source_fd)


def prove_sealed(fd: int) -> None:
    for mutation in (
        lambda: os.pwrite(fd, b"\0", 0),
        lambda: os.ftruncate(fd, 0),
    ):
        try:
            mutation()
        except OSError as error:
            if error.errno in (errno.EPERM, errno.EBUSY):
                continue
            fail(f"unexpected sealed-memfd mutation error: {error}")
        fail("sealed ARM64 emulator accepted a mutation")


def register(fd: int) -> None:
    status_path = "/proc/sys/fs/binfmt_misc/qemu-aarch64"
    if os.path.lexists(status_path):
        fail("private ARM64 binfmt registration was not initially empty")
    interpreter = f"/proc/self/fd/{fd}"
    escaped_magic = "".join(f"\\x{byte:02x}" for byte in MAGIC)
    escaped_mask = "".join(f"\\x{byte:02x}" for byte in MASK)
    record = (
        f":qemu-aarch64:M::{escaped_magic}:{escaped_mask}:"
        f"{interpreter}:POF\n"
    ).encode("ascii")
    register_fd = os.open(
        "/proc/sys/fs/binfmt_misc/register",
        os.O_WRONLY | os.O_CLOEXEC,
    )
    try:
        write_all(register_fd, record)
    finally:
        os.close(register_fd)
    with open(status_path, encoding="ascii") as status_file:
        status = status_file.read().splitlines()
    if f"interpreter {interpreter}" not in status or "flags: POF" not in status:
        fail("private ARM64 binfmt registration did not pin the sealed memfd")


def main(argv: list[str]) -> int:
    if len(argv) < 5:
        fail(
            "usage: run-sealed-arm64-binfmt.py "
            "QEMU SIZE SHA256 (--self-test | -- COMMAND [ARG...])"
        )
    qemu = argv[1]
    try:
        expected_size = int(argv[2])
    except ValueError:
        fail("invalid expected ARM64 emulator size")
    expected_sha = argv[3]
    if (
        expected_size <= 0
        or len(expected_sha) != 64
        or any(character not in "0123456789abcdef" for character in expected_sha)
    ):
        fail("invalid expected ARM64 emulator identity")

    sealed_fd = copy_and_seal(qemu, expected_size, expected_sha)
    if argv[4:] == ["--self-test"]:
        prove_sealed(sealed_fd)
        os.close(sealed_fd)
        print("PASS exact ARM64 emulator bytes are held in a sealed memfd")
        return 0
    if argv[4] != "--" or len(argv) < 6:
        os.close(sealed_fd)
        fail("missing command for sealed private ARM64 binfmt")

    prove_sealed(sealed_fd)
    register(sealed_fd)
    os.close(sealed_fd)
    os.execvp(argv[5], argv[5:])
    return 127


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
