#!/usr/bin/env python3
"""Verify the exact ROG Phone 5 buttons and green-indicator DTB delta."""

from __future__ import annotations

import argparse
from hashlib import sha256
import importlib.util
from pathlib import Path
import struct
import sys
from types import ModuleType
from typing import NoReturn


ACCEPTED_BASE_SHA256 = (
    "86e5cb81191e3de39c9527b838fa03d78744cd9b0d862336f0c1f36a9f534f46"
)
ACCEPTED_BASE_SIZE = 102870

SYMBOLS = "/__symbols__"
GPIO_KEYS = "/gpio-keys"
VOLUME_UP = f"{GPIO_KEYS}/key-volume-up"
SPMI = "/soc@0/spmi@c440000"
PMK8350 = f"{SPMI}/pmic@0"
PM8350 = f"{SPMI}/pmic@1"
PM8350C = f"{SPMI}/pmic@2"
PM8350_GPIO = f"{PM8350}/gpio@8800"
VOLUME_UP_PINCTRL = f"{PM8350_GPIO}/volume-up-default-state"
PON = f"{PMK8350}/pon@1300"
PWRKEY = f"{PON}/pwrkey"
RESIN = f"{PON}/resin"
PM8350C_PWM = f"{PM8350C}/pwm"
GREEN_LED = f"{PM8350C_PWM}/led@2"


def fail(message: str) -> NoReturn:
    raise ValueError(message)


def cell(value: int) -> bytes:
    return struct.pack(">I", value)


def string(value: str) -> bytes:
    return value.encode("ascii") + b"\0"


def load_dtb_parser() -> ModuleType:
    parser_path = Path(__file__).with_name("verify-recovery-dtb-delta.py")
    specification = importlib.util.spec_from_file_location(
        "rog5_recovery_dtb_parser", parser_path
    )
    if specification is None or specification.loader is None:
        fail(f"cannot load bounded DTB parser: {parser_path}")
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


def node_phandle(
    nodes: dict[str, dict[str, bytes]], path: str, label: str
) -> bytes:
    properties = nodes.get(path)
    if properties is None:
        fail(f"{label} node is missing: {path}")
    phandle = properties.get("phandle")
    linux_phandle = properties.get("linux,phandle")
    if phandle is None:
        phandle = linux_phandle
    elif linux_phandle is not None and linux_phandle != phandle:
        fail(f"{label} has conflicting phandle properties: {path}")
    if phandle is None or len(phandle) != 4 or phandle == b"\0\0\0\0":
        fail(f"{label} lacks an exact nonzero one-cell phandle: {path}")
    return phandle


def require_exact_properties(
    nodes: dict[str, dict[str, bytes]],
    path: str,
    expected: dict[str, bytes],
) -> None:
    actual = nodes.get(path)
    if actual is None:
        fail(f"candidate lacks approved node: {path}")
    if actual != expected:
        added = sorted(set(actual) - set(expected))
        removed = sorted(set(expected) - set(actual))
        wrong = sorted(
            name
            for name in set(actual) & set(expected)
            if actual[name] != expected[name]
        )
        fail(
            f"candidate node properties are wrong: {path} "
            f"added={added} removed={removed} wrong={wrong}"
        )


def require_enabled_parent(
    nodes: dict[str, dict[str, bytes]], path: str, label: str
) -> None:
    properties = nodes.get(path)
    if properties is None:
        fail(f"candidate lacks approved parent: {path}")
    status = properties.get("status")
    if status not in (None, string("okay")):
        fail(f"candidate approved parent is disabled: {label}: {path}")


def require_gpio_provider(nodes: dict[str, dict[str, bytes]]) -> None:
    properties = nodes.get(PM8350_GPIO)
    if properties is None:
        fail(f"candidate lacks PM8350 GPIO provider: {PM8350_GPIO}")
    expected = {
        "gpio-controller": b"",
        "#gpio-cells": cell(2),
        "interrupt-controller": b"",
        "#interrupt-cells": cell(2),
    }
    for name, value in expected.items():
        if properties.get(name) != value:
            fail(f"candidate PM8350 GPIO provider is wrong: {name}")


def require_unique_phandles(nodes: dict[str, dict[str, bytes]]) -> None:
    owners: dict[bytes, str] = {}
    for path, properties in nodes.items():
        phandle = properties.get("phandle")
        linux_phandle = properties.get("linux,phandle")
        if phandle is None:
            phandle = linux_phandle
        elif linux_phandle is not None and linux_phandle != phandle:
            fail(f"candidate has conflicting phandle properties: {path}")
        if phandle is None:
            continue
        if len(phandle) != 4 or phandle == b"\0\0\0\0":
            fail(f"candidate has an invalid phandle: {path}")
        previous = owners.setdefault(phandle, path)
        if previous != path:
            fail(
                "candidate has a duplicate phandle: "
                f"{previous} and {path}"
            )


def compare(
    base: dict[str, dict[str, bytes]],
    candidate: dict[str, dict[str, bytes]],
    parser: ModuleType,
) -> tuple[int, int]:
    parser.require_board_identity(base, "base DTB")
    parser.require_board_identity(candidate, "candidate DTB")

    for path, label in (
        (SPMI, "SPMI"),
        (PMK8350, "PMK8350"),
        (PON, "PMK8350 PON"),
        (PM8350, "PM8350"),
        (PM8350_GPIO, "PM8350 GPIO"),
        (PM8350C, "PM8350C"),
    ):
        require_enabled_parent(candidate, path, label)
    require_gpio_provider(candidate)

    expected_added_nodes = {
        GPIO_KEYS,
        VOLUME_UP,
        VOLUME_UP_PINCTRL,
        GREEN_LED,
    }
    added_nodes = set(candidate) - set(base)
    removed_nodes = set(base) - set(candidate)
    if added_nodes != expected_added_nodes or removed_nodes:
        fail(
            "candidate changed an unapproved node set: "
            f"added={sorted(added_nodes)} removed={sorted(removed_nodes)}"
        )

    expected_changes = {
        (SYMBOLS, "rog5_volume_up_default"): string(VOLUME_UP_PINCTRL),
        (PWRKEY, "status"): string("okay"),
        (RESIN, "linux,code"): cell(114),
        (RESIN, "status"): string("okay"),
        (PM8350C_PWM, "#address-cells"): cell(1),
        (PM8350C_PWM, "#size-cells"): cell(0),
        (PM8350C_PWM, "status"): string("okay"),
    }
    actual_changes: dict[tuple[str, str], bytes | None] = {}
    absent = object()
    for path in sorted(set(base) & set(candidate)):
        before_properties = base[path]
        after_properties = candidate[path]
        for name in sorted(set(before_properties) | set(after_properties)):
            before = before_properties.get(name, absent)
            after = after_properties.get(name, absent)
            if before != after:
                actual_changes[(path, name)] = (
                    None if after is absent else after
                )
    if set(actual_changes) != set(expected_changes):
        fail(
            "candidate changed an unapproved property set: "
            f"changed={sorted(actual_changes)}"
        )
    for key, expected in expected_changes.items():
        if actual_changes[key] != expected:
            fail(f"candidate approved property is wrong: {key[0]}:{key[1]}")

    gpio_phandle = node_phandle(candidate, PM8350_GPIO, "PM8350 GPIO")
    pinctrl_phandle = node_phandle(
        candidate, VOLUME_UP_PINCTRL, "volume-up pinctrl"
    )
    require_exact_properties(
        candidate,
        GPIO_KEYS,
        {
            "compatible": string("gpio-keys"),
            "pinctrl-0": pinctrl_phandle,
            "pinctrl-names": string("default"),
        },
    )
    require_exact_properties(
        candidate,
        VOLUME_UP,
        {
            "debounce-interval": cell(15),
            "gpios": gpio_phandle + cell(6) + cell(1),
            "label": string("volume_up"),
            "linux,can-disable": b"",
            "linux,code": cell(115),
            "linux,input-type": cell(1),
            "wakeup-source": b"",
        },
    )
    require_exact_properties(
        candidate,
        VOLUME_UP_PINCTRL,
        {
            "bias-pull-up": b"",
            "function": string("normal"),
            "input-enable": b"",
            "phandle": pinctrl_phandle,
            "pins": string("gpio6"),
            "power-source": cell(1),
        },
    )
    require_exact_properties(
        candidate,
        GREEN_LED,
        {
            "color": cell(2),
            "default-state": string("off"),
            "function": string("status"),
            "reg": cell(2),
        },
    )
    require_unique_phandles(candidate)
    return len(added_nodes), len(actual_changes)


def parse_arguments(arguments: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("base", type=Path)
    parser.add_argument("candidate", type=Path)
    return parser.parse_args(arguments)


def main(arguments: list[str]) -> int:
    options = parse_arguments(arguments)
    parser = load_dtb_parser()
    base_data = parser.read_dtb_bytes(options.base)
    if len(base_data) != ACCEPTED_BASE_SIZE:
        fail(
            "base DTB size is not the accepted corrected artifact: "
            f"{len(base_data)}"
        )
    digest = sha256(base_data).hexdigest()
    if digest != ACCEPTED_BASE_SHA256:
        fail(f"base DTB hash is not the accepted corrected artifact: {digest}")
    base = parser.parse_dtb(base_data, str(options.base))
    candidate = parser.read_dtb(options.candidate)
    added, changed = compare(base, candidate, parser)
    print(f"base_sha256={digest}")
    print(f"added_nodes={added}")
    print(f"changed_existing_properties={changed}")
    print("PASS exact buttons and green-indicator DTB delta")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv[1:]))
    except (OSError, ValueError) as error:
        print(f"FAIL {error}", file=sys.stderr)
        raise SystemExit(1)
