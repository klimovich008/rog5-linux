#!/usr/bin/env python3
"""Back up exact GPT metadata and non-data partitions over pinned SSH."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import stat
import subprocess
import sys


EXCLUDED_PARTITIONS = frozenset({"super", "userdata"})
DEVICE_RE = re.compile(r"sd[a-z]+[0-9]+")
DISK_RE = re.compile(r"sd[a-z]+")
LABEL_RE = re.compile(r"[A-Za-z0-9_.+-]{1,72}")
SHA256_RE = re.compile(r"[0-9a-f]{64}")
PARTITION_MANIFEST_HEADER = (
    "file\tlabel\tnode\tbytes\tunique_guid\tsource_sha256\thost_sha256"
)
GPT_MANIFEST_HEADER = (
    "file\tdisk\trole\toffset_bytes\tbytes\tdisk_guid\t"
    "source_sha256\thost_sha256"
)
BOOT_ID_RE = re.compile(
    r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
)


class BackupError(RuntimeError):
    pass


def canonical_file(path: Path, label: str, *, private: bool = False) -> Path:
    resolved = path.resolve(strict=True)
    metadata = resolved.lstat()
    if not stat.S_ISREG(metadata.st_mode) or path.is_symlink():
        raise BackupError(f"{label} is not a regular non-symlink file")
    if metadata.st_uid != os.geteuid():
        raise BackupError(f"{label} is not caller-owned")
    if private and stat.S_IMODE(metadata.st_mode) & 0o077:
        raise BackupError(f"{label} is accessible by another user")
    return resolved


def canonical_private_directory(path: Path, label: str) -> Path:
    resolved = path.resolve(strict=True)
    metadata = path.lstat()
    if path.is_symlink() or not stat.S_ISDIR(metadata.st_mode):
        raise BackupError(f"{label} is not a non-symlink directory")
    if metadata.st_uid != os.geteuid() or stat.S_IMODE(metadata.st_mode) != 0o700:
        raise BackupError(f"{label} is not caller-owned mode 0700")
    return resolved


def load_inventory(path: Path) -> dict[str, object]:
    path = canonical_file(path, "inventory", private=True)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise BackupError("inventory is not valid JSON") from error
    if payload.get("format") != "rog5-readonly-storage-inventory-v1":
        raise BackupError("inventory format is not exact")
    if not BOOT_ID_RE.fullmatch(str(payload.get("boot_id", ""))):
        raise BackupError("inventory boot ID is invalid")
    return payload


def backup_plan(inventory: dict[str, object]) -> tuple[list[dict[str, object]], int]:
    plan: list[dict[str, object]] = []
    total = 0
    seen_labels: set[str] = set()
    seen_guids: set[str] = set()
    disks = inventory.get("disks")
    if not isinstance(disks, list) or len(disks) != 7:
        raise BackupError("inventory does not contain exactly seven UFS LUNs")
    for disk in disks:
        if not isinstance(disk, dict) or not DISK_RE.fullmatch(str(disk.get("name", ""))):
            raise BackupError("inventory disk name is invalid")
        gpt = disk.get("gpt")
        if not isinstance(gpt, dict):
            raise BackupError("inventory GPT record is invalid")
        for key in (
            "primary_entries_crc32_valid",
            "primary_backup_crosscheck",
        ):
            if gpt.get(key) is not True:
                raise BackupError(f"inventory GPT check failed: {key}")
        primary = gpt.get("primary")
        backup = gpt.get("backup")
        if not isinstance(primary, dict) or not isinstance(backup, dict):
            raise BackupError("inventory GPT headers are invalid")
        if primary.get("header_crc32_valid") is not True or backup.get(
            "header_crc32_valid"
        ) is not True:
            raise BackupError("inventory GPT header CRC is invalid")
        partitions = gpt.get("partitions")
        if not isinstance(partitions, list):
            raise BackupError("inventory GPT partitions are invalid")
        for entry in partitions:
            if not isinstance(entry, dict):
                raise BackupError("inventory partition entry is invalid")
            label = str(entry.get("name", ""))
            if not LABEL_RE.fullmatch(label):
                raise BackupError(f"unsafe partition label: {label!r}")
            if label in seen_labels:
                raise BackupError(f"duplicate partition label: {label}")
            seen_labels.add(label)
            if label in EXCLUDED_PARTITIONS:
                continue
            guid = str(entry.get("unique_guid", ""))
            if guid in seen_guids or not re.fullmatch(
                r"[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}", guid
            ):
                raise BackupError(f"invalid or duplicate partition GUID: {guid}")
            seen_guids.add(guid)
            sysfs = entry.get("sysfs")
            if not isinstance(sysfs, dict) or entry.get(
                "sysfs_gpt_geometry_match"
            ) is not True:
                raise BackupError(f"partition geometry is not exact: {label}")
            node = str(sysfs.get("name", ""))
            size_bytes = int(entry.get("size_bytes", -1))
            size_sectors = int(sysfs.get("size_512_sectors", -1))
            start_sectors = int(sysfs.get("start_512_sectors", -1))
            if (
                not DEVICE_RE.fullmatch(node)
                or size_bytes <= 0
                or size_bytes != size_sectors * 512
                or start_sectors < 0
            ):
                raise BackupError(f"partition geometry is invalid: {label}")
            record = {
                "node": node,
                "label": label,
                "unique_guid": guid,
                "size_bytes": size_bytes,
                "size_512_sectors": size_sectors,
                "start_512_sectors": start_sectors,
            }
            plan.append(record)
            total += size_bytes
    if len(seen_labels) != 109 or len(plan) != 107:
        raise BackupError("partition selection is not the exact 109-minus-2 map")
    return plan, total


def gpt_backup_plan(inventory: dict[str, object]) -> tuple[list[dict[str, object]], int]:
    plan: list[dict[str, object]] = []
    total = 0
    disks = inventory.get("disks")
    if not isinstance(disks, list) or len(disks) != 7:
        raise BackupError("inventory does not contain exactly seven UFS LUNs")
    for disk in disks:
        if not isinstance(disk, dict):
            raise BackupError("inventory disk record is invalid")
        name = str(disk.get("name", ""))
        if not DISK_RE.fullmatch(name):
            raise BackupError("inventory disk name is invalid")
        logical = int(disk.get("logical_block_bytes", -1))
        size_bytes = int(disk.get("size_bytes", -1))
        size_sectors = int(disk.get("size_512_sectors", -1))
        gpt = disk.get("gpt")
        if (
            logical < 512
            or logical > 65536
            or logical & (logical - 1)
            or size_bytes != size_sectors * 512
            or not isinstance(gpt, dict)
        ):
            raise BackupError(f"invalid GPT disk geometry: {name}")
        primary = gpt.get("primary")
        backup = gpt.get("backup")
        if not isinstance(primary, dict) or not isinstance(backup, dict):
            raise BackupError(f"invalid GPT header record: {name}")
        primary_end = (
            int(primary["entries_lba"]) * logical + int(primary["table_bytes"])
        )
        primary_bytes = ((primary_end + logical - 1) // logical) * logical
        backup_offset = int(backup["entries_lba"]) * logical
        backup_bytes = size_bytes - backup_offset
        if (
            primary_bytes <= 2 * logical
            or primary_bytes > 1024 * 1024
            or backup_offset <= primary_bytes
            or backup_bytes <= logical
            or backup_bytes > 1024 * 1024
            or primary_bytes % logical
            or backup_offset % logical
            or backup_bytes % logical
        ):
            raise BackupError(f"GPT backup range is invalid: {name}")
        for role, offset, length in (
            ("primary", 0, primary_bytes),
            ("backup", backup_offset, backup_bytes),
        ):
            plan.append(
                {
                    "disk": name,
                    "disk_guid": primary["disk_guid"],
                    "disk_size_512_sectors": size_sectors,
                    "logical_block_bytes": logical,
                    "role": role,
                    "offset_bytes": offset,
                    "size_bytes": length,
                }
            )
            total += length
    return plan, total


def ssh_base(key: Path, known_hosts: Path) -> list[str]:
    return [
        "ssh",
        "-n",
        "-F",
        "/dev/null",
        "-i",
        str(key),
        "-o",
        "IdentitiesOnly=yes",
        "-o",
        "BatchMode=yes",
        "-o",
        "StrictHostKeyChecking=yes",
        "-o",
        f"UserKnownHostsFile={known_hosts}",
        "-o",
        "GlobalKnownHostsFile=/dev/null",
        "-o",
        "HostKeyAlias=rog5-fallback",
        "-o",
        "ConnectTimeout=8",
        "-o",
        "ConnectionAttempts=1",
        "-o",
        "ServerAliveInterval=5",
        "-o",
        "ServerAliveCountMax=2",
        "-o",
        "LogLevel=ERROR",
        "root@169.254.77.2",
    ]


def run_text(base: list[str], command: str) -> str:
    result = subprocess.run(
        [*base, command],
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="strict",
        timeout=180,
        check=False,
    )
    if result.returncode != 0:
        raise BackupError(
            f"remote read failed ({result.returncode}): {result.stderr.strip()}"
        )
    return result.stdout.strip()


def validation_prefix(boot_id: str, record: dict[str, object]) -> str:
    node = str(record["node"])
    label = str(record["label"])
    return (
        "set -eu; "
        f"[ \"$(cat /proc/sys/kernel/random/boot_id)\" = {shlex.quote(boot_id)} ]; "
        f"[ \"$(cat /sys/class/block/{node}/size)\" = {record['size_512_sectors']} ]; "
        f"[ \"$(cat /sys/class/block/{node}/start)\" = {record['start_512_sectors']} ]; "
        f"[ \"$(sed -n 's/^PARTNAME=//p' /sys/class/block/{node}/uevent)\" = {shlex.quote(label)} ]; "
    )


def source_sha256(base: list[str], boot_id: str, record: dict[str, object]) -> str:
    command = validation_prefix(boot_id, record) + f"exec sha256sum /dev/{record['node']}"
    output = run_text(base, command)
    digest = output.split(maxsplit=1)[0] if output else ""
    if not SHA256_RE.fullmatch(digest):
        raise BackupError(f"source hash is invalid for {record['label']}")
    return digest


def stream_partition(
    base: list[str], boot_id: str, record: dict[str, object], output: Path
) -> None:
    command = validation_prefix(boot_id, record) + (
        f"exec dd if=/dev/{record['node']} bs=4194304 status=none"
    )
    partial = output.with_name(output.name + ".partial")
    fd = os.open(partial, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC, 0o600)
    try:
        with os.fdopen(fd, "wb", closefd=True) as stream:
            process = subprocess.Popen(
                [*base, command],
                stdin=subprocess.DEVNULL,
                stdout=stream,
                stderr=subprocess.PIPE,
            )
            _, stderr = process.communicate(timeout=240)
            if process.returncode != 0:
                raise BackupError(
                    f"partition stream failed for {record['label']}: "
                    f"{stderr.decode('utf-8', errors='replace').strip()}"
                )
            stream.flush()
            os.fsync(stream.fileno())
        if partial.stat().st_size != int(record["size_bytes"]):
            raise BackupError(f"partition size mismatch for {record['label']}")
        os.rename(partial, output)
        fsync_directory(output.parent)
    except BaseException:
        try:
            partial.unlink()
        except FileNotFoundError:
            pass
        raise


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def fsync_directory(path: Path) -> None:
    flags = os.O_RDONLY | os.O_CLOEXEC | getattr(os, "O_DIRECTORY", 0)
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(path, flags)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def verified_resume_file(path: Path, size: int, digest: str, label: str) -> None:
    resolved = canonical_file(path, label, private=True)
    if stat.S_IMODE(resolved.stat().st_mode) != 0o600:
        raise BackupError(f"{label} is not mode 0600")
    if resolved.stat().st_size != size:
        raise BackupError(f"{label} has the wrong size")
    if file_sha256(resolved) != digest:
        raise BackupError(f"{label} does not match its accepted hash")


def manifest_lines(path: Path, header: str, label: str) -> list[list[str]]:
    path = canonical_file(path, label, private=True)
    if stat.S_IMODE(path.stat().st_mode) != 0o600:
        raise BackupError(f"{label} is not mode 0600")
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError) as error:
        raise BackupError(f"{label} cannot be read") from error
    if not lines or lines[0] != header or any(not line for line in lines[1:]):
        raise BackupError(f"{label} header or records are invalid")
    return [line.split("\t") for line in lines[1:]]


def verify_gpt_resume(
    output: Path, directory: Path, manifest: Path, plan: list[dict[str, object]]
) -> int:
    rows = manifest_lines(manifest, GPT_MANIFEST_HEADER, "GPT manifest")
    if len(rows) > len(plan):
        raise BackupError("GPT manifest contains more records than the exact plan")
    accepted: set[str] = set()
    for index, (row, record) in enumerate(zip(rows, plan, strict=False), 1):
        filename = f"{record['disk']}-{record['role']}.bin"
        expected = (
            f"gpt/{filename}",
            str(record["disk"]),
            str(record["role"]),
            str(record["offset_bytes"]),
            str(record["size_bytes"]),
            str(record["disk_guid"]),
        )
        if len(row) != 8 or tuple(row[:6]) != expected:
            raise BackupError(f"GPT manifest record {index} is not the exact plan prefix")
        if not SHA256_RE.fullmatch(row[6]) or row[6] != row[7]:
            raise BackupError(f"GPT manifest record {index} has invalid hashes")
        verified_resume_file(
            output / row[0], int(record["size_bytes"]), row[7], f"GPT file {filename}"
        )
        accepted.add(filename)
    if {entry.name for entry in directory.iterdir()} != accepted:
        raise BackupError("GPT directory is not the exact accepted manifest prefix")
    return len(rows)


def verify_partition_resume(
    output: Path, directory: Path, manifest: Path, plan: list[dict[str, object]]
) -> int:
    rows = manifest_lines(manifest, PARTITION_MANIFEST_HEADER, "partition manifest")
    if len(rows) > len(plan):
        raise BackupError("partition manifest contains more records than the exact plan")
    accepted: set[str] = set()
    for index, (row, record) in enumerate(zip(rows, plan, strict=False), 1):
        filename = f"{index:03d}-{record['label']}.img"
        expected = (
            f"partitions/{filename}",
            str(record["label"]),
            str(record["node"]),
            str(record["size_bytes"]),
            str(record["unique_guid"]),
        )
        if len(row) != 7 or tuple(row[:5]) != expected:
            raise BackupError(
                f"partition manifest record {index} is not the exact plan prefix"
            )
        if not SHA256_RE.fullmatch(row[5]) or row[5] != row[6]:
            raise BackupError(f"partition manifest record {index} has invalid hashes")
        verified_resume_file(
            output / row[0],
            int(record["size_bytes"]),
            row[6],
            f"partition file {filename}",
        )
        accepted.add(filename)
    if {entry.name for entry in directory.iterdir()} != accepted:
        raise BackupError("partition directory is not the exact accepted manifest prefix")
    return len(rows)


def gpt_validation_prefix(boot_id: str, record: dict[str, object]) -> str:
    disk = str(record["disk"])
    return (
        "set -eu; "
        f"[ \"$(cat /proc/sys/kernel/random/boot_id)\" = {shlex.quote(boot_id)} ]; "
        f"[ \"$(cat /sys/class/block/{disk}/size)\" = {record['disk_size_512_sectors']} ]; "
        f"[ \"$(cat /sys/class/block/{disk}/queue/logical_block_size)\" = {record['logical_block_bytes']} ]; "
    )


def gpt_read_command(boot_id: str, record: dict[str, object]) -> str:
    logical = int(record["logical_block_bytes"])
    skip = int(record["offset_bytes"]) // logical
    count = int(record["size_bytes"]) // logical
    return gpt_validation_prefix(boot_id, record) + (
        f"dd if=/dev/{record['disk']} bs={logical} skip={skip} count={count} status=none"
    )


def source_gpt_sha256(
    base: list[str], boot_id: str, record: dict[str, object]
) -> str:
    output = run_text(base, gpt_read_command(boot_id, record) + " | sha256sum")
    digest = output.split(maxsplit=1)[0] if output else ""
    if not SHA256_RE.fullmatch(digest):
        raise BackupError(
            f"source GPT hash is invalid for {record['disk']} {record['role']}"
        )
    return digest


def stream_gpt(
    base: list[str], boot_id: str, record: dict[str, object], output: Path
) -> None:
    partial = output.with_name(output.name + ".partial")
    fd = os.open(partial, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC, 0o600)
    try:
        with os.fdopen(fd, "wb", closefd=True) as stream:
            process = subprocess.Popen(
                [*base, gpt_read_command(boot_id, record)],
                stdin=subprocess.DEVNULL,
                stdout=stream,
                stderr=subprocess.PIPE,
            )
            _, stderr = process.communicate(timeout=60)
            if process.returncode != 0:
                raise BackupError(
                    f"GPT stream failed for {record['disk']} {record['role']}: "
                    f"{stderr.decode('utf-8', errors='replace').strip()}"
                )
            stream.flush()
            os.fsync(stream.fileno())
        if partial.stat().st_size != int(record["size_bytes"]):
            raise BackupError(
                f"GPT range size mismatch for {record['disk']} {record['role']}"
            )
        os.rename(partial, output)
        fsync_directory(output.parent)
    except BaseException:
        try:
            partial.unlink()
        except FileNotFoundError:
            pass
        raise


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--inventory", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--ssh-key", type=Path, required=True)
    parser.add_argument("--known-hosts", type=Path, required=True)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    try:
        inventory = load_inventory(args.inventory)
        key = canonical_file(args.ssh_key, "SSH key", private=True)
        known_hosts = canonical_file(args.known_hosts, "known-hosts")
        plan, partition_bytes = backup_plan(inventory)
        gpt_plan, gpt_bytes = gpt_backup_plan(inventory)
        total_bytes = partition_bytes + gpt_bytes
        output = args.output
        if output == Path("/") or output.is_symlink():
            raise BackupError("backup output is unsafe")
        output.parent.resolve(strict=True)
        manifest = output / "SHA256SUMS.tsv"
        gpt_manifest = output / "GPT-SHA256SUMS.tsv"
        if args.resume:
            output = canonical_private_directory(output, "backup output")
            partitions = canonical_private_directory(
                output / "partitions", "partition backup directory"
            )
            gpt_output = canonical_private_directory(output / "gpt", "GPT backup directory")
            gpt_done = verify_gpt_resume(output, gpt_output, gpt_manifest, gpt_plan)
            partition_done = verify_partition_resume(
                output, partitions, manifest, plan
            )
        else:
            if output.exists():
                raise BackupError("backup output already exists")
            output.mkdir(mode=0o700)
            partitions = output / "partitions"
            partitions.mkdir(mode=0o700)
            gpt_output = output / "gpt"
            gpt_output.mkdir(mode=0o700)
            with gpt_manifest.open("x", encoding="utf-8", newline="\n") as records:
                os.chmod(gpt_manifest, 0o600)
                records.write(GPT_MANIFEST_HEADER + "\n")
                records.flush()
                os.fsync(records.fileno())
            with manifest.open("x", encoding="utf-8", newline="\n") as records:
                os.chmod(manifest, 0o600)
                records.write(PARTITION_MANIFEST_HEADER + "\n")
                records.flush()
                os.fsync(records.fileno())
            gpt_done = 0
            partition_done = 0
        remaining_bytes = sum(
            int(record["size_bytes"]) for record in gpt_plan[gpt_done:]
        ) + sum(int(record["size_bytes"]) for record in plan[partition_done:])
        available = shutil.disk_usage(output.parent).free
        if available < remaining_bytes + 1024 * 1024 * 1024:
            raise BackupError("less than the required remaining backup headroom is free")
        boot_id = str(inventory["boot_id"])
        base = ssh_base(key, known_hosts)
        remote_id = run_text(
            base,
            "set -eu; printf '%s\\n' \"$(cat /proc/sys/kernel/random/boot_id)\"",
        )
        if remote_id != boot_id:
            raise BackupError("phone boot identity changed before backup")
        with gpt_manifest.open("a", encoding="utf-8", newline="\n") as records:
            for index, record in enumerate(gpt_plan[gpt_done:], gpt_done + 1):
                filename = f"{record['disk']}-{record['role']}.bin"
                destination = gpt_output / filename
                source_digest = source_gpt_sha256(base, boot_id, record)
                stream_gpt(base, boot_id, record, destination)
                host_digest = file_sha256(destination)
                if source_digest != host_digest:
                    raise BackupError(
                        f"source/host GPT hash mismatch: {record['disk']} {record['role']}"
                    )
                records.write(
                    "\t".join(
                        (
                            f"gpt/{filename}",
                            str(record["disk"]),
                            str(record["role"]),
                            str(record["offset_bytes"]),
                            str(record["size_bytes"]),
                            str(record["disk_guid"]),
                            source_digest,
                            host_digest,
                        )
                    )
                    + "\n"
                )
                records.flush()
                os.fsync(records.fileno())
                print(
                    f"GPT_BACKED_UP {index}/14 disk={record['disk']} "
                    f"role={record['role']} sha256={host_digest}"
                )
        with manifest.open("a", encoding="utf-8", newline="\n") as records:
            for index, record in enumerate(
                plan[partition_done:], partition_done + 1
            ):
                filename = f"{index:03d}-{record['label']}.img"
                destination = partitions / filename
                source_digest = source_sha256(base, boot_id, record)
                stream_partition(base, boot_id, record, destination)
                host_digest = file_sha256(destination)
                if host_digest != source_digest:
                    raise BackupError(f"source/host hash mismatch: {record['label']}")
                records.write(
                    "\t".join(
                        (
                            f"partitions/{filename}",
                            str(record["label"]),
                            str(record["node"]),
                            str(record["size_bytes"]),
                            str(record["unique_guid"]),
                            source_digest,
                            host_digest,
                        )
                    )
                    + "\n"
                )
                records.flush()
                os.fsync(records.fileno())
                print(
                    f"BACKED_UP {index}/107 label={record['label']} "
                    f"bytes={record['size_bytes']} sha256={host_digest}"
                )
        print(
            f"PASS read-only storage backup gpt_ranges={len(gpt_plan)} "
            f"partitions={len(plan)} bytes={total_bytes} "
            f"output={output}"
        )
        return 0
    except (BackupError, OSError, subprocess.SubprocessError, ValueError) as error:
        print(f"FAIL read-only partition backup: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
