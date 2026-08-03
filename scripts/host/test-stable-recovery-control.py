#!/usr/bin/env python3
"""Pseudoterminal tests for the stable recovery host transaction client."""

from __future__ import annotations

from contextlib import redirect_stdout
from dataclasses import replace
import importlib.util
import io
import json
import os
from pathlib import Path
import pty
import select
import stat
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
sys.modules[SPEC.name] = MODULE
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
DIAGNOSTIC_BUNDLE = "headless-netroot-early-diag-v1"
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

    def test_recovery_acm_observation_classifies_without_exposing_identity(self):
        metadata = mock.Mock(st_mode=stat.S_IFCHR | 0o660, st_rdev=123)
        recovery = {
            "ID_VENDOR_ID": "1d6b",
            "ID_MODEL_ID": "0104",
            "ID_MODEL": "ROG5_recovery",
            "DEVPATH": "/devices/secret",
            "ID_PATH": "secret-port",
            "ID_SERIAL": "secret-serial",
        }
        cases = (
            ([], {}, {}, None, "absent", None),
            (
                ["/dev/ttyACM-secret"],
                {"/dev/ttyACM-secret": {"ID_MODEL": "other"}},
                {"/dev/ttyACM-secret": metadata},
                None,
                "product-mismatch",
                None,
            ),
            (
                ["/dev/ttyACM-secret"],
                {"/dev/ttyACM-secret": recovery},
                {"/dev/ttyACM-secret": OSError("private path")},
                None,
                "inspect-error",
                None,
            ),
            (
                ["/dev/ttyACM-secret"],
                {"/dev/ttyACM-secret": recovery},
                {
                    "/dev/ttyACM-secret": mock.Mock(
                        st_mode=stat.S_IFREG | 0o660,
                        st_rdev=123,
                    )
                },
                None,
                "node-mismatch",
                None,
            ),
            (
                ["/dev/ttyACM-a", "/dev/ttyACM-b"],
                {"/dev/ttyACM-a": recovery, "/dev/ttyACM-b": recovery},
                {"/dev/ttyACM-a": metadata, "/dev/ttyACM-b": metadata},
                None,
                "duplicate",
                None,
            ),
            (
                ["/dev/ttyACM-secret"],
                {"/dev/ttyACM-secret": recovery},
                {"/dev/ttyACM-secret": metadata},
                {os.R_OK: False},
                "unreadable",
                None,
            ),
            (
                ["/dev/ttyACM-secret"],
                {"/dev/ttyACM-secret": recovery},
                {"/dev/ttyACM-secret": metadata},
                {os.R_OK: True, os.W_OK: False},
                "read-only",
                None,
            ),
        )
        for (
            devices,
            properties,
            metadata_by_path,
            access,
            state,
            identity,
        ) in cases:
            def fake_stat(path, **_kwargs):
                value = metadata_by_path[path]
                if isinstance(value, BaseException):
                    raise value
                return value

            with (
                self.subTest(state=state),
                mock.patch.object(MODULE.glob, "glob", return_value=devices),
                mock.patch.object(
                    MODULE,
                    "udev_properties",
                    side_effect=lambda path: properties[path],
                ),
                mock.patch.object(
                    MODULE.os,
                    "stat",
                    side_effect=fake_stat,
                ),
                mock.patch.object(
                    MODULE.os,
                    "access",
                    side_effect=lambda _path, mode: access[mode],
                ) as access_mock,
            ):
                observed = MODULE.observe_recovery_acm()
            self.assertEqual(observed.state, state)
            self.assertEqual(observed.identity, identity)
            if access is None:
                access_mock.assert_not_called()

    def test_opaque_acm_node_prevents_an_otherwise_exact_observation(self):
        metadata = mock.Mock(st_mode=stat.S_IFCHR | 0o660, st_rdev=123)
        recovery = {
            "ID_VENDOR_ID": "1d6b",
            "ID_MODEL_ID": "0104",
            "ID_MODEL": "ROG5_recovery",
        }

        def inspect(path):
            if path.endswith("opaque"):
                raise OSError("private path")
            return recovery

        with (
            mock.patch.object(
                MODULE.glob,
                "glob",
                return_value=["/dev/ttyACM-exact", "/dev/ttyACM-opaque"],
            ),
            mock.patch.object(MODULE, "udev_properties", side_effect=inspect),
            mock.patch.object(MODULE.os, "stat", return_value=metadata),
            mock.patch.object(MODULE.os, "access") as access,
        ):
            observed = MODULE.observe_recovery_acm()
        self.assertEqual(observed.state, "inspect-error")
        self.assertIsNone(observed.identity)
        access.assert_not_called()

    def test_recovery_acm_observation_invariants_fail_closed(self):
        identity = ("device", 1, "devpath", "id-path", "serial")
        for state, value in (
            ("invalid", None),
            ("exact", None),
            ("absent", identity),
        ):
            with self.subTest(state=state), self.assertRaises(ValueError):
                MODULE.RecoveryAcmObservation(state, value)
        with self.assertRaisesRegex(RuntimeError, "has no exact device"):
            MODULE.RecoveryAcmObservation("absent").path()

    def test_recovery_acm_observation_accepts_one_exact_rw_device(self):
        metadata = mock.Mock(st_mode=stat.S_IFCHR | 0o660, st_rdev=123)
        properties = {
            "ID_VENDOR_ID": "1d6b",
            "ID_MODEL_ID": "0104",
            "ID_MODEL": "ROG5_recovery",
            "DEVPATH": "/devices/secret",
            "ID_PATH": "secret-port",
            "ID_SERIAL": "secret-serial",
        }
        with (
            mock.patch.object(
                MODULE.glob, "glob", return_value=["/dev/ttyACM-secret"]
            ),
            mock.patch.object(
                MODULE, "udev_properties", return_value=properties
            ),
            mock.patch.object(MODULE.os, "stat", return_value=metadata),
            mock.patch.object(MODULE.os, "access", return_value=True),
        ):
            observed = MODULE.observe_recovery_acm()
        self.assertEqual(observed.state, "exact")
        self.assertEqual(observed.identity[1], 123)
        self.assertEqual(observed.path(), "/dev/ttyACM-secret")

    def test_stability_returns_only_after_exact_identity_revalidation(self):
        identity = ("/dev/ttyACM-secret", 1, "dev", "path", "serial")
        observation = MODULE.RecoveryAcmObservation("exact", identity)
        with (
            mock.patch.object(
                MODULE,
                "observe_recovery_acm",
                side_effect=(observation, observation, observation),
            ) as observe,
            mock.patch.object(
                MODULE.time,
                "monotonic",
                side_effect=(0.0, 0.0, 0.0, 0.1, 0.1),
            ),
            mock.patch.object(MODULE.time, "sleep"),
        ):
            path = MODULE.wait_for_stable_recovery_acm(
                settle_seconds=0.1,
                timeout_seconds=1.0,
                poll_seconds=0.01,
            )
        self.assertEqual(path, "/dev/ttyACM-secret")
        self.assertEqual(observe.call_count, 3)

    def test_recovery_acm_trace_is_bounded_and_reports_only_field_names(self):
        trace = MODULE.RecoveryAcmTrace()
        first = MODULE.RecoveryAcmObservation(
            "exact",
            (
                "/dev/ttyACM-secret-a",
                1,
                "secret-dev-a",
                "secret-path-a",
                "secret-serial-a",
            ),
        )
        second = MODULE.RecoveryAcmObservation(
            "exact",
            (
                "/dev/ttyACM-secret-b",
                2,
                "secret-dev-b",
                "secret-path-b",
                "secret-serial-b",
            ),
        )
        trace.record(first)
        trace.record(second)
        for index in range(MODULE.RECOVERY_ACM_TRACE_LIMIT + 4):
            trace.record(
                MODULE.RecoveryAcmObservation(
                    "absent" if index % 2 else "product-mismatch"
                )
            )
        summary = trace.summary()
        self.assertIn("identity_changes=path,rdev,devpath,id-path,serial", summary)
        self.assertIn("transitions_truncated=yes", summary)
        self.assertLessEqual(
            len(trace.transitions), MODULE.RECOVERY_ACM_TRACE_LIMIT
        )
        for secret in ("secret-a", "secret-b", "ttyACM"):
            self.assertNotIn(secret, summary)

    def test_recovery_acm_trace_counts_saturate_and_empty_summary_is_fixed(self):
        empty = MODULE.RecoveryAcmTrace().summary()
        self.assertEqual(
            empty,
            "states=none; transitions=none; identity_changes=none; "
            "transitions_truncated=no",
        )
        trace = MODULE.RecoveryAcmTrace()
        for _ in range(MODULE.RECOVERY_ACM_COUNT_LIMIT + 10):
            trace.record(MODULE.RecoveryAcmObservation("absent"))
        self.assertEqual(
            trace.counts["absent"], MODULE.RECOVERY_ACM_COUNT_LIMIT
        )
        self.assertEqual(trace.transitions, ["absent"])
        self.assertLess(len(trace.summary()), 160)

    def test_stability_timeout_includes_bounded_non_sensitive_classifier(self):
        observations = (
            MODULE.RecoveryAcmObservation("absent"),
            MODULE.RecoveryAcmObservation(
                "exact", ("/dev/ttyACM-secret", 1, "dev", "path", "serial")
            ),
        )
        with (
            mock.patch.object(
                MODULE, "observe_recovery_acm", side_effect=observations
            ),
            mock.patch.object(
                MODULE.time,
                "monotonic",
                side_effect=(0.0, 0.0, 0.0, 0.1, 0.1, 0.2),
            ),
            mock.patch.object(MODULE.time, "sleep"),
            self.assertRaisesRegex(
                RuntimeError,
                r"states=absent:1,exact:1; transitions=absent>exact",
            ) as failure,
        ):
            MODULE.wait_for_stable_recovery_acm(
                settle_seconds=2.0,
                timeout_seconds=0.15,
                poll_seconds=0.01,
            )
        self.assertNotIn("ttyACM-secret", str(failure.exception))

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
        on_prepared=None,
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
                    on_prepared=on_prepared,
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

    def test_prepared_response_is_observable_before_precommit_failure(self):
        def refuse():
            raise RuntimeError("NFS not ready")

        output = io.StringIO()
        with (
            redirect_stdout(output),
            self.assertRaisesRegex(RuntimeError, "NFS not ready"),
        ):
            self.pty_transaction(
                before_commit=refuse,
                on_prepared=MODULE.show_response,
            )
        lines = output.getvalue().splitlines()
        self.assertEqual(len(lines), 1)
        self.assertEqual(json.loads(lines[0])["result"], "PREPARED")
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
            mock.patch.object(
                MODULE,
                "prepare_and_commit",
                side_effect=RuntimeError("unexpected device discovery"),
            ),
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
            mock.patch.object(
                MODULE,
                "prepare_and_commit",
                side_effect=RuntimeError("unexpected device discovery"),
            ),
            self.assertRaisesRegex(
                RuntimeError,
                "ROG5_NFS_PACKAGE_SHA256",
            ),
        ):
            MODULE.main(
                ["prepare-commit", DEPLOYMENT_BUNDLE, MANIFEST]
            )
        ready.assert_not_called()

    def test_diagnostic_profile_precedes_device_discovery(self):
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
            mock.patch.object(
                MODULE,
                "prepare_and_commit",
                side_effect=RuntimeError("unexpected device discovery"),
            ),
            self.assertRaisesRegex(RuntimeError, "ROG5_NFS_PROFILE"),
        ):
            MODULE.main(
                ["prepare-commit", DIAGNOSTIC_BUNDLE, MANIFEST]
            )
        ready.assert_not_called()

    def test_diagnostic_package_identity_precedes_device_discovery(self):
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
            mock.patch.object(
                MODULE,
                "prepare_and_commit",
                side_effect=RuntimeError("unexpected device discovery"),
            ),
            self.assertRaisesRegex(
                RuntimeError,
                "ROG5_NFS_PACKAGE_SHA256",
            ),
        ):
            MODULE.main(
                ["prepare-commit", DIAGNOSTIC_BUNDLE, MANIFEST]
            )
        ready.assert_not_called()

    def test_diagnostic_handoff_binds_v3_profile_package_and_bundle(self):
        with (
            mock.patch.dict(
                os.environ,
                {
                    "ALLOW_STABLE_RECOVERY_CONTROL": "1",
                    "ALLOW_ATTENDED_KEXEC": "1",
                    "ALLOW_NETWORK_ROOT_NFS_HANDOFF": "1",
                    "ROG5_NFS_HANDOFF_TOKEN": HANDOFF_TOKEN,
                    "ROG5_NFS_PROFILE": DEPLOYMENT_PROFILE,
                    "ROG5_NFS_PACKAGE_SHA256": PACKAGE_SHA256,
                },
                clear=True,
            ),
            mock.patch.object(MODULE, "ensure_host_ready"),
            mock.patch.object(
                MODULE,
                "prepare_and_commit",
                side_effect=RuntimeError("captured handoff"),
            ) as transaction,
            self.assertRaisesRegex(RuntimeError, "captured handoff"),
        ):
            MODULE.main(
                ["prepare-commit", DIAGNOSTIC_BUNDLE, MANIFEST]
            )
        callback = transaction.call_args.kwargs["before_commit"]
        self.assertIsNotNone(callback)
        with mock.patch.object(
            MODULE,
            "wait_for_network_root_nfs",
        ) as wait:
            callback()
        wait.assert_called_once_with(
            HANDOFF_TOKEN,
            bundle=DIAGNOSTIC_BUNDLE,
            package_sha256=PACKAGE_SHA256,
        )

    def test_unknown_bundle_cannot_request_nfs_before_device_discovery(self):
        for guard_value in ("1", "0", ""):
            with self.subTest(guard_value=guard_value):
                with (
                    mock.patch.dict(
                        os.environ,
                        {
                            "ALLOW_STABLE_RECOVERY_CONTROL": "1",
                            "ALLOW_ATTENDED_KEXEC": "1",
                            "ALLOW_NETWORK_ROOT_NFS_HANDOFF": guard_value,
                            "ROG5_NFS_HANDOFF_TOKEN": HANDOFF_TOKEN,
                        },
                        clear=True,
                    ),
                    mock.patch.object(MODULE, "ensure_host_ready") as ready,
                    mock.patch.object(
                        MODULE,
                        "prepare_and_commit",
                        side_effect=RuntimeError("unexpected device discovery"),
                    ),
                    self.assertRaisesRegex(
                        RuntimeError,
                        "does not permit network-root NFS handoff",
                    ),
                ):
                    MODULE.main(
                        ["prepare-commit", "unknown-bundle", MANIFEST]
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

    def test_diagnostic_readiness_passes_exact_bundle_and_package_to_marker(self):
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
                    DIAGNOSTIC_BUNDLE,
                    PACKAGE_SHA256,
                )
            )
        marker.assert_called_once_with(
            HANDOFF_TOKEN,
            DIAGNOSTIC_BUNDLE,
            PACKAGE_SHA256,
        )

    def test_diagnostic_marker_matches_exact_v3_handoff_bytes(self):
        marker_bytes = (
            "format=rog5-nfs-handoff-v2\n"
            f"profile={DEPLOYMENT_PROFILE}\n"
            f"token={HANDOFF_TOKEN}\n"
            "listener=169.254.77.1:2049\n"
            "versions=4.2-only\n"
            f"export_root={MODULE.DEPLOYMENT_NFS_HANDOFF_ROOT}\n"
            f"package_sha256={PACKAGE_SHA256}\n"
        ).encode("ascii")
        marker_path = Path(self.temporary.name) / "nfs-ready"
        marker_path.write_bytes(marker_bytes)
        metadata = mock.Mock(
            st_mode=stat.S_IFREG | 0o444,
            st_uid=0,
            st_gid=0,
            st_nlink=1,
            st_size=len(marker_bytes),
        )
        with (
            mock.patch.object(MODULE, "NFS_HANDOFF_MARKER", marker_path),
            mock.patch.object(MODULE.os, "fstat", return_value=metadata),
        ):
            self.assertTrue(
                MODULE.nfs_handoff_marker_matches(
                    HANDOFF_TOKEN,
                    DIAGNOSTIC_BUNDLE,
                    PACKAGE_SHA256,
                )
            )
            self.assertFalse(
                MODULE.nfs_handoff_marker_matches(
                    HANDOFF_TOKEN,
                    DIAGNOSTIC_BUNDLE,
                    "0" * 64,
                )
            )
            self.assertFalse(
                MODULE.nfs_handoff_marker_matches(
                    HANDOFF_TOKEN,
                    DIAGNOSTIC_BUNDLE,
                    "not-a-sha256",
                )
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
