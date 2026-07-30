#!/usr/bin/env python3
"""Verify an experimental ASUS stable-recovery wrapper config reduction."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import stat
import sys
from typing import NoReturn


PROFILE_FORMAT = "rog5-stable-wrapper-slim-profile-v1"
PROFILE_KEYS = (
    "format",
    "status",
    "authority",
    "baseline_config_sha256",
    "fragment_sha256",
    "candidate_config_sha256",
    "source_tree_sha256",
    "builder_id",
    "builder_digest",
    "minimum_builtin_reduction",
    "minimum_active_reduction",
    "minimum_integer_config",
    "allowed_enabled_additions",
    "allowed_builtin_promotions",
    "candidate_required",
    "forbidden_config",
)
HEX = frozenset("0123456789abcdef")


class ConfigAuditError(RuntimeError):
    """The wrapper config does not satisfy the experimental audit."""


def fail(message: str) -> NoReturn:
    raise ConfigAuditError(message)


def duplicate_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            fail(f"duplicate JSON field: {key}")
        result[key] = value
    return result


def is_sha256(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in HEX for character in value)
    )


def read_regular(path: Path) -> bytes:
    metadata = path.lstat()
    if (
        path.is_symlink()
        or not stat.S_ISREG(metadata.st_mode)
        or metadata.st_nlink != 1
    ):
        fail(f"input is not a single-link regular file: {path}")
    descriptor = os.open(
        path,
        os.O_RDONLY
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_NOFOLLOW", 0),
    )
    try:
        opened = os.fstat(descriptor)
        if (
            opened.st_dev,
            opened.st_ino,
            opened.st_mode,
            opened.st_size,
            opened.st_mtime_ns,
        ) != (
            metadata.st_dev,
            metadata.st_ino,
            metadata.st_mode,
            metadata.st_size,
            metadata.st_mtime_ns,
        ):
            fail(f"input changed while opening: {path}")
        data = bytearray()
        while chunk := os.read(descriptor, 1024 * 1024):
            data.extend(chunk)
        after = os.fstat(descriptor)
        if (
            after.st_dev,
            after.st_ino,
            after.st_mode,
            after.st_size,
            after.st_mtime_ns,
        ) != (
            opened.st_dev,
            opened.st_ino,
            opened.st_mode,
            opened.st_size,
            opened.st_mtime_ns,
        ):
            fail(f"input changed while reading: {path}")
        return bytes(data)
    finally:
        os.close(descriptor)


def load_profile(path: Path) -> dict[str, object]:
    raw = read_regular(path)
    try:
        profile = json.loads(
            raw.decode("ascii"),
            object_pairs_hook=duplicate_object,
        )
    except (UnicodeError, json.JSONDecodeError) as error:
        raise ConfigAuditError("profile is not canonical ASCII JSON") from error
    if not isinstance(profile, dict) or tuple(profile) != PROFILE_KEYS:
        fail("profile fields or ordering changed")
    canonical = (
        json.dumps(profile, indent=2, ensure_ascii=True) + "\n"
    ).encode("ascii")
    if raw != canonical:
        fail("profile JSON is not canonical")
    if profile["format"] != PROFILE_FORMAT:
        fail("profile format changed")
    if profile["status"] != "experiment" or profile["authority"] != "none":
        fail("profile claims non-experimental state or authority")
    for key in (
        "baseline_config_sha256",
        "fragment_sha256",
        "candidate_config_sha256",
        "source_tree_sha256",
        "builder_id",
    ):
        if not is_sha256(profile[key]):
            fail(f"profile has invalid SHA-256: {key}")
    digest = profile["builder_digest"]
    if not (
        isinstance(digest, str)
        and digest.startswith("sha256:")
        and is_sha256(digest.removeprefix("sha256:"))
    ):
        fail("profile builder digest is malformed")
    for key in ("minimum_builtin_reduction", "minimum_active_reduction"):
        if not isinstance(profile[key], int) or int(profile[key]) <= 0:
            fail(f"profile has invalid reduction threshold: {key}")
    minimum = profile["minimum_integer_config"]
    required = profile["candidate_required"]
    additions = profile["allowed_enabled_additions"]
    promotions = profile["allowed_builtin_promotions"]
    forbidden = profile["forbidden_config"]
    if (
        not isinstance(minimum, dict)
        or tuple(minimum) != tuple(sorted(minimum))
        or not minimum
    ):
        fail("minimum integer config is empty, unsorted, or malformed")
    if (
        not isinstance(required, dict)
        or tuple(required) != tuple(sorted(required))
        or not required
    ):
        fail("candidate required config is empty, unsorted, or malformed")
    if not all(
        isinstance(key, str)
        and key.startswith("CONFIG_")
        and isinstance(value, (str, int))
        for key, value in minimum.items()
    ):
        fail("minimum integer config has malformed entries")
    if not all(
        isinstance(key, str)
        and key.startswith("CONFIG_")
        and isinstance(value, str)
        and value
        and "\n" not in value
        and "\0" not in value
        for key, value in required.items()
    ):
        fail("candidate required config has malformed entries")
    for label, values in (
        ("allowed enabled additions", additions),
        ("allowed builtin promotions", promotions),
        ("forbidden config", forbidden),
    ):
        if (
            not isinstance(values, list)
            or values != sorted(set(values))
            or (label != "allowed builtin promotions" and not values)
            or not all(
                isinstance(value, str) and value.startswith("CONFIG_")
                for value in values
            )
        ):
            fail(f"{label} is empty, unsorted, duplicated, or malformed")
    if set(additions) - set(required):
        fail("allowed enabled addition is not explicitly required")
    if set(promotions) - set(required):
        fail("allowed builtin promotion is not explicitly required")
    if set(additions) & set(promotions):
        fail("enabled additions and builtin promotions overlap")
    if set(forbidden) & {
        key for key, value in required.items() if value != "n"
    }:
        fail("required and forbidden config overlap")
    return profile


def parse_config(data: bytes, label: str) -> dict[str, str]:
    try:
        text = data.decode("ascii")
    except UnicodeError as error:
        raise ConfigAuditError(f"{label} is not ASCII") from error
    if not text.endswith("\n") or "\r" in text or "\0" in text:
        fail(f"{label} is not canonical LF text")
    result: dict[str, str] = {}
    for line in text.splitlines():
        if line.startswith("CONFIG_") and "=" in line:
            key, value = line.split("=", 1)
        elif line.startswith("# CONFIG_") and line.endswith(" is not set"):
            key = line[2:-11]
            value = "n"
        else:
            continue
        if key in result:
            fail(f"{label} contains duplicate symbol: {key}")
        result[key] = value
    if not result:
        fail(f"{label} contains no kernel config symbols")
    return result


def enabled_symbols(config: dict[str, str]) -> set[str]:
    return {
        symbol
        for symbol, value in config.items()
        if value in ("y", "m")
    }


def active_count(config: dict[str, str]) -> int:
    return sum(value in ("y", "m") for value in config.values())


def verify_candidate(
    profile: dict[str, object],
    baseline: dict[str, str],
    candidate: dict[str, str],
) -> tuple[int, int]:
    required = profile["candidate_required"]
    assert isinstance(required, dict)
    for symbol, expected in required.items():
        actual = candidate.get(symbol, "n")
        if actual != expected:
            fail(
                f"candidate requirement changed: "
                f"{symbol} expected {expected} got {actual}"
            )
    minimum = profile["minimum_integer_config"]
    assert isinstance(minimum, dict)
    for symbol, expected in minimum.items():
        try:
            actual = int(candidate.get(symbol, "0"), 10)
        except ValueError as error:
            raise ConfigAuditError(
                f"candidate integer is malformed: {symbol}"
            ) from error
        if actual < int(expected):
            fail(f"candidate integer is below minimum: {symbol}")
    forbidden = profile["forbidden_config"]
    assert isinstance(forbidden, list)
    for symbol in forbidden:
        if candidate.get(symbol, "n") != "n":
            fail(f"candidate retained forbidden config: {symbol}")
    additions = set(profile["allowed_enabled_additions"])
    unexpected = enabled_symbols(candidate) - enabled_symbols(baseline) - additions
    if unexpected:
        fail(
            "candidate enabled unreviewed config: "
            + ",".join(sorted(unexpected))
        )
    promotions = set(profile["allowed_builtin_promotions"])
    unexpected_promotions = {
        symbol
        for symbol, value in baseline.items()
        if value == "m" and candidate.get(symbol, "n") == "y"
    } - promotions
    if unexpected_promotions:
        fail(
            "candidate promoted unreviewed module to builtin: "
            + ",".join(sorted(unexpected_promotions))
        )
    baseline_builtin = sum(value == "y" for value in baseline.values())
    candidate_builtin = sum(value == "y" for value in candidate.values())
    builtin_reduction = baseline_builtin - candidate_builtin
    if builtin_reduction < int(profile["minimum_builtin_reduction"]):
        fail("candidate builtin reduction is below the profile threshold")
    reduction = active_count(baseline) - active_count(candidate)
    if reduction < int(profile["minimum_active_reduction"]):
        fail("candidate active reduction is below the profile threshold")
    return builtin_reduction, reduction


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", required=True, type=Path)
    parser.add_argument("--baseline", required=True, type=Path)
    parser.add_argument("--candidate", type=Path)
    values = parser.parse_args()
    profile = load_profile(values.profile)
    baseline_data = read_regular(values.baseline)
    baseline_hash = hashlib.sha256(baseline_data).hexdigest()
    if baseline_hash != profile["baseline_config_sha256"]:
        fail("accepted baseline config identity changed")
    baseline = parse_config(baseline_data, "baseline config")
    print(f"baseline_builtin={sum(value == 'y' for value in baseline.values())}")
    print(f"baseline_active={active_count(baseline)}")
    if values.candidate is not None:
        candidate_data = read_regular(values.candidate)
        if hashlib.sha256(candidate_data).hexdigest() != (
            profile["candidate_config_sha256"]
        ):
            fail("candidate config identity changed")
        candidate = parse_config(candidate_data, "candidate config")
        builtin_reduction, active_reduction = verify_candidate(
            profile, baseline, candidate
        )
        print(
            f"candidate_builtin="
            f"{sum(value == 'y' for value in candidate.values())}"
        )
        print(f"builtin_reduction={builtin_reduction}")
        print(f"active_reduction={active_reduction}")
    print("status=experiment")
    print("authority=none")
    print("PASS stable-recovery wrapper config slimming audit")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ConfigAuditError, OSError) as error:
        print(f"FAIL {error}", file=sys.stderr)
        raise SystemExit(1)
