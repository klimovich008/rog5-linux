#!/usr/bin/env python3
"""Parse one-way, bounded ROG5 early-target diagnostic records."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
import sys
from typing import NoReturn


REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from tools.recovery_control.reference import (  # noqa: E402
    FrameParser,
    ProtocolViolation,
    encode_frame,
)


FORMAT = "rog5-early-target-diag-v1"
PAYLOAD_MAX = 1024
MAX_U64 = (1 << 64) - 1
CANDIDATE = re.compile(r"[a-z0-9][a-z0-9.-]{0,63}\Z")
BOOT_ID = re.compile(
    r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-"
    r"[0-9a-f]{4}-[0-9a-f]{12}\Z"
)
STAGES = {
    10: "reporter-up",
    20: "gadget-configured",
    30: "udc-bound",
    40: "ncm-interface-up",
    50: "address-configured",
    60: "ncm-carrier-up",
    70: "nfs-mount-begin",
    80: "nfs-mount-ok",
    90: "seal-verify-ok",
    100: "overlay-ready",
    110: "handoff-begin",
    120: "switch-root-exec",
    130: "new-init-up",
    140: "sshd-active",
    200: "fault",
    210: "watchdog-pretimeout",
}
PROGRESS_CODES = frozenset(range(10, 141, 10))
TERMINAL_CODES = frozenset({200, 210})
FAULTS = frozenset(
    {
        "none",
        "cmdline-invalid",
        "storage-visible",
        "watchdog-failed",
        "gadget-config-failed",
        "udc-bind-failed",
        "ncm-interface-failed",
        "address-failed",
        "carrier-timeout",
        "nfs-mount-failed",
        "seal-verify-failed",
        "overlay-failed",
        "diagnostic-units-failed",
        "identity-publish-failed",
        "storage-before-switch",
        "exitrd-failed",
        "handoff-failed",
        "switch-root-returned",
    }
)
FIELDS = (
    "format",
    "candidate",
    "boot_id",
    "sequence",
    "boottime_ms",
    "stage_code",
    "stage",
    "last_good_code",
    "fault",
    "watchdog_deadline_ms",
    "dropped_updates",
)


class DiagnosticError(RuntimeError):
    """A noncanonical or contradictory diagnostic stream."""


def fail(message: str) -> NoReturn:
    raise DiagnosticError(message)


def valid_candidate(value: str) -> bool:
    return bool(CANDIDATE.fullmatch(value)) and ".." not in value


def canonical_decimal(
    value: str,
    label: str,
    *,
    minimum: int = 0,
    maximum: int = MAX_U64,
) -> int:
    if (
        not value
        or not value.isascii()
        or not value.isdecimal()
        or len(value) > 1
        and value.startswith("0")
    ):
        fail(f"{label} is not a canonical decimal")
    parsed = int(value)
    if parsed < minimum or parsed > maximum:
        fail(f"{label} is outside policy")
    return parsed


@dataclass(frozen=True)
class DiagnosticRecord:
    candidate: str
    boot_id: str
    sequence: int
    boottime_ms: int
    stage_code: int
    stage: str
    last_good_code: int
    fault: str
    watchdog_deadline_ms: int
    dropped_updates: int


def parse_payload(
    payload: bytes, *, expected_candidate: str
) -> DiagnosticRecord:
    if (
        not isinstance(payload, bytes)
        or not payload
        or len(payload) > PAYLOAD_MAX
        or not payload.endswith(b"\n")
        or b"\r" in payload
        or b"\0" in payload
    ):
        fail("diagnostic payload framing is invalid")
    try:
        text = payload.decode("ascii")
    except UnicodeDecodeError as error:
        raise DiagnosticError("diagnostic payload is not ASCII") from error
    lines = text[:-1].split("\n")
    if len(lines) != len(FIELDS):
        fail("diagnostic field count is invalid")
    values: dict[str, str] = {}
    for expected, line in zip(FIELDS, lines, strict=True):
        if "=" not in line:
            fail("diagnostic field separator is missing")
        name, value = line.split("=", 1)
        if name != expected or not value:
            fail("diagnostic field order or value is invalid")
        values[name] = value

    if values["format"] != FORMAT:
        fail("diagnostic format is invalid")
    if (
        not valid_candidate(values["candidate"])
        or values["candidate"] != expected_candidate
    ):
        fail("diagnostic candidate is invalid")
    if not BOOT_ID.fullmatch(values["boot_id"]):
        fail("diagnostic boot ID is invalid")
    sequence = canonical_decimal(
        values["sequence"], "sequence", minimum=1
    )
    boottime = canonical_decimal(values["boottime_ms"], "boottime")
    stage_code = canonical_decimal(
        values["stage_code"], "stage code", minimum=10, maximum=210
    )
    if STAGES.get(stage_code) != values["stage"]:
        fail("diagnostic stage code/name pair is invalid")
    last_good = canonical_decimal(
        values["last_good_code"],
        "last-good code",
        minimum=10,
        maximum=140,
    )
    if last_good not in PROGRESS_CODES:
        fail("diagnostic last-good code is invalid")
    fault = values["fault"]
    if fault not in FAULTS:
        fail("diagnostic fault is invalid")
    if stage_code in PROGRESS_CODES:
        if last_good != stage_code or fault != "none":
            fail("progress diagnostic carries inconsistent terminal state")
    elif stage_code == 200:
        if fault == "none":
            fail("fault diagnostic lacks a reason")
    elif stage_code == 210 and fault != "none":
        fail("watchdog pretimeout carries a fault reason")
    deadline = canonical_decimal(
        values["watchdog_deadline_ms"],
        "watchdog deadline",
        minimum=1,
    )
    if boottime >= deadline and stage_code != 210:
        fail("diagnostic boottime reaches watchdog deadline")
    dropped = canonical_decimal(
        values["dropped_updates"],
        "dropped-update count",
        maximum=1_000_000,
    )
    return DiagnosticRecord(
        candidate=values["candidate"],
        boot_id=values["boot_id"],
        sequence=sequence,
        boottime_ms=boottime,
        stage_code=stage_code,
        stage=values["stage"],
        last_good_code=last_good,
        fault=fault,
        watchdog_deadline_ms=deadline,
        dropped_updates=dropped,
    )


def payload_for(record: DiagnosticRecord) -> bytes:
    values = (
        FORMAT,
        record.candidate,
        record.boot_id,
        str(record.sequence),
        str(record.boottime_ms),
        str(record.stage_code),
        record.stage,
        str(record.last_good_code),
        record.fault,
        str(record.watchdog_deadline_ms),
        str(record.dropped_updates),
    )
    return "".join(
        f"{name}={value}\n"
        for name, value in zip(FIELDS, values, strict=True)
    ).encode("ascii")


def frame_for(record: DiagnosticRecord) -> bytes:
    payload = payload_for(record)
    if len(payload) > PAYLOAD_MAX:
        fail("diagnostic payload exceeds policy")
    return encode_frame(payload)


class DiagnosticStream:
    """Incrementally validate one candidate and one target boot."""

    def __init__(self, expected_candidate: str):
        if not valid_candidate(expected_candidate):
            raise ValueError("invalid expected diagnostic candidate")
        self.expected_candidate = expected_candidate
        self.parser = FrameParser(PAYLOAD_MAX)
        self.records: list[DiagnosticRecord] = []
        self.boot_id: str | None = None
        self.sequence = 0
        self.boottime_ms = 0
        self.maximum_progress = 0
        self.terminal: tuple[int, int, str] | None = None
        self.watchdog_deadline_ms: int | None = None
        self.dropped_updates = 0

    def accept(self, record: DiagnosticRecord) -> None:
        if (
            record.stage_code != 210
            and record.watchdog_deadline_ms <= record.boottime_ms
        ):
            fail("diagnostic record is not before watchdog deadline")
        if self.boot_id is None:
            self.boot_id = record.boot_id
            self.watchdog_deadline_ms = record.watchdog_deadline_ms
            if (
                record.stage_code != 210
                and record.watchdog_deadline_ms - record.boottime_ms
                > 900_000
            ):
                fail("diagnostic watchdog interval is invalid")
        elif record.boot_id != self.boot_id:
            fail("diagnostic stream mixes target boots")
        if record.sequence <= self.sequence:
            fail("diagnostic sequence did not increase")
        if record.boottime_ms < self.boottime_ms:
            fail("diagnostic boottime regressed")
        if record.watchdog_deadline_ms != self.watchdog_deadline_ms:
            fail("diagnostic watchdog deadline changed")
        if record.dropped_updates < self.dropped_updates:
            fail("diagnostic dropped-update count regressed")

        if record.stage_code in PROGRESS_CODES:
            if self.terminal is not None:
                fail("diagnostic progress followed terminal state")
            if record.stage_code < self.maximum_progress:
                fail("diagnostic stage regressed")
            self.maximum_progress = record.stage_code
        else:
            terminal = (
                record.stage_code,
                record.last_good_code,
                record.fault,
            )
            if record.last_good_code < self.maximum_progress:
                fail("terminal diagnostic regressed last-good stage")
            if self.terminal is None:
                self.terminal = terminal
            elif terminal != self.terminal:
                fail("diagnostic terminal state changed")
            self.maximum_progress = max(
                self.maximum_progress, record.last_good_code
            )

        self.sequence = record.sequence
        self.boottime_ms = record.boottime_ms
        self.dropped_updates = record.dropped_updates
        self.records.append(record)

    def feed(self, data: bytes) -> list[DiagnosticRecord]:
        try:
            payloads = self.parser.feed(data)
        except ProtocolViolation as error:
            raise DiagnosticError(
                f"invalid diagnostic netstring: {error}"
            ) from error
        accepted: list[DiagnosticRecord] = []
        for payload in payloads:
            record = parse_payload(
                payload, expected_candidate=self.expected_candidate
            )
            self.accept(record)
            accepted.append(record)
        return accepted

    def finalize(self) -> None:
        try:
            self.parser.finalize()
        except ProtocolViolation as error:
            raise DiagnosticError(
                f"truncated diagnostic netstring: {error}"
            ) from error
