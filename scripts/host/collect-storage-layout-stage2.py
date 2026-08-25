#!/usr/bin/env python3
"""Capture the exact sealed Stage-2 clone and native-root result over ACM."""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
from pathlib import Path
import re
import stat
import sys
import time
from typing import NoReturn, Protocol


PREFIX = "ROG5_LAYOUT_STAGE2_V1"
MAX_LINE = 1024
HEX32 = re.compile(r"^[0-9a-f]{32}$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")
UUID = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
)
STAGES = (
    "S00_CONFIG",
    "S10_TOPOLOGY",
    "S20_SOURCE",
    "S30_WATCHDOG_DISARM",
    "S40_CLONE",
    "S50_NATIVE_FILESYSTEM",
    "S60_NATIVE_SEAL",
    "S70_READONLY_VERIFY",
)
SOURCE_SHA256 = "533973be0e0ca76c5db8645fdef9aeb64d20b8c9c98b70124a2561700f119153"
SEAL_SHA256 = "02231e86746fbc656090f52c96d7e0c968c7ca86ba7449c306f611ea20c6a876"
TREE_SHA256 = "4701c23b93624bf894bb76331c165b650c9a2aecb99273a4e6d37c20ac3ef167"


class Stage2ProtocolError(RuntimeError):
    """The target did not emit one exact Stage-2 result."""


class Transport(Protocol):
    def readline(self, maximum: int, timeout: float) -> bytes: ...


def fail(message: str) -> NoReturn:
    raise Stage2ProtocolError(message)


def load_module(filename: str, name: str):
    path = Path(__file__).with_name(filename)
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        fail(f"cannot load {filename}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def parse_line(payload: bytes) -> list[str]:
    if not payload.endswith(b"\n") or payload.count(b"\n") != 1:
        fail("line framing is not exact")
    try:
        line = payload[:-1].decode("ascii")
    except UnicodeDecodeError as error:
        raise Stage2ProtocolError("protocol line is not ASCII") from error
    tokens = line.split(" ")
    if not tokens or tokens[0] != PREFIX or "" in tokens:
        fail("protocol prefix or spacing changed")
    return tokens


def exact_fields(tokens: list[str], names: tuple[str, ...]) -> dict[str, str]:
    if len(tokens) != len(names) + 1:
        fail("protocol field count changed")
    result: dict[str, str] = {}
    for token, expected in zip(tokens[1:], names, strict=True):
        name, separator, value = token.partition("=")
        if separator != "=" or name != expected or not value:
            fail("protocol field order changed")
        result[name] = value
    return result


def prepare_output(path: Path) -> None:
    if not path.is_absolute():
        fail("output path must be absolute")
    if path.exists() or path.is_symlink():
        fail("output path already exists")
    parent = path.parent
    if not parent.is_dir() or parent.is_symlink():
        fail("output parent is unsafe")
    metadata = parent.stat()
    if metadata.st_uid != os.getuid() or stat.S_IMODE(metadata.st_mode) & 0o022:
        fail("output parent ownership or mode is unsafe")
    path.mkdir(mode=0o700)


def capture(
    transport: Transport,
    operation_id: str,
    target_uuid: str,
    timeout: float,
) -> tuple[bytes, bytes]:
    deadline = time.monotonic() + timeout
    transcript = bytearray()
    next_stage = 0
    for _ in range(64):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            fail("Stage-2 terminal deadline expired")
        payload = transport.readline(MAX_LINE, remaining)
        transcript.extend(payload)
        tokens = parse_line(payload)
        status = tokens[1] if len(tokens) > 1 else ""
        if status == "status=RUNNING":
            fields = exact_fields(tokens, ("status", "stage", "reason"))
            if fields["reason"] != "none" or next_stage >= len(STAGES):
                fail("unexpected Stage-2 running record")
            if fields["stage"] != STAGES[next_stage]:
                fail("Stage-2 sequence changed")
            next_stage += 1
            continue
        if status == "status=FAIL":
            fields = exact_fields(
                tokens,
                ("status", "stage", "reason", "target_state", "cleanup", "relock"),
            )
            if fields["stage"] not in STAGES or fields["reason"] == "none":
                fail("Stage-2 failure classification changed")
            if next_stage == 0 or fields["stage"] != STAGES[next_stage - 1]:
                fail("Stage-2 failure stage contradicts progress")
            if fields["target_state"] not in {
                "untouched",
                "partial",
                "cloned",
                "native",
                "final",
            }:
                fail("Stage-2 target-state classification changed")
            if fields["cleanup"] not in {"0", "1"} or fields["relock"] not in {"0", "1"}:
                fail("Stage-2 cleanup classification changed")
            return bytes(transcript), payload
        if status == "status=PASS":
            fields = exact_fields(
                tokens,
                (
                    "status",
                    "stage",
                    "reason",
                    "operation_id",
                    "source_sha256",
                    "target_uuid",
                    "target_blocks",
                    "native_seal_sha256",
                    "tree_sha256",
                    "all_read_only",
                    "block_mounts",
                ),
            )
            expected = {
                "status": "PASS",
                "stage": "S99_COMPLETE",
                "reason": "none",
                "operation_id": operation_id,
                "source_sha256": SOURCE_SHA256,
                "target_uuid": target_uuid,
                "target_blocks": "8388603",
                "native_seal_sha256": SEAL_SHA256,
                "tree_sha256": TREE_SHA256,
                "all_read_only": "1",
                "block_mounts": "0",
            }
            if fields != expected or next_stage != len(STAGES):
                fail("Stage-2 PASS identity or sequence changed")
            return bytes(transcript), payload
        fail("unexpected Stage-2 status")
    fail("Stage-2 record count exceeded its bound")


def parse_arguments(arguments: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--usb-location", required=True)
    parser.add_argument("--operation-id", required=True)
    parser.add_argument("--target-uuid", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--enumeration-timeout", type=int, default=120)
    parser.add_argument("--operation-timeout", type=int, default=900)
    return parser.parse_args(arguments)


def main(arguments: list[str]) -> int:
    options = parse_arguments(arguments)
    if HEX32.fullmatch(options.operation_id) is None:
        fail("operation identity is not canonical")
    if UUID.fullmatch(options.target_uuid) is None:
        fail("target UUID is not canonical")
    for value in (SOURCE_SHA256, SEAL_SHA256, TREE_SHA256):
        if HEX64.fullmatch(value) is None:
            fail("sealed SHA-256 constant is invalid")
    prepare_output(options.output)

    stage1 = load_module("collect-storage-layout-stage1.py", "rog5_stage2_serial")
    preflight = load_module("collect-storage-preflight-report.py", "rog5_stage2_usb")
    identity = preflight.wait_storage_acm(
        options.usb_location, options.enumeration_timeout
    )
    with stage1.RawSerial(identity.path) as transport:
        transcript, terminal = capture(
            transport,
            options.operation_id,
            options.target_uuid,
            options.operation_timeout,
        )
    preflight.revalidate_storage_acm(identity)
    stage1.write_exact(options.output / "transcript.txt", transcript)
    stage1.write_exact(options.output / "terminal.txt", terminal)
    fields = exact_fields(parse_line(terminal), tuple(
        token.partition("=")[0] for token in terminal.decode("ascii").strip().split(" ")[1:]
    ))
    manifest = {
        "format": "rog5-storage-layout-stage2-result-v1",
        "operation_id": options.operation_id,
        "status": fields["status"],
        "target_uuid": options.target_uuid,
        "source_sha256": SOURCE_SHA256,
        "native_seal_sha256": SEAL_SHA256,
        "tree_sha256": TREE_SHA256,
    }
    stage1.write_exact(
        options.output / "manifest.json",
        (json.dumps(manifest, sort_keys=True, separators=(",", ":")) + "\n").encode(
            "ascii"
        ),
    )
    stage1.fsync_directory(options.output)
    stage1.fsync_directory(options.output.parent)
    print(
        f"STORAGE_LAYOUT_STAGE2 status={fields['status']} "
        f"target_uuid={options.target_uuid}"
    )
    return 0 if fields["status"] == "PASS" else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv[1:]))
    except (Stage2ProtocolError, RuntimeError) as error:
        print(f"FAIL {error}", file=sys.stderr)
        raise SystemExit(1)
