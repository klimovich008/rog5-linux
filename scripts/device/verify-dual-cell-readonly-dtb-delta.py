#!/usr/bin/env python3
"""Verify the one-property ROG5 read-only dual-cell telemetry DTB delta."""

from __future__ import annotations

import argparse
from hashlib import sha256
import importlib.util
from pathlib import Path
import sys
from types import ModuleType
from typing import NoReturn


ACCEPTED_BASE_SHA256 = (
    "3f4305d7fbbd2c74d15c1011bb8a2e8e24b3a5228f31ed86281917d16cf18f11"
)
ACCEPTED_BASE_SIZE = 102938
PMIC_GLINK = "/pmic-glink"
OPT_IN = "asus,cell-voltage-readonly"
COMPATIBLE = b"qcom,sm8350-pmic-glink\0qcom,pmic-glink\0"


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


def compare(
    base: dict[str, dict[str, bytes]],
    candidate: dict[str, dict[str, bytes]],
    parser: ModuleType,
) -> int:
    parser.require_board_identity(base, "base DTB")
    parser.require_board_identity(candidate, "candidate DTB")

    if set(base) != set(candidate):
        fail(
            "candidate changed the DTB node set: "
            f"added={sorted(set(candidate) - set(base))} "
            f"removed={sorted(set(base) - set(candidate))}"
        )

    if PMIC_GLINK not in base:
        fail("base DTB lacks the accepted PMIC GLINK node")
    if base[PMIC_GLINK].get("compatible") != COMPATIBLE:
        fail("base DTB PMIC GLINK compatible is not accepted")
    if candidate[PMIC_GLINK].get("compatible") != COMPATIBLE:
        fail("candidate changed the PMIC GLINK compatible")
    if OPT_IN in base[PMIC_GLINK]:
        fail("accepted base unexpectedly enables ASUS cell voltages")
    if candidate[PMIC_GLINK].get(OPT_IN) != b"":
        fail("candidate ASUS cell-voltage opt-in is absent or non-empty")

    expected_change = (PMIC_GLINK, OPT_IN)
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
    argument_parser = argparse.ArgumentParser()
    argument_parser.add_argument("base", type=Path)
    argument_parser.add_argument("candidate", type=Path)
    return argument_parser.parse_args()


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
        "PASS read-only dual-cell DTB "
        f"approved_changes={changes} opt_in={PMIC_GLINK}:{OPT_IN}"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError) as error:
        print(f"FAIL {error}", file=sys.stderr)
        raise SystemExit(1)
