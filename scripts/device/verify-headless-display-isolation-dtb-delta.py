#!/usr/bin/env python3
"""Verify the one-property ROG5 headless display-isolation DTB delta."""

from __future__ import annotations

import argparse
from hashlib import sha256
import importlib.util
from pathlib import Path
import sys
from types import ModuleType
from typing import NoReturn


ACCEPTED_BASE_SHA256 = (
    "86e5cb81191e3de39c9527b838fa03d78744cd9b0d862336f0c1f36a9f534f46"
)
ACCEPTED_BASE_SIZE = 102870

MDSS = "/soc@0/display-subsystem@ae00000"
DPU = f"{MDSS}/display-controller@ae01000"
DP = f"{MDSS}/displayport-controller@ae90000"
DSI0 = f"{MDSS}/dsi@ae94000"
DSI0_PHY = f"{MDSS}/phy@ae94400"
DSI1 = f"{MDSS}/dsi@ae96000"
DSI1_PHY = f"{MDSS}/phy@ae96400"
DISPCC = "/soc@0/clock-controller@af00000"
DISABLED = b"disabled\0"


def fail(message: str) -> NoReturn:
    raise ValueError(message)


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


def require_disabled(
    nodes: dict[str, dict[str, bytes]], path: str, label: str, tree: str
) -> None:
    properties = nodes.get(path)
    if properties is None:
        fail(f"{tree} lacks headless display provider: {label}")
    if properties.get("status") != DISABLED:
        fail(f"{tree} headless display provider is not disabled: {label}")


def require_no_panel_provider(
    nodes: dict[str, dict[str, bytes]], tree: str
) -> None:
    for path, properties in nodes.items():
        name = path.rsplit("/", 1)[-1].lower()
        compatible = properties.get("compatible", b"").lower()
        if (
            name == "panel"
            or name.startswith("panel@")
            or "backlight" in name
            or "framebuffer" in name
            or b"simple-framebuffer\0" in compatible
        ):
            fail(f"{tree} contains a panel/backlight/framebuffer provider: {path}")


def compare(
    base: dict[str, dict[str, bytes]],
    candidate: dict[str, dict[str, bytes]],
    parser: ModuleType,
) -> int:
    parser.require_board_identity(base, "base DTB")
    parser.require_board_identity(candidate, "candidate DTB")

    # The DPU child is intentionally status-less under the disabled MDSS
    # parent.  Require that exact topology instead of pretending it is an
    # independently active provider.
    if DPU not in base or DPU not in candidate:
        fail("headless display topology lacks the DPU child")
    for nodes, tree in ((base, "base"), (candidate, "candidate")):
        for path, label in (
            (MDSS, "mdss"),
            (DP, "displayport"),
            (DSI0, "dsi0"),
            (DSI0_PHY, "dsi0-phy"),
            (DSI1, "dsi1"),
            (DSI1_PHY, "dsi1-phy"),
        ):
            require_disabled(nodes, path, label, tree)
        require_no_panel_provider(nodes, tree)
    require_disabled(candidate, DISPCC, "dispcc", "candidate")

    if DISPCC not in base:
        fail("base DTB lacks DISPCC")
    if "status" in base[DISPCC]:
        fail("accepted base unexpectedly has an explicit DISPCC status")

    if set(base) != set(candidate):
        fail(
            "candidate changed the DTB node set: "
            f"added={sorted(set(candidate) - set(base))} "
            f"removed={sorted(set(base) - set(candidate))}"
        )

    expected_change = (DISPCC, "status")
    actual_changes: list[tuple[str, str]] = []
    absent = object()
    for path in sorted(base):
        before_properties = base[path]
        after_properties = candidate[path]
        for name in sorted(set(before_properties) | set(after_properties)):
            before = before_properties.get(name, absent)
            after = after_properties.get(name, absent)
            if before == after:
                continue
            if (path, name) != expected_change:
                fail(f"candidate changed an unapproved property: {path}:{name}")
            actual_changes.append((path, name))
    if actual_changes != [expected_change]:
        fail(f"candidate changed the wrong property set: {actual_changes}")
    return len(actual_changes)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("base", type=Path)
    parser.add_argument("candidate", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    parser = load_dtb_parser()
    base_bytes = parser.read_dtb_bytes(args.base)
    if (
        len(base_bytes) != ACCEPTED_BASE_SIZE
        or sha256(base_bytes).hexdigest() != ACCEPTED_BASE_SHA256
    ):
        fail(f"base DTB identity is not accepted: {args.base}")
    base = parser.parse_dtb(base_bytes, str(args.base))
    candidate = parser.read_dtb(args.candidate)
    changes = compare(base, candidate, parser)
    print(
        "PASS headless display-isolation DTB "
        f"approved_changes={changes} dispcc=disabled"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError) as error:
        print(f"FAIL {error}", file=sys.stderr)
        raise SystemExit(1)
