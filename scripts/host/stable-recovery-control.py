#!/usr/bin/env python3
"""Drive one framed stable-recovery transaction with a durable host intent."""

from __future__ import annotations

from dataclasses import asdict
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
    Response,
    decode_response,
    encode_frame,
    encode_request,
)

SS = Path("/usr/bin/ss")
NETWORK_ROOT_BUNDLE = "headless-network-root-v1"
DEPLOYMENT_NETWORK_ROOT_BUNDLE = "headless-ssh-network-root-v3"
DEPLOYMENT_NFS_PROFILE = "headless-ssh-deployment-v3"
NFS_HANDOFF_MARKER = Path("/run/rog5-network-root-nfs-ready")
NFS_HANDOFF_ROOT = Path("/var/lib/rog5-headless-network-root-v1/root")
DEPLOYMENT_NFS_HANDOFF_ROOT = Path(
    "/var/lib/rog5-headless-ssh-network-root-v3/root"
)


class TransportLost(RuntimeError):
    """The ACM transaction ended without one correlated response."""


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


def find_recovery_acm() -> str:
    expected = {
        "ID_VENDOR_ID": "1d6b",
        "ID_MODEL_ID": "0104",
        "ID_MODEL": "ROG5_recovery",
    }
    matches: list[str] = []
    for device in glob.glob("/dev/ttyACM*"):
        try:
            properties = udev_properties(device)
            metadata = os.stat(device, follow_symlinks=False)
        except (OSError, subprocess.CalledProcessError):
            continue
        if stat.S_ISCHR(metadata.st_mode) and all(
            properties.get(key) == value for key, value in expected.items()
        ):
            matches.append(device)
    if len(matches) != 1:
        fail(f"expected exactly one ROG5 recovery ACM device, found {len(matches)}")
    if not os.access(matches[0], os.R_OK | os.W_OK):
        fail("recovery ACM is not readable and writable")
    return matches[0]


def recovery_acm_identity(path: str) -> tuple[str, int, str, str, str]:
    properties = udev_properties(path)
    metadata = os.stat(path, follow_symlinks=False)
    return (
        path,
        metadata.st_rdev,
        properties.get("DEVPATH", ""),
        properties.get("ID_PATH", ""),
        properties.get("ID_SERIAL", ""),
    )


def wait_for_stable_recovery_acm(
    *,
    settle_seconds: float = 2.0,
    timeout_seconds: float = 45.0,
    poll_seconds: float = 0.2,
) -> str:
    deadline = time.monotonic() + timeout_seconds
    candidate: tuple[str, int, str, str, str] | None = None
    stable_since = 0.0
    while time.monotonic() < deadline:
        now = time.monotonic()
        try:
            path = find_recovery_acm()
            identity = recovery_acm_identity(path)
        except (OSError, RuntimeError, subprocess.CalledProcessError):
            candidate = None
            stable_since = 0.0
        else:
            if identity != candidate:
                candidate = identity
                stable_since = now
            elif now - stable_since >= settle_seconds:
                final = find_recovery_acm()
                if recovery_acm_identity(final) == candidate:
                    return final
                candidate = None
                stable_since = 0.0
        time.sleep(poll_seconds)
    fail("recovery ACM identity did not remain stable")


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

    def exchange(self, payload: bytes, timeout_seconds: float) -> Response:
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
                if len(payloads) != 1:
                    fail("recovery returned multiple responses to one request")
                return decode_response(payloads[0])


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


def connect() -> tuple[RecoverySerial, str, Response]:
    serial = RecoverySerial(wait_for_stable_recovery_acm())
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
            bundle == DEPLOYMENT_NETWORK_ROOT_BUNDLE
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
    timeout_seconds: float = 45.0,
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
) -> tuple[Response, Response, object]:
    serial, session, _hello = connect()
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
    try:
        try:
            prepared = serial.exchange(prepare_wire, 75)
        except TransportLost:
            serial.close()
            serial, repeated_session, _hello = connect()
            if repeated_session != session:
                fail("recovery rebooted during PREPARE; refusing cross-session replay")
            prepared = serial.exchange(prepare_wire, 75)
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
                f"result={prepared.result} state={prepared.state}"
            )

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
            return prepared, committed, intent
        finally:
            ledger.close()
    finally:
        serial.close()


def show_response(response: Response) -> None:
    print(json.dumps(asdict(response), sort_keys=True, separators=(",", ":")))


def show_intent(intent: object) -> None:
    print(json.dumps(asdict(intent), sort_keys=True, separators=(",", ":")))


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
            show_response(hello_response)
            show_response(status)
            return 0
        finally:
            serial.close()

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
        if arguments[1] in {
            NETWORK_ROOT_BUNDLE,
            DEPLOYMENT_NETWORK_ROOT_BUNDLE,
        }:
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
            if arguments[1] == DEPLOYMENT_NETWORK_ROOT_BUNDLE:
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
                bundle=arguments[1],
                package_sha256=package_sha256,
            )
        ensure_host_ready()
        prepared, committed, intent = prepare_and_commit(
            arguments[1],
            arguments[2],
            before_commit=before_commit,
        )
        show_response(prepared)
        show_response(committed)
        show_intent(intent)
        print("PASS recovery accepted one commit; outcome remains UNKNOWN")
        return 0

    fail(
        "usage: stable-recovery-control.py status | show SESSION | "
        "resolve SESSION REQUEST OUTCOME | "
        "prepare-commit BUNDLE MANIFEST_SHA256"
    )


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv[1:]))
    except (OSError, RuntimeError, subprocess.SubprocessError, ValueError) as error:
        print(f"FAIL {error}", file=sys.stderr)
        raise SystemExit(1)
