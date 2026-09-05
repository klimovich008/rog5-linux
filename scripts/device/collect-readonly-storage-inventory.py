#!/usr/bin/env python3
"""Emit a read-only UFS/GPT/filesystem inventory as canonical JSON."""

from __future__ import annotations

import argparse
import binascii
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import shlex
import struct
import subprocess
import sys
import uuid


GPT_HEADER = struct.Struct("<8sIIIIQQQQ16sQIII")
GPT_ENTRY_PREFIX = struct.Struct("<16s16sQQQ")
ZERO_GUID = bytes(16)
MAX_GPT_TABLE_BYTES = 16 * 1024 * 1024


class InventoryError(RuntimeError):
    pass


def read_text(path: Path, *, required: bool = False) -> str | None:
    try:
        return path.read_text(encoding="utf-8", errors="strict").strip()
    except FileNotFoundError:
        if required:
            raise InventoryError(f"required path is absent: {path}")
        return None
    except OSError as error:
        if required:
            raise InventoryError(f"cannot read required path: {path}") from error
        return None


def read_at(fd: int, offset: int, size: int) -> bytes:
    data = os.pread(fd, size, offset)
    if len(data) != size:
        raise InventoryError(
            f"short block read at offset {offset}: expected {size}, got {len(data)}"
        )
    return data


def parse_gpt_header(raw: bytes, logical_block_bytes: int) -> dict[str, object]:
    if len(raw) != logical_block_bytes:
        raise InventoryError("GPT header block has the wrong size")
    values = GPT_HEADER.unpack_from(raw)
    (
        signature,
        revision,
        header_size,
        stored_crc32,
        reserved,
        current_lba,
        backup_lba,
        first_usable_lba,
        last_usable_lba,
        disk_guid,
        entries_lba,
        entry_count,
        entry_size,
        entries_crc32,
    ) = values
    if signature != b"EFI PART":
        raise InventoryError("GPT signature is absent")
    if not GPT_HEADER.size <= header_size <= logical_block_bytes:
        raise InventoryError("GPT header size is invalid")
    if reserved != 0:
        raise InventoryError("GPT reserved field is nonzero")
    if not 1 <= entry_count <= 4096:
        raise InventoryError("GPT entry count is outside the reviewed bound")
    if entry_size < 128 or entry_size > 4096 or entry_size % 8:
        raise InventoryError("GPT entry size is outside the reviewed bound")
    table_bytes = entry_count * entry_size
    if table_bytes > MAX_GPT_TABLE_BYTES:
        raise InventoryError("GPT entry table exceeds the reviewed bound")
    checked = bytearray(raw[:header_size])
    checked[16:20] = b"\0\0\0\0"
    actual_crc32 = binascii.crc32(checked) & 0xFFFFFFFF
    return {
        "revision": f"0x{revision:08x}",
        "header_size": header_size,
        "header_crc32": f"{stored_crc32:08x}",
        "header_crc32_valid": actual_crc32 == stored_crc32,
        "current_lba": current_lba,
        "backup_lba": backup_lba,
        "first_usable_lba": first_usable_lba,
        "last_usable_lba": last_usable_lba,
        "disk_guid": str(uuid.UUID(bytes_le=disk_guid)),
        "entries_lba": entries_lba,
        "entry_count": entry_count,
        "entry_size": entry_size,
        "entries_crc32": f"{entries_crc32:08x}",
        "table_bytes": table_bytes,
    }


def parse_gpt(device: Path, logical_block_bytes: int, size_bytes: int) -> dict[str, object]:
    flags = os.O_RDONLY | os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    fd = os.open(device, flags)
    try:
        primary_raw = read_at(fd, logical_block_bytes, logical_block_bytes)
        primary = parse_gpt_header(primary_raw, logical_block_bytes)
        table_offset = int(primary["entries_lba"]) * logical_block_bytes
        table = read_at(fd, table_offset, int(primary["table_bytes"]))
        table_crc32 = binascii.crc32(table) & 0xFFFFFFFF
        partitions = []
        entry_size = int(primary["entry_size"])
        for number in range(1, int(primary["entry_count"]) + 1):
            entry = table[(number - 1) * entry_size : number * entry_size]
            type_guid, unique_guid, first_lba, last_lba, attributes = (
                GPT_ENTRY_PREFIX.unpack_from(entry)
            )
            if type_guid == ZERO_GUID:
                continue
            if last_lba < first_lba:
                raise InventoryError(f"GPT partition {number} has reversed bounds")
            name = entry[56:entry_size].decode("utf-16-le", errors="strict")
            name = name.split("\0", 1)[0]
            partitions.append(
                {
                    "number": number,
                    "type_guid": str(uuid.UUID(bytes_le=type_guid)),
                    "unique_guid": str(uuid.UUID(bytes_le=unique_guid)),
                    "first_lba": first_lba,
                    "last_lba": last_lba,
                    "size_lba": last_lba - first_lba + 1,
                    "offset_bytes": first_lba * logical_block_bytes,
                    "size_bytes": (last_lba - first_lba + 1)
                    * logical_block_bytes,
                    "attributes": f"0x{attributes:016x}",
                    "name": name,
                }
            )
        backup_offset = int(primary["backup_lba"]) * logical_block_bytes
        if backup_offset + logical_block_bytes > size_bytes:
            raise InventoryError("backup GPT header lies beyond the disk")
        backup = parse_gpt_header(
            read_at(fd, backup_offset, logical_block_bytes), logical_block_bytes
        )
    finally:
        os.close(fd)
    return {
        "primary": primary,
        "backup": backup,
        "primary_entries_crc32_valid": (
            table_crc32 == int(str(primary["entries_crc32"]), 16)
        ),
        "primary_backup_crosscheck": (
            primary["disk_guid"] == backup["disk_guid"]
            and primary["current_lba"] == backup["backup_lba"]
            and primary["backup_lba"] == backup["current_lba"]
            and primary["first_usable_lba"] == backup["first_usable_lba"]
            and primary["last_usable_lba"] == backup["last_usable_lba"]
            and primary["entry_count"] == backup["entry_count"]
            and primary["entry_size"] == backup["entry_size"]
            and primary["entries_crc32"] == backup["entries_crc32"]
        ),
        "partitions": partitions,
    }


def uevent(path: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    payload = read_text(path)
    if payload is None:
        return result
    for line in payload.splitlines():
        key, separator, value = line.partition("=")
        if separator and key and key not in result:
            result[key] = value
    return result


def unsigned(path: Path) -> int:
    value = read_text(path, required=True)
    assert value is not None
    if not re.fullmatch(r"[0-9]+", value):
        raise InventoryError(f"expected unsigned integer in {path}")
    return int(value)


def parse_blkid_output(payload: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in payload.splitlines():
        if ": " in line:
            _, line = line.split(": ", 1)
            try:
                fields = shlex.split(line, posix=True)
            except ValueError as error:
                raise InventoryError("blkid returned malformed quoting") from error
            for field in fields:
                key, separator, value = field.partition("=")
                if separator and key and key not in values:
                    values[key] = value
            continue
        key, separator, value = line.partition("=")
        if separator and key and key not in values:
            values[key] = value
    return values


def probe_blkid(device: Path) -> dict[str, object]:
    command = ["blkid", "-p", "-c", "/dev/null", "-o", "export", str(device)]
    try:
        result = subprocess.run(
            command,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="strict",
            timeout=15,
            check=False,
        )
    except FileNotFoundError:
        return {"status": "tool-unavailable"}
    except subprocess.TimeoutExpired:
        return {"status": "timeout"}
    values = parse_blkid_output(result.stdout)
    return {
        "status": "identified" if result.returncode == 0 else "unidentified",
        "returncode": result.returncode,
        "values": values,
        "stderr": result.stderr.strip(),
    }


def sysfs_partition_map(sys_block: Path, disk: str) -> dict[int, dict[str, object]]:
    result: dict[int, dict[str, object]] = {}
    for candidate in sorted(sys_block.glob(f"{disk}*")):
        partition_file = candidate / "partition"
        if not partition_file.exists():
            continue
        number = unsigned(partition_file)
        values = uevent(candidate / "uevent")
        result[number] = {
            "name": candidate.name,
            "partition_number": number,
            "partition_name": values.get("PARTNAME"),
            "major_minor": read_text(candidate / "dev", required=True),
            "read_only": unsigned(candidate / "ro"),
            "start_512_sectors": unsigned(candidate / "start"),
            "size_512_sectors": unsigned(candidate / "size"),
            "devtype": values.get("DEVTYPE"),
        }
    return result


def inventory_disk(sys_block: Path, dev_root: Path, disk_path: Path) -> dict[str, object]:
    name = disk_path.name
    logical_block_bytes = unsigned(disk_path / "queue/logical_block_size")
    size_512_sectors = unsigned(disk_path / "size")
    size_bytes = size_512_sectors * 512
    partitions = sysfs_partition_map(sys_block, name)
    gpt = parse_gpt(dev_root / name, logical_block_bytes, size_bytes)
    for entry in gpt["partitions"]:
        assert isinstance(entry, dict)
        number = int(entry["number"])
        sys_entry = partitions.get(number)
        entry["sysfs"] = sys_entry
        if sys_entry is not None:
            expected_offset = int(sys_entry["start_512_sectors"]) * 512
            expected_size = int(sys_entry["size_512_sectors"]) * 512
            entry["sysfs_gpt_geometry_match"] = (
                expected_offset == int(entry["offset_bytes"])
                and expected_size == int(entry["size_bytes"])
            )
            entry["filesystem_probe"] = probe_blkid(
                dev_root / str(sys_entry["name"])
            )
    device = disk_path / "device"
    return {
        "name": name,
        "major_minor": read_text(disk_path / "dev", required=True),
        "read_only": unsigned(disk_path / "ro"),
        "size_512_sectors": size_512_sectors,
        "size_bytes": size_bytes,
        "logical_block_bytes": logical_block_bytes,
        "physical_block_bytes": unsigned(disk_path / "queue/physical_block_size"),
        "sysfs_path": str(disk_path.resolve()),
        "scsi": {
            key: read_text(device / key)
            for key in ("vendor", "model", "rev", "type", "wwid")
        },
        "disk_probe": probe_blkid(dev_root / name),
        "gpt": gpt,
    }


def mount_inventory(proc_root: Path) -> dict[str, object]:
    return {
        "mounts": read_text(proc_root / "mounts", required=True).splitlines(),
        "mountinfo": read_text(proc_root / "self/mountinfo", required=True).splitlines(),
        "swaps": read_text(proc_root / "swaps", required=True).splitlines(),
    }


def cmdline_fields(cmdline: str) -> dict[str, object]:
    selected: dict[str, list[str]] = {}
    prefixes = (
        "androidboot.slot_suffix=",
        "androidboot.bootdevice=",
        "androidboot.boot_devices=",
        "androidboot.vbmeta.",
        "androidboot.verifiedbootstate=",
        "androidboot.device_state=",
        "androidboot.serialno=",
        "androidboot.fused",
        "androidboot.bootreason=",
    )
    for token in cmdline.split():
        if token.startswith(prefixes):
            key, separator, value = token.partition("=")
            selected.setdefault(key, []).append(value if separator else "")
    return selected


def list_paths(root: Path, pattern: str) -> list[str]:
    return [str(path.resolve()) for path in sorted(root.glob(pattern))]


def collect(sys_root: Path, dev_root: Path, proc_root: Path) -> dict[str, object]:
    sys_block = sys_root / "class/block"
    disks = [
        path
        for path in sorted(sys_block.glob("sd*"))
        if re.fullmatch(r"sd[a-z]+", path.name)
        and (path / "device").exists()
        and not (path / "partition").exists()
    ]
    if not disks:
        raise InventoryError("no SCSI/UFS disks were found")
    cmdline = read_text(proc_root / "cmdline", required=True)
    assert cmdline is not None
    return {
        "format": "rog5-readonly-storage-inventory-v1",
        "captured_utc": datetime.now(timezone.utc).isoformat(),
        "kernel_release": os.uname().release,
        "boot_id": read_text(
            proc_root / "sys/kernel/random/boot_id", required=True
        ),
        "cmdline": cmdline,
        "boot_fields": cmdline_fields(cmdline),
        "ufs": {
            "platform_controllers": list_paths(
                sys_root / "bus/platform/drivers", "ufshcd-qcom/*"
            ),
            "scsi_hosts": list_paths(sys_root / "class/scsi_host", "host*"),
            "scsi_disks": list_paths(sys_root / "class/scsi_disk", "*") ,
            "rpmb_devices": list_paths(sys_root / "class", "rpmb/rpmb*"),
        },
        "disks": [inventory_disk(sys_block, dev_root, path) for path in disks],
        "mounts": mount_inventory(proc_root),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sys-root", type=Path, default=Path("/sys"))
    parser.add_argument("--dev-root", type=Path, default=Path("/dev"))
    parser.add_argument("--proc-root", type=Path, default=Path("/proc"))
    args = parser.parse_args()
    try:
        result = collect(args.sys_root, args.dev_root, args.proc_root)
    except (InventoryError, OSError, UnicodeError, ValueError) as error:
        print(f"FAIL read-only storage inventory: {error}", file=sys.stderr)
        return 1
    json.dump(result, sys.stdout, sort_keys=True, separators=(",", ":"))
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
