#!/usr/bin/env python3
"""Offline tests for the privilege-separated recovery progress runtime."""

from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import stat
import tempfile
import unittest
from unittest import mock


REPO = Path(__file__).resolve().parents[2]
RUNTIME_PATH = (
    REPO / "packaging/host/rog5-recovery-progress-collector.py"
)
SPEC = importlib.util.spec_from_file_location(
    "rog5_recovery_progress_runtime",
    RUNTIME_PATH,
)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("cannot load recovery progress runtime")
runtime = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runtime)


BUNDLE = "arch-test-v1"
MANIFEST = "a" * 64


class RecoveryProgressRuntimeTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(
            prefix="rog5-progress-runtime-test-"
        )
        self.root = Path(self.temporary.name)
        self.root.chmod(0o700)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def arguments(self) -> list[str]:
        return [
            "enp4s0f3u1u2",
            BUNDLE,
            MANIFEST,
            str(self.root),
            str(os.geteuid()),
            str(os.getegid()),
            "250",
            str(self.root / "bundle.eof"),
            str(os.getppid()),
        ]

    def test_argument_surface_is_fixed_and_canonical(self):
        if os.geteuid() == 0 or os.getegid() == 0:
            self.skipTest("argument fixture requires a non-root test user")
        parsed = runtime.validate_arguments(self.arguments())
        self.assertEqual(parsed[:3], ("enp4s0f3u1u2", BUNDLE, MANIFEST))
        for index, mutation in (
            (0, "usb/0"),
            (1, "../escape"),
            (2, "0" * 64),
            (3, "/tmp/../escape"),
            (4, "0"),
            (5, "0"),
            (6, "301"),
            (7, "/tmp/../escape"),
            (8, "1"),
        ):
            arguments = self.arguments()
            arguments[index] = mutation
            with self.subTest(index=index), self.assertRaises(
                runtime.CollectorError
            ):
                runtime.validate_arguments(arguments)

    def test_output_directory_is_opened_once_by_descriptor(self):
        descriptor, identity = runtime.open_output_directory(
            self.root,
            os.geteuid(),
            os.getegid(),
        )
        try:
            self.assertEqual(identity.st_ino, os.fstat(descriptor).st_ino)
            output = runtime.open_output(
                descriptor,
                identity,
                os.geteuid(),
                os.getegid(),
            )
            try:
                metadata = os.fstat(output)
                self.assertEqual(stat.S_IMODE(metadata.st_mode), 0o600)
                self.assertEqual(metadata.st_nlink, 1)
            finally:
                os.close(output)
        finally:
            os.close(descriptor)

    def test_output_path_replacement_and_existing_name_refuse(self):
        outside = self.root.parent / f"{self.root.name}-outside"
        outside.mkdir(mode=0o700)
        self.addCleanup(outside.rmdir)
        alias = self.root / "alias"
        alias.symlink_to(outside)
        with self.assertRaises(runtime.CollectorError):
            runtime.open_output_directory(
                alias,
                os.geteuid(),
                os.getegid(),
            )
        (self.root / runtime.OUTPUT_NAME).write_bytes(b"existing")
        with self.assertRaisesRegex(runtime.CollectorError, "already exists"):
            runtime.open_output_directory(
                self.root,
                os.geteuid(),
                os.getegid(),
            )

    def test_privilege_drop_order_and_irreversibility_are_explicit(self):
        uid = 1001
        gid = 1002
        status = {
            "Uid": f"{uid}\t{uid}\t{uid}\t{uid}",
            "Gid": f"{gid}\t{gid}\t{gid}\t{gid}",
            "Groups": "",
            "NoNewPrivs": "1",
            "CapInh": "0000000000000000",
            "CapPrm": "0000000000000000",
            "CapEff": "0000000000000000",
            "CapBnd": "0000000000000000",
            "CapAmb": "0000000000000000",
        }
        calls: list[tuple[int, int, int]] = []

        def setresuid(real: int, effective: int, saved: int) -> None:
            calls.append((real, effective, saved))
            if real == 0:
                raise PermissionError

        with (
            mock.patch.object(runtime.os, "geteuid", return_value=0),
            mock.patch.object(runtime.Path, "read_text", return_value="2\n"),
            mock.patch.object(runtime, "prctl") as prctl,
            mock.patch.object(runtime.os, "setgroups") as setgroups,
            mock.patch.object(runtime.os, "setresgid") as setresgid,
            mock.patch.object(runtime.os, "setresuid", side_effect=setresuid),
            mock.patch.object(runtime, "process_status", return_value=status),
        ):
            runtime.drop_privileges(uid, gid)
        self.assertEqual(
            prctl.call_args_list,
            [
                mock.call(runtime.PR_SET_NO_NEW_PRIVS, 1),
                mock.call(runtime.PR_CAPBSET_DROP, 0),
                mock.call(runtime.PR_CAPBSET_DROP, 1),
                mock.call(runtime.PR_CAPBSET_DROP, 2),
                mock.call(
                    runtime.PR_CAP_AMBIENT,
                    runtime.PR_CAP_AMBIENT_CLEAR_ALL,
                ),
            ],
        )
        setgroups.assert_called_once_with([])
        setresgid.assert_called_once_with(gid, gid, gid)
        self.assertEqual(calls, [(uid, uid, uid), (0, 0, 0)])

    def test_parent_death_signal_is_armed_and_identity_checked(self):
        parent = os.getppid()
        with (
            mock.patch.object(runtime, "prctl") as prctl,
            mock.patch.object(runtime.os, "getppid", return_value=parent),
        ):
            runtime.arm_parent_death(parent)
        prctl.assert_called_once_with(
            runtime.PR_SET_PDEATHSIG,
            runtime.signal.SIGTERM,
        )
        with (
            mock.patch.object(runtime, "prctl"),
            mock.patch.object(runtime.os, "getppid", return_value=parent + 1),
            self.assertRaisesRegex(runtime.CollectorError, "parent changed"),
        ):
            runtime.arm_parent_death(parent)

    def test_success_publishes_one_private_authority_free_record(self):
        if os.geteuid() == 0 or os.getegid() == 0:
            self.skipTest("runtime fixture requires a non-root test user")
        listener = mock.MagicMock()
        capture = runtime.partial_capture(BUNDLE, MANIFEST, "NO_ADMISSION")
        with (
            mock.patch.object(
                runtime,
                "open_fixed_listener",
                return_value=listener,
            ),
            mock.patch.object(runtime, "drop_privileges"),
            mock.patch.object(runtime, "arm_parent_death") as parent_death,
            mock.patch.object(
                runtime,
                "collect_listener",
                return_value=capture,
            ),
        ):
            self.assertEqual(runtime.run(self.arguments()), 0)
        self.assertEqual(parent_death.call_count, 2)
        output = self.root / runtime.OUTPUT_NAME
        metadata = output.lstat()
        self.assertEqual(stat.S_IMODE(metadata.st_mode), 0o600)
        payload = output.read_text(encoding="ascii")
        self.assertIn("result=PARTIAL\n", payload)
        self.assertIn("reason=NO_ADMISSION\n", payload)
        self.assertIn("authority=NONE\n", payload)
        listener.close.assert_called()

    def test_refusal_is_demoted_to_non_authoritative_partial_evidence(self):
        if os.geteuid() == 0 or os.getegid() == 0:
            self.skipTest("runtime fixture requires a non-root test user")
        listener = mock.MagicMock()
        with (
            mock.patch.object(
                runtime,
                "open_fixed_listener",
                return_value=listener,
            ),
            mock.patch.object(runtime, "drop_privileges"),
            mock.patch.object(runtime, "arm_parent_death") as parent_death,
            mock.patch.object(
                runtime,
                "collect_listener",
                side_effect=runtime.CollectorRefusal(
                    "progress admission stopped"
                ),
            ),
        ):
            self.assertEqual(runtime.run(self.arguments()), 0)
        self.assertEqual(parent_death.call_count, 2)
        payload = (self.root / runtime.OUTPUT_NAME).read_text(
            encoding="ascii"
        )
        self.assertIn("reason=NO_ADMISSION\n", payload)
        self.assertIn("authority=NONE\n", payload)

    def test_stream_refusal_preserves_observed_wire_identity(self):
        if os.geteuid() == 0 or os.getegid() == 0:
            self.skipTest("runtime fixture requires a non-root test user")
        listener = mock.MagicMock()
        observed = runtime.ProgressCapture(
            session="1" * 32,
            request="2" * 32,
            bundle=BUNDLE,
            manifest_sha256=MANIFEST,
            phases=("REQUEST_ACCEPTED",),
            wire_bytes=37,
            wire_sha256="b" * 64,
            result="PARTIAL",
            truncated=True,
            reason="INVALID_RECORD",
        )
        with (
            mock.patch.object(
                runtime,
                "open_fixed_listener",
                return_value=listener,
            ),
            mock.patch.object(runtime, "drop_privileges"),
            mock.patch.object(runtime, "arm_parent_death"),
            mock.patch.object(
                runtime,
                "collect_listener",
                side_effect=runtime.CollectorRefusal(
                    "invalid progress record",
                    capture=observed,
                ),
            ),
        ):
            self.assertEqual(runtime.run(self.arguments()), 0)
        payload = (self.root / runtime.OUTPUT_NAME).read_text(
            encoding="ascii"
        )
        self.assertIn("wire_bytes=37\n", payload)
        self.assertIn(f"wire_sha256={'b' * 64}\n", payload)
        self.assertIn("reason=INVALID_RECORD\n", payload)
        self.assertIn("authority=NONE\n", payload)


if __name__ == "__main__":
    unittest.main()
