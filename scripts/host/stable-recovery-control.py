#!/usr/bin/env python3
"""Drive one framed stable-recovery transaction with a durable host intent."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import errno
import glob
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import select
import shutil
import stat
import subprocess
import sys
import termios
import time
import tty
from typing import Callable, NoReturn


REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from tools.recovery_control import (  # noqa: E402
    ZERO_ID,
    FrameParser,
    HostIntentLedger,
    PREPARE_PROGRESS_PHASES,
    Progress,
    Response,
    decode_recovery_record,
    encode_frame,
    encode_request,
)

SS = Path("/usr/bin/ss")
NETWORK_ROOT_BUNDLE = "headless-network-root-v1"
DEPLOYMENT_NETWORK_ROOT_BUNDLE = "headless-ssh-network-root-v3-r2"
# Both bundles intentionally use the same sealed v3 export; package_sha256
# remains the per-payload identity carried by the handoff marker.
# Read-side compatibility for immutable consumed Generations 0-12. No current
# candidate or credentialed builder emits this identity.
LEGACY_DIAGNOSTIC_NETWORK_ROOT_BUNDLE = "headless-netroot-early-diag-v1"
DIAGNOSTIC_NETWORK_ROOT_BUNDLE = "headless-netroot-early-diag-v2"
FULL_UCSI_CHARGING_BUNDLE = "headless-full-ucsi-charging-v1"
V3_NETWORK_ROOT_BUNDLES = frozenset(
    {
        DEPLOYMENT_NETWORK_ROOT_BUNDLE,
        LEGACY_DIAGNOSTIC_NETWORK_ROOT_BUNDLE,
        DIAGNOSTIC_NETWORK_ROOT_BUNDLE,
        FULL_UCSI_CHARGING_BUNDLE,
    }
)
NETWORK_ROOT_BUNDLES = frozenset({NETWORK_ROOT_BUNDLE}) | V3_NETWORK_ROOT_BUNDLES
DEPLOYMENT_NFS_PROFILE = "headless-ssh-deployment-v3"
NFS_HANDOFF_MARKER = Path("/run/rog5-network-root-nfs-ready")
NFS_HANDOFF_ROOT = Path("/var/lib/rog5-headless-network-root-v1/root")
DEPLOYMENT_NFS_HANDOFF_ROOT = Path(
    "/home/rog5-linux/exports/headless-ssh-network-root-v3/root"
)
PREPARE_DEADLINE_SECONDS = 260
# The sealed export can become ready just after 45 seconds on a cold host.
# This is only a pre-COMMIT wait; readiness returns immediately when observed.
NFS_READY_TIMEOUT_SECONDS = 90
POST_CLAIM_STATUS_TIMEOUT_SECONDS = 8
POST_CLAIM_DEPARTURE_TIMEOUT_SECONDS = 2.0
POST_CLAIM_DEPARTURE_POLL_SECONDS = 0.1
RECOVERY_ACM_TRACE_LIMIT = 16
RECOVERY_ACM_COUNT_LIMIT = 999
RECOVERY_ACM_STATES = (
    "absent",
    "inspect-error",
    "product-mismatch",
    "node-mismatch",
    "duplicate",
    "unreadable",
    "read-only",
    "exact",
)
RECOVERY_ACM_IDENTITY_FIELDS = (
    "path",
    "rdev",
    "devpath",
    "id-path",
    "serial",
)
RECOVERY_ACM_DISCOVERY_PHASES = frozenset({"initial", "prepare-replay"})
TARGET_LINEAGE_PREFIX = (
    "rog5-network-root: lineage "
    "format=rog5-target-lineage-v1 candidate="
)
CANDIDATE_ID = re.compile(r"[a-z0-9][a-z0-9._-]{0,63}\Z")
BOOT_ID = re.compile(
    r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-"
    r"[0-9a-f]{4}-[0-9a-f]{12}\Z"
)


class TransportLost(RuntimeError):
    """The ACM transaction ended without one correlated response."""


class RecoveryAcmUnavailable(RuntimeError):
    """Bounded recovery ACM discovery evidence for one named phase."""


@dataclass(frozen=True)
class PostmortemLineageCorrelation:
    """Expected identity and bounded recovery snapshot classification."""

    classification: str
    recovery_session: str
    status_request: str
    postmortem_state: str
    postmortem_records: str
    postmortem_bytes: str
    postmortem_sha256: str
    expected_candidate: str
    expected_boot_id: str
    expected_lineage_sha256: str
    observed_lineage_matches: str
    observed_lineage_sha256: str


def bounded_failure_summary(
    error: BaseException,
    allowed: tuple[type[BaseException], ...],
) -> str:
    """Return one printable bounded detail only for fixed exception types."""
    if isinstance(error, allowed):
        summary = str(error)
        if re.fullmatch(r"[\x20-\x7e]{1,512}", summary):
            return summary
    return type(error).__name__


@dataclass(frozen=True)
class RecoveryAcmObservation:
    """One sanitized recovery ACM inventory sample."""

    state: str
    identity: tuple[str, int, str, str, str] | None = None

    def __post_init__(self) -> None:
        if self.state not in RECOVERY_ACM_STATES:
            raise ValueError("invalid recovery ACM observation state")
        if (self.state == "exact") != (self.identity is not None):
            raise ValueError("recovery ACM identity/state mismatch")

    def path(self) -> str:
        if self.identity is None:
            fail("recovery ACM observation has no exact device")
        return self.identity[0]


@dataclass
class RecoveryAcmTrace:
    """Bounded state transitions with no device identity values."""

    counts: dict[str, int] = field(
        default_factory=lambda: {state: 0 for state in RECOVERY_ACM_STATES}
    )
    transitions: list[str] = field(default_factory=list)
    changed_fields: set[str] = field(default_factory=set)
    transitions_truncated: bool = False
    _last_state: str | None = None
    _last_identity: tuple[str, int, str, str, str] | None = None

    def record(self, observation: RecoveryAcmObservation) -> None:
        self.counts[observation.state] = min(
            RECOVERY_ACM_COUNT_LIMIT,
            self.counts[observation.state] + 1,
        )
        if observation.state != self._last_state:
            if len(self.transitions) < RECOVERY_ACM_TRACE_LIMIT:
                self.transitions.append(observation.state)
            else:
                self.transitions_truncated = True
            self._last_state = observation.state
        if observation.identity is not None:
            if self._last_identity is not None:
                for label, previous, current in zip(
                    RECOVERY_ACM_IDENTITY_FIELDS,
                    self._last_identity,
                    observation.identity,
                    strict=True,
                ):
                    if previous != current:
                        self.changed_fields.add(label)
            self._last_identity = observation.identity

    def summary(self) -> str:
        states = ",".join(
            f"{state}:{self.counts[state]}"
            for state in RECOVERY_ACM_STATES
            if self.counts[state]
        ) or "none"
        transitions = ">".join(self.transitions) or "none"
        changes = ",".join(
            field_name
            for field_name in RECOVERY_ACM_IDENTITY_FIELDS
            if field_name in self.changed_fields
        ) or "none"
        truncated = "yes" if self.transitions_truncated else "no"
        return (
            f"states={states}; transitions={transitions}; "
            f"identity_changes={changes}; transitions_truncated={truncated}"
        )


@dataclass
class PrepareProgressTrace:
    """Correlated, ordered PREPARE evidence from at most two attempts."""

    session: str
    request: str
    bundle: str
    manifest_sha256: str
    attempts: list[list[str]] = field(default_factory=lambda: [[]])

    def record(self, progress: Progress) -> None:
        if (
            progress.session != self.session
            or progress.request != self.request
            or progress.bundle != self.bundle
            or progress.manifest_sha256 != self.manifest_sha256
            or progress.watchdog != "ARMED"
        ):
            fail("PREPARE progress does not correlate to the request")
        current = self.attempts[-1]
        expected_sequence = len(current) + 1
        if (
            expected_sequence > len(PREPARE_PROGRESS_PHASES)
            or progress.sequence != expected_sequence
            or progress.phase
            != PREPARE_PROGRESS_PHASES[expected_sequence - 1]
        ):
            fail("PREPARE progress is not a contiguous ordered prefix")
        current.append(progress.phase)

    def start_replay(self) -> None:
        if len(self.attempts) != 1:
            fail("PREPARE progress permits only one replay attempt")
        self.attempts.append([])

    def summary(self) -> str:
        return ";".join(
            f"attempt{index}=" + (">".join(phases) or "none")
            for index, phases in enumerate(self.attempts, 1)
        )


def fail(message: str) -> NoReturn:
    raise RuntimeError(message)


def request_id() -> str:
    value = ZERO_ID
    while value == ZERO_ID:
        value = secrets.token_hex(16)
    return value


def ledger_root() -> Path:
    state_home = os.environ.get("XDG_STATE_HOME")
    base = Path(state_home) if state_home else Path.home() / ".local" / "state"
    return base / "rog5-recovery-intents"


def udev_properties(device: str) -> dict[str, str]:
    result = subprocess.run(
        ["udevadm", "info", "--query=property", f"--name={device}"],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
    )
    properties: dict[str, str] = {}
    for line in result.stdout.splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            properties[key] = value
    return properties


def observe_recovery_acm() -> RecoveryAcmObservation:
    expected = {
        "ID_VENDOR_ID": "1d6b",
        "ID_MODEL_ID": "0104",
        "ID_MODEL": "ROG5_recovery",
    }
    devices = sorted(glob.glob("/dev/ttyACM*"))
    if not devices:
        return RecoveryAcmObservation("absent")
    matches: list[tuple[str, os.stat_result, dict[str, str]]] = []
    inspection_failed = False
    node_mismatch = False
    for device in devices:
        try:
            properties = udev_properties(device)
            metadata = os.stat(device, follow_symlinks=False)
        except (OSError, subprocess.CalledProcessError):
            inspection_failed = True
            continue
        if all(properties.get(key) == value for key, value in expected.items()):
            if stat.S_ISCHR(metadata.st_mode):
                matches.append((device, metadata, properties))
            else:
                node_mismatch = True
    if inspection_failed:
        return RecoveryAcmObservation("inspect-error")
    if len(matches) > 1:
        return RecoveryAcmObservation("duplicate")
    if not matches:
        return RecoveryAcmObservation(
            "node-mismatch" if node_mismatch else "product-mismatch"
        )
    if node_mismatch:
        return RecoveryAcmObservation("node-mismatch")
    device, metadata, properties = matches[0]
    if not os.access(device, os.R_OK):
        return RecoveryAcmObservation("unreadable")
    if not os.access(device, os.W_OK):
        return RecoveryAcmObservation("read-only")
    return RecoveryAcmObservation(
        "exact",
        (
            device,
            metadata.st_rdev,
            properties.get("DEVPATH", ""),
            properties.get("ID_PATH", ""),
            properties.get("ID_SERIAL", ""),
        ),
    )


def wait_for_stable_recovery_acm(
    *,
    discovery_phase: str = "initial",
    settle_seconds: float = 2.0,
    timeout_seconds: float = 45.0,
    poll_seconds: float = 0.2,
) -> str:
    if discovery_phase not in RECOVERY_ACM_DISCOVERY_PHASES:
        raise ValueError("invalid discovery phase")
    deadline = time.monotonic() + timeout_seconds
    candidate: tuple[str, int, str, str, str] | None = None
    stable_since = 0.0
    trace = RecoveryAcmTrace()
    while time.monotonic() < deadline:
        now = time.monotonic()
        observation = observe_recovery_acm()
        trace.record(observation)
        if observation.identity is None:
            candidate = None
            stable_since = 0.0
        else:
            identity = observation.identity
            if identity != candidate:
                candidate = identity
                stable_since = now
            elif now - stable_since >= settle_seconds:
                final = observe_recovery_acm()
                trace.record(final)
                if final.identity == candidate:
                    return final.path()
                candidate = None
                stable_since = 0.0
        time.sleep(poll_seconds)
    raise RecoveryAcmUnavailable(
        "recovery ACM identity did not remain stable; "
        f"phase={discovery_phase}; {trace.summary()}"
    )


class RecoverySerial:
    def __init__(self, path: str):
        flags = os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        self.fd = os.open(path, flags)
        metadata = os.fstat(self.fd)
        if not stat.S_ISCHR(metadata.st_mode):
            self.close()
            fail("recovery ACM path is not a character device")
        tty.setraw(self.fd, termios.TCSANOW)
        attributes = termios.tcgetattr(self.fd)
        attributes[4] = termios.B115200
        attributes[5] = termios.B115200
        termios.tcsetattr(self.fd, termios.TCSANOW, attributes)
        termios.tcflush(self.fd, termios.TCIFLUSH)

    def close(self) -> None:
        descriptor = getattr(self, "fd", -1)
        if descriptor >= 0:
            os.close(descriptor)
            self.fd = -1

    def __enter__(self):
        return self

    def __exit__(self, _kind, _value, _traceback):
        self.close()

    def exchange(
        self,
        payload: bytes,
        timeout_seconds: float,
        *,
        on_progress: Callable[[Progress], None] | None = None,
    ) -> Response:
        frame = encode_frame(payload)
        deadline = time.monotonic() + timeout_seconds
        view = memoryview(frame)
        while view:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TransportLost("timed out writing a framed request")
            _, writable, _ = select.select([], [self.fd], [], remaining)
            if not writable:
                raise TransportLost("timed out writing a framed request")
            try:
                written = os.write(self.fd, view)
            except OSError as error:
                if error.errno in {errno.EIO, errno.ENODEV}:
                    raise TransportLost("recovery ACM departed while writing") from error
                raise
            if written < 1:
                raise TransportLost("recovery ACM accepted no request bytes")
            view = view[written:]

        parser = FrameParser()
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TransportLost("timed out waiting for a framed response")
            readable, _, _ = select.select([self.fd], [], [], remaining)
            if not readable:
                raise TransportLost("timed out waiting for a framed response")
            try:
                chunk = os.read(self.fd, 8192)
            except OSError as error:
                if error.errno in {errno.EIO, errno.ENODEV}:
                    raise TransportLost("recovery ACM departed before response") from error
                raise
            if not chunk:
                raise TransportLost("recovery ACM closed before response")
            payloads = parser.feed(chunk)
            if payloads:
                response = None
                for framed_payload in payloads:
                    record = decode_recovery_record(framed_payload)
                    if isinstance(record, Progress):
                        if response is not None:
                            fail("recovery returned progress after its response")
                        if on_progress is None:
                            fail("recovery returned unexpected progress")
                        on_progress(record)
                    elif response is not None:
                        fail("recovery returned multiple responses to one request")
                    else:
                        response = record
                if response is not None:
                    return response


def assert_correlated(
    response: Response,
    *,
    session: str,
    request: str,
    verb: str,
) -> None:
    if (
        response.session != session
        or response.request != request
        or response.verb != verb
    ):
        fail("recovery response does not correlate to the request")


def observe_post_claim(
    serial: RecoverySerial,
    session: str,
    committed: Response,
) -> Response | None:
    """Distinguish target departure from a responder that returned."""
    identifier = request_id()
    try:
        status = serial.exchange(
            encode_request(
                session=session,
                request=identifier,
                verb="STATUS",
            ),
            POST_CLAIM_STATUS_TIMEOUT_SECONDS,
        )
    except TransportLost as error:
        deadline = time.monotonic() + POST_CLAIM_DEPARTURE_TIMEOUT_SECONDS
        while True:
            observation = observe_recovery_acm()
            if observation.state in {"absent", "product-mismatch"}:
                return None
            if (
                observation.state != "inspect-error"
                or time.monotonic() >= deadline
            ):
                fail(
                    "post-claim response was absent while recovery ACM "
                    f"remained {observation.state}: "
                    f"{bounded_failure_summary(error, (TransportLost,))}"
                )
            time.sleep(POST_CLAIM_DEPARTURE_POLL_SECONDS)
    assert_correlated(
        status,
        session=session,
        request=identifier,
        verb="STATUS",
    )
    if (
        status.result != "OK"
        or status.watchdog != "ARMED"
        or status.prepared_bundle != committed.prepared_bundle
        or status.manifest_sha256 != committed.manifest_sha256
        or status.prepare_request != committed.prepare_request
        or status.commit_request != committed.commit_request
        or status.commit_fingerprint != committed.commit_fingerprint
    ):
        fail("post-claim recovery status is inconsistent")
    return status


def hello(serial: RecoverySerial) -> tuple[str, Response]:
    identifier = request_id()
    response = serial.exchange(
        encode_request(
            session=ZERO_ID,
            request=identifier,
            verb="HELLO",
        ),
        8,
    )
    if (
        response.request != identifier
        or response.verb != "HELLO"
        or response.result != "OK"
        or response.session == ZERO_ID
        or response.watchdog != "ARMED"
    ):
        fail("recovery HELLO did not return one armed live session")
    return response.session, response


def connect(
    *, discovery_phase: str = "initial"
) -> tuple[RecoverySerial, str, Response]:
    serial = RecoverySerial(
        wait_for_stable_recovery_acm(discovery_phase=discovery_phase)
    )
    try:
        session, response = hello(serial)
    except BaseException:
        serial.close()
        raise
    return serial, session, response


def valid_handoff_token(value: str) -> bool:
    return bool(re.fullmatch(r"[0-9a-f]{64}", value)) and value != "0" * 64


def nfs_handoff_marker_matches(
    token: str,
    bundle: str = NETWORK_ROOT_BUNDLE,
    package_sha256: str = "",
) -> bool:
    flags = os.O_RDONLY | os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = -1
    try:
        descriptor = os.open(NFS_HANDOFF_MARKER, flags)
        metadata = os.fstat(descriptor)
        if (
            not stat.S_ISREG(metadata.st_mode)
            or metadata.st_uid != 0
            or metadata.st_gid != 0
            or stat.S_IMODE(metadata.st_mode) != 0o444
            or metadata.st_nlink != 1
            or metadata.st_size > 512
        ):
            return False
        marker = os.read(descriptor, 513)
        if len(marker) > 512:
            return False
        if bundle == NETWORK_ROOT_BUNDLE and not package_sha256:
            expected = (
                "format=rog5-nfs-handoff-v1\n"
                f"token={token}\n"
                "listener=169.254.77.1:2049\n"
                "versions=4.2-only\n"
                f"export_root={NFS_HANDOFF_ROOT}\n"
            ).encode("ascii")
        elif (
            bundle in V3_NETWORK_ROOT_BUNDLES
            and re.fullmatch(r"[0-9a-f]{64}", package_sha256)
            and package_sha256 != "0" * 64
        ):
            expected = (
                "format=rog5-nfs-handoff-v2\n"
                f"profile={DEPLOYMENT_NFS_PROFILE}\n"
                f"token={token}\n"
                "listener=169.254.77.1:2049\n"
                "versions=4.2-only\n"
                f"export_root={DEPLOYMENT_NFS_HANDOFF_ROOT}\n"
                f"package_sha256={package_sha256}\n"
            ).encode("ascii")
        else:
            return False
        return secrets.compare_digest(marker, expected)
    except OSError:
        return False
    finally:
        if descriptor >= 0:
            os.close(descriptor)


def network_root_nfs_ready(
    token: str,
    bundle: str = NETWORK_ROOT_BUNDLE,
    package_sha256: str = "",
) -> bool:
    try:
        marker_matches = (
            nfs_handoff_marker_matches(token)
            if bundle == NETWORK_ROOT_BUNDLE and not package_sha256
            else nfs_handoff_marker_matches(
                token,
                bundle,
                package_sha256,
            )
        )
        if not marker_matches:
            return False
        metadata = SS.stat(follow_symlinks=False)
        if (
            not stat.S_ISREG(metadata.st_mode)
            or metadata.st_uid != 0
            or metadata.st_gid != 0
            or stat.S_IMODE(metadata.st_mode) != 0o755
        ):
            fail("fixed root-owned ss executable is unavailable")
        result = subprocess.run(
            [str(SS), "-H", "-lnt4", "sport = :2049"],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
        )
        listeners = [
            line.split()
            for line in result.stdout.splitlines()
            if line.strip()
        ]
        if (
            len(listeners) != 1
            or len(listeners[0]) < 4
            or listeners[0][3] != "169.254.77.1:2049"
        ):
            return False
        return True
    except (OSError, subprocess.CalledProcessError):
        return False


def wait_for_network_root_nfs(
    token: str,
    *,
    bundle: str = NETWORK_ROOT_BUNDLE,
    package_sha256: str = "",
    timeout_seconds: float = NFS_READY_TIMEOUT_SECONDS,
    poll_seconds: float = 0.2,
) -> None:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if network_root_nfs_ready(token, bundle, package_sha256):
            return
        time.sleep(poll_seconds)
    fail("exact network-root NFSv4.2 listener was not ready before COMMIT")


def prepare_and_commit(
    bundle: str,
    manifest_sha256: str,
    *,
    ledger_path: Path | None = None,
    before_commit: Callable[[], None] | None = None,
    on_prepared: Callable[[Response], None] | None = None,
    on_progress: Callable[[Progress], None] | None = None,
    on_committed: Callable[[Response], None] | None = None,
    on_post_claim: Callable[[Response], None] | None = None,
    require_post_claim_observation: bool = False,
) -> tuple[Response, Response, object]:
    serial, session, _hello = connect()
    prepare_deadline = time.monotonic() + PREPARE_DEADLINE_SECONDS
    prepare_identifier = request_id()
    prepare_wire = encode_request(
        session=session,
        request=prepare_identifier,
        verb="PREPARE",
        body={
            "bundle": bundle,
            "manifest_sha256": manifest_sha256,
        },
    )
    progress_trace = PrepareProgressTrace(
        session=session,
        request=prepare_identifier,
        bundle=bundle,
        manifest_sha256=manifest_sha256,
    )

    def record_progress(progress: Progress) -> None:
        progress_trace.record(progress)
        if on_progress is not None:
            on_progress(progress)

    try:
        try:
            prepared = serial.exchange(
                prepare_wire,
                prepare_deadline - time.monotonic(),
                on_progress=record_progress,
            )
        except TransportLost as initial_error:
            serial.close()
            serial = None
            progress_trace.start_replay()
            try:
                replay_serial, repeated_session, _hello = connect(
                    discovery_phase="prepare-replay"
                )
            except Exception as replay_error:
                initial_summary = bounded_failure_summary(
                    initial_error,
                    (TransportLost,),
                )
                replay_summary = bounded_failure_summary(
                    replay_error,
                    (RecoveryAcmUnavailable, TransportLost),
                )
                raise TransportLost(
                    "PREPARE transport lost before response; "
                    f"initial={initial_summary}; replay={replay_summary}; "
                    f"progress={progress_trace.summary()}"
                ) from replay_error
            serial = replay_serial
            if repeated_session != session:
                fail("recovery rebooted during PREPARE; refusing cross-session replay")
            remaining = prepare_deadline - time.monotonic()
            if remaining <= 0:
                raise TransportLost(
                    "PREPARE deadline expired before same-session replay; "
                    f"progress={progress_trace.summary()}"
                )
            try:
                prepared = serial.exchange(
                    prepare_wire,
                    remaining,
                    on_progress=record_progress,
                )
            except TransportLost as replay_error:
                initial_summary = bounded_failure_summary(
                    initial_error,
                    (TransportLost,),
                )
                replay_summary = bounded_failure_summary(
                    replay_error,
                    (TransportLost,),
                )
                raise TransportLost(
                    "PREPARE transport lost before response; "
                    f"initial={initial_summary}; replay={replay_summary}; "
                    f"progress={progress_trace.summary()}"
                ) from replay_error
        assert_correlated(
            prepared,
            session=session,
            request=prepare_identifier,
            verb="PREPARE",
        )
        if (
            prepared.result != "PREPARED"
            or prepared.state != "PREPARED"
            or prepared.prepared_bundle != bundle
            or prepared.manifest_sha256 != manifest_sha256
            or prepared.prepare_request != prepare_identifier
            or prepared.watchdog != "ARMED"
        ):
            fail(
                "recovery refused PREPARE "
                f"result={prepared.result} state={prepared.state} "
                f"last_error={prepared.last_error}"
            )

        if on_prepared is not None:
            on_prepared(prepared)

        if before_commit is not None:
            before_commit()

        commit_identifier = request_id()
        commit_wire = encode_request(
            session=session,
            request=commit_identifier,
            verb="COMMIT_EXEC",
            body={
                "prepare_request": prepare_identifier,
                "manifest_sha256": manifest_sha256,
            },
        )
        ledger = HostIntentLedger(ledger_path or ledger_root())
        try:
            intent = ledger.arm(
                session=session,
                request=commit_identifier,
                manifest_sha256=manifest_sha256,
                target=bundle,
            )
            try:
                committed = serial.exchange(commit_wire, 12)
            except TransportLost as error:
                raise TransportLost(
                    f"{error}; commit intent remains UNKNOWN "
                    f"session={session} request={commit_identifier}"
                ) from error
            assert_correlated(
                committed,
                session=session,
                request=commit_identifier,
                verb="COMMIT_EXEC",
            )
            if committed.result != "CLAIMED":
                if (
                    committed.state in {"IDLE", "PREPARED"}
                    and committed.execution_started == "NO"
                ):
                    intent = ledger.resolve(
                        session=session,
                        request=commit_identifier,
                        outcome="RECOVERY_REJECTED",
                    )
                fail(
                    "recovery did not claim execution "
                    f"result={committed.result} state={committed.state}"
                )
            if (
                committed.commit_request != commit_identifier
                or committed.commit_fingerprint
                != hashlib.sha256(commit_wire).hexdigest()
                or committed.prepare_request != prepare_identifier
                or committed.manifest_sha256 != manifest_sha256
                or committed.execution_started != "NO"
                or committed.watchdog != "ARMED"
            ):
                fail("recovery returned an inconsistent CLAIMED response")
            if on_committed is not None:
                on_committed(committed)
            if require_post_claim_observation:
                post_claim = observe_post_claim(serial, session, committed)
                if post_claim is not None:
                    if on_post_claim is not None:
                        on_post_claim(post_claim)
                    fail(
                        "claimed execution returned to recovery "
                        f"state={post_claim.state} "
                        f"execution_started={post_claim.execution_started} "
                        f"last_error={post_claim.last_error}"
                    )
            return prepared, committed, intent
        finally:
            ledger.close()
    finally:
        if serial is not None:
            serial.close()


def show_response(response: Response) -> None:
    print(
        json.dumps(asdict(response), sort_keys=True, separators=(",", ":")),
        flush=True,
    )


def expected_postmortem_lineage_sha256(
    expected_candidate: str,
    expected_boot_id: str,
) -> str:
    if (
        not CANDIDATE_ID.fullmatch(expected_candidate)
        or expected_candidate == "none"
        or ".." in expected_candidate
    ):
        fail("invalid expected postmortem candidate")
    if not BOOT_ID.fullmatch(expected_boot_id):
        fail("invalid expected postmortem boot ID")
    marker = (
        f"{TARGET_LINEAGE_PREFIX}{expected_candidate} "
        f"boot_id={expected_boot_id}"
    ).encode("ascii")
    return hashlib.sha256(marker).hexdigest()


def correlate_postmortem_lineage(
    response: Response,
    expected_candidate: str,
    expected_boot_id: str,
) -> PostmortemLineageCorrelation:
    expected_digest = expected_postmortem_lineage_sha256(
        expected_candidate, expected_boot_id
    )
    if response.postmortem_state == "UNAVAILABLE":
        classification = "UNAVAILABLE"
    elif response.postmortem_state == "EMPTY":
        classification = "NO_RECORDS"
    elif response.postmortem_lineage_state == "NONE":
        classification = "NO_MARKER"
    elif response.postmortem_lineage_state == "AMBIGUOUS":
        classification = "AMBIGUOUS"
    elif response.postmortem_lineage_sha256 != expected_digest:
        classification = "DIFFERENT_MARKER"
    elif response.postmortem_lineage_state == "UNIQUE":
        classification = "MATCH"
    else:
        classification = "MATCH_REPEATED"
    return PostmortemLineageCorrelation(
        classification=classification,
        recovery_session=response.session,
        status_request=response.request,
        postmortem_state=response.postmortem_state,
        postmortem_records=response.postmortem_records,
        postmortem_bytes=response.postmortem_bytes,
        postmortem_sha256=response.postmortem_sha256,
        expected_candidate=expected_candidate,
        expected_boot_id=expected_boot_id,
        expected_lineage_sha256=expected_digest,
        observed_lineage_matches=response.postmortem_lineage_matches,
        observed_lineage_sha256=response.postmortem_lineage_sha256,
    )


def read_recovery_status() -> tuple[Response, Response]:
    ensure_host_ready()
    serial, session, hello_response = connect()
    try:
        identifier = request_id()
        status = serial.exchange(
            encode_request(
                session=session,
                request=identifier,
                verb="STATUS",
            ),
            8,
        )
        assert_correlated(
            status,
            session=session,
            request=identifier,
            verb="STATUS",
        )
        if status.result != "OK":
            fail(f"recovery STATUS failed: {status.result}")
        return hello_response, status
    finally:
        serial.close()


def show_intent(intent: object) -> None:
    print(
        json.dumps(asdict(intent), sort_keys=True, separators=(",", ":")),
        flush=True,
    )


def ensure_host_ready() -> None:
    if os.uname().sysname != "Linux":
        fail("stable recovery control requires Linux")
    for command in ("systemctl", "udevadm"):
        if shutil.which(command) is None:
            fail(f"missing host command: {command}")
    if subprocess.run(
        ["systemctl", "is-active", "--quiet", "ModemManager.service"],
        check=False,
    ).returncode == 0:
        fail("stop ModemManager before using the recovery ACM")


def main(arguments: list[str]) -> int:
    if arguments == ["status"]:
        hello_response, status = read_recovery_status()
        show_response(hello_response)
        show_response(status)
        return 0

    if len(arguments) == 3 and arguments[0] == "postmortem-status":
        expected_candidate = arguments[1]
        expected_boot_id = arguments[2]
        # Validate caller-supplied lineage before any host/device discovery.
        expected_postmortem_lineage_sha256(
            expected_candidate, expected_boot_id
        )
        _, status = read_recovery_status()
        correlation = correlate_postmortem_lineage(
            status, expected_candidate, expected_boot_id
        )
        print(
            json.dumps(
                asdict(correlation), sort_keys=True, separators=(",", ":")
            ),
            flush=True,
        )
        return 0

    if len(arguments) == 2 and arguments[0] == "show":
        ledger = HostIntentLedger(ledger_root())
        try:
            intent = ledger.read(arguments[1])
        finally:
            ledger.close()
        if intent is None:
            fail("intent does not exist")
        show_intent(intent)
        return 0

    if len(arguments) == 4 and arguments[0] == "resolve":
        if os.environ.get("ALLOW_RECOVERY_INTENT_RESOLVE") != "1":
            fail(
                "set ALLOW_RECOVERY_INTENT_RESOLVE=1 only after "
                "out-of-band outcome evidence"
            )
        ledger = HostIntentLedger(ledger_root())
        try:
            intent = ledger.resolve(
                session=arguments[1],
                request=arguments[2],
                outcome=arguments[3],
            )
        finally:
            ledger.close()
        show_intent(intent)
        return 0

    if len(arguments) == 3 and arguments[0] == "prepare-commit":
        if os.environ.get("ALLOW_STABLE_RECOVERY_CONTROL") != "1":
            fail("set ALLOW_STABLE_RECOVERY_CONTROL=1 for one signed bundle")
        if os.environ.get("ALLOW_ATTENDED_KEXEC") != "1":
            fail("set ALLOW_ATTENDED_KEXEC=1 for the non-retryable commit")
        before_commit = None
        bundle = arguments[1]
        if bundle in NETWORK_ROOT_BUNDLES:
            if os.environ.get("ALLOW_NETWORK_ROOT_NFS_HANDOFF") != "1":
                fail(
                    "set ALLOW_NETWORK_ROOT_NFS_HANDOFF=1 to require "
                    "the exact NFS listener before COMMIT"
                )
            handoff_token = os.environ.get("ROG5_NFS_HANDOFF_TOKEN", "")
            if not valid_handoff_token(handoff_token):
                fail(
                    "set ROG5_NFS_HANDOFF_TOKEN to one fresh nonzero "
                    "256-bit hex token shared with the NFS server"
                )
            package_sha256 = ""
            if bundle in V3_NETWORK_ROOT_BUNDLES:
                if (
                    os.environ.get("ROG5_NFS_PROFILE")
                    != DEPLOYMENT_NFS_PROFILE
                ):
                    fail(
                        "set ROG5_NFS_PROFILE to the exact deployment "
                        "profile"
                    )
                package_sha256 = os.environ.get(
                    "ROG5_NFS_PACKAGE_SHA256",
                    "",
                )
                if (
                    not re.fullmatch(r"[0-9a-f]{64}", package_sha256)
                    or package_sha256 == "0" * 64
                ):
                    fail(
                        "set ROG5_NFS_PACKAGE_SHA256 to the exact admitted "
                        "package identity"
                    )
            before_commit = lambda: wait_for_network_root_nfs(
                handoff_token,
                bundle=bundle,
                package_sha256=package_sha256,
            )
        # Presence is deliberate: an unsupported bundle must fail closed even
        # when a caller mistakenly supplies an empty or false-looking guard.
        elif "ALLOW_NETWORK_ROOT_NFS_HANDOFF" in os.environ:
            fail("bundle does not permit network-root NFS handoff")
        ensure_host_ready()
        prepared, committed, intent = prepare_and_commit(
            bundle,
            arguments[2],
            before_commit=before_commit,
            on_prepared=show_response,
            on_committed=show_response,
            on_post_claim=show_response,
            require_post_claim_observation=True,
        )
        show_intent(intent)
        print(
            "PASS recovery accepted one commit; outcome remains UNKNOWN",
            flush=True,
        )
        return 0

    fail(
        "usage: stable-recovery-control.py status | "
        "postmortem-status CANDIDATE BOOT_ID | show SESSION | "
        "resolve SESSION REQUEST OUTCOME | "
        "prepare-commit BUNDLE MANIFEST_SHA256"
    )


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv[1:]))
    except (OSError, RuntimeError, subprocess.SubprocessError, ValueError) as error:
        print(f"FAIL {error}", file=sys.stderr)
        raise SystemExit(1)
