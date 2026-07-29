#!/usr/bin/env python3
"""Verify the ROG Phone 5 minimal-headless compatibility ancestry."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys
from typing import Any, NoReturn


FORMAT = "rog5-core-compatibility-oracle-v1"
DEFAULT_PROFILE = Path(
    "configs/compatibility/rog5-minimal-headless-v1.json"
)
MAX_TEXT_SIZE = 4 * 1024 * 1024
SHA256 = re.compile(r"[0-9a-f]{64}")
SYMBOL = re.compile(r"CONFIG_[A-Za-z0-9_]+")
REQUIRED_CAPABILITIES = {
    "audio",
    "battery-charging",
    "buttons-indicators",
    "cpu-ram",
    "display-off-server",
    "init-key-only-ssh",
    "read-only-network-root",
    "sensors",
    "suspend-resume",
    "thermal-readonly",
    "usb-ncm-network",
    "watchdog-rollback-reboot",
}
ACTIVE_CAPABILITIES = {
    "cpu-ram",
    "init-key-only-ssh",
    "read-only-network-root",
    "thermal-readonly",
    "usb-ncm-network",
    "watchdog-rollback-reboot",
}
ROOT_KEYS = {
    "format",
    "profile",
    "status",
    "authority",
    "artifact_manifest",
    "artifact_manifest_sha256",
    "baseline",
    "evidence",
    "artifacts",
    "equivalence_sets",
    "candidate",
    "integration",
    "capabilities",
}
BASELINE_KEYS = {
    "vendor_release",
    "accepted_target_release",
    "accepted_target_state",
    "new_root_state",
}
EVIDENCE_KEYS = {"id", "path", "sha256", "markers"}
ARTIFACT_KEYS = {"id", "path", "size", "sha256"}
CANDIDATE_KEYS = {"path", "sha256", "identity", "artifact_links"}
INTEGRATION_KEYS = {"ci_entrypoint", "ci_test", "build_verifier"}
CAPABILITY_KEYS = {
    "id",
    "phase",
    "candidate_status",
    "baseline_evidence",
    "required_config",
    "minimum_integer_config",
    "forbidden_config",
    "ci_gates",
}
FUTURE_STATUS = {
    "baseline-only",
    "baseline-diagnostic-partial",
    "baseline-diagnostic-readonly",
    "pending",
}
CANDIDATE_IDENTITY = {
    "format": "rog5-recovery-candidate-v1",
    "candidate": "headless-network-root-v1",
    "status": "offline",
    "authority": "none",
    "profile": "network-root-v1",
    "target_id": "headless-network-root",
    "target_release": "7.1.4-g7a5cef0db479",
}
INTEGRATION_IDENTITY = {
    "ci_entrypoint": "scripts/host/test-repository-linux.sh",
    "ci_test": "scripts/host/test-core-compatibility-oracle.py",
    "build_verifier": "scripts/device/verify-mainline-network-root-build.sh",
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


def require_object(
    value: Any,
    expected_keys: set[str],
    label: str,
) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != expected_keys:
        fail(f"{label} fields are not canonical")
    return value


def require_string(value: Any, label: str) -> str:
    if (
        not isinstance(value, str)
        or not value
        or value.strip() != value
        or any(ord(character) < 0x20 or ord(character) == 0x7F for character in value)
    ):
        fail(f"{label} is not a canonical nonempty string")
    return value


def require_sha256(value: Any, label: str) -> str:
    text = require_string(value, label)
    if not SHA256.fullmatch(text):
        fail(f"{label} is not a lowercase SHA-256")
    return text


def safe_input_file(value: Path, label: str) -> Path:
    lexical = Path(os.path.abspath(value.expanduser()))
    if lexical.is_symlink():
        fail(f"{label} is linked")
    resolved = lexical.resolve(strict=True)
    if lexical != resolved:
        fail(f"{label} contains a linked path component")
    if not resolved.is_file() or resolved.is_symlink():
        fail(f"{label} is not an ordinary file")
    return resolved


def safe_relative_path(repo: Path, value: Any, label: str) -> tuple[str, Path]:
    raw = require_string(value, label)
    relative = Path(raw)
    if relative.is_absolute() or not relative.parts:
        fail(f"{label} is not a relative repository path")
    if any(part in {"", ".", ".."} for part in relative.parts):
        fail(f"{label} contains an unsafe path component")
    lexical = repo.joinpath(relative)
    resolved = lexical.resolve(strict=True)
    if lexical.absolute() != resolved:
        fail(f"{label} is linked or escapes the repository")
    if not resolved.is_file() or resolved.is_symlink():
        fail(f"{label} is not an ordinary file")
    return raw, resolved


def read_bounded(path: Path, label: str) -> bytes:
    descriptor = os.open(
        path,
        os.O_RDONLY | os.O_CLOEXEC | getattr(os, "O_NOFOLLOW", 0),
    )
    try:
        before = os.fstat(descriptor)
        if (
            not stat.S_ISREG(before.st_mode)
            or before.st_size <= 0
            or before.st_size > MAX_TEXT_SIZE
        ):
            fail(f"{label} has an invalid size")
        with os.fdopen(descriptor, "rb", closefd=False) as stream:
            data = stream.read(MAX_TEXT_SIZE + 1)
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


def canonical_lf_lines(data: bytes, label: str) -> list[str]:
    text = data.decode("utf-8")
    if not text.endswith("\n") or "\r" in text or "\0" in text:
        fail(f"{label} is not canonical LF-delimited text")
    return text[:-1].split("\n")


def read_json(path: Path, label: str) -> dict[str, Any]:
    value = json.loads(
        read_bounded(path, label),
        object_pairs_hook=unique_object,
    )
    if not isinstance(value, dict):
        fail(f"{label} root is not an object")
    return value


def validate_evidence(
    repo: Path,
    rows: Any,
) -> dict[str, dict[str, Any]]:
    if not isinstance(rows, list) or not rows:
        fail("evidence inventory is absent")
    evidence: dict[str, dict[str, Any]] = {}
    for index, raw in enumerate(rows):
        row = require_object(raw, EVIDENCE_KEYS, f"evidence[{index}]")
        identity = require_string(row["id"], f"evidence[{index}].id")
        if identity in evidence:
            fail(f"duplicate evidence identity: {identity}")
        path_text, path = safe_relative_path(
            repo, row["path"], f"evidence[{identity}].path"
        )
        expected_hash = require_sha256(
            row["sha256"], f"evidence[{identity}].sha256"
        )
        data = read_bounded(path, f"evidence[{identity}]")
        if hashlib.sha256(data).hexdigest() != expected_hash:
            fail(f"evidence hash changed: {identity}")
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            fail(f"evidence is not UTF-8: {identity}")
        markers = row["markers"]
        if not isinstance(markers, list) or not markers:
            fail(f"evidence markers are absent: {identity}")
        seen: set[str] = set()
        for marker_raw in markers:
            marker = require_string(
                marker_raw, f"evidence[{identity}].marker"
            )
            if marker in seen:
                fail(f"evidence marker is duplicate: {identity}")
            if len(marker) < 12 or marker not in text:
                fail(f"evidence marker is invalid or absent: {identity}")
            seen.add(marker)
        evidence[identity] = {
            "path": path_text,
            "sha256": expected_hash,
        }
    return evidence


def load_artifact_manifest(
    path: Path,
    expected_sha256: str,
) -> dict[str, tuple[int, str]]:
    data = read_bounded(path, "artifact manifest")
    if hashlib.sha256(data).hexdigest() != expected_sha256:
        fail("artifact manifest hash changed")
    lines = canonical_lf_lines(data, "artifact manifest")
    if not lines or lines[0] != "name\tsize\tsha256\trole\ttracked":
        fail("artifact manifest header is not canonical")
    result: dict[str, tuple[int, str]] = {}
    for number, line in enumerate(lines[1:], 2):
        fields = line.split("\t")
        if len(fields) != 5:
            fail(f"artifact manifest row {number} is malformed")
        name, size_raw, digest, role, tracked = fields
        if (
            not name
            or name in result
            or not role
            or tracked not in {"yes", "no"}
            or not SHA256.fullmatch(digest)
        ):
            fail(f"artifact manifest row {number} is noncanonical")
        if not size_raw.isdecimal():
            fail(f"artifact manifest row {number} has an invalid size")
        size = int(size_raw)
        if size <= 0 or str(size) != size_raw:
            fail(f"artifact manifest row {number} has an invalid size")
        result[name] = (size, digest)
    return result


def validate_artifacts(
    rows: Any,
    manifest: dict[str, tuple[int, str]],
) -> dict[str, dict[str, Any]]:
    if not isinstance(rows, list) or not rows:
        fail("artifact oracle is absent")
    artifacts: dict[str, dict[str, Any]] = {}
    for index, raw in enumerate(rows):
        row = require_object(raw, ARTIFACT_KEYS, f"artifact[{index}]")
        identity = require_string(row["id"], f"artifact[{index}].id")
        path = require_string(row["path"], f"artifact[{identity}].path")
        relative = Path(path)
        if (
            relative.is_absolute()
            or not relative.parts
            or any(part in {"", ".", ".."} for part in relative.parts)
        ):
            fail(f"artifact path is unsafe: {identity}")
        size = row["size"]
        if not isinstance(size, int) or isinstance(size, bool) or size <= 0:
            fail(f"artifact size is invalid: {identity}")
        digest = require_sha256(row["sha256"], f"artifact[{identity}].sha256")
        if identity in artifacts:
            fail(f"duplicate artifact identity: {identity}")
        if manifest.get(path) != (size, digest):
            fail(f"artifact manifest identity changed: {identity}")
        artifacts[identity] = {
            "path": path,
            "size": size,
            "sha256": digest,
        }
    return artifacts


def validate_equivalence_sets(
    rows: Any,
    artifacts: dict[str, dict[str, Any]],
) -> None:
    if not isinstance(rows, list) or not rows:
        fail("artifact equivalence sets are absent")
    for index, raw in enumerate(rows):
        if not isinstance(raw, list) or len(raw) < 2:
            fail(f"artifact equivalence set {index} is invalid")
        artifact_ids = [
            require_string(item, f"artifact equivalence set {index}")
            for item in raw
        ]
        if len(set(artifact_ids)) != len(artifact_ids):
            fail(f"artifact equivalence set {index} is invalid")
        try:
            identities = [artifacts[item] for item in artifact_ids]
        except KeyError as error:
            fail(f"artifact equivalence references unknown identity: {error}")
        expected = (identities[0]["size"], identities[0]["sha256"])
        if any(
            (item["size"], item["sha256"]) != expected
            for item in identities[1:]
        ):
            fail(f"artifact equivalence set {index} differs")


def validate_candidate(
    repo: Path,
    raw: Any,
    artifacts: dict[str, dict[str, Any]],
) -> None:
    candidate = require_object(raw, CANDIDATE_KEYS, "candidate")
    _path_text, path = safe_relative_path(
        repo, candidate["path"], "candidate.path"
    )
    digest = require_sha256(candidate["sha256"], "candidate.sha256")
    data = read_bounded(path, "candidate")
    if hashlib.sha256(data).hexdigest() != digest:
        fail("candidate identity file hash changed")
    parsed = json.loads(data, object_pairs_hook=unique_object)
    if not isinstance(parsed, dict):
        fail("candidate identity root is not an object")
    identity = candidate["identity"]
    if identity != CANDIDATE_IDENTITY:
        fail("candidate identity contract is not canonical")
    for key, expected in identity.items():
        if key not in parsed:
            fail(f"candidate identity field is absent: {key}")
        if parsed[key] != expected:
            fail(f"candidate identity field changed: {key}")
    if parsed.get("status") != "offline" or parsed.get("authority") != "none":
        fail("candidate has live authority")
    links = candidate["artifact_links"]
    if not isinstance(links, dict) or not links:
        fail("candidate artifact links are absent")
    candidate_artifacts = parsed.get("artifacts")
    if (
        not isinstance(candidate_artifacts, dict)
        or set(candidate_artifacts) != set(links)
    ):
        fail("candidate artifact inventory differs from the oracle")
    for name, artifact_id_raw in links.items():
        artifact_id = require_string(
            artifact_id_raw, f"candidate artifact link {name}"
        )
        if artifact_id not in artifacts:
            fail(f"candidate references unknown artifact oracle: {artifact_id}")
        expected_artifact = artifacts[artifact_id]
        actual = candidate_artifacts[name]
        if (
            not isinstance(actual, dict)
            or actual.get("path") != expected_artifact["path"]
            or actual.get("size") != expected_artifact["size"]
            or actual.get("sha256") != expected_artifact["sha256"]
        ):
            fail(f"candidate artifact ancestry changed: {name}")


def require_executable(path: Path, label: str) -> None:
    if not os.access(path, os.X_OK):
        fail(f"{label} is not executable")


def validate_capabilities(
    repo: Path,
    rows: Any,
    evidence: dict[str, dict[str, Any]],
    ci_source: str,
) -> list[dict[str, Any]]:
    if not isinstance(rows, list) or not rows:
        fail("capability inventory is absent")
    capabilities: list[dict[str, Any]] = []
    identities: set[str] = set()
    for index, raw in enumerate(rows):
        row = require_object(raw, CAPABILITY_KEYS, f"capability[{index}]")
        identity = require_string(row["id"], f"capability[{index}].id")
        if identity in identities:
            fail(f"duplicate capability identity: {identity}")
        identities.add(identity)
        phase = row["phase"]
        status = row["candidate_status"]
        if phase not in {"active", "future"}:
            fail(f"capability phase is invalid: {identity}")
        if phase == "active" and status != "accepted-ancestry":
            fail(f"active capability is not accepted ancestry: {identity}")
        if phase == "future" and status not in FUTURE_STATUS:
            fail(f"future capability status is invalid: {identity}")
        references = row["baseline_evidence"]
        if not isinstance(references, list):
            fail(f"capability evidence list is invalid: {identity}")
        reference_ids = [
            require_string(
                reference,
                f"capability[{identity}].baseline_evidence",
            )
            for reference in references
        ]
        if len(set(reference_ids)) != len(reference_ids):
            fail(f"capability evidence list is invalid: {identity}")
        if phase == "active" and not references:
            fail(f"active capability has no baseline evidence: {identity}")
        for reference in reference_ids:
            if reference not in evidence:
                fail(f"capability references unknown evidence: {identity}")
        required = row["required_config"]
        minimum = row["minimum_integer_config"]
        forbidden = row["forbidden_config"]
        gates = row["ci_gates"]
        if not isinstance(required, dict) or not isinstance(minimum, dict):
            fail(f"capability config contract is invalid: {identity}")
        if not isinstance(forbidden, list):
            fail(f"capability forbidden config is invalid: {identity}")
        forbidden_symbols = [
            require_string(
                symbol,
                f"capability[{identity}].forbidden_config",
            )
            for symbol in forbidden
        ]
        if len(set(forbidden_symbols)) != len(forbidden_symbols):
            fail(f"capability forbidden config is invalid: {identity}")
        for symbol, value in required.items():
            if not SYMBOL.fullmatch(symbol) or value not in {"y", "m"}:
                fail(f"capability required config is invalid: {identity}")
        for symbol, value in minimum.items():
            if (
                not SYMBOL.fullmatch(symbol)
                or not isinstance(value, int)
                or isinstance(value, bool)
                or value <= 0
            ):
                fail(f"capability minimum config is invalid: {identity}")
        if set(required) & set(minimum):
            fail(f"capability config contract overlaps: {identity}")
        for symbol in forbidden_symbols:
            if (
                not SYMBOL.fullmatch(symbol)
                or symbol in required
                or symbol in minimum
            ):
                fail(f"capability forbidden symbol is invalid: {identity}")
        if not isinstance(gates, list):
            fail(f"capability CI gate list is invalid: {identity}")
        gate_names = [
            require_string(gate, f"capability[{identity}].ci_gates")
            for gate in gates
        ]
        if len(set(gate_names)) != len(gate_names):
            fail(f"capability CI gate list is invalid: {identity}")
        if phase == "active" and (not gates or not required):
            fail(f"active capability lacks config or CI gates: {identity}")
        for gate_raw in gate_names:
            gate_text, gate = safe_relative_path(
                repo, gate_raw, f"capability[{identity}].gate"
            )
            require_executable(gate, f"capability gate {identity}")
            if phase == "active" and not source_has_exact_line(
                ci_source,
                gate_text,
            ):
                fail(f"active capability gate is absent from CI: {gate_text}")
        capabilities.append(row)
    if identities != REQUIRED_CAPABILITIES:
        fail("capability inventory does not cover the complete core roadmap")
    active = {
        row["id"] for row in capabilities if row["phase"] == "active"
    }
    if active != ACTIVE_CAPABILITIES:
        fail("active minimal-headless capability set is not canonical")
    return capabilities


def parse_kernel_config(path: Path) -> dict[str, str]:
    if path.is_symlink() or not path.is_file():
        fail("kernel config is not an ordinary file")
    lines = canonical_lf_lines(
        read_bounded(path, "kernel config"),
        "kernel config",
    )
    result: dict[str, str] = {}
    disabled = re.compile(r"# (CONFIG_[A-Za-z0-9_]+) is not set")
    enabled = re.compile(r"(CONFIG_[A-Za-z0-9_]+)=(.+)")
    for number, line in enumerate(lines, 1):
        match = disabled.fullmatch(line)
        if match:
            symbol, value = match.group(1), "n"
        else:
            match = enabled.fullmatch(line)
            if not match:
                if line.startswith("CONFIG_"):
                    fail(f"kernel config line {number} is malformed")
                continue
            symbol, value = match.groups()
        if symbol in result:
            fail(f"kernel config contains duplicate symbol: {symbol}")
        result[symbol] = value
    return result


def validate_kernel_config(
    config: dict[str, str],
    capabilities: list[dict[str, Any]],
    include_future: bool,
) -> int:
    required: dict[str, str] = {}
    minimum: dict[str, int] = {}
    forbidden: set[str] = set()
    selected = [
        row
        for row in capabilities
        if row["phase"] == "active" or include_future
    ]
    for row in selected:
        for symbol, value in row["required_config"].items():
            if symbol in required and required[symbol] != value:
                fail(f"capability config requirements conflict: {symbol}")
            if symbol in forbidden or symbol in minimum:
                fail(f"capability config requirements conflict: {symbol}")
            required[symbol] = value
        for symbol, value in row["minimum_integer_config"].items():
            if symbol in required or symbol in forbidden:
                fail(f"capability config requirements conflict: {symbol}")
            minimum[symbol] = max(minimum.get(symbol, 0), value)
        for symbol in row["forbidden_config"]:
            if symbol in required or symbol in minimum:
                fail(f"capability config allow/forbid conflict: {symbol}")
            forbidden.add(symbol)
    for symbol, expected in sorted(required.items()):
        if config.get(symbol) != expected:
            fail(f"kernel config violates oracle: {symbol}={expected}")
    for symbol, expected in sorted(minimum.items()):
        actual = config.get(symbol)
        if (
            actual is None
            or not re.fullmatch(r"(?:0|[1-9][0-9]*|0x[0-9A-Fa-f]+)", actual)
            or int(actual, 0) < expected
        ):
            fail(f"kernel config is below oracle minimum: {symbol}>={expected}")
    for symbol in sorted(forbidden):
        if config.get(symbol, "n") != "n":
            fail(f"kernel config enables forbidden oracle symbol: {symbol}")
    return len(selected)


def validate_integration(
    repo: Path,
    raw: Any,
) -> tuple[str, str]:
    integration = require_object(raw, INTEGRATION_KEYS, "integration")
    if integration != INTEGRATION_IDENTITY:
        fail("integration identity is not canonical")
    ci_text, ci_path = safe_relative_path(
        repo, integration["ci_entrypoint"], "integration.ci_entrypoint"
    )
    test_text, test_path = safe_relative_path(
        repo, integration["ci_test"], "integration.ci_test"
    )
    build_text, build_path = safe_relative_path(
        repo, integration["build_verifier"], "integration.build_verifier"
    )
    require_executable(ci_path, "CI entrypoint")
    require_executable(test_path, "compatibility oracle test")
    require_executable(build_path, "kernel build verifier")
    ci_source = read_bounded(ci_path, "CI entrypoint").decode("utf-8")
    if not source_has_exact_line(ci_source, test_text):
        fail("compatibility oracle test is absent from CI")
    build_source = read_bounded(
        build_path, "kernel build verifier"
    ).decode("utf-8")
    for line in (
        "compatibility_oracle=$repo/scripts/host/"
        "verify-core-compatibility-oracle.py",
        "compatibility_profile=$repo/configs/compatibility/"
        "rog5-minimal-headless-v1.json",
        '"$compatibility_oracle" \\',
        '--repo "$repo" \\',
        '--profile "$compatibility_profile" \\',
        '--kernel-config "$config"',
    ):
        if not source_has_exact_line(build_source, line):
            fail(f"kernel build verifier omits compatibility line: {line}")
    return ci_source, build_text


def source_has_exact_line(source: str, expected: str) -> bool:
    return any(line.strip() == expected for line in source.split("\n"))


def validate_profile(
    repo: Path,
    profile: dict[str, Any],
    kernel_config: Path | None,
    include_future: bool,
) -> tuple[int, int, str]:
    root = require_object(profile, ROOT_KEYS, "profile")
    if root["format"] != FORMAT:
        fail("compatibility profile format is unsupported")
    if (
        root["profile"] != "minimal-headless-v1"
        or root["status"] != "offline"
        or root["authority"] != "none"
    ):
        fail("compatibility profile identity or authority is invalid")
    baseline = require_object(root["baseline"], BASELINE_KEYS, "baseline")
    if baseline != {
        "vendor_release": "5.4.210-qgki-perf",
        "accepted_target_release": "7.1.4-g7a5cef0db479",
        "accepted_target_state": "network-root-v3-live",
        "new_root_state": "live-pending",
    }:
        fail("compatibility baseline identity is not canonical")
    evidence = validate_evidence(repo, root["evidence"])
    _manifest_text, manifest_path = safe_relative_path(
        repo, root["artifact_manifest"], "artifact_manifest"
    )
    manifest_sha256 = require_sha256(
        root["artifact_manifest_sha256"],
        "artifact_manifest_sha256",
    )
    artifacts = validate_artifacts(
        root["artifacts"],
        load_artifact_manifest(manifest_path, manifest_sha256),
    )
    validate_equivalence_sets(root["equivalence_sets"], artifacts)
    validate_candidate(repo, root["candidate"], artifacts)
    ci_source, _build_path = validate_integration(repo, root["integration"])
    capabilities = validate_capabilities(
        repo, root["capabilities"], evidence, ci_source
    )
    config_status = "metadata-only"
    if kernel_config is not None:
        validate_kernel_config(
            parse_kernel_config(kernel_config),
            capabilities,
            include_future,
        )
        config_status = "verified"
    active_count = sum(
        row["phase"] == "active" for row in capabilities
    )
    future_count = len(capabilities) - active_count
    return active_count, future_count, config_status


def parse_arguments(arguments: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo",
        type=Path,
        default=Path(__file__).resolve().parents[2],
    )
    parser.add_argument("--profile", type=Path)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--kernel-config", type=Path)
    mode.add_argument("--metadata-only", action="store_true")
    parser.add_argument("--include-future", action="store_true")
    return parser.parse_args(arguments)


def main(arguments: list[str]) -> int:
    options = parse_arguments(arguments)
    repo = options.repo.resolve(strict=True)
    if not (repo / ".git").exists():
        fail("repository is not a Git worktree")
    if repo != Path(__file__).resolve().parents[2]:
        fail("repository does not contain this compatibility verifier")
    if options.metadata_only and options.include_future:
        fail("--include-future requires --kernel-config")
    profile_path = (
        options.profile
        if options.profile is not None
        else repo / DEFAULT_PROFILE
    )
    profile_path = safe_input_file(
        profile_path,
        "compatibility profile",
    )
    try:
        profile_path.relative_to(repo)
    except ValueError:
        fail("compatibility profile is outside the repository")
    kernel_config = options.kernel_config
    if kernel_config is not None:
        kernel_config = safe_input_file(kernel_config, "kernel config")
    active, future, config_status = validate_profile(
        repo,
        read_json(profile_path, "compatibility profile"),
        kernel_config,
        options.include_future,
    )
    print("profile=minimal-headless-v1")
    print(f"active_capabilities={active}")
    print(f"future_capabilities={future}")
    print(f"kernel_config={config_status}")
    print("new_root_state=live-pending")
    print("authority=none")
    print(
        "status=ready"
        if config_status == "verified"
        else "status=metadata-only"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv[1:]))
    except (
        json.JSONDecodeError,
        OSError,
        UnicodeDecodeError,
        ValueError,
    ) as error:
        print(f"FAIL {error}", file=sys.stderr)
        raise SystemExit(1)
