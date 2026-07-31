#!/usr/bin/env python3
"""Verify sustained read-only ROG5 battery observations."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import os
from pathlib import Path
import re
import stat
import statistics
import sys
from typing import NoReturn


REPO = Path(__file__).resolve().parents[2]
COLLECTOR = REPO / "scripts/device/collect-headless-battery-series.sh"
FORMAT = "rog5-headless-battery-series-v1"
PROFILE = "battery-readonly-v1"
CANDIDATE = "headless-ssh-network-root-v3"
KERNEL_RELEASE = "7.1.4-g7a5cef0db479"
MAX_RECORD_SIZE = 64 * 1024
LIVE_SAMPLE_COUNT = 21
LIVE_INTERVAL_SECONDS = 30
MIN_PAIR_CURRENT_UA = 25_000
MAX_PAIR_CAPACITY_DELTA = 10
SHA256 = re.compile(r"[0-9a-f]{64}\Z")
BOOT_ID = re.compile(
    r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-"
    r"[0-9a-f]{4}-[0-9a-f]{12}\Z"
)
HEADER_FIELDS = (
    "format",
    "profile",
    "execution_mode",
    "collector_sha256",
    "candidate",
    "boot_id",
    "kernel_release",
    "phase",
    "interval_seconds",
    "sample_count",
    "battery_supply",
    "usb_supply",
    "wireless_supply",
    "battery_property_modes",
    "usb_input_current_limit_mode",
    "charge_control_surface_count",
    "typec_device_count",
)
EXACT_HEADER = {
    "format": FORMAT,
    "profile": PROFILE,
    "candidate": CANDIDATE,
    "kernel_release": KERNEL_RELEASE,
    "battery_supply": "qcom-battmgr-bat",
    "usb_supply": "qcom-battmgr-usb",
    "wireless_supply": "qcom-battmgr-wls",
    "battery_property_modes": (
        "capacity:444,voltage_now:444,current_now:444,"
        "temp:444,status:444"
    ),
    "usb_input_current_limit_mode": "444",
    "charge_control_surface_count": "0",
    "typec_device_count": "0",
}
STATUSES = {
    "Unknown",
    "Charging",
    "Discharging",
    "Not_charging",
    "Full",
}
PHASE_ONLINE = {
    "unplugged": (0, 0),
    "usb-online": (1, 0),
    "wireless-online": (0, 1),
}


class BatterySeriesError(RuntimeError):
    """A stable battery-series refusal."""


def fail(message: str) -> NoReturn:
    raise BatterySeriesError(message)


@dataclass(frozen=True)
class Sample:
    elapsed_seconds: int
    capacity_percent: int
    voltage_uv: int
    current_ua: int
    temp_dc: int
    status: str
    usb_online: int
    wireless_online: int


@dataclass(frozen=True)
class Series:
    values: dict[str, str]
    samples: tuple[Sample, ...]


def identity(metadata: os.stat_result) -> tuple[int, ...]:
    return (
        metadata.st_dev,
        metadata.st_ino,
        metadata.st_mode,
        metadata.st_uid,
        metadata.st_gid,
        metadata.st_nlink,
        metadata.st_size,
        metadata.st_mtime_ns,
        metadata.st_ctime_ns,
    )


def canonical_record(
    path: Path,
    *,
    owner: int,
    group: int,
) -> bytes:
    if not path.is_absolute():
        fail("battery-series record path must be absolute")
    lexical = Path(os.path.abspath(path))
    try:
        named = lexical.lstat()
        resolved = lexical.resolve(strict=True)
        resolved_metadata = resolved.lstat()
        parent = resolved.parent.lstat()
    except OSError as error:
        raise BatterySeriesError(
            "battery-series record is unavailable"
        ) from error
    if (
        lexical != resolved
        or stat.S_ISLNK(named.st_mode)
        or identity(named) != identity(resolved_metadata)
        or not stat.S_ISREG(named.st_mode)
        or named.st_uid != owner
        or named.st_gid != group
        or stat.S_IMODE(named.st_mode) != 0o600
        or named.st_nlink != 1
        or named.st_size < 1
        or named.st_size > MAX_RECORD_SIZE
        or not stat.S_ISDIR(parent.st_mode)
        or parent.st_uid != owner
        or parent.st_gid != group
        or stat.S_IMODE(parent.st_mode) != 0o700
    ):
        fail("battery-series record metadata is unsafe")
    flags = os.O_RDONLY | os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(resolved, flags)
    try:
        before = os.fstat(descriptor)
        payload = bytearray()
        while len(payload) <= MAX_RECORD_SIZE:
            block = os.read(descriptor, 64 * 1024)
            if not block:
                break
            payload.extend(block)
        after = os.fstat(descriptor)
        named_after = resolved.lstat()
        if (
            len(payload) != before.st_size
            or len(payload) > MAX_RECORD_SIZE
            or identity(before) != identity(after)
            or identity(before) != identity(named_after)
        ):
            fail("battery-series record changed while being read")
        return bytes(payload)
    finally:
        os.close(descriptor)


def canonical_unsigned(value: str, label: str) -> int:
    if not value.isascii() or not value.isdecimal():
        fail(f"{label} is not an unsigned integer")
    if value != "0" and value.startswith("0"):
        fail(f"{label} is not canonical")
    return int(value)


def canonical_signed(value: str, label: str) -> int:
    body = value.removeprefix("-")
    parsed = canonical_unsigned(body, label)
    if value == "-0":
        fail(f"{label} is not canonical")
    return -parsed if value.startswith("-") else parsed


def parse_header_line(line: str, expected: str) -> str:
    key, separator, value = line.partition("=")
    if separator != "=" or key != expected or not value or "=" in value:
        fail("battery-series header framing changed")
    return value


def parse_sample(
    line: str,
    index: int,
    *,
    phase: str,
    interval_seconds: int,
) -> Sample:
    expected_key = f"sample_{index:03d}"
    key, separator, value = line.partition("=")
    if separator != "=" or key != expected_key:
        fail("battery-series sample ordering changed")
    fields = value.split(",")
    if len(fields) != 8:
        fail("battery-series sample width changed")
    elapsed = canonical_unsigned(fields[0], "sample elapsed time")
    capacity = canonical_unsigned(fields[1], "sample capacity")
    voltage = canonical_unsigned(fields[2], "sample voltage")
    current = canonical_signed(fields[3], "sample current")
    temperature = canonical_signed(fields[4], "sample temperature")
    status = fields[5]
    usb_online = canonical_unsigned(fields[6], "sample USB state")
    wireless_online = canonical_unsigned(
        fields[7],
        "sample wireless state",
    )
    if elapsed != index * interval_seconds:
        fail("battery-series sample schedule changed")
    if not 0 <= capacity <= 100:
        fail("battery-series capacity is outside the diagnostic range")
    if not 2_500_000 <= voltage <= 10_000_000:
        fail("battery-series voltage is outside the diagnostic range")
    if not -20_000_000 <= current <= 20_000_000:
        fail("battery-series current is outside the diagnostic range")
    if not -200 <= temperature <= 1_000:
        fail("battery-series temperature is outside the diagnostic range")
    if status not in STATUSES:
        fail("battery-series status is unsupported")
    if (usb_online, wireless_online) != PHASE_ONLINE[phase]:
        fail("battery-series online state contradicts its phase")
    return Sample(
        elapsed_seconds=elapsed,
        capacity_percent=capacity,
        voltage_uv=voltage,
        current_ua=current,
        temp_dc=temperature,
        status=status,
        usb_online=usb_online,
        wireless_online=wireless_online,
    )


def parse_payload(
    payload: bytes,
    *,
    expected_boot_id: str,
    expected_mode: str = "live",
    expected_sample_count: int = LIVE_SAMPLE_COUNT,
    expected_interval_seconds: int = LIVE_INTERVAL_SECONDS,
) -> Series:
    try:
        text = payload.decode("ascii")
    except UnicodeDecodeError as error:
        raise BatterySeriesError(
            "battery-series record is not ASCII"
        ) from error
    if not text.endswith("\n") or "\r" in text or "\0" in text:
        fail("battery-series record framing changed")
    lines = text.splitlines()
    expected_lines = len(HEADER_FIELDS) + expected_sample_count + 1
    if len(lines) != expected_lines:
        fail("battery-series record line count changed")
    values = {
        field: parse_header_line(lines[index], field)
        for index, field in enumerate(HEADER_FIELDS)
    }
    collector_sha256 = hashlib.sha256(COLLECTOR.read_bytes()).hexdigest()
    expected = {
        **EXACT_HEADER,
        "execution_mode": expected_mode,
        "collector_sha256": collector_sha256,
        "boot_id": expected_boot_id,
        "interval_seconds": str(expected_interval_seconds),
        "sample_count": str(expected_sample_count),
    }
    for field, value in expected.items():
        if values.get(field) != value:
            fail(f"battery-series {field} changed")
    if not BOOT_ID.fullmatch(values["boot_id"]):
        fail("battery-series boot identity is invalid")
    if not SHA256.fullmatch(values["collector_sha256"]):
        fail("battery-series collector identity is invalid")
    phase = values["phase"]
    if phase not in PHASE_ONLINE:
        fail("battery-series phase is unsupported")
    samples = tuple(
        parse_sample(
            lines[len(HEADER_FIELDS) + index],
            index,
            phase=phase,
            interval_seconds=expected_interval_seconds,
        )
        for index in range(expected_sample_count)
    )
    if lines[-1] != "result=OBSERVED":
        fail("battery-series result changed")
    return Series(values=values, samples=samples)


def verify_record(
    path: Path,
    expected_boot_id: str,
    *,
    owner: int | None = None,
    group: int | None = None,
    expected_mode: str = "live",
    expected_sample_count: int = LIVE_SAMPLE_COUNT,
    expected_interval_seconds: int = LIVE_INTERVAL_SECONDS,
) -> Series:
    if not BOOT_ID.fullmatch(expected_boot_id):
        fail("expected battery-series boot identity is invalid")
    selected_owner = os.geteuid() if owner is None else owner
    selected_group = os.getegid() if group is None else group
    payload = canonical_record(
        path,
        owner=selected_owner,
        group=selected_group,
    )
    return parse_payload(
        payload,
        expected_boot_id=expected_boot_id,
        expected_mode=expected_mode,
        expected_sample_count=expected_sample_count,
        expected_interval_seconds=expected_interval_seconds,
    )


def verify_usb_pair(
    unplugged: Series,
    usb_online: Series,
) -> str:
    if (
        unplugged.values["phase"] != "unplugged"
        or usb_online.values["phase"] != "usb-online"
    ):
        fail("battery-series comparison phases changed")
    for field in ("candidate", "boot_id", "kernel_release"):
        if unplugged.values[field] != usb_online.values[field]:
            fail("battery-series comparison identity changed")
    unplugged_statuses = {sample.status for sample in unplugged.samples}
    usb_statuses = {sample.status for sample in usb_online.samples}
    if "Discharging" not in unplugged_statuses:
        fail("unplugged series never reported Discharging")
    if not usb_statuses.intersection({"Charging", "Full"}):
        fail("USB series never reported Charging or Full")
    if unplugged_statuses.difference({"Unknown", "Discharging", "Full"}):
        fail("unplugged series reported a contradictory status")
    if usb_statuses.difference(
        {"Unknown", "Charging", "Not_charging", "Full"}
    ):
        fail("USB series reported a contradictory status")
    unplugged_current = int(
        statistics.median(
            sample.current_ua for sample in unplugged.samples
        )
    )
    usb_current = int(
        statistics.median(sample.current_ua for sample in usb_online.samples)
    )
    if (
        abs(unplugged_current) < MIN_PAIR_CURRENT_UA
        or abs(usb_current) < MIN_PAIR_CURRENT_UA
        or (unplugged_current > 0) == (usb_current > 0)
    ):
        fail("battery-series current direction is not distinguishable")
    unplugged_capacity = int(
        statistics.median(
            sample.capacity_percent for sample in unplugged.samples
        )
    )
    usb_capacity = int(
        statistics.median(
            sample.capacity_percent for sample in usb_online.samples
        )
    )
    if abs(unplugged_capacity - usb_capacity) > MAX_PAIR_CAPACITY_DELTA:
        fail("battery-series pair spans an incomparable capacity state")
    return (
        "positive-discharge"
        if unplugged_current > 0
        else "positive-charge"
    )


def parse_arguments(arguments: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    commands = parser.add_subparsers(dest="command", required=True)
    single = commands.add_parser("single", allow_abbrev=False)
    single.add_argument("record", type=Path)
    single.add_argument("expected_boot_id")
    pair = commands.add_parser("usb-pair", allow_abbrev=False)
    pair.add_argument("unplugged_record", type=Path)
    pair.add_argument("usb_record", type=Path)
    pair.add_argument("expected_boot_id")
    return parser.parse_args(arguments)


def main(arguments: list[str] | None = None) -> int:
    try:
        options = parse_arguments(
            sys.argv[1:] if arguments is None else arguments
        )
        if options.command == "single":
            series = verify_record(
                options.record,
                options.expected_boot_id,
            )
            print(
                "PASS observed canonical read-only battery series "
                f"phase={series.values['phase']} "
                f"samples={len(series.samples)}"
            )
        else:
            unplugged = verify_record(
                options.unplugged_record,
                options.expected_boot_id,
            )
            usb_online = verify_record(
                options.usb_record,
                options.expected_boot_id,
            )
            convention = verify_usb_pair(unplugged, usb_online)
            print(
                "PASS compared unplugged and USB battery series "
                f"current_convention={convention}"
            )
    except (BatterySeriesError, OSError):
        print("FAIL headless battery-series verification refused", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
