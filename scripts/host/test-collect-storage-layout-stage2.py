#!/usr/bin/env python3
"""Protocol tests for the Stage-2 ACM result collector."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import unittest


REPO = Path(__file__).resolve().parents[2]
PATH = REPO / "scripts/host/collect-storage-layout-stage2.py"
SPEC = importlib.util.spec_from_file_location("rog5_stage2_collector_test", PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)

OPERATION = "0123456789abcdef0123456789abcdef"
TARGET_UUID = "11111111-2222-4333-8444-555555555555"


class FakeTransport:
    def __init__(self, records: list[bytes]) -> None:
        self.records = list(records)

    def readline(self, maximum: int, timeout: float) -> bytes:
        del timeout
        if not self.records:
            raise MODULE.Stage2ProtocolError("fixture exhausted")
        result = self.records.pop(0)
        if len(result) > maximum:
            raise MODULE.Stage2ProtocolError("fixture line too long")
        return result


def running(stage: str) -> bytes:
    return f"{MODULE.PREFIX} status=RUNNING stage={stage} reason=none\n".encode()


def passing(**changes: str) -> bytes:
    fields = {
        "status": "PASS",
        "stage": "S99_COMPLETE",
        "reason": "none",
        "operation_id": OPERATION,
        "source_sha256": MODULE.SOURCE_SHA256,
        "target_uuid": TARGET_UUID,
        "target_blocks": "8388603",
        "native_seal_sha256": MODULE.SEAL_SHA256,
        "tree_sha256": MODULE.TREE_SHA256,
        "all_read_only": "1",
        "block_mounts": "0",
    }
    fields.update(changes)
    return (
        MODULE.PREFIX
        + " "
        + " ".join(f"{name}={value}" for name, value in fields.items())
        + "\n"
    ).encode()


def preflight_passing(**changes: str) -> bytes:
    fields = {
        "status": "PASS",
        "stage": "S99_COMPLETE",
        "reason": "none",
        "operation_id": OPERATION,
        "wrapper_physical_count": "117",
        "userdata_uuid": "0892bacf-3e02-41b0-84a4-5f05c2df7ce5",
        "userdata_blocks": "51124000",
        "arch_root_guid": "60f49e17-bdc6-46bf-8d47-8a24907024c9",
        "arch_root_empty": "1",
        "all_read_only": "1",
        "block_mounts": "0",
    }
    fields.update(changes)
    return (
        MODULE.PREFIX
        + " "
        + " ".join(f"{name}={value}" for name, value in fields.items())
        + "\n"
    ).encode()


def guards(**changes: str) -> bytes:
    fields = {
        "status": "GUARDS",
        "discovery": "pass",
        "isolation": "pass",
        "power": "pass",
        "inventory": "pass",
        "auto_markers": "1",
        "host_markers": "1",
        "wlun_markers": "8",
        "blocked_queries": "0",
        "blocked_scsi": "0",
        "wrapper_physical_count": "117",
    }
    fields.update(changes)
    return (
        MODULE.PREFIX
        + " "
        + " ".join(f"{name}={value}" for name, value in fields.items())
        + "\n"
    ).encode()


def partition(**changes: str) -> bytes:
    fields = {
        "status": "PARTITION",
        "number": "24",
        "read": "pass",
        "first": "53477376",
        "last": "61865978",
        "type": "0fc63daf-8483-4772-8e79-3d69d8477de4",
        "unique": "60f49e17-bdc6-46bf-8d47-8a24907024c9",
        "name": "arch_root_a",
        "attrs": "0004000000000000",
    }
    fields.update(changes)
    return (
        MODULE.PREFIX
        + " "
        + " ".join(f"{name}={value}" for name, value in fields.items())
        + "\n"
    ).encode()


class CollectorTest(unittest.TestCase):
    def records(self) -> list[bytes]:
        return [*(running(stage) for stage in MODULE.STAGES), passing()]

    def test_exact_sequence_and_pass_are_accepted(self) -> None:
        records = self.records()
        transcript, terminal = MODULE.capture(
            FakeTransport(records), OPERATION, TARGET_UUID, 1.0
        )
        self.assertEqual(terminal, passing())
        self.assertEqual(transcript, b"".join(self.records()))

    def test_exact_read_only_preflight_and_hostile_mutations(self) -> None:
        records = [
            running("S00_CONFIG"),
            guards(),
            running("S10_TOPOLOGY"),
            partition(),
            preflight_passing(),
        ]
        transcript, terminal = MODULE.capture(
            FakeTransport(records), OPERATION, TARGET_UUID, 1.0, "preflight"
        )
        self.assertEqual(terminal, preflight_passing())
        self.assertEqual(transcript, b"".join(records))
        for changes in (
            {"userdata_blocks": "51123999"},
            {"wrapper_physical_count": "0"},
            {"wrapper_physical_count": "1000"},
            {"arch_root_empty": "0"},
            {"all_read_only": "0"},
            {"block_mounts": "1"},
        ):
            with self.subTest(changes=changes):
                hostile = [
                    running("S00_CONFIG"),
                    guards(),
                    running("S10_TOPOLOGY"),
                    partition(),
                    preflight_passing(**changes),
                ]
                with self.assertRaisesRegex(
                    MODULE.Stage2ProtocolError,
                    "preflight (PASS identity|wrapper count)",
                ):
                    MODULE.capture(
                        FakeTransport(hostile),
                        OPERATION,
                        TARGET_UUID,
                        1.0,
                        "preflight",
                    )

    def test_preflight_requires_one_exact_guard_record(self) -> None:
        for records in (
            [running("S00_CONFIG"), running("S10_TOPOLOGY"), preflight_passing()],
            [running("S00_CONFIG"), guards(discovery="unknown"), running("S10_TOPOLOGY")],
            [running("S00_CONFIG"), guards(), guards(), running("S10_TOPOLOGY")],
        ):
            with self.subTest(records=records):
                with self.assertRaises(MODULE.Stage2ProtocolError):
                    MODULE.capture(
                        FakeTransport(records),
                        OPERATION,
                        TARGET_UUID,
                        1.0,
                        "preflight",
                    )

    def test_unsupported_wrapper_power_markers_are_nonfatal(self) -> None:
        records = [
            running("S00_CONFIG"),
            guards(
                power="unsupported",
                auto_markers="0",
                host_markers="0",
                wlun_markers="0",
            ),
            running("S10_TOPOLOGY"),
            partition(),
            preflight_passing(),
        ]
        transcript, terminal = MODULE.capture(
            FakeTransport(records), OPERATION, TARGET_UUID, 1.0, "preflight"
        )
        self.assertEqual(terminal, preflight_passing())
        self.assertEqual(transcript, b"".join(records))

    def test_preflight_requires_one_canonical_partition_record(self) -> None:
        base = [running("S00_CONFIG"), guards(), running("S10_TOPOLOGY")]
        hostile = (
            [*base, preflight_passing()],
            [*base, partition(number="23"), preflight_passing()],
            [*base, partition(first="invalid"), preflight_passing()],
            [*base, partition(read="fail"), preflight_passing()],
            [*base, partition(), partition(), preflight_passing()],
        )
        for records in hostile:
            with self.subTest(records=records):
                with self.assertRaises(MODULE.Stage2ProtocolError):
                    MODULE.capture(
                        FakeTransport(records),
                        OPERATION,
                        TARGET_UUID,
                        1.0,
                        "preflight",
                    )

    def test_skipped_or_duplicate_stage_is_rejected(self) -> None:
        for records in (
            [running(MODULE.STAGES[1]), passing()],
            [running(MODULE.STAGES[0]), running(MODULE.STAGES[0]), passing()],
        ):
            with self.subTest(records=records):
                with self.assertRaisesRegex(
                    MODULE.Stage2ProtocolError, "sequence changed"
                ):
                    MODULE.capture(FakeTransport(records), OPERATION, TARGET_UUID, 1.0)

    def test_changed_terminal_identity_is_rejected(self) -> None:
        for changes in (
            {"operation_id": "f" * 32},
            {"source_sha256": "0" * 64},
            {"target_uuid": "00000000-0000-0000-0000-000000000000"},
            {"target_blocks": "8388602"},
            {"native_seal_sha256": "0" * 64},
            {"tree_sha256": "0" * 64},
            {"all_read_only": "0"},
            {"block_mounts": "1"},
        ):
            with self.subTest(changes=changes):
                records = [*(running(stage) for stage in MODULE.STAGES), passing(**changes)]
                with self.assertRaisesRegex(
                    MODULE.Stage2ProtocolError, "PASS identity"
                ):
                    MODULE.capture(FakeTransport(records), OPERATION, TARGET_UUID, 1.0)

    def test_exact_failure_classes_are_retained(self) -> None:
        terminal = (
            f"{MODULE.PREFIX} status=FAIL stage=S40_CLONE reason=clone_failed "
            "target_state=partial cleanup=0 relock=0\n"
        ).encode()
        transcript, result = MODULE.capture(
            FakeTransport([running(stage) for stage in MODULE.STAGES[:5]] + [terminal]),
            OPERATION,
            TARGET_UUID,
            1.0,
        )
        self.assertEqual(result, terminal)
        self.assertTrue(transcript.endswith(terminal))

    def test_malformed_failure_classification_is_rejected(self) -> None:
        for terminal in (
            f"{MODULE.PREFIX} status=FAIL stage=S40_CLONE reason=none target_state=partial cleanup=0 relock=0\n",
            f"{MODULE.PREFIX} status=FAIL stage=S40_CLONE reason=clone_failed target_state=unknown cleanup=0 relock=0\n",
            f"{MODULE.PREFIX} status=FAIL stage=S40_CLONE reason=clone_failed target_state=partial cleanup=2 relock=0\n",
        ):
            with self.subTest(terminal=terminal):
                with self.assertRaises(MODULE.Stage2ProtocolError):
                    MODULE.capture(
                        FakeTransport([terminal.encode()]), OPERATION, TARGET_UUID, 1.0
                    )

    def test_failure_cannot_claim_a_future_stage(self) -> None:
        terminal = (
            f"{MODULE.PREFIX} status=FAIL stage=S40_CLONE reason=clone_failed "
            "target_state=partial cleanup=0 relock=0\n"
        ).encode()
        with self.assertRaisesRegex(
            MODULE.Stage2ProtocolError, "contradicts progress"
        ):
            MODULE.capture(
                FakeTransport([running("S00_CONFIG"), terminal]),
                OPERATION,
                TARGET_UUID,
                1.0,
            )


if __name__ == "__main__":
    unittest.main()
