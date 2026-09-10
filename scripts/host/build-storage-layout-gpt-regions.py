#!/usr/bin/env python3
"""Build fixed 4 KiB GPT write regions without touching a block device."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
import stat
import struct
import sys
import uuid
import zlib


SECTOR = 4096
PRIMARY_SIZE = 6 * SECTOR
SECONDARY_SIZE = 5 * SECTOR
BACKUP_SIZE = 512 * 3 + SECTOR
DISK_GUID = uuid.UUID("bec01849-9a65-de9d-ff59-daecada50043")
USERDATA_TYPE = uuid.UUID("1b81e7e6-f50d-419b-a739-2aeef8da3335")
USERDATA_GUID = uuid.UUID("8d82ef11-4d42-60e9-24e8-4d6ebf20491b")
ROOT_TYPE = uuid.UUID("0fc63daf-8483-4772-8e79-3d69d8477de4")
ROOT_GUID = uuid.UUID("60f49e17-bdc6-46bf-8d47-8a24907024c9")


def fail(message: str) -> None:
    raise RuntimeError(message)


def read_exact(path: Path, size: int, label: str) -> bytes:
    metadata = path.lstat()
    if (
        not stat.S_ISREG(metadata.st_mode)
        or path.is_symlink()
        or metadata.st_uid != os.geteuid()
        or metadata.st_nlink != 1
        or metadata.st_size != size
    ):
        fail(f"{label} metadata is not exact")
    data = path.read_bytes()
    if len(data) != size:
        fail(f"{label} changed while reading")
    return data


def parse_header(header: bytes, entries: bytes, current: int, backup: int, table: int) -> None:
    values = struct.unpack_from("<8sIIIIQQQQ16sQIII", header)
    signature, revision, header_size, header_crc, reserved = values[:5]
    current_lba, backup_lba, first, last, disk_guid = values[5:10]
    table_lba, count, entry_size, entries_crc = values[10:14]
    candidate = bytearray(header[:header_size])
    if len(candidate) != 92:
        fail("GPT header size changed")
    struct.pack_into("<I", candidate, 16, 0)
    if (
        signature != b"EFI PART"
        or revision != 0x00010000
        or reserved != 0
        or current_lba != current
        or backup_lba != backup
        or first != 6
        or last != 61865978
        or uuid.UUID(bytes_le=disk_guid) != DISK_GUID
        or table_lba != table
        or count != 32
        or entry_size != 128
        or zlib.crc32(candidate) & 0xFFFFFFFF != header_crc
        or zlib.crc32(entries) & 0xFFFFFFFF != entries_crc
    ):
        fail("GPT header or entry CRC contract changed")


def entry(entries: bytes, number: int) -> tuple[uuid.UUID | None, uuid.UUID | None, int, int, int, str]:
    data = entries[(number - 1) * 128 : number * 128]
    type_raw, unique_raw, first, last, attributes = struct.unpack_from("<16s16sQQQ", data)
    name = data[56:128].decode("utf-16le").rstrip("\0")
    type_guid = None if type_raw == bytes(16) else uuid.UUID(bytes_le=type_raw)
    unique_guid = None if unique_raw == bytes(16) else uuid.UUID(bytes_le=unique_raw)
    return type_guid, unique_guid, first, last, attributes, name


def expect_entry(
    entries: bytes,
    number: int,
    type_guid: uuid.UUID,
    unique_guid: uuid.UUID,
    first: int,
    last: int,
    name: str,
) -> None:
    if entry(entries, number) != (type_guid, unique_guid, first, last, 0, name):
        fail(f"partition {number} identity changed")


def build_regions(old_primary: bytes, old_secondary: bytes, backup: bytes) -> tuple[bytes, bytes]:
    old_entries = old_primary[2 * SECTOR : 3 * SECTOR]
    old_secondary_entries = old_secondary[:SECTOR]
    old_primary_header = old_primary[SECTOR : SECTOR + 512]
    old_secondary_header = old_secondary[4 * SECTOR : 4 * SECTOR + 512]
    parse_header(old_primary_header, old_entries, 1, 61865983, 2)
    parse_header(old_secondary_header, old_secondary_entries, 61865983, 1, 61865979)
    if old_entries != old_secondary_entries:
        fail("old primary and secondary partition entries differ")
    expect_entry(old_entries, 23, USERDATA_TYPE, USERDATA_GUID, 2352680, 61865978, "userdata")
    if entry(old_entries, 24) != (None, None, 0, 0, 0, ""):
        fail("old partition 24 is not empty")

    new_mbr = backup[:512]
    new_primary_header = backup[512:1024]
    new_secondary_header = backup[1024:1536]
    new_entries = backup[1536:]
    parse_header(new_primary_header, new_entries, 1, 61865983, 2)
    parse_header(new_secondary_header, new_entries, 61865983, 1, 61865979)
    protective = new_mbr[446:462]
    if (
        new_mbr[510:512] != b"\x55\xaa"
        or protective[4] != 0xEE
        or struct.unpack_from("<I", protective, 8)[0] != 1
        or struct.unpack_from("<I", protective, 12)[0] != 61865983
        or new_mbr != old_primary[:512]
        or new_entries[: 22 * 128] != old_entries[: 22 * 128]
    ):
        fail("protective MBR or protected partition entries changed")
    expect_entry(new_entries, 23, USERDATA_TYPE, USERDATA_GUID, 2352680, 53477375, "userdata")
    expect_entry(new_entries, 24, ROOT_TYPE, ROOT_GUID, 53477376, 61865978, "arch_root_a")
    if any(new_entries[24 * 128 :]):
        fail("unexpected partition exists after partition 24")

    primary = bytearray(old_primary)
    primary[:512] = new_mbr
    primary[SECTOR : SECTOR + 512] = new_primary_header
    primary[2 * SECTOR : 3 * SECTOR] = new_entries
    secondary = bytearray(old_secondary)
    secondary[:SECTOR] = new_entries
    secondary[4 * SECTOR : 4 * SECTOR + 512] = new_secondary_header
    return bytes(primary), bytes(secondary)


def write_new(path: Path, data: bytes) -> str:
    parent = path.parent
    metadata = parent.stat()
    if not parent.is_dir() or parent.is_symlink() or metadata.st_uid != os.geteuid() or metadata.st_mode & 0o022:
        fail("output parent is unsafe")
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC, 0o600)
    try:
        view = memoryview(data)
        while view:
            written = os.write(descriptor, view)
            if written < 1:
                fail("output write made no progress")
            view = view[written:]
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    directory = os.open(parent, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)
    return hashlib.sha256(data).hexdigest()


def main(arguments: list[str]) -> int:
    if len(arguments) != 5:
        fail("usage: build-storage-layout-gpt-regions.py OLD_PRIMARY OLD_SECONDARY NEW_GPT_BACKUP OUTPUT_PRIMARY OUTPUT_SECONDARY")
    old_primary = read_exact(Path(arguments[0]), PRIMARY_SIZE, "old primary region")
    old_secondary = read_exact(Path(arguments[1]), SECONDARY_SIZE, "old secondary region")
    backup = read_exact(Path(arguments[2]), BACKUP_SIZE, "new GPT backup")
    primary, secondary = build_regions(old_primary, old_secondary, backup)
    primary_sha = write_new(Path(arguments[3]), primary)
    secondary_sha = write_new(Path(arguments[4]), secondary)
    print(f"primary_size={len(primary)} primary_sha256={primary_sha}")
    print(f"secondary_size={len(secondary)} secondary_sha256={secondary_sha}")
    print("PASS fixed GPT regions preserve all non-GPT bytes and protected entries")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv[1:]))
    except (OSError, RuntimeError, UnicodeError, ValueError, struct.error) as error:
        print(f"FAIL {error}", file=sys.stderr)
        raise SystemExit(1)
