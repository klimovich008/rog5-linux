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
from unittest import mock


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

    def test_atomic_confirmation_requires_kexec_guard_before_discovery(self) -> None:
        environment = os.environ.copy()
        environment["ALLOW_NETWORK_ROOT_ACM"] = "1"
        environment.pop("ALLOW_ATTENDED_KEXEC", None)
        result = subprocess.run(
            [sys.executable, SOURCE, "confirm-gpucc"],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=environment,
            text=True,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("ALLOW_ATTENDED_KEXEC", result.stderr)

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
            mock.patch.object(MODULE, "find_recovery_acm", side_effect=paths),
            mock.patch.object(MODULE, "recovery_acm_identity", side_effect=identity),
            mock.patch.object(
                MODULE.time,
                "monotonic",
                side_effect=[0.0, 0.0, 0.1, 0.2, 0.3],
            ),
            mock.patch.object(MODULE.time, "sleep"),
        ):
            path = MODULE.wait_for_stable_recovery_acm(
                settle_seconds=0.05,
                timeout_seconds=1.0,
                poll_seconds=0.0,
            )
        self.assertEqual(path, "/dev/ttyACM1")

    def test_load_retries_once_after_marker_race(self) -> None:
        with (
            mock.patch.object(
                MODULE,
                "wait_for_stable_recovery_acm",
                side_effect=["/dev/ttyACM0", "/dev/ttyACM1"],
            ) as wait,
            mock.patch.object(
                MODULE,
                "run_serial",
                side_effect=[
                    MODULE.MissingLoadMarkerError(
                        "expected staging PASS marker was not observed"
                    ),
                    MODULE.LOAD_MARKER.decode() + "\n",
                ],
            ) as run,
        ):
            output = MODULE.run_fixed_action("load-gpucc-diagnostic")
        self.assertEqual(output, MODULE.LOAD_MARKER.decode() + "\n")
        self.assertEqual(wait.call_count, 2)
        self.assertEqual(run.call_count, 2)
        self.assertEqual(run.call_args_list[0].args[0], "/dev/ttyACM0")
        self.assertEqual(run.call_args_list[1].args[0], "/dev/ttyACM1")
        self.assertEqual(run.call_args_list[0].args[1:], run.call_args_list[1].args[1:])

    def test_load_retry_replays_same_command_on_two_real_ptys(self) -> None:
        command = MODULE.ACTIONS["load-normal"][0]
        endpoints = [pty.openpty(), pty.openpty()]
        paths = [os.ttyname(slave) for _, slave in endpoints]
        received = [bytearray(), bytearray()]
        release_second = threading.Event()

        def emulate(index: int, response: bytes) -> None:
            master, _ = endpoints[index]
            received[index].extend(read_line(master))
            if response:
                os.write(master, response)
                release_second.wait(timeout=5)
            os.close(master)

        threads = [
            threading.Thread(target=emulate, args=(0, b"")),
            threading.Thread(
                target=emulate,
                args=(1, MODULE.LOAD_MARKER + b"\r\n"),
            ),
        ]
        for thread in threads:
            thread.start()
        try:
            with mock.patch.object(
                MODULE,
                "wait_for_stable_recovery_acm",
                side_effect=paths,
            ):
                output = MODULE.run_fixed_action("load-normal")
        finally:
            release_second.set()
            for _, slave in endpoints:
                os.close(slave)
            for thread in threads:
                thread.join(timeout=5)

        self.assertTrue(all(not thread.is_alive() for thread in threads))
        self.assertEqual(
            [bytes(value) for value in received],
            [(command + "\n").encode()] * 2,
        )
        self.assertIn(MODULE.LOAD_MARKER.decode(), output)

    def test_load_retry_is_bounded_to_one(self) -> None:
        missing = MODULE.MissingLoadMarkerError(
            "expected staging PASS marker was not observed"
        )
        with (
            mock.patch.object(
                MODULE,
                "wait_for_stable_recovery_acm",
                side_effect=["/dev/ttyACM0", "/dev/ttyACM1"],
            ) as wait,
            mock.patch.object(
                MODULE,
                "run_serial",
                side_effect=[missing, missing],
            ) as run,
        ):
            with self.assertRaises(MODULE.MissingLoadMarkerError):
                MODULE.run_fixed_action("load-normal")
        self.assertEqual(wait.call_count, 2)
        self.assertEqual(run.call_count, 2)

    def test_execute_is_never_retried(self) -> None:
        with (
            mock.patch.object(
                MODULE,
                "wait_for_stable_recovery_acm",
                return_value="/dev/ttyACM0",
            ) as wait,
            mock.patch.object(
                MODULE,
                "run_serial",
                side_effect=MODULE.MissingLoadMarkerError("synthetic failure"),
            ) as run,
        ):
            with self.assertRaises(MODULE.MissingLoadMarkerError):
                MODULE.run_fixed_action("execute")
        wait.assert_called_once_with()
        run.assert_called_once()

    def test_atomic_confirmation_loads_then_executes_without_gap(self) -> None:
        with mock.patch.object(
            MODULE,
            "run_fixed_action",
            side_effect=[MODULE.LOAD_MARKER.decode() + "\n", ""],
        ) as run:
            output = MODULE.run_fixed_sequence("confirm-gpucc")
        self.assertEqual(output, MODULE.LOAD_MARKER.decode() + "\n")
        self.assertEqual(
            [call.args[0] for call in run.call_args_list],
            ["load-gpucc-confirmation", "execute"],
        )

    def test_atomic_confirmation_never_executes_after_load_failure(self) -> None:
        failure = MODULE.MissingLoadMarkerError("synthetic load failure")
        with mock.patch.object(
            MODULE,
            "run_fixed_action",
            side_effect=failure,
        ) as run:
            with self.assertRaises(MODULE.MissingLoadMarkerError):
                MODULE.run_fixed_sequence("confirm-gpucc")
        run.assert_called_once_with("load-gpucc-confirmation")

    def test_actions_are_fixed_and_storage_safe(self) -> None:
        self.assertEqual(
            set(MODULE.ACTIONS),
            {
                "load-normal",
                "load-diagnostic",
                "load-gpucc-confirmation",
                "load-gpucc-diagnostic",
                "execute",
            },
        )
        self.assertEqual(
            MODULE.SEQUENCES,
            {"confirm-gpucc": ("load-gpucc-confirmation", "execute")},
        )
        self.assertEqual(
            MODULE.ACTIONS["load-gpucc-confirmation"][0],
            "ROG5_SYSTEMD_DIAGNOSTIC=1 ROG5_RECOVERY_TIMEOUT=900 "
            "/usr/local/sbin/rog5-load-mainline-recovery",
        )
        self.assertEqual(
            MODULE.ACTIONS["load-gpucc-diagnostic"][0],
            "ROG5_SYSTEMD_DIAGNOSTIC=1 ROG5_QCOM_CC_PROBE_TRACE=1 "
            "ROG5_CCF_REGISTER_TRACE=1 "
            "ROG5_RCG2_PARENT_TRACE=1 "
            "ROG5_RECOVERY_TIMEOUT=900 "
            "/usr/local/sbin/rog5-load-mainline-recovery",
        )
        self.assertEqual(MODULE.ACTIONS["execute"][0], "kexec -e")
        source = SOURCE.read_text()
        self.assertNotRegex(source, r"fastboot\s+flash|dd\s+.*of=/dev/")
        self.assertNotIn("socat", source)
        self.assertIn("ID_MODEL_ID", source)
        self.assertIn("ROG5_recovery", source)
        self.assertIn("os.O_NOCTTY", source)
        self.assertIn("ALLOW_ATTENDED_KEXEC", source)
        self.assertIn('if action == "execute":', source)
        self.assertIn("run_fixed_sequence", source)
        self.assertIn('"confirm-gpucc"', source)
        recovery = SOURCE.with_name("recovery-linux.sh").read_text()
        self.assertNotIn("network-root-acm.py", recovery)
        self.assertNotIn("ALLOW_ATTENDED_KEXEC=1", recovery)
        self.assertIn(
            "no payload execution is currently authorized",
            recovery,
        )
        self.assertIn("docs/recovery-control-plane.md", recovery)
        self.assertNotIn("socat", recovery)


if __name__ == "__main__":
    unittest.main(verbosity=2)
