#!/usr/bin/env python3
"""Pseudoterminal regression for the control-safe ROG5 staging transport."""

from __future__ import annotations

import importlib.util
import os
import pathlib
import pty
import subprocess
import sys
import threading
import unittest


sys.dont_write_bytecode = True
SOURCE = pathlib.Path(__file__).with_name("network-root-acm.py")
SPEC = importlib.util.spec_from_file_location("network_root_acm", SOURCE)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def read_line(fd: int) -> bytes:
    data = bytearray()
    while not data.endswith(b"\n"):
        data.extend(os.read(fd, 1))
    return bytes(data)


class SerialTransportTest(unittest.TestCase):
    def run_emulator(
        self,
        command: str,
        response: bytes,
        *,
        expect_disconnect: bool,
        marker: bytes | None,
    ) -> tuple[str, bytes]:
        master, slave = pty.openpty()
        slave_path = os.ttyname(slave)
        received = bytearray()

        def emulate() -> None:
            received.extend(read_line(master))
            if response:
                os.write(master, response)
            if expect_disconnect:
                os.close(master)

        thread = threading.Thread(target=emulate)
        thread.start()
        try:
            output = MODULE.run_serial(
                slave_path,
                command,
                marker,
                expect_disconnect,
                5,
                settle_seconds=0,
            )
        finally:
            os.close(slave)
            if not expect_disconnect:
                os.close(master)
            thread.join(timeout=5)
        self.assertFalse(thread.is_alive())
        return output, bytes(received)

    def test_loader_strips_dsr_without_replying(self) -> None:
        command = MODULE.ACTIONS["load-normal"][0]
        response = (
            b"\x1b[6n"
            + command.encode()
            + b"\r\nImage: OK\r\nboard.dtb: OK\r\ninitramfs.cpio.gz: OK\r\n"
            + MODULE.LOAD_MARKER
            + b"\r\n~ # \x1b[6n"
        )
        output, received = self.run_emulator(
            command,
            response,
            expect_disconnect=False,
            marker=MODULE.LOAD_MARKER,
        )
        self.assertEqual(received, (command + "\n").encode())
        self.assertNotIn("\x1b", output)
        self.assertIn(MODULE.LOAD_MARKER.decode(), output)

    def test_execute_requires_acm_disconnect(self) -> None:
        command = MODULE.ACTIONS["execute"][0]
        output, received = self.run_emulator(
            command,
            b"",
            expect_disconnect=True,
            marker=None,
        )
        self.assertEqual(received, b"kexec -e\n")
        self.assertEqual(output, "")

    def test_missing_guard_fails_before_device_discovery(self) -> None:
        environment = os.environ.copy()
        environment.pop("ALLOW_NETWORK_ROOT_ACM", None)
        result = subprocess.run(
            [sys.executable, SOURCE, "load-normal"],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=environment,
            text=True,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("ALLOW_NETWORK_ROOT_ACM", result.stderr)

    def test_actions_are_fixed_and_storage_safe(self) -> None:
        self.assertEqual(set(MODULE.ACTIONS), {"load-normal", "load-diagnostic", "execute"})
        self.assertEqual(MODULE.ACTIONS["execute"][0], "kexec -e")
        source = SOURCE.read_text()
        self.assertNotRegex(source, r"fastboot\s+flash|dd\s+.*of=/dev/")
        self.assertNotIn("socat", source)
        self.assertIn("ID_MODEL_ID", source)
        self.assertIn("ROG5_recovery", source)
        self.assertIn("os.O_NOCTTY", source)
        self.assertIn("ALLOW_ATTENDED_KEXEC", source)
        recovery = SOURCE.with_name("recovery-linux.sh").read_text()
        self.assertIn("network-root-acm.py load-normal", recovery)
        self.assertNotIn("socat -,rawer", recovery)


if __name__ == "__main__":
    unittest.main(verbosity=2)
