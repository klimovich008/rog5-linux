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


CONFIG = Path("/etc/rog5-recovery-host/control.conf")
CONTROLLER = Path("/usr/libexec/rog5-recovery-bundle-controller")
NETWORK_SERVER = Path(
    "/usr/libexec/rog5-recovery-host/serve-network-root.sh"
)
V1_ROOT = "/var/lib/rog5-headless-network-root-v1/root"
V3_ROOT = "/home/rog5-linux/exports/headless-ssh-network-root-v3/root"
STATUS_PREFIX = b"__ROG5_HOST_CONTROL_STATUS__="
SHA256 = re.compile(r"[0-9a-f]{64}")
IDENTITY = re.compile(r"[a-z0-9][a-z0-9._-]{0,63}")


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


def command(arguments: list[str], controller: Path, network: Path) -> list[str]:
    action = arguments[0] if arguments else ""
    if action == "bundle" and len(arguments) == 3:
        bundle, digest = arguments[1:]
        if (
            not IDENTITY.fullmatch(bundle)
            or ".." in bundle
            or bundle == "none"
        ):
            fail("invalid bundle identity")
        if not SHA256.fullmatch(digest) or digest == "0" * 64:
            fail("invalid manifest SHA-256")
        return [str(controller), bundle, digest]
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
        signal.pthread_sigmask(signal.SIG_SETMASK, original_mask)
        raise

    def forward(signum: int, _frame: object) -> None:
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
    signal.pthread_sigmask(signal.SIG_SETMASK, original_mask)
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
        peer_pid, peer_uid, _peer_gid = struct.unpack(
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
        argv = command(arguments, controller, network)
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
