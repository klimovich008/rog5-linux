#!/usr/bin/env python3
"""Focused tests for fixed GPT-region construction."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import struct
import sys
import unittest
import uuid
import zlib


SOURCE = Path(__file__).with_name("build-storage-layout-gpt-regions.py")
SPEC = importlib.util.spec_from_file_location("rog5_gpt_regions", SOURCE)
assert SPEC is not None and SPEC.loader is not None
REGIONS = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = REGIONS
SPEC.loader.exec_module(REGIONS)


def partition(type_guid: uuid.UUID, unique_guid: uuid.UUID, first: int, last: int, name: str) -> bytes:
    data = bytearray(128)
    struct.pack_into("<16s16sQQQ", data, 0, type_guid.bytes_le, unique_guid.bytes_le, first, last, 0)
    encoded = name.encode("utf-16le")
    data[56 : 56 + len(encoded)] = encoded
    return bytes(data)


def header(current: int, backup: int, table: int, entries: bytes) -> bytes:
    data = bytearray(512)
    struct.pack_into(
        "<8sIIIIQQQQ16sQIII",
        data,
        0,
        b"EFI PART",
        0x00010000,
        92,
        0,
        0,
        current,
        backup,
        6,
        61865978,
        REGIONS.DISK_GUID.bytes_le,
        table,
        32,
        128,
        zlib.crc32(entries) & 0xFFFFFFFF,
    )
    struct.pack_into("<I", data, 16, zlib.crc32(data[:92]) & 0xFFFFFFFF)
    return bytes(data)


def fixture() -> tuple[bytes, bytes, bytes]:
    old_entries = bytearray(REGIONS.SECTOR)
    old_entries[22 * 128 : 23 * 128] = partition(
        REGIONS.USERDATA_TYPE,
        REGIONS.USERDATA_GUID,
        2352680,
        61865978,
        "userdata",
    )
    new_entries = bytearray(old_entries)
    new_entries[22 * 128 : 23 * 128] = partition(
        REGIONS.USERDATA_TYPE,
        REGIONS.USERDATA_GUID,
        2352680,
        53477375,
        "userdata",
    )
    new_entries[23 * 128 : 24 * 128] = partition(
        REGIONS.ROOT_TYPE,
        REGIONS.ROOT_GUID,
        53477376,
        61865978,
        "arch_root_a",
    )
    mbr = bytearray(512)
    mbr[446 + 4] = 0xEE
    struct.pack_into("<II", mbr, 446 + 8, 1, 61865983)
    mbr[510:512] = b"\x55\xaa"

    old_primary = bytearray(b"P" * REGIONS.PRIMARY_SIZE)
    old_primary[:512] = mbr
    old_primary[REGIONS.SECTOR : REGIONS.SECTOR + 512] = header(1, 61865983, 2, old_entries)
    old_primary[2 * REGIONS.SECTOR : 3 * REGIONS.SECTOR] = old_entries
    old_secondary = bytearray(b"S" * REGIONS.SECONDARY_SIZE)
    old_secondary[:REGIONS.SECTOR] = old_entries
    old_secondary[4 * REGIONS.SECTOR : 4 * REGIONS.SECTOR + 512] = header(
        61865983, 1, 61865979, old_entries
    )
    backup = bytes(mbr) + header(1, 61865983, 2, new_entries) + header(
        61865983, 1, 61865979, new_entries
    ) + bytes(new_entries)
    return bytes(old_primary), bytes(old_secondary), backup


class GptRegionTest(unittest.TestCase):
    def test_build_preserves_gaps_and_changes_only_exact_gpt_metadata(self) -> None:
        old_primary, old_secondary, backup = fixture()
        primary, secondary = REGIONS.build_regions(old_primary, old_secondary, backup)
        self.assertEqual(primary[512:REGIONS.SECTOR], old_primary[512:REGIONS.SECTOR])
        self.assertEqual(primary[REGIONS.SECTOR + 512 : 2 * REGIONS.SECTOR], old_primary[REGIONS.SECTOR + 512 : 2 * REGIONS.SECTOR])
        self.assertEqual(primary[3 * REGIONS.SECTOR :], old_primary[3 * REGIONS.SECTOR :])
        self.assertEqual(secondary[REGIONS.SECTOR : 4 * REGIONS.SECTOR], old_secondary[REGIONS.SECTOR : 4 * REGIONS.SECTOR])
        self.assertEqual(secondary[4 * REGIONS.SECTOR + 512 :], old_secondary[4 * REGIONS.SECTOR + 512 :])
        entries = primary[2 * REGIONS.SECTOR : 3 * REGIONS.SECTOR]
        REGIONS.expect_entry(entries, 23, REGIONS.USERDATA_TYPE, REGIONS.USERDATA_GUID, 2352680, 53477375, "userdata")
        REGIONS.expect_entry(entries, 24, REGIONS.ROOT_TYPE, REGIONS.ROOT_GUID, 53477376, 61865978, "arch_root_a")

    def test_crc_protected_entries_and_mbr_mutations_fail(self) -> None:
        old_primary, old_secondary, backup = fixture()
        for offset in (510, 512 + 16, 1536):
            hostile = bytearray(backup)
            hostile[offset] ^= 1
            with self.assertRaises(RuntimeError):
                REGIONS.build_regions(old_primary, old_secondary, bytes(hostile))


if __name__ == "__main__":
    unittest.main()
