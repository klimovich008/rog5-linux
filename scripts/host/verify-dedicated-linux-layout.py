#!/usr/bin/env python3
"""Verify the public, non-secret Phase-3 ROG5 partition geometry."""

from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import NoReturn


FORMAT = "rog5-dedicated-linux-layout-v1"
LINUX_FILESYSTEM_GUID = "0fc63daf-8483-4772-8e79-3d69d8477de4"
MIB = 1024 * 1024


class LayoutError(RuntimeError):
    pass


def fail(message: str) -> NoReturn:
    raise LayoutError(message)


def exact_keys(value: object, expected: set[str], label: str) -> dict[str, object]:
    if not isinstance(value, dict) or set(value) != expected:
        fail(f"{label} keys changed")
    return value


def integer(value: object, label: str) -> int:
    if type(value) is not int or value < 0:
        fail(f"{label} is not a non-negative integer")
    return value


def partition(value: object, label: str, *, pre_shrink: bool) -> dict[str, object]:
    keys = {"number", "name", "first_lba", "last_lba", "size_lba"}
    if pre_shrink:
        keys.add("pre_shrink_filesystem_blocks")
    row = exact_keys(value, keys, label)
    first = integer(row["first_lba"], f"{label} first LBA")
    last = integer(row["last_lba"], f"{label} last LBA")
    size = integer(row["size_lba"], f"{label} size")
    if last < first or size != last - first + 1:
        fail(f"{label} geometry is inconsistent")
    return row


def verify(path: Path) -> dict[str, int]:
    try:
        data = json.loads(path.read_text(encoding="ascii"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        fail(f"cannot read layout: {error}")
    root = exact_keys(data, {"format", "source_checkpoint", "ext4_checkpoint", "proposal"}, "layout")
    if root["format"] != FORMAT:
        fail("layout format changed")

    source = exact_keys(
        root["source_checkpoint"],
        {
            "captured_date",
            "lun_bytes",
            "logical_block_bytes",
            "gpt_entry_count",
            "first_usable_lba",
            "last_usable_lba",
            "backup_header_lba",
            "preserved_prefix_last_lba",
            "userdata",
        },
        "source checkpoint",
    )
    block_bytes = integer(source["logical_block_bytes"], "logical block size")
    last_usable = integer(source["last_usable_lba"], "last usable LBA")
    backup_header = integer(source["backup_header_lba"], "backup header LBA")
    if (
        block_bytes != 4096
        or integer(source["lun_bytes"], "LUN size") != 253403070464
        or integer(source["first_usable_lba"], "first usable LBA") != 6
        or last_usable != 61865978
        or backup_header != 61865983
        or (backup_header + 1) * block_bytes != source["lun_bytes"]
    ):
        fail("source LUN/GPT geometry changed")
    current = partition(source["userdata"], "current userdata", pre_shrink=False)
    if (
        current["number"] != 23
        or current["name"] != "userdata"
        or current["first_lba"] != integer(source["preserved_prefix_last_lba"], "preserved prefix") + 1
        or current["last_lba"] != last_usable
    ):
        fail("current userdata boundary changed")

    ext4 = exact_keys(
        root["ext4_checkpoint"],
        {"block_size", "block_count", "estimated_minimum_blocks", "state"},
        "ext4 checkpoint",
    )
    if ext4["state"] != "clean" or integer(ext4["block_size"], "ext4 block size") != block_bytes:
        fail("ext4 checkpoint is not clean 4 KiB geometry")
    if integer(ext4["block_count"], "ext4 block count") != current["size_lba"]:
        fail("ext4 does not fill current userdata")
    minimum = integer(ext4["estimated_minimum_blocks"], "estimated minimum blocks")

    proposal = exact_keys(
        root["proposal"],
        {"unchanged_partition_numbers", "userdata", "arch_root_a", "swap"},
        "proposal",
    )
    if proposal["unchanged_partition_numbers"] != list(range(1, 23)):
        fail("protected partition set changed")
    if proposal["swap"] != "zram-only":
        fail("storage-backed swap is not proposed")

    userdata = partition(proposal["userdata"], "proposed userdata", pre_shrink=True)
    root_partition = exact_keys(
        proposal["arch_root_a"],
        {
            "number",
            "name",
            "type_guid",
            "filesystem",
            "filesystem_label",
            "first_lba",
            "last_lba",
            "size_lba",
        },
        "Arch root",
    )
    root_partition = partition(
        {key: root_partition[key] for key in ("number", "name", "first_lba", "last_lba", "size_lba")},
        "Arch root",
        pre_shrink=False,
    ) | {
        key: proposal["arch_root_a"][key]
        for key in ("type_guid", "filesystem", "filesystem_label")
    }

    if userdata["number"] != 23 or userdata["name"] != "userdata" or userdata["first_lba"] != current["first_lba"]:
        fail("userdata identity/start would change")
    if userdata["last_lba"] + 1 != root_partition["first_lba"]:
        fail("proposed partitions overlap or leave a gap")
    if root_partition["last_lba"] != last_usable:
        fail("Arch root does not end at the existing last usable LBA")
    if root_partition["number"] != 24 or root_partition["number"] > integer(source["gpt_entry_count"], "GPT entry count"):
        fail("Arch root GPT entry is unavailable")
    if root_partition["name"] != "arch_root_a" or root_partition["type_guid"] != LINUX_FILESYSTEM_GUID:
        fail("Arch root GPT identity changed")
    if root_partition["filesystem"] != "ext4" or root_partition["filesystem_label"] != "ROG5_ARCH_A":
        fail("Arch root filesystem identity changed")
    if root_partition["first_lba"] * block_bytes % MIB:
        fail("Arch root start is not 1 MiB aligned")

    pre_shrink = integer(userdata["pre_shrink_filesystem_blocks"], "pre-shrink filesystem blocks")
    if minimum >= pre_shrink:
        fail("pre-shrink size has no measured ext4 headroom")
    if pre_shrink >= userdata["size_lba"] or userdata["size_lba"] - pre_shrink < 128:
        fail("pre-shrink size lacks a partition-boundary margin")
    if root_partition["size_lba"] * block_bytes < 32 * 1024**3 - MIB:
        fail("Arch root is smaller than the aligned 32 GiB target")

    return {
        "userdata_bytes": userdata["size_lba"] * block_bytes,
        "arch_root_bytes": root_partition["size_lba"] * block_bytes,
        "ext4_headroom_bytes": (pre_shrink - minimum) * block_bytes,
    }


def main(arguments: list[str]) -> int:
    if len(arguments) != 1:
        fail("usage: verify-dedicated-linux-layout.py LAYOUT.json")
    result = verify(Path(arguments[0]))
    print(
        "PASS dedicated Linux layout "
        f"userdata_bytes={result['userdata_bytes']} "
        f"arch_root_bytes={result['arch_root_bytes']} "
        f"ext4_headroom_bytes={result['ext4_headroom_bytes']}"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv[1:]))
    except LayoutError as error:
        print(f"FAIL {error}", file=sys.stderr)
        raise SystemExit(1)
