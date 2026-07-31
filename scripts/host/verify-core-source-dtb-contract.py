#!/usr/bin/env python3
"""Verify ROG5 core kernel-source integration and corrected DTB semantics."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import stat
import struct
import subprocess
import sys
from types import ModuleType
from typing import Any, NoReturn


REPO = Path(__file__).resolve().parents[2]
DEFAULT_PROFILE = Path(
    "configs/compatibility/rog5-core-source-dtb-v1.json"
)
FORMAT = "rog5-core-source-dtb-contract-v1"
SHA256 = re.compile(r"[0-9a-f]{64}")
GIT_COMMIT = re.compile(r"[0-9a-f]{40}")
IDENTIFIER = re.compile(r"[a-z0-9][a-z0-9-]*")
KCONFIG_SYMBOL = re.compile(r"[A-Z0-9_]+")
MAKEFILE_REQUIREMENT = re.compile(
    r"(CONFIG_[A-Z0-9_]+):([A-Za-z0-9_.+-]+[.]o)"
)
COMPATIBLE = re.compile(r"[A-Za-z0-9][A-Za-z0-9,._+-]*")
PROPERTY = re.compile(r"[#A-Za-z0-9][#A-Za-z0-9,._+-]*")
MAX_PROFILE_SIZE = 1024 * 1024
MAX_SOURCE_SIZE = 8 * 1024 * 1024

EXPECTED_ACTIVE = (
    "cpu-ram",
    "read-only-network-root",
    "usb-ncm-network",
    "init-key-only-ssh",
    "watchdog-rollback-reboot",
    "thermal-readonly",
)
EXPECTED_DTB_REQUIRED = (
    "cpu-ram",
    "read-only-network-root",
    "usb-ncm-network",
    "watchdog-rollback-reboot",
    "thermal-readonly",
)
EXPECTED_FORBIDDEN_ENABLED = (
    "qcom,sm8350-ufshc",
    "qcom,ufshc",
    "jedec,ufs-2.0",
    "qcom,sm8350-qmp-ufs-phy",
    "qcom,sm8350-qmp-usb3-dp-phy",
    "qcom,sm8350-qmp-usb3-uni-phy",
    "qcom,sm8350-qmp-usb3-phy",
)
ROOT_KEYS = {
    "format",
    "profile",
    "compatibility_profile",
    "baseline_source",
    "accepted_dtb",
    "active_capabilities",
    "dt_required_capabilities",
    "forbidden_enabled_compatibles",
    "thermal_policy",
    "source_checks",
    "dt_checks",
}
COMPATIBILITY_KEYS = {"path", "sha256"}
BASELINE_KEYS = {"commit", "release"}
ACCEPTED_DTB_KEYS = {"artifact_id", "path", "size", "sha256"}
SOURCE_CHECK_KEYS = {"id", "capabilities", "kind", "path", "required"}
DT_CHECK_KEYS = {
    "id",
    "capabilities",
    "path",
    "status",
    "compatible",
    "string_properties",
    "u32_properties",
    "present_properties",
}
DT_CHECK_OPTIONAL_KEYS = {
    "phandle_properties",
    "phandle_args_properties",
}
PHANDLE_ARGS_CELL_PROPERTIES = {
    "clocks": "#clock-cells",
    "qcom,freq-domain": "#freq-domain-cells",
}
PHANDLE_ARGS_KEYS = {"target", "args"}
EXPECTED_COMPATIBLE_ABSENT = {"cpu-container", "memory-banks"}
EXPECTED_CPU_NODE_PATHS = {
    "/cpus/cpu@0",
    "/cpus/cpu@100",
    "/cpus/cpu@200",
    "/cpus/cpu@300",
    "/cpus/cpu@400",
    "/cpus/cpu@500",
    "/cpus/cpu@600",
    "/cpus/cpu@700",
}
EXPECTED_MEMORY_NODE_PATHS = {"/memory@80000000"}
SOURCE_KINDS = {"kconfig", "makefile", "of-match", "binding", "source"}
NORMALIZED_SOURCE_CHECKS = {
    "thermal-tsens-critical-source",
    "thermal-tsens-v2-feature-source",
    "thermal-hw-protection-source",
}
THERMAL_NO_LIMIT = 0xFFFFFFFF
EXPECTED_THERMAL_POLICY = {
    "pdc_path": "/soc@0/interrupt-controller@b220000",
    "pdc_parent_path": "/soc@0/interrupt-controller@17a00000",
    "sensor_controllers": [
        {
            "path": "/soc@0/thermal-sensor@c263000",
            "sensor_count": 15,
            "interrupt_args": [[26, 4], [28, 4]],
        },
        {
            "path": "/soc@0/thermal-sensor@c265000",
            "sensor_count": 14,
            "interrupt_args": [[27, 4], [29, 4]],
        },
    ],
    "cpu_zone_groups": [
        {
            "zone_names": [
                "cpu0-thermal",
                "cpu1-thermal",
                "cpu2-thermal",
                "cpu3-thermal",
            ],
            "sensor_path": "/soc@0/thermal-sensor@c263000",
            "sensor_indexes": [1, 2, 3, 4],
            "cooling_cpu_paths": [
                "/cpus/cpu@0",
                "/cpus/cpu@100",
                "/cpus/cpu@200",
                "/cpus/cpu@300",
            ],
        },
        {
            "zone_names": [
                "cpu4-top-thermal",
                "cpu5-top-thermal",
                "cpu6-top-thermal",
                "cpu7-top-thermal",
                "cpu4-bottom-thermal",
                "cpu5-bottom-thermal",
                "cpu6-bottom-thermal",
                "cpu7-bottom-thermal",
            ],
            "sensor_path": "/soc@0/thermal-sensor@c263000",
            "sensor_indexes": [7, 8, 9, 10, 11, 12, 13, 14],
            "cooling_cpu_paths": [
                "/cpus/cpu@400",
                "/cpus/cpu@500",
                "/cpus/cpu@600",
                "/cpus/cpu@700",
            ],
        },
    ],
    "polling_delay_passive_ms": 250,
    "passive_trip_millicelsius": [90000, 95000],
    "passive_hysteresis_millicelsius": 2000,
    "critical_trip_millicelsius": 110000,
    "critical_hysteresis_millicelsius": 1000,
    "pmic_polling_delay_passive_ms": 100,
    "pmic_passive_trip_millicelsius": 95000,
    "pmic_critical_trip_millicelsius": 115000,
    "pmic_temp_alarms": [
        {
            "alarm_path": (
                "/soc@0/spmi@c440000/pmic@1/temp-alarm@a00"
            ),
            "sid": 1,
            "zone_name": "pm8350-thermal",
            "critical_trip_name": "pm8350c-crit",
        },
        {
            "alarm_path": (
                "/soc@0/spmi@c440000/pmic@2/temp-alarm@a00"
            ),
            "sid": 2,
            "zone_name": "pm8350c-thermal",
            "critical_trip_name": "pm8350c-crit",
        },
        {
            "alarm_path": (
                "/soc@0/spmi@c440000/pmic@3/temp-alarm@a00"
            ),
            "sid": 3,
            "zone_name": "pm8350b-thermal",
            "critical_trip_name": "pm8350c-crit",
        },
        {
            "alarm_path": (
                "/soc@0/spmi@c440000/pmic@4/temp-alarm@a00"
            ),
            "sid": 4,
            "zone_name": "pmr735a-thermal",
            "critical_trip_name": "pmr735a-crit",
        },
        {
            "alarm_path": (
                "/soc@0/spmi@c440000/pmic@5/temp-alarm@a00"
            ),
            "sid": 5,
            "zone_name": "pmr735b-thermal",
            "critical_trip_name": "pmr735a-crit",
        },
    ],
}


def fail(message: str) -> NoReturn:
    raise ValueError(message)


def unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            fail(f"duplicate JSON field: {key}")
        result[key] = value
    return result


def require_object(value: Any, keys: set[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != keys:
        fail(f"{label} is not canonical")
    return value


def require_string(value: Any, label: str) -> str:
    if (
        not isinstance(value, str)
        or not value
        or value != value.strip()
        or any(ord(character) < 0x20 or ord(character) == 0x7F for character in value)
    ):
        fail(f"{label} is not a canonical nonempty string")
    return value


def require_sha256(value: Any, label: str) -> str:
    text = require_string(value, label)
    if not SHA256.fullmatch(text):
        fail(f"{label} is not a lowercase SHA-256")
    return text


def require_git_commit(value: Any, label: str) -> str:
    text = require_string(value, label)
    if not GIT_COMMIT.fullmatch(text):
        fail(f"{label} is not a lowercase full Git commit")
    return text


def require_string_list(
    value: Any,
    label: str,
    *,
    allow_empty: bool = False,
) -> list[str]:
    if not isinstance(value, list) or (not value and not allow_empty):
        fail(f"{label} is not a canonical string list")
    result: list[str] = []
    seen: set[str] = set()
    for index, raw in enumerate(value):
        text = require_string(raw, f"{label}[{index}]")
        if text in seen:
            fail(f"{label} contains a duplicate value: {text}")
        seen.add(text)
        result.append(text)
    return result


def safe_input_file(path: Path, label: str, maximum: int) -> Path:
    lexical = Path(os.path.abspath(path.expanduser()))
    if lexical.is_symlink():
        fail(f"{label} is linked")
    resolved = lexical.resolve(strict=True)
    if lexical != resolved:
        fail(f"{label} contains a linked path component")
    if not resolved.is_file() or resolved.is_symlink():
        fail(f"{label} is not an ordinary file")
    size = resolved.stat().st_size
    if size <= 0 or size > maximum:
        fail(f"{label} has an invalid size")
    return resolved


def read_bounded(path: Path, label: str, maximum: int) -> bytes:
    resolved = safe_input_file(path, label, maximum)
    descriptor = os.open(
        resolved,
        os.O_RDONLY | os.O_CLOEXEC | getattr(os, "O_NOFOLLOW", 0),
    )
    try:
        before = os.fstat(descriptor)
        if (
            not stat.S_ISREG(before.st_mode)
            or before.st_size <= 0
            or before.st_size > maximum
        ):
            fail(f"{label} has an invalid size")
        with os.fdopen(descriptor, "rb", closefd=False) as stream:
            data = stream.read(maximum + 1)
        after = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    if (
        len(data) != before.st_size
        or before.st_dev != after.st_dev
        or before.st_ino != after.st_ino
        or before.st_size != after.st_size
        or before.st_mtime_ns != after.st_mtime_ns
        or before.st_ctime_ns != after.st_ctime_ns
    ):
        fail(f"{label} changed while it was read")
    return data


def read_json(path: Path, label: str) -> dict[str, Any]:
    value = json.loads(
        read_bounded(path, label, MAX_PROFILE_SIZE),
        object_pairs_hook=unique_object,
    )
    if not isinstance(value, dict):
        fail(f"{label} root is not an object")
    return value


def safe_relative_path(value: Any, label: str) -> str:
    text = require_string(value, label)
    path = Path(text)
    if (
        path.is_absolute()
        or not path.parts
        or any(part in {"", ".", ".."} for part in path.parts)
    ):
        fail(f"{label} is unsafe")
    return text


def repository_file(repo: Path, value: Any, label: str) -> tuple[str, Path]:
    text = safe_relative_path(value, label)
    lexical = repo / text
    resolved = safe_input_file(lexical, label, MAX_PROFILE_SIZE)
    if lexical.absolute() != resolved:
        fail(f"{label} escapes the repository")
    return text, resolved


def load_module(path: Path, name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        fail(f"cannot load verifier module: {path.name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def validate_core_profile(
    repo: Path,
    contract: dict[str, Any],
) -> dict[str, Any]:
    reference = require_object(
        contract["compatibility_profile"],
        COMPATIBILITY_KEYS,
        "compatibility_profile",
    )
    _path_text, path = repository_file(
        repo,
        reference["path"],
        "compatibility profile path",
    )
    expected_hash = require_sha256(
        reference["sha256"],
        "compatibility profile sha256",
    )
    data = read_bounded(path, "compatibility profile", MAX_PROFILE_SIZE)
    if hashlib.sha256(data).hexdigest() != expected_hash:
        fail("compatibility profile hash changed")
    core_profile = json.loads(data, object_pairs_hook=unique_object)
    if not isinstance(core_profile, dict):
        fail("compatibility profile root is not an object")
    core = load_module(
        repo / "scripts/host/verify-core-compatibility-oracle.py",
        "rog5_core_compatibility_oracle",
    )
    active, future, config_status = core.validate_profile(
        repo,
        core_profile,
        None,
        False,
    )
    if (active, future, config_status) != (6, 8, "metadata-only"):
        fail("compatibility profile result changed")
    return core_profile


def active_core_capabilities(core_profile: dict[str, Any]) -> tuple[str, ...]:
    rows = core_profile.get("capabilities")
    if not isinstance(rows, list):
        fail("compatibility capability inventory is malformed")
    result: list[str] = []
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            fail(f"compatibility capability {index} is malformed")
        if row.get("phase") == "active":
            result.append(
                require_string(
                    row.get("id"),
                    f"compatibility capability {index} id",
                )
            )
    return tuple(result)


def validate_accepted_dtb_link(
    contract: dict[str, Any],
    core_profile: dict[str, Any],
) -> None:
    accepted = require_object(
        contract["accepted_dtb"],
        ACCEPTED_DTB_KEYS,
        "accepted_dtb",
    )
    artifact_id = require_string(
        accepted["artifact_id"],
        "accepted_dtb artifact_id",
    )
    path = safe_relative_path(accepted["path"], "accepted DTB path")
    size = accepted["size"]
    if (
        not isinstance(size, int)
        or isinstance(size, bool)
        or size <= 0
        or size > 2 * 1024 * 1024
    ):
        fail("accepted DTB size is invalid")
    digest = require_sha256(accepted["sha256"], "accepted DTB sha256")
    artifacts = core_profile.get("artifacts")
    if not isinstance(artifacts, list):
        fail("compatibility artifact inventory is malformed")
    matches = [
        row
        for row in artifacts
        if isinstance(row, dict) and row.get("id") == artifact_id
    ]
    if len(matches) != 1:
        fail("accepted DTB artifact link is absent or ambiguous")
    if matches[0] != {
        "id": artifact_id,
        "path": path,
        "size": size,
        "sha256": digest,
    }:
        fail("accepted DTB artifact identity changed")
    candidate = core_profile.get("candidate")
    if (
        not isinstance(candidate, dict)
        or not isinstance(candidate.get("artifact_links"), dict)
        or candidate["artifact_links"].get("board.dtb") != artifact_id
        or not isinstance(candidate.get("identity"), dict)
        or candidate["identity"].get("authority") != "none"
        or candidate["identity"].get("status") != "offline"
    ):
        fail("corrected candidate no longer links the authority-free DTB")


def validate_capability_list(
    value: Any,
    label: str,
    expected: tuple[str, ...],
) -> list[str]:
    result = require_string_list(value, label)
    if tuple(result) != expected:
        if label == "active_capabilities":
            fail("active capability set differs from compatibility profile")
        fail(f"{label.replace('_', ' ')} differs from compatibility profile")
    return result


def validate_source_checks(
    value: Any,
    active: set[str],
) -> list[dict[str, Any]]:
    if not isinstance(value, list) or not value:
        fail("source check inventory is absent")
    result: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    coverage: set[str] = set()
    for index, raw in enumerate(value):
        row = require_object(
            raw,
            SOURCE_CHECK_KEYS,
            f"source check {index}",
        )
        identity = require_string(row["id"], f"source check {index} id")
        if not IDENTIFIER.fullmatch(identity) or identity in seen_ids:
            fail(f"source check identity is invalid or duplicate: {identity}")
        seen_ids.add(identity)
        capabilities = require_string_list(
            row["capabilities"],
            f"source check {identity} capabilities",
        )
        unknown = set(capabilities) - active
        if unknown:
            fail(
                f"source check {identity} has unknown capabilities: "
                f"{sorted(unknown)}"
            )
        coverage.update(capabilities)
        kind = require_string(row["kind"], f"source check {identity} kind")
        if kind not in SOURCE_KINDS:
            fail(f"source check kind is unsupported: {identity}")
        path = safe_relative_path(
            row["path"],
            f"source path",
        )
        required = require_string_list(
            row["required"],
            f"source check {identity} requirements",
        )
        for requirement in required:
            if kind == "kconfig" and not KCONFIG_SYMBOL.fullmatch(requirement):
                fail(f"source check {identity} has an invalid Kconfig symbol")
            if kind == "makefile" and not MAKEFILE_REQUIREMENT.fullmatch(
                requirement
            ):
                fail(f"source check {identity} has an invalid Makefile rule")
            if kind in {"of-match", "binding"} and not COMPATIBLE.fullmatch(
                requirement
            ):
                fail(f"source check {identity} has an invalid compatible")
        result.append(
            {
                "id": identity,
                "capabilities": capabilities,
                "kind": kind,
                "path": path,
                "required": required,
            }
        )
    for capability in EXPECTED_ACTIVE:
        if capability not in coverage:
            fail(f"active capability lacks source coverage: {capability}")
    return result


def validate_property_name(value: Any, label: str) -> str:
    text = require_string(value, label)
    if not PROPERTY.fullmatch(text):
        fail(f"{label} is not a canonical property name")
    return text


def validate_dt_node_path(value: Any, label: str) -> str:
    path = require_string(value, label)
    if (
        not path.startswith("/")
        or "//" in path
        or path != "/" and path.endswith("/")
    ):
        fail(f"{label} is not a canonical absolute DT node path")
    return path


def validate_string_properties(
    value: Any,
    label: str,
) -> dict[str, list[str]]:
    if not isinstance(value, dict):
        fail(f"{label} is not an object")
    result: dict[str, list[str]] = {}
    for raw_name, raw_values in value.items():
        name = validate_property_name(raw_name, f"{label} name")
        result[name] = require_string_list(
            raw_values,
            f"{label} {name}",
        )
    return result


def validate_u32_properties(
    value: Any,
    label: str,
) -> dict[str, list[int]]:
    if not isinstance(value, dict):
        fail(f"{label} is not an object")
    result: dict[str, list[int]] = {}
    for raw_name, raw_values in value.items():
        name = validate_property_name(raw_name, f"{label} name")
        if not isinstance(raw_values, list) or not raw_values:
            fail(f"{label} {name} is not a nonempty u32 list")
        values: list[int] = []
        for raw in raw_values:
            if (
                not isinstance(raw, int)
                or isinstance(raw, bool)
                or raw < 0
                or raw > 0xFFFFFFFF
            ):
                fail(f"{label} {name} contains an invalid u32")
            values.append(raw)
        result[name] = values
    return result


def validate_phandle_properties(
    value: Any,
    label: str,
) -> dict[str, list[str]]:
    if not isinstance(value, dict):
        fail(f"{label} is not an object")
    result: dict[str, list[str]] = {}
    for raw_name, raw_targets in value.items():
        name = validate_property_name(raw_name, f"{label} name")
        targets = require_string_list(
            raw_targets,
            f"{label} {name}",
        )
        for target in targets:
            validate_dt_node_path(target, f"{label} {name} target")
        result[name] = targets
    return result


def validate_phandle_args_properties(
    value: Any,
    label: str,
) -> dict[str, list[dict[str, Any]]]:
    if not isinstance(value, dict):
        fail(f"{label} is not an object")
    result: dict[str, list[dict[str, Any]]] = {}
    for raw_name, raw_entries in value.items():
        name = validate_property_name(raw_name, f"{label} name")
        if name not in PHANDLE_ARGS_CELL_PROPERTIES:
            fail(f"{label} {name} is not a supported phandle-array property")
        if not isinstance(raw_entries, list) or not raw_entries:
            fail(f"{label} {name} is not a nonempty phandle-array list")
        entries: list[dict[str, Any]] = []
        for index, raw_entry in enumerate(raw_entries):
            entry = require_object(
                raw_entry,
                PHANDLE_ARGS_KEYS,
                f"{label} {name}[{index}]",
            )
            target = validate_dt_node_path(
                entry["target"],
                f"{label} {name}[{index}] target",
            )
            raw_args = entry["args"]
            if not isinstance(raw_args, list) or not raw_args:
                fail(f"{label} {name}[{index}] has no phandle arguments")
            args: list[int] = []
            for raw_arg in raw_args:
                if (
                    not isinstance(raw_arg, int)
                    or isinstance(raw_arg, bool)
                    or raw_arg < 0
                    or raw_arg > 0xFFFFFFFF
                ):
                    fail(f"{label} {name}[{index}] has an invalid u32 argument")
                args.append(raw_arg)
            entries.append({"target": target, "args": args})
        result[name] = entries
    return result


def validate_dt_checks(
    value: Any,
    active: set[str],
    required_capabilities: set[str],
) -> list[dict[str, Any]]:
    if not isinstance(value, list) or not value:
        fail("DT check inventory is absent")
    result: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    seen_paths: set[str] = set()
    compatible_absent: set[str] = set()
    coverage: set[str] = set()
    for index, raw in enumerate(value):
        if (
            not isinstance(raw, dict)
            or not DT_CHECK_KEYS.issubset(raw)
            or set(raw) - DT_CHECK_KEYS - DT_CHECK_OPTIONAL_KEYS
        ):
            fail(f"DT check {index} is not canonical")
        row = raw
        identity = require_string(row["id"], f"DT check {index} id")
        if not IDENTIFIER.fullmatch(identity) or identity in seen_ids:
            fail(f"DT check identity is invalid or duplicate: {identity}")
        seen_ids.add(identity)
        capabilities = require_string_list(
            row["capabilities"],
            f"DT check {identity} capabilities",
        )
        unknown = set(capabilities) - active
        if unknown:
            fail(
                f"DT check {identity} has unknown capabilities: "
                f"{sorted(unknown)}"
            )
        coverage.update(capabilities)
        path = validate_dt_node_path(
            row["path"],
            f"DT check {identity} path",
        )
        if path in seen_paths:
            fail(f"DT check path is duplicate: {path}")
        seen_paths.add(path)
        status = require_string(row["status"], f"DT check {identity} status")
        if status not in {"okay", "disabled"}:
            fail(f"DT check {identity} has an unsupported status")
        compatible = require_string_list(
            row["compatible"],
            f"DT check {identity} compatible",
            allow_empty=True,
        )
        if not compatible:
            compatible_absent.add(identity)
        for item in compatible:
            if not COMPATIBLE.fullmatch(item):
                fail(f"DT check {identity} has an invalid compatible")
        string_properties = validate_string_properties(
            row["string_properties"],
            f"DT check {identity} string properties",
        )
        u32_properties = validate_u32_properties(
            row["u32_properties"],
            f"DT check {identity} u32 properties",
        )
        phandle_properties = validate_phandle_properties(
            row.get("phandle_properties", {}),
            f"DT check {identity} phandle properties",
        )
        phandle_args_properties = validate_phandle_args_properties(
            row.get("phandle_args_properties", {}),
            f"DT check {identity} phandle-argument properties",
        )
        present_properties = require_string_list(
            row["present_properties"],
            f"DT check {identity} present properties",
            allow_empty=True,
        )
        for name in present_properties:
            validate_property_name(
                name,
                f"DT check {identity} present property",
            )
        overlap = (
            set(string_properties) & set(u32_properties)
            | set(string_properties) & set(phandle_properties)
            | set(string_properties) & set(phandle_args_properties)
            | set(string_properties) & set(present_properties)
            | set(u32_properties) & set(phandle_properties)
            | set(u32_properties) & set(phandle_args_properties)
            | set(u32_properties) & set(present_properties)
            | set(phandle_properties) & set(phandle_args_properties)
            | set(phandle_properties) & set(present_properties)
            | set(phandle_args_properties) & set(present_properties)
        )
        if overlap:
            fail(f"DT check {identity} repeats property contracts: {sorted(overlap)}")
        result.append(
            {
                "id": identity,
                "capabilities": capabilities,
                "path": path,
                "status": status,
                "compatible": compatible,
                "string_properties": string_properties,
                "u32_properties": u32_properties,
                "phandle_properties": phandle_properties,
                "phandle_args_properties": phandle_args_properties,
                "present_properties": present_properties,
            }
        )
    if compatible_absent != EXPECTED_COMPATIBLE_ABSENT:
        fail(
            "DT compatible-absence inventory changed: "
            f"{sorted(compatible_absent)}"
        )
    for capability in EXPECTED_DTB_REQUIRED:
        if capability not in coverage:
            fail(f"active capability lacks DT coverage: {capability}")
    for check in result:
        for targets in check["phandle_properties"].values():
            missing = sorted(set(targets) - seen_paths)
            if missing:
                fail(
                    f"DT check {check['id']} has unchecked phandle targets: "
                    f"{missing}"
                )
        for entries in check["phandle_args_properties"].values():
            missing = sorted(
                {
                    entry["target"]
                    for entry in entries
                    if entry["target"] not in seen_paths
                }
            )
            if missing:
                fail(
                    f"DT check {check['id']} has unchecked phandle-array targets: "
                    f"{missing}"
                )
    if coverage - required_capabilities:
        fail(
            "DT checks unexpectedly cover non-DT capabilities: "
            f"{sorted(coverage - required_capabilities)}"
        )
    return result


def validate_thermal_policy(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        fail("thermal policy is malformed")
    try:
        passive = value["passive_trip_millicelsius"]
        critical = value["critical_trip_millicelsius"]
        hysteresis = value["passive_hysteresis_millicelsius"]
        critical_hysteresis = value[
            "critical_hysteresis_millicelsius"
        ]
        groups = value["cpu_zone_groups"]
    except (KeyError, TypeError):
        fail("thermal policy is malformed")
    if (
        not isinstance(passive, list)
        or len(passive) != 2
        or not all(isinstance(item, int) for item in passive)
        or not isinstance(critical, int)
        or not isinstance(hysteresis, int)
        or not isinstance(critical_hysteresis, int)
        or not isinstance(groups, list)
    ):
        fail("thermal policy is malformed")
    if not (
        passive[0] < passive[1] < critical
        and 0 < hysteresis < passive[1] - passive[0]
        and 0 < critical_hysteresis < critical - passive[1]
    ):
        fail("thermal trip ordering or hysteresis is unsafe")
    names: list[str] = []
    bindings: list[tuple[str, int]] = []
    try:
        for group in groups:
            if len(group["zone_names"]) != len(group["sensor_indexes"]):
                fail("thermal CPU zone and sensor inventories differ")
            names.extend(group["zone_names"])
            bindings.extend(
                zip(
                    [group["sensor_path"]] * len(group["sensor_indexes"]),
                    group["sensor_indexes"],
                )
            )
    except (KeyError, TypeError):
        fail("thermal policy is malformed")
    try:
        unique_names = set(names)
        unique_bindings = set(bindings)
    except TypeError:
        fail("thermal policy is malformed")
    if len(names) != 12 or len(unique_names) != 12:
        fail("thermal CPU zone inventory is not exact")
    if len(unique_bindings) != len(bindings):
        fail("thermal CPU sensor bindings are duplicated")
    if value != EXPECTED_THERMAL_POLICY:
        fail("thermal policy differs from the accepted static topology")
    return value


def validate_contract(repo: Path, contract: dict[str, Any]) -> dict[str, Any]:
    root = require_object(contract, ROOT_KEYS, "source/DTB contract")
    if root["format"] != FORMAT or root["profile"] != "minimal-headless-v1":
        fail("source/DTB contract identity is unsupported")
    core_profile = validate_core_profile(repo, root)
    active = validate_capability_list(
        root["active_capabilities"],
        "active_capabilities",
        EXPECTED_ACTIVE,
    )
    if tuple(active) != active_core_capabilities(core_profile):
        fail("active capability set differs from compatibility profile")
    dt_required = validate_capability_list(
        root["dt_required_capabilities"],
        "dt_required_capabilities",
        EXPECTED_DTB_REQUIRED,
    )
    forbidden_enabled_compatibles = require_string_list(
        root["forbidden_enabled_compatibles"],
        "forbidden_enabled_compatibles",
    )
    if tuple(forbidden_enabled_compatibles) != EXPECTED_FORBIDDEN_ENABLED:
        fail("forbidden enabled compatible inventory changed")
    for compatible in forbidden_enabled_compatibles:
        if not COMPATIBLE.fullmatch(compatible):
            fail("forbidden enabled compatible is invalid")
    baseline = require_object(
        root["baseline_source"],
        BASELINE_KEYS,
        "baseline_source",
    )
    require_git_commit(baseline["commit"], "baseline source commit")
    if baseline["release"] != "7.1.4":
        fail("baseline source release changed")
    validate_accepted_dtb_link(root, core_profile)
    thermal_policy = validate_thermal_policy(root["thermal_policy"])
    source_checks = validate_source_checks(
        root["source_checks"],
        set(active),
    )
    dt_checks = validate_dt_checks(
        root["dt_checks"],
        set(active),
        set(dt_required),
    )
    validated = dict(root)
    validated["source_checks"] = source_checks
    validated["dt_checks"] = dt_checks
    validated["forbidden_enabled_compatibles"] = forbidden_enabled_compatibles
    validated["thermal_policy"] = thermal_policy
    thermal_fallback = next(
        row
        for row in core_profile["capabilities"]
        if row["id"] == "thermal-emergency-fallback"
    )
    validated["thermal_fallback_status"] = thermal_fallback[
        "candidate_status"
    ]
    return validated


def git_output(source: Path, arguments: list[str]) -> str:
    process = subprocess.run(
        ["git", "-C", str(source), *arguments],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env={
            "PATH": os.environ.get("PATH", ""),
            "LC_ALL": "C",
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_TERMINAL_PROMPT": "0",
        },
    )
    if process.returncode != 0:
        fail(
            "kernel source Git inspection failed: "
            f"{process.stderr.strip() or process.returncode}"
        )
    return process.stdout


def validate_source_root(
    source: Path,
    contract: dict[str, Any],
    role: str,
) -> tuple[Path, str]:
    lexical = Path(os.path.abspath(source.expanduser()))
    if lexical.is_symlink():
        fail("kernel source tree is linked")
    resolved = lexical.resolve(strict=True)
    if lexical != resolved or not resolved.is_dir():
        fail("kernel source tree contains a linked component or is not a directory")
    top = Path(
        git_output(resolved, ["rev-parse", "--show-toplevel"]).strip()
    ).resolve(strict=True)
    if top != resolved:
        fail("kernel source path is not the Git worktree root")
    commit = git_output(resolved, ["rev-parse", "HEAD"]).strip()
    if not GIT_COMMIT.fullmatch(commit):
        fail("kernel source HEAD is not a full SHA-1 identity")
    dirty = git_output(
        resolved,
        ["status", "--porcelain=v1", "--untracked-files=all"],
    )
    if dirty:
        fail("kernel source tree is dirty")
    if role == "baseline" and commit != contract["baseline_source"]["commit"]:
        fail("baseline source commit changed")
    return resolved, commit


def source_file(source: Path, relative: str, label: str) -> Path:
    lexical = source / relative
    if lexical.is_symlink():
        fail(f"source input is linked: {relative}")
    resolved = lexical.resolve(strict=True)
    if lexical.absolute() != resolved:
        fail(f"source input is linked or escapes the tree: {relative}")
    if not resolved.is_file() or resolved.is_symlink():
        fail(f"source input is not an ordinary file: {relative}")
    return resolved


def source_text(source: Path, relative: str, label: str) -> str:
    data = read_bounded(
        source_file(source, relative, label),
        label,
        MAX_SOURCE_SIZE,
    )
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        fail(f"{label} is not UTF-8")
    if "\0" in text or "\r" in text:
        fail(f"{label} is not canonical source text")
    return text


def validate_tracked_source_inputs(
    source: Path,
    checks: list[dict[str, Any]],
) -> None:
    paths = sorted({check["path"] for check in checks})
    stage_output = git_output(
        source,
        ["ls-files", "--stage", "-z", "--", *paths],
    )
    stages: dict[str, tuple[str, str]] = {}
    for raw_record in stage_output.split("\0"):
        if not raw_record:
            continue
        match = re.fullmatch(
            r"(100644|100755) ([0-9a-f]{40}) 0\t(.+)",
            raw_record,
        )
        if match is None:
            fail("source input is not an ordinary stage-zero tracked blob")
        mode, object_id, path = match.groups()
        if path in stages:
            fail(f"source input has duplicate index entries: {path}")
        stages[path] = (mode, object_id)
    if set(stages) != set(paths):
        missing = sorted(set(paths) - set(stages))
        fail(f"source input is not an ordinary tracked blob: {missing}")

    tag_output = git_output(
        source,
        ["ls-files", "-v", "-z", "--", *paths],
    )
    tags: dict[str, str] = {}
    for raw_record in tag_output.split("\0"):
        if not raw_record:
            continue
        if len(raw_record) < 3 or raw_record[1] != " ":
            fail("source input has a malformed Git index tag")
        tag, path = raw_record[0], raw_record[2:]
        if path in tags:
            fail(f"source input has duplicate Git index tags: {path}")
        tags[path] = tag
    if set(tags) != set(paths) or any(tag != "H" for tag in tags.values()):
        fail("source input uses an assume-unchanged or skip-worktree index flag")


def parse_kconfig_symbols(text: str) -> set[str]:
    return set(
        re.findall(
            r"(?m)^(?:menuconfig|config)[ \t]+([A-Z0-9_]+)[ \t]*$",
            text,
        )
    )


def makefile_logical_lines(text: str) -> list[str]:
    result: list[str] = []
    pending = ""
    for raw in text.splitlines():
        line = raw.split("#", 1)[0].rstrip()
        if line.endswith("\\"):
            pending += line[:-1] + " "
            continue
        line = pending + line
        pending = ""
        if line.strip():
            result.append(line)
    if pending.strip():
        fail("Makefile ends in an unterminated continuation")
    return result


def parse_makefile_rules(text: str) -> set[tuple[str, str]]:
    rules: set[tuple[str, str]] = set()
    pattern = re.compile(
        r"^(?:obj|[A-Za-z0-9_]+)-[$][(](CONFIG_[A-Z0-9_]+)[)]"
        r"[ \t]*(?:[+:]?=)[ \t]*(.*)$"
    )
    for line in makefile_logical_lines(text):
        match = pattern.match(line.strip())
        if match is None:
            continue
        symbol, objects = match.groups()
        for object_name in objects.split():
            if object_name.endswith(".o"):
                rules.add((symbol, object_name))
    return rules


def strip_c_comments(text: str) -> str:
    text = text.replace("\\\n", "")
    result: list[str] = []
    index = 0
    state = "code"
    while index < len(text):
        character = text[index]
        following = text[index + 1] if index + 1 < len(text) else ""
        if state == "code":
            if character == "/" and following == "/":
                result.extend((" ", " "))
                index += 2
                state = "line-comment"
                continue
            if character == "/" and following == "*":
                result.extend((" ", " "))
                index += 2
                state = "block-comment"
                continue
            if character == '"':
                state = "string"
            elif character == "'":
                state = "character"
            result.append(character)
            index += 1
            continue
        if state == "line-comment":
            if character == "\n":
                result.append(character)
                state = "code"
            else:
                result.append(" ")
            index += 1
            continue
        if state == "block-comment":
            if character == "*" and following == "/":
                result.extend((" ", " "))
                index += 2
                state = "code"
            else:
                result.append("\n" if character == "\n" else " ")
                index += 1
            continue
        result.append(character)
        if character == "\\" and following:
            result.append(following)
            index += 2
            continue
        if state == "string" and character == '"':
            state = "code"
        elif state == "character" and character == "'":
            state = "code"
        index += 1
    if state == "block-comment":
        fail("source input has an unterminated block comment")
    return "".join(result)


def registered_of_compatibles(text: str) -> set[str]:
    identifier = r"[A-Za-z_][A-Za-z0-9_]*"
    table_pattern = re.compile(
        rf"\b(?:static[ \t]+)?const[ \t]+struct[ \t]+of_device_id"
        rf"[ \t]+({identifier})[ \t]*\[\s*\][ \t]*=[ \t]*"
        r"\{(.*?)^[ \t]*\};",
        re.MULTILINE | re.DOTALL,
    )
    driver_pattern = re.compile(
        rf"\b(?:static[ \t]+)?(?:const[ \t]+)?struct[ \t]+platform_driver"
        rf"[ \t]+({identifier})[ \t]*=[ \t]*\{{(.*?)^[ \t]*\}};",
        re.MULTILINE | re.DOTALL,
    )
    drivers = list(driver_pattern.finditer(text))
    integrated: set[str] = set()
    for table_match in table_pattern.finditer(text):
        table, body = table_match.groups()
        if re.search(
            rf"\bMODULE_DEVICE_TABLE[ \t]*\([ \t]*of[ \t]*,"
            rf"[ \t]*{re.escape(table)}[ \t]*\)[ \t]*;",
            text,
        ) is None:
            continue
        for driver_match in drivers:
            driver, driver_body = driver_match.groups()
            if re.search(
                rf"[.]of_match_table[ \t]*=[ \t]*"
                rf"(?:of_match_ptr[ \t]*\([ \t]*)?"
                rf"{re.escape(table)}(?:[ \t]*\))?[ \t]*,",
                driver_body,
            ) is None:
                continue
            macro_registration = re.search(
                rf"\b(?:module|builtin)_platform_driver"
                rf"(?:_probe)?[ \t]*\([ \t]*{re.escape(driver)}"
                rf"(?:[ \t]*,|\s*\))",
                text,
            )
            direct_registration = re.search(
                rf"\bplatform_driver_(?:register|probe)[ \t]*\("
                rf"[ \t]*&[ \t]*{re.escape(driver)}(?:[ \t]*,|\s*\))",
                text,
            )
            if macro_registration is None and direct_registration is None:
                continue
            integrated.update(
                re.findall(
                    r"[.]compatible[ \t]*=[ \t]*"
                    r"\"([A-Za-z0-9,._+-]+)\"",
                    body,
                )
            )
    return integrated


def validate_source_check(source: Path, check: dict[str, Any]) -> None:
    identity = check["id"]
    text = source_text(
        source,
        check["path"],
        f"source check {identity}",
    )
    kind = check["kind"]
    if kind in {"of-match", "source"}:
        text = strip_c_comments(text)
    if kind == "kconfig":
        symbols = parse_kconfig_symbols(text)
        for symbol in check["required"]:
            if symbol not in symbols:
                fail(f"source check {identity} missing Kconfig symbol: {symbol}")
    elif kind == "makefile":
        rules = parse_makefile_rules(text)
        for requirement in check["required"]:
            symbol, object_name = requirement.split(":", 1)
            if (symbol, object_name) not in rules:
                fail(
                    f"source check {identity} missing Makefile object rule: "
                    f"{requirement}"
                )
    elif kind == "of-match":
        compatibles = registered_of_compatibles(text)
        for compatible in check["required"]:
            if compatible not in compatibles:
                fail(
                    f"source check {identity} missing registered OF compatible: "
                    f"{compatible}"
                )
    elif kind == "binding":
        binding_compatibles = set(
            match.group(1)
            for line in text.splitlines()
            if not line.lstrip().startswith("#")
            for match in [
                re.search(
                    r"(?:^|[ \t])(?:-[ \t]+|const:[ \t]+)"
                    r"[\"']?([A-Za-z0-9][A-Za-z0-9,._+-]*)[\"']?"
                    r"[ \t]*$",
                    line,
                )
            ]
            if match is not None
        )
        for compatible in check["required"]:
            if compatible not in binding_compatibles:
                fail(
                    f"source check {identity} missing binding compatible: "
                    f"{compatible}"
                )
    elif kind == "source":
        normalized = (
            re.sub(r"[ \t\n]+", " ", text)
            if identity in NORMALIZED_SOURCE_CHECKS
            else ""
        )
        for literal in check["required"]:
            if literal not in text and literal not in normalized:
                fail(
                    f"source check {identity} missing source contract literal: "
                    f"{literal}"
                )
    else:
        fail(f"source check kind is unsupported: {identity}")


def validate_source(
    source: Path,
    contract: dict[str, Any],
    role: str,
) -> str:
    root, commit = validate_source_root(source, contract, role)
    validate_tracked_source_inputs(root, contract["source_checks"])
    for check in contract["source_checks"]:
        validate_source_check(root, check)
    return commit


def dtb_module() -> ModuleType:
    return load_module(
        REPO / "scripts/device/verify-recovery-dtb-delta.py",
        "rog5_recovery_dtb_parser",
    )


def decode_string_list(value: bytes, label: str) -> list[str]:
    if not value or not value.endswith(b"\0"):
        fail(f"{label} is not a NUL-terminated string list")
    raw_parts = value[:-1].split(b"\0")
    if not raw_parts or any(not part for part in raw_parts):
        fail(f"{label} contains an empty string")
    result: list[str] = []
    for raw in raw_parts:
        try:
            text = raw.decode("ascii")
        except UnicodeDecodeError:
            fail(f"{label} is not ASCII")
        if not text or any(ord(character) < 0x20 for character in text):
            fail(f"{label} contains a noncanonical string")
        result.append(text)
    return result


def effective_status(properties: dict[str, bytes], label: str) -> str:
    value = properties.get("status")
    if value is None:
        return "okay"
    statuses = decode_string_list(value, f"{label} status")
    if statuses in (["okay"], ["ok"]):
        return "okay"
    if statuses == ["disabled"]:
        return "disabled"
    fail(f"{label} has an unsupported status: {statuses}")


def decode_u32_list(value: bytes, label: str) -> list[int]:
    if not value or len(value) % 4:
        fail(f"{label} is not a nonempty u32 list")
    return list(struct.unpack(f">{len(value) // 4}I", value))


def node_phandle(
    nodes: dict[str, dict[str, bytes]],
    path: str,
    label: str,
) -> int:
    properties = nodes.get(path)
    if properties is None:
        fail(f"{label} target node is absent: {path}")
    values: list[int] = []
    for name in ("phandle", "linux,phandle"):
        raw = properties.get(name)
        if raw is not None:
            decoded = decode_u32_list(raw, f"{label} target {path} {name}")
            if len(decoded) != 1 or decoded[0] == 0:
                fail(f"{label} target {path} has an invalid {name}")
            values.append(decoded[0])
    if not values or len(set(values)) != 1:
        fail(f"{label} target {path} has no unique phandle")
    value = values[0]
    owners: set[str] = set()
    for candidate_path, candidate_properties in nodes.items():
        for name in ("phandle", "linux,phandle"):
            raw = candidate_properties.get(name)
            if raw is not None and raw == struct.pack(">I", value):
                owners.add(candidate_path)
    if owners != {path}:
        fail(f"{label} target {path} phandle is not unique")
    return value


def validate_enabled_ancestors(
    nodes: dict[str, dict[str, bytes]],
    path: str,
    identity: str,
) -> None:
    parts = [part for part in path.split("/") if part]
    for depth in range(len(parts)):
        ancestor = "/" + "/".join(parts[:depth]) if depth else "/"
        properties = nodes.get(ancestor)
        if properties is None:
            fail(f"DT check {identity} ancestor is absent: {ancestor}")
        if effective_status(properties, f"DT check {identity} ancestor {ancestor}") != "okay":
            fail(f"DT check {identity} ancestor is not enabled: {ancestor}")


def validate_enabled_path(
    nodes: dict[str, dict[str, bytes]],
    path: str,
    identity: str,
) -> None:
    validate_enabled_ancestors(nodes, path, identity)
    properties = nodes.get(path)
    if properties is None:
        fail(f"DT check {identity} node is absent: {path}")
    if effective_status(properties, f"DT check {identity}") != "okay":
        fail(f"DT check {identity} is not enabled: {path}")


def path_is_effectively_enabled(
    nodes: dict[str, dict[str, bytes]],
    path: str,
) -> bool:
    if path == "/":
        lineage = ["/"]
    else:
        parts = [part for part in path.split("/") if part]
        lineage = ["/"] + [
            "/" + "/".join(parts[:depth])
            for depth in range(1, len(parts) + 1)
        ]
    for member in lineage:
        properties = nodes.get(member)
        if properties is None:
            fail(f"DT node ancestor is absent: {member}")
        if effective_status(properties, f"DT node {member}") != "okay":
            return False
    return True


def validate_forbidden_enabled_compatibles(
    nodes: dict[str, dict[str, bytes]],
    forbidden: list[str],
) -> None:
    forbidden_set = set(forbidden)
    for path, properties in nodes.items():
        raw = properties.get("compatible")
        if raw is None:
            continue
        compatibles = decode_string_list(raw, f"DT node {path} compatible")
        matched = sorted(set(compatibles) & forbidden_set)
        if matched and path_is_effectively_enabled(nodes, path):
            fail(
                f"forbidden compatible is effectively enabled: "
                f"path={path} compatible={matched}"
            )


def validate_cpu_memory_node_inventories(
    nodes: dict[str, dict[str, bytes]],
) -> None:
    cpu_paths: set[str] = set()
    memory_paths: set[str] = set()
    for path, properties in nodes.items():
        raw_device_type = properties.get("device_type")
        device_types = (
            decode_string_list(raw_device_type, f"DT node {path} device_type")
            if raw_device_type is not None
            else []
        )
        direct_cpu_child = (
            path.startswith("/cpus/")
            and path.count("/") == 2
            and path.rsplit("/", 1)[1].startswith("cpu@")
        )
        root_memory_node = (
            path.count("/") == 1
            and path.rsplit("/", 1)[1].startswith("memory@")
        )
        if direct_cpu_child or "cpu" in device_types:
            cpu_paths.add(path)
        if root_memory_node or "memory" in device_types:
            memory_paths.add(path)
    if cpu_paths != EXPECTED_CPU_NODE_PATHS:
        fail(
            "DT CPU node inventory changed: "
            f"expected={sorted(EXPECTED_CPU_NODE_PATHS)} "
            f"actual={sorted(cpu_paths)}"
        )
    if memory_paths != EXPECTED_MEMORY_NODE_PATHS:
        fail(
            "DT system-memory node inventory changed: "
            f"expected={sorted(EXPECTED_MEMORY_NODE_PATHS)} "
            f"actual={sorted(memory_paths)}"
        )


def phandle_owners(
    nodes: dict[str, dict[str, bytes]],
) -> dict[int, str]:
    result: dict[int, str] = {}
    for path, properties in nodes.items():
        for name in ("phandle", "linux,phandle"):
            raw = properties.get(name)
            if raw is None:
                continue
            values = decode_u32_list(raw, f"DT node {path} {name}")
            if len(values) != 1 or values[0] == 0:
                fail(f"DT node {path} has an invalid {name}")
            owner = result.setdefault(values[0], path)
            if owner != path:
                fail(
                    f"DT phandle is owned by multiple nodes: {values[0]}"
                )
    return result


def exact_u32_property(
    properties: dict[str, bytes],
    name: str,
    expected: list[int],
    label: str,
) -> None:
    raw = properties.get(name)
    if raw is None:
        fail(f"{label} property is absent: {name}")
    actual = decode_u32_list(raw, f"{label} property {name}")
    if actual != expected:
        fail(
            f"{label} property changed: {name} "
            f"expected={expected} actual={actual}"
        )


def exact_string_property(
    properties: dict[str, bytes],
    name: str,
    expected: list[str],
    label: str,
) -> None:
    raw = properties.get(name)
    if raw is None:
        fail(f"{label} property is absent: {name}")
    actual = decode_string_list(raw, f"{label} property {name}")
    if actual != expected:
        fail(
            f"{label} property changed: {name} "
            f"expected={expected} actual={actual}"
        )


def direct_children(
    nodes: dict[str, dict[str, bytes]],
    parent: str,
) -> set[str]:
    prefix = parent.rstrip("/") + "/"
    depth = parent.count("/") + 1
    return {
        path
        for path in nodes
        if path.startswith(prefix) and path.count("/") == depth
    }


def thermal_sensor_reference(
    nodes: dict[str, dict[str, bytes]],
    owners: dict[int, str],
    path: str,
) -> tuple[str, tuple[int, ...]]:
    properties = nodes[path]
    raw = properties.get("thermal-sensors")
    if raw is None:
        fail(f"thermal zone has no sensor reference: {path}")
    values = decode_u32_list(raw, f"thermal zone {path} thermal-sensors")
    if not values or values[0] not in owners:
        fail(f"thermal zone has an unresolved sensor reference: {path}")
    target = owners[values[0]]
    target_properties = nodes[target]
    cells_raw = target_properties.get("#thermal-sensor-cells")
    if cells_raw is None:
        fail(f"thermal sensor target lacks cell count: {target}")
    cells = decode_u32_list(
        cells_raw,
        f"thermal sensor target {target} #thermal-sensor-cells",
    )
    if len(cells) != 1 or cells[0] > 8:
        fail(f"thermal sensor target has an invalid cell count: {target}")
    if len(values) != cells[0] + 1:
        fail(f"thermal zone sensor specifier width changed: {path}")
    return target, tuple(values[1:])


def validate_trip(
    nodes: dict[str, dict[str, bytes]],
    path: str,
    *,
    temperature: int,
    hysteresis: int,
    trip_type: str,
    require_phandle: bool = False,
) -> None:
    properties = nodes.get(path)
    if properties is None:
        fail(f"thermal trip is absent: {path}")
    required = {"temperature", "hysteresis", "type"}
    permitted = required | {"phandle", "linux,phandle"}
    if not required.issubset(properties) or set(properties) - permitted:
        fail(f"thermal trip properties changed: {path}")
    exact_u32_property(
        properties,
        "temperature",
        [temperature],
        f"thermal trip {path}",
    )
    exact_u32_property(
        properties,
        "hysteresis",
        [hysteresis],
        f"thermal trip {path}",
    )
    exact_string_property(
        properties,
        "type",
        [trip_type],
        f"thermal trip {path}",
    )
    if require_phandle:
        node_phandle(nodes, path, f"thermal trip {path}")


def validate_cpu_thermal_zones(
    nodes: dict[str, dict[str, bytes]],
    owners: dict[int, str],
    policy: dict[str, Any],
) -> set[tuple[str, tuple[int, ...]]]:
    expected_paths = {
        f"/thermal-zones/{name}"
        for group in policy["cpu_zone_groups"]
        for name in group["zone_names"]
    }
    cpu_paths = {
        path
        for group in policy["cpu_zone_groups"]
        for path in group["cooling_cpu_paths"]
    }
    actual_paths = {
        path
        for path in direct_children(nodes, "/thermal-zones")
        if path.rsplit("/", 1)[1].startswith("cpu")
        and path.endswith("-thermal")
    }
    for zone_path in direct_children(nodes, "/thermal-zones"):
        maps_path = f"{zone_path}/cooling-maps"
        if maps_path not in nodes:
            continue
        for map_path in direct_children(nodes, maps_path):
            properties = nodes[map_path]
            raw = properties.get("cooling-device")
            if raw is None:
                continue
            values = decode_u32_list(
                raw,
                f"thermal cooling map {map_path} cooling-device",
            )
            offset = 0
            while offset < len(values):
                target = owners.get(values[offset])
                if target is None:
                    fail(
                        f"thermal cooling map has an unresolved device: "
                        f"{map_path}"
                    )
                cells_raw = nodes[target].get("#cooling-cells")
                if cells_raw is None:
                    fail(
                        f"thermal cooling target lacks cell count: {target}"
                    )
                cells = decode_u32_list(
                    cells_raw,
                    f"thermal cooling target {target} #cooling-cells",
                )
                if len(cells) != 1 or cells[0] > 8:
                    fail(
                        f"thermal cooling target has an invalid "
                        f"cell count: {target}"
                    )
                offset += 1 + cells[0]
                if offset > len(values):
                    fail(
                        f"thermal cooling map specifier width changed: "
                        f"{map_path}"
                    )
                if target in cpu_paths:
                    actual_paths.add(zone_path)
    if actual_paths != expected_paths:
        fail(
            "thermal CPU zone inventory changed: "
            f"expected={sorted(expected_paths)} actual={sorted(actual_paths)}"
        )
    bindings: set[tuple[str, tuple[int, ...]]] = set()
    passive = policy["passive_trip_millicelsius"]
    for group in policy["cpu_zone_groups"]:
        sensor_path = group["sensor_path"]
        sensor_count = next(
            controller["sensor_count"]
            for controller in policy["sensor_controllers"]
            if controller["path"] == sensor_path
        )
        cooling_values: list[int] = []
        for cpu_path in group["cooling_cpu_paths"]:
            cpu = nodes.get(cpu_path)
            if cpu is None:
                fail(f"thermal cooling CPU is absent: {cpu_path}")
            exact_u32_property(
                cpu,
                "#cooling-cells",
                [2],
                f"thermal cooling CPU {cpu_path}",
            )
            cooling_values.extend(
                [
                    node_phandle(
                        nodes,
                        cpu_path,
                        f"thermal cooling CPU {cpu_path}",
                    ),
                    THERMAL_NO_LIMIT,
                    THERMAL_NO_LIMIT,
                ]
            )
        for zone_name, sensor_index in zip(
            group["zone_names"],
            group["sensor_indexes"],
        ):
            path = f"/thermal-zones/{zone_name}"
            properties = nodes[path]
            validate_enabled_path(nodes, path, f"thermal zone {zone_name}")
            if "polling-delay" in properties:
                fail(f"thermal CPU zone has an unexpected polling delay: {path}")
            exact_u32_property(
                properties,
                "polling-delay-passive",
                [policy["polling_delay_passive_ms"]],
                f"thermal CPU zone {path}",
            )
            reference = thermal_sensor_reference(
                nodes,
                owners,
                path,
            )
            if (
                len(reference[1]) != 1
                or not 0 <= reference[1][0] < sensor_count
            ):
                fail(f"thermal CPU zone sensor index is out of range: {path}")
            expected_reference = (sensor_path, (sensor_index,))
            if reference != expected_reference:
                fail(
                    f"thermal CPU zone sensor binding changed: {path} "
                    f"expected={expected_reference} actual={reference}"
                )
            if reference in bindings:
                fail(f"thermal CPU sensor binding is duplicated: {reference}")
            bindings.add(reference)

            trips_path = f"{path}/trips"
            if nodes.get(trips_path) != {}:
                fail(f"thermal CPU trip container changed: {trips_path}")
            expected_trips = {
                f"{trips_path}/trip-point0",
                f"{trips_path}/trip-point1",
                f"{trips_path}/cpu-crit",
            }
            if direct_children(nodes, trips_path) != expected_trips:
                fail(f"thermal CPU trip inventory changed: {path}")
            validate_trip(
                nodes,
                f"{trips_path}/trip-point0",
                temperature=passive[0],
                hysteresis=policy["passive_hysteresis_millicelsius"],
                trip_type="passive",
                require_phandle=True,
            )
            validate_trip(
                nodes,
                f"{trips_path}/trip-point1",
                temperature=passive[1],
                hysteresis=policy["passive_hysteresis_millicelsius"],
                trip_type="passive",
                require_phandle=True,
            )
            validate_trip(
                nodes,
                f"{trips_path}/cpu-crit",
                temperature=policy["critical_trip_millicelsius"],
                hysteresis=policy["critical_hysteresis_millicelsius"],
                trip_type="critical",
            )

            maps_path = f"{path}/cooling-maps"
            if nodes.get(maps_path) != {}:
                fail(f"thermal CPU cooling-map container changed: {maps_path}")
            expected_maps = {
                f"{maps_path}/map0",
                f"{maps_path}/map1",
            }
            if direct_children(nodes, maps_path) != expected_maps:
                fail(f"thermal CPU cooling-map inventory changed: {path}")
            for index in range(2):
                map_path = f"{maps_path}/map{index}"
                map_properties = nodes[map_path]
                if set(map_properties) != {"trip", "cooling-device"}:
                    fail(f"thermal CPU cooling-map properties changed: {map_path}")
                exact_u32_property(
                    map_properties,
                    "trip",
                    [
                        node_phandle(
                            nodes,
                            f"{trips_path}/trip-point{index}",
                            f"thermal CPU cooling map {map_path}",
                        )
                    ],
                    f"thermal CPU cooling map {map_path}",
                )
                exact_u32_property(
                    map_properties,
                    "cooling-device",
                    cooling_values,
                    f"thermal CPU cooling map {map_path}",
                )
    return bindings


def validate_pmic_thermal_zones(
    nodes: dict[str, dict[str, bytes]],
    owners: dict[int, str],
    policy: dict[str, Any],
) -> set[tuple[str, tuple[int, ...]]]:
    expected_alarm_paths = {
        row["alarm_path"] for row in policy["pmic_temp_alarms"]
    }
    actual_alarm_paths: set[str] = set()
    for path, properties in nodes.items():
        raw = properties.get("compatible")
        if raw is None:
            continue
        compatibles = decode_string_list(
            raw,
            f"DT node {path} compatible",
        )
        if compatibles == ["qcom,spmi-temp-alarm"]:
            actual_alarm_paths.add(path)
    if actual_alarm_paths != expected_alarm_paths:
        fail(
            "thermal PMIC alarm inventory changed: "
            f"expected={sorted(expected_alarm_paths)} "
            f"actual={sorted(actual_alarm_paths)}"
        )

    expected_zone_paths = {
        f"/thermal-zones/{row['zone_name']}"
        for row in policy["pmic_temp_alarms"]
    }
    bindings: set[tuple[str, tuple[int, ...]]] = set()
    for row in policy["pmic_temp_alarms"]:
        alarm_path = row["alarm_path"]
        alarm = nodes[alarm_path]
        validate_enabled_path(
            nodes,
            alarm_path,
            f"thermal PMIC alarm {alarm_path}",
        )
        exact_string_property(
            alarm,
            "compatible",
            ["qcom,spmi-temp-alarm"],
            f"thermal PMIC alarm {alarm_path}",
        )
        exact_u32_property(
            alarm,
            "reg",
            [0xA00],
            f"thermal PMIC alarm {alarm_path}",
        )
        exact_u32_property(
            alarm,
            "interrupts",
            [row["sid"], 0xA, 0, 3],
            f"thermal PMIC alarm {alarm_path}",
        )
        exact_u32_property(
            alarm,
            "#thermal-sensor-cells",
            [0],
            f"thermal PMIC alarm {alarm_path}",
        )

        zone_path = f"/thermal-zones/{row['zone_name']}"
        zone = nodes.get(zone_path)
        if zone is None:
            fail(f"thermal PMIC zone is absent: {zone_path}")
        validate_enabled_path(
            nodes,
            zone_path,
            f"thermal PMIC zone {zone_path}",
        )
        if "polling-delay" in zone:
            fail(f"thermal PMIC zone has an unexpected polling delay: {zone_path}")
        exact_u32_property(
            zone,
            "polling-delay-passive",
            [policy["pmic_polling_delay_passive_ms"]],
            f"thermal PMIC zone {zone_path}",
        )
        reference = thermal_sensor_reference(
            nodes,
            owners,
            zone_path,
        )
        expected_reference = (alarm_path, ())
        if reference != expected_reference:
            fail(
                f"thermal PMIC zone sensor binding changed: {zone_path} "
                f"expected={expected_reference} actual={reference}"
            )
        if reference in bindings:
            fail(f"thermal PMIC sensor binding is duplicated: {reference}")
        bindings.add(reference)

        trips_path = f"{zone_path}/trips"
        if nodes.get(trips_path) != {}:
            fail(f"thermal PMIC trip container changed: {trips_path}")
        expected_trips = {
            f"{trips_path}/trip0",
            f"{trips_path}/{row['critical_trip_name']}",
        }
        if direct_children(nodes, trips_path) != expected_trips:
            fail(f"thermal PMIC trip inventory changed: {zone_path}")
        validate_trip(
            nodes,
            f"{trips_path}/trip0",
            temperature=policy["pmic_passive_trip_millicelsius"],
            hysteresis=0,
            trip_type="passive",
        )
        validate_trip(
            nodes,
            f"{trips_path}/{row['critical_trip_name']}",
            temperature=policy["pmic_critical_trip_millicelsius"],
            hysteresis=0,
            trip_type="critical",
        )
        if f"{zone_path}/cooling-maps" in nodes:
            fail(f"thermal PMIC zone unexpectedly has cooling maps: {zone_path}")

    actual_zone_paths: set[str] = set()
    for path in direct_children(nodes, "/thermal-zones"):
        if "thermal-sensors" not in nodes[path]:
            continue
        target, _arguments = thermal_sensor_reference(nodes, owners, path)
        if target in expected_alarm_paths:
            actual_zone_paths.add(path)
    if actual_zone_paths != expected_zone_paths:
        fail(
            "thermal PMIC zone inventory changed: "
            f"expected={sorted(expected_zone_paths)} "
            f"actual={sorted(actual_zone_paths)}"
        )
    return bindings


def validate_thermal_policy_dtb(
    nodes: dict[str, dict[str, bytes]],
    policy: dict[str, Any],
) -> None:
    owners = phandle_owners(nodes)
    pdc_path = policy["pdc_path"]
    pdc_parent_path = policy["pdc_parent_path"]
    for path in (pdc_path, pdc_parent_path):
        if path not in nodes:
            fail(f"thermal interrupt controller is absent: {path}")
        validate_enabled_path(
            nodes,
            path,
            f"thermal interrupt controller {path}",
        )
        if nodes[path].get("interrupt-controller") != b"":
            fail(f"thermal interrupt controller marker changed: {path}")
    exact_u32_property(
        nodes[pdc_path],
        "#interrupt-cells",
        [2],
        f"thermal PDC {pdc_path}",
    )
    exact_u32_property(
        nodes[pdc_parent_path],
        "#interrupt-cells",
        [3],
        f"thermal interrupt parent {pdc_parent_path}",
    )
    exact_u32_property(
        nodes[pdc_path],
        "interrupt-parent",
        [
            node_phandle(
                nodes,
                pdc_parent_path,
                f"thermal PDC {pdc_path}",
            )
        ],
        f"thermal PDC {pdc_path}",
    )
    pdc_phandle = node_phandle(
        nodes,
        pdc_path,
        f"thermal PDC {pdc_path}",
    )
    for controller in policy["sensor_controllers"]:
        path = controller["path"]
        properties = nodes.get(path)
        if properties is None:
            fail(f"thermal sensor controller is absent: {path}")
        validate_enabled_path(
            nodes,
            path,
            f"thermal sensor controller {path}",
        )
        exact_u32_property(
            properties,
            "#qcom,sensors",
            [controller["sensor_count"]],
            f"thermal sensor controller {path}",
        )
        exact_u32_property(
            properties,
            "#thermal-sensor-cells",
            [1],
            f"thermal sensor controller {path}",
        )
        exact_string_property(
            properties,
            "interrupt-names",
            ["uplow", "critical"],
            f"thermal sensor controller {path}",
        )
        expected_interrupts: list[int] = []
        for arguments in controller["interrupt_args"]:
            expected_interrupts.append(pdc_phandle)
            expected_interrupts.extend(arguments)
        exact_u32_property(
            properties,
            "interrupts-extended",
            expected_interrupts,
            f"thermal sensor controller {path}",
        )

    expected_bindings = validate_cpu_thermal_zones(
        nodes,
        owners,
        policy,
    )
    expected_bindings.update(
        validate_pmic_thermal_zones(
            nodes,
            owners,
            policy,
        )
    )
    all_bindings: dict[tuple[str, tuple[int, ...]], str] = {}
    for path in direct_children(nodes, "/thermal-zones"):
        if "thermal-sensors" not in nodes[path]:
            continue
        reference = thermal_sensor_reference(nodes, owners, path)
        previous = all_bindings.setdefault(reference, path)
        if previous != path:
            fail(
                "thermal zone sensor binding is duplicated: "
                f"{reference} paths={[previous, path]}"
            )
    missing = expected_bindings - set(all_bindings)
    if missing:
        fail(f"thermal expected sensor bindings are absent: {sorted(missing)}")


def validate_dt_check(
    nodes: dict[str, dict[str, bytes]],
    check: dict[str, Any],
) -> None:
    identity = check["id"]
    properties = nodes.get(check["path"])
    if properties is None:
        fail(f"DT check {identity} node is absent: {check['path']}")
    status = effective_status(properties, f"DT check {identity}")
    if status != check["status"]:
        fail(
            f"DT check {identity} status changed: "
            f"expected={check['status']} actual={status}"
        )
    if status == "okay":
        validate_enabled_ancestors(nodes, check["path"], identity)
    compatible_raw = properties.get("compatible")
    if check["compatible"]:
        if compatible_raw is None:
            fail(f"DT check {identity} compatible is absent")
        compatible = decode_string_list(
            compatible_raw,
            f"DT check {identity} compatible",
        )
        if compatible != check["compatible"]:
            fail(
                f"DT check {identity} compatible changed: "
                f"expected={check['compatible']} actual={compatible}"
            )
    elif compatible_raw is not None:
        fail(f"DT check {identity} has an unexpected compatible")
    for name, expected in check["string_properties"].items():
        raw = properties.get(name)
        if raw is None:
            fail(f"DT check {identity} string property is absent: {name}")
        actual = decode_string_list(
            raw,
            f"DT check {identity} property {name}",
        )
        if actual != expected:
            fail(
                f"DT check {identity} string property changed: {name} "
                f"expected={expected} actual={actual}"
            )
    for name, expected in check["u32_properties"].items():
        raw = properties.get(name)
        if raw is None:
            fail(f"DT check {identity} u32 property is absent: {name}")
        actual = decode_u32_list(
            raw,
            f"DT check {identity} property {name}",
        )
        if actual != expected:
            fail(
                f"DT check {identity} u32 property changed: {name} "
                f"expected={expected} actual={actual}"
            )
    for name, target_paths in check["phandle_properties"].items():
        raw = properties.get(name)
        if raw is None:
            fail(f"DT check {identity} phandle property is absent: {name}")
        actual = decode_u32_list(
            raw,
            f"DT check {identity} property {name}",
        )
        expected = [
            node_phandle(
                nodes,
                target,
                f"DT check {identity} property {name}",
            )
            for target in target_paths
        ]
        if actual != expected:
            fail(
                f"DT check {identity} phandle property changed: {name} "
                f"expected_targets={target_paths} actual={actual}"
            )
    for name, entries in check["phandle_args_properties"].items():
        raw = properties.get(name)
        if raw is None:
            fail(
                f"DT check {identity} phandle-array property is absent: {name}"
            )
        actual = decode_u32_list(
            raw,
            f"DT check {identity} property {name}",
        )
        expected: list[int] = []
        cell_property = PHANDLE_ARGS_CELL_PROPERTIES[name]
        for entry in entries:
            target = entry["target"]
            target_properties = nodes.get(target)
            if target_properties is None:
                fail(
                    f"DT check {identity} phandle-array target is absent: "
                    f"{target}"
                )
            cell_raw = target_properties.get(cell_property)
            if cell_raw is None:
                fail(
                    f"DT check {identity} phandle-array target lacks "
                    f"{cell_property}: {target}"
                )
            cell_count = decode_u32_list(
                cell_raw,
                f"DT check {identity} target {target} {cell_property}",
            )
            if cell_count != [len(entry["args"])]:
                fail(
                    f"DT check {identity} phandle-array target cell count "
                    f"changed: {target} {cell_property}"
                )
            expected.append(
                node_phandle(
                    nodes,
                    target,
                    f"DT check {identity} property {name}",
                )
            )
            expected.extend(entry["args"])
        if actual != expected:
            fail(
                f"DT check {identity} phandle-array property changed: {name} "
                f"actual={actual}"
            )
    for name in check["present_properties"]:
        if name not in properties:
            fail(f"DT check {identity} property is absent: {name}")


def validate_dtb(
    path: Path,
    contract: dict[str, Any],
    role: str,
) -> str:
    parser = dtb_module()
    data = parser.read_dtb_bytes(path)
    digest = hashlib.sha256(data).hexdigest()
    accepted = contract["accepted_dtb"]
    if role == "baseline":
        if len(data) != accepted["size"]:
            fail("baseline DTB size changed")
        if digest != accepted["sha256"]:
            fail("baseline DTB hash changed")
    nodes = parser.parse_dtb(data, str(path))
    validate_forbidden_enabled_compatibles(
        nodes,
        contract["forbidden_enabled_compatibles"],
    )
    validate_cpu_memory_node_inventories(nodes)
    validate_thermal_policy_dtb(nodes, contract["thermal_policy"])
    for check in contract["dt_checks"]:
        validate_dt_check(nodes, check)
    return digest


def parse_arguments(arguments: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", type=Path, default=REPO / DEFAULT_PROFILE)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--metadata-only", action="store_true")
    mode.add_argument("--kernel-source", type=Path)
    parser.add_argument("--source-role", choices=("baseline", "candidate"))
    parser.add_argument("--dtb", type=Path)
    parser.add_argument("--dtb-role", choices=("baseline", "candidate"))
    options = parser.parse_args(arguments)
    if not options.metadata_only:
        for name in ("source_role", "dtb", "dtb_role"):
            if getattr(options, name) is None:
                parser.error(f"--{name.replace('_', '-')} is required with --kernel-source")
    elif any(
        getattr(options, name) is not None
        for name in ("source_role", "dtb", "dtb_role")
    ):
        parser.error("source and DTB options cannot be combined with --metadata-only")
    return options


def main(arguments: list[str]) -> int:
    options = parse_arguments(arguments)
    profile_path = safe_input_file(
        options.profile,
        "source/DTB profile",
        MAX_PROFILE_SIZE,
    )
    contract = validate_contract(
        REPO,
        read_json(profile_path, "source/DTB profile"),
    )
    print("profile=minimal-headless-v1")
    print(f"active_capabilities={len(contract['active_capabilities'])}")
    print(f"source_checks={len(contract['source_checks'])}")
    print(f"dt_checks={len(contract['dt_checks'])}")
    thermal_policy = contract["thermal_policy"]
    thermal_cpu_zones = sum(
        len(group["zone_names"])
        for group in thermal_policy["cpu_zone_groups"]
    )
    print(f"thermal_cpu_zones={thermal_cpu_zones}")
    print(
        "thermal_pmic_alarms="
        f"{len(thermal_policy['pmic_temp_alarms'])}"
    )
    print(
        "thermal_forced_fallback="
        f"{contract['thermal_fallback_status']}"
    )
    if options.metadata_only:
        print("source_role=metadata-only")
        print("dtb_role=metadata-only")
        print("authority=none")
        print("status=metadata-only")
        return 0
    source_commit = validate_source(
        options.kernel_source,
        contract,
        options.source_role,
    )
    dtb_sha256 = validate_dtb(
        options.dtb,
        contract,
        options.dtb_role,
    )
    print(f"source_role={options.source_role}")
    print(f"source_commit={source_commit}")
    print(f"dtb_role={options.dtb_role}")
    print(f"dtb_sha256={dtb_sha256}")
    print("hardware_acceptance=unproven")
    print("authority=none")
    if options.source_role == "baseline" and options.dtb_role == "baseline":
        print("status=baseline-verified")
    else:
        print("status=compatible-not-accepted")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv[1:]))
    except (
        json.JSONDecodeError,
        OSError,
        subprocess.SubprocessError,
        UnicodeDecodeError,
        ValueError,
    ) as error:
        print(f"FAIL {error}", file=sys.stderr)
        raise SystemExit(1)
