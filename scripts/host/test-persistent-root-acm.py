#!/usr/bin/env python3
"""Regression tests for the fixed P2 recovery-ACM actions."""

from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import unittest
from unittest import mock


sys.dont_write_bytecode = True
SOURCE = Path(__file__).with_name("persistent-root-acm.py")
SPEC = importlib.util.spec_from_file_location("rog5_persistent_root_acm", SOURCE)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class PersistentRootAcmTest(unittest.TestCase):
    def test_load_is_exact_and_retries_only_once(self) -> None:
        missing = MODULE.TRANSPORT.MissingLoadMarkerError("synthetic race")
        with (
            mock.patch.object(
                MODULE.TRANSPORT,
                "wait_for_stable_recovery_acm",
                side_effect=["/dev/ttyACM0", "/dev/ttyACM1"],
            ) as wait,
            mock.patch.object(
                MODULE.TRANSPORT,
                "run_serial",
                side_effect=[missing, MODULE.LOAD_MARKER.decode() + "\n"],
            ) as run,
        ):
            output = MODULE.load_persistent_root()
        self.assertEqual(output, MODULE.LOAD_MARKER.decode() + "\n")
        self.assertEqual(wait.call_count, 2)
        self.assertEqual(run.call_count, 2)
        for index, path in enumerate(("/dev/ttyACM0", "/dev/ttyACM1")):
            self.assertEqual(
                run.call_args_list[index].args,
                (
                    path,
                    MODULE.LOAD_COMMAND,
                    MODULE.LOAD_MARKER,
                    False,
                    60,
                ),
            )

    def test_second_missing_marker_is_terminal(self) -> None:
        missing = MODULE.TRANSPORT.MissingLoadMarkerError("synthetic race")
        with (
            mock.patch.object(
                MODULE.TRANSPORT,
                "wait_for_stable_recovery_acm",
                side_effect=["/dev/ttyACM0", "/dev/ttyACM1"],
            ),
            mock.patch.object(
                MODULE.TRANSPORT,
                "run_serial",
                side_effect=[missing, missing],
            ) as run,
        ):
            with self.assertRaises(MODULE.TRANSPORT.MissingLoadMarkerError):
                MODULE.load_persistent_root()
        self.assertEqual(run.call_count, 2)

    def test_execute_is_exact_and_never_retried(self) -> None:
        with (
            mock.patch.object(
                MODULE.TRANSPORT,
                "wait_for_stable_recovery_acm",
                return_value="/dev/ttyACM0",
            ) as wait,
            mock.patch.object(
                MODULE.TRANSPORT,
                "run_serial",
                return_value="",
            ) as run,
        ):
            self.assertEqual(MODULE.execute_persistent_root(), "")
        wait.assert_called_once_with()
        run.assert_called_once_with("/dev/ttyACM0", "kexec -e", None, True, 20)

    def test_preflight_is_fixed_read_only_and_bounded(self) -> None:
        with (
            mock.patch.object(
                MODULE.TRANSPORT,
                "wait_for_stable_recovery_acm",
                return_value="/dev/ttyACM0",
            ),
            mock.patch.object(
                MODULE.TRANSPORT,
                "run_serial",
                return_value=MODULE.PREFLIGHT_MARKER.decode() + "\n",
            ) as run,
        ):
            output = MODULE.preflight_persistent_root()
        self.assertEqual(output, MODULE.PREFLIGHT_MARKER.decode() + "\n")
        run.assert_called_once_with(
            "/dev/ttyACM0",
            MODULE.PREFLIGHT_COMMAND,
            MODULE.PREFLIGHT_MARKER,
            False,
            60,
        )
        self.assertIn('/sys/kernel/kexec_loaded)" = 1', MODULE.PREFLIGHT_COMMAND)
        self.assertIn("sha256sum -c SHA256SUMS", MODULE.PREFLIGHT_COMMAND)
        self.assertIn('block_mounts" = 0', MODULE.PREFLIGHT_COMMAND)

    def test_load_guard_fails_before_device_discovery(self) -> None:
        environment = os.environ.copy()
        environment.pop("ALLOW_PERSISTENT_ROOT_ACM", None)
        result = subprocess.run(
            [sys.executable, SOURCE, "load"],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=environment,
            text=True,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("ALLOW_PERSISTENT_ROOT_ACM", result.stderr)

    def test_execute_guard_fails_before_device_discovery(self) -> None:
        environment = os.environ.copy()
        environment["ALLOW_PERSISTENT_ROOT_ACM"] = "1"
        environment.pop("ALLOW_ATTENDED_KEXEC", None)
        result = subprocess.run(
            [sys.executable, SOURCE, "execute"],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=environment,
            text=True,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("ALLOW_ATTENDED_KEXEC", result.stderr)

    def test_source_has_no_persistent_write_or_credential_path(self) -> None:
        source = SOURCE.read_text()
        self.assertEqual(
            MODULE.LOAD_COMMAND,
            "ROG5_RECOVERY_TIMEOUT=600 "
            "/usr/local/sbin/rog5-load-mainline-recovery",
        )
        self.assertNotRegex(source, r"fastboot\s+flash|dd\s+.*of=/dev/")
        self.assertNotRegex(source, r"BEGIN .*PRIVATE KEY|authorized_keys")
        self.assertNotRegex(MODULE.PREFLIGHT_COMMAND, r"\bmount\b|\bdd\b")
        self.assertIn("network-root-acm.py", source)
        self.assertIn("ALLOW_ATTENDED_KEXEC", source)


if __name__ == "__main__":
    unittest.main(verbosity=2)
