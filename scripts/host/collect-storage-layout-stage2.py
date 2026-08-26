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
from typing import Callable, NoReturn, Protocol


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
    result_profile: str = "clone",
    on_record: Callable[[bytes], None] | None = None,
) -> tuple[bytes, bytes]:
    deadline = time.monotonic() + timeout
    transcript = bytearray()
    stages = STAGES if result_profile == "clone" else STAGES[:2]
    next_stage = 0
    guards_seen = result_profile == "clone"
    partition_seen = result_profile == "clone"
    signature_seen = False
    for _ in range(64):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            fail("Stage-2 terminal deadline expired")
        payload = transport.readline(MAX_LINE, remaining)
        transcript.extend(payload)
        tokens = parse_line(payload)
        status = tokens[1] if len(tokens) > 1 else ""
        if status == "status=GUARDS":
            if result_profile != "preflight" or guards_seen or next_stage != 1:
                fail("unexpected Stage-2 guard record")
            fields = exact_fields(
                tokens,
                (
                    "status",
                    "discovery",
                    "isolation",
                    "power",
                    "inventory",
                    "auto_markers",
                    "host_markers",
                    "wlun_markers",
                    "blocked_queries",
                    "blocked_scsi",
                    "wrapper_physical_count",
                ),
            )
            if (
                any(fields[name] not in {"pass", "fail"} for name in (
                    "discovery", "isolation", "inventory"
                ))
                or fields["power"] not in {"pass", "fail", "unsupported"}
                or any(
                re.fullmatch(r"[0-9]{1,6}", fields[name]) is None
                for name in (
                    "auto_markers", "host_markers", "wlun_markers",
                    "blocked_queries", "blocked_scsi", "wrapper_physical_count",
                )
                )
            ):
                fail("Stage-2 guard classification changed")
            if on_record is not None:
                on_record(payload)
            guards_seen = True
            continue
        if status == "status=PARTITION":
            if result_profile != "preflight" or partition_seen or next_stage != 2:
                fail("unexpected Stage-2 partition record")
            fields = exact_fields(
                tokens,
                (
                    "status", "number", "read", "first", "last", "type",
                    "unique", "name", "attrs",
                ),
            )
            if fields["number"] != "24" or fields["read"] not in {"pass", "fail"}:
                fail("Stage-2 partition classification changed")
            if fields["read"] == "pass":
                if (
                    re.fullmatch(r"[0-9]{1,12}", fields["first"]) is None
                    or re.fullmatch(r"[0-9]{1,12}", fields["last"]) is None
                    or UUID.fullmatch(fields["type"]) is None
                    or UUID.fullmatch(fields["unique"]) is None
                    or re.fullmatch(r"[A-Za-z0-9._-]{1,36}", fields["name"]) is None
                    or re.fullmatch(r"[0-9a-f]{16}", fields["attrs"]) is None
                ):
                    fail("Stage-2 partition classification changed")
            elif any(fields[name] != "invalid" for name in (
                "first", "last", "type", "unique", "name", "attrs"
            )):
                fail("Stage-2 partition classification changed")
            if on_record is not None:
                on_record(payload)
            partition_seen = True
            continue
        if status == "status=SIGNATURE":
            if result_profile != "preflight" or signature_seen or not partition_seen:
                fail("unexpected Stage-2 signature record")
            fields = exact_fields(
                tokens,
                ("status", "type", "uuid", "label", "bytes", "sha256"),
            )
            if (
                re.fullmatch(r"[A-Za-z0-9._+-]{1,32}|invalid", fields["type"])
                is None
                or fields["uuid"] not in {"present", "absent"}
                or fields["label"] not in {"present", "absent"}
                or re.fullmatch(r"[1-9][0-9]{0,3}", fields["bytes"]) is None
                or HEX64.fullmatch(fields["sha256"]) is None
            ):
                fail("Stage-2 signature classification changed")
            if on_record is not None:
                on_record(payload)
            signature_seen = True
            continue
        if status == "status=RUNNING":
            fields = exact_fields(tokens, ("status", "stage", "reason"))
            if fields["reason"] != "none" or next_stage >= len(stages):
                fail("unexpected Stage-2 running record")
            if fields["stage"] != stages[next_stage]:
                fail("Stage-2 sequence changed")
            if on_record is not None:
                on_record(payload)
            next_stage += 1
            continue
        if status == "status=FAIL":
            fields = exact_fields(
                tokens,
                ("status", "stage", "reason", "target_state", "cleanup", "relock"),
            )
            if fields["stage"] not in stages or fields["reason"] == "none":
                fail("Stage-2 failure classification changed")
            if next_stage == 0 or fields["stage"] != stages[next_stage - 1]:
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
            if on_record is not None:
                on_record(payload)
            return bytes(transcript), payload
        if status == "status=PASS":
            if result_profile == "preflight":
                fields = exact_fields(
                    tokens,
                    (
                        "status",
                        "stage",
                        "reason",
                        "operation_id",
                        "wrapper_physical_count",
                        "userdata_uuid",
                        "userdata_blocks",
                        "arch_root_guid",
                        "arch_root_empty",
                        "all_read_only",
                        "block_mounts",
                    ),
                )
                wrapper_count = fields["wrapper_physical_count"]
                if re.fullmatch(r"[1-9][0-9]{0,2}", wrapper_count) is None:
                    fail("Stage-2 preflight wrapper count is invalid")
                expected = {
                    "status": "PASS",
                    "stage": "S99_COMPLETE",
                    "reason": "none",
                    "operation_id": operation_id,
                    "wrapper_physical_count": wrapper_count,
                    "userdata_uuid": "0892bacf-3e02-41b0-84a4-5f05c2df7ce5",
                    "userdata_blocks": "51124000",
                    "arch_root_guid": "60f49e17-bdc6-46bf-8d47-8a24907024c9",
                    "arch_root_empty": "1",
                    "all_read_only": "1",
                    "block_mounts": "0",
                }
                if (
                    fields != expected
                    or next_stage != len(stages)
                    or not guards_seen
                    or not partition_seen
                ):
                    fail("Stage-2 preflight PASS identity or sequence changed")
                if on_record is not None:
                    on_record(payload)
                return bytes(transcript), payload
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
            if fields != expected or next_stage != len(stages):
                fail("Stage-2 PASS identity or sequence changed")
            if on_record is not None:
                on_record(payload)
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
    parser.add_argument(
        "--result-profile", choices=("clone", "preflight"), default="clone"
    )
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

    partial_path = options.output / "transcript.partial"
    partial_fd = os.open(
        partial_path,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC | os.O_NOFOLLOW,
        0o600,
    )
    output_fd = os.open(
        options.output,
        os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC | os.O_NOFOLLOW,
    )
    try:
        os.fsync(output_fd)
    finally:
        os.close(output_fd)
    retained = bytearray()

    def retain_record(payload: bytes) -> None:
        view = memoryview(payload)
        while view:
            written = os.write(partial_fd, view)
            if written < 1:
                fail("Stage-2 partial transcript write made no progress")
            view = view[written:]
        os.fsync(partial_fd)
        retained.extend(payload)

    try:
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
                options.result_profile,
                retain_record,
            )
    finally:
        os.close(partial_fd)
    if transcript != bytes(retained):
        fail("Stage-2 durable transcript differs from accepted records")
    preflight.revalidate_storage_acm(identity)
    partial_path.rename(options.output / "transcript.txt")
    stage1.fsync_directory(options.output)
    stage1.write_exact(options.output / "terminal.txt", terminal)
    fields = exact_fields(parse_line(terminal), tuple(
        token.partition("=")[0] for token in terminal.decode("ascii").strip().split(" ")[1:]
    ))
    manifest = {
        "format": f"rog5-storage-layout-stage2-{options.result_profile}-result-v1",
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
