#!/usr/bin/env python3
"""Hostile tests for the ROG5 early-target diagnostic stream."""

from __future__ import annotations

import array
import importlib.util
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
import unittest


SOURCE = Path(__file__).with_name("early-target-diagnostics.py")
SPEC = importlib.util.spec_from_file_location("early_target_diagnostics", SOURCE)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)

CANDIDATE = "headless-netroot-early-diag-v1"
BOOT = "12345678-1234-4abc-8def-1234567890ab"


def record(
    sequence: int = 1,
    stage_code: int = 10,
    *,
    boottime_ms: int | None = None,
    boot_id: str = BOOT,
    candidate: str = CANDIDATE,
    last_good_code: int | None = None,
    fault: str = "none",
    deadline: int = 600_000,
    dropped: int = 0,
):
    if boottime_ms is None:
        boottime_ms = sequence * 250
    if last_good_code is None:
        last_good_code = stage_code if stage_code <= 140 else 10
    return MODULE.DiagnosticRecord(
        candidate=candidate,
        boot_id=boot_id,
        sequence=sequence,
        boottime_ms=boottime_ms,
        stage_code=stage_code,
        stage=MODULE.STAGES[stage_code],
        last_good_code=last_good_code,
        fault=fault,
        watchdog_deadline_ms=deadline,
        dropped_updates=dropped,
    )


class EarlyTargetDiagnosticTest(unittest.TestCase):
    def test_every_progress_stage_round_trips(self):
        stream = MODULE.DiagnosticStream(CANDIDATE)
        payload = b"".join(
            MODULE.frame_for(record(index, code))
            for index, code in enumerate(
                sorted(MODULE.PROGRESS_CODES), 1
            )
        )
        accepted = stream.feed(payload)
        stream.finalize()
        self.assertEqual(
            [item.stage_code for item in accepted],
            sorted(MODULE.PROGRESS_CODES),
        )
        self.assertEqual(stream.maximum_progress, 140)

    def test_every_fault_reason_round_trips(self):
        for reason in sorted(MODULE.FAULTS - {"none"}):
            with self.subTest(reason=reason):
                stream = MODULE.DiagnosticStream(CANDIDATE)
                accepted = stream.feed(
                    MODULE.frame_for(
                        record(
                            stage_code=200,
                            last_good_code=70,
                            fault=reason,
                        )
                    )
                )
                self.assertEqual(accepted[0].fault, reason)

    def test_every_byte_split_reassembles(self):
        frame = MODULE.frame_for(record())
        for split in range(len(frame) + 1):
            with self.subTest(split=split):
                stream = MODULE.DiagnosticStream(CANDIDATE)
                accepted = stream.feed(frame[:split])
                accepted.extend(stream.feed(frame[split:]))
                stream.finalize()
                self.assertEqual(accepted, [record()])

    def test_coalesced_heartbeats_and_stage_repeat_pass(self):
        stream = MODULE.DiagnosticStream(CANDIDATE)
        frames = b"".join(
            MODULE.frame_for(record(index, 70))
            for index in range(1, 9)
        )
        self.assertEqual(len(stream.feed(frames)), 8)
        self.assertEqual(stream.maximum_progress, 70)

    def test_nfs_return_boundary_is_monotonic_between_begin_and_success(self):
        stream = MODULE.DiagnosticStream(CANDIDATE)
        accepted = stream.feed(
            b"".join(
                MODULE.frame_for(record(index, stage))
                for index, stage in enumerate((70, 75, 75, 80), 1)
            )
        )
        self.assertEqual(
            [item.stage for item in accepted],
            [
                "nfs-mount-begin",
                "nfs-mount-returned",
                "nfs-mount-returned",
                "nfs-mount-ok",
            ],
        )
        regressing = MODULE.DiagnosticStream(CANDIDATE)
        regressing.feed(MODULE.frame_for(record(1, 75)))
        with self.assertRaises(MODULE.DiagnosticError):
            regressing.feed(MODULE.frame_for(record(2, 70)))

    def test_deadline_is_absolute_but_remaining_interval_is_bounded(self):
        stream = MODULE.DiagnosticStream(CANDIDATE)
        accepted = stream.feed(
            MODULE.frame_for(
                record(boottime_ms=5_000, deadline=905_000)
            )
        )
        self.assertEqual(accepted[0].watchdog_deadline_ms, 905_000)
        for deadline in (5_000, 905_001):
            with self.subTest(deadline=deadline):
                stream = MODULE.DiagnosticStream(CANDIDATE)
                with self.assertRaises(MODULE.DiagnosticError):
                    stream.feed(
                        MODULE.frame_for(
                            record(boottime_ms=5_000, deadline=deadline)
                        )
                    )
        stream = MODULE.DiagnosticStream(CANDIDATE)
        stream.feed(MODULE.frame_for(record(deadline=600_000)))
        with self.assertRaises(MODULE.DiagnosticError):
            stream.feed(
                MODULE.frame_for(
                    record(
                        sequence=2,
                        boottime_ms=600_000,
                        deadline=600_000,
                    )
                )
            )

    def test_payload_field_mutations_fail(self):
        canonical = MODULE.payload_for(record())
        mutations = (
            canonical.replace(b"format=", b"unknown="),
            canonical.replace(b"candidate=", b"candidate=x\nextra="),
            canonical.replace(b"sequence=1", b"sequence=01"),
            canonical.replace(b"stage=reporter-up", b"stage=fault"),
            canonical.replace(b"last_good_code=10", b"last_good_code=20"),
            canonical.replace(b"fault=none", b"fault=unknown"),
            canonical.replace(b"watchdog_deadline_ms=600000", b"watchdog_deadline_ms=1"),
            canonical[:-1],
            canonical + b"extra=1\n",
            canonical.replace(b"\n", b"\r\n", 1),
        )
        for payload in mutations:
            with self.subTest(payload=payload):
                with self.assertRaises(MODULE.DiagnosticError):
                    MODULE.parse_payload(
                        payload, expected_candidate=CANDIDATE
                    )

    def test_malformed_oversize_and_truncated_frames_fail(self):
        malformed = (b"01:x,", b"x:x,", b"1:x.", b"1025:")
        for frame in malformed:
            with self.subTest(frame=frame):
                stream = MODULE.DiagnosticStream(CANDIDATE)
                with self.assertRaises(MODULE.DiagnosticError):
                    stream.feed(frame)
        stream = MODULE.DiagnosticStream(CANDIDATE)
        stream.feed(MODULE.frame_for(record())[:-1])
        with self.assertRaises(MODULE.DiagnosticError):
            stream.finalize()

    def test_wrong_candidate_and_mixed_boot_fail(self):
        with self.assertRaises(MODULE.DiagnosticError):
            MODULE.parse_payload(
                MODULE.payload_for(record(candidate="another-diag")),
                expected_candidate=CANDIDATE,
            )
        stream = MODULE.DiagnosticStream(CANDIDATE)
        stream.feed(MODULE.frame_for(record()))
        with self.assertRaises(MODULE.DiagnosticError):
            stream.feed(
                MODULE.frame_for(
                    record(
                        2,
                        boot_id="87654321-4321-4abc-8def-1234567890ab",
                    )
                )
            )


class NativeDiagnosticEmitterTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory()
        cls.binary = Path(cls.temporary.name) / "rog5-early-target-diag"
        cls.production_binary = (
            Path(cls.temporary.name) / "rog5-early-target-diag-production"
        )
        source = (
            Path(__file__).resolve().parents[2]
            / "tools/early_target_diag/rog5-early-target-diag.c"
        )
        subprocess.run(
            [
                "gcc",
                "-DROG5_DIAG_TESTING",
                "-std=c11",
                "-Wall",
                "-Wextra",
                "-Werror",
                "-O2",
                str(source),
                "-o",
                str(cls.binary),
            ],
            check=True,
        )
        subprocess.run(
            [
                "gcc",
                "-std=c11",
                "-Wall",
                "-Wextra",
                "-Werror",
                "-O2",
                str(source),
                "-o",
                str(cls.production_binary),
            ],
            check=True,
        )

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    def emit(self, item):
        return subprocess.run(
            [
                str(self.binary),
                "frame",
                item.candidate,
                item.boot_id,
                str(item.sequence),
                str(item.boottime_ms),
                str(item.stage_code),
                str(item.last_good_code),
                item.fault,
                str(item.watchdog_deadline_ms),
                str(item.dropped_updates),
            ],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

    def test_native_frames_match_python_oracle(self):
        fixtures = [record(index, code) for index, code in enumerate(
            sorted(MODULE.PROGRESS_CODES), 1
        )]
        fixtures.extend(
            record(
                100 + index,
                200,
                last_good_code=70,
                fault=reason,
            )
            for index, reason in enumerate(
                sorted(MODULE.FAULTS - {"none"}), 1
            )
        )
        fixtures.append(record(200, 210, last_good_code=120))
        for item in fixtures:
            with self.subTest(item=item):
                result = self.emit(item)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stdout, MODULE.frame_for(item))
                stream = MODULE.DiagnosticStream(CANDIDATE)
                self.assertEqual(stream.feed(result.stdout), [item])

    def test_native_emitter_rejects_identity_and_state_mutations(self):
        canonical = record()
        arguments = [
            str(self.binary),
            "frame",
            canonical.candidate,
            canonical.boot_id,
            "1",
            "250",
            "10",
            "10",
            "none",
            "600000",
            "0",
        ]
        mutations = {
            2: ("../escape", "UPPER"),
            3: ("not-a-uuid", BOOT.upper()),
            4: ("0", "01", "-1"),
            5: ("600001", "x"),
            6: ("11", "0", "211"),
            7: ("20", "0", "141"),
            8: ("unknown",),
            9: ("0", "18446744073709551616", "-1", "x"),
            10: ("1000001", "-1"),
        }
        for position, values in mutations.items():
            for value in values:
                with self.subTest(position=position, value=value):
                    changed = arguments.copy()
                    changed[position] = value
                    result = subprocess.run(
                        changed,
                        stdin=subprocess.DEVNULL,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        check=False,
                    )
                    self.assertNotEqual(result.returncode, 0)
                    self.assertEqual(result.stdout, b"")

    def test_native_source_has_no_input_or_execution_surface(self):
        source = (
            Path(__file__).resolve().parents[2]
            / "tools/early_target_diag/rog5-early-target-diag.c"
        ).read_text(encoding="utf-8")
        for forbidden in (
            "system(",
            "execv",
            "popen(",
            "fork(",
            "STDIN_FILENO",
            "O_RDWR",
        ):
            self.assertNotIn(forbidden, source)
        for required in (
            "O_WRONLY | O_NONBLOCK | O_NOCTTY | O_CLOEXEC",
            "SOCK_DGRAM | SOCK_NONBLOCK | SOCK_CLOEXEC",
            "MSG_DONTWAIT | MSG_NOSIGNAL",
            "MSG_DONTWAIT | MSG_TRUNC | MSG_CMSG_CLOEXEC",
            "header.msg_flags & MSG_CTRUNC",
            "SO_PASSCRED",
            "SCM_CREDENTIALS",
            "SCM_RIGHTS",
            "credentials.uid != 0",
            "address->sun_path + 1",
            "ioctl(descriptor, TIOCEXCL)",
            "attributes.c_cflag &= ~(CSIZE | PARENB | HUPCL)",
        ):
            self.assertIn(required, source)

    def test_production_binary_excludes_every_test_hook(self):
        self.assertNotIn(
            b"ROG5_DIAG_TEST_", self.production_binary.read_bytes()
        )

    def service_environment(
        self, suffix, *, frames=5, start=1000, step=25
    ):
        environment = os.environ.copy()
        environment.update(
            {
                "ROG5_DIAG_TEST_OUTPUT_FD": "1",
                "ROG5_DIAG_TEST_FRAME_LIMIT": str(frames),
                "ROG5_DIAG_TEST_CLOCK_START_MS": str(start),
                "ROG5_DIAG_TEST_CLOCK_STEP_MS": str(step),
                "ROG5_DIAG_TEST_SOCKET_SUFFIX": suffix,
            }
        )
        return environment

    def start_service(self, suffix, **environment_options):
        environment = self.service_environment(
            suffix, **environment_options
        )
        process = subprocess.Popen(
            [
                str(self.binary),
                "serve",
                CANDIDATE,
                BOOT,
                "600000",
            ],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=environment,
        )
        return process, environment

    def emit_when_ready(self, environment, stage, fault=None):
        command = [str(self.binary), "emit", str(stage)]
        if fault is not None:
            command.append(fault)
        deadline = time.monotonic() + 2
        while True:
            result = subprocess.run(
                command,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=environment,
                check=False,
            )
            if result.returncode == 0:
                return
            if time.monotonic() >= deadline:
                self.fail(result.stderr.decode(errors="replace"))
            time.sleep(0.01)

    def parse_service_output(self, payload):
        stream = MODULE.DiagnosticStream(CANDIDATE)
        records = stream.feed(payload)
        stream.finalize()
        return stream, records

    def test_service_emits_bounded_cadenced_heartbeats(self):
        process, _ = self.start_service("heartbeat", frames=3, step=25)
        output, error = process.communicate(timeout=3)
        self.assertEqual(process.returncode, 0, error)
        stream, records = self.parse_service_output(output)
        self.assertEqual(len(records), 3)
        self.assertEqual(stream.maximum_progress, 10)
        intervals = [
            later.boottime_ms - earlier.boottime_ms
            for earlier, later in zip(records, records[1:])
        ]
        self.assertTrue(all(interval >= 250 for interval in intervals))

    def test_nonblocking_local_updates_advance_and_terminate(self):
        process, environment = self.start_service(
            "updates", frames=8, step=10
        )
        self.emit_when_ready(environment, 70)
        self.emit_when_ready(environment, 200, "nfs-mount-failed")
        self.emit_when_ready(environment, 80)
        output, error = process.communicate(timeout=5)
        self.assertEqual(process.returncode, 0, error)
        stream, records = self.parse_service_output(output)
        self.assertIn(70, [item.last_good_code for item in records])
        self.assertEqual(
            stream.terminal, (200, 70, "nfs-mount-failed")
        )
        self.assertTrue(any(item.dropped_updates > 0 for item in records))

    def test_malformed_local_update_is_counted_not_fatal(self):
        suffix = "malformed"
        process, environment = self.start_service(
            suffix, frames=5, step=10
        )
        self.emit_when_ready(environment, 20)
        with socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM) as sender:
            sender.sendto(
                b"not-canonical", "\0" + MODULE.FORMAT + "-" + suffix
            )
            sender.sendto(
                b"x" * 128, "\0" + MODULE.FORMAT + "-" + suffix
            )
        output, error = process.communicate(timeout=5)
        self.assertEqual(process.returncode, 0, error)
        _, records = self.parse_service_output(output)
        self.assertTrue(any(item.dropped_updates >= 2 for item in records))

    def test_watchdog_pretimeout_is_automatic_and_terminal(self):
        process, _ = self.start_service(
            "pretimeout", frames=3, start=599700, step=100
        )
        output, error = process.communicate(timeout=3)
        self.assertEqual(process.returncode, 0, error)
        stream, records = self.parse_service_output(output)
        self.assertIn(210, [item.stage_code for item in records])
        self.assertEqual(stream.terminal, (210, 10, "none"))
        self.assertTrue(
            any(item.boottime_ms > 600000 for item in records)
        )

    def test_host_bytes_on_output_channel_are_never_consumed(self):
        host, target = socket.socketpair()
        target.setblocking(False)
        try:
            environment = self.service_environment(
                "noinput", frames=3, start=1000, step=25
            )
            environment["ROG5_DIAG_TEST_OUTPUT_FD"] = str(
                target.fileno()
            )
            process = subprocess.Popen(
                [
                    str(self.binary),
                    "serve",
                    CANDIDATE,
                    BOOT,
                    "600000",
                ],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                env=environment,
                pass_fds=(target.fileno(),),
            )
            probe = b"host-to-target-bytes-must-remain-unread"
            host.sendall(probe)
            _, error = process.communicate(timeout=3)
            self.assertEqual(process.returncode, 0, error)
            host.settimeout(0.1)
            output = b""
            while True:
                try:
                    output += host.recv(8192)
                except TimeoutError:
                    break
            _, records = self.parse_service_output(output)
            self.assertEqual(len(records), 3)
            self.assertEqual(target.recv(len(probe)), probe)
        finally:
            host.close()
            target.close()

    def test_rights_datagrams_are_closed_rejected_and_nonfatal(self):
        read_descriptor, write_descriptor = os.pipe()
        os.set_blocking(write_descriptor, False)
        try:
            block = b"x" * 4096
            while True:
                try:
                    os.write(write_descriptor, block)
                except BlockingIOError:
                    break
            suffix = "rights"
            environment = self.service_environment(suffix, frames=1)
            environment["ROG5_DIAG_TEST_OUTPUT_FD"] = str(
                write_descriptor
            )
            process = subprocess.Popen(
                [
                    str(self.binary),
                    "serve",
                    CANDIDATE,
                    BOOT,
                    "600000",
                ],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                env=environment,
                pass_fds=(write_descriptor,),
            )
            self.emit_when_ready(environment, 20)
            time.sleep(0.05)
            baseline = len(list(Path(f"/proc/{process.pid}/fd").iterdir()))
            rights = array.array("i", [read_descriptor])
            message = b"stage_code=70\nfault=none\n"
            address = "\0" + MODULE.FORMAT + "-" + suffix
            with socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM) as sender:
                for _ in range(64):
                    sender.sendmsg(
                        [message],
                        [(socket.SOL_SOCKET, socket.SCM_RIGHTS, rights)],
                        0,
                        address,
                    )
            time.sleep(0.2)
            current = len(list(Path(f"/proc/{process.pid}/fd").iterdir()))
            self.assertLessEqual(current, baseline)
            self.emit_when_ready(environment, 70)
            self.assertIsNone(process.poll())
            process.terminate()
            _, error = process.communicate(timeout=2)
            self.assertEqual(process.returncode, -15, error)
        finally:
            os.close(write_descriptor)
            os.close(read_descriptor)

    def test_blocked_output_cannot_block_local_stage_update(self):
        read_descriptor, write_descriptor = os.pipe()
        os.set_blocking(write_descriptor, False)
        try:
            block = b"x" * 4096
            while True:
                try:
                    os.write(write_descriptor, block)
                except BlockingIOError:
                    break
            suffix = "blocked"
            environment = self.service_environment(
                suffix, frames=1, start=1000, step=10
            )
            environment["ROG5_DIAG_TEST_OUTPUT_FD"] = str(
                write_descriptor
            )
            process = subprocess.Popen(
                [
                    str(self.binary),
                    "serve",
                    CANDIDATE,
                    BOOT,
                    "600000",
                ],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                env=environment,
                pass_fds=(write_descriptor,),
            )
            started = time.monotonic()
            self.emit_when_ready(environment, 70)
            self.assertLess(time.monotonic() - started, 0.5)
            self.assertIsNone(process.poll())
            process.terminate()
            _, error = process.communicate(timeout=2)
            self.assertEqual(process.returncode, -15, error)
        finally:
            os.close(write_descriptor)
            os.close(read_descriptor)


class EarlyTargetDiagnosticStateTest(unittest.TestCase):

    def test_route_loss_is_a_distinct_terminal_fault(self):
        stream = MODULE.DiagnosticStream(CANDIDATE)
        stream.feed(MODULE.frame_for(record(1, 70)))
        parsed = stream.feed(
            MODULE.frame_for(
                record(
                    2,
                    200,
                    last_good_code=70,
                    fault="route-failed",
                )
            )
        )
        self.assertEqual(parsed[-1].fault, "route-failed")
        self.assertEqual(stream.terminal, (200, 70, "route-failed"))

    def test_sequence_time_stage_and_drop_regressions_fail(self):
        mutations = (
            record(1, 20),
            record(2, 20, boottime_ms=100),
            record(2, 10),
            record(2, 20, dropped=0),
        )
        baselines = (
            record(1, 10),
            record(1, 10, boottime_ms=250),
            record(1, 20),
            record(1, 10, dropped=1),
        )
        for baseline, mutation in zip(baselines, mutations, strict=True):
            with self.subTest(mutation=mutation):
                stream = MODULE.DiagnosticStream(CANDIDATE)
                stream.feed(MODULE.frame_for(baseline))
                with self.assertRaises(MODULE.DiagnosticError):
                    stream.feed(MODULE.frame_for(mutation))

    def test_watchdog_deadline_must_remain_fixed(self):
        stream = MODULE.DiagnosticStream(CANDIDATE)
        stream.feed(MODULE.frame_for(record()))
        with self.assertRaises(MODULE.DiagnosticError):
            stream.feed(MODULE.frame_for(record(2, deadline=599_999)))

    def test_terminal_state_repeats_but_never_changes(self):
        stream = MODULE.DiagnosticStream(CANDIDATE)
        stream.feed(MODULE.frame_for(record(1, 70)))
        stream.feed(
            MODULE.frame_for(
                record(
                    2,
                    200,
                    last_good_code=70,
                    fault="nfs-mount-failed",
                )
            )
        )
        stream.feed(
            MODULE.frame_for(
                record(
                    3,
                    200,
                    last_good_code=70,
                    fault="nfs-mount-failed",
                )
            )
        )
        with self.assertRaises(MODULE.DiagnosticError):
            stream.feed(
                MODULE.frame_for(
                    record(
                        4,
                        200,
                        last_good_code=70,
                        fault="seal-verify-failed",
                    )
                )
            )

    def test_progress_after_terminal_and_last_good_regression_fail(self):
        for terminal in (
            record(2, 200, last_good_code=60, fault="carrier-timeout"),
            record(2, 210, last_good_code=60),
        ):
            with self.subTest(terminal=terminal):
                stream = MODULE.DiagnosticStream(CANDIDATE)
                stream.feed(MODULE.frame_for(record(1, 60)))
                stream.feed(MODULE.frame_for(terminal))
                with self.assertRaises(MODULE.DiagnosticError):
                    stream.feed(MODULE.frame_for(record(3, 70)))
        stream = MODULE.DiagnosticStream(CANDIDATE)
        stream.feed(MODULE.frame_for(record(1, 80)))
        with self.assertRaises(MODULE.DiagnosticError):
            stream.feed(
                MODULE.frame_for(
                    record(
                        2,
                        200,
                        last_good_code=70,
                        fault="seal-verify-failed",
                    )
                )
            )

    def test_pretimeout_is_terminal_and_fault_free(self):
        parsed = MODULE.parse_payload(
            MODULE.payload_for(record(stage_code=210)),
            expected_candidate=CANDIDATE,
        )
        self.assertEqual(parsed.stage, "watchdog-pretimeout")
        self.assertEqual(parsed.fault, "none")
        parsed_late = MODULE.parse_payload(
            MODULE.payload_for(
                record(
                    stage_code=210,
                    boottime_ms=600001,
                )
            ),
            expected_candidate=CANDIDATE,
        )
        self.assertEqual(parsed_late.boottime_ms, 600001)
        with self.assertRaises(MODULE.DiagnosticError):
            MODULE.parse_payload(
                MODULE.payload_for(
                    record(stage_code=140, boottime_ms=600001)
                ),
                expected_candidate=CANDIDATE,
            )
        with self.assertRaises(MODULE.DiagnosticError):
            MODULE.parse_payload(
                MODULE.payload_for(
                    record(
                        stage_code=210,
                        fault="watchdog-failed",
                    )
                ),
                expected_candidate=CANDIDATE,
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
