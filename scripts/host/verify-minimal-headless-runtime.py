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
CANDIDATE_TOOL_PATH = Path("scripts/host/prepare-recovery-candidate.py")
FORMAT = "rog5-minimal-headless-runtime-v1"
MAX_RECORD_SIZE = 16 * 1024
MAX_CANDIDATE_SIZE = 64 * 1024
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
    "overlay_mount_id",
    "overlay_lower_mount_id",
    "state_mount_id",
    "overlay_lowerdir",
    "overlay_upperdir",
    "overlay_workdir",
    "root_fstype",
    "lower_fstype",
    "lower_source",
    "lower_nfs_version",
    "lower_transport",
    "lower_read_only",
    "state_fstype",
    "state_nodev",
    "state_nosuid",
    "block_device_count",
    "physical_block_devices",
    "scsi_host_count",
    "rpmb_device_count",
    "ufs_platform_device_count",
    "block_backed_mounts",
    "usb_gadget",
    "usb_vid_pid",
    "usb_product",
    "usb_configuration",
    "usb_function",
    "usb_udc_controller",
    "usb_current_speed",
    "usb_interface",
    "usb_carrier",
    "usb_operstate",
    "usb_mtu",
    "usb_ipv4_cidr",
    "usb_route_cidr",
    "usb_default_route_count",
    "sshd_state",
    "ssh_port",
    "ssh_session_count",
    "ssh_session_local",
    "ssh_session_peer",
    "ssh_authorized_key_type",
    "ssh_authorized_key_bits",
    "ssh_host_key_type",
    "ssh_host_key_bits",
    "ssh_host_key_pair_match",
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
HISTORICAL_PROFILE = "historical-headless-network-root-v1"
DEPLOYMENT_PROFILE = "headless-ssh-deployment-v3"
DIAGNOSTIC_PROFILE = "diagnostic-initramfs-v1"
HISTORICAL_CANDIDATE = "headless-network-root-v1"
DEPLOYMENT_CANDIDATE = "headless-ssh-network-root-v3"
DEPLOYMENT_BUNDLE = "headless-ssh-network-root-v3-r2"
DEPLOYMENT_TARGET = "headless-ssh-network-root"
DIAGNOSTIC_CANDIDATE = "headless-netroot-early-diag-v2"
DIAGNOSTIC_BUNDLE = "headless-netroot-early-diag-v2"
DIAGNOSTIC_TARGET = "headless-netroot-early-diag-v2"
DEPLOYMENT_RELEASE = "7.1.4-g7a5cef0db479"
EXTERNAL_PROFILES = {
    DEPLOYMENT_PROFILE: {
        "candidate": DEPLOYMENT_CANDIDATE,
        "bundle": DEPLOYMENT_BUNDLE,
        "profile": "network-root-v1",
        "target": DEPLOYMENT_TARGET,
    },
    DIAGNOSTIC_PROFILE: {
        "candidate": DIAGNOSTIC_CANDIDATE,
        "bundle": DIAGNOSTIC_BUNDLE,
        "profile": DIAGNOSTIC_PROFILE,
        "target": DIAGNOSTIC_TARGET,
    },
}
FIXTURE_TREE_SHA256 = (
    "6f8a8f11bfb581bb52ca7d590141ce46"
    "5b8d48d8f9f4577a076b7a37604a2fd5"
)
FIXTURE_SEAL_SHA256 = (
    "f443a47c456b33d670e6efd4a2e20cff"
    "2bc72061e7661472694acfbba45c8d5a"
)
EXACT_VALUES = {
    "format": FORMAT,
    "profile": "minimal-headless-v1",
    "execution_mode": "live",
    "active_capabilities": ",".join(CAPABILITIES),
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
    "overlay_lowerdir": "/mnt/root-ro",
    "overlay_upperdir": "/mnt/state/upper",
    "overlay_workdir": "/mnt/state/work",
    "root_fstype": "overlay",
    "lower_fstype": "nfs4",
    "lower_source": "169.254.77.1:/",
    "lower_nfs_version": "4.2",
    "lower_transport": "tcp",
    "lower_read_only": "1",
    "state_fstype": "tmpfs",
    "state_nodev": "1",
    "state_nosuid": "1",
    "block_device_count": "9",
    "physical_block_devices": "0",
    "scsi_host_count": "0",
    "rpmb_device_count": "0",
    "ufs_platform_device_count": "0",
    "block_backed_mounts": "0",
    "usb_gadget": "rog5-network-root",
    "usb_vid_pid": "1d6b:0104",
    "usb_product": "ROG5 network root",
    "usb_configuration": "NFS root over NCM",
    "usb_function": "ncm.usb0",
    "usb_udc_controller": "a600000",
    "usb_current_speed": "high-speed",
    "usb_interface": "usb0",
    "usb_carrier": "1",
    "usb_operstate": "up",
    "usb_mtu": "1500",
    "usb_ipv4_cidr": "169.254.77.2/30",
    "usb_route_cidr": "169.254.77.0/30",
    "usb_default_route_count": "0",
    "sshd_state": "active",
    "ssh_port": "22",
    "ssh_session_count": "1",
    "ssh_session_local": "169.254.77.2:22",
    "ssh_session_peer": "169.254.77.1",
    "ssh_authorized_key_type": "ssh-ed25519",
    "ssh_authorized_key_bits": "256",
    "ssh_host_key_type": "ssh-ed25519",
    "ssh_host_key_bits": "256",
    "ssh_host_key_pair_match": "1",
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


def load_candidate_module(repo: Path):
    path = repo / CANDIDATE_TOOL_PATH
    specification = importlib.util.spec_from_file_location(
        "rog5_runtime_candidate",
        path,
    )
    if specification is None or specification.loader is None:
        fail("cannot load the recovery candidate verifier")
    module = importlib.util.module_from_spec(specification)
    sys.modules[specification.name] = module
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


def load_compatibility_profile(
    repo: Path,
    oracle_module,
) -> dict[str, object]:
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
    return profile


def load_historical_candidate(
    repo: Path,
    oracle_module,
    profile: dict[str, object],
) -> dict[str, object]:
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
    return candidate


def safe_external_candidate(repo: Path, path: Path) -> Path:
    if not path.is_absolute():
        fail("deployment candidate path must be absolute")
    lexical = Path(os.path.abspath(path.expanduser()))
    if lexical.is_symlink():
        fail("deployment candidate is linked")
    resolved = lexical.resolve(strict=True)
    if lexical != resolved or not resolved.is_file() or resolved.is_symlink():
        fail("deployment candidate path is unsafe")
    try:
        resolved.relative_to(repo)
    except ValueError:
        pass
    else:
        fail("deployment candidate must remain outside the repository")
    metadata = resolved.stat()
    if (
        not stat.S_ISREG(metadata.st_mode)
        or metadata.st_uid != os.geteuid()
        or stat.S_IMODE(metadata.st_mode) not in {0o400, 0o444}
        or metadata.st_nlink != 1
        or metadata.st_size <= 0
        or metadata.st_size > MAX_CANDIDATE_SIZE
    ):
        fail("deployment candidate metadata is unsafe")
    return resolved


def read_external_candidate(path: Path) -> bytes:
    descriptor = os.open(
        path,
        os.O_RDONLY | os.O_CLOEXEC | getattr(os, "O_NOFOLLOW", 0),
    )
    try:
        before = os.fstat(descriptor)
        payload = bytearray()
        while len(payload) <= MAX_CANDIDATE_SIZE:
            block = os.read(
                descriptor,
                min(65536, MAX_CANDIDATE_SIZE + 1 - len(payload)),
            )
            if not block:
                break
            payload.extend(block)
        after = os.fstat(descriptor)
        named = path.lstat()
    finally:
        os.close(descriptor)
    identity = lambda value: (
        value.st_dev,
        value.st_ino,
        value.st_mode,
        value.st_uid,
        value.st_gid,
        value.st_nlink,
        value.st_size,
        value.st_mtime_ns,
        value.st_ctime_ns,
    )
    if (
        len(payload) != before.st_size
        or identity(before) != identity(after)
        or identity(before) != identity(named)
    ):
        fail("deployment candidate changed while it was read")
    return bytes(payload)


def load_deployment_candidate(
    repo: Path,
    path: Path | None,
    expected_sha256: str,
    deployment_profile: str = DEPLOYMENT_PROFILE,
) -> dict[str, object]:
    expected = EXTERNAL_PROFILES.get(deployment_profile)
    if expected is None:
        fail("runtime deployment profile is unsupported")
    if path is None:
        fail("deployment candidate record is required")
    require_sha256(expected_sha256, "deployment candidate identity")
    candidate_path = safe_external_candidate(repo, path)
    before = read_external_candidate(candidate_path)
    if hashlib.sha256(before).hexdigest() != expected_sha256:
        fail("deployment candidate identity changed")
    candidate_module = load_candidate_module(repo)
    try:
        candidate = candidate_module.load_candidate_path(
            candidate_path,
            expected["candidate"],
        )
    except candidate_module.CandidateError as error:
        raise RuntimeAcceptanceError(
            "deployment candidate record is invalid"
        ) from error
    after = read_external_candidate(candidate_path)
    if before != after:
        fail("deployment candidate changed during validation")
    if (
        candidate.get("candidate") != expected["candidate"]
        or candidate.get("bundle") != expected["bundle"]
        or candidate.get("status") != "offline"
        or candidate.get("authority") != "none"
        or candidate.get("profile") != expected["profile"]
        or candidate.get("target_id") != expected["target"]
        or candidate.get("target_release") != DEPLOYMENT_RELEASE
        or candidate.get("rollback_timeout") != "600"
        or candidate.get("target_timeout") != "480"
    ):
        fail("deployment candidate tuple is unsupported")
    if (
        candidate.get("root_tree_sha256") == FIXTURE_TREE_SHA256
        or candidate.get("root_seal_sha256") == FIXTURE_SEAL_SHA256
    ):
        fail("deployment candidate still carries fixture root identity")
    return candidate


def select_candidate(
    repo: Path,
    oracle_module,
    deployment_profile: str,
    candidate_record: Path | None,
    candidate_sha256: str,
) -> tuple[str, dict[str, object]]:
    profile = load_compatibility_profile(repo, oracle_module)
    if deployment_profile == HISTORICAL_PROFILE:
        if candidate_record is not None or candidate_sha256:
            fail("historical profile does not accept a dynamic candidate")
        return (
            HISTORICAL_CANDIDATE,
            load_historical_candidate(repo, oracle_module, profile),
        )
    if deployment_profile in EXTERNAL_PROFILES:
        expected = EXTERNAL_PROFILES[deployment_profile]
        return (
            expected["candidate"],
            load_deployment_candidate(
                repo,
                candidate_record,
                candidate_sha256,
                deployment_profile,
            ),
        )
    fail("runtime deployment profile is unsupported")


def verify_record(
    repo_path: Path,
    record_path: Path,
    expected_boot_id: str,
    deployment_profile: str = HISTORICAL_PROFILE,
    candidate_record: Path | None = None,
    candidate_sha256: str = "",
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
    expected_candidate, candidate = select_candidate(
        repo,
        oracle_module,
        deployment_profile,
        candidate_record,
        candidate_sha256,
    )
    if values["candidate"] != expected_candidate:
        fail("runtime candidate does not match the deployment profile")
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

    mount_ids = tuple(
        canonical_decimal(values[key], f"{key} storage mount ID")
        for key in (
            "overlay_mount_id",
            "overlay_lower_mount_id",
            "state_mount_id",
        )
    )
    if 0 in mount_ids or len(set(mount_ids)) != len(mount_ids):
        fail("runtime storage mount identities are zero or duplicated")

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
    parser.add_argument(
        "--deployment-profile",
        default=HISTORICAL_PROFILE,
        choices=(
            HISTORICAL_PROFILE,
            DEPLOYMENT_PROFILE,
            DIAGNOSTIC_PROFILE,
        ),
    )
    parser.add_argument("--candidate-record", type=Path)
    parser.add_argument("--candidate-sha256", default="")
    return parser.parse_args(arguments)


def main(arguments: list[str]) -> int:
    options = parse_arguments(arguments)
    try:
        digest, values = verify_record(
            options.repo,
            options.record,
            options.expected_boot_id,
            options.deployment_profile,
            options.candidate_record,
            options.candidate_sha256,
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
