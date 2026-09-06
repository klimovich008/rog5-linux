#!/usr/bin/env python3
"""Verify a private ROG5 storage backup and rehearse GPT restoration offline."""

from __future__ import annotations

import argparse
import binascii
import importlib.util
import os
from pathlib import Path
import stat
import sys
import tempfile


REPO = Path(__file__).resolve().parents[2]


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


BACKUP = load_module(
    "rog5_storage_backup_verify_dependency",
    REPO / "scripts/host/backup-readonly-storage-inventory.py",
)
INVENTORY = load_module(
    "rog5_storage_inventory_verify_dependency",
    REPO / "scripts/device/collect-readonly-storage-inventory.py",
)


def write_range(fd: int, source: Path, offset: int) -> None:
    position = offset
    with source.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            written = os.pwrite(fd, chunk, position)
            if written != len(chunk):
                raise BACKUP.BackupError("short write in host-only GPT rehearsal")
            position += written


def partition_projection(partitions: list[dict[str, object]]) -> list[dict[str, object]]:
    keys = (
        "number",
        "type_guid",
        "unique_guid",
        "first_lba",
        "last_lba",
        "size_lba",
        "offset_bytes",
        "size_bytes",
        "attributes",
        "name",
    )
    return [{key: entry[key] for key in keys} for entry in partitions]


def rehearse_gpt_restore(
    inventory: dict[str, object], output: Path, plan: list[dict[str, object]]
) -> None:
    disks = inventory["disks"]
    assert isinstance(disks, list)
    by_disk: dict[str, list[dict[str, object]]] = {}
    for record in plan:
        by_disk.setdefault(str(record["disk"]), []).append(record)
    with tempfile.TemporaryDirectory(prefix="rog5-gpt-rehearsal-", dir=output.parent) as tmp:
        temporary = Path(tmp)
        for disk in disks:
            assert isinstance(disk, dict)
            name = str(disk["name"])
            records = by_disk.get(name, [])
            if len(records) != 2 or {str(item["role"]) for item in records} != {
                "primary",
                "backup",
            }:
                raise BACKUP.BackupError(f"GPT rehearsal plan is incomplete for {name}")
            image = temporary / f"{name}.sparse.img"
            fd = os.open(
                image,
                os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC,
                0o600,
            )
            try:
                os.ftruncate(fd, int(disk["size_bytes"]))
                for record in records:
                    source = output / "gpt" / f"{name}-{record['role']}.bin"
                    write_range(fd, source, int(record["offset_bytes"]))
                os.fsync(fd)
            finally:
                os.close(fd)
            metadata = image.stat()
            restored_bytes = sum(int(item["size_bytes"]) for item in records)
            if stat.S_IMODE(metadata.st_mode) != 0o600:
                raise BACKUP.BackupError("GPT rehearsal image is not private")
            if metadata.st_blocks * 512 > restored_bytes + 1024 * 1024:
                raise BACKUP.BackupError("GPT rehearsal image was not created sparsely")
            logical = int(disk["logical_block_bytes"])
            parsed = INVENTORY.parse_gpt(image, logical, int(disk["size_bytes"]))
            expected = disk["gpt"]
            assert isinstance(expected, dict)
            for key in (
                "primary",
                "backup",
                "primary_entries_crc32_valid",
                "primary_backup_crosscheck",
            ):
                if parsed[key] != expected[key]:
                    raise BACKUP.BackupError(
                        f"restored GPT {key} differs from inventory for {name}"
                    )
            expected_partitions = expected["partitions"]
            assert isinstance(expected_partitions, list)
            if parsed["partitions"] != partition_projection(expected_partitions):
                raise BACKUP.BackupError(
                    f"restored GPT partition map differs from inventory for {name}"
                )
            backup = parsed["backup"]
            assert isinstance(backup, dict)
            table_bytes = int(backup["table_bytes"])
            with image.open("rb") as stream:
                stream.seek(int(backup["entries_lba"]) * logical)
                backup_table = stream.read(table_bytes)
            if (
                len(backup_table) != table_bytes
                or binascii.crc32(backup_table) & 0xFFFFFFFF
                != int(str(backup["entries_crc32"]), 16)
            ):
                raise BACKUP.BackupError(
                    f"restored backup GPT entry table CRC differs for {name}"
                )
            print(
                f"GPT_RESTORE_REHEARSAL_PASS disk={name} "
                f"partitions={len(parsed['partitions'])}"
            )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--inventory", type=Path, required=True)
    parser.add_argument("--backup", type=Path, required=True)
    args = parser.parse_args()
    try:
        inventory = BACKUP.load_inventory(args.inventory)
        output = BACKUP.canonical_private_directory(args.backup, "backup output")
        partitions = BACKUP.canonical_private_directory(
            output / "partitions", "partition backup directory"
        )
        gpt = BACKUP.canonical_private_directory(output / "gpt", "GPT backup directory")
        plan, partition_bytes = BACKUP.backup_plan(inventory)
        gpt_plan, gpt_bytes = BACKUP.gpt_backup_plan(inventory)
        gpt_count = BACKUP.verify_gpt_resume(
            output, gpt, output / "GPT-SHA256SUMS.tsv", gpt_plan
        )
        partition_count = BACKUP.verify_partition_resume(
            output, partitions, output / "SHA256SUMS.tsv", plan
        )
        if gpt_count != len(gpt_plan) or partition_count != len(plan):
            raise BACKUP.BackupError("backup is only a prefix, not complete")
        rehearse_gpt_restore(inventory, output, gpt_plan)
        print(
            f"PASS verified backup and offline GPT restoration rehearsal "
            f"gpt_ranges={gpt_count} partitions={partition_count} "
            f"bytes={partition_bytes + gpt_bytes}"
        )
        return 0
    except (BACKUP.BackupError, OSError, ValueError, KeyError) as error:
        print(f"FAIL backup verification: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
