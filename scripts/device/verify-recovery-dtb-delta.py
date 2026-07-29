#!/usr/bin/env python3
"""Verify that a recovery DTB changes only the reviewed isolation contract."""

from __future__ import annotations

import argparse
from pathlib import Path
import struct
import sys
from typing import NoReturn


FDT_MAGIC = 0xD00DFEED
FDT_BEGIN_NODE = 1
FDT_END_NODE = 2
FDT_PROP = 3
FDT_NOP = 4
FDT_END = 9
HEADER_WORDS = 10
HEADER_SIZE = HEADER_WORDS * 4
MAX_DTB_SIZE = 2 * 1024 * 1024

GPU = "/soc@0/gpu@3d00000"
GMU = "/soc@0/gmu@3d6a000"
GPUCC = "/soc@0/clock-controller@3d90000"
ADRENO_SMMU = "/soc@0/iommu@3da0000"
RMTFS = "/reserved-memory/memory@9b800000"
USB = "/soc@0/usb@a6f8800"
USB_DWC3 = f"{USB}/usb@a600000"
USB_HSPHY = "/soc@0/phy@88e3000"

FIXED_PROPERTIES = {
    (RMTFS, "status"): b"disabled\0",
    (GPU, "status"): b"disabled\0",
    (GMU, "status"): b"disabled\0",
    (GPUCC, "status"): b"disabled\0",
    (ADRENO_SMMU, "status"): b"disabled\0",
    (USB, "qcom,select-utmi-as-pipe-clk"): b"",
    (USB, "status"): b"okay\0",
    (USB_DWC3, "maximum-speed"): b"high-speed\0",
    (USB_DWC3, "phy-names"): b"usb2-phy\0",
    (USB_HSPHY, "status"): b"okay\0",
}


def fail(message: str) -> NoReturn:
    raise ValueError(message)


def aligned(value: int) -> int:
    return (value + 3) & ~3


def bounded_slice(data: bytes, offset: int, size: int, label: str) -> bytes:
    if offset < 0 or size < 0 or offset > len(data) - size:
        fail(f"{label} is outside the DTB")
    return data[offset : offset + size]


def c_string(data: bytes, offset: int, label: str) -> tuple[str, int]:
    if offset < 0 or offset >= len(data):
        fail(f"{label} offset is outside its block")
    end = data.find(b"\0", offset)
    if end < 0:
        fail(f"{label} is not NUL terminated")
    try:
        value = data[offset:end].decode("ascii")
    except UnicodeDecodeError:
        fail(f"{label} is not ASCII")
    return value, end + 1


def read_dtb(path: Path) -> dict[str, dict[str, bytes]]:
    if path.is_symlink() or not path.is_file():
        fail(f"DTB is not an ordinary file: {path}")
    data = path.read_bytes()
    if len(data) < HEADER_SIZE or len(data) > MAX_DTB_SIZE:
        fail(f"DTB has an invalid size: {path}")
    (
        magic,
        total_size,
        structure_offset,
        strings_offset,
        reservation_offset,
        version,
        compatible_version,
        _boot_cpu,
        strings_size,
        structure_size,
    ) = struct.unpack(">10I", data[:HEADER_SIZE])
    if magic != FDT_MAGIC:
        fail(f"DTB has an invalid magic: {path}")
    if total_size != len(data):
        fail(f"DTB total size does not equal its file size: {path}")
    if version != 17 or compatible_version != 16:
        fail(f"DTB has an unsupported format version: {path}")
    if (
        reservation_offset < HEADER_SIZE
        or reservation_offset % 8
        or reservation_offset > total_size - 16
        or structure_offset % 4
    ):
        fail(f"DTB reservation map offset is invalid: {path}")
    reservation_end = reservation_offset
    while reservation_end <= total_size - 16:
        address, size = struct.unpack_from(">QQ", data, reservation_end)
        reservation_end += 16
        if address == 0 and size == 0:
            break
    else:
        fail(f"DTB reservation map is unterminated: {path}")
    blocks = sorted(
        (
            (reservation_offset, reservation_end, "reservation map"),
            (
                structure_offset,
                structure_offset + structure_size,
                "structure block",
            ),
            (strings_offset, strings_offset + strings_size, "strings block"),
        )
    )
    for start, end, label in blocks:
        if start < HEADER_SIZE or end < start or end > total_size:
            fail(f"DTB {label} range is invalid: {path}")
    for first, second in zip(blocks, blocks[1:]):
        if first[1] > second[0]:
            fail(f"DTB blocks overlap: {first[2]} and {second[2]}")
    structure = bounded_slice(
        data, structure_offset, structure_size, "structure block"
    )
    strings = bounded_slice(data, strings_offset, strings_size, "strings block")

    nodes: dict[str, dict[str, bytes]] = {}
    stack: list[str] = []
    position = 0
    ended = False
    while position < len(structure):
        if position > len(structure) - 4:
            fail("truncated DTB structure token")
        token = struct.unpack_from(">I", structure, position)[0]
        position += 4
        if token == FDT_BEGIN_NODE:
            name, next_position = c_string(
                structure, position, "DTB node name"
            )
            position = aligned(next_position)
            if not stack:
                if nodes or name:
                    fail("DTB does not begin with one empty root node")
                path_name = "/"
            else:
                if not name or "/" in name:
                    fail("DTB contains an invalid child node name")
                parent = stack[-1]
                path_name = f"/{name}" if parent == "/" else f"{parent}/{name}"
            if path_name in nodes:
                fail(f"DTB contains a duplicate node: {path_name}")
            nodes[path_name] = {}
            stack.append(path_name)
        elif token == FDT_END_NODE:
            if not stack:
                fail("DTB closes a node outside the root")
            stack.pop()
        elif token == FDT_PROP:
            if not stack or position > len(structure) - 8:
                fail("DTB property appears outside a node or is truncated")
            size, name_offset = struct.unpack_from(">II", structure, position)
            position += 8
            value = bounded_slice(
                structure, position, size, "DTB property value"
            )
            position = aligned(position + size)
            name, _next_name = c_string(
                strings, name_offset, "DTB property name"
            )
            if not name or "/" in name:
                fail("DTB contains an invalid property name")
            properties = nodes[stack[-1]]
            if name in properties:
                fail(f"DTB contains a duplicate property: {stack[-1]}:{name}")
            properties[name] = value
        elif token == FDT_NOP:
            continue
        elif token == FDT_END:
            if stack:
                fail("DTB ended with unclosed nodes")
            if any(structure[position:]):
                fail("DTB structure has nonzero data after its end token")
            ended = True
            break
        else:
            fail(f"DTB contains an unknown structure token: {token}")
    if not ended or "/" not in nodes:
        fail("DTB structure has no complete root")
    return nodes


def require_board_identity(nodes: dict[str, dict[str, bytes]], label: str) -> None:
    expected = b"asus,rog-phone5\0qcom,sm8350\0"
    if nodes.get("/", {}).get("compatible") != expected:
        fail(f"{label} lacks the exact ROG Phone 5 compatible identity")


def compare(
    base: dict[str, dict[str, bytes]],
    candidate: dict[str, dict[str, bytes]],
) -> int:
    require_board_identity(base, "base DTB")
    require_board_identity(candidate, "candidate DTB")
    if set(base) != set(candidate):
        added = sorted(set(candidate) - set(base))
        removed = sorted(set(base) - set(candidate))
        fail(f"recovery overlay changed DTB nodes: added={added} removed={removed}")

    hsphy = candidate.get(USB_HSPHY)
    if hsphy is None:
        fail("candidate lacks the USB2 PHY node")
    hsphy_phandle = hsphy.get("phandle")
    if hsphy_phandle is None:
        hsphy_phandle = hsphy.get("linux,phandle")
    if hsphy_phandle is None or len(hsphy_phandle) != 4:
        fail("candidate USB2 PHY has no exact one-cell phandle")
    expected = dict(FIXED_PROPERTIES)
    expected[(USB_DWC3, "phys")] = hsphy_phandle

    changed = 0
    absent = object()
    for path in sorted(base):
        base_properties = base[path]
        candidate_properties = candidate[path]
        for name in sorted(set(base_properties) | set(candidate_properties)):
            key = (path, name)
            before = base_properties.get(name, absent)
            after = candidate_properties.get(name, absent)
            if key in expected:
                if after != expected[key]:
                    fail(f"candidate recovery property is wrong: {path}:{name}")
            elif before != after:
                fail(f"recovery overlay changed an unapproved property: {path}:{name}")
            if before != after:
                changed += 1

    for (path, name), value in expected.items():
        if candidate.get(path, {}).get(name, absent) != value:
            fail(f"candidate lacks an approved recovery property: {path}:{name}")
    if changed == 0:
        fail("recovery overlay made no semantic change")
    return changed


def parse_arguments(arguments: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("base", type=Path)
    parser.add_argument("candidate", type=Path)
    return parser.parse_args(arguments)


def main(arguments: list[str]) -> int:
    options = parse_arguments(arguments)
    changed = compare(read_dtb(options.base), read_dtb(options.candidate))
    print(f"changed_properties={changed}")
    print("PASS recovery DTB is an exact board-preserving isolation delta")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv[1:]))
    except (OSError, ValueError) as error:
        print(f"FAIL {error}", file=sys.stderr)
        raise SystemExit(1)
