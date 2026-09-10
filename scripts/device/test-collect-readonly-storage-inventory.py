#!/usr/bin/env python3
"""Focused tests for the read-only GPT parser and collector boundary."""

from __future__ import annotations

import ast
import binascii
import importlib.util
from pathlib import Path
import struct
import sys
import tempfile
import unittest
import uuid


REPO = Path(__file__).resolve().parents[2]
SOURCE = REPO / "scripts/device/collect-readonly-storage-inventory.py"
SPEC = importlib.util.spec_from_file_location("rog5_storage_inventory", SOURCE)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("cannot load storage inventory module")
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class StorageInventoryTest(unittest.TestCase):
    def synthetic_gpt(self, path: Path, *, corrupt_primary: bool = False) -> None:
        logical = 4096
        blocks = 128
        entry_count = 128
        entry_size = 128
        entries = bytearray(entry_count * entry_size)
        type_guid = uuid.UUID("0fc63daf-8483-4772-8e79-3d69d8477de4")
        unique_guid = uuid.UUID("11111111-2222-3333-4444-555555555555")
        struct.pack_into(
            "<16s16sQQQ",
            entries,
            0,
            type_guid.bytes_le,
            unique_guid.bytes_le,
            16,
            47,
            0,
        )
        name = "userdata".encode("utf-16-le")
        entries[56 : 56 + len(name)] = name
        entries_crc = binascii.crc32(entries) & 0xFFFFFFFF
        disk_guid = uuid.UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")

        def header(current: int, backup: int, entries_lba: int) -> bytes:
            raw = bytearray(logical)
            struct.pack_into(
                "<8sIIIIQQQQ16sQIII",
                raw,
                0,
                b"EFI PART",
                0x00010000,
                92,
                0,
                0,
                current,
                backup,
                8,
                119,
                disk_guid.bytes_le,
                entries_lba,
                entry_count,
                entry_size,
                entries_crc,
            )
            crc = binascii.crc32(raw[:92]) & 0xFFFFFFFF
            struct.pack_into("<I", raw, 16, crc)
            return bytes(raw)

        image = bytearray(logical * blocks)
        image[logical : 2 * logical] = header(1, blocks - 1, 2)
        image[2 * logical : 2 * logical + len(entries)] = entries
        backup_entries_lba = blocks - 1 - (len(entries) // logical)
        start = backup_entries_lba * logical
        image[start : start + len(entries)] = entries
        image[(blocks - 1) * logical : blocks * logical] = header(
            blocks - 1, 1, backup_entries_lba
        )
        if corrupt_primary:
            image[logical + 56] ^= 0x01
        path.write_bytes(image)

    def test_primary_backup_and_partition_geometry(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            image = Path(temporary) / "disk.img"
            self.synthetic_gpt(image)
            parsed = MODULE.parse_gpt(image, 4096, image.stat().st_size)
        self.assertTrue(parsed["primary"]["header_crc32_valid"])
        self.assertTrue(parsed["backup"]["header_crc32_valid"])
        self.assertTrue(parsed["primary_entries_crc32_valid"])
        self.assertTrue(parsed["primary_backup_crosscheck"])
        self.assertEqual(len(parsed["partitions"]), 1)
        partition = parsed["partitions"][0]
        self.assertEqual(partition["name"], "userdata")
        self.assertEqual(partition["number"], 1)
        self.assertEqual(partition["offset_bytes"], 16 * 4096)
        self.assertEqual(partition["size_bytes"], 32 * 4096)

    def test_corrupt_header_is_reported_not_hidden(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            image = Path(temporary) / "disk.img"
            self.synthetic_gpt(image, corrupt_primary=True)
            parsed = MODULE.parse_gpt(image, 4096, image.stat().st_size)
        self.assertFalse(parsed["primary"]["header_crc32_valid"])
        self.assertTrue(parsed["backup"]["header_crc32_valid"])

    def test_blkid_export_and_busybox_dialects(self) -> None:
        self.assertEqual(
            MODULE.parse_blkid_output(
                'DEVNAME=/dev/sda23\nLABEL=rog5-linux\nTYPE=ext4\n'
            ),
            {
                "DEVNAME": "/dev/sda23",
                "LABEL": "rog5-linux",
                "TYPE": "ext4",
            },
        )
        self.assertEqual(
            MODULE.parse_blkid_output(
                '/dev/sda23: LABEL="rog5-linux" UUID="15b5" TYPE="ext4"\n'
            ),
            {"LABEL": "rog5-linux", "UUID": "15b5", "TYPE": "ext4"},
        )

    def test_source_opens_devices_read_only_and_disables_blkid_cache(self) -> None:
        source = SOURCE.read_text(encoding="utf-8")
        tree = ast.parse(source)
        self.assertIn("os.O_RDONLY | os.O_CLOEXEC", source)
        self.assertNotIn("os.O_WRONLY", source)
        self.assertNotIn("os.O_RDWR", source)
        self.assertIn('["blkid", "-p", "-c", "/dev/null"', source)
        forbidden = {"dd", "mount", "umount", "mkfs", "sgdisk", "parted", "fdisk"}
        calls = {
            node.func.id
            for node in ast.walk(tree)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
        }
        self.assertTrue(forbidden.isdisjoint(calls))


if __name__ == "__main__":
    unittest.main(verbosity=2)
