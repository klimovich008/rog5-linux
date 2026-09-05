#!/usr/bin/env python3
"""Native integration tests for the fixed recovery bundle transport.

The suite compiles ``rog5-bundle-fetch.c`` with ``ROG5_FETCH_TESTING`` unless
``ROG5_FETCH_TEST_BINARY`` names a prebuilt helper.  A non-native binary may
be supplied with ``ROG5_FETCH_TEST_RUNNER``.

The testing build is expected to accept this CLI:

    rog5-bundle-fetch-test \
        --bundle-root ROOT \
        --server-ip 127.0.0.1 \
        --source-ip 127.0.0.1 \
        --port PORT \
        --timeout-ms MILLISECONDS \
        --connect-timeout-ms MILLISECONDS \
        --worker-uid UID \
        --worker-gid GID \
        --skip-device-bind \
        [--skip-seccomp] \
        [--probe-forbidden-syscall] \
        [--fail-write-artifact NAME] \
        BUNDLE MANIFEST_SHA256

All endpoint, path, timeout, identity, seccomp, and probe overrides must be
compiled out of the production helper. QEMU user-mode runs use
``--skip-seccomp`` because a guest BPF filter cannot safely filter the
emulator's host-architecture syscall stream; the native suite exercises the
real filter.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import os
from pathlib import Path
import re
import shlex
import shutil
import signal
import socket
import struct
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest import mock
from typing import Callable, Iterable


REPO = Path(__file__).resolve().parents[2]
SOURCE = REPO / "tools/recovery_control/rog5-bundle-fetch.c"
sys.path.insert(0, str(REPO))

from tools.recovery_control import host_bundle_server as HOST_SERVER  # noqa: E402

BUNDLE = "arch-test-v1"
OTHER_BUNDLE = "debian-test-v1"
CONFLICT_EXIT = 42
HEADER_MAX = 1024
MANIFEST_MAX = 4096
KERNEL_MAX = 128 * 1024 * 1024
DTB_MAX = 2 * 1024 * 1024
INITRAMFS_MAX = 256 * 1024 * 1024
FILES = (
    "manifest",
    "manifest.sig",
    "Image",
    "board.dtb",
    "initramfs.cpio.gz",
)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def frame(payload: bytes) -> bytes:
    return struct.pack(">I", len(payload)) + payload


def render_fields(fields: Iterable[tuple[str, str]]) -> bytes:
    return "".join(f"{name}={value}\n" for name, value in fields).encode(
        "ascii"
    )


def wait_until(
    predicate: Callable[[], bool],
    *,
    timeout: float = 3.0,
    interval: float = 0.01,
) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(interval)
    return predicate()


def proc_children(pid: int) -> list[int]:
    path = Path(f"/proc/{pid}/task/{pid}/children")
    try:
        return [int(value) for value in path.read_text().split()]
    except (FileNotFoundError, ProcessLookupError):
        return []


def proc_status(pid: int) -> dict[str, str]:
    status: dict[str, str] = {}
    for line in Path(f"/proc/{pid}/status").read_text(
        encoding="ascii"
    ).splitlines():
        if ":" in line:
            name, value = line.split(":", 1)
            status[name] = value.strip()
    return status


def process_gone_or_zombie(pid: int) -> bool:
    try:
        return proc_status(pid).get("State", "").startswith("Z")
    except (FileNotFoundError, ProcessLookupError):
        return True


@dataclass(frozen=True)
class BundlePayload:
    bundle: str
    manifest: bytes
    signature: bytes
    kernel: bytes
    dtb: bytes
    initramfs: bytes

    @classmethod
    def create(
        cls,
        bundle: str = BUNDLE,
        *,
        salt: int = 0,
    ) -> "BundlePayload":
        kernel = bytes((index * 17 + 3 + salt) & 0xFF for index in range(64))
        dtb = bytes((index * 11 + 5 + salt) & 0xFF for index in range(40))
        initramfs = bytes(
            (index * 7 + 9 + salt) & 0xFF for index in range(73)
        )
        signature = bytes(
            (index * 13 + 1 + salt) & 0xFF for index in range(64)
        )
        manifest = render_fields(
            cls.manifest_fields(
                bundle,
                kernel=kernel,
                dtb=dtb,
                initramfs=initramfs,
            )
        )
        return cls(
            bundle=bundle,
            manifest=manifest,
            signature=signature,
            kernel=kernel,
            dtb=dtb,
            initramfs=initramfs,
        )

    @staticmethod
    def manifest_fields(
        bundle: str,
        *,
        kernel: bytes,
        dtb: bytes,
        initramfs: bytes,
    ) -> list[tuple[str, str]]:
        return [
            ("format", "rog5-recovery-bundle-v2"),
            ("bundle", bundle),
            ("profile", "network-root-v1"),
            ("kernel_size", str(len(kernel))),
            ("kernel_sha256", sha256(kernel)),
            ("dtb_size", str(len(dtb))),
            ("dtb_sha256", sha256(dtb)),
            ("initramfs_size", str(len(initramfs))),
            ("initramfs_sha256", sha256(initramfs)),
            ("target_id", "rog5-test"),
            ("target_release", "test-1"),
            ("rollback_timeout", "180"),
            ("target_timeout", "90"),
            ("a660_command_manifest_sha256", "a" * 64),
            ("root_generation", "arch-a"),
            ("root_tree_sha256", "b" * 64),
            ("root_seal_sha256", "c" * 64),
            ("root_tree_entries", "7"),
            ("root_subtree", "/"),
        ]

    @property
    def manifest_hash(self) -> str:
        return sha256(self.manifest)

    @property
    def bodies(self) -> tuple[bytes, ...]:
        return (
            self.manifest,
            self.signature,
            self.kernel,
            self.dtb,
            self.initramfs,
        )

    def response_fields(
        self,
        *,
        expected_hash: str | None = None,
    ) -> list[tuple[str, str]]:
        return [
            ("format", "rog5-fetch-response-v1"),
            ("bundle", self.bundle),
            (
                "manifest_sha256",
                self.manifest_hash
                if expected_hash is None
                else expected_hash,
            ),
            ("manifest_size", str(len(self.manifest))),
            ("signature_size", str(len(self.signature))),
            ("kernel_size", str(len(self.kernel))),
            ("dtb_size", str(len(self.dtb))),
            ("initramfs_size", str(len(self.initramfs))),
        ]

    def response_header(
        self,
        *,
        expected_hash: str | None = None,
    ) -> bytes:
        return render_fields(
            self.response_fields(expected_hash=expected_hash)
        )

    def artifact_map(self) -> dict[str, bytes]:
        return dict(zip(FILES, self.bodies, strict=True))


class RawFetchServer:
    """One-connection raw TCP server with exact request capture."""

    def __init__(
        self,
        handler: Callable[[socket.socket, "RawFetchServer"], None] | None,
    ):
        self.handler = handler
        self.listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.listener.bind(("127.0.0.1", 0))
        self.listener.listen(2)
        self.listener.settimeout(0.1)
        self.port = self.listener.getsockname()[1]
        self.accepted = threading.Event()
        self.request_ready = threading.Event()
        self.stop_requested = threading.Event()
        self.request_prefix: bytes | None = None
        self.request_payload: bytes | None = None
        self.request_frame: bytes | None = None
        self.error: BaseException | None = None
        self.thread = threading.Thread(
            target=self._run,
            name=f"rog5-fetch-server-{self.port}",
            daemon=True,
        )

    def __enter__(self) -> "RawFetchServer":
        self.thread.start()
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        self.stop_requested.set()
        self.listener.close()
        self.thread.join(timeout=3)
        if self.thread.is_alive() and exc is None:
            raise AssertionError("raw fetch server did not terminate")
        if self.error is not None and exc is None:
            raise self.error

    @staticmethod
    def _receive_exact(
        connection: socket.socket,
        length: int,
    ) -> bytes | None:
        output = bytearray()
        while len(output) < length:
            try:
                chunk = connection.recv(length - len(output))
            except socket.timeout:
                continue
            if not chunk:
                return None
            output.extend(chunk)
        return bytes(output)

    @staticmethod
    def _receive_request_end(connection: socket.socket) -> bytes:
        deadline = time.monotonic() + 2
        while True:
            try:
                return connection.recv(1)
            except socket.timeout:
                if time.monotonic() >= deadline:
                    raise TimeoutError(
                        "fetch helper did not close its canonical request"
                    )

    def _run(self) -> None:
        connection: socket.socket | None = None
        try:
            while not self.stop_requested.is_set():
                try:
                    connection, _ = self.listener.accept()
                    break
                except socket.timeout:
                    continue
                except OSError:
                    return
            if connection is None:
                return
            self.accepted.set()
            connection.settimeout(0.1)
            prefix = self._receive_exact(connection, 4)
            if prefix is None:
                return
            self.request_prefix = prefix
            request_length = struct.unpack(">I", prefix)[0]
            if request_length < 1 or request_length > 256:
                raise AssertionError(
                    f"helper emitted invalid request length {request_length}"
                )
            payload = self._receive_exact(connection, request_length)
            if payload is None:
                return
            self.request_payload = payload
            self.request_frame = prefix + payload
            request_end = self._receive_request_end(connection)
            if request_end:
                raise AssertionError(
                    "helper emitted bytes after its canonical request"
                )
            self.request_ready.set()
            if self.handler is not None:
                self.handler(connection, self)
        except (BrokenPipeError, ConnectionResetError):
            pass
        except OSError as error:
            if not self.stop_requested.is_set():
                self.error = error
        except BaseException as error:
            self.error = error
        finally:
            if connection is not None:
                connection.close()


def send_fragmented(
    connection: socket.socket,
    data: bytes,
    *,
    fragments: tuple[int, ...] = (1, 2, 7, 31, 4096),
) -> None:
    offset = 0
    index = 0
    while offset < len(data):
        length = fragments[index % len(fragments)]
        connection.sendall(data[offset : offset + length])
        offset += length
        index += 1


def reply_handler(
    payload: BundlePayload,
    *,
    header: bytes | None = None,
    bodies: tuple[bytes, ...] | None = None,
    raw_prefix: bytes | None = None,
    trailing: bytes = b"",
    fragments: tuple[int, ...] = (1, 2, 7, 31, 4096),
) -> Callable[[socket.socket, RawFetchServer], None]:
    selected_header = (
        payload.response_header() if header is None else header
    )
    selected_bodies = payload.bodies if bodies is None else bodies

    def handle(
        connection: socket.socket,
        server: RawFetchServer,
    ) -> None:
        del server
        prefix = (
            struct.pack(">I", len(selected_header))
            if raw_prefix is None
            else raw_prefix
        )
        send_fragmented(
            connection,
            prefix + selected_header + b"".join(selected_bodies) + trailing,
            fragments=fragments,
        )
        connection.shutdown(socket.SHUT_WR)

    return handle


class NativeRecoveryFetchTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.build = tempfile.TemporaryDirectory(prefix="rog5-fetch-build-")
        cls.build_path = Path(cls.build.name)
        cls.runner = shlex.split(
            os.environ.get("ROG5_FETCH_TEST_RUNNER", "")
        )
        override = os.environ.get("ROG5_FETCH_TEST_BINARY")
        cls.binary = (
            Path(override)
            if override is not None
            else cls.build_path / "rog5-bundle-fetch-test"
        )
        if override is None:
            if shutil.which("gcc") is None:
                raise RuntimeError("gcc is required")
            subprocess.run(
                [
                    "gcc",
                    "-std=c11",
                    "-O2",
                    "-fPIE",
                    "-pie",
                    "-fstack-protector-strong",
                    "-Wall",
                    "-Wextra",
                    "-Werror",
                    "-Wl,-z,relro,-z,now,-z,noexecstack,--build-id=none",
                    "-DROG5_FETCH_TESTING=1",
                    str(SOURCE),
                    "-o",
                    str(cls.binary),
                ],
                check=True,
                cwd=REPO,
            )
        elif not cls.binary.is_file():
            raise RuntimeError("ROG5_FETCH_TEST_BINARY is not a file")

    @classmethod
    def tearDownClass(cls) -> None:
        cls.build.cleanup()

    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(
            prefix="rog5-fetch-test-"
        )
        self.work = Path(self.temporary.name)
        self.payload = BundlePayload.create()
        self.processes: list[subprocess.Popen[bytes]] = []

    def tearDown(self) -> None:
        for process in self.processes:
            if process.poll() is None:
                process.kill()
                process.wait(timeout=2)
            if process.stdout is not None:
                process.stdout.close()
            if process.stderr is not None:
                process.stderr.close()
        self.temporary.cleanup()

    def new_root(self, label: str = "bundles") -> Path:
        safe = re.sub(r"[^a-zA-Z0-9_.-]", "-", label)
        root = self.work / safe
        root.mkdir(mode=0o700)
        return root

    @property
    def worker_uid(self) -> int:
        return 65534 if os.geteuid() == 0 else os.geteuid()

    @property
    def worker_gid(self) -> int:
        return 65534 if os.geteuid() == 0 else os.getegid()

    def command(
        self,
        root: Path,
        port: int,
        *,
        bundle: str | None = None,
        expected_hash: str | None = None,
        timeout_ms: int = 700,
        connect_timeout_ms: int | None = None,
        extra: Iterable[str] = (),
    ) -> list[str]:
        return [
            *self.runner,
            str(self.binary),
            "--bundle-root",
            str(root),
            "--server-ip",
            "127.0.0.1",
            "--source-ip",
            "127.0.0.1",
            "--port",
            str(port),
            "--timeout-ms",
            str(timeout_ms),
            *(
                (
                    "--connect-timeout-ms",
                    str(connect_timeout_ms),
                )
                if connect_timeout_ms is not None
                else ()
            ),
            "--worker-uid",
            str(self.worker_uid),
            "--worker-gid",
            str(self.worker_gid),
            "--skip-device-bind",
            *(("--skip-seccomp",) if self.runner else ()),
            *extra,
            self.payload.bundle if bundle is None else bundle,
            (
                self.payload.manifest_hash
                if expected_hash is None
                else expected_hash
            ),
        ]

    def start_helper(
        self,
        root: Path,
        port: int,
        **kwargs,
    ) -> subprocess.Popen[bytes]:
        process = subprocess.Popen(
            self.command(root, port, **kwargs),
            cwd=REPO,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        self.processes.append(process)
        return process

    def finish_helper(
        self,
        process: subprocess.Popen[bytes],
        *,
        timeout: float = 5,
    ) -> subprocess.CompletedProcess[bytes]:
        try:
            stdout, stderr = process.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            process.kill()
            stdout, stderr = process.communicate(timeout=2)
            self.fail(
                "fetch helper exceeded harness timeout\n"
                f"stdout={stdout.decode(errors='replace')}\n"
                f"stderr={stderr.decode(errors='replace')}"
            )
        return subprocess.CompletedProcess(
            process.args,
            process.returncode,
            stdout,
            stderr,
        )

    def invoke(
        self,
        root: Path,
        port: int,
        **kwargs,
    ) -> subprocess.CompletedProcess[bytes]:
        return self.finish_helper(
            self.start_helper(root, port, **kwargs)
        )

    def assert_success(
        self,
        result: subprocess.CompletedProcess[bytes],
    ) -> None:
        self.assertEqual(
            result.returncode,
            0,
            result.stderr.decode(errors="replace"),
        )

    def assert_rejected(
        self,
        result: subprocess.CompletedProcess[bytes],
    ) -> None:
        self.assertNotEqual(
            result.returncode,
            0,
            result.stdout.decode(errors="replace"),
        )

    def assert_root_empty(self, root: Path) -> None:
        self.assertEqual(
            list(root.iterdir()),
            [],
            f"incomplete fetch left state in {root}",
        )

    def assert_published(
        self,
        root: Path,
        payload: BundlePayload | None = None,
    ) -> Path:
        selected = self.payload if payload is None else payload
        final = root / selected.bundle
        self.assertTrue(final.is_dir())
        self.assertFalse(final.is_symlink())
        self.assertEqual(
            {entry.name for entry in final.iterdir()},
            set(FILES),
        )
        self.assertEqual(final.stat().st_mode & 0o7777, 0o500)
        self.assertEqual(final.stat().st_uid, os.geteuid())
        self.assertEqual(final.stat().st_gid, os.getegid())
        for name, expected in selected.artifact_map().items():
            path = final / name
            metadata = path.stat()
            self.assertTrue(path.is_file())
            self.assertFalse(path.is_symlink())
            self.assertEqual(metadata.st_nlink, 1)
            self.assertEqual(metadata.st_mode & 0o7777, 0o400)
            self.assertEqual(metadata.st_uid, os.geteuid())
            self.assertEqual(metadata.st_gid, os.getegid())
            self.assertEqual(path.read_bytes(), expected)
        return final

    def write_final(
        self,
        root: Path,
        payload: BundlePayload,
    ) -> Path:
        final = root / payload.bundle
        final.mkdir(mode=0o700)
        for name, data in payload.artifact_map().items():
            path = final / name
            path.write_bytes(data)
            path.chmod(0o400)
        final.chmod(0o500)
        return final

    def assert_response_rejected(
        self,
        *,
        label: str,
        payload: BundlePayload | None = None,
        expected_hash: str | None = None,
        expected_returncode: int | None = None,
        handler: Callable[[socket.socket, RawFetchServer], None] | None = None,
        timeout_ms: int = 500,
    ) -> None:
        selected = self.payload if payload is None else payload
        root = self.new_root(label)
        selected_handler = (
            reply_handler(
                selected,
                header=selected.response_header(
                    expected_hash=expected_hash
                ),
            )
            if handler is None
            else handler
        )
        with RawFetchServer(selected_handler) as server:
            result = self.invoke(
                root,
                server.port,
                bundle=selected.bundle,
                expected_hash=(
                    selected.manifest_hash
                    if expected_hash is None
                    else expected_hash
                ),
                timeout_ms=timeout_ms,
            )
        self.assert_rejected(result)
        if expected_returncode is not None:
            self.assertEqual(result.returncode, expected_returncode)
        self.assert_root_empty(root)

    def test_valid_fragmented_fetch_is_atomic_and_request_is_exact(
        self,
    ) -> None:
        root = self.new_root()
        body_blocked = threading.Event()
        release = threading.Event()
        wire = (
            frame(self.payload.response_header())
            + b"".join(self.payload.bodies)
        )

        def handle(
            connection: socket.socket,
            server: RawFetchServer,
        ) -> None:
            del server
            send_fragmented(connection, wire[:-1], fragments=(1, 3, 17))
            body_blocked.set()
            if not release.wait(timeout=3):
                raise AssertionError(
                    "atomic-publication test was not released"
                )
            connection.sendall(wire[-1:])
            connection.shutdown(socket.SHUT_WR)

        with RawFetchServer(handle) as server:
            process = self.start_helper(root, server.port)
            self.assertTrue(body_blocked.wait(timeout=3))
            self.assertFalse((root / self.payload.bundle).exists())
            entries = list(root.iterdir())
            self.assertEqual(len(entries), 1)
            self.assertTrue(
                entries[0].name.startswith(".incoming."),
                entries[0].name,
            )
            release.set()
            result = self.finish_helper(process)

        self.assert_success(result)
        expected_request = render_fields(
            [
                ("format", "rog5-fetch-request-v1"),
                ("bundle", self.payload.bundle),
                ("manifest_sha256", self.payload.manifest_hash),
            ]
        )
        self.assertEqual(server.request_payload, expected_request)
        self.assertEqual(server.request_frame, frame(expected_request))
        self.assert_published(root)

    def test_blackholed_connect_uses_its_shorter_deadline(self) -> None:
        root = self.new_root("blackholed-connect")
        listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
        listener.listen(1)
        blockers = [
            socket.create_connection(("127.0.0.1", port), timeout=1)
            for _attempt in range(2)
        ]
        started = time.monotonic()
        try:
            result = self.invoke(
                root,
                port,
                timeout_ms=2_000,
                connect_timeout_ms=300,
            )
        finally:
            for blocker in blockers:
                blocker.close()
            listener.close()
        elapsed = time.monotonic() - started
        self.assertEqual(result.returncode, 45, result.stderr)
        self.assertGreaterEqual(elapsed, 0.25)
        self.assertLess(elapsed, 1.0)
        self.assert_root_empty(root)

    def test_real_host_server_and_fetcher_transfer_generation4_scale(self):
        kernel = b"K" * 40_049_152
        dtb = b"D" * 102_870
        initramfs = b"I" * 6_010_870
        signature = b"S" * 64
        manifest = render_fields(
            BundlePayload.manifest_fields(
                self.payload.bundle,
                kernel=kernel,
                dtb=dtb,
                initramfs=initramfs,
            )
        )
        self.payload = BundlePayload(
            bundle=self.payload.bundle,
            manifest=manifest,
            signature=signature,
            kernel=kernel,
            dtb=dtb,
            initramfs=initramfs,
        )

        source_root = self.new_root("real-host-source")
        source_bundle = source_root / self.payload.bundle
        source_bundle.mkdir(mode=0o700)
        for name, payload in self.payload.artifact_map().items():
            path = source_bundle / name
            path.write_bytes(payload)
            path.chmod(0o400)
        source_bundle.chmod(0o500)
        source_descriptor = os.open(
            source_root,
            os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC,
        )
        prepared = HOST_SERVER.prepare_bundle(
            source_descriptor,
            self.payload.bundle,
            self.payload.manifest_hash,
            os.geteuid(),
        )
        listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        listener.bind(("127.0.0.1", 0))
        listener.listen(1)
        port = listener.getsockname()[1]
        server_error: list[BaseException] = []

        def serve() -> None:
            try:
                connection, _peer = listener.accept()
                with connection:
                    HOST_SERVER.serve_connection(
                        connection,
                        prepared,
                        time.monotonic() + 15,
                    )
                    connection.shutdown(socket.SHUT_WR)
            except BaseException as error:
                server_error.append(error)
            finally:
                listener.close()

        thread = threading.Thread(target=serve, daemon=True)
        thread.start()
        destination = self.new_root("real-host-destination")
        try:
            result = self.invoke(
                destination,
                port,
                timeout_ms=15_000,
            )
            thread.join(timeout=20)
            self.assertFalse(thread.is_alive())
            self.assertEqual(server_error, [])
            self.assert_success(result)
            self.assert_published(destination)
        finally:
            listener.close()
            prepared.close()
            os.close(source_descriptor)

    def test_response_header_requires_exact_canonical_record(self) -> None:
        base = self.payload.response_fields()
        mutations: list[tuple[str, bytes, bytes | None]] = [
            ("missing-field", render_fields(base[:-1]), None),
            (
                "reordered",
                render_fields([base[1], base[0], *base[2:]]),
                None,
            ),
            (
                "duplicate",
                render_fields([base[0], base[0], *base[1:]]),
                None,
            ),
            (
                "unknown",
                render_fields([*base, ("extension", "no")]),
                None,
            ),
            (
                "wrong-format",
                render_fields(
                    [("format", "rog5-fetch-response-v2"), *base[1:]]
                ),
                None,
            ),
            ("blank-line", render_fields(base) + b"\n", None),
            ("crlf", render_fields(base).replace(b"\n", b"\r\n"), None),
            ("no-final-newline", render_fields(base).rstrip(b"\n"), None),
            (
                "embedded-space",
                render_fields(
                    [*base[:3], ("manifest_size", " 1"), *base[4:]]
                ),
                None,
            ),
            (
                "leading-zero",
                render_fields(
                    [
                        *base[:3],
                        ("manifest_size", f"0{len(self.payload.manifest)}"),
                        *base[4:],
                    ]
                ),
                None,
            ),
            (
                "plus-number",
                render_fields(
                    [*base[:3], ("manifest_size", "+1"), *base[4:]]
                ),
                None,
            ),
            (
                "nul-byte",
                render_fields(base).replace(
                    b"bundle=arch", b"bundle=arch\x00", 1
                ),
                None,
            ),
            ("zero-frame", b"", struct.pack(">I", 0)),
            (
                "oversize-frame",
                b"",
                struct.pack(">I", HEADER_MAX + 1),
            ),
        ]
        for index, (name, header, prefix) in enumerate(mutations):
            with self.subTest(case=name):
                handler = reply_handler(
                    self.payload,
                    header=header,
                    raw_prefix=prefix,
                )
                self.assert_response_rejected(
                    label=f"header-{index}-{name}",
                    handler=handler,
                )

    def test_response_rejects_bundle_and_hash_echo_mismatch(self) -> None:
        cases = (
            (
                "bundle",
                [
                    self.payload.response_fields()[0],
                    ("bundle", OTHER_BUNDLE),
                    *self.payload.response_fields()[2:],
                ],
            ),
            (
                "hash",
                [
                    *self.payload.response_fields()[:2],
                    ("manifest_sha256", "b" * 64),
                    *self.payload.response_fields()[3:],
                ],
            ),
        )
        for name, fields in cases:
            with self.subTest(case=name):
                self.assert_response_rejected(
                    label=f"echo-{name}",
                    handler=reply_handler(
                        self.payload,
                        header=render_fields(fields),
                    ),
                )

    def test_response_rejects_out_of_range_and_overflow_sizes(self) -> None:
        limits = {
            "manifest_size": ("0", str(MANIFEST_MAX + 1)),
            "signature_size": ("63", "65"),
            "kernel_size": ("63", str(KERNEL_MAX + 1)),
            "dtb_size": ("39", str(DTB_MAX + 1)),
            "initramfs_size": ("1", str(INITRAMFS_MAX + 1)),
        }
        for field, values in limits.items():
            for value in (*values, str(2**64), "184467440737095516150"):
                name = f"{field}-{value}"
                with self.subTest(case=name):
                    fields = [
                        (key, value if key == field else current)
                        for key, current in self.payload.response_fields()
                    ]
                    self.assert_response_rejected(
                        label=f"bounds-{field}-{len(value)}-{value[:4]}",
                        handler=reply_handler(
                            self.payload,
                            header=render_fields(fields),
                        ),
                    )

    def test_manifest_hash_and_canonical_manifest_are_enforced(self) -> None:
        wrong_hash = "b" * 64
        self.assert_response_rejected(
            label="manifest-hash",
            expected_hash=wrong_hash,
        )

        fields = BundlePayload.manifest_fields(
            self.payload.bundle,
            kernel=self.payload.kernel,
            dtb=self.payload.dtb,
            initramfs=self.payload.initramfs,
        )
        manifests = (
            ("missing", render_fields(fields[:-1])),
            (
                "reordered",
                render_fields([fields[1], fields[0], *fields[2:]]),
            ),
            (
                "duplicate",
                render_fields([fields[0], fields[0], *fields[1:]]),
            ),
            (
                "unknown",
                render_fields([*fields, ("extension", "no")]),
            ),
            (
                "wrong-bundle",
                render_fields(
                    [
                        fields[0],
                        ("bundle", OTHER_BUNDLE),
                        *fields[2:],
                    ]
                ),
            ),
            (
                "zero-artifact-hash",
                render_fields(
                    [
                        (
                            name,
                            "0" * 64
                            if name == "kernel_sha256"
                            else value,
                        )
                        for name, value in fields
                    ]
                ),
            ),
            (
                "zero-root-hash",
                render_fields(
                    [
                        (
                            name,
                            "0" * 64
                            if name == "root_tree_sha256"
                            else value,
                        )
                        for name, value in fields
                    ]
                ),
            ),
            (
                "wrong-root-generation",
                render_fields(
                    [
                        (
                            name,
                            "arch-b"
                            if name == "root_generation"
                            else value,
                        )
                        for name, value in fields
                    ]
                ),
            ),
            (
                "leading-dot-target",
                render_fields(
                    [
                        (
                            name,
                            ".target" if name == "target_id" else value,
                        )
                        for name, value in fields
                    ]
                ),
            ),
            (
                "dotdot-release",
                render_fields(
                    [
                        (
                            name,
                            "release..1"
                            if name == "target_release"
                            else value,
                        )
                        for name, value in fields
                    ]
                ),
            ),
            (
                "rollback-too-low",
                render_fields(
                    [
                        (
                            name,
                            "59" if name == "rollback_timeout" else value,
                        )
                        for name, value in fields
                    ]
                ),
            ),
            (
                "rollback-too-high",
                render_fields(
                    [
                        (
                            name,
                            "901" if name == "rollback_timeout" else value,
                        )
                        for name, value in fields
                    ]
                ),
            ),
            ("blank", render_fields(fields) + b"\n"),
            ("control", render_fields(fields).replace(b"\n", b"\t\n", 1)),
        )
        for index, (name, manifest) in enumerate(manifests):
            with self.subTest(case=name):
                mutated = BundlePayload(
                    bundle=self.payload.bundle,
                    manifest=manifest,
                    signature=self.payload.signature,
                    kernel=self.payload.kernel,
                    dtb=self.payload.dtb,
                    initramfs=self.payload.initramfs,
                )
                self.assert_response_rejected(
                    label=f"manifest-{index}-{name}",
                    payload=mutated,
                )

    def slow_local_publication(self):
        """Inject one bounded directory fsync stall in the native fixture."""
        shim = self.work / "slow-fsync.c"
        shim.write_text("""#define _GNU_SOURCE
#include <dlfcn.h>
#include <sys/stat.h>
#include <unistd.h>
int fsync(int fd) {
    static int delayed;
    int (*real_fsync)(int) = dlsym(RTLD_NEXT, "fsync");
    struct stat st;
    if (!delayed && fstat(fd, &st) == 0 && S_ISDIR(st.st_mode) &&
        (st.st_mode & 0777) == 0500) {
        delayed = 1;
        usleep(750000);
    }
    return real_fsync(fd);
}
""")
        library = self.work / "slow-fsync.so"
        subprocess.run(["gcc", "-shared", "-fPIC", str(shim), "-ldl",
                        "-o", str(library)], check=True)
        return mock.patch.dict(os.environ, {"LD_PRELOAD": str(library)})

    def test_diagnostic_profile_tolerates_slow_local_publication(self) -> None:
        if self.runner:
            self.skipTest("native filesystem-delay fixture")
        with self.slow_local_publication():
            self.test_diagnostic_profile_requires_network_root_trust_tuple()

    def test_concurrent_helper_tolerates_slow_local_publication(self) -> None:
        if self.runner:
            self.skipTest("native filesystem-delay fixture")
        with self.slow_local_publication():
            self.test_concurrent_helper_is_excluded_without_second_fetch()

    def test_diagnostic_profile_requires_network_root_trust_tuple(self) -> None:
        base = BundlePayload.manifest_fields(
            self.payload.bundle,
            kernel=self.payload.kernel,
            dtb=self.payload.dtb,
            initramfs=self.payload.initramfs,
        )
        diagnostic = BundlePayload(
            bundle=self.payload.bundle,
            manifest=render_fields(
                [
                    (
                        name,
                        "diagnostic-initramfs-v1"
                        if name == "profile"
                        else value,
                    )
                    for name, value in base
                ]
            ),
            signature=self.payload.signature,
            kernel=self.payload.kernel,
            dtb=self.payload.dtb,
            initramfs=self.payload.initramfs,
        )
        root = self.new_root("diagnostic-root")
        with RawFetchServer(reply_handler(diagnostic)) as server:
            result = self.invoke(
                root,
                server.port,
                bundle=diagnostic.bundle,
                expected_hash=diagnostic.manifest_hash,
                # This checks schema/publication, not a subsecond deadline.
                timeout_ms=3_000,
            )
        self.assert_success(result)
        self.assert_published(root, diagnostic)

        invalid_values = {
            "a660_command_manifest_sha256": "0" * 64,
            "root_generation": "none",
            "root_tree_sha256": "0" * 64,
            "root_seal_sha256": "0" * 64,
            "root_tree_entries": "0",
            "root_subtree": "none",
        }
        for invalid_field, invalid_value in invalid_values.items():
            with self.subTest(invalid_field=invalid_field):
                invalid = BundlePayload(
                    bundle=self.payload.bundle,
                    manifest=render_fields(
                        [
                            (
                                name,
                                "diagnostic-initramfs-v1"
                                if name == "profile"
                                else invalid_value
                                if name == invalid_field
                                else value,
                            )
                            for name, value in base
                        ]
                    ),
                    signature=self.payload.signature,
                    kernel=self.payload.kernel,
                    dtb=self.payload.dtb,
                    initramfs=self.payload.initramfs,
                )
                self.assert_response_rejected(
                    label=f"diagnostic-invalid-{invalid_field}",
                    payload=invalid,
                    expected_returncode=50,
                )

    def test_persistent_profile_requires_unset_root_and_rollback_floor(
        self,
    ) -> None:
        base = BundlePayload.manifest_fields(
            self.payload.bundle,
            kernel=self.payload.kernel,
            dtb=self.payload.dtb,
            initramfs=self.payload.initramfs,
        )
        persistent_values = {
            "profile": "persistent-root-ro-v1",
            "rollback_timeout": "300",
            "a660_command_manifest_sha256": "0" * 64,
            "root_generation": "none",
            "root_tree_sha256": "0" * 64,
            "root_seal_sha256": "0" * 64,
            "root_tree_entries": "0",
            "root_subtree": "none",
        }

        def persistent_payload(
            overrides: dict[str, str] | None = None,
        ) -> BundlePayload:
            values = {**persistent_values, **(overrides or {})}
            return BundlePayload(
                bundle=self.payload.bundle,
                manifest=render_fields(
                    [
                        (name, values.get(name, value))
                        for name, value in base
                    ]
                ),
                signature=self.payload.signature,
                kernel=self.payload.kernel,
                dtb=self.payload.dtb,
                initramfs=self.payload.initramfs,
            )

        persistent = persistent_payload()
        root = self.new_root("persistent-root")
        with RawFetchServer(reply_handler(persistent)) as server:
            result = self.invoke(
                root,
                server.port,
                bundle=persistent.bundle,
                expected_hash=persistent.manifest_hash,
            )
        self.assert_success(result)
        self.assert_published(root, persistent)

        network_values = dict(base)
        for invalid_field in (
            "a660_command_manifest_sha256",
            "root_generation",
            "root_tree_sha256",
            "root_seal_sha256",
            "root_tree_entries",
            "root_subtree",
        ):
            with self.subTest(invalid_field=invalid_field):
                self.assert_response_rejected(
                    label=f"persistent-carries-{invalid_field}",
                    payload=persistent_payload(
                        {invalid_field: network_values[invalid_field]}
                    ),
                    expected_returncode=50,
                )
        self.assert_response_rejected(
            label="persistent-rollback-below-floor",
            payload=persistent_payload({"rollback_timeout": "299"}),
            expected_returncode=50,
        )

    def test_stock_charging_profile_requires_unset_root_and_rollback_floor(
        self,
    ) -> None:
        base = BundlePayload.manifest_fields(
            self.payload.bundle,
            kernel=self.payload.kernel,
            dtb=self.payload.dtb,
            initramfs=self.payload.initramfs,
        )
        values = {
            "profile": "stock-charging-recovery-v1",
            "rollback_timeout": "900",
            "target_timeout": "600",
            "a660_command_manifest_sha256": "0" * 64,
            "root_generation": "none",
            "root_tree_sha256": "0" * 64,
            "root_seal_sha256": "0" * 64,
            "root_tree_entries": "0",
            "root_subtree": "none",
        }

        def stock_payload(overrides: dict[str, str] | None = None) -> BundlePayload:
            fields = {**values, **(overrides or {})}
            return BundlePayload(
                bundle=self.payload.bundle,
                manifest=render_fields(
                    [(name, fields.get(name, value)) for name, value in base]
                ),
                signature=self.payload.signature,
                kernel=self.payload.kernel,
                dtb=self.payload.dtb,
                initramfs=self.payload.initramfs,
            )

        stock = stock_payload()
        root = self.new_root("stock-charging-root")
        with RawFetchServer(reply_handler(stock)) as server:
            result = self.invoke(
                root,
                server.port,
                bundle=stock.bundle,
                expected_hash=stock.manifest_hash,
            )
        self.assert_success(result)
        self.assert_published(root, stock)
        self.assert_response_rejected(
            label="stock-charging-rollback-below-floor",
            payload=stock_payload({"rollback_timeout": "899"}),
            expected_returncode=50,
        )

    def test_manifest_timeout_boundaries_match_verifier_schema(self) -> None:
        base = BundlePayload.manifest_fields(
            self.payload.bundle,
            kernel=self.payload.kernel,
            dtb=self.payload.dtb,
            initramfs=self.payload.initramfs,
        )
        for rollback, target in (("60", "30"), ("900", "600")):
            with self.subTest(rollback=rollback, target=target):
                fields = [
                    (
                        name,
                        rollback
                        if name == "rollback_timeout"
                        else target
                        if name == "target_timeout"
                        else value,
                    )
                    for name, value in base
                ]
                payload = BundlePayload(
                    bundle=self.payload.bundle,
                    manifest=render_fields(fields),
                    signature=self.payload.signature,
                    kernel=self.payload.kernel,
                    dtb=self.payload.dtb,
                    initramfs=self.payload.initramfs,
                )
                root = self.new_root(f"time-{rollback}-{target}")
                with RawFetchServer(reply_handler(payload)) as server:
                    result = self.invoke(
                        root,
                        server.port,
                        expected_hash=payload.manifest_hash,
                    )
                self.assert_success(result)
                self.assert_published(root, payload)

    def test_header_sizes_must_equal_manifest_sizes(self) -> None:
        for field, deltas in (
            ("manifest_size", (-1, 1)),
            ("kernel_size", (1,)),
            ("dtb_size", (1,)),
            ("initramfs_size", (1,)),
        ):
            for delta in deltas:
                with self.subTest(field=field, delta=delta):
                    fields = [
                        (
                            name,
                            str(int(value) + delta)
                            if name == field
                            else value,
                        )
                        for name, value in self.payload.response_fields()
                    ]
                    self.assert_response_rejected(
                        label=f"manifest-size-{field}-{delta}",
                        handler=reply_handler(
                            self.payload,
                            header=render_fields(fields),
                        ),
                    )

    def test_root_metadata_policy_rejects_writable_root(self) -> None:
        root = self.new_root()
        root.chmod(0o777)
        with RawFetchServer(None) as server:
            result = self.invoke(root, server.port)
            self.assertFalse(server.accepted.is_set())
        self.assert_rejected(result)
        self.assert_root_empty(root)

    def test_publication_crash_points_are_contained(self) -> None:
        crash_points = (
            "after-worker",
            "after-parent-validation",
            "after-directory-lockdown",
            *(f"after-normalize-{name}" for name in FILES),
            "after-directory-sync",
            "after-final-validation",
            "before-rename",
            "after-rename",
            "after-root-sync",
        )
        published_points = {"after-rename", "after-root-sync"}
        for index, point in enumerate(crash_points):
            with self.subTest(point=point):
                root = self.new_root(f"crash-{index}-{point}")
                with RawFetchServer(reply_handler(self.payload)) as server:
                    crashed = self.invoke(
                        root,
                        server.port,
                        extra=("--crash-at", point),
                    )
                self.assertEqual(
                    crashed.returncode,
                    99,
                    crashed.stderr.decode(errors="replace"),
                )
                if point in published_points:
                    self.assert_published(root)
                    with RawFetchServer(None) as retry_server:
                        retry = self.invoke(root, retry_server.port)
                        self.assertFalse(retry_server.accepted.is_set())
                    self.assertEqual(retry.returncode, CONFLICT_EXIT)
                else:
                    self.assertFalse(
                        (root / self.payload.bundle).exists()
                    )
                    with RawFetchServer(
                        reply_handler(self.payload)
                    ) as retry_server:
                        retry = self.invoke(root, retry_server.port)
                    self.assert_success(retry)
                self.assert_published(root)

    def test_every_artifact_hash_is_checked(self) -> None:
        for body_index, name in enumerate(FILES):
            if name == "manifest.sig":
                continue
            with self.subTest(artifact=name):
                bodies = list(self.payload.bodies)
                damaged = bytearray(bodies[body_index])
                damaged[-1] ^= 0x80
                bodies[body_index] = bytes(damaged)
                self.assert_response_rejected(
                    label=f"hash-{name}",
                    handler=reply_handler(
                        self.payload,
                        bodies=tuple(bodies),
                    ),
                )

    def test_enospc_after_each_first_artifact_write_is_contained(
        self,
    ) -> None:
        for index, name in enumerate(FILES):
            with self.subTest(artifact=name):
                root = self.new_root(f"enospc-{index}-{name}")
                with RawFetchServer(
                    reply_handler(self.payload)
                ) as server:
                    result = self.invoke(
                        root,
                        server.port,
                        extra=("--fail-write-artifact", name),
                    )
                self.assert_rejected(result)
                self.assert_root_empty(root)

    def test_every_protocol_segment_rejects_truncation(self) -> None:
        header = self.payload.response_header()
        complete = frame(header) + b"".join(self.payload.bodies)
        offsets = [2, 4 + len(header) - 1]
        cursor = 4 + len(header)
        for body in self.payload.bodies:
            offsets.append(cursor + len(body) - 1)
            cursor += len(body)
        for index, cutoff in enumerate(offsets):
            with self.subTest(segment=index):
                root = self.new_root(f"truncated-{index}")

                def handle(
                    connection: socket.socket,
                    server: RawFetchServer,
                    *,
                    data: bytes = complete[:cutoff],
                ) -> None:
                    del server
                    connection.sendall(data)
                    connection.shutdown(socket.SHUT_WR)

                with RawFetchServer(handle) as server:
                    result = self.invoke(root, server.port)
                self.assert_rejected(result)
                self.assert_root_empty(root)

    def test_body_reordering_and_trailing_data_are_rejected(self) -> None:
        bodies = list(self.payload.bodies)
        bodies[2], bodies[3] = bodies[3], bodies[2]
        cases = (
            (
                "reordered",
                reply_handler(self.payload, bodies=tuple(bodies)),
            ),
            (
                "trailing-byte",
                reply_handler(self.payload, trailing=b"\x00"),
            ),
            (
                "second-frame",
                reply_handler(self.payload, trailing=frame(b"x")),
            ),
        )
        for name, handler in cases:
            with self.subTest(case=name):
                self.assert_response_rejected(
                    label=f"stream-{name}",
                    handler=handler,
                )

    def test_timeout_slowloris_and_reset_are_bounded(self) -> None:
        def stall(
            connection: socket.socket,
            server: RawFetchServer,
        ) -> None:
            del connection, server
            time.sleep(0.5)

        def slowloris(
            connection: socket.socket,
            server: RawFetchServer,
        ) -> None:
            del server
            connection.sendall(
                frame(self.payload.response_header())[:1]
            )
            time.sleep(0.5)

        def reset(
            connection: socket.socket,
            server: RawFetchServer,
        ) -> None:
            del server
            connection.setsockopt(
                socket.SOL_SOCKET,
                socket.SO_LINGER,
                struct.pack("ii", 1, 0),
            )

        for name, handler in (
            ("timeout", stall),
            ("slowloris", slowloris),
            ("reset", reset),
        ):
            with self.subTest(case=name):
                started = time.monotonic()
                self.assert_response_rejected(
                    label=f"transport-{name}",
                    handler=handler,
                    timeout_ms=150,
                )
                self.assertLess(time.monotonic() - started, 2.0)

    def test_existing_final_is_permanent_conflict_without_network(self) -> None:
        root = self.new_root()
        self.write_final(root, self.payload)
        with RawFetchServer(None) as server:
            result = self.invoke(root, server.port)
            time.sleep(0.05)
            self.assertFalse(server.accepted.is_set())
        self.assertEqual(result.returncode, CONFLICT_EXIT)
        self.assertIn(
            b"pre-existing final bundle is forbidden",
            result.stderr,
        )
        self.assert_published(root)

    def test_existing_same_id_different_hash_is_permanent_conflict(
        self,
    ) -> None:
        root = self.new_root()
        conflicting = BundlePayload.create(self.payload.bundle, salt=19)
        self.write_final(root, conflicting)
        with RawFetchServer(None) as server:
            result = self.invoke(root, server.port)
            self.assertFalse(server.accepted.is_set())
        self.assertEqual(result.returncode, CONFLICT_EXIT)
        self.assert_published(root, conflicting)

    def test_one_final_bundle_quota_refuses_another_bundle(self) -> None:
        root = self.new_root()
        existing = BundlePayload.create(OTHER_BUNDLE, salt=23)
        self.write_final(root, existing)
        with RawFetchServer(None) as server:
            result = self.invoke(root, server.port)
            self.assertFalse(server.accepted.is_set())
        self.assertEqual(result.returncode, CONFLICT_EXIT)
        self.assert_published(root, existing)
        self.assertFalse((root / self.payload.bundle).exists())

    def test_safe_stale_stage_is_cleaned_before_retry(self) -> None:
        root = self.new_root()
        stale = root / f".incoming.{self.payload.bundle}"
        stale.mkdir(mode=0o700)
        for name in FILES[:3]:
            path = stale / name
            path.write_bytes(b"partial")
            path.chmod(0o600)
        with RawFetchServer(reply_handler(self.payload)) as server:
            result = self.invoke(root, server.port)
        self.assert_success(result)
        self.assert_published(root)

    def test_unsafe_stale_inventory_fails_without_recursive_delete(
        self,
    ) -> None:
        mutations: tuple[tuple[str, Callable[[Path], Path]], ...] = (
            (
                "extra",
                lambda stage: (
                    stage / "do-not-delete"
                ),
            ),
            (
                "symlink",
                lambda stage: stage / "manifest",
            ),
            (
                "hardlink",
                lambda stage: stage / "manifest",
            ),
            (
                "subdirectory",
                lambda stage: stage / "manifest",
            ),
            (
                "file-mode",
                lambda stage: stage / "manifest",
            ),
            (
                "directory-mode",
                lambda stage: stage,
            ),
        )
        for index, (name, target_factory) in enumerate(mutations):
            with self.subTest(case=name):
                root = self.new_root(f"unsafe-stale-{index}-{name}")
                stage = root / f".incoming.{self.payload.bundle}"
                stage.mkdir(mode=0o700)
                target = target_factory(stage)
                if name == "extra":
                    target.write_text("sentinel", encoding="ascii")
                elif name == "symlink":
                    target.symlink_to(self.work / "outside")
                elif name == "hardlink":
                    outside = self.work / f"outside-{index}"
                    outside.write_bytes(b"sentinel")
                    os.link(outside, target)
                elif name == "subdirectory":
                    target.mkdir()
                elif name == "file-mode":
                    target.write_bytes(b"partial")
                    target.chmod(0o666)
                else:
                    stage.chmod(0o777)
                with RawFetchServer(None) as server:
                    result = self.invoke(root, server.port)
                    self.assertFalse(server.accepted.is_set())
                self.assert_rejected(result)
                self.assertTrue(os.path.lexists(target))
                self.assertFalse((root / self.payload.bundle).exists())

    def test_unknown_root_and_unrecognized_stage_fail_before_network(
        self,
    ) -> None:
        for index, name in enumerate(
            ("unknown-file", ".incoming.other-bundle", "unexpected-dir")
        ):
            with self.subTest(entry=name):
                root = self.new_root(f"unknown-root-{index}")
                entry = root / name
                if "." in name and not name.startswith("unknown"):
                    entry.mkdir()
                elif name.endswith("dir"):
                    entry.mkdir()
                else:
                    entry.write_text("sentinel", encoding="ascii")
                with RawFetchServer(None) as server:
                    result = self.invoke(root, server.port)
                    self.assertFalse(server.accepted.is_set())
                self.assert_rejected(result)
                self.assertTrue(entry.exists())

    def test_root_and_final_links_or_unsafe_metadata_are_rejected(
        self,
    ) -> None:
        real_root = self.new_root("real-root")
        linked_root = self.work / "linked-root"
        linked_root.symlink_to(real_root, target_is_directory=True)
        with RawFetchServer(None) as server:
            result = self.invoke(linked_root, server.port)
            self.assertFalse(server.accepted.is_set())
        self.assert_rejected(result)

        mutations = (
            "missing",
            "extra",
            "symlink",
            "hardlink",
            "file-mode",
            "dir-mode",
        )
        for index, mutation in enumerate(mutations):
            with self.subTest(case=mutation):
                root = self.new_root(f"unsafe-final-{index}")
                final = self.write_final(root, self.payload)
                final.chmod(0o700)
                if mutation == "missing":
                    (final / "Image").unlink()
                elif mutation == "extra":
                    (final / "extra").write_bytes(b"x")
                elif mutation == "symlink":
                    (final / "Image").unlink()
                    (final / "Image").symlink_to(self.work / "outside")
                elif mutation == "hardlink":
                    os.link(
                        final / "manifest",
                        self.work / f"manifest-link-{index}",
                    )
                elif mutation == "file-mode":
                    (final / "Image").chmod(0o600)
                elif mutation == "dir-mode":
                    pass
                final.chmod(0o700 if mutation == "dir-mode" else 0o500)
                with RawFetchServer(None) as server:
                    result = self.invoke(root, server.port)
                    self.assertFalse(server.accepted.is_set())
                self.assert_rejected(result)
                self.assertTrue(final.exists())

    def test_concurrent_helper_is_excluded_without_second_fetch(self) -> None:
        root = self.new_root()
        first_blocked = threading.Event()
        release = threading.Event()

        def hold_first(
            connection: socket.socket,
            server: RawFetchServer,
        ) -> None:
            del server
            first_blocked.set()
            if not release.wait(timeout=3):
                raise AssertionError("concurrency test was not released")
            send_fragmented(
                connection,
                frame(self.payload.response_header())
                + b"".join(self.payload.bodies),
            )
            connection.shutdown(socket.SHUT_WR)

        with RawFetchServer(hold_first) as first_server:
            # This success path waits for a competing process and fsyncs the
            # publication. Test lock exclusion, not a subsecond CI disk SLA.
            # Dedicated timeout cases and the rejected contender stay short.
            first = self.start_helper(root, first_server.port, timeout_ms=3_000)
            self.assertTrue(first_blocked.wait(timeout=3))
            with RawFetchServer(None) as second_server:
                second = self.invoke(
                    root,
                    second_server.port,
                    timeout_ms=250,
                )
                self.assert_rejected(second)
                self.assertFalse(second_server.accepted.is_set())
            release.set()
            first_result = self.finish_helper(first)
        self.assert_success(first_result)
        self.assert_published(root)

    def test_worker_identity_fds_capabilities_and_seccomp_are_bounded(
        self,
    ) -> None:
        if self.runner:
            self.skipTest("process inspection requires a native runner")
        root = self.new_root()
        request_seen = threading.Event()
        release = threading.Event()

        def hold(
            connection: socket.socket,
            server: RawFetchServer,
        ) -> None:
            del server
            request_seen.set()
            release.wait(timeout=3)
            connection.shutdown(socket.SHUT_WR)

        with RawFetchServer(hold) as server:
            parent = self.start_helper(root, server.port)
            self.assertTrue(request_seen.wait(timeout=3))
            self.assertTrue(
                wait_until(lambda: len(proc_children(parent.pid)) == 1)
            )
            worker = proc_children(parent.pid)[0]
            status = proc_status(worker)
            self.assertEqual(
                {int(value) for value in status["Uid"].split()},
                {self.worker_uid},
            )
            self.assertEqual(
                {int(value) for value in status["Gid"].split()},
                {self.worker_gid},
            )
            self.assertEqual(status.get("NoNewPrivs"), "1")
            self.assertEqual(status.get("Seccomp"), "2")
            self.assertEqual(int(status.get("CapEff", "1"), 16), 0)
            self.assertEqual(int(status.get("CapPrm", "1"), 16), 0)
            if os.geteuid() == 0:
                self.assertEqual(int(status.get("CapBnd", "1"), 16), 0)
            self.assertEqual(int(status.get("CapAmb", "1"), 16), 0)
            descriptors = {
                path.name for path in Path(f"/proc/{worker}/fd").iterdir()
            }
            self.assertEqual(descriptors, {"3", "4"})
            release.set()
            result = self.finish_helper(parent)
        self.assert_rejected(result)
        self.assert_root_empty(root)

    def test_forbidden_syscall_probe_is_killed_before_request_bytes(
        self,
    ) -> None:
        if self.runner:
            self.skipTest("qemu-user cannot emulate a guest seccomp filter")
        root = self.new_root()
        with RawFetchServer(None) as server:
            result = self.invoke(
                root,
                server.port,
                extra=("--probe-forbidden-syscall",),
            )
            self.assertTrue(server.accepted.wait(timeout=1))
            self.assertFalse(server.request_ready.is_set())
        self.assert_rejected(result)
        self.assert_root_empty(root)

    def test_parent_death_kills_worker_and_retry_cleans_stale_stage(
        self,
    ) -> None:
        if self.runner:
            self.skipTest("parent/worker inspection requires a native runner")
        root = self.new_root()
        request_seen = threading.Event()
        release = threading.Event()

        def hold(
            connection: socket.socket,
            server: RawFetchServer,
        ) -> None:
            del server
            request_seen.set()
            release.wait(timeout=3)

        with RawFetchServer(hold) as server:
            parent = self.start_helper(root, server.port, timeout_ms=2000)
            self.assertTrue(request_seen.wait(timeout=3))
            self.assertTrue(
                wait_until(lambda: len(proc_children(parent.pid)) == 1)
            )
            worker = proc_children(parent.pid)[0]
            parent.send_signal(signal.SIGKILL)
            parent.wait(timeout=2)
            self.assertTrue(
                wait_until(
                    lambda: process_gone_or_zombie(worker),
                    timeout=2,
                ),
                f"worker {worker} survived parent death",
            )
            try:
                os.waitpid(worker, os.WNOHANG)
            except ChildProcessError:
                pass
            release.set()
        self.assertFalse((root / self.payload.bundle).exists())

        with RawFetchServer(reply_handler(self.payload)) as retry_server:
            retry = self.invoke(root, retry_server.port, timeout_ms=2_000)
        self.assert_success(retry)
        self.assert_published(root)

    def test_parent_death_during_every_response_segment_is_contained(
        self,
    ) -> None:
        if self.runner:
            self.skipTest("parent/worker inspection requires a native runner")
        header = self.payload.response_header()
        wire = frame(header) + b"".join(self.payload.bodies)
        cutoffs = [2, 4 + len(header) // 2]
        cursor = 4 + len(header)
        for body in self.payload.bodies:
            cutoffs.append(cursor + max(1, len(body) // 2))
            cursor += len(body)

        for index, cutoff in enumerate(cutoffs):
            with self.subTest(segment=index):
                root = self.new_root(f"parent-death-segment-{index}")
                blocked = threading.Event()
                release = threading.Event()

                def hold(
                    connection: socket.socket,
                    server: RawFetchServer,
                    *,
                    data: bytes = wire[:cutoff],
                ) -> None:
                    del server
                    connection.sendall(data)
                    blocked.set()
                    release.wait(timeout=3)

                with RawFetchServer(hold) as server:
                    parent = self.start_helper(
                        root,
                        server.port,
                        timeout_ms=2000,
                    )
                    self.assertTrue(blocked.wait(timeout=3))
                    self.assertTrue(
                        wait_until(
                            lambda: len(proc_children(parent.pid)) == 1
                        )
                    )
                    worker = proc_children(parent.pid)[0]
                    parent.send_signal(signal.SIGKILL)
                    parent.wait(timeout=2)
                    self.assertTrue(
                        wait_until(
                            lambda: process_gone_or_zombie(worker),
                            timeout=2,
                        ),
                        f"worker {worker} survived parent death",
                    )
                    try:
                        os.waitpid(worker, os.WNOHANG)
                    except ChildProcessError:
                        pass
                    release.set()
                self.assertFalse((root / self.payload.bundle).exists())
                with RawFetchServer(
                    reply_handler(self.payload)
                ) as retry_server:
                    retry = self.invoke(
                        root,
                        retry_server.port,
                        timeout_ms=2_000,
                    )
                self.assert_success(retry)
                self.assert_published(root)

    def test_repeated_reset_failures_leave_no_process_or_fd_growth(
        self,
    ) -> None:
        if self.runner:
            self.skipTest("process inspection requires a native runner")
        root = self.new_root()
        baseline_fds = len(list(Path("/proc/self/fd").iterdir()))

        def reset(
            connection: socket.socket,
            server: RawFetchServer,
        ) -> None:
            del server
            connection.setsockopt(
                socket.SOL_SOCKET,
                socket.SO_LINGER,
                struct.pack("ii", 1, 0),
            )

        for _ in range(8):
            with RawFetchServer(reset) as server:
                result = self.invoke(root, server.port, timeout_ms=250)
            self.assert_rejected(result)
            self.assert_root_empty(root)
        self.assertEqual(proc_children(os.getpid()), [])
        self.assertLessEqual(
            len(list(Path("/proc/self/fd").iterdir())),
            baseline_fds + 1,
        )

    def test_invalid_cli_identities_fail_before_network(self) -> None:
        cases = (
            ("bundle-traversal", "../bad", self.payload.manifest_hash),
            ("bundle-none", "none", self.payload.manifest_hash),
            ("uppercase-hash", self.payload.bundle, "A" * 64),
            ("zero-hash", self.payload.bundle, "0" * 64),
            ("short-hash", self.payload.bundle, "a" * 63),
        )
        for index, (name, bundle, expected_hash) in enumerate(cases):
            with self.subTest(case=name):
                root = self.new_root(f"identity-{index}")
                with RawFetchServer(None) as server:
                    result = self.invoke(
                        root,
                        server.port,
                        bundle=bundle,
                        expected_hash=expected_hash,
                    )
                    self.assertFalse(server.accepted.is_set())
                self.assert_rejected(result)
                self.assert_root_empty(root)


if __name__ == "__main__":
    unittest.main(verbosity=2)
