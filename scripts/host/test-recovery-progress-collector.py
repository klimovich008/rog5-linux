#!/usr/bin/env python3
"""Offline tests for the receive-only recovery progress collector."""

from __future__ import annotations

import hashlib
from pathlib import Path
import select
import socket
import sys
import threading
import time
import unittest
from unittest import mock


REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from tools.recovery_control import (  # noqa: E402
    PREPARE_PROGRESS_PHASES,
    Progress,
    encode_frame,
    encode_progress,
)
from tools.recovery_control.host_progress_collector import (  # noqa: E402
    CollectorRefusal,
    ProgressCapture,
    collect_connection,
    collect_listener,
    open_fixed_listener,
)


SESSION = "1" * 32
REQUEST = "2" * 32
BUNDLE = "arch-test-v1"
MANIFEST = "a" * 64


def progress_stream(*, request: str = REQUEST) -> bytes:
    return b"".join(
        encode_frame(
            encode_progress(
                Progress(
                    session=SESSION,
                    request=request,
                    sequence=sequence,
                    phase=phase,
                    bundle=BUNDLE,
                    manifest_sha256=MANIFEST,
                )
            )
        )
        for sequence, phase in enumerate(PREPARE_PROGRESS_PHASES, 1)
    )


def capture_bytes(
    wire: bytes,
    *,
    wire_max: int = 8192,
    expected_session: str | None = None,
    expected_request: str | None = None,
) -> ProgressCapture:
    client, server = socket.socketpair()
    with client, server:
        client.sendall(wire)
        client.shutdown(socket.SHUT_WR)
        return collect_connection(
            server,
            bundle=BUNDLE,
            manifest_sha256=MANIFEST,
            deadline=time.monotonic() + 2,
            expected_session=expected_session,
            expected_request=expected_request,
            wire_max=wire_max,
        )


class RecoveryProgressCollectorTest(unittest.TestCase):
    def test_complete_stream_is_correlated_and_explicitly_advisory(self):
        wire = progress_stream()
        capture = capture_bytes(wire)
        self.assertTrue(capture.complete)
        self.assertEqual(capture.session, SESSION)
        self.assertEqual(capture.request, REQUEST)
        self.assertEqual(capture.phases, PREPARE_PROGRESS_PHASES)
        self.assertEqual(capture.wire_bytes, len(wire))
        self.assertEqual(capture.wire_sha256, hashlib.sha256(wire).hexdigest())
        record = capture.record().decode("ascii")
        self.assertIn("result=COMPLETE\n", record)
        self.assertIn("truncated=NO\n", record)
        self.assertIn("authority=NONE\n", record)
        self.assertNotIn("COMMIT_EXEC", record)

    def test_every_wire_truncation_point_is_never_complete(self):
        wire = progress_stream()
        for end in range(len(wire)):
            with self.subTest(end=end):
                capture = capture_bytes(wire[:end])
                self.assertFalse(capture.complete)
                self.assertTrue(capture.truncated)
                self.assertIn(
                    "truncated=YES\n", capture.record().decode("ascii")
                )

    def test_wire_cap_has_an_explicit_truncation_marker(self):
        wire = progress_stream()
        capture = capture_bytes(wire, wire_max=len(wire) - 1)
        self.assertEqual(capture.result, "PARTIAL")
        self.assertEqual(capture.reason, "WIRE_CAP")
        self.assertTrue(capture.truncated)
        self.assertEqual(capture.wire_bytes, len(wire) - 1)

    def test_exact_wire_cap_accepts_clean_eof(self):
        wire = progress_stream()
        capture = capture_bytes(wire, wire_max=len(wire))
        self.assertTrue(capture.complete)
        self.assertFalse(capture.truncated)

    def test_stalled_stream_times_out_without_authority(self):
        client, server = socket.socketpair()
        self.addCleanup(client.close)
        self.addCleanup(server.close)
        started = time.monotonic()
        capture = collect_connection(
            server,
            bundle=BUNDLE,
            manifest_sha256=MANIFEST,
            deadline=started + 0.03,
        )
        self.assertEqual(capture.reason, "TIMEOUT")
        self.assertTrue(capture.truncated)
        self.assertIn("authority=NONE\n", capture.record().decode("ascii"))

    def test_wrong_pinned_session_or_request_rejects_whole_stream(self):
        for session, request in (("f" * 32, REQUEST), (SESSION, "f" * 32)):
            with self.subTest(session=session, request=request):
                with self.assertRaisesRegex(
                    CollectorRefusal, "identity mismatch"
                ):
                    capture_bytes(
                        progress_stream(),
                        expected_session=session,
                        expected_request=request,
                    )

    def test_identity_change_rejects_whole_stream(self):
        first = encode_frame(
            encode_progress(
                Progress(
                    session=SESSION,
                    request=REQUEST,
                    sequence=1,
                    phase=PREPARE_PROGRESS_PHASES[0],
                    bundle=BUNDLE,
                    manifest_sha256=MANIFEST,
                )
            )
        )
        wrong = encode_frame(
            encode_progress(
                Progress(
                    session=SESSION,
                    request="3" * 32,
                    sequence=2,
                    phase=PREPARE_PROGRESS_PHASES[1],
                    bundle=BUNDLE,
                    manifest_sha256=MANIFEST,
                )
            )
        )
        with self.assertRaisesRegex(CollectorRefusal, "identity mismatch"):
            capture_bytes(first + wrong)

    def test_noncontiguous_prefix_rejects_whole_stream(self):
        record = Progress(
            session=SESSION,
            request=REQUEST,
            sequence=2,
            phase=PREPARE_PROGRESS_PHASES[1],
            bundle=BUNDLE,
            manifest_sha256=MANIFEST,
        )
        with self.assertRaisesRegex(CollectorRefusal, "noncontiguous"):
            capture_bytes(encode_frame(encode_progress(record)))

    def test_partial_record_tear_is_reported_not_promoted(self):
        wire = progress_stream()
        first_comma = wire.index(b",") + 1
        capture = capture_bytes(wire[: first_comma + 7])
        self.assertEqual(capture.phases, PREPARE_PROGRESS_PHASES[:1])
        self.assertEqual(capture.reason, "TORN_FRAME")
        self.assertTrue(capture.truncated)

    def test_complete_phases_plus_trailing_tear_are_never_promoted(self):
        wire = progress_stream() + b"12:version=1\n"
        capture = capture_bytes(wire)
        self.assertEqual(capture.phases, PREPARE_PROGRESS_PHASES)
        self.assertEqual(capture.result, "PARTIAL")
        self.assertEqual(capture.reason, "TORN_FRAME")
        self.assertTrue(capture.truncated)

    def test_fragmented_stream_remains_complete(self):
        client, server = socket.socketpair()
        self.addCleanup(client.close)
        self.addCleanup(server.close)

        def send() -> None:
            for byte in progress_stream():
                client.send(bytes([byte]))
            client.shutdown(socket.SHUT_WR)

        sender = threading.Thread(target=send)
        sender.start()
        capture = collect_connection(
            server,
            bundle=BUNDLE,
            manifest_sha256=MANIFEST,
            deadline=time.monotonic() + 3,
        )
        sender.join(timeout=3)
        self.assertFalse(sender.is_alive())
        self.assertTrue(capture.complete)

    def test_listener_rejects_wrong_peer_then_closes_after_one_stream(self):
        client, valid = socket.socketpair()
        self.addCleanup(client.close)
        wrong = mock.MagicMock()
        listener = mock.MagicMock()
        listener.accept.side_effect = (
            (wrong, ("192.0.2.1", 1000)),
            (valid, ("169.254.77.2", 1001)),
        )
        client.sendall(progress_stream())
        client.shutdown(socket.SHUT_WR)
        real_select = select.select

        def select_listener(readers, writers, errors, timeout=None):
            if listener in readers:
                return [listener], [], []
            return real_select(readers, writers, errors, timeout)

        with mock.patch("select.select", side_effect=select_listener):
            capture = collect_listener(
                listener,
                bundle=BUNDLE,
                manifest_sha256=MANIFEST,
                deadline=time.monotonic() + 2,
            )
        self.assertTrue(capture.complete)
        self.assertEqual(client.recv(1), b"")
        wrong.close.assert_called_once_with()
        listener.close.assert_called_once_with()
        self.assertEqual(listener.accept.call_count, 2)

    def test_fixed_listener_is_bound_to_exact_interface_and_endpoint(self):
        listener = mock.MagicMock()
        listener.getsockopt.return_value = b"usb0\0"
        listener.getsockname.return_value = ("169.254.77.1", 8081)
        with mock.patch("socket.socket", return_value=listener):
            result = open_fixed_listener("usb0")
        self.assertIs(result, listener)
        listener.setsockopt.assert_any_call(
            socket.SOL_SOCKET,
            socket.SO_BINDTODEVICE,
            b"usb0\0",
        )
        listener.bind.assert_called_once_with(("169.254.77.1", 8081))
        listener.listen.assert_called_once_with(1)

    def test_fixed_listener_rejects_every_other_interface(self):
        for interface in ("eth0", "usbé", "usb/0", "usb 0", "", 3):
            with self.subTest(interface=interface), self.assertRaisesRegex(
                CollectorRefusal, "invalid"
            ):
                open_fixed_listener(interface)

    def test_fixed_listener_rejects_post_bind_identity_mismatch(self):
        cases = (
            (b"eth0\0", ("169.254.77.1", 8081)),
            (b"usb0\0", ("0.0.0.0", 8081)),
            (b"usb0\0", ("169.254.77.1", 8082)),
        )
        for bound_interface, endpoint in cases:
            with self.subTest(interface=bound_interface, endpoint=endpoint):
                listener = mock.MagicMock()
                listener.getsockopt.return_value = bound_interface
                listener.getsockname.return_value = endpoint
                with (
                    mock.patch("socket.socket", return_value=listener),
                    self.assertRaisesRegex(CollectorRefusal, "binding mismatch"),
                ):
                    open_fixed_listener("usb0")
                listener.close.assert_called_once_with()
                listener.listen.assert_not_called()

    def test_capture_rejects_noncanonical_caller_identity(self):
        invalid = (
            ("bad/../bundle", MANIFEST, None, None),
            (BUNDLE, "0" * 64, None, None),
            (BUNDLE, MANIFEST, "1\n" + "1" * 30, None),
            (BUNDLE, MANIFEST, SESSION, "0" * 32),
        )
        for bundle, manifest, session, request in invalid:
            with self.subTest(bundle=bundle, session=session), self.assertRaisesRegex(
                CollectorRefusal, "invalid progress"
            ):
                client, server = socket.socketpair()
                with client, server:
                    collect_connection(
                        server,
                        bundle=bundle,
                        manifest_sha256=manifest,
                        deadline=time.monotonic() + 1,
                        expected_session=session,
                        expected_request=request,
                    )

    def test_wrong_peers_cannot_exhaust_a_fixed_reject_budget(self):
        client, valid = socket.socketpair()
        self.addCleanup(client.close)
        listener = mock.MagicMock()
        wrong_connections = [mock.MagicMock() for _ in range(16)]
        peers = ["not-a-peer", (), ("192.0.2.1", 1)]
        peers.extend(("192.0.2.1", port) for port in range(2, 15))
        listener.accept.side_effect = (
            *tuple(zip(wrong_connections, peers, strict=True)),
            (valid, ("169.254.77.2", 1001)),
        )
        client.sendall(progress_stream())
        client.shutdown(socket.SHUT_WR)
        real_select = select.select

        def select_listener(readers, writers, errors, timeout=None):
            if listener in readers:
                return [listener], [], []
            return real_select(readers, writers, errors, timeout)

        with mock.patch("select.select", side_effect=select_listener):
            capture = collect_listener(
                listener,
                bundle=BUNDLE,
                manifest_sha256=MANIFEST,
                deadline=time.monotonic() + 2,
            )
        self.assertTrue(capture.complete)
        self.assertEqual(client.recv(1), b"")
        self.assertEqual(listener.accept.call_count, 17)
        for connection in wrong_connections:
            connection.close.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
