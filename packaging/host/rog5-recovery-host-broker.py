#!/usr/bin/env python3
"""Root socket broker for the fixed recovery-host operations."""

from __future__ import annotations

import os
from pathlib import Path
import re
import signal
import socket
import stat
import struct
import subprocess
import sys
import time


CONFIG = Path("/etc/rog5-recovery-host/control.conf")
CONTROLLER = Path("/usr/libexec/rog5-recovery-bundle-controller")
NETWORK_SERVER = Path(
    "/usr/libexec/rog5-recovery-host/serve-network-root.sh"
)
NFS_EXPORTS = Path("/var/lib/nfs/etab")
V1_ROOT = "/var/lib/rog5-headless-network-root-v1/root"
V3_ROOT = "/home/rog5-linux/exports/headless-ssh-network-root-v3/root"
STATUS_PREFIX = b"__ROG5_HOST_CONTROL_STATUS__="
SHA256 = re.compile(r"[0-9a-f]{64}")
IDENTITY = re.compile(r"[a-z0-9][a-z0-9._-]{0,63}")
USB_LOCATION = re.compile(r"[A-Za-z0-9._:/+-]{1,512}")
ANCHOR_PATH = re.compile(r"/[A-Za-z0-9._/+-]{1,399}")
BOOT_ID = re.compile(
    r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-"
    r"[0-9a-f]{4}-[0-9a-f]{12}"
)
CONTACT_START_MAX_AGE_SECONDS = 3600
ANCHOR_FIELDS = (
    "format",
    "host_boot_id",
    "created_unix",
    "usb_location",
    "recovery_vendor",
    "recovery_product_id",
    "recovery_product",
)


class BrokerError(RuntimeError):
    pass


def fail(message: str) -> "NoReturn":
    raise BrokerError(message)


def safe_regular(path: Path, uid: int, gid: int, mode: int) -> None:
    metadata = path.lstat()
    if (
        not stat.S_ISREG(metadata.st_mode)
        or metadata.st_uid != uid
        or metadata.st_gid != gid
        or stat.S_IMODE(metadata.st_mode) != mode
        or metadata.st_nlink != 1
    ):
        fail(f"unsafe fixed host-control file: {path}")


def safe_directory(path: Path, uid: int, gid: int, mode: int) -> None:
    metadata = path.lstat()
    if (
        not stat.S_ISDIR(metadata.st_mode)
        or metadata.st_uid != uid
        or metadata.st_gid != gid
        or stat.S_IMODE(metadata.st_mode) != mode
    ):
        fail(f"unsafe fixed host-control directory: {path}")


def sha256(path: Path) -> str:
    import hashlib

    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def configuration() -> tuple[int, Path, Path, bool, str, str]:
    offline = os.environ.get("ROG5_BROKER_OFFLINE_TEST") == "1"
    if offline:
        if os.geteuid() == 0:
            fail("offline broker test refuses root")
        config = Path(os.environ["ROG5_TEST_BROKER_CONFIG"])
        controller = Path(os.environ["ROG5_TEST_BROKER_CONTROLLER"])
        network = Path(os.environ["ROG5_TEST_BROKER_NETWORK_SERVER"])
        owner_uid = os.geteuid()
        owner_gid = os.getegid()
    else:
        if os.geteuid() != 0:
            fail("host-control broker must run as root")
        for name in (
            "ROG5_TEST_BROKER_CONFIG",
            "ROG5_TEST_BROKER_CONTROLLER",
            "ROG5_TEST_BROKER_NETWORK_SERVER",
            "ROG5_TEST_BROKER_NFS_EXPORTS",
        ):
            if name in os.environ:
                fail("test path override is forbidden")
        config = CONFIG
        controller = CONTROLLER
        network = NETWORK_SERVER
        owner_uid = 0
        owner_gid = 0
        for directory in (
            Path("/"),
            Path("/usr"),
            Path("/usr/libexec"),
            network.parent,
            Path("/etc"),
            config.parent,
        ):
            safe_directory(directory, 0, 0, 0o755)
    safe_regular(config, owner_uid, owner_gid, 0o444)
    safe_regular(controller, owner_uid, owner_gid, 0o555)
    safe_regular(network, owner_uid, owner_gid, 0o555)
    lines = config.read_text(encoding="ascii").splitlines()
    if len(lines) != 3:
        fail("host-control configuration field count changed")
    values: dict[str, str] = {}
    for line in lines:
        if line.count("=") != 1:
            fail("host-control configuration is malformed")
        key, value = line.split("=", 1)
        if key in values:
            fail("host-control configuration has a duplicate field")
        values[key] = value
    if tuple(values) != (
        "operator_uid",
        "bundle_controller_sha256",
        "network_server_sha256",
    ):
        fail("host-control configuration fields changed")
    if not values["operator_uid"].isascii() or not values["operator_uid"].isdecimal():
        fail("host-control operator UID is malformed")
    operator_uid = int(values["operator_uid"])
    if operator_uid <= 0:
        fail("host-control operator UID is unsafe")
    for key in (
        "bundle_controller_sha256",
        "network_server_sha256",
    ):
        expected = values[key]
        if not SHA256.fullmatch(expected) or expected == "0" * 64:
            fail("host-control executable hash is malformed")
    return (
        operator_uid,
        controller,
        network,
        offline,
        values["bundle_controller_sha256"],
        values["network_server_sha256"],
    )


def verify_executable_hashes(
    controller: Path,
    network: Path,
    controller_hash: str,
    network_hash: str,
) -> None:
    for path, expected in (
        (controller, controller_hash),
        (network, network_hash),
    ):
        if sha256(path) != expected:
            fail(f"fixed host-control executable changed: {path}")


def inspect_network_exports(path: Path, uid: int, gid: int) -> None:
    """Prove that the fixed NFS export table is exact, safe, and empty."""
    flags = os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW
    try:
        descriptor = os.open(path, flags)
    except OSError as error:
        raise BrokerError("host NFS export table cannot be opened") from error
    try:
        opened = os.fstat(descriptor)
        if opened.st_size > 1024 * 1024:
            fail("host NFS export table size is unsafe")
        chunks: list[bytes] = []
        remaining = opened.st_size + 1
        while remaining:
            chunk = os.read(descriptor, remaining)
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        payload = b"".join(chunks)
        after = os.fstat(descriptor)
        named = path.lstat()
    except OSError as error:
        raise BrokerError("host NFS export table cannot be inspected") from error
    finally:
        os.close(descriptor)

    def identity(value: os.stat_result) -> tuple[int, ...]:
        return (
            value.st_dev,
            value.st_ino,
            value.st_uid,
            value.st_gid,
            stat.S_IFMT(value.st_mode),
            stat.S_IMODE(value.st_mode),
            value.st_nlink,
            value.st_size,
        )

    if (
        not stat.S_ISREG(opened.st_mode)
        or opened.st_uid != uid
        or opened.st_gid != gid
        or stat.S_IMODE(opened.st_mode) not in {0o600, 0o644}
        or opened.st_nlink != 1
        or len(payload) != opened.st_size
        or identity(after) != identity(opened)
        or identity(named) != identity(opened)
    ):
        fail("host NFS export table metadata or identity is unsafe")
    if payload:
        fail("host retains an NFS export")


def read_request(channel: socket.socket) -> list[str]:
    channel.settimeout(5)
    payload = b""
    while True:
        chunk = channel.recv(513 - len(payload))
        if not chunk:
            break
        payload += chunk
        if len(payload) > 512:
            fail("host-control request exceeds 512 bytes")
    if payload.count(b"\n") != 1 or not payload.endswith(b"\n"):
        fail("host-control request must be one newline-terminated record")
    try:
        line = payload[:-1].decode("ascii")
    except UnicodeDecodeError as error:
        raise BrokerError("host-control request is not ASCII") from error
    if not line or line != line.strip() or "  " in line:
        fail("host-control request spacing is not canonical")
    channel.settimeout(None)
    return line.split(" ")


def recovery_anchor_location(
    value: str,
    operator_uid: int,
    operator_gid: int,
    *,
    offline: bool,
) -> str:
    if (
        not ANCHOR_PATH.fullmatch(value)
        or value.endswith("/")
        or "//" in value
        or ".." in value.split("/")
    ):
        fail("invalid recovery anchor path")
    path = Path(value)
    try:
        resolved = path.resolve(strict=True)
        parent = path.parent.lstat()
    except OSError as error:
        raise BrokerError("recovery anchor is unavailable") from error
    if resolved != path:
        fail("recovery anchor path is not canonical")
    if (
        not stat.S_ISDIR(parent.st_mode)
        or parent.st_uid != operator_uid
        or parent.st_gid != operator_gid
        or stat.S_IMODE(parent.st_mode) != 0o700
    ):
        fail("recovery anchor parent is unsafe")
    flags = os.O_RDONLY | os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(path, flags)
    except OSError as error:
        raise BrokerError("recovery anchor cannot be opened") from error
    try:
        opened = os.fstat(descriptor)
        if not 1 <= opened.st_size <= 4096:
            fail("recovery anchor size is unsafe")
        payload = os.read(descriptor, opened.st_size + 1)
        after = os.fstat(descriptor)
        named = path.lstat()
    except OSError as error:
        raise BrokerError("recovery anchor cannot be inspected") from error
    finally:
        os.close(descriptor)

    def stat_identity(value: os.stat_result) -> tuple[int, ...]:
        return (
            value.st_dev,
            value.st_ino,
            value.st_uid,
            value.st_gid,
            stat.S_IFMT(value.st_mode),
            value.st_size,
        )

    if (
        not stat.S_ISREG(opened.st_mode)
        or opened.st_uid != operator_uid
        or opened.st_gid != operator_gid
        or stat.S_IMODE(opened.st_mode) != 0o600
        or opened.st_nlink != 1
        or len(payload) != opened.st_size
        or stat_identity(after) != stat_identity(opened)
        or stat_identity(named) != stat_identity(opened)
    ):
        fail("recovery anchor metadata or identity is unsafe")
    if not payload.endswith(b"\n") or b"\r" in payload or b"\0" in payload:
        fail("recovery anchor encoding is not canonical")
    try:
        lines = payload.decode("ascii").splitlines()
    except UnicodeDecodeError as error:
        raise BrokerError("recovery anchor is not ASCII") from error
    if len(lines) != len(ANCHOR_FIELDS):
        fail("recovery anchor field count changed")
    values: dict[str, str] = {}
    for expected, line in zip(ANCHOR_FIELDS, lines, strict=True):
        name, separator, field = line.partition("=")
        if separator != "=" or name != expected or not field:
            fail("recovery anchor is not canonical")
        values[name] = field
    boot_id_path = (
        Path(os.environ["ROG5_TEST_BROKER_BOOT_ID"])
        if offline
        else Path("/proc/sys/kernel/random/boot_id")
    )
    try:
        boot_payload = boot_id_path.read_bytes()
    except OSError as error:
        raise BrokerError("host boot identity is unavailable") from error
    if boot_payload.count(b"\n") != 1 or not boot_payload.endswith(b"\n"):
        fail("host boot identity is not canonical")
    try:
        host_boot_id = boot_payload[:-1].decode("ascii")
    except UnicodeDecodeError as error:
        raise BrokerError("host boot identity is not ASCII") from error
    created = values["created_unix"]
    location = values["usb_location"]
    now = int(time.time())
    if (
        not BOOT_ID.fullmatch(host_boot_id)
        or values["format"] != "rog5-minimal-headless-usb-anchor-v1"
        or values["host_boot_id"] != host_boot_id
        or values["recovery_vendor"] != "1d6b"
        or values["recovery_product_id"] != "0104"
        or values["recovery_product"] != "ROG5 recovery"
        or not created.isascii()
        or not created.isdecimal()
        or created.startswith("0")
        or int(created) > now + 5
        or now - int(created) > CONTACT_START_MAX_AGE_SECONDS
        or not USB_LOCATION.fullmatch(location)
        or location.startswith("/")
        or location.endswith("/")
        or "//" in location
        or ".." in location.split("/")
    ):
        fail("recovery anchor identity or freshness is invalid")
    return location


def operator_output_directory(value: str, operator_uid: int, operator_gid: int) -> str:
    if (
        not ANCHOR_PATH.fullmatch(value)
        or value.endswith("/")
        or "//" in value
        or ".." in value.split("/")
    ):
        fail("invalid progress output directory")
    path = Path(value)
    try:
        resolved = path.resolve(strict=True)
        metadata = path.lstat()
    except OSError as error:
        raise BrokerError("progress output directory is unavailable") from error
    if resolved != path:
        fail("progress output directory path is not canonical")
    if (
        not stat.S_ISDIR(metadata.st_mode)
        or metadata.st_uid != operator_uid
        or metadata.st_gid != operator_gid
        or stat.S_IMODE(metadata.st_mode) != 0o700
    ):
        fail("progress output directory metadata is unsafe")
    for name in ("recovery-progress.capture", "recovery-progress.stop"):
        output = path / name
        if output.exists() or output.is_symlink():
            fail("progress output path already exists")
    return value


def command(
    arguments: list[str],
    controller: Path,
    network: Path,
    operator_uid: int,
    operator_gid: int,
    *,
    offline: bool,
) -> list[str]:
    action = arguments[0] if arguments else ""
    if action in {
        "bundle",
        "bundle-deferred",
        "bundle-progress-deferred",
    } and len(arguments) in {3, 4}:
        if (action == "bundle-progress-deferred") != (len(arguments) == 4):
            fail("invalid bundle progress request shape")
        bundle, digest = arguments[1:3]
        if action == "bundle-progress-deferred":
            bundle, digest, output = arguments[1:]
        if (
            not IDENTITY.fullmatch(bundle)
            or ".." in bundle
            or bundle == "none"
        ):
            fail("invalid bundle identity")
        if not SHA256.fullmatch(digest) or digest == "0" * 64:
            fail("invalid manifest SHA-256")
        if action == "bundle-deferred":
            return [str(controller), "serve-deferred", bundle, digest]
        if action == "bundle-progress-deferred":
            output = operator_output_directory(
                output,
                operator_uid,
                operator_gid,
            )
            return [
                str(controller),
                "serve-progress-deferred",
                bundle,
                digest,
                output,
            ]
        return [str(controller), bundle, digest]
    if action == "fallback-profile-restore" and len(arguments) == 3:
        anchor, timeout = arguments[1:]
        if (
            not timeout.isascii()
            or not timeout.isdecimal()
            or not 1 <= int(timeout) <= 900
        ):
            fail("invalid fallback-profile timeout")
        location = recovery_anchor_location(
            anchor,
            operator_uid,
            operator_gid,
            offline=offline,
        )
        return [str(controller), "restore-fallback", location, timeout]
    if action == "network-preflight-v1" and len(arguments) == 1:
        return [str(network), "preflight", V1_ROOT]
    if action == "network-preflight-v3" and len(arguments) == 2:
        digest = arguments[1]
        if not SHA256.fullmatch(digest) or digest == "0" * 64:
            fail("invalid deployment package SHA-256")
        return [str(network), "preflight", V3_ROOT, digest]
    if action == "network-serve-v1" and len(arguments) == 3:
        token, timeout = arguments[1:]
        if not SHA256.fullmatch(token) or token == "0" * 64:
            fail("invalid handoff token")
        if not timeout.isascii() or not timeout.isdecimal() or not 600 <= int(timeout) <= 900:
            fail("invalid server timeout")
        return [str(network), "serve", V1_ROOT, token, timeout]
    if action == "network-serve-v3" and len(arguments) == 4:
        digest, token, timeout = arguments[1:]
        if not SHA256.fullmatch(digest) or digest == "0" * 64:
            fail("invalid deployment package SHA-256")
        if not SHA256.fullmatch(token) or token == "0" * 64:
            fail("invalid handoff token")
        if not timeout.isascii() or not timeout.isdecimal() or not 600 <= int(timeout) <= 900:
            fail("invalid server timeout")
        return [str(network), "serve", V3_ROOT, digest, token, timeout]
    if action == "network-cancel" and len(arguments) == 2:
        token = arguments[1]
        if not SHA256.fullmatch(token) or token == "0" * 64:
            fail("invalid handoff token")
        return [str(network), "cancel", token]
    fail("unsupported host-control request")


def send(channel: socket.socket, payload: bytes) -> None:
    try:
        channel.sendall(payload)
    except BrokenPipeError as error:
        raise BrokerError("host-control client disconnected") from error


def execute(
    channel: socket.socket,
    argv: list[str],
    operator_uid: int,
    *,
    offline: bool,
) -> int:
    environment = {
        "HOME": "/root",
        "LANG": "C",
        "LC_ALL": "C",
        "PATH": "/usr/sbin:/usr/bin:/sbin:/bin",
        "PKEXEC_UID": str(operator_uid),
    }
    if offline:
        environment["MOCK_CALLS"] = os.environ["MOCK_CALLS"]
        environment["MOCK_EXIT_STATUS"] = os.environ.get(
            "MOCK_EXIT_STATUS", "0"
        )
        environment["MOCK_DELAY"] = os.environ.get("MOCK_DELAY", "0")
        environment["MOCK_COLLIDE"] = os.environ.get("MOCK_COLLIDE", "0")
        environment["MOCK_PARTIAL"] = os.environ.get("MOCK_PARTIAL", "0")
    managed_signals = {signal.SIGHUP, signal.SIGINT, signal.SIGTERM}
    original_mask = signal.pthread_sigmask(
        signal.SIG_BLOCK, managed_signals
    )
    child: subprocess.Popen[bytes] | None = None
    pending_signals: list[int] = []

    def forward(signum: int, _frame: object) -> None:
        if child is None:
            pending_signals.append(signum)
            return
        if child.poll() is not None:
            return
        try:
            os.killpg(child.pid, signum)
        except ProcessLookupError:
            pass

    previous = {
        signum: signal.signal(signum, forward)
        for signum in managed_signals
    }
    # A blocked signal mask is inherited across fork and exec. Restore the
    # caller's mask before spawning so the fixed controller, its watchdog,
    # and cleanup children can receive TERM. The handlers above retain any
    # signal arriving in the narrow pre-spawn window and forward it once the
    # new process group exists.
    signal.pthread_sigmask(signal.SIG_SETMASK, original_mask)
    try:
        child = subprocess.Popen(
            argv,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            env=environment,
            start_new_session=True,
        )
    except BaseException:
        signal.pthread_sigmask(signal.SIG_BLOCK, managed_signals)
        for signum, handler in previous.items():
            signal.signal(signum, handler)
        signal.pthread_sigmask(signal.SIG_SETMASK, original_mask)
        if pending_signals:
            return 128 + min(pending_signals[-1], 127)
        raise
    for signum in pending_signals:
        forward(signum, None)
    try:
        assert child.stdout is not None
        with child.stdout:
            while True:
                line = child.stdout.readline(1024 * 1024 + 1)
                if not line:
                    break
                if len(line) > 1024 * 1024:
                    fail("host-control child output line exceeds 1 MiB")
                if not line.endswith(b"\n"):
                    fail("host-control child output is not newline terminated")
                if line.startswith(STATUS_PREFIX):
                    fail("host-control child output collides with framing")
                send(channel, line)
        status = child.wait()
    except BaseException:
        if child.poll() is None:
            try:
                os.killpg(child.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
        try:
            child.wait(timeout=5)
        except subprocess.TimeoutExpired:
            if child.poll() is None:
                try:
                    os.killpg(child.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
            child.wait()
        raise
    finally:
        signal.pthread_sigmask(signal.SIG_BLOCK, managed_signals)
        for signum, handler in previous.items():
            signal.signal(signum, handler)
        signal.pthread_sigmask(signal.SIG_SETMASK, original_mask)
    if status < 0:
        status = 128 + min(-status, 127)
    return min(status, 255)


def run() -> int:
    channel = socket.socket(fileno=os.dup(0))
    authorized = False
    try:
        (
            operator_uid,
            controller,
            network,
            offline,
            controller_hash,
            network_hash,
        ) = configuration()
        peer_pid, peer_uid, peer_gid = struct.unpack(
            "3i", channel.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, 12)
        )
        if peer_pid <= 0 or peer_uid != operator_uid:
            try:
                channel.shutdown(socket.SHUT_RD)
            except OSError:
                pass
            fail("host-control socket peer is not the configured operator")
        authorized = True
        arguments = read_request(channel)
        verify_executable_hashes(
            controller,
            network,
            controller_hash,
            network_hash,
        )
        if arguments == ["network-export-state"]:
            if offline:
                exports_value = os.environ.get(
                    "ROG5_TEST_BROKER_NFS_EXPORTS", ""
                )
                if not exports_value:
                    fail("offline host NFS export table path is absent")
                exports = Path(exports_value)
            else:
                exports = NFS_EXPORTS
            inspect_network_exports(
                exports,
                operator_uid if offline else 0,
                peer_gid if offline else 0,
            )
            send(channel, b"PASS host NFS export table is empty\n")
            status = 0
        else:
            argv = command(
                arguments,
                controller,
                network,
                operator_uid,
                peer_gid,
                offline=offline,
            )
            status = execute(channel, argv, operator_uid, offline=offline)
        send(channel, STATUS_PREFIX + str(status).encode("ascii") + b"\n")
        return 0
    except (BrokerError, KeyError, OSError, UnicodeError) as error:
        if authorized:
            try:
                send(
                    channel,
                    f"FAIL {error}\n".encode("utf-8", "replace"),
                )
                send(channel, STATUS_PREFIX + b"1\n")
            except (BrokerError, OSError):
                pass
        return 1
    finally:
        channel.close()


def main() -> int:
    try:
        return run()
    except (BrokerError, OSError) as error:
        print(f"FAIL {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
