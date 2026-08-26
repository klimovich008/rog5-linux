#!/usr/bin/env python3
"""Hardware-free tests for receive-only Stage-1 prewrite observation."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import unittest


SOURCE = Path(__file__).with_name("observe-storage-layout-stage1-prewrite.py")
SPEC = importlib.util.spec_from_file_location("stage1_prewrite_observer", SOURCE)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("cannot load Stage-1 prewrite observer")
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def running(stage: str) -> bytes:
    return (
        f"ROG5_LAYOUT_STAGE1_V1 status=RUNNING stage={stage} reason=none\n"
    ).encode("ascii")


def failure(stage: str, reason: str) -> bytes:
    return (
        "ROG5_LAYOUT_STAGE1_V1 status=FAIL "
        f"stage={stage} reason={reason} gpt_restored=not_needed\n"
    ).encode("ascii")


class FakeTransport:
    def __init__(self, lines: list[bytes]) -> None:
        self.lines = list(lines)

    def readline(self, _maximum: int, _timeout: float) -> bytes:
        if not self.lines:
            raise MODULE.STAGE1.LayoutProtocolError("test transport exhausted")
        return self.lines.pop(0)

    def write_all(self, _payload: bytes, _timeout: float) -> None:
        raise AssertionError("receive-only observer attempted a write")


class ObserverTests(unittest.TestCase):
    def test_each_exact_prewrite_failure_is_captured_without_writing(self) -> None:
        cases = (
            ("S00_CONFIG", "invalid_private_config", []),
            ("S10_TOPOLOGY", "topology_identity", ["S00_CONFIG"]),
            (
                "S20_PROTECTED_SEAL",
                "protected_partition_read_failed",
                ["S00_CONFIG", "S10_TOPOLOGY"],
            ),
        )
        for stage, reason, prior in cases:
            with self.subTest(stage=stage):
                transport = FakeTransport(
                    [*(running(value) for value in prior), failure(stage, reason)]
                )
                result = MODULE.observe(transport, 1)
                self.assertEqual(result["outcome"], "TARGET_FAIL_BEFORE_S30")
                self.assertEqual(result["terminal"]["stage"], stage)
                self.assertEqual(result["terminal"]["reason"], reason)

    def test_s30_stops_before_readiness_backup_or_ack(self) -> None:
        transport = FakeTransport([running(stage) for stage in MODULE.STAGES])
        result = MODULE.observe(transport, 1)
        self.assertEqual(result["outcome"], "REACHED_S30_NO_HOST_BYTES_SENT")
        self.assertEqual(result["stages"], list(MODULE.STAGES))
        self.assertIsNone(result["terminal"])

    def test_regression_malformed_and_mutating_states_fail_closed(self) -> None:
        cases = (
            [running("S10_TOPOLOGY")],
            [running("S00_CONFIG"), running("S20_PROTECTED_SEAL")],
            [failure("S30_FRESH_BACKUP", "host_ready_empty")],
            [failure("S10_TOPOLOGY", "none")],
            [
                b"ROG5_LAYOUT_STAGE1_V1 status=PASS stage=S99_COMPLETE "
                b"reason=none\n"
            ],
        )
        for lines in cases:
            with self.subTest(lines=lines):
                with self.assertRaises(
                    (MODULE.ObservationError, MODULE.STAGE1.LayoutProtocolError)
                ):
                    MODULE.observe(FakeTransport(lines), 1)

    def test_source_has_no_serial_write_or_mutation_surface(self) -> None:
        source = SOURCE.read_text(encoding="utf-8")
        for forbidden in (
            ".write_all(",
            "os.write(",
            "BACKUP_ACK",
            "blockdev",
            "resize2fs",
            "sgdisk --",
            "fastboot boot",
        ):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main(verbosity=2)
