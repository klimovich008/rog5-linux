#!/usr/bin/env python3
"""Verify the ROG Phone 5 VCNL36866 vendor, port, and runtime contract."""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
from typing import Any, NoReturn


MAX_FILE_SIZE = 4 * 1024 * 1024
MAX_CONTRACT_SIZE = 256 * 1024


class ContractError(RuntimeError):
    """A fail-closed contract violation."""


def fail(message: str) -> NoReturn:
    raise ContractError(message)


def no_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            fail(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def lexical_absolute(path: Path) -> Path:
    return Path(os.path.abspath(os.fspath(path)))


def read_ordinary(path: Path, limit: int) -> bytes:
    lexical = lexical_absolute(path)
    try:
        metadata = lexical.lstat()
    except FileNotFoundError:
        fail(f"missing source file: {path}")
    if lexical.is_symlink() or not stat.S_ISREG(metadata.st_mode):
        fail(f"unsafe source file: {path}")
    try:
        resolved = lexical.resolve(strict=True)
    except OSError as error:
        fail(f"unsafe source file: {path}: {error}")
    if resolved != lexical or metadata.st_size <= 0 or metadata.st_size > limit:
        fail(f"unsafe source file: {path}")
    flags = os.O_RDONLY | os.O_CLOEXEC | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(lexical, flags)
    try:
        before = os.fstat(descriptor)
        data = os.read(descriptor, limit + 1)
        after = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    if (
        not stat.S_ISREG(before.st_mode)
        or len(data) != before.st_size
        or before.st_dev != after.st_dev
        or before.st_ino != after.st_ino
        or before.st_size != after.st_size
        or before.st_mtime_ns != after.st_mtime_ns
        or before.st_ctime_ns != after.st_ctime_ns
    ):
        fail(f"source file changed while read: {path}")
    return data


def load_contract(path: Path) -> dict[str, Any]:
    try:
        payload = read_ordinary(path, MAX_CONTRACT_SIZE)
        parsed = json.loads(payload, object_pairs_hook=no_duplicates)
    except (UnicodeError, json.JSONDecodeError) as error:
        fail(f"invalid contract JSON: {error}")
    if not isinstance(parsed, dict):
        fail("contract root is not an object")
    validate_contract(parsed)
    return parsed


def require_exact_keys(value: dict[str, Any], expected: set[str], label: str) -> None:
    if set(value) != expected:
        fail(f"{label} fields are not exact")


def require_string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value:
        fail(f"{label} is not a non-empty string")
    return value


def validate_source_entries(
    entries: Any, marker_key: str, *, pinned: bool
) -> list[dict[str, Any]]:
    if not isinstance(entries, list) or not entries:
        fail("source entry list is empty or malformed")
    paths: set[str] = set()
    expected = {"path", marker_key}
    if pinned:
        expected |= {"size", "sha256"}
    for entry in entries:
        if not isinstance(entry, dict):
            fail("source entry is not an object")
        require_exact_keys(entry, expected, "source entry")
        path = require_string(entry["path"], "source path")
        pure = Path(path)
        if pure.is_absolute() or ".." in pure.parts or path in paths:
            fail(f"unsafe or duplicate source path: {path}")
        paths.add(path)
        markers = entry[marker_key]
        if (
            not isinstance(markers, list)
            or not markers
            or any(not isinstance(marker, str) or not marker for marker in markers)
            or len(set(markers)) != len(markers)
        ):
            fail(f"source markers are malformed: {path}")
        if pinned:
            if not isinstance(entry["size"], int) or entry["size"] <= 0:
                fail(f"source size is malformed: {path}")
            digest = entry["sha256"]
            if (
                not isinstance(digest, str)
                or len(digest) != 64
                or any(character not in "0123456789abcdef" for character in digest)
            ):
                fail(f"source hash is malformed: {path}")
    return entries


def validate_contract(contract: dict[str, Any]) -> None:
    require_exact_keys(
        contract,
        {
            "format",
            "state",
            "authority",
            "accepted_upstream",
            "board",
            "protocol",
            "vendor_sources",
            "upstream_gap_sources",
            "candidate_sources",
            "candidate_forbidden_markers",
            "runtime",
        },
        "contract",
    )
    if contract["format"] != "rog5-vcnl36866-port-contract-v1":
        fail("contract format is wrong")
    if contract["state"] != "port-required" or contract["authority"] != "none":
        fail("contract state or authority is wrong")

    upstream = contract["accepted_upstream"]
    if not isinstance(upstream, dict):
        fail("accepted upstream is malformed")
    require_exact_keys(upstream, {"commit", "tree", "release"}, "accepted upstream")
    for field in ("commit", "tree"):
        value = require_string(upstream[field], f"accepted upstream {field}")
        if len(value) != 40 or any(c not in "0123456789abcdef" for c in value):
            fail(f"accepted upstream {field} is malformed")
    if upstream["release"] != "7.1.4":
        fail("accepted upstream release is wrong")

    board = contract["board"]
    if not isinstance(board, dict):
        fail("board contract is malformed")
    require_exact_keys(
        board,
        {
            "revision_chain",
            "controller_label",
            "controller_address",
            "upstream_controller_path",
            "i2c_address",
            "vendor_compatible",
            "candidate_compatible",
            "irq_gpio",
            "irq_trigger",
            "supply",
            "supply_microvolt",
        },
        "board contract",
    )
    expected_chain = [
        "ZS673KS-EVB-overlay.dts",
        "ZS673KS-EVB2-overlay.dts",
        "ZS673KS-SR1-overlay.dts",
        "ZS673KS-ER1-overlay.dts",
        "ZS673KS-ER2-overlay.dts",
        "ZS673KS-PR1-overlay.dts",
        "ZS673KS-MP-overlay.dts",
        "ZS673KS-MP3-overlay.dts",
        "ZS673KS-MP4-overlay.dts",
        "ZS673KS-MP5-overlay.dts",
    ]
    if board["revision_chain"] != expected_chain:
        fail("board revision chain is wrong")
    expected_board = {
        "controller_label": "qupv3_se0_i2c",
        "controller_address": "0x980000",
        "upstream_controller_path": "/soc@0/geniqup@9c0000/i2c@980000",
        "i2c_address": "0x60",
        "vendor_compatible": "qcom,vcnl36866",
        "candidate_compatible": "vishay,vcnl36866",
        "irq_gpio": 89,
        "irq_trigger": "low",
        "supply": "pm8350c_l7",
        "supply_microvolt": 3300000,
    }
    for field, expected in expected_board.items():
        if board[field] != expected:
            fail(f"board field is wrong: {field}")

    protocol = contract["protocol"]
    if not isinstance(protocol, dict):
        fail("protocol contract is malformed")
    expected_protocol = {
        "chip_id_register": "0xf6",
        "chip_id": "0x62",
        "als_data_register": "0xf1",
        "proximity_data_register": "0xf4",
        "register_width_bits": 8,
        "value_width_bits": 16,
        "value_endianness": "little",
        "raw_min": 0,
        "raw_max": 65535,
    }
    require_exact_keys(protocol, set(expected_protocol), "protocol contract")
    if protocol != expected_protocol:
        fail("protocol contract values are wrong")

    vendor = validate_source_entries(
        contract["vendor_sources"], "required_markers", pinned=True
    )
    gap = validate_source_entries(
        contract["upstream_gap_sources"], "required_gap_markers", pinned=True
    )
    candidate = validate_source_entries(
        contract["candidate_sources"], "required_markers", pinned=False
    )
    expected_vendor_paths = {
        "arch/arm64/boot/dts/vendor/qcom/" + name for name in expected_chain
    }
    expected_vendor_paths |= {
        "arch/arm64/boot/dts/vendor/qcom/lahaina-qupv3.dtsi",
        "drivers/sensors/ASH/ASH_Hardware/ASH_Hardware.c",
        "drivers/sensors/ASH/ASH_Hardware/ALSPSsensor_Hardware/ALSPSsensor_Hardware.c",
        "drivers/sensors/ASH/ASH_GPIO/ALSPSsensor_GPIO.c",
        "drivers/sensors/ASH/ASH_Hardware/ALSPSsensor_Hardware/vcnl36866/vcnl36866.c",
        "drivers/sensors/ASH/ASH_Hardware/ALSPSsensor_Hardware/vcnl36866/vcnl36866.h",
    }
    if {entry["path"] for entry in vendor} != expected_vendor_paths:
        fail("vendor source path set is wrong")
    expected_gap_paths = {
        "drivers/iio/light/Kconfig",
        "drivers/iio/light/Makefile",
        "drivers/iio/light/vcnl4000.c",
        "Documentation/devicetree/bindings/iio/light/vishay,vcnl4000.yaml",
    }
    if {entry["path"] for entry in gap} != expected_gap_paths:
        fail("upstream gap source path set is wrong")
    expected_candidate_paths = {
        "drivers/iio/light/Kconfig",
        "drivers/iio/light/Makefile",
        "drivers/iio/light/vcnl36866.c",
        "Documentation/devicetree/bindings/iio/light/vishay,vcnl36866.yaml",
        "dts/qcom/sm8350-asus-rog-phone5-vcnl36866.dtso",
    }
    if {entry["path"] for entry in candidate} != expected_candidate_paths:
        fail("candidate source path set is wrong")
    forbidden = contract["candidate_forbidden_markers"]
    if (
        not isinstance(forbidden, list)
        or not forbidden
        or any(not isinstance(marker, str) or not marker for marker in forbidden)
        or len(set(forbidden)) != len(forbidden)
    ):
        fail("candidate forbidden markers are malformed")

    runtime = contract["runtime"]
    if not isinstance(runtime, dict):
        fail("runtime contract is malformed")
    require_exact_keys(
        runtime,
        {"format", "status", "data_surface_modes", "phone_storage_access", "authority"},
        "runtime contract",
    )
    if runtime != {
        "format": "rog5-vcnl36866-readonly-runtime-v1",
        "status": "observed-not-hardware-accepted",
        "data_surface_modes": {
            "in_illuminance_raw": "0444",
            "in_proximity_raw": "0444",
        },
        "phone_storage_access": "none",
        "authority": "none",
    }:
        fail("runtime contract values are wrong")


def require_root(path: Path) -> Path:
    if not path.is_absolute():
        fail("source root must be an absolute non-linked directory")
    lexical = lexical_absolute(path)
    try:
        metadata = lexical.lstat()
    except FileNotFoundError:
        fail("source root must be an absolute non-linked directory")
    if lexical.is_symlink() or not stat.S_ISDIR(metadata.st_mode):
        fail("source root must be an absolute non-linked directory")
    try:
        resolved = lexical.resolve(strict=True)
    except OSError:
        fail("source root must be an absolute non-linked directory")
    if resolved != lexical:
        fail("source root must be an absolute non-linked directory")
    return lexical


def read_pinned_sources(
    root: Path, entries: list[dict[str, Any]], marker_key: str
) -> dict[str, str]:
    texts: dict[str, str] = {}
    for entry in entries:
        relative = entry["path"]
        data = read_ordinary(root / relative, MAX_FILE_SIZE)
        digest = sha256(data).hexdigest()
        if len(data) != entry["size"] or digest != entry["sha256"]:
            fail(f"pinned source identity changed: {relative}")
        try:
            texts[relative] = data.decode("utf-8")
        except UnicodeDecodeError as error:
            fail(f"source file is not UTF-8: {relative}: {error}")
    return texts


def verify_markers(
    texts: dict[str, str], entries: list[dict[str, Any]], marker_key: str, label: str
) -> None:
    expected_paths = {entry["path"] for entry in entries}
    if set(texts) != expected_paths:
        fail(f"{label} source path set is not exact")
    for entry in entries:
        text = re.sub(r"\s+", " ", texts[entry["path"]]).strip()
        for marker in entry[marker_key]:
            normalized_marker = re.sub(r"\s+", " ", marker).strip()
            if normalized_marker not in text:
                fail(f"{label} source marker is missing: {entry['path']}: {marker}")


def verify_vendor_texts(
    texts: dict[str, str], contract: dict[str, Any]
) -> dict[str, Any]:
    verify_markers(
        texts, contract["vendor_sources"], "required_markers", "vendor"
    )
    prefix = "arch/arm64/boot/dts/vendor/qcom/"
    for successor in contract["board"]["revision_chain"][1:]:
        text = texts[prefix + successor].lower()
        if "vcnl36866" in text:
            fail(f"successor overlay overrides VCNL36866: {successor}")
    return {
        "controller_address": contract["board"]["controller_address"],
        "i2c_address": contract["board"]["i2c_address"],
        "compatible": contract["board"]["vendor_compatible"],
        "irq_gpio": contract["board"]["irq_gpio"],
        "chip_id": contract["protocol"]["chip_id"],
    }


def verify_vendor_source(
    root_path: Path, contract: dict[str, Any]
) -> dict[str, Any]:
    root = require_root(root_path)
    texts = read_pinned_sources(
        root, contract["vendor_sources"], "required_markers"
    )
    return verify_vendor_texts(texts, contract)


def classify_upstream_texts(
    texts: dict[str, str], contract: dict[str, Any]
) -> str:
    gap_entries = contract["upstream_gap_sources"]
    candidate_entries = contract["candidate_sources"]
    gap_paths = {entry["path"] for entry in gap_entries}
    candidate_paths = {entry["path"] for entry in candidate_entries}
    combined = "\n".join(texts.values())

    if set(texts) == gap_paths:
        verify_markers(texts, gap_entries, "required_gap_markers", "upstream gap")
        if "vcnl36866" in combined.lower():
            fail("partial or unreviewed VCNL36866 support")
        return "port-required"

    if set(texts) == candidate_paths:
        try:
            verify_markers(
                texts, candidate_entries, "required_markers", "candidate"
            )
        except ContractError:
            fail("partial or unreviewed VCNL36866 support")
        for marker in contract["candidate_forbidden_markers"]:
            if marker in combined:
                fail("partial or unreviewed VCNL36866 support")
        return "candidate-ready-not-hardware-accepted"

    fail("partial or unreviewed VCNL36866 support")


def git_output(root: Path, *arguments: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(root), *arguments],
        check=False,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if completed.returncode:
        fail(f"git {' '.join(arguments)} failed: {completed.stderr.strip()}")
    return completed.stdout.strip()


def verify_upstream_source(root_path: Path, contract: dict[str, Any]) -> str:
    root = require_root(root_path)
    upstream = contract["accepted_upstream"]
    if git_output(root, "rev-parse", "HEAD") != upstream["commit"]:
        fail("accepted upstream commit changed")
    if git_output(root, "rev-parse", "HEAD^{tree}") != upstream["tree"]:
        fail("accepted upstream tree changed")
    if git_output(root, "status", "--porcelain=v1", "--untracked-files=all"):
        fail("accepted upstream source is dirty")
    texts = read_pinned_sources(
        root, contract["upstream_gap_sources"], "required_gap_markers"
    )
    return classify_upstream_texts(texts, contract)


RUNTIME_FIELDS = {
    "format",
    "status",
    "controller",
    "address",
    "compatible",
    "driver",
    "iio_name",
    "illuminance_raw",
    "proximity_raw",
    "data_surface_modes",
    "control_surfaces",
    "phone_storage_access",
    "authority",
}


def verify_runtime_record(record: dict[str, Any], contract: dict[str, Any]) -> str:
    if not isinstance(record, dict) or set(record) != RUNTIME_FIELDS:
        fail("runtime record fields are not exact")
    expected = {
        "format": contract["runtime"]["format"],
        "status": contract["runtime"]["status"],
        "controller": contract["board"]["upstream_controller_path"],
        "address": contract["board"]["i2c_address"],
        "compatible": contract["board"]["candidate_compatible"],
        "driver": "vcnl36866",
        "iio_name": "vcnl36866",
        "phone_storage_access": contract["runtime"]["phone_storage_access"],
        "authority": contract["runtime"]["authority"],
    }
    for field, value in expected.items():
        if record[field] != value:
            fail(f"runtime field is wrong: {field}")
    lower = contract["protocol"]["raw_min"]
    upper = contract["protocol"]["raw_max"]
    for field in ("illuminance_raw", "proximity_raw"):
        value = record[field]
        if isinstance(value, bool) or not isinstance(value, int) or not lower <= value <= upper:
            fail(f"runtime reading is out of range: {field}")
    modes = record["data_surface_modes"]
    if not isinstance(modes, dict) or set(modes) != set(contract["runtime"]["data_surface_modes"]):
        fail("runtime data surface set is not exact")
    for surface, expected_mode in contract["runtime"]["data_surface_modes"].items():
        if modes[surface] != expected_mode:
            fail(f"runtime data surface is writable: {surface}")
    if record["control_surfaces"] != []:
        fail("runtime control surface is present")
    return record["status"]


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--vendor-source", type=Path, required=True)
    parser.add_argument("--upstream-source", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    arguments = parse_arguments()
    try:
        contract = load_contract(arguments.contract)
        facts = verify_vendor_source(arguments.vendor_source, contract)
        state = verify_upstream_source(arguments.upstream_source, contract)
    except (ContractError, OSError, UnicodeError) as error:
        print(f"FAIL {error}", file=sys.stderr)
        return 1
    print("vendor_oracle=verified")
    print(f"vendor_compatible={facts['compatible']}")
    print(f"controller_address={facts['controller_address']}")
    print(f"upstream_state={state}")
    print("hardware_acceptance=unproven")
    print("authority=none")
    print("PASS exact ROG5 VCNL36866 source and port contract")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
