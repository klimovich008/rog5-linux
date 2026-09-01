#!/usr/bin/env python3
"""Verify the exact ROG Phone 5 60 Hz display DTB delta."""

from __future__ import annotations

import argparse
from hashlib import sha256
import importlib.util
from pathlib import Path
import struct
import sys
from types import ModuleType
from typing import NoReturn


BASE_SHA256 = "8b1250cefd69870662edb9131190f005f492b4c93c192ee7e2b89b9a121f22da"
BASE_SIZE = 107194
SYMBOLS = "/__symbols__"
REGULATORS = "/soc@0/rsc@18200000/regulators-1"
BOB = f"{REGULATORS}/bob"
L12 = f"{REGULATORS}/ldo12"
L13 = f"{REGULATORS}/ldo13"
TLMM = "/soc@0/pinctrl@f100000"
PINCTRL = f"{TLMM}/rog5-panel-default-state"
RESET_PIN = f"{PINCTRL}/reset-pins"
TE_PIN = f"{PINCTRL}/te-pins"
IRIS_WAKE_PIN = f"{PINCTRL}/iris-wakeup-pins"
IRIS_READY_PIN = f"{PINCTRL}/iris-ready-pins"
DISPCC = "/soc@0/clock-controller@af00000"
MDSS = "/soc@0/display-subsystem@ae00000"
MDP = f"{MDSS}/display-controller@ae01000"
DSI = f"{MDSS}/dsi@ae94000"
DSI_OUT = f"{DSI}/ports/port@1/endpoint"
DSI_PHY = f"{MDSS}/phy@ae94400"
PANEL = f"{DSI}/panel@0"
PANEL_PORT = f"{PANEL}/port"
PANEL_IN = f"{PANEL_PORT}/endpoint"


def fail(message: str) -> NoReturn:
    raise ValueError(message)


def cell(value: int) -> bytes:
    return struct.pack(">I", value)


def cells(*values: int) -> bytes:
    return b"".join(cell(value) for value in values)


def string(value: str) -> bytes:
    return value.encode("ascii") + b"\0"


def load_parser() -> ModuleType:
    path = Path(__file__).with_name("verify-recovery-dtb-delta.py")
    specification = importlib.util.spec_from_file_location("rog5_dtb", path)
    if specification is None or specification.loader is None:
        fail("bounded DTB parser is unavailable")
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


def phandle(nodes: dict[str, dict[str, bytes]], path: str) -> bytes:
    properties = nodes.get(path)
    if properties is None:
        fail(f"missing phandle node: {path}")
    value = properties.get("phandle", properties.get("linux,phandle"))
    if value is None or len(value) != 4 or value == cell(0):
        fail(f"invalid phandle: {path}")
    return value


def require_properties(
    nodes: dict[str, dict[str, bytes]], path: str, expected: dict[str, bytes]
) -> None:
    actual = nodes.get(path)
    if actual != expected:
        fail(f"wrong exact properties: {path}")


def compare(
    base: dict[str, dict[str, bytes]],
    candidate: dict[str, dict[str, bytes]],
    parser: ModuleType,
) -> tuple[int, int]:
    parser.require_board_identity(base, "base DTB")
    parser.require_board_identity(candidate, "candidate DTB")

    expected_added = {
        L12, L13, PINCTRL, RESET_PIN, TE_PIN, IRIS_WAKE_PIN,
        IRIS_READY_PIN, PANEL, PANEL_PORT, PANEL_IN,
    }
    added = set(candidate) - set(base)
    removed = set(base) - set(candidate)
    if added != expected_added or removed:
        fail(f"unapproved node delta added={sorted(added)} removed={sorted(removed)}")

    panel_in = phandle(candidate, PANEL_IN)
    dsi_out = phandle(candidate, DSI_OUT)
    pinctrl = phandle(candidate, PINCTRL)
    l12 = phandle(candidate, L12)
    l13 = phandle(candidate, L13)
    tlmm = phandle(candidate, TLMM)
    bob = phandle(candidate, BOB)

    expected_changes = {
        (SYMBOLS, "rog5_panel_default"): string(PINCTRL),
        (SYMBOLS, "rog5_panel_in"): string(PANEL_IN),
        (SYMBOLS, "vreg_l12c_1p8"): string(L12),
        (SYMBOLS, "vreg_l13c_3p0"): string(L13),
        (DISPCC, "status"): string("okay"),
        (MDSS, "status"): string("okay"),
        (MDP, "status"): string("okay"),
        (DSI, "status"): string("okay"),
        (DSI_OUT, "data-lanes"): cells(0, 1, 2, 3),
        (DSI_OUT, "remote-endpoint"): panel_in,
        (DSI_PHY, "status"): string("okay"),
        (REGULATORS, "vdd-l3-l4-l5-l7-l13-supply"): bob,
    }
    actual_changes: dict[tuple[str, str], bytes | None] = {}
    absent = object()
    for path in sorted(set(base) & set(candidate)):
        for name in sorted(set(base[path]) | set(candidate[path])):
            before = base[path].get(name, absent)
            after = candidate[path].get(name, absent)
            if before != after:
                actual_changes[(path, name)] = None if after is absent else after
    if actual_changes != expected_changes:
        fail(f"unapproved property delta: {sorted(actual_changes)}")

    require_properties(candidate, L12, {
        "phandle": l12,
        "regulator-initial-mode": cell(3),
        "regulator-max-microvolt": cell(1800000),
        "regulator-min-microvolt": cell(1800000),
        "regulator-name": string("vreg_l12c_1p8"),
    })
    require_properties(candidate, L13, {
        "phandle": l13,
        "regulator-initial-mode": cell(3),
        "regulator-max-microvolt": cell(3000000),
        "regulator-min-microvolt": cell(3000000),
        "regulator-name": string("vreg_l13c_3p0"),
    })
    require_properties(candidate, PINCTRL, {"phandle": pinctrl})
    require_properties(candidate, RESET_PIN, {
        "bias-disable": b"", "drive-strength": cell(8),
        "function": string("gpio"), "pins": string("gpio24"),
    })
    require_properties(candidate, TE_PIN, {
        "bias-pull-down": b"", "drive-strength": cell(2),
        "function": string("gpio"), "input-enable": b"",
        "pins": string("gpio82"),
    })
    require_properties(candidate, IRIS_WAKE_PIN, {
        "bias-disable": b"", "drive-strength": cell(8),
        "function": string("gpio"), "pins": string("gpio92"),
    })
    require_properties(candidate, IRIS_READY_PIN, {
        "bias-disable": b"", "drive-strength": cell(8),
        "function": string("gpio"), "input-enable": b"",
        "pins": string("gpio84"),
    })
    require_properties(candidate, PANEL, {
        "compatible": string("asus,rog5-ams678-er2"),
        "height-mm": cell(157),
        "iris-bypass-ready-gpios": tlmm + cells(84, 0),
        "iris-wakeup-gpios": tlmm + cells(92, 0),
        "pinctrl-0": pinctrl,
        "pinctrl-names": string("default"),
        "reg": cell(0),
        "reset-gpios": tlmm + cells(24, 1),
        "te-gpios": tlmm + cells(82, 0),
        "vdd-supply": l13,
        "vddio-supply": l12,
        "width-mm": cell(69),
    })
    require_properties(candidate, PANEL_PORT, {})
    require_properties(candidate, PANEL_IN, {
        "phandle": panel_in, "remote-endpoint": dsi_out,
    })
    return len(added), len(actual_changes)


def main(arguments: list[str]) -> int:
    arguments_parser = argparse.ArgumentParser(description=__doc__)
    arguments_parser.add_argument("base", type=Path)
    arguments_parser.add_argument("candidate", type=Path)
    options = arguments_parser.parse_args(arguments)
    parser = load_parser()
    base_data = parser.read_dtb_bytes(options.base)
    digest = sha256(base_data).hexdigest()
    if len(base_data) != BASE_SIZE or digest != BASE_SHA256:
        fail(f"base DTB identity changed: size={len(base_data)} sha256={digest}")
    base = parser.parse_dtb(base_data, str(options.base))
    candidate = parser.read_dtb(options.candidate)
    added, changed = compare(base, candidate, parser)
    print(f"base_sha256={digest}")
    print(f"added_nodes={added}")
    print(f"changed_existing_properties={changed}")
    print("PASS exact 60 Hz AMS678/Iris-bypass DTB delta")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv[1:]))
    except (OSError, ValueError) as error:
        print(f"FAIL {error}", file=sys.stderr)
        raise SystemExit(1)
