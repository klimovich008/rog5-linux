#!/usr/bin/env python3
"""Focused selection tests for the private read-only backup runner."""

from __future__ import annotations

import importlib.util
import hashlib
import os
from pathlib import Path
import sys
import tempfile
import unittest


REPO = Path(__file__).resolve().parents[2]
SOURCE = REPO / "scripts/host/backup-readonly-storage-inventory.py"
SPEC = importlib.util.spec_from_file_location("rog5_storage_backup", SOURCE)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("cannot load storage backup module")
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class StorageBackupTest(unittest.TestCase):
    def inventory(self):
        partitions = []
        number = 1
        for disk_index in range(7):
            count = 23 if disk_index == 0 else 6 if disk_index == 1 else 2
            if disk_index == 4:
                count = 7
            elif disk_index == 5:
                count = 3
            elif disk_index == 6:
                count = 66
            entries = []
            for local in range(1, count + 1):
                label = f"p{number}"
                if number == 19:
                    label = "super"
                elif number == 23:
                    label = "userdata"
                node = f"sd{chr(97 + disk_index)}{local}"
                entries.append(
                    {
                        "name": label,
                        "unique_guid": f"{number:08x}-0000-0000-0000-{number:012x}",
                        "size_bytes": 4096,
                        "sysfs_gpt_geometry_match": True,
                        "sysfs": {
                            "name": node,
                            "size_512_sectors": 8,
                            "start_512_sectors": number * 8,
                        },
                    }
                )
                number += 1
            partitions.append(
                {
                    "name": f"sd{chr(97 + disk_index)}",
                    "size_512_sectors": 2048,
                    "size_bytes": 1048576,
                    "logical_block_bytes": 4096,
                    "gpt": {
                        "primary_entries_crc32_valid": True,
                        "primary_backup_crosscheck": True,
                        "primary": {
                            "header_crc32_valid": True,
                            "disk_guid": f"{disk_index:08x}-0000-0000-0000-000000000001",
                            "entries_lba": 2,
                            "table_bytes": 16384,
                        },
                        "backup": {
                            "header_crc32_valid": True,
                            "entries_lba": 251,
                        },
                        "partitions": entries,
                    },
                }
            )
        return {"disks": partitions}

    def test_plan_backs_up_every_partition_except_super_and_userdata(self):
        plan, total = MODULE.backup_plan(self.inventory())
        self.assertEqual(len(plan), 107)
        self.assertEqual(total, 107 * 4096)
        labels = {item["label"] for item in plan}
        self.assertNotIn("super", labels)
        self.assertNotIn("userdata", labels)
        gpt, gpt_total = MODULE.gpt_backup_plan(self.inventory())
        self.assertEqual(len(gpt), 14)
        self.assertEqual(gpt_total, 7 * (24576 + 20480))

    def test_geometry_or_duplicate_label_refuses(self):
        inventory = self.inventory()
        inventory["disks"][0]["gpt"]["partitions"][0][
            "sysfs_gpt_geometry_match"
        ] = False
        with self.assertRaises(MODULE.BackupError):
            MODULE.backup_plan(inventory)
        inventory = self.inventory()
        inventory["disks"][0]["gpt"]["partitions"][1]["name"] = "p1"
        with self.assertRaises(MODULE.BackupError):
            MODULE.backup_plan(inventory)

    def test_source_contains_no_phone_write_or_partition_tool(self):
        source = SOURCE.read_text(encoding="utf-8")
        for token in (
            "fastboot flash",
            "mkfs",
            "mke2fs",
            "sgdisk",
            "parted",
            "fdisk",
            "blockdev --set",
            "/proc/sysrq-trigger",
        ):
            self.assertNotIn(token, source)
        self.assertIn("dd if=/dev/", source)
        self.assertIn('parser.add_argument("--resume"', source)

    def test_resume_accepts_only_an_exact_hash_verified_prefix(self):
        plan, _ = MODULE.backup_plan(self.inventory())
        gpt_plan, _ = MODULE.gpt_backup_plan(self.inventory())
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "backup"
            output.mkdir(mode=0o700)
            partitions = output / "partitions"
            partitions.mkdir(mode=0o700)
            gpt = output / "gpt"
            gpt.mkdir(mode=0o700)
            partition_manifest = output / "SHA256SUMS.tsv"
            gpt_manifest = output / "GPT-SHA256SUMS.tsv"
            partition_lines = [MODULE.PARTITION_MANIFEST_HEADER]
            for index, record in enumerate(plan[:3], 1):
                filename = f"{index:03d}-{record['label']}.img"
                payload = bytes([index]) * int(record["size_bytes"])
                path = partitions / filename
                path.write_bytes(payload)
                os.chmod(path, 0o600)
                digest = hashlib.sha256(payload).hexdigest()
                partition_lines.append(
                    "\t".join(
                        (
                            f"partitions/{filename}",
                            str(record["label"]),
                            str(record["node"]),
                            str(record["size_bytes"]),
                            str(record["unique_guid"]),
                            digest,
                            digest,
                        )
                    )
                )
            partition_manifest.write_text("\n".join(partition_lines) + "\n")
            os.chmod(partition_manifest, 0o600)
            gpt_lines = [MODULE.GPT_MANIFEST_HEADER]
            for record in gpt_plan[:2]:
                filename = f"{record['disk']}-{record['role']}.bin"
                payload = b"G" * int(record["size_bytes"])
                path = gpt / filename
                path.write_bytes(payload)
                os.chmod(path, 0o600)
                digest = hashlib.sha256(payload).hexdigest()
                gpt_lines.append(
                    "\t".join(
                        (
                            f"gpt/{filename}",
                            str(record["disk"]),
                            str(record["role"]),
                            str(record["offset_bytes"]),
                            str(record["size_bytes"]),
                            str(record["disk_guid"]),
                            digest,
                            digest,
                        )
                    )
                )
            gpt_manifest.write_text("\n".join(gpt_lines) + "\n")
            os.chmod(gpt_manifest, 0o600)
            self.assertEqual(
                MODULE.verify_partition_resume(
                    output, partitions, partition_manifest, plan
                ),
                3,
            )
            self.assertEqual(
                MODULE.verify_gpt_resume(output, gpt, gpt_manifest, gpt_plan), 2
            )
            (partitions / "orphan.partial").write_bytes(b"")
            os.chmod(partitions / "orphan.partial", 0o600)
            with self.assertRaises(MODULE.BackupError):
                MODULE.verify_partition_resume(
                    output, partitions, partition_manifest, plan
                )
            (partitions / "orphan.partial").unlink()
            first = partitions / f"001-{plan[0]['label']}.img"
            first.write_bytes(b"X" * int(plan[0]["size_bytes"]))
            os.chmod(first, 0o600)
            with self.assertRaises(MODULE.BackupError):
                MODULE.verify_partition_resume(
                    output, partitions, partition_manifest, plan
                )


if __name__ == "__main__":
    unittest.main(verbosity=2)
