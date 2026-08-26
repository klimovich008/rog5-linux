#!/usr/bin/env python3
"""Capture one Stage-1 prewrite verdict without sending any phone bytes."""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
from pathlib import Path
import stat
import sys
import time
from typing import NoReturn, Protocol


REPO = Path(__file__).resolve().parents[2]
STAGES = ("S00_CONFIG", "S10_TOPOLOGY", "S20_PROTECTED_SEAL", "S30_FRESH_BACKUP")
MAX_LINES = 32


def load_module(name: str, filename: str):
    path = Path(__file__).with_name(filename)
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {filename}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


STAGE1 = load_module("rog5_stage1_observer_protocol", "collect-storage-layout-stage1.py")
PREFLIGHT = load_module("rog5_stage1_observer_usb", "collect-storage-preflight-report.py")


class ReadTransport(Protocol):
    def readline(self, maximum: int, timeout: float) -> bytes: ...


class ObservationError(RuntimeError):
    pass


def fail(message: str) -> NoReturn:
    raise ObservationError(message)


def observe(transport: ReadTransport, timeout: int) -> dict[str, object]:
    deadline = time.monotonic() + timeout
    lines: list[str] = []
    stages: list[str] = []
    last_index = -1
    for _ in range(MAX_LINES):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            fail("prewrite observation deadline expired")
        payload = transport.readline(STAGE1.MAX_LINE, remaining)
        tokens = STAGE1.ascii_line(payload)
        status = tokens[1] if len(tokens) > 1 else ""
        line = payload.decode("ascii").rstrip("\n")
        lines.append(line)
        if status == "status=RUNNING":
            fields = STAGE1.exact_fields(tokens, ("status", "stage", "reason"))
            if fields["reason"] != "none" or fields["stage"] not in STAGES:
                fail("prewrite running state changed")
            index = STAGES.index(fields["stage"])
            if index < last_index or index > last_index + 1:
                fail("prewrite stage order changed")
            if index > last_index:
                stages.append(fields["stage"])
                last_index = index
            if fields["stage"] == "S30_FRESH_BACKUP":
                return {
                    "format": "rog5-storage-layout-stage1-prewrite-observation-v1",
                    "lines": lines,
                    "outcome": "REACHED_S30_NO_HOST_BYTES_SENT",
                    "stages": stages,
                    "terminal": None,
                }
            continue
        if status == "status=FAIL":
            fields = STAGE1.exact_fields(
                tokens, ("status", "stage", "reason", "gpt_restored")
            )
            if (
                fields["stage"] not in STAGES[:-1]
                or fields["reason"] == "none"
                or fields["gpt_restored"] != "not_needed"
            ):
                fail("prewrite terminal classification changed")
            return {
                "format": "rog5-storage-layout-stage1-prewrite-observation-v1",
                "lines": lines,
                "outcome": "TARGET_FAIL_BEFORE_S30",
                "stages": stages,
                "terminal": fields,
            }
        fail("unexpected prewrite protocol status")
    fail("prewrite observation exceeded its line bound")


def safe_output(path: Path) -> None:
    if not path.is_absolute() or path.name in {"", ".", ".."}:
        fail("prewrite output must be one absolute file")
    try:
        parent = path.parent.resolve(strict=True)
        metadata = parent.lstat()
    except OSError as error:
        raise ObservationError("prewrite output parent is unavailable") from error
    try:
        path.relative_to(REPO)
    except ValueError:
        pass
    else:
        fail("prewrite output must remain outside the repository")
    if (
        parent != path.parent
        or not stat.S_ISDIR(metadata.st_mode)
        or metadata.st_uid != os.geteuid()
        or stat.S_IMODE(metadata.st_mode) != 0o700
        or os.path.lexists(path)
    ):
        fail("prewrite output metadata is unsafe")


def classify_post_capture(identity) -> str:
    try:
        PREFLIGHT.revalidate_storage_acm(identity)
    except (PREFLIGHT.PreflightError, PREFLIGHT.CORE.CollectorError, OSError):
        products = PREFLIGHT.storage_product_locations()
        interfaces = PREFLIGHT.storage_acm_identities()
        if not products and not interfaces:
            return "DEPARTED"
        return "CHANGED"
    return "PRESENT"


def main(arguments: list[str]) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--usb-location", required=True)
    parser.add_argument("--operation-id", required=True)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--enumeration-timeout", type=int, default=60)
    parser.add_argument("--capture-timeout", type=int, default=60)
    options = parser.parse_args(arguments)
    STAGE1.validate_operation(options.operation_id)
    if not 1 <= options.enumeration_timeout <= 120 or not 1 <= options.capture_timeout <= 120:
        fail("prewrite timeout is outside policy")
    safe_output(options.output)
    identity = PREFLIGHT.wait_storage_acm(
        options.usb_location, options.enumeration_timeout
    )
    started = time.time_ns()
    with STAGE1.RawSerial(identity.path) as transport:
        result = observe(transport, options.capture_timeout)
    post_identity = classify_post_capture(identity)
    result.update(
        {
            "ended_unix_ns": time.time_ns(),
            "operation_id": options.operation_id,
            "post_capture_identity": post_identity,
            "started_unix_ns": started,
            "usb_location": identity.location,
        }
    )
    payload = (
        json.dumps(result, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode("ascii")
    STAGE1.write_exact(options.output, payload)
    STAGE1.fsync_directory(options.output.parent)
    if post_identity == "CHANGED":
        fail("validated prewrite evidence retained after USB identity changed")
    print(f"PASS Stage-1 receive-only prewrite outcome={result['outcome']}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv[1:]))
    except (ObservationError, STAGE1.LayoutProtocolError, OSError, ValueError) as error:
        print(f"FAIL {error}", file=sys.stderr)
        raise SystemExit(1)
