#!/usr/bin/env python3
"""Hostile tests for the ROG5 early-target diagnostic stream."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import subprocess
import sys
import tempfile
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
        source = (
            Path(__file__).resolve().parents[2]
            / "tools/early_target_diag/rog5-early-target-diag.c"
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
                str(cls.binary),
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
            9: ("59999", "900001"),
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
            "read(",
            "recv(",
            "/dev/",
        ):
            self.assertNotIn(forbidden, source)


class EarlyTargetDiagnosticStateTest(unittest.TestCase):

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
