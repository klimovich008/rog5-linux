"""Receive-only collector for advisory recovery PREPARE progress.

The production listener is intentionally separate from the ACM request/reply
channel and from the recovery bundle stream.  It accepts no application data
from the host and has no API that can authorize COMMIT_EXEC.  Tests use the
descriptor-oriented core with already-created sockets.
"""

from __future__ import annotations

from dataclasses import dataclass
import errno
import hashlib
import re
import select
import socket
import time
from typing import Callable

from .reference import (
    FrameParser,
    PREPARE_PROGRESS_PHASES,
    ProtocolViolation,
    ZERO_ID,
    decode_progress,
)


HOST_ADDRESS = "169.254.77.1"
DEVICE_ADDRESS = "169.254.77.2"
HOST_PORT = 8081
WIRE_MAX = 8192
READ_SIZE = 1024
HEX_ID = re.compile(r"[0-9a-f]{32}\Z")
HEX_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
BUNDLE_ID = re.compile(r"[a-z0-9][a-z0-9._-]{0,63}\Z")
INTERFACE = re.compile(r"[A-Za-z0-9_.:-]{1,15}\Z")


class CollectorRefusal(RuntimeError):
    """A stable fail-closed collector rejection."""

    def __init__(
        self,
        message: str,
        *,
        capture: ProgressCapture | None = None,
    ) -> None:
        super().__init__(message)
        self.capture = capture


def _validate_capture_identity(
    bundle: str,
    manifest_sha256: str,
    expected_session: str | None,
    expected_request: str | None,
) -> None:
    if (
        not isinstance(bundle, str)
        or not BUNDLE_ID.fullmatch(bundle)
        or ".." in bundle
        or bundle == "none"
        or not isinstance(manifest_sha256, str)
        or not HEX_SHA256.fullmatch(manifest_sha256)
        or manifest_sha256 == "0" * 64
    ):
        raise CollectorRefusal("invalid progress capture identity")
    for value in (expected_session, expected_request):
        if value is not None and (
            not isinstance(value, str)
            or not HEX_ID.fullmatch(value)
            or value == ZERO_ID
        ):
            raise CollectorRefusal("invalid progress correlation identity")


@dataclass(frozen=True)
class ProgressCapture:
    session: str
    request: str
    bundle: str
    manifest_sha256: str
    phases: tuple[str, ...]
    wire_bytes: int
    wire_sha256: str
    result: str
    truncated: bool
    reason: str

    @property
    def complete(self) -> bool:
        return self.result == "COMPLETE"

    def record(self) -> bytes:
        phases = ">".join(self.phases) if self.phases else "none"
        return (
            "format=rog5-recovery-progress-capture-v1\n"
            f"session={self.session}\n"
            f"request={self.request}\n"
            f"bundle={self.bundle}\n"
            f"manifest_sha256={self.manifest_sha256}\n"
            f"records={len(self.phases)}\n"
            f"phases={phases}\n"
            f"wire_bytes={self.wire_bytes}\n"
            f"wire_sha256={self.wire_sha256}\n"
            f"result={self.result}\n"
            f"truncated={'YES' if self.truncated else 'NO'}\n"
            f"reason={self.reason}\n"
            "authority=NONE\n"
        ).encode("ascii")


def _capture(
    *,
    session: str,
    request: str,
    bundle: str,
    manifest_sha256: str,
    phases: list[str],
    digest,
    wire_bytes: int,
    result: str,
    truncated: bool,
    reason: str,
) -> ProgressCapture:
    return ProgressCapture(
        session=session,
        request=request,
        bundle=bundle,
        manifest_sha256=manifest_sha256,
        phases=tuple(phases),
        wire_bytes=wire_bytes,
        wire_sha256=digest.hexdigest(),
        result=result,
        truncated=truncated,
        reason=reason,
    )


def collect_connection(
    connection: socket.socket,
    *,
    bundle: str,
    manifest_sha256: str,
    deadline: float,
    expected_session: str | None = None,
    expected_request: str | None = None,
    wire_max: int = WIRE_MAX,
    stop_requested: Callable[[], bool] | None = None,
    stop_poll_interval: float = 0.1,
) -> ProgressCapture:
    """Collect one bounded stream and return explicit complete/partial state."""

    if wire_max < 1 or wire_max > WIRE_MAX:
        raise ValueError("invalid progress wire cap")
    if stop_requested is not None and not 0 < stop_poll_interval <= 1:
        raise ValueError("invalid progress stop poll interval")
    _validate_capture_identity(
        bundle,
        manifest_sha256,
        expected_session,
        expected_request,
    )
    parser = FrameParser()
    digest = hashlib.sha256()
    wire_bytes = 0
    phases: list[str] = []
    session = expected_session or ZERO_ID
    request = expected_request or ZERO_ID
    connection.setblocking(False)

    def refuse(message: str, reason: str) -> CollectorRefusal:
        return CollectorRefusal(
            message,
            capture=_capture(
                session=session,
                request=request,
                bundle=bundle,
                manifest_sha256=manifest_sha256,
                phases=phases,
                digest=digest,
                wire_bytes=wire_bytes,
                result="PARTIAL",
                truncated=True,
                reason=reason,
            ),
        )

    while True:
        stopping = stop_requested is not None and stop_requested()
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return _capture(
                session=session,
                request=request,
                bundle=bundle,
                manifest_sha256=manifest_sha256,
                phases=phases,
                digest=digest,
                wire_bytes=wire_bytes,
                result="PARTIAL",
                truncated=True,
                reason="STOP_REQUESTED" if stopping else "TIMEOUT",
            )
        try:
            readable, _, _ = select.select(
                [connection],
                [],
                [],
                0
                if stopping
                else (
                    min(remaining, stop_poll_interval)
                    if stop_requested is not None
                    else remaining
                ),
            )
        except (OSError, ValueError) as error:
            raise refuse("progress poll failed", "POLL_ERROR") from error
        if not readable and stopping:
            return _capture(
                session=session,
                request=request,
                bundle=bundle,
                manifest_sha256=manifest_sha256,
                phases=phases,
                digest=digest,
                wire_bytes=wire_bytes,
                result="PARTIAL",
                truncated=True,
                reason="STOP_REQUESTED",
            )
        if not readable:
            continue
        allowance = wire_max - wire_bytes
        try:
            block = connection.recv(
                1 if allowance == 0 else min(READ_SIZE, allowance + 1)
            )
        except BlockingIOError:
            continue
        except OSError as error:
            raise refuse("progress read failed", "READ_ERROR") from error
        if block and allowance == 0:
            return _capture(
                session=session,
                request=request,
                bundle=bundle,
                manifest_sha256=manifest_sha256,
                phases=phases,
                digest=digest,
                wire_bytes=wire_bytes,
                result="PARTIAL",
                truncated=True,
                reason="WIRE_CAP",
            )
        if len(block) > allowance:
            digest.update(block[:allowance])
            wire_bytes += allowance
            return _capture(
                session=session,
                request=request,
                bundle=bundle,
                manifest_sha256=manifest_sha256,
                phases=phases,
                digest=digest,
                wire_bytes=wire_bytes,
                result="PARTIAL",
                truncated=True,
                reason="WIRE_CAP",
            )
        if not block:
            try:
                parser.finalize()
            except ProtocolViolation:
                framing_clean = False
                reason = "TORN_FRAME"
            else:
                framing_clean = True
                reason = "EOF"
            complete = (
                framing_clean
                and phases == list(PREPARE_PROGRESS_PHASES)
            )
            return _capture(
                session=session,
                request=request,
                bundle=bundle,
                manifest_sha256=manifest_sha256,
                phases=phases,
                digest=digest,
                wire_bytes=wire_bytes,
                result="COMPLETE" if complete else "PARTIAL",
                truncated=not complete,
                reason="CLEAN_EOF" if complete else reason,
            )

        digest.update(block)
        wire_bytes += len(block)
        try:
            payloads = parser.feed(block)
        except ProtocolViolation as error:
            raise refuse(
                "invalid progress framing", "INVALID_FRAMING"
            ) from error
        for payload in payloads:
            try:
                progress = decode_progress(payload)
            except ProtocolViolation as error:
                raise refuse(
                    "invalid progress record", "INVALID_RECORD"
                ) from error
            if session == ZERO_ID:
                session = progress.session
            if request == ZERO_ID:
                request = progress.request
            if (
                progress.session != session
                or progress.request != request
                or progress.bundle != bundle
                or progress.manifest_sha256 != manifest_sha256
                or progress.watchdog != "ARMED"
            ):
                raise refuse(
                    "progress identity mismatch", "IDENTITY_MISMATCH"
                )
            expected_sequence = len(phases) + 1
            if (
                expected_sequence > len(PREPARE_PROGRESS_PHASES)
                or progress.sequence != expected_sequence
                or progress.phase
                != PREPARE_PROGRESS_PHASES[expected_sequence - 1]
            ):
                raise refuse(
                    "noncontiguous progress stream", "ORDER_MISMATCH"
                )
            phases.append(progress.phase)


def collect_listener(
    listener: socket.socket,
    *,
    bundle: str,
    manifest_sha256: str,
    deadline: float,
    expected_peer: str = DEVICE_ADDRESS,
    expected_session: str | None = None,
    expected_request: str | None = None,
    admission_stop_requested: Callable[[], bool] | None = None,
    stream_stop_requested: Callable[[], bool] | None = None,
    stop_poll_interval: float = 0.1,
) -> ProgressCapture:
    """Accept exactly one valid device peer; a second stream is impossible."""

    _validate_capture_identity(
        bundle,
        manifest_sha256,
        expected_session,
        expected_request,
    )
    if (
        (admission_stop_requested is not None or stream_stop_requested is not None)
        and not 0 < stop_poll_interval <= 1
    ):
        raise ValueError("invalid progress stop poll interval")
    try:
        socket.inet_pton(socket.AF_INET, expected_peer)
    except (OSError, TypeError) as error:
        raise CollectorRefusal("invalid progress peer identity") from error
    listener.setblocking(False)
    while True:
        if (
            admission_stop_requested is not None
            and admission_stop_requested()
        ):
            raise CollectorRefusal("progress admission stopped")
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise CollectorRefusal("progress listener timed out")
        try:
            readable, _, _ = select.select(
                [listener],
                [],
                [],
                min(remaining, stop_poll_interval)
                if admission_stop_requested is not None
                else remaining,
            )
        except (OSError, ValueError) as error:
            raise CollectorRefusal("progress listener poll failed") from error
        if not readable:
            continue
        try:
            connection, peer = listener.accept()
        except BlockingIOError:
            continue
        except OSError as error:
            raise CollectorRefusal("progress listener accept failed") from error
        if (
            not isinstance(peer, tuple)
            or len(peer) < 2
            or peer[0] != expected_peer
        ):
            connection.close()
            continue
        listener.close()
        with connection:
            try:
                connection.shutdown(socket.SHUT_WR)
            except OSError as error:
                if error.errno != errno.ENOTCONN:
                    raise CollectorRefusal(
                        "progress receive-only shutdown failed"
                    ) from error
            return collect_connection(
                connection,
                bundle=bundle,
                manifest_sha256=manifest_sha256,
                deadline=deadline,
                expected_session=expected_session,
                expected_request=expected_request,
                stop_requested=stream_stop_requested,
                stop_poll_interval=stop_poll_interval,
            )


def open_fixed_listener(interface: str) -> socket.socket:
    """Open the production listener on one exact NCM interface."""

    if not isinstance(interface, str) or not INTERFACE.fullmatch(interface):
        raise CollectorRefusal("invalid progress interface")
    listener = socket.socket(
        socket.AF_INET,
        socket.SOCK_STREAM | socket.SOCK_CLOEXEC | socket.SOCK_NONBLOCK,
    )
    try:
        listener.setsockopt(
            socket.SOL_SOCKET,
            socket.SO_BINDTODEVICE,
            interface.encode("ascii") + b"\0",
        )
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        listener.bind((HOST_ADDRESS, HOST_PORT))
        bound_interface = listener.getsockopt(
            socket.SOL_SOCKET,
            socket.SO_BINDTODEVICE,
            16,
        ).rstrip(b"\0")
        if (
            bound_interface != interface.encode("ascii")
            or listener.getsockname()[:2] != (HOST_ADDRESS, HOST_PORT)
        ):
            raise CollectorRefusal("progress listener binding mismatch")
        listener.listen(1)
        return listener
    except BaseException:
        listener.close()
        raise
