"""Executable reference model for the ROG5 recovery control protocol.

This is an offline oracle, not the production recovery responder. The
production implementation is expected to be a small static native binary.
"""

from __future__ import annotations

from collections import OrderedDict
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import stat
import time
from typing import Callable, Mapping


MAX_FRAME_PAYLOAD = 4096
MAX_LENGTH_DIGITS = len(str(MAX_FRAME_PAYLOAD))
MAX_FEED_BYTES = 8192
MAX_FRAMES_PER_FEED = 32
MAX_SNAPSHOT_BYTES = 65536
ZERO_ID = "0" * 32
ZERO_SHA256 = "0" * 64
EMPTY_BODY_SHA256 = hashlib.sha256(b"").hexdigest()
HEX_ID = re.compile(r"[0-9a-f]{32}\Z")
HEX_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
BUNDLE_ID = re.compile(r"[a-z0-9][a-z0-9._-]{0,63}\Z")
KEY = re.compile(r"[a-z][a-z0-9_]*\Z")
VALUE = re.compile(r"[\x21-\x7e]*\Z")

COMMON_FIELDS = (
    "version",
    "kind",
    "session",
    "request",
    "verb",
    "body_sha256",
)
VERB_FIELDS = {
    "HELLO": (),
    "STATUS": (),
    "PREPARE": ("bundle", "manifest_sha256"),
    "COMMIT_EXEC": ("prepare_request", "manifest_sha256"),
}
RESULTS = {
    "OK",
    "PREPARED",
    "FETCH_FAILED",
    "BUNDLE_ID_CONFLICT",
    "VERIFY_FAILED",
    "PREPARE_ID_CONFLICT",
    "BUNDLE_CONFLICT",
    "SESSION_CONSUMED",
    "PREPARE_REQUIRED",
    "PREPARE_MISMATCH",
    "CLAIMED",
    "ALREADY_CLAIMED",
    "STALE_SESSION",
    "REQUEST_CONFLICT",
    "LEDGER_FULL",
    "OBSERVATION_ONLY",
}
VERB_RESULTS = {
    "HELLO": {
        "OK",
        "REQUEST_CONFLICT",
        "LEDGER_FULL",
    },
    "STATUS": {
        "OK",
        "STALE_SESSION",
        "REQUEST_CONFLICT",
        "LEDGER_FULL",
    },
    "PREPARE": {
        "PREPARED",
        "FETCH_FAILED",
        "BUNDLE_ID_CONFLICT",
        "VERIFY_FAILED",
        "PREPARE_ID_CONFLICT",
        "BUNDLE_CONFLICT",
        "SESSION_CONSUMED",
        "STALE_SESSION",
        "REQUEST_CONFLICT",
        "LEDGER_FULL",
        "OBSERVATION_ONLY",
    },
    "COMMIT_EXEC": {
        "PREPARE_REQUIRED",
        "PREPARE_MISMATCH",
        "CLAIMED",
        "ALREADY_CLAIMED",
        "STALE_SESSION",
        "REQUEST_CONFLICT",
        "LEDGER_FULL",
        "OBSERVATION_ONLY",
    },
}
RESULT_STATES = {
    "PREPARED": {"PREPARED", "CLAIMED", "EXEC_FAILED"},
    "FETCH_FAILED": {"IDLE", "PREPARED", "CLAIMED", "EXEC_FAILED"},
    "BUNDLE_ID_CONFLICT": {"IDLE", "PREPARED", "CLAIMED", "EXEC_FAILED"},
    "VERIFY_FAILED": {"IDLE", "PREPARED", "CLAIMED", "EXEC_FAILED"},
    "PREPARE_ID_CONFLICT": {"IDLE", "PREPARED", "CLAIMED", "EXEC_FAILED"},
    "BUNDLE_CONFLICT": {"PREPARED", "CLAIMED", "EXEC_FAILED"},
    "SESSION_CONSUMED": {"CLAIMED", "EXEC_FAILED"},
    "PREPARE_REQUIRED": {"IDLE", "PREPARED", "CLAIMED", "EXEC_FAILED"},
    "PREPARE_MISMATCH": {"PREPARED", "CLAIMED", "EXEC_FAILED"},
    "CLAIMED": {"CLAIMED", "EXEC_FAILED"},
    "ALREADY_CLAIMED": {"CLAIMED", "EXEC_FAILED"},
    "OBSERVATION_ONLY": {"IDLE"},
}
STATES = {"IDLE", "PREPARED", "CLAIMED", "EXEC_FAILED"}
LAST_ERRORS = {
    "NONE",
    "FETCH_FAILED",
    "FETCH_ROOT",
    "FETCH_STAGE",
    "FETCH_CONNECT",
    "FETCH_WORKER_TIMEOUT",
    "FETCH_WORKER_SIGNAL",
    "FETCH_WORKER_SETUP",
    "FETCH_WORKER_FORK",
    "FETCH_TRANSPORT",
    "FETCH_HEADER",
    "FETCH_MANIFEST",
    "FETCH_ARTIFACT",
    "FETCH_EOF",
    "FETCH_PARENT_VERIFY",
    "FETCH_NORMALIZE",
    "FETCH_FINAL_VERIFY",
    "FETCH_PUBLISH",
    "FETCH_CONTROL_TIMEOUT",
    "FETCH_EXEC",
    "BUNDLE_ID_CONFLICT",
    "VERIFY_FAILED",
    "HAVEN_WDOG_FAILED",
    "EXEC_FAILED",
    "EXEC_RETURNED",
    "LEDGER_FULL",
}
RESPONSE_BODY_FIELDS = (
    "state",
    "prepared_bundle",
    "manifest_sha256",
    "prepare_request",
    "commit_request",
    "commit_fingerprint",
    "execution_started",
    "watchdog",
    "last_error",
    "postmortem_state",
    "postmortem_records",
    "postmortem_bytes",
    "postmortem_sha256",
    "postmortem_tail_hex",
    "postmortem_lineage_state",
    "postmortem_lineage_matches",
    "postmortem_lineage_sha256",
)
PREPARE_PROGRESS_PHASES = (
    "REQUEST_ACCEPTED",
    "FETCH_COMPLETE",
    "VERIFY_COMPLETE",
    "KEXEC_LOAD_COMPLETE",
    "PREPARED_PERSISTED",
)
PROGRESS_BODY_FIELDS = (
    "sequence",
    "phase",
    "bundle",
    "manifest_sha256",
    "watchdog",
)
POSTMORTEM_STATES = {"UNAVAILABLE", "EMPTY", "PRESENT"}
POSTMORTEM_LINEAGE_STATES = {"NONE", "UNIQUE", "REPEATED", "AMBIGUOUS"}
EMPTY_SHA256 = hashlib.sha256(b"").hexdigest()
TAIL_HEX = re.compile(r"(?:[0-9a-f]{2}){1,512}\Z")


class ProtocolViolation(ValueError):
    """A fixed protocol rejection suitable for a machine response."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


class InjectedCrash(RuntimeError):
    """Fault-injection event used only by the reference test suite."""


class TargetDeparted(BaseException):
    """Simulates successful kexec, which cannot return to the responder."""


class FrameParser:
    """Incremental, bounded netstring parser."""

    def __init__(self, maximum: int = MAX_FRAME_PAYLOAD):
        if maximum < 1 or maximum > MAX_FRAME_PAYLOAD:
            raise ValueError("invalid frame maximum")
        self.maximum = maximum
        self._buffer = bytearray()
        self.failed = False

    def feed(self, data: bytes) -> list[bytes]:
        if self.failed:
            raise ProtocolViolation("PARSER_FAILED")
        if not isinstance(data, bytes):
            raise TypeError("frame input must be bytes")
        if len(data) > MAX_FEED_BYTES:
            self.failed = True
            raise ProtocolViolation("READ_TOO_LARGE")
        self._buffer.extend(data)
        frames: list[bytes] = []
        try:
            while self._buffer:
                if len(frames) >= MAX_FRAMES_PER_FEED:
                    raise ProtocolViolation("TOO_MANY_FRAMES")
                colon = self._buffer.find(b":")
                if colon < 0:
                    if (
                        len(self._buffer) > MAX_LENGTH_DIGITS
                        or not self._buffer.isdigit()
                    ):
                        raise ProtocolViolation("BAD_LENGTH")
                    break
                if colon == 0 or colon > MAX_LENGTH_DIGITS:
                    raise ProtocolViolation("BAD_LENGTH")
                length_bytes = bytes(self._buffer[:colon])
                if not length_bytes.isdigit():
                    raise ProtocolViolation("BAD_LENGTH")
                if len(length_bytes) > 1 and length_bytes.startswith(b"0"):
                    raise ProtocolViolation("BAD_LENGTH")
                length = int(length_bytes)
                if length > self.maximum:
                    raise ProtocolViolation("FRAME_TOO_LARGE")
                total = colon + 1 + length + 1
                if len(self._buffer) < total:
                    break
                if self._buffer[total - 1] != ord(","):
                    raise ProtocolViolation("BAD_TERMINATOR")
                frames.append(bytes(self._buffer[colon + 1 : total - 1]))
                del self._buffer[:total]
        except ProtocolViolation:
            self._buffer.clear()
            self.failed = True
            raise
        return frames

    def finalize(self) -> None:
        if self.failed:
            raise ProtocolViolation("PARSER_FAILED")
        if self._buffer:
            self._buffer.clear()
            self.failed = True
            raise ProtocolViolation("TRUNCATED_FRAME")


def encode_frame(payload: bytes) -> bytes:
    if not isinstance(payload, bytes):
        raise TypeError("frame payload must be bytes")
    if len(payload) > MAX_FRAME_PAYLOAD:
        raise ProtocolViolation("FRAME_TOO_LARGE")
    return str(len(payload)).encode("ascii") + b":" + payload + b","


@dataclass(frozen=True)
class Request:
    version: str
    kind: str
    session: str
    request: str
    verb: str
    body_sha256: str
    body: tuple[tuple[str, str], ...]
    wire: bytes

    @property
    def fingerprint(self) -> str:
        return hashlib.sha256(self.wire).hexdigest()

    def value(self, key: str) -> str:
        for candidate, value in self.body:
            if candidate == key:
                return value
        raise KeyError(key)


@dataclass(frozen=True)
class Progress:
    session: str
    request: str
    sequence: int
    phase: str
    bundle: str
    manifest_sha256: str
    watchdog: str = "ARMED"


@dataclass(frozen=True)
class Response:
    session: str
    request: str
    verb: str
    result: str
    state: str
    prepared_bundle: str = "none"
    manifest_sha256: str = ZERO_SHA256
    prepare_request: str = ZERO_ID
    commit_request: str = ZERO_ID
    commit_fingerprint: str = ZERO_SHA256
    execution_started: str = "NO"
    watchdog: str = "ARMED"
    last_error: str = "NONE"
    postmortem_state: str = "UNAVAILABLE"
    postmortem_records: str = "0"
    postmortem_bytes: str = "0"
    postmortem_sha256: str = ZERO_SHA256
    postmortem_tail_hex: str = "none"
    postmortem_lineage_state: str = "NONE"
    postmortem_lineage_matches: str = "0"
    postmortem_lineage_sha256: str = ZERO_SHA256


def encode_progress(progress: Progress) -> bytes:
    if (
        not all(
            isinstance(value, str)
            for value in (
                progress.session,
                progress.request,
                progress.phase,
                progress.bundle,
                progress.manifest_sha256,
                progress.watchdog,
            )
        )
        or isinstance(progress.sequence, bool)
        or not isinstance(progress.sequence, int)
        or progress.sequence < 1
        or progress.sequence > len(PREPARE_PROGRESS_PHASES)
        or progress.phase
        != PREPARE_PROGRESS_PHASES[progress.sequence - 1]
        or not HEX_ID.fullmatch(progress.session)
        or progress.session == ZERO_ID
        or not HEX_ID.fullmatch(progress.request)
        or progress.request == ZERO_ID
        or not BUNDLE_ID.fullmatch(progress.bundle)
        or ".." in progress.bundle
        or not HEX_SHA256.fullmatch(progress.manifest_sha256)
        or progress.manifest_sha256 == ZERO_SHA256
        or progress.watchdog != "ARMED"
    ):
        raise ProtocolViolation("BAD_PROGRESS")
    body = (
        ("sequence", str(progress.sequence)),
        ("phase", progress.phase),
        ("bundle", progress.bundle),
        ("manifest_sha256", progress.manifest_sha256),
        ("watchdog", progress.watchdog),
    )
    fields = (
        ("version", "1"),
        ("kind", "progress"),
        ("session", progress.session),
        ("request", progress.request),
        ("verb", "PREPARE"),
        ("body_sha256", hashlib.sha256(_body_bytes(body)).hexdigest()),
        *body,
    )
    return _body_bytes(fields)


def encode_response(response: Response) -> bytes:
    prepared_values = (
        response.prepared_bundle != "none",
        response.manifest_sha256 != ZERO_SHA256,
        response.prepare_request != ZERO_ID,
    )
    claimed_values = (
        response.commit_request != ZERO_ID,
        response.commit_fingerprint != ZERO_SHA256,
    )
    prepared = all(prepared_values)
    claimed = all(claimed_values)
    if (
        not all(
            isinstance(value, str)
            for value in (
                response.session,
                response.request,
                response.verb,
                response.result,
                response.state,
                response.prepared_bundle,
                response.manifest_sha256,
                response.prepare_request,
                response.commit_request,
                response.commit_fingerprint,
                response.execution_started,
                response.watchdog,
                response.last_error,
                response.postmortem_state,
                response.postmortem_records,
                response.postmortem_bytes,
                response.postmortem_sha256,
                response.postmortem_tail_hex,
                response.postmortem_lineage_state,
                response.postmortem_lineage_matches,
                response.postmortem_lineage_sha256,
            )
        )
        or not HEX_ID.fullmatch(response.session)
        or response.session == ZERO_ID
        or not HEX_ID.fullmatch(response.request)
        or response.request == ZERO_ID
        or response.verb not in VERB_FIELDS
        or response.result not in RESULTS
        or response.result not in VERB_RESULTS.get(response.verb, set())
        or response.state not in STATES
        or (
            response.result in RESULT_STATES
            and response.state not in RESULT_STATES[response.result]
        )
        or (
            response.prepared_bundle != "none"
            and (
                not BUNDLE_ID.fullmatch(response.prepared_bundle)
                or ".." in response.prepared_bundle
            )
        )
        or not HEX_SHA256.fullmatch(response.manifest_sha256)
        or not HEX_ID.fullmatch(response.prepare_request)
        or not HEX_ID.fullmatch(response.commit_request)
        or not HEX_SHA256.fullmatch(response.commit_fingerprint)
        or response.execution_started not in {"NO", "YES"}
        or response.watchdog != "ARMED"
        or response.last_error not in LAST_ERRORS
        or response.postmortem_state not in POSTMORTEM_STATES
        or not response.postmortem_records.isdecimal()
        or (
            len(response.postmortem_records) > 1
            and response.postmortem_records.startswith("0")
        )
        or len(response.postmortem_records) > 2
        or int(response.postmortem_records) > 64
        or not response.postmortem_bytes.isdecimal()
        or (
            len(response.postmortem_bytes) > 1
            and response.postmortem_bytes.startswith("0")
        )
        or len(response.postmortem_bytes) > 7
        or int(response.postmortem_bytes) > 4194304
        or not HEX_SHA256.fullmatch(response.postmortem_sha256)
        or (
            response.postmortem_tail_hex != "none"
            and not TAIL_HEX.fullmatch(response.postmortem_tail_hex)
        )
        or response.postmortem_lineage_state
        not in POSTMORTEM_LINEAGE_STATES
        or not response.postmortem_lineage_matches.isdecimal()
        or (
            len(response.postmortem_lineage_matches) > 1
            and response.postmortem_lineage_matches.startswith("0")
        )
        or len(response.postmortem_lineage_matches) > 5
        or int(response.postmortem_lineage_matches) > 65535
        or not HEX_SHA256.fullmatch(response.postmortem_lineage_sha256)
        or (
            response.postmortem_state == "PRESENT"
            and (
                response.postmortem_records == "0"
                or response.postmortem_bytes == "0"
                or response.postmortem_sha256 == ZERO_SHA256
                or response.postmortem_tail_hex == "none"
            )
        )
        or (
            response.postmortem_state == "EMPTY"
            and (
                response.postmortem_records != "0"
                or response.postmortem_bytes != "0"
                or response.postmortem_sha256 != EMPTY_SHA256
                or response.postmortem_tail_hex != "none"
            )
        )
        or (
            response.postmortem_state == "UNAVAILABLE"
            and (
                response.postmortem_records != "0"
                or response.postmortem_bytes != "0"
                or response.postmortem_sha256 != ZERO_SHA256
                or response.postmortem_tail_hex != "none"
            )
        )
        or (
            response.postmortem_state != "PRESENT"
            and (
                response.postmortem_lineage_state != "NONE"
                or response.postmortem_lineage_matches != "0"
                or response.postmortem_lineage_sha256 != ZERO_SHA256
            )
        )
        or (
            response.postmortem_lineage_state == "NONE"
            and (
                response.postmortem_lineage_matches != "0"
                or response.postmortem_lineage_sha256 != ZERO_SHA256
            )
        )
        or (
            response.postmortem_lineage_state == "UNIQUE"
            and (
                response.postmortem_lineage_matches != "1"
                or response.postmortem_lineage_sha256 == ZERO_SHA256
            )
        )
        or (
            response.postmortem_lineage_state == "REPEATED"
            and (
                int(response.postmortem_lineage_matches) < 2
                or response.postmortem_lineage_sha256 == ZERO_SHA256
            )
        )
        or (
            response.postmortem_lineage_state == "AMBIGUOUS"
            and response.postmortem_lineage_sha256 != ZERO_SHA256
        )
        or any(prepared_values) != prepared
        or any(claimed_values) != claimed
        or (response.state == "IDLE" and (prepared or claimed))
        or (response.state == "PREPARED" and (not prepared or claimed))
        or (
            response.state in {"CLAIMED", "EXEC_FAILED"}
            and (not prepared or not claimed)
        )
        or (
            response.execution_started == "YES"
            and response.state not in {"CLAIMED", "EXEC_FAILED"}
        )
        or (
            response.state == "EXEC_FAILED"
            and response.execution_started != "YES"
            and response.last_error != "HAVEN_WDOG_FAILED"
        )
        or (
            response.last_error == "HAVEN_WDOG_FAILED"
            and (
                response.state != "EXEC_FAILED"
                or response.execution_started != "NO"
            )
        )
    ):
        raise ProtocolViolation("BAD_RESPONSE")
    body = tuple(
        (name, getattr(response, name))
        for name in RESPONSE_BODY_FIELDS
    )
    fields = (
        ("version", "1"),
        ("kind", "response"),
        ("session", response.session),
        ("request", response.request),
        ("verb", response.verb),
        ("result", response.result),
        ("body_sha256", hashlib.sha256(_body_bytes(body)).hexdigest()),
        *body,
    )
    return _body_bytes(fields)


def decode_response(payload: bytes) -> Response:
    keys, fields = _parse_lines(payload)
    expected = [
        "version",
        "kind",
        "session",
        "request",
        "verb",
        "result",
        "body_sha256",
        *RESPONSE_BODY_FIELDS,
    ]
    if keys != expected:
        raise ProtocolViolation("BAD_FIELDS")
    response = Response(
        session=fields["session"],
        request=fields["request"],
        verb=fields["verb"],
        result=fields["result"],
        state=fields["state"],
        prepared_bundle=fields["prepared_bundle"],
        manifest_sha256=fields["manifest_sha256"],
        prepare_request=fields["prepare_request"],
        commit_request=fields["commit_request"],
        commit_fingerprint=fields["commit_fingerprint"],
        execution_started=fields["execution_started"],
        watchdog=fields["watchdog"],
        last_error=fields["last_error"],
        postmortem_state=fields["postmortem_state"],
        postmortem_records=fields["postmortem_records"],
        postmortem_bytes=fields["postmortem_bytes"],
        postmortem_sha256=fields["postmortem_sha256"],
        postmortem_tail_hex=fields["postmortem_tail_hex"],
        postmortem_lineage_state=fields["postmortem_lineage_state"],
        postmortem_lineage_matches=fields["postmortem_lineage_matches"],
        postmortem_lineage_sha256=fields["postmortem_lineage_sha256"],
    )
    if fields["version"] != "1" or fields["kind"] != "response":
        raise ProtocolViolation("BAD_VERSION")
    body = tuple((name, fields[name]) for name in RESPONSE_BODY_FIELDS)
    if hashlib.sha256(_body_bytes(body)).hexdigest() != fields["body_sha256"]:
        raise ProtocolViolation("BAD_BODY_HASH")
    encode_response(response)
    return response


def decode_progress(payload: bytes) -> Progress:
    keys, fields = _parse_lines(payload)
    expected = [
        "version",
        "kind",
        "session",
        "request",
        "verb",
        "body_sha256",
        *PROGRESS_BODY_FIELDS,
    ]
    if keys != expected:
        raise ProtocolViolation("BAD_FIELDS")
    if (
        fields["version"] != "1"
        or fields["kind"] != "progress"
        or fields["verb"] != "PREPARE"
    ):
        raise ProtocolViolation("BAD_VERSION")
    body = tuple((name, fields[name]) for name in PROGRESS_BODY_FIELDS)
    if hashlib.sha256(_body_bytes(body)).hexdigest() != fields["body_sha256"]:
        raise ProtocolViolation("BAD_BODY_HASH")
    sequence_text = fields["sequence"]
    if (
        not sequence_text.isdecimal()
        or (len(sequence_text) > 1 and sequence_text.startswith("0"))
    ):
        raise ProtocolViolation("BAD_PROGRESS")
    progress = Progress(
        session=fields["session"],
        request=fields["request"],
        sequence=int(sequence_text),
        phase=fields["phase"],
        bundle=fields["bundle"],
        manifest_sha256=fields["manifest_sha256"],
        watchdog=fields["watchdog"],
    )
    encode_progress(progress)
    return progress


def decode_recovery_record(payload: bytes) -> Response | Progress:
    _keys, fields = _parse_lines(payload)
    kind = fields.get("kind")
    if kind == "response":
        return decode_response(payload)
    if kind == "progress":
        return decode_progress(payload)
    raise ProtocolViolation("BAD_KIND")


def _body_bytes(body: tuple[tuple[str, str], ...]) -> bytes:
    return "".join(f"{key}={value}\n" for key, value in body).encode("ascii")


def _parse_lines(payload: bytes) -> tuple[list[str], dict[str, str]]:
    if not payload or len(payload) > MAX_FRAME_PAYLOAD:
        raise ProtocolViolation("BAD_PAYLOAD")
    try:
        text = payload.decode("ascii")
    except UnicodeDecodeError as error:
        raise ProtocolViolation("NON_ASCII") from error
    if not text.endswith("\n") or "\r" in text or "\x00" in text:
        raise ProtocolViolation("NON_CANONICAL")
    keys: list[str] = []
    fields: dict[str, str] = {}
    for line in text[:-1].split("\n"):
        if "=" not in line:
            raise ProtocolViolation("BAD_FIELD")
        key, value = line.split("=", 1)
        if not KEY.fullmatch(key) or not VALUE.fullmatch(value):
            raise ProtocolViolation("BAD_FIELD")
        if key in fields:
            raise ProtocolViolation("DUPLICATE_FIELD")
        keys.append(key)
        fields[key] = value
    return keys, fields


def decode_request(payload: bytes) -> Request:
    keys, fields = _parse_lines(payload)
    verb = fields.get("verb", "")
    body_names = VERB_FIELDS.get(verb)
    if body_names is None:
        raise ProtocolViolation("UNKNOWN_VERB")
    expected = list(COMMON_FIELDS + body_names)
    if keys != expected:
        raise ProtocolViolation("BAD_FIELDS")
    if fields["version"] != "1" or fields["kind"] != "request":
        raise ProtocolViolation("BAD_VERSION")
    if not HEX_ID.fullmatch(fields["session"]):
        raise ProtocolViolation("BAD_SESSION")
    if not HEX_ID.fullmatch(fields["request"]) or fields["request"] == ZERO_ID:
        raise ProtocolViolation("BAD_REQUEST_ID")
    if not HEX_SHA256.fullmatch(fields["body_sha256"]):
        raise ProtocolViolation("BAD_BODY_HASH")
    if verb == "HELLO":
        if fields["session"] != ZERO_ID:
            raise ProtocolViolation("BAD_SESSION")
    elif fields["session"] == ZERO_ID:
        raise ProtocolViolation("BAD_SESSION")

    body = tuple((name, fields[name]) for name in body_names)
    if hashlib.sha256(_body_bytes(body)).hexdigest() != fields["body_sha256"]:
        raise ProtocolViolation("BAD_BODY_HASH")

    if verb == "PREPARE":
        bundle = fields["bundle"]
        if (
            bundle == "none"
            or not BUNDLE_ID.fullmatch(bundle)
            or ".." in bundle
        ):
            raise ProtocolViolation("BAD_BUNDLE")
        if (
            not HEX_SHA256.fullmatch(fields["manifest_sha256"])
            or fields["manifest_sha256"] == ZERO_SHA256
        ):
            raise ProtocolViolation("BAD_MANIFEST_HASH")
    elif verb == "COMMIT_EXEC":
        if (
            not HEX_ID.fullmatch(fields["prepare_request"])
            or fields["prepare_request"] == ZERO_ID
        ):
            raise ProtocolViolation("BAD_PREPARE_ID")
        if (
            not HEX_SHA256.fullmatch(fields["manifest_sha256"])
            or fields["manifest_sha256"] == ZERO_SHA256
        ):
            raise ProtocolViolation("BAD_MANIFEST_HASH")

    return Request(
        version=fields["version"],
        kind=fields["kind"],
        session=fields["session"],
        request=fields["request"],
        verb=verb,
        body_sha256=fields["body_sha256"],
        body=body,
        wire=payload,
    )


def encode_request(
    *,
    session: str,
    request: str,
    verb: str,
    body: Mapping[str, str] | None = None,
) -> bytes:
    body_names = VERB_FIELDS.get(verb)
    if body_names is None:
        raise ProtocolViolation("UNKNOWN_VERB")
    body = {} if body is None else dict(body)
    if tuple(body) != body_names:
        raise ProtocolViolation("BAD_FIELDS")
    body_items = tuple((name, body[name]) for name in body_names)
    fields = (
        ("version", "1"),
        ("kind", "request"),
        ("session", session),
        ("request", request),
        ("verb", verb),
        ("body_sha256", hashlib.sha256(_body_bytes(body_items)).hexdigest()),
        *body_items,
    )
    payload = _body_bytes(fields)
    decode_request(payload)
    return payload


@dataclass
class LedgerEntry:
    fingerprint: str
    response: Response


@dataclass
class RecoveryState:
    session: str = field(default_factory=lambda: secrets.token_hex(16))
    phase: str = "IDLE"
    prepared_bundle: str | None = None
    manifest_sha256: str | None = None
    prepare_request: str | None = None
    prepare_fingerprint: str | None = None
    commit_request: str | None = None
    commit_fingerprint: str | None = None
    claim_owner: str | None = None
    execution_started: bool = False
    watchdog_armed: bool = True
    last_error: str = "NONE"
    prepare_calls: int = 0
    execute_claims: int = 0
    execute_calls: int = 0
    ledger: OrderedDict[str, LedgerEntry] = field(default_factory=OrderedDict)

    def __post_init__(self) -> None:
        if not HEX_ID.fullmatch(self.session) or self.session == ZERO_ID:
            raise ValueError("state session must be a nonzero 128-bit hex ID")
        if self.phase not in STATES:
            raise ValueError("invalid recovery phase")
        if not self.watchdog_armed:
            raise ValueError("recovery watchdog must remain armed")
        if self.last_error not in LAST_ERRORS:
            raise ValueError("invalid recovery error")
        if self.prepared_bundle is not None and (
            self.prepared_bundle == "none"
            or not BUNDLE_ID.fullmatch(self.prepared_bundle)
            or ".." in self.prepared_bundle
        ):
            raise ValueError("invalid prepared bundle")
        if (
            self.manifest_sha256 is not None
            and (
                not HEX_SHA256.fullmatch(self.manifest_sha256)
                or self.manifest_sha256 == ZERO_SHA256
            )
        ):
            raise ValueError("invalid prepared manifest")
        for value, label in (
            (self.prepare_request, "prepare request"),
            (self.commit_request, "commit request"),
        ):
            if value is not None and (
                not HEX_ID.fullmatch(value) or value == ZERO_ID
            ):
                raise ValueError(f"invalid {label}")
        if (
            self.prepare_fingerprint is not None
            and (
                not HEX_SHA256.fullmatch(self.prepare_fingerprint)
                or self.prepare_fingerprint == ZERO_SHA256
            )
        ):
            raise ValueError("invalid prepare fingerprint")
        if (
            self.commit_fingerprint is not None
            and (
                not HEX_SHA256.fullmatch(self.commit_fingerprint)
                or self.commit_fingerprint == ZERO_SHA256
            )
        ):
            raise ValueError("invalid commit fingerprint")
        if any(
            type(value) is not int or value < 0
            for value in (
                self.prepare_calls,
                self.execute_claims,
                self.execute_calls,
            )
        ):
            raise ValueError("invalid recovery counters")
        prepared_values = (
            self.prepared_bundle is not None,
            self.manifest_sha256 is not None,
            self.prepare_request is not None,
            self.prepare_fingerprint is not None,
        )
        claimed_values = (
            self.commit_request is not None,
            self.commit_fingerprint is not None,
        )
        prepared = all(prepared_values)
        claimed = all(claimed_values)
        if any(prepared_values) != prepared or any(claimed_values) != claimed:
            raise ValueError("partial recovery transaction")
        if self.phase == "IDLE" and (prepared or claimed):
            raise ValueError("idle state contains a transaction")
        if self.phase == "PREPARED" and (not prepared or claimed):
            raise ValueError("prepared state is inconsistent")
        if self.phase in {"CLAIMED", "EXEC_FAILED"} and (
            not prepared or not claimed
        ):
            raise ValueError("claimed state is inconsistent")
        if self.execution_started and self.phase not in {
            "CLAIMED",
            "EXEC_FAILED",
        }:
            raise ValueError("execution marker is inconsistent")
        if (
            self.phase == "EXEC_FAILED"
            and not self.execution_started
            and self.last_error != "HAVEN_WDOG_FAILED"
        ):
            raise ValueError("terminal state lacks execution marker")
        if self.last_error == "HAVEN_WDOG_FAILED" and (
            self.phase != "EXEC_FAILED" or self.execution_started
        ):
            raise ValueError("invalid Haven watchdog failure state")
        if not isinstance(self.ledger, OrderedDict):
            raise ValueError("invalid recovery ledger")
        for request, entry in self.ledger.items():
            if (
                not isinstance(request, str)
                or not HEX_ID.fullmatch(request)
                or request == ZERO_ID
                or not isinstance(entry, LedgerEntry)
                or not isinstance(entry.fingerprint, str)
                or not HEX_SHA256.fullmatch(entry.fingerprint)
                or entry.fingerprint == ZERO_SHA256
                or entry.response.request != request
                or entry.response.session != self.session
            ):
                raise ValueError("invalid recovery ledger entry")
            encode_response(entry.response)

    def snapshot(self) -> bytes:
        data = {
            "version": 1,
            "session": self.session,
            "phase": self.phase,
            "prepared_bundle": self.prepared_bundle,
            "manifest_sha256": self.manifest_sha256,
            "prepare_request": self.prepare_request,
            "prepare_fingerprint": self.prepare_fingerprint,
            "commit_request": self.commit_request,
            "commit_fingerprint": self.commit_fingerprint,
            "execution_started": self.execution_started,
            "watchdog_armed": self.watchdog_armed,
            "last_error": self.last_error,
            "prepare_calls": self.prepare_calls,
            "execute_claims": self.execute_claims,
            "execute_calls": self.execute_calls,
            "ledger": [
                {
                    "request": request,
                    "fingerprint": entry.fingerprint,
                    "response": asdict(entry.response),
                }
                for request, entry in self.ledger.items()
            ],
        }
        return (
            json.dumps(data, sort_keys=True, separators=(",", ":")) + "\n"
        ).encode("ascii")

    @classmethod
    def from_snapshot(cls, payload: bytes) -> "RecoveryState":
        if len(payload) > MAX_SNAPSHOT_BYTES:
            raise ValueError("recovery snapshot is too large")
        def unique(pairs):
            result = {}
            for key, value in pairs:
                if key in result:
                    raise ValueError("duplicate recovery snapshot field")
                result[key] = value
            return result

        data = json.loads(
            payload.decode("ascii"),
            object_pairs_hook=unique,
        )
        if not isinstance(data, dict):
            raise ValueError("invalid recovery snapshot")
        if data.pop("version", None) != 1:
            raise ValueError("invalid recovery snapshot version")
        ledger_data = data.pop("ledger", None)
        if not isinstance(ledger_data, list):
            raise ValueError("invalid recovery snapshot ledger")
        ledger: OrderedDict[str, LedgerEntry] = OrderedDict()
        for item in ledger_data:
            if not isinstance(item, dict) or set(item) != {
                "request",
                "fingerprint",
                "response",
            }:
                raise ValueError("invalid recovery snapshot entry")
            request = item["request"]
            fingerprint = item["fingerprint"]
            if (
                not isinstance(request, str)
                or not HEX_ID.fullmatch(request)
                or request == ZERO_ID
                or not isinstance(fingerprint, str)
                or not HEX_SHA256.fullmatch(fingerprint)
                or request in ledger
            ):
                raise ValueError("invalid recovery snapshot identity")
            if not isinstance(item["response"], dict):
                raise ValueError("invalid recovery snapshot response")
            response = Response(**item["response"])
            encode_response(response)
            ledger[request] = LedgerEntry(
                fingerprint=fingerprint,
                response=response,
            )
        expected = {
            "session",
            "phase",
            "prepared_bundle",
            "manifest_sha256",
            "prepare_request",
            "prepare_fingerprint",
            "commit_request",
            "commit_fingerprint",
            "execution_started",
            "watchdog_armed",
            "last_error",
            "prepare_calls",
            "execute_claims",
            "execute_calls",
        }
        if set(data) != expected:
            raise ValueError("invalid recovery snapshot fields")
        return cls(**data, claim_owner=None, ledger=ledger)


class RecoveryModel:
    """State oracle for one recovery boot and responder restarts."""

    def __init__(
        self,
        state: RecoveryState | None = None,
        *,
        maximum_ledger_entries: int = 32,
        fetcher: Callable[[str, str], str] | None = None,
        verifier: Callable[[str, str], bool] | None = None,
    ):
        if maximum_ledger_entries < 4:
            raise ValueError("ledger bound must retain active transactions")
        self.state = RecoveryState() if state is None else state
        self.maximum_ledger_entries = maximum_ledger_entries
        self.fetcher = fetcher or (lambda _bundle, _manifest: "FETCHED")
        self.verifier = verifier or (lambda _bundle, _manifest: True)
        self.owner = secrets.token_hex(16)

    def _response(self, request: Request, result: str) -> Response:
        response = Response(
            session=self.state.session,
            request=request.request,
            verb=request.verb,
            result=result,
            state=self.state.phase,
            prepared_bundle=self.state.prepared_bundle or "none",
            manifest_sha256=self.state.manifest_sha256 or ZERO_SHA256,
            prepare_request=self.state.prepare_request or ZERO_ID,
            commit_request=self.state.commit_request or ZERO_ID,
            commit_fingerprint=self.state.commit_fingerprint or ZERO_SHA256,
            execution_started="YES" if self.state.execution_started else "NO",
            watchdog="ARMED" if self.state.watchdog_armed else "INVALID",
            last_error=self.state.last_error,
        )
        encode_response(response)
        return response

    def _remember(self, request: Request, response: Response) -> None:
        if request.verb in {"HELLO", "STATUS"}:
            raise ValueError("read-only requests are not transaction decisions")
        self.state.ledger[request.request] = LedgerEntry(
            fingerprint=request.fingerprint,
            response=response,
        )
        self.state.ledger.move_to_end(request.request)
        if len(self.state.ledger) > self.maximum_ledger_entries:
            raise RuntimeError("request ledger exceeded its fixed bound")

    def handle(
        self,
        request: Request | bytes,
        *,
        inject: str | None = None,
    ) -> Response:
        if isinstance(request, bytes):
            request = decode_request(request)
        if request.verb != "HELLO" and request.session != self.state.session:
            return self._response(request, "STALE_SESSION")

        if request.verb in {"HELLO", "STATUS"}:
            response = self._response(request, "OK")
            if inject == "after_response":
                raise InjectedCrash("after_response")
            return response

        previous = self.state.ledger.get(request.request)
        if previous is not None:
            if previous.fingerprint == request.fingerprint:
                return self._response(request, previous.response.result)
            return self._response(request, "REQUEST_CONFLICT")

        if (
            request.request == self.state.commit_request
            and self.state.commit_fingerprint is not None
        ):
            if request.fingerprint != self.state.commit_fingerprint:
                return self._response(request, "REQUEST_CONFLICT")
            return self._response(request, "CLAIMED")

        if (
            request.request == self.state.prepare_request
            and self.state.prepare_fingerprint is not None
        ):
            if request.fingerprint != self.state.prepare_fingerprint:
                return self._response(request, "REQUEST_CONFLICT")
            return self._response(request, "PREPARED")

        reserved = self.maximum_ledger_entries - 3
        if len(self.state.ledger) >= self.maximum_ledger_entries:
            self.state.last_error = "LEDGER_FULL"
            return self._response(request, "LEDGER_FULL")
        if len(self.state.ledger) >= reserved:
            can_use_reserved = False
            if (
                request.verb == "PREPARE"
                and self.state.phase == "IDLE"
                and len(self.state.ledger) == reserved
            ):
                can_use_reserved = True
            elif (
                request.verb == "COMMIT_EXEC"
                and self.state.phase == "PREPARED"
                and request.value("prepare_request")
                == self.state.prepare_request
                and request.value("manifest_sha256")
                == self.state.manifest_sha256
            ):
                can_use_reserved = True
            if not can_use_reserved:
                self.state.last_error = "LEDGER_FULL"
                return self._response(request, "LEDGER_FULL")

        fetch_decided = any(
            entry.response.verb == "PREPARE"
            and entry.response.result in {
                "FETCH_FAILED",
                "BUNDLE_ID_CONFLICT",
                "PREPARE_ID_CONFLICT",
            }
            for entry in self.state.ledger.values()
        )
        if (
            request.verb == "PREPARE"
            and self.state.phase == "IDLE"
            and fetch_decided
        ):
            response = self._response(request, "PREPARE_ID_CONFLICT")
        elif request.verb == "PREPARE":
            response = self._prepare(
                request,
                inject=inject,
                verified=None,
            )
        elif request.verb == "COMMIT_EXEC":
            response = self._commit(request, inject=inject)
        else:
            raise AssertionError("decode_request admitted an unknown verb")

        self._remember(request, response)
        if inject == "after_response":
            raise InjectedCrash("after_response")
        return response

    def _prepare(
        self,
        request: Request,
        *,
        inject: str | None,
        verified: bool | None,
    ) -> Response:
        bundle = request.value("bundle")
        manifest = request.value("manifest_sha256")
        if self.state.phase == "IDLE":
            fetched = self.fetcher(bundle, manifest)
            if fetched == "BUNDLE_ID_CONFLICT":
                self.state.last_error = "BUNDLE_ID_CONFLICT"
                return self._response(request, "BUNDLE_ID_CONFLICT")
            if fetched == "FETCH_FAILED":
                self.state.last_error = "FETCH_FAILED"
                return self._response(request, "FETCH_FAILED")
            if fetched != "FETCHED":
                raise ValueError("invalid fixed-fetch outcome")
            self.state.prepare_calls += 1
            if verified is None:
                verified = self.verifier(bundle, manifest)
            if not verified:
                self.state.last_error = "VERIFY_FAILED"
                return self._response(request, "VERIFY_FAILED")
            self.state.prepared_bundle = bundle
            self.state.manifest_sha256 = manifest
            self.state.prepare_request = request.request
            self.state.prepare_fingerprint = request.fingerprint
            self.state.phase = "PREPARED"
            if inject == "after_prepare":
                raise InjectedCrash("after_prepare")
            return self._response(request, "PREPARED")
        if (
            self.state.phase == "PREPARED"
            and bundle == self.state.prepared_bundle
            and manifest == self.state.manifest_sha256
        ):
            return self._response(request, "PREPARE_ID_CONFLICT")
        if self.state.phase == "PREPARED":
            return self._response(request, "BUNDLE_CONFLICT")
        return self._response(request, "SESSION_CONSUMED")

    def _commit(self, request: Request, *, inject: str | None) -> Response:
        if self.state.phase == "IDLE":
            return self._response(request, "PREPARE_REQUIRED")
        if self.state.phase != "PREPARED":
            return self._response(request, "ALREADY_CLAIMED")
        if (
            request.value("prepare_request") != self.state.prepare_request
            or request.value("manifest_sha256") != self.state.manifest_sha256
        ):
            return self._response(request, "PREPARE_MISMATCH")
        if inject == "before_claim":
            raise InjectedCrash("before_claim")

        self.state.phase = "CLAIMED"
        self.state.commit_request = request.request
        self.state.commit_fingerprint = request.fingerprint
        self.state.claim_owner = self.owner
        self.state.execute_claims += 1
        response = self._response(request, "CLAIMED")
        if inject == "after_claim":
            raise InjectedCrash("after_claim")
        return response

    def execute_claimed(
        self,
        executor: Callable[[], object],
        *,
        haven_handoff: Callable[[], bool],
        inject: str | None = None,
    ) -> str:
        if (
            self.state.phase != "CLAIMED"
            or self.state.claim_owner != self.owner
            or self.state.execution_started
        ):
            return self.state.phase
        if not haven_handoff():
            self.state.phase = "EXEC_FAILED"
            self.state.last_error = "HAVEN_WDOG_FAILED"
            return self.state.phase
        self.state.execution_started = True
        self.state.execute_calls += 1
        if inject == "after_execute_start":
            raise InjectedCrash("after_execute_start")
        try:
            executor()
        except TargetDeparted:
            return self.state.phase
        except InjectedCrash:
            raise
        except BaseException:
            self.state.phase = "EXEC_FAILED"
            self.state.last_error = "EXEC_FAILED"
            return self.state.phase
        self.state.phase = "EXEC_FAILED"
        self.state.last_error = "EXEC_RETURNED"
        return self.state.phase


@dataclass(frozen=True)
class IntentRecord:
    session: str
    request: str
    manifest_sha256: str
    target: str
    created_unix_ns: int
    state: str
    outcome: str


class HostIntentLedger:
    """Durable host-side write-ahead intent reference implementation."""

    def __init__(self, root: Path):
        self.root = Path(root)
        created = False
        if self.root.exists() or self.root.is_symlink():
            if self.root.is_symlink() or not self.root.is_dir():
                raise ValueError("ledger root must be an unlinked directory")
        else:
            self.root.mkdir(mode=0o700, parents=True)
            created = True
        os.chmod(self.root, 0o700)
        if created:
            parent = os.open(
                self.root.parent,
                os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
            )
            try:
                os.fsync(parent)
            finally:
                os.close(parent)
        self._dir_fd = os.open(
            self.root,
            os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
        )
        metadata = os.fstat(self._dir_fd)
        if (
            not stat.S_ISDIR(metadata.st_mode)
            or metadata.st_uid != os.geteuid()
            or stat.S_IMODE(metadata.st_mode) & 0o077
        ):
            os.close(self._dir_fd)
            raise ValueError("unsafe ledger directory")
        descriptor = os.open(
            ".lock",
            os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW,
            0o600,
            dir_fd=self._dir_fd,
        )
        os.fchmod(descriptor, 0o600)
        os.close(descriptor)

    def close(self) -> None:
        descriptor = getattr(self, "_dir_fd", -1)
        if descriptor >= 0:
            os.close(descriptor)
            self._dir_fd = -1

    def __del__(self):
        try:
            self.close()
        except OSError:
            pass

    @staticmethod
    def _validate_hex(value: str, pattern: re.Pattern[str], label: str) -> None:
        if (
            not isinstance(value, str)
            or not pattern.fullmatch(value)
            or value == ZERO_ID
        ):
            raise ValueError(f"invalid {label}")

    def _record_name(self, session: str) -> str:
        self._validate_hex(session, HEX_ID, "session")
        return f"{session}.json"

    @contextmanager
    def _locked(self):
        descriptor = os.open(
            ".lock",
            os.O_RDWR | os.O_NOFOLLOW,
            dir_fd=self._dir_fd,
        )
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX)
            yield
        finally:
            fcntl.flock(descriptor, fcntl.LOCK_UN)
            os.close(descriptor)

    @staticmethod
    def _decode_json(stream) -> dict[str, object]:
        def unique(pairs):
            result = {}
            for key, value in pairs:
                if key in result:
                    raise ValueError("duplicate ledger field")
                result[key] = value
            return result

        return json.load(stream, object_pairs_hook=unique)

    @staticmethod
    def _validate_record(record: IntentRecord, session: str) -> None:
        if record.session != session:
            raise ValueError("ledger session does not match its path")
        HostIntentLedger._validate_hex(record.session, HEX_ID, "session")
        HostIntentLedger._validate_hex(record.request, HEX_ID, "request")
        if (
            not isinstance(record.manifest_sha256, str)
            or not HEX_SHA256.fullmatch(record.manifest_sha256)
        ):
            raise ValueError("invalid ledger manifest hash")
        if (
            not isinstance(record.target, str)
            or not re.fullmatch(r"[A-Za-z0-9._-]{1,64}", record.target)
        ):
            raise ValueError("invalid ledger target")
        if type(record.created_unix_ns) is not int or record.created_unix_ns < 1:
            raise ValueError("invalid ledger timestamp")
        if (
            not isinstance(record.state, str)
            or record.state not in {"TRANSMITTED", "RESOLVED"}
        ):
            raise ValueError("invalid ledger state")
        if not isinstance(record.outcome, str) or record.outcome not in {
            "UNKNOWN",
            "TARGET_ACCEPTED",
            "FALLBACK_RETURNED",
            "RECOVERY_REJECTED",
        }:
            raise ValueError("invalid ledger outcome")
        if (
            record.state == "TRANSMITTED"
            and record.outcome != "UNKNOWN"
        ) or (
            record.state == "RESOLVED"
            and record.outcome == "UNKNOWN"
        ):
            raise ValueError("inconsistent ledger state")

    def read(self, session: str) -> IntentRecord | None:
        name = self._record_name(session)
        try:
            descriptor = os.open(
                name,
                os.O_RDONLY | os.O_NOFOLLOW,
                dir_fd=self._dir_fd,
            )
        except FileNotFoundError:
            return None
        metadata = os.fstat(descriptor)
        if (
            not stat.S_ISREG(metadata.st_mode)
            or metadata.st_uid != os.geteuid()
            or stat.S_IMODE(metadata.st_mode) & 0o077
            or metadata.st_size < 2
            or metadata.st_size > MAX_FRAME_PAYLOAD
        ):
            os.close(descriptor)
            raise ValueError("unsafe ledger record")
        with os.fdopen(descriptor, "r", encoding="ascii") as stream:
            data = self._decode_json(stream)
        record = IntentRecord(**data)
        self._validate_record(record, session)
        return record

    def arm(
        self,
        *,
        session: str,
        request: str,
        manifest_sha256: str,
        target: str,
        inject: str | None = None,
    ) -> IntentRecord:
        name = self._record_name(session)
        self._validate_hex(request, HEX_ID, "request")
        if (
            not isinstance(manifest_sha256, str)
            or not HEX_SHA256.fullmatch(manifest_sha256)
            or manifest_sha256 == ZERO_SHA256
        ):
            raise ValueError("invalid manifest hash")
        if (
            not isinstance(target, str)
            or not re.fullmatch(r"[A-Za-z0-9._-]{1,64}", target)
        ):
            raise ValueError("invalid target")
        record = IntentRecord(
            session=session,
            request=request,
            manifest_sha256=manifest_sha256,
            target=target,
            created_unix_ns=time.time_ns(),
            state="TRANSMITTED",
            outcome="UNKNOWN",
        )
        with self._locked():
            try:
                os.stat(
                    name,
                    dir_fd=self._dir_fd,
                    follow_symlinks=False,
                )
            except FileNotFoundError:
                pass
            else:
                raise FileExistsError("session already has a commit intent")
            self._write(
                name,
                record,
                create_only=True,
                inject=inject,
            )
        return record

    def resolve(
        self,
        *,
        session: str,
        request: str,
        outcome: str,
    ) -> IntentRecord:
        if outcome not in {
            "TARGET_ACCEPTED",
            "FALLBACK_RETURNED",
            "RECOVERY_REJECTED",
        }:
            raise ValueError("invalid outcome")
        self._validate_hex(request, HEX_ID, "request")
        with self._locked():
            current = self.read(session)
            if current is None:
                raise FileNotFoundError("intent does not exist")
            if current.request != request:
                raise ValueError("request does not match session intent")
            if current.state == "RESOLVED":
                if current.outcome != outcome:
                    raise ValueError("resolved outcome is immutable")
                return current
            resolved = IntentRecord(
                session=current.session,
                request=current.request,
                manifest_sha256=current.manifest_sha256,
                target=current.target,
                created_unix_ns=current.created_unix_ns,
                state="RESOLVED",
                outcome=outcome,
            )
            self._write(self._record_name(session), resolved)
        return resolved

    def _write(
        self,
        name: str,
        record: IntentRecord,
        *,
        create_only: bool = False,
        inject: str | None = None,
    ) -> None:
        temporary = f".{name}.{secrets.token_hex(8)}.tmp"
        payload = (
            json.dumps(asdict(record), sort_keys=True, separators=(",", ":"))
            + "\n"
        ).encode("ascii")
        descriptor = os.open(
            temporary,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
            0o600,
            dir_fd=self._dir_fd,
        )
        try:
            written = 0
            while written < len(payload):
                count = os.write(descriptor, payload[written:])
                if count == 0:
                    raise OSError("short ledger write")
                written += count
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
        if inject == "after_file_fsync":
            raise InjectedCrash("after_file_fsync")
        if create_only:
            try:
                os.link(
                    temporary,
                    name,
                    src_dir_fd=self._dir_fd,
                    dst_dir_fd=self._dir_fd,
                    follow_symlinks=False,
                )
            except FileExistsError:
                os.unlink(temporary, dir_fd=self._dir_fd)
                raise
            os.unlink(temporary, dir_fd=self._dir_fd)
        else:
            os.replace(
                temporary,
                name,
                src_dir_fd=self._dir_fd,
                dst_dir_fd=self._dir_fd,
            )
        if inject == "after_replace":
            raise InjectedCrash("after_replace")
        os.fsync(self._dir_fd)
