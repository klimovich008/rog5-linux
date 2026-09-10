#!/usr/bin/env python3
"""Regression tests for the receive-only P2 early-entry ACM oracle."""

from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import pty
import select
import subprocess
import sys
import termios
import threading
import tty
import unittest
from unittest import mock


sys.dont_write_bytecode = True
SOURCE = Path(__file__).with_name("persistent-root-entry-acm.py")
if not SOURCE.is_file():
    raise SystemExit(f"FAIL missing receive-only entry ACM reader: {SOURCE}")
SPEC = importlib.util.spec_from_file_location("rog5_p2_entry_acm", SOURCE)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class PersistentRootEntryAcmTest(unittest.TestCase):
    def run_emulator(self, payload: bytes) -> tuple[str, bytes]:
        master, slave = pty.openpty()
        slave_path = os.ttyname(slave)
        tty.setraw(slave, termios.TCSANOW)

        def emulate() -> None:
            midpoint = len(payload) // 2
            os.write(master, payload[:midpoint])
            os.write(master, payload[midpoint:])

        thread = threading.Thread(target=emulate)
        thread.start()
        try:
            output = MODULE.read_entry_marker(
                slave_path,
                timeout_seconds=5,
            )
            ready, _, _ = select.select([master], [], [], 0)
            received = os.read(master, 4096) if ready else b""
        finally:
            os.close(slave)
            os.close(master)
            thread.join(timeout=5)
        self.assertFalse(thread.is_alive())
        return output, received

    def test_exact_marker_is_received_without_transmitting_a_command(self) -> None:
        payload = (
            b"partial old record\n"
            + MODULE.EXPECTED_MARKER
            + MODULE.EXPECTED_MARKER
        )
        output, received = self.run_emulator(payload)
        self.assertEqual(output, MODULE.EXPECTED_MARKER.decode())
        self.assertEqual(received, b"")

    def test_mismatched_marker_is_rejected(self) -> None:
        payload = MODULE.EXPECTED_MARKER.replace(
            b"block_backed_mounts=0",
            b"block_backed_mounts=1",
            1,
        ).replace(
            MODULE.PASS_LINE,
            MODULE.FAIL_LINE,
            1,
        )
        with self.assertRaises(MODULE.EntryMarkerRejectedError):
            self.run_emulator(payload)

    def test_missing_marker_times_out(self) -> None:
        master, slave = pty.openpty()
        try:
            os.write(master, b"unrelated output\n")
            with self.assertRaises(MODULE.MissingEntryMarkerError):
                MODULE.read_entry_marker(
                    os.ttyname(slave),
                    timeout_seconds=0.05,
                )
        finally:
            os.close(slave)
            os.close(master)

    def test_entry_identity_is_exact_and_read_only_is_sufficient(self) -> None:
        expected = {
            "ID_VENDOR_ID": "1d6b",
            "ID_MODEL_ID": "0104",
            "ID_MODEL": "ROG5_P2_entry_oracle",
        }
        with (
            mock.patch.object(
                MODULE.glob,
                "glob",
                return_value=["/dev/ttyACM7"],
            ),
            mock.patch.object(
                MODULE.TRANSPORT,
                "udev_properties",
                return_value=expected,
            ),
            mock.patch.object(
                MODULE.os,
                "stat",
                return_value=mock.Mock(st_mode=0o020600),
            ),
            mock.patch.object(MODULE.stat, "S_ISCHR", return_value=True),
            mock.patch.object(MODULE.os, "access", return_value=True) as access,
        ):
            self.assertEqual(MODULE.find_entry_acm(), "/dev/ttyACM7")
        access.assert_called_once_with("/dev/ttyACM7", os.R_OK)

    def test_acm_must_stabilize_after_reenumeration(self) -> None:
        paths = [
            "/dev/ttyACM0",
            RuntimeError("device departed"),
            "/dev/ttyACM1",
            "/dev/ttyACM1",
            "/dev/ttyACM1",
        ]

        def identity(path: str) -> tuple[str, int, str, str, str]:
            return (path, 16640 if path.endswith("0") else 16641, "", "", "")

        with (
            mock.patch.object(MODULE, "find_entry_acm", side_effect=paths),
            mock.patch.object(MODULE, "entry_acm_identity", side_effect=identity),
            mock.patch.object(
                MODULE.time,
                "monotonic",
                side_effect=[0.0, 0.0, 0.1, 0.2, 0.3],
            ),
            mock.patch.object(MODULE.time, "sleep"),
        ):
            path = MODULE.wait_for_stable_entry_acm(
                settle_seconds=0.05,
                timeout_seconds=1.0,
                poll_seconds=0.0,
            )
        self.assertEqual(path, "/dev/ttyACM1")

    def test_entrypoint_is_retired_before_device_discovery(self) -> None:
        with (
            mock.patch.object(MODULE.os, "uname") as uname,
            mock.patch.object(MODULE.shutil, "which") as which,
            mock.patch.object(MODULE.subprocess, "run") as run,
            mock.patch.object(MODULE, "wait_for_stable_entry_acm") as wait,
        ):
            with self.assertRaisesRegex(RuntimeError, "legacy interactive ACM"):
                MODULE.main(["read"])
        uname.assert_not_called()
        which.assert_not_called()
        run.assert_not_called()
        wait.assert_not_called()

    def test_source_has_no_transmit_or_credential_path(self) -> None:
        source = SOURCE.read_text()
        self.assertNotIn("os.write(", source)
        self.assertNotIn("write_all", source)
        self.assertNotIn("authorized_keys", source)
        self.assertNotRegex(source, r"fastboot\s+flash|dd\s+.*of=/dev/")
        self.assertIn("os.O_RDONLY", source)
        self.assertIn("ROG5_P2_entry_oracle", source)


if __name__ == "__main__":
    unittest.main(verbosity=2)
