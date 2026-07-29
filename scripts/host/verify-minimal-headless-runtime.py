#!/usr/bin/env python3
"""Verify one canonical ROG5 minimal-headless runtime observation."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import stat
import sys
from typing import NoReturn


REPO = Path(__file__).resolve().parents[2]
PROFILE_PATH = Path("configs/compatibility/rog5-minimal-headless-v1.json")
PROBE_PATH = Path("scripts/device/collect-minimal-headless-runtime.sh")
FORMAT = "rog5-minimal-headless-runtime-v1"
MAX_RECORD_SIZE = 16 * 1024
SHA256 = re.compile(r"[0-9a-f]{64}\Z")
BOOT_ID = re.compile(
    r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-"
    r"[0-9a-f]{4}-[0-9a-f]{12}\Z"
)
FIELDS = (
    "format",
    "profile",
    "execution_mode",
    "probe_sha256",
    "active_capabilities",
    "candidate",
    "boot_id",
    "kernel_release",
    "machine",
    "pid1",
    "system_state",
    "default_target",
    "cpu_online_count",
    "cpu_online_set",
    "cpu_present_set",
    "cpufreq_policy_count",
    "cpufreq_policy_names",
    "cpufreq_policy_cpu_sets",
    "cpufreq_policy_drivers",
    "cpufreq_policy_governors",
    "memory_total_kib",
    "memory_available_kib",
    "root_fstype",
    "lower_source",
    "lower_read_only",
    "state_fstype",
    "state_nodev",
    "state_nosuid",
    "physical_block_devices",
    "block_backed_mounts",
    "usb_interface",
    "usb_carrier",
    "usb_ipv4_cidr",
    "sshd_state",
    "ssh_auth",
    "server_inhibitor_state",
    "failed_units",
    "fatal_kernel_signatures",
    "thermal_zone_count",
    "thermal_min_millidegree_c",
    "thermal_max_millidegree_c",
    "watchdog_state",
    "watchdog_timeout_seconds",
    "watchdog_remaining_seconds",
    "network_root_identity_format",
    "root_generation",
    "root_tree_sha256",
    "root_seal_sha256",
    "root_seal_file_sha256",
    "root_tree_entries",
    "root_subtree",
    "command_manifest_sha256",
    "command_manifest_format",
    "workload",
    "result",
)
CAPABILITIES = (
    "cpu-ram",
    "init-key-only-ssh",
    "read-only-network-root",
    "thermal-readonly",
    "usb-ncm-network",
    "watchdog-rollback-reboot",
)
EXACT_VALUES = {
    "format": FORMAT,
    "profile": "minimal-headless-v1",
    "execution_mode": "live",
    "active_capabilities": ",".join(CAPABILITIES),
    "candidate": "headless-network-root-v1",
    "machine": "aarch64",
    "pid1": "systemd",
    "system_state": "running",
    "default_target": "multi-user.target",
    "cpu_online_set": "0-7",
    "cpu_present_set": "0-7",
    "cpufreq_policy_count": "3",
    "cpufreq_policy_names": "policy0;policy4;policy7",
    "cpufreq_policy_cpu_sets": "0 1 2 3;4 5 6;7",
    "cpufreq_policy_drivers": (
        "qcom-cpufreq-hw;qcom-cpufreq-hw;qcom-cpufreq-hw"
    ),
    "cpufreq_policy_governors": "schedutil;schedutil;schedutil",
    "root_fstype": "overlay",
    "lower_source": "169.254.77.1:/",
    "lower_read_only": "1",
    "state_fstype": "tmpfs",
    "state_nodev": "1",
    "state_nosuid": "1",
    "physical_block_devices": "0",
    "block_backed_mounts": "0",
    "usb_interface": "usb0",
    "usb_carrier": "1",
    "usb_ipv4_cidr": "169.254.77.2/30",
    "sshd_state": "active",
    "ssh_auth": "key-only",
    "server_inhibitor_state": "active",
    "failed_units": "0",
    "fatal_kernel_signatures": "0",
    "watchdog_state": "armed",
    "network_root_identity_format": "rog5-network-root-identity-v1",
    "command_manifest_format": "rog5-headless-command-manifest-v1",
    "workload": "none",
    "result": "PASS",
}


class RuntimeAcceptanceError(RuntimeError):
    """A stable runtime-record refusal."""


def fail(message: str) -> NoReturn:
    raise RuntimeAcceptanceError(message)


def load_oracle_module(repo: Path):
    path = repo / "scripts/host/verify-core-compatibility-oracle.py"
    specification = importlib.util.spec_from_file_location(
        "rog5_core_compatibility_oracle",
        path,
    )
    if specification is None or specification.loader is None:
        fail("cannot load the compatibility oracle verifier")
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


def safe_repo(repo: Path) -> Path:
    lexical = Path(os.path.abspath(repo.expanduser()))
    if lexical.is_symlink():
        fail("repository path is linked")
    resolved = lexical.resolve(strict=True)
    if lexical != resolved or not resolved.is_dir() or resolved.is_symlink():
        fail("repository path is unsafe")
    return resolved


def safe_record(path: Path) -> Path:
    lexical = Path(os.path.abspath(path.expanduser()))
    if lexical.is_symlink():
        fail("runtime record is linked")
    resolved = lexical.resolve(strict=True)
    if lexical != resolved or not resolved.is_file() or resolved.is_symlink():
        fail("runtime record path is unsafe")
    metadata = resolved.stat()
    if (
        not stat.S_ISREG(metadata.st_mode)
        or metadata.st_uid != os.geteuid()
        or stat.S_IMODE(metadata.st_mode) != 0o600
        or metadata.st_nlink != 1
        or metadata.st_size <= 0
        or metadata.st_size > MAX_RECORD_SIZE
    ):
        fail("runtime record metadata is unsafe")
    return resolved


def read_stable(path: Path) -> bytes:
    descriptor = os.open(
        path,
        os.O_RDONLY | os.O_CLOEXEC | getattr(os, "O_NOFOLLOW", 0),
    )
    try:
        before = os.fstat(descriptor)
        payload = bytearray()
        while len(payload) <= MAX_RECORD_SIZE:
            block = os.read(
                descriptor,
                min(65536, MAX_RECORD_SIZE + 1 - len(payload)),
            )
            if not block:
                break
            payload.extend(block)
        data = bytes(payload)
        after = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    identity_before = (
        before.st_dev,
        before.st_ino,
        before.st_mode,
        before.st_uid,
        before.st_gid,
        before.st_nlink,
        before.st_size,
        before.st_mtime_ns,
        before.st_ctime_ns,
    )
    identity_after = (
        after.st_dev,
        after.st_ino,
        after.st_mode,
        after.st_uid,
        after.st_gid,
        after.st_nlink,
        after.st_size,
        after.st_mtime_ns,
        after.st_ctime_ns,
    )
    if len(data) != before.st_size or identity_before != identity_after:
        fail("runtime record changed while it was read")
    return data


def parse_record(data: bytes) -> dict[str, str]:
    try:
        text = data.decode("ascii")
    except UnicodeDecodeError as error:
        raise RuntimeAcceptanceError(
            "runtime record is not ASCII"
        ) from error
    if not text.endswith("\n") or "\r" in text or "\0" in text:
        fail("runtime record is not canonical LF-delimited text")
    lines = text[:-1].split("\n")
    if len(lines) != len(FIELDS):
        fail("runtime record field count changed")
    values: dict[str, str] = {}
    for expected, line in zip(FIELDS, lines, strict=True):
        key, separator, value = line.partition("=")
        if (
            separator != "="
            or key != expected
            or not value
            or "=" in value
            or value.strip() != value
            or key in values
        ):
            fail(f"runtime record field is noncanonical: {expected}")
        values[key] = value
    rendered = "".join(f"{key}={values[key]}\n" for key in FIELDS)
    if rendered.encode("ascii") != data:
        fail("runtime record encoding changed")
    return values


def canonical_decimal(value: str, label: str) -> int:
    if not re.fullmatch(r"0|[1-9][0-9]*", value):
        fail(f"{label} is not a canonical decimal")
    return int(value)


def canonical_signed_decimal(value: str, label: str) -> int:
    if not re.fullmatch(r"0|[1-9][0-9]*|-[1-9][0-9]*", value):
        fail(f"{label} is not a canonical signed decimal")
    return int(value)


def require_sha256(value: str, label: str) -> str:
    if not SHA256.fullmatch(value) or value == "0" * 64:
        fail(f"{label} is not a nonzero SHA-256")
    return value


def load_candidate(
    repo: Path,
    oracle_module,
) -> tuple[dict[str, object], dict[str, object]]:
    profile_path = repo / PROFILE_PATH
    profile = oracle_module.read_json(profile_path, "compatibility profile")
    oracle_module.validate_profile(repo, profile, None, False)
    active = tuple(
        sorted(
            row["id"]
            for row in profile["capabilities"]
            if row["phase"] == "active"
        )
    )
    if active != CAPABILITIES:
        fail("compatibility oracle active capability set changed")
    candidate_path = repo / profile["candidate"]["path"]
    try:
        candidate_data = oracle_module.read_bounded(
            candidate_path,
            "pinned recovery candidate",
        )
        if (
            hashlib.sha256(candidate_data).hexdigest()
            != profile["candidate"]["sha256"]
        ):
            fail("recovery candidate identity changed")
        candidate = json.loads(
            candidate_data,
            object_pairs_hook=oracle_module.unique_object,
        )
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise RuntimeAcceptanceError(
            "cannot load the pinned recovery candidate"
        ) from error
    if not isinstance(candidate, dict):
        fail("recovery candidate root is invalid")
    return profile, candidate


def verify_record(
    repo_path: Path,
    record_path: Path,
    expected_boot_id: str,
) -> tuple[str, dict[str, str]]:
    repo = safe_repo(repo_path)
    if not BOOT_ID.fullmatch(expected_boot_id):
        fail("expected boot identity is invalid")
    record = safe_record(record_path)
    data = read_stable(record)
    values = parse_record(data)
    for key, expected in EXACT_VALUES.items():
        if values[key] != expected:
            fail(f"runtime acceptance value changed: {key}")

    oracle_module = load_oracle_module(repo)
    _profile, candidate = load_candidate(repo, oracle_module)
    probe = repo / PROBE_PATH
    probe_hash = hashlib.sha256(
        oracle_module.read_bounded(probe, "runtime probe")
    ).hexdigest()
    if values["probe_sha256"] != probe_hash:
        fail("runtime probe identity changed")
    if values["boot_id"] != expected_boot_id:
        fail("runtime record boot identity is stale")
    if values["kernel_release"] != candidate.get("target_release"):
        fail("runtime kernel does not match the candidate")

    cpu_online = canonical_decimal(
        values["cpu_online_count"], "online CPU count"
    )
    memory_total = canonical_decimal(
        values["memory_total_kib"], "total memory"
    )
    memory_available = canonical_decimal(
        values["memory_available_kib"], "available memory"
    )
    if cpu_online != 8:
        fail("runtime does not have exactly eight online CPUs")
    if memory_total < 10 * 1024 * 1024:
        fail("runtime total memory is below the accepted baseline")
    if (
        memory_available < 8 * 1024 * 1024
        or memory_available > memory_total
    ):
        fail("runtime available memory is outside the headless envelope")

    thermal_count = canonical_decimal(
        values["thermal_zone_count"], "thermal zone count"
    )
    thermal_min = canonical_signed_decimal(
        values["thermal_min_millidegree_c"], "minimum thermal value"
    )
    thermal_max = canonical_signed_decimal(
        values["thermal_max_millidegree_c"], "maximum thermal value"
    )
    if thermal_count < 30 or thermal_count > 128:
        fail("runtime thermal-zone count is outside the accepted envelope")
    if (
        thermal_min < -20000
        or thermal_max > 120000
        or thermal_min > thermal_max
    ):
        fail("runtime thermal values are outside the safety envelope")

    timeout = canonical_decimal(
        values["watchdog_timeout_seconds"], "watchdog timeout"
    )
    remaining = canonical_decimal(
        values["watchdog_remaining_seconds"], "watchdog remaining time"
    )
    expected_timeout = canonical_decimal(
        str(candidate.get("rollback_timeout", "")),
        "candidate rollback timeout",
    )
    if timeout != expected_timeout:
        fail("runtime watchdog timeout does not match the candidate")
    if remaining < 60 or remaining > timeout:
        fail("runtime watchdog remaining time is outside the live gate")

    candidate_matches = {
        "root_generation": candidate.get("root_generation"),
        "root_tree_sha256": candidate.get("root_tree_sha256"),
        "root_seal_sha256": candidate.get("root_seal_sha256"),
        "root_seal_file_sha256": candidate.get("root_seal_sha256"),
        "root_tree_entries": candidate.get("root_tree_entries"),
        "root_subtree": candidate.get("root_subtree"),
        "command_manifest_sha256": candidate.get(
            "a660_command_manifest_sha256"
        ),
    }
    for key, expected in candidate_matches.items():
        if values[key] != expected:
            fail(f"runtime root identity does not match candidate: {key}")
    for key in (
        "probe_sha256",
        "root_tree_sha256",
        "root_seal_sha256",
        "root_seal_file_sha256",
        "command_manifest_sha256",
    ):
        require_sha256(values[key], key)

    return hashlib.sha256(data).hexdigest(), values


def parse_arguments(arguments: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=REPO)
    parser.add_argument("--record", type=Path, required=True)
    parser.add_argument("--expected-boot-id", required=True)
    return parser.parse_args(arguments)


def main(arguments: list[str]) -> int:
    options = parse_arguments(arguments)
    try:
        digest, values = verify_record(
            options.repo,
            options.record,
            options.expected_boot_id,
        )
    except (OSError, RuntimeAcceptanceError, ValueError) as error:
        print(f"FAIL {error}", file=sys.stderr)
        return 1
    print(
        "PASS minimal headless runtime acceptance "
        f"active_capabilities={len(CAPABILITIES)} "
        f"record_sha256={digest} "
        "boot_id=verified "
        f"kernel={values['kernel_release']} "
        f"memory_available_kib={values['memory_available_kib']} "
        f"thermal_zones={values['thermal_zone_count']} "
        f"watchdog_remaining_seconds={values['watchdog_remaining_seconds']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
