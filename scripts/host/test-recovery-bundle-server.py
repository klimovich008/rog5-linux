#!/usr/bin/env python3
"""Offline tests for the fixed read-only recovery bundle host server."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
import socket
import struct
import subprocess
import sys
import tempfile
import threading
import unittest


REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from tools.recovery_control.host_bundle_server import (  # noqa: E402
    ARTIFACTS,
    BUNDLE_ROOT,
    DEVICE_ADDRESS,
    HEADER_MAX,
    HOST_ADDRESS,
    HOST_PORT,
    MAX_REJECTED_PEERS,
    REQUEST_MAX,
    ServerRefusal,
    parse_record,
    prepare_bundle,
    run_preflight,
    serve_connection,
    serve_listener,
    validate_manifest,
)


BUNDLE = "arch-test-v1"
REQUEST_FIELDS = (
    "format",
    "bundle",
    "manifest_sha256",
)


class BundleFixture:
    def __init__(self):
        self.temporary = tempfile.TemporaryDirectory(
            prefix="rog5-host-bundle-"
        )
        self.root = Path(self.temporary.name)
        self.root.chmod(0o700)
        self.bundle = self.root / BUNDLE
        self.bundle.mkdir(mode=0o700)
        self.payloads = {
            "Image": b"K" * 64,
            "board.dtb": b"D" * 40,
            "initramfs.cpio.gz": b"\x1f\x8b",
        }
        manifest = (
            "format=rog5-recovery-bundle-v2\n"
            f"bundle={BUNDLE}\n"
            "profile=network-root-v1\n"
            f"kernel_size={len(self.payloads['Image'])}\n"
            f"kernel_sha256={self.digest('Image')}\n"
            f"dtb_size={len(self.payloads['board.dtb'])}\n"
            f"dtb_sha256={self.digest('board.dtb')}\n"
            f"initramfs_size={len(self.payloads['initramfs.cpio.gz'])}\n"
            f"initramfs_sha256={self.digest('initramfs.cpio.gz')}\n"
            "target_id=rog5-test\n"
            "target_release=test-1\n"
            "rollback_timeout=120\n"
            "target_timeout=90\n"
            f"a660_command_manifest_sha256={'a' * 64}\n"
            "root_generation=arch-a\n"
            f"root_tree_sha256={'b' * 64}\n"
            f"root_seal_sha256={'c' * 64}\n"
            "root_tree_entries=7\n"
            "root_subtree=/\n"
        ).encode("ascii")
        self.payloads = {
            "manifest": manifest,
            "manifest.sig": bytes(range(64)),
            **self.payloads,
        }
        for name, _minimum, _maximum in ARTIFACTS:
            path = self.bundle / name
            path.write_bytes(self.payloads[name])
            path.chmod(0o400)
        self.bundle.chmod(0o500)
        self.manifest_hash = hashlib.sha256(manifest).hexdigest()

    def digest(self, name: str) -> str:
        return hashlib.sha256(self.payloads[name]).hexdigest()

    def open_root(self) -> int:
        return os.open(
            self.root,
            os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC,
        )

    def prepare(self):
        root = self.open_root()
        try:
            prepared = prepare_bundle(
                root, BUNDLE, self.manifest_hash, os.geteuid()
            )
        except BaseException:
            os.close(root)
            raise
        return root, prepared

    def close(self) -> None:
        self.temporary.cleanup()


def request(
    *,
    bundle: str = BUNDLE,
    manifest_hash: str,
) -> bytes:
    payload = (
        "format=rog5-fetch-request-v1\n"
        f"bundle={bundle}\n"
        f"manifest_sha256={manifest_hash}\n"
    ).encode("ascii")
    return struct.pack(">I", len(payload)) + payload


def receive_all(connection: socket.socket) -> bytes:
    output = bytearray()
    while True:
        try:
            block = connection.recv(65536)
        except ConnectionResetError:
            return bytes(output)
        if not block:
            return bytes(output)
        output.extend(block)


class HostBundleServerTest(unittest.TestCase):
    def setUp(self):
        self.fixture = BundleFixture()

    def tearDown(self):
        self.fixture.close()

    def run_connection(self, wire: bytes) -> tuple[bytes, BaseException | None]:
        root, prepared = self.fixture.prepare()
        client, server = socket.socketpair()
        outcome: list[BaseException] = []

        def worker() -> None:
            with server:
                try:
                    serve_connection(
                        server,
                        prepared,
                        __import__("time").monotonic() + 2,
                    )
                    server.shutdown(socket.SHUT_WR)
                except BaseException as error:
                    outcome.append(error)

        thread = threading.Thread(target=worker, daemon=True)
        thread.start()
        with client:
            client.sendall(wire)
            client.shutdown(socket.SHUT_WR)
            response = receive_all(client)
        thread.join(timeout=2)
        self.assertFalse(thread.is_alive())
        prepared.close()
        os.close(root)
        return response, outcome[0] if outcome else None

    def test_exact_stream_uses_opened_read_only_descriptors(self):
        response, error = self.run_connection(
            request(manifest_hash=self.fixture.manifest_hash)
        )
        self.assertIsNone(error)
        header_size = struct.unpack(">I", response[:4])[0]
        self.assertLessEqual(header_size, HEADER_MAX)
        header_end = 4 + header_size
        header = response[4:header_end]
        expected_header = (
            "format=rog5-fetch-response-v1\n"
            f"bundle={BUNDLE}\n"
            f"manifest_sha256={self.fixture.manifest_hash}\n"
            f"manifest_size={len(self.fixture.payloads['manifest'])}\n"
            "signature_size=64\n"
            "kernel_size=64\n"
            "dtb_size=40\n"
            "initramfs_size=2\n"
        ).encode("ascii")
        self.assertEqual(header, expected_header)
        expected_bodies = b"".join(
            self.fixture.payloads[name]
            for name, _minimum, _maximum in ARTIFACTS
        )
        self.assertEqual(response[header_end:], expected_bodies)

    def test_success_reports_monotonic_artifact_progress(self):
        root, prepared = self.fixture.prepare()
        self.addCleanup(os.close, root)
        self.addCleanup(prepared.close)
        client, server = socket.socketpair()
        events: list[tuple[str, int, int]] = []
        outcome: list[BaseException] = []

        def observe(phase: str, sent: int, total: int) -> None:
            events.append((phase, sent, total))
            if phase == "manifest.sig":
                raise RuntimeError("injected observer failure")

        def worker() -> None:
            with server:
                try:
                    serve_connection(
                        server,
                        prepared,
                        __import__("time").monotonic() + 2,
                        progress=observe,
                    )
                    server.shutdown(socket.SHUT_WR)
                except BaseException as error:
                    outcome.append(error)

        thread = threading.Thread(target=worker, daemon=True)
        thread.start()
        with client:
            client.sendall(
                request(manifest_hash=self.fixture.manifest_hash)
            )
            client.shutdown(socket.SHUT_WR)
            receive_all(client)
        thread.join(timeout=2)
        self.assertFalse(thread.is_alive())
        self.assertEqual(outcome, [])
        total = sum(prepared.sizes)
        cumulative = 0
        expected = [("request-accepted", 0, total)]
        for (name, _minimum, _maximum), size in zip(
            ARTIFACTS,
            prepared.sizes,
            strict=True,
        ):
            cumulative += size
            expected.append((name, cumulative, total))
        self.assertEqual(events, expected)

    def test_path_replacement_after_prepare_cannot_change_bytes(self):
        root, prepared = self.fixture.prepare()
        original = b"".join(
            self.fixture.payloads[name]
            for name, _minimum, _maximum in ARTIFACTS
        )
        self.fixture.bundle.chmod(0o700)
        for name, _minimum, _maximum in ARTIFACTS:
            path = self.fixture.bundle / name
            replacement = self.fixture.bundle / f".{name}.replacement"
            replacement.write_bytes(b"R" * len(self.fixture.payloads[name]))
            replacement.chmod(0o400)
            os.replace(replacement, path)
        self.fixture.bundle.chmod(0o500)
        client, server = socket.socketpair()
        outcome = []

        def worker() -> None:
            with server:
                try:
                    serve_connection(
                        server,
                        prepared,
                        __import__("time").monotonic() + 2,
                    )
                    server.shutdown(socket.SHUT_WR)
                except BaseException as error:
                    outcome.append(error)

        thread = threading.Thread(target=worker, daemon=True)
        thread.start()
        with client:
            client.sendall(
                request(manifest_hash=self.fixture.manifest_hash)
            )
            client.shutdown(socket.SHUT_WR)
            response = receive_all(client)
        thread.join(timeout=2)
        self.assertEqual(outcome, [])
        header_size = struct.unpack(">I", response[:4])[0]
        self.assertEqual(response[4 + header_size :], original)
        prepared.close()
        os.close(root)

    def test_request_is_exact_and_bounded(self):
        valid = request(manifest_hash=self.fixture.manifest_hash)
        payload_size = struct.unpack(">I", valid[:4])[0]
        payload = valid[4:]
        mutations = (
            struct.pack(">I", 0),
            struct.pack(">I", REQUEST_MAX + 1),
            struct.pack(">I", payload_size + 1) + payload,
            struct.pack(">I", payload_size) + payload[:-1],
            request(
                bundle="another-bundle",
                manifest_hash=self.fixture.manifest_hash,
            ),
            request(manifest_hash="b" * 64),
            struct.pack(">I", payload_size)
            + payload.replace(
                b"format=rog5-fetch-request-v1",
                b"format=rog5-fetch-request-v2",
            ),
            valid + b"x",
        )
        for index, mutation in enumerate(mutations):
            with self.subTest(mutation=index):
                response, error = self.run_connection(mutation)
                self.assertEqual(response, b"")
                self.assertIsInstance(error, ServerRefusal)

    def test_delayed_trailing_request_byte_is_rejected_before_response(self):
        root, prepared = self.fixture.prepare()
        client, server = socket.socketpair()
        outcome: list[BaseException] = []

        def worker() -> None:
            with server:
                try:
                    serve_connection(
                        server,
                        prepared,
                        __import__("time").monotonic() + 2,
                    )
                except BaseException as error:
                    outcome.append(error)

        thread = threading.Thread(target=worker, daemon=True)
        thread.start()
        with client:
            client.sendall(
                request(manifest_hash=self.fixture.manifest_hash)
            )
            __import__("time").sleep(0.05)
            client.sendall(b"x")
            client.shutdown(socket.SHUT_WR)
            response = receive_all(client)
        thread.join(timeout=2)
        self.assertFalse(thread.is_alive())
        self.assertEqual(response, b"")
        self.assertEqual(len(outcome), 1)
        self.assertIsInstance(outcome[0], ServerRefusal)
        self.assertIn("trailing bytes", str(outcome[0]))
        prepared.close()
        os.close(root)

    def test_bundle_metadata_inventory_and_hash_fail_closed(self):
        mutations = (
            ("root-mode", lambda: self.fixture.root.chmod(0o755)),
            ("bundle-mode", lambda: self.fixture.bundle.chmod(0o700)),
            (
                "file-mode",
                lambda: (self.fixture.bundle / "Image").chmod(0o600),
            ),
            (
                "extra",
                self.add_extra,
            ),
            (
                "symlink",
                lambda: self.replace_with_symlink("board.dtb"),
            ),
            (
                "hardlink",
                lambda: self.replace_with_hardlink("board.dtb", "Image"),
            ),
            (
                "hash",
                lambda: self.replace_bytes("Image", b"Z" * 64),
            ),
        )
        for name, mutate in mutations:
            with self.subTest(mutation=name):
                self.fixture.close()
                self.fixture = BundleFixture()
                mutate()
                root = self.fixture.open_root()
                try:
                    with self.assertRaises(ServerRefusal):
                        prepare_bundle(
                            root,
                            BUNDLE,
                            self.fixture.manifest_hash,
                            os.geteuid(),
                        )
                finally:
                    os.close(root)

    def replace_bytes(self, name: str, payload: bytes) -> None:
        self.fixture.bundle.chmod(0o700)
        path = self.fixture.bundle / name
        path.chmod(0o600)
        path.write_bytes(payload)
        path.chmod(0o400)
        self.fixture.bundle.chmod(0o500)

    def add_extra(self) -> None:
        self.fixture.bundle.chmod(0o700)
        (self.fixture.bundle / "extra").write_bytes(b"x")
        self.fixture.bundle.chmod(0o500)

    def replace_with_symlink(self, name: str) -> None:
        self.fixture.bundle.chmod(0o700)
        path = self.fixture.bundle / name
        path.unlink()
        path.symlink_to("Image")
        self.fixture.bundle.chmod(0o500)

    def replace_with_hardlink(self, name: str, target: str) -> None:
        self.fixture.bundle.chmod(0o700)
        path = self.fixture.bundle / name
        path.unlink()
        os.link(self.fixture.bundle / target, path)
        self.fixture.bundle.chmod(0o500)

    def test_listener_rejects_wrong_peers_then_serves_once(self):
        root, prepared = self.fixture.prepare()
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
            listener.bind(("127.0.0.1", 0))
            listener.listen(2)
            port = listener.getsockname()[1]
            decisions = iter((False, True))
            outcome = []

            def worker() -> None:
                try:
                    serve_listener(
                        listener,
                        prepared,
                        lambda _peer: next(decisions),
                        timeout_seconds=2,
                    )
                except BaseException as error:
                    outcome.append(error)

            thread = threading.Thread(target=worker, daemon=True)
            thread.start()
            with socket.create_connection(("127.0.0.1", port)) as rejected:
                rejected.shutdown(socket.SHUT_WR)
                self.assertEqual(receive_all(rejected), b"")
            with socket.create_connection(("127.0.0.1", port)) as accepted:
                accepted.sendall(
                    request(manifest_hash=self.fixture.manifest_hash)
                )
                accepted.shutdown(socket.SHUT_WR)
                response = receive_all(accepted)
            thread.join(timeout=2)
            self.assertFalse(thread.is_alive())
            self.assertEqual(outcome, [])
            self.assertGreater(len(response), 4)
        prepared.close()
        os.close(root)

    def test_too_many_wrong_peers_is_terminal(self):
        root, prepared = self.fixture.prepare()
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
            listener.bind(("127.0.0.1", 0))
            listener.listen(MAX_REJECTED_PEERS)
            port = listener.getsockname()[1]
            outcome = []

            def worker() -> None:
                try:
                    serve_listener(
                        listener,
                        prepared,
                        lambda _peer: False,
                        timeout_seconds=3,
                    )
                except BaseException as error:
                    outcome.append(error)

            thread = threading.Thread(target=worker, daemon=True)
            thread.start()
            for _index in range(MAX_REJECTED_PEERS):
                with socket.create_connection(("127.0.0.1", port)):
                    pass
            thread.join(timeout=2)
            self.assertFalse(thread.is_alive())
            self.assertEqual(len(outcome), 1)
            self.assertIsInstance(outcome[0], ServerRefusal)
        prepared.close()
        os.close(root)

    def test_production_surface_is_fixed_and_has_no_key_access(self):
        source = (
            REPO / "tools/recovery_control/host_bundle_server.py"
        ).read_text(encoding="utf-8")
        self.assertEqual(BUNDLE_ROOT, Path("/var/lib/rog5-recovery-bundles"))
        self.assertEqual(HOST_ADDRESS, "169.254.77.1")
        self.assertEqual(DEVICE_ADDRESS, "169.254.77.2")
        self.assertEqual(HOST_PORT, 8080)
        for forbidden in (
            "PRIVATE KEY",
            "recovery-bundle-ed25519",
            "openssl",
            "http://",
            "https://",
            "urllib",
            "requests.",
            "subprocess.",
            "shell=True",
        ):
            self.assertNotIn(forbidden, source)
        self.assertEqual(source.count('hasattr(os, "O_NOATIME")'), 3)
        refusal = subprocess.run(
            [
                sys.executable,
                str(REPO / "tools/recovery_control/host_bundle_server.py"),
            ],
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertNotEqual(refusal.returncode, 0)
        self.assertIn("usage:", refusal.stderr)
        invalid = subprocess.run(
            [
                sys.executable,
                str(REPO / "tools/recovery_control/host_bundle_server.py"),
                "../escape",
                "a" * 64,
            ],
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertNotEqual(invalid.returncode, 0)
        self.assertIn("invalid requested bundle identity", invalid.stderr)
        self.assertNotIn("bundle root", invalid.stderr)

    def test_preflight_uses_exact_descriptor_validation_without_listener(self):
        module = sys.modules[
            "tools.recovery_control.host_bundle_server"
        ]
        original = module.BUNDLE_ROOT
        module.BUNDLE_ROOT = self.fixture.root
        extra = self.fixture.root / "consumed-bundle"
        tracked = [
            self.fixture.root,
            self.fixture.bundle,
            *(self.fixture.bundle / name for name, *_limits in ARTIFACTS),
        ]
        for path in tracked:
            metadata = path.stat()
            os.utime(
                path,
                ns=(1_000_000_000, metadata.st_mtime_ns),
            )
        atimes = {path: path.stat().st_atime_ns for path in tracked}
        try:
            run_preflight(BUNDLE, self.fixture.manifest_hash)
            self.assertEqual(
                {path: path.stat().st_atime_ns for path in tracked},
                atimes,
            )
            extra.mkdir(mode=0o500)
            with self.assertRaisesRegex(
                ServerRefusal, "unexpected bundle-root inventory"
            ):
                run_preflight(BUNDLE, self.fixture.manifest_hash)
        finally:
            if extra.exists():
                extra.rmdir()
            module.BUNDLE_ROOT = original

    def test_record_parser_rejects_noncanonical_fields(self):
        valid = (
            "format=rog5-fetch-request-v1\n"
            f"bundle={BUNDLE}\n"
            f"manifest_sha256={self.fixture.manifest_hash}\n"
        ).encode("ascii")
        self.assertEqual(
            parse_record(valid, REQUEST_FIELDS)["bundle"], BUNDLE
        )
        for payload in (
            valid[:-1],
            valid.replace(b"\n", b"\r\n"),
            valid.replace(b"bundle=", b"unknown=", 1),
            valid.replace(
                b"bundle=",
                b"bundle=x\nbundle=",
                1,
            ),
            valid + b"extra=value\n",
            valid.replace(b"arch-test-v1", b"arch-\xffest-v1"),
        ):
            with self.assertRaises(ServerRefusal):
                parse_record(payload, REQUEST_FIELDS)

    def test_manifest_root_trust_identity_is_fail_closed(self):
        payload = self.fixture.payloads["manifest"]
        observed = {
            name: (
                len(self.fixture.payloads[name]),
                hashlib.sha256(
                    self.fixture.payloads[name]
                ).hexdigest(),
            )
            for name in ("Image", "board.dtb", "initramfs.cpio.gz")
        }
        mutations = (
            payload.replace(b"root_generation=arch-a", b"root_generation=arch-b"),
            payload.replace(
                b"root_tree_sha256=" + b"b" * 64,
                b"root_tree_sha256=" + b"0" * 64,
            ),
            payload.replace(b"root_tree_entries=7", b"root_tree_entries=0"),
            payload.replace(
                b"profile=network-root-v1",
                b"profile=persistent-root-ro-v1",
            ),
        )
        for mutation in mutations:
            with self.subTest(mutation=hashlib.sha256(mutation).hexdigest()):
                with self.assertRaises(ServerRefusal):
                    validate_manifest(
                        mutation,
                        BUNDLE,
                        hashlib.sha256(mutation).hexdigest(),
                        observed,
                    )


if __name__ == "__main__":
    unittest.main(verbosity=2)
