#!/usr/bin/env python3
"""Capture one exact read-only storage-preflight report over recovery ACM."""

from __future__ import annotations

from collections import OrderedDict
import base64
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import stat
import sys
import time
from typing import NoReturn


REPO = Path(__file__).resolve().parents[2]
CORE_PATH = Path(__file__).with_name("collect-early-target-diagnostics.py")
CORE_SPEC = importlib.util.spec_from_file_location(
    "rog5_storage_preflight_collector_core", CORE_PATH
)
if CORE_SPEC is None or CORE_SPEC.loader is None:
    raise RuntimeError("cannot load the receive-only ACM collector core")
CORE = importlib.util.module_from_spec(CORE_SPEC)
sys.modules[CORE_SPEC.name] = CORE
CORE_SPEC.loader.exec_module(CORE)

FORMAT = "rog5-storage-preflight-evidence-v2"
REJECTED_FORMAT = "rog5-storage-preflight-rejected-evidence-v1"
PREFIX = "ROG5_STORAGE_PREFLIGHT_V2"
RECOVERY_PRODUCT = "ROG5 recovery"
USB_INTERFACE = "02"
MAX_REPORT_BYTES = 2048
ENUMERATION_TIMEOUT_SECONDS = 120
CAPTURE_TIMEOUT_SECONDS = 30
STABLE_ENUMERATION_SECONDS = 0.5

PASS_FIELDS: OrderedDict[str, str | None] = OrderedDict(
    (
        ("status", "PASS"),
        ("stage", "S99_COMPLETE"),
        ("reason", "none"),
        ("logical_block_bytes", "4096"),
        ("lun_bytes", "253403070464"),
        ("gpt_entries", "32"),
        ("userdata_first_lba", "2352680"),
        ("userdata_last_lba", "61865978"),
        ("userdata_blocks", "59513299"),
        ("ext4_blocks", "59513299"),
        ("ext4_minimum_blocks", None),
        ("proposed_userdata_last_lba", "53477375"),
        ("proposed_root_first_lba", "53477376"),
        ("proposed_root_last_lba", "61865978"),
        ("sgdisk", "1.0.10"),
        ("e2fsprogs", "1.47.4"),
        ("all_read_only", "1"),
        ("block_mounts", "0"),
    )
)

SHORT_FIELDS: OrderedDict[str, str | None] = OrderedDict(
    (
        ("status", None),
        ("stage", None),
        ("reason", None),
        ("all_read_only", None),
        ("block_mounts", "0"),
    )
)

RUNNING_STAGES = frozenset(
    (
        "S00_USB_READY",
        "S10_TOPOLOGY",
        "S11_DISK_READ_ONLY",
        "S12_USERDATA_READ_ONLY",
        "S20_TOOLSET",
        "S30_GPT_VERIFY",
        "S40_EXT4_CHECK",
        "S41_EXT4_SUPERBLOCK",
        "S42_EXT4_MINIMUM",
        "S50_GPT_HEADER",
        "S60_TOOL_VERSIONS",
    )
)

FAILURE_STAGE_REASONS = {
    "topology_identity": "S10_TOPOLOGY",
    "disk_not_read_only": "S11_DISK_READ_ONLY",
    "userdata_not_read_only": "S12_USERDATA_READ_ONLY",
    "missing_sgdisk": "S20_TOOLSET",
    "missing_e2fsck": "S20_TOOLSET",
    "missing_resize2fs": "S20_TOOLSET",
    "missing_dumpe2fs": "S20_TOOLSET",
    "missing_mkfs_ext4": "S20_TOOLSET",
    "missing_partprobe": "S20_TOOLSET",
    "gpt_verify_failed": "S30_GPT_VERIFY",
    "e2fsck_failed": "S40_EXT4_CHECK",
    "dumpe2fs_failed": "S41_EXT4_SUPERBLOCK",
    "block_count_changed": "S41_EXT4_SUPERBLOCK",
    "block_size_changed": "S41_EXT4_SUPERBLOCK",
    "filesystem_not_clean": "S41_EXT4_SUPERBLOCK",
    "filesystem_requires_recovery": "S41_EXT4_SUPERBLOCK",
    "resize2fs_failed": "S42_EXT4_MINIMUM",
    "minimum_invalid": "S42_EXT4_MINIMUM",
    "minimum_too_large": "S42_EXT4_MINIMUM",
    "gpt_entry_count_changed": "S50_GPT_HEADER",
    "sgdisk_version_changed": "S60_TOOL_VERSIONS",
    "mkfs_version_failed": "S60_TOOL_VERSIONS",
    "partprobe_failed": "S60_TOOL_VERSIONS",
}


class PreflightError(RuntimeError):
    """The exact storage-preflight report cannot be trusted."""


class RejectedReport(PreflightError):
    """One bounded ACM line failed the exact report grammar."""

    def __init__(self, message: str, payload: bytes) -> None:
        super().__init__(message)
        self.payload = payload


def fail(message: str) -> NoReturn:
    raise PreflightError(message)


def parse_fields(
    tokens: list[str], expected_fields: OrderedDict[str, str | None]
) -> OrderedDict[str, str]:
    if len(tokens) != len(expected_fields):
        fail("storage-preflight report shape is not exact")
    observed: OrderedDict[str, str] = OrderedDict()
    for expected_name, token in zip(expected_fields, tokens, strict=True):
        name, separator, value = token.partition("=")
        if separator != "=" or name != expected_name or not value:
            fail("storage-preflight report field order changed")
        expected = expected_fields[name]
        if expected is not None and value != expected:
            fail(f"storage-preflight {name} identity changed")
        observed[name] = value
    return observed


def parse_report(payload: bytes) -> OrderedDict[str, str]:
    if not payload.endswith(b"\n") or payload.count(b"\n") != 1:
        fail("storage-preflight report framing is not exact")
    try:
        line = payload[:-1].decode("ascii")
    except UnicodeDecodeError as error:
        raise PreflightError("storage-preflight report is not ASCII") from error
    tokens = line.split(" ")
    if not tokens or tokens[0] != PREFIX or "" in tokens:
        fail("storage-preflight report shape is not exact")
    status_token = tokens[1] if len(tokens) > 1 else ""
    if status_token == "status=PASS":
        observed = parse_fields(tokens[1:], PASS_FIELDS)
    elif status_token in ("status=RUNNING", "status=FAIL"):
        observed = parse_fields(tokens[1:], SHORT_FIELDS)
    else:
        fail("storage-preflight status is invalid")

    status = observed["status"]
    stage = observed["stage"]
    reason = observed["reason"]
    if status == "RUNNING":
        if stage not in RUNNING_STAGES or reason != "none":
            fail("storage-preflight running stage/reason is invalid")
        if observed["all_read_only"] != "1":
            fail("storage-preflight running read-only state changed")
    elif status == "FAIL":
        if FAILURE_STAGE_REASONS.get(reason) != stage:
            fail("storage-preflight failure stage/reason is invalid")
        expected_read_only = (
            "0"
            if reason in ("disk_not_read_only", "userdata_not_read_only")
            else "1"
        )
        if observed["all_read_only"] != expected_read_only:
            fail("storage-preflight failure read-only state is invalid")
    else:
        if stage != "S99_COMPLETE" or reason != "none":
            fail("storage-preflight pass stage/reason is invalid")
    if status == "PASS":
        minimum = observed["ext4_minimum_blocks"]
        if (
            not minimum.isascii()
            or not minimum.isdecimal()
            or minimum.startswith("0")
            or not 1 <= int(minimum) <= 51_124_000
        ):
            fail("storage-preflight ext4 minimum is outside policy")
    canonical = PREFIX + " " + " ".join(
        f"{name}={value}" for name, value in observed.items()
    )
    if canonical.encode("ascii") + b"\n" != payload:
        fail("storage-preflight report encoding changed")
    return observed


def storage_product_locations() -> set[str]:
    locations: set[str] = set()
    try:
        entries = sorted(CORE.SYS_BUS_USB.iterdir())
    except OSError as error:
        raise PreflightError("cannot inspect recovery USB inventory") from error
    for entry in entries:
        observed = CORE.usb_ancestor(entry)
        if observed is None:
            continue
        raw, vendor, product_id, product = observed
        if (
            vendor == CORE.USB_VENDOR
            and product_id == CORE.USB_PRODUCT
            and product == RECOVERY_PRODUCT
        ):
            locations.add(raw.relative_to(CORE.SYS_DEVICES).as_posix())
    return locations


def storage_acm_identities() -> list[CORE.AcmIdentity]:
    matches: list[CORE.AcmIdentity] = []
    for device in sorted(CORE.DEV_ROOT.glob("ttyACM*")):
        try:
            metadata = os.stat(device, follow_symlinks=False)
        except OSError:
            continue
        observed = CORE.usb_ancestor(CORE.SYS_CLASS_TTY / device.name)
        if observed is None or not stat.S_ISCHR(metadata.st_mode):
            continue
        raw, vendor, product_id, product = observed
        interface = CORE.usb_interface_identity(
            CORE.SYS_CLASS_TTY / device.name, raw
        )
        if (
            vendor != CORE.USB_VENDOR
            or product_id != CORE.USB_PRODUCT
            or product != RECOVERY_PRODUCT
            or interface != (USB_INTERFACE, CORE.USB_DRIVER)
            or not os.access(device, os.R_OK)
        ):
            continue
        location = raw.relative_to(CORE.SYS_DEVICES).as_posix()
        CORE.validate_location(location)
        matches.append(CORE.AcmIdentity(str(device), location, metadata.st_rdev))
    return matches


def find_storage_acm(expected_location: str) -> CORE.AcmIdentity:
    CORE.validate_location(expected_location)
    products = storage_product_locations()
    matches = storage_acm_identities()
    if len(products) != 1 or len(matches) != 1:
        fail(
            "expected exactly one recovery USB product and ACM interface, "
            f"found products={len(products)} acm={len(matches)}"
        )
    identity = matches[0]
    if products != {identity.location}:
        fail("storage-preflight ACM escaped the exact recovery product")
    if identity.location != expected_location:
        fail("storage preflight enumerated on another physical USB port")
    return identity


def wait_storage_acm(
    expected_location: str, timeout_seconds: int
) -> CORE.AcmIdentity:
    deadline = time.monotonic() + timeout_seconds
    candidate: CORE.AcmIdentity | None = None
    stable_since = 0.0
    while time.monotonic() < deadline:
        try:
            observed = find_storage_acm(expected_location)
        except (CORE.CollectorError, PreflightError, OSError):
            candidate = None
            stable_since = 0.0
        else:
            now = time.monotonic()
            if observed != candidate:
                candidate = observed
                stable_since = now
            elif now - stable_since >= STABLE_ENUMERATION_SECONDS:
                return observed
        time.sleep(0.1)
    fail("exact storage-preflight ACM did not stabilize before its deadline")


def revalidate_storage_acm(identity: CORE.AcmIdentity) -> None:
    if find_storage_acm(identity.location) != identity:
        fail("storage-preflight ACM identity changed during capture")


def capture_report(
    serial: CORE.ReceiveOnlySerial,
    identity: CORE.AcmIdentity,
    timeout_seconds: int,
) -> tuple[bytes, OrderedDict[str, str]]:
    deadline = time.monotonic() + timeout_seconds
    buffer = bytearray()
    terminal_payload: bytes | None = None
    terminal_values: OrderedDict[str, str] | None = None
    last_validation = 0.0
    while time.monotonic() < deadline:
        now = time.monotonic()
        if now - last_validation >= 1.0:
            revalidate_storage_acm(identity)
            last_validation = now
        chunk = serial.read(min(0.25, max(0.0, deadline - now)))
        if chunk == b"":
            fail("storage-preflight ACM disconnected before one terminal report")
        if chunk is None:
            continue
        buffer.extend(chunk)
        while (newline := buffer.find(b"\n")) >= 0:
            payload = bytes(buffer[: newline + 1])
            del buffer[: newline + 1]
            if len(payload) > MAX_REPORT_BYTES:
                fail("storage-preflight report exceeded its byte bound")
            try:
                values = parse_report(payload)
            except PreflightError as error:
                raise RejectedReport(str(error), payload) from error
            if terminal_payload is not None:
                if payload != terminal_payload:
                    fail("storage-preflight terminal repetition changed")
                continue
            if values["status"] == "RUNNING":
                continue
            terminal_payload = payload
            terminal_values = values
        if terminal_payload is not None:
            if buffer and not terminal_payload.startswith(buffer):
                fail("storage-preflight ACM delivered invalid trailing data")
            revalidate_storage_acm(identity)
            if terminal_values is None:
                fail("storage-preflight terminal state is unavailable")
            return terminal_payload, terminal_values
        if len(buffer) > MAX_REPORT_BYTES:
            fail("storage-preflight report exceeded its byte bound")
    fail("storage-preflight terminal report did not arrive before its deadline")


def write_rejected_evidence(
    output_path: Path,
    anchor: OrderedDict[str, str],
    identity: CORE.AcmIdentity,
    started_unix_ns: int,
    rejection: RejectedReport,
) -> None:
    document = {
        "ended_unix_ns": time.time_ns(),
        "error": str(rejection),
        "format": REJECTED_FORMAT,
        "host_boot_id": anchor["host_boot_id"],
        "payload_base64": base64.b64encode(rejection.payload).decode("ascii"),
        "payload_sha256": hashlib.sha256(rejection.payload).hexdigest(),
        "payload_size": len(rejection.payload),
        "started_unix_ns": started_unix_ns,
        "usb_location": identity.location,
    }
    encoded = json.dumps(
        document, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("ascii") + b"\n"
    CORE.write_evidence(output_path, encoded)


def canonical_timeout(value: str, maximum: int) -> int:
    if (
        not value.isascii()
        or not value.isdecimal()
        or value.startswith("0")
        or not 1 <= int(value) <= maximum
    ):
        fail("storage-preflight timeout is outside policy")
    return int(value)


def main(arguments: list[str]) -> int:
    if not 2 <= len(arguments) <= 4:
        fail(
            "usage: collect-storage-preflight-report.py ANCHOR OUTPUT "
            "[ENUMERATION_TIMEOUT] [CAPTURE_TIMEOUT]"
        )
    anchor_path = Path(arguments[0])
    output_path = Path(arguments[1])
    enumeration_timeout = (
        canonical_timeout(arguments[2], 170)
        if len(arguments) >= 3
        else ENUMERATION_TIMEOUT_SECONDS
    )
    capture_timeout = (
        canonical_timeout(arguments[3], 60)
        if len(arguments) == 4
        else CAPTURE_TIMEOUT_SECONDS
    )
    anchor = CORE.read_anchor(anchor_path)
    CORE.safe_new_output(output_path)
    identity = wait_storage_acm(anchor["usb_location"], enumeration_timeout)
    started = time.time_ns()
    try:
        with CORE.ReceiveOnlySerial(identity) as serial:
            payload, values = capture_report(serial, identity, capture_timeout)
    except RejectedReport as error:
        write_rejected_evidence(
            output_path,
            anchor,
            identity,
            started,
            error,
        )
        raise
    if CORE.read_anchor(anchor_path) != anchor:
        fail("recovery anchor changed during storage-preflight capture")
    document = {
        "ended_unix_ns": time.time_ns(),
        "fields": dict(values),
        "format": FORMAT,
        "host_boot_id": anchor["host_boot_id"],
        "report": payload.decode("ascii").rstrip("\n"),
        "started_unix_ns": started,
        "usb_location": anchor["usb_location"],
    }
    encoded = json.dumps(
        document, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("ascii") + b"\n"
    CORE.write_evidence(output_path, encoded)
    if values["status"] == "PASS":
        print(
            "PASS exact read-only storage preflight report captured "
            f"ext4_minimum_blocks={values['ext4_minimum_blocks']}"
        )
    else:
        print(
            "FAIL exact read-only storage preflight failure captured "
            f"stage={values['stage']} reason={values['reason']}"
        )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv[1:]))
    except (CORE.CollectorError, OSError, PreflightError, ValueError) as error:
        print(f"FAIL {error}", file=sys.stderr)
        raise SystemExit(1)
