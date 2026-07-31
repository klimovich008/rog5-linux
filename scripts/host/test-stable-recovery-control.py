#!/usr/bin/env python3
"""Pseudoterminal tests for the stable recovery host transaction client."""

from __future__ import annotations

import importlib.util
from dataclasses import replace
import os
from pathlib import Path
import pty
import select
import sys
import tempfile
import threading
import unittest
from unittest import mock


sys.dont_write_bytecode = True
SOURCE = Path(__file__).with_name("stable-recovery-control.py")
SPEC = importlib.util.spec_from_file_location("stable_recovery_control", SOURCE)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)

REPO = SOURCE.parents[2]
sys.path.insert(0, str(REPO))

from tools.recovery_control import (  # noqa: E402
    FrameParser,
    RecoveryModel,
    RecoveryState,
    decode_request,
    encode_frame,
    encode_response,
)


SESSION = "1" * 32
MANIFEST = "a" * 64
BUNDLE = "headless-network-root-v1"
DEPLOYMENT_BUNDLE = "headless-ssh-network-root-v3-r2"
DEPLOYMENT_PROFILE = "headless-ssh-deployment-v3"
PACKAGE_SHA256 = "c" * 64
HANDOFF_TOKEN = "b" * 64


class StableRecoveryControlTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.ledger = Path(self.temporary.name) / "ledger"
        self.commit_requests: list[str] = []

    def tearDown(self):
        self.temporary.cleanup()

    def run_responder(
        self,
        master: int,
        *,
        drop_commit: bool = False,
        wrong_commit_fingerprint: bool = False,
    ) -> None:
        model = RecoveryModel(RecoveryState(session=SESSION))
        parser = FrameParser()
        while True:
            readable, _, _ = select.select([master], [], [], 5)
            if not readable:
                return
            try:
                chunk = os.read(master, 8192)
            except OSError:
                return
            if not chunk:
                return
            for payload in parser.feed(chunk):
                request = decode_request(payload)
                response = model.handle(request)
                if request.verb == "COMMIT_EXEC":
                    self.commit_requests.append(request.request)
                    if drop_commit:
                        os.close(master)
                        return
                    if wrong_commit_fingerprint:
                        response = replace(
                            response,
                            commit_fingerprint="f" * 64,
                        )
                os.write(master, encode_frame(encode_response(response)))
                if request.verb == "COMMIT_EXEC":
                    return

    def pty_transaction(
        self,
        *,
        drop_commit: bool = False,
        wrong_commit_fingerprint: bool = False,
        before_commit=None,
    ):
        master, slave = pty.openpty()
        path = os.ttyname(slave)
        thread = threading.Thread(
            target=self.run_responder,
            args=(master,),
            kwargs={
                "drop_commit": drop_commit,
                "wrong_commit_fingerprint": wrong_commit_fingerprint,
            },
        )
        thread.start()
        try:
            with mock.patch.object(
                MODULE,
                "wait_for_stable_recovery_acm",
                return_value=path,
            ):
                return MODULE.prepare_and_commit(
                    BUNDLE,
                    MANIFEST,
                    ledger_path=self.ledger,
                    before_commit=before_commit,
                )
        finally:
            os.close(slave)
            if not drop_commit:
                os.close(master)
            thread.join(timeout=5)
            self.assertFalse(thread.is_alive())

    def test_one_commit_is_claimed_but_remains_unknown(self):
        prepared, committed, intent = self.pty_transaction()
        self.assertEqual(prepared.result, "PREPARED")
        self.assertEqual(committed.result, "CLAIMED")
        self.assertEqual(intent.state, "TRANSMITTED")
        self.assertEqual(intent.outcome, "UNKNOWN")
        self.assertEqual(intent.session, SESSION)
        self.assertEqual(intent.manifest_sha256, MANIFEST)
        self.assertEqual(len(self.commit_requests), 1)

    def test_dropped_commit_response_is_never_retried(self):
        with self.assertRaisesRegex(
            MODULE.TransportLost,
            "intent remains UNKNOWN",
        ):
            self.pty_transaction(drop_commit=True)
        records = list(self.ledger.glob("*.json"))
        self.assertEqual(len(records), 1)
        ledger = MODULE.HostIntentLedger(self.ledger)
        try:
            intent = ledger.read(SESSION)
        finally:
            ledger.close()
        self.assertEqual(intent.state, "TRANSMITTED")
        self.assertEqual(intent.outcome, "UNKNOWN")
        self.assertEqual(len(self.commit_requests), 1)

    def test_mismatched_commit_fingerprint_is_not_accepted(self):
        with self.assertRaisesRegex(
            RuntimeError,
            "inconsistent CLAIMED",
        ):
            self.pty_transaction(wrong_commit_fingerprint=True)
        self.assertEqual(len(self.commit_requests), 1)
        ledger = MODULE.HostIntentLedger(self.ledger)
        try:
            intent = ledger.read(SESSION)
        finally:
            ledger.close()
        self.assertEqual(intent.state, "TRANSMITTED")
        self.assertEqual(intent.outcome, "UNKNOWN")

    def test_failed_precommit_rendezvous_never_arms_or_sends_commit(self):
        def refuse():
            raise RuntimeError("NFS not ready")

        with self.assertRaisesRegex(RuntimeError, "NFS not ready"):
            self.pty_transaction(before_commit=refuse)
        self.assertEqual(self.commit_requests, [])
        self.assertFalse(self.ledger.exists())

    def test_prepare_replay_shares_one_absolute_deadline(self):
        first = mock.MagicMock()
        second = mock.MagicMock()
        first.exchange.side_effect = MODULE.TransportLost("lost")
        second.exchange.side_effect = RuntimeError("stop after replay")
        with (
            mock.patch.object(
                MODULE,
                "connect",
                side_effect=(
                    (first, SESSION, mock.sentinel.hello),
                    (second, SESSION, mock.sentinel.hello),
                ),
            ),
            mock.patch.object(
                MODULE.time,
                "monotonic",
                side_effect=(100.0, 101.0, 104.0),
            ),
            self.assertRaisesRegex(RuntimeError, "stop after replay"),
        ):
            MODULE.prepare_and_commit(BUNDLE, MANIFEST)
        self.assertEqual(first.exchange.call_args.args[1], 259.0)
        self.assertEqual(second.exchange.call_args.args[1], 256.0)
        first.close.assert_called_once_with()

    def test_guards_precede_device_discovery(self):
        with (
            mock.patch.dict(os.environ, {}, clear=True),
            mock.patch.object(MODULE, "ensure_host_ready") as ready,
            self.assertRaisesRegex(RuntimeError, "ALLOW_STABLE_RECOVERY_CONTROL"),
        ):
            MODULE.main(["prepare-commit", BUNDLE, MANIFEST])
        ready.assert_not_called()

    def test_network_root_handoff_guard_precedes_device_discovery(self):
        with (
            mock.patch.dict(
                os.environ,
                {
                    "ALLOW_STABLE_RECOVERY_CONTROL": "1",
                    "ALLOW_ATTENDED_KEXEC": "1",
                },
                clear=True,
            ),
            mock.patch.object(MODULE, "ensure_host_ready") as ready,
            self.assertRaisesRegex(
                RuntimeError,
                "ALLOW_NETWORK_ROOT_NFS_HANDOFF",
            ),
        ):
            MODULE.main(["prepare-commit", BUNDLE, MANIFEST])
        ready.assert_not_called()

    def test_network_root_handoff_token_precedes_device_discovery(self):
        with (
            mock.patch.dict(
                os.environ,
                {
                    "ALLOW_STABLE_RECOVERY_CONTROL": "1",
                    "ALLOW_ATTENDED_KEXEC": "1",
                    "ALLOW_NETWORK_ROOT_NFS_HANDOFF": "1",
                },
                clear=True,
            ),
            mock.patch.object(MODULE, "ensure_host_ready") as ready,
            self.assertRaisesRegex(
                RuntimeError,
                "ROG5_NFS_HANDOFF_TOKEN",
            ),
        ):
            MODULE.main(["prepare-commit", BUNDLE, MANIFEST])
        ready.assert_not_called()

    def test_deployment_profile_precedes_device_discovery(self):
        with (
            mock.patch.dict(
                os.environ,
                {
                    "ALLOW_STABLE_RECOVERY_CONTROL": "1",
                    "ALLOW_ATTENDED_KEXEC": "1",
                    "ALLOW_NETWORK_ROOT_NFS_HANDOFF": "1",
                    "ROG5_NFS_HANDOFF_TOKEN": HANDOFF_TOKEN,
                },
                clear=True,
            ),
            mock.patch.object(MODULE, "ensure_host_ready") as ready,
            self.assertRaisesRegex(RuntimeError, "ROG5_NFS_PROFILE"),
        ):
            MODULE.main(
                ["prepare-commit", DEPLOYMENT_BUNDLE, MANIFEST]
            )
        ready.assert_not_called()

    def test_deployment_package_identity_precedes_device_discovery(self):
        with (
            mock.patch.dict(
                os.environ,
                {
                    "ALLOW_STABLE_RECOVERY_CONTROL": "1",
                    "ALLOW_ATTENDED_KEXEC": "1",
                    "ALLOW_NETWORK_ROOT_NFS_HANDOFF": "1",
                    "ROG5_NFS_HANDOFF_TOKEN": HANDOFF_TOKEN,
                    "ROG5_NFS_PROFILE": DEPLOYMENT_PROFILE,
                },
                clear=True,
            ),
            mock.patch.object(MODULE, "ensure_host_ready") as ready,
            self.assertRaisesRegex(
                RuntimeError,
                "ROG5_NFS_PACKAGE_SHA256",
            ),
        ):
            MODULE.main(
                ["prepare-commit", DEPLOYMENT_BUNDLE, MANIFEST]
            )
        ready.assert_not_called()

    def test_network_root_readiness_uses_token_marker_and_listener(self):
        fake_ss = mock.MagicMock()
        with (
            mock.patch.object(
                MODULE,
                "nfs_handoff_marker_matches",
                return_value=True,
            ) as marker,
            mock.patch.object(MODULE, "SS", fake_ss),
            mock.patch.object(MODULE.subprocess, "run") as run,
        ):
            fake_ss.stat.return_value.st_mode = 0o100755
            fake_ss.stat.return_value.st_uid = 0
            fake_ss.stat.return_value.st_gid = 0
            run.return_value.stdout = (
                "LISTEN 0 4096 169.254.77.1:2049 0.0.0.0:*\n"
            )
            self.assertTrue(MODULE.network_root_nfs_ready(HANDOFF_TOKEN))
        marker.assert_called_once_with(HANDOFF_TOKEN)
        self.assertNotIn(
            "/proc/fs/nfsd",
            SOURCE.read_text(encoding="utf-8"),
        )

    def test_deployment_readiness_uses_exact_profile_and_package(self):
        fake_ss = mock.MagicMock()
        with (
            mock.patch.object(
                MODULE,
                "nfs_handoff_marker_matches",
                return_value=True,
            ) as marker,
            mock.patch.object(MODULE, "SS", fake_ss),
            mock.patch.object(MODULE.subprocess, "run") as run,
        ):
            fake_ss.stat.return_value.st_mode = 0o100755
            fake_ss.stat.return_value.st_uid = 0
            fake_ss.stat.return_value.st_gid = 0
            run.return_value.stdout = (
                "LISTEN 0 4096 169.254.77.1:2049 0.0.0.0:*\n"
            )
            self.assertTrue(
                MODULE.network_root_nfs_ready(
                    HANDOFF_TOKEN,
                    DEPLOYMENT_BUNDLE,
                    PACKAGE_SHA256,
                )
            )
        marker.assert_called_once_with(
            HANDOFF_TOKEN,
            DEPLOYMENT_BUNDLE,
            PACKAGE_SHA256,
        )

    def test_resolution_guard_precedes_ledger_access(self):
        with (
            mock.patch.dict(os.environ, {}, clear=True),
            mock.patch.object(MODULE, "HostIntentLedger") as ledger,
            self.assertRaisesRegex(
                RuntimeError,
                "ALLOW_RECOVERY_INTENT_RESOLVE",
            ),
        ):
            MODULE.main(
                [
                    "resolve",
                    SESSION,
                    "2" * 32,
                    "TARGET_ACCEPTED",
                ]
            )
        ledger.assert_not_called()

    def test_resolve_uses_only_the_exact_session_and_request(self):
        _, _, intent = self.pty_transaction()
        ledger = MODULE.HostIntentLedger(self.ledger)
        try:
            resolved = ledger.resolve(
                session=intent.session,
                request=intent.request,
                outcome="TARGET_ACCEPTED",
            )
        finally:
            ledger.close()
        self.assertEqual(resolved.state, "RESOLVED")
        self.assertEqual(resolved.outcome, "TARGET_ACCEPTED")


if __name__ == "__main__":
    unittest.main()
