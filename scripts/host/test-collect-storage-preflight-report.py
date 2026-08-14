#!/usr/bin/env python3
"""Hardware-free tests for exact storage-preflight report collection."""

from __future__ import annotations

from collections import OrderedDict
import base64
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock


REPO = Path(__file__).resolve().parents[2]
SOURCE = REPO / "scripts/host/collect-storage-preflight-report.py"
SPEC = importlib.util.spec_from_file_location("collect_storage_preflight", SOURCE)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("cannot load storage-preflight collector")
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)

LOCATION = "pci0000:00/0000:00:08.1/usb1/1-1/1-1.2"
VALID = (
    b"ROG5_STORAGE_PREFLIGHT_V2 status=PASS stage=S99_COMPLETE reason=none "
    b"logical_block_bytes=4096 "
    b"lun_bytes=253403070464 gpt_entries=32 userdata_first_lba=2352680 "
    b"userdata_last_lba=61865978 userdata_blocks=59513299 "
    b"ext4_blocks=59513299 ext4_minimum_blocks=11695396 "
    b"proposed_userdata_last_lba=53477375 "
    b"proposed_root_first_lba=53477376 "
    b"proposed_root_last_lba=61865978 sgdisk=1.0.10 "
    b"e2fsprogs=1.47.4 all_read_only=1 block_mounts=0\n"
)
RUNNING = (
    b"ROG5_STORAGE_PREFLIGHT_V2 status=RUNNING stage=S30_GPT_VERIFY "
    b"reason=none all_read_only=1 block_mounts=0\n"
)
FAILED = (
    b"ROG5_STORAGE_PREFLIGHT_V2 status=FAIL stage=S30_GPT_VERIFY "
    b"reason=gpt_verify_failed all_read_only=1 block_mounts=0\n"
)


class FakeSerial:
    def __init__(self, chunks: list[bytes | None]) -> None:
        self.chunks = iter(chunks)

    def read(self, _timeout: float) -> bytes | None:
        return next(self.chunks, None)


class ReportTests(unittest.TestCase):
    def test_exact_report_passes(self) -> None:
        values = MODULE.parse_report(VALID)
        self.assertIsInstance(values, OrderedDict)
        self.assertEqual(values["ext4_minimum_blocks"], "11695396")

    def test_exact_running_and_failure_classification_pass(self) -> None:
        running = MODULE.parse_report(RUNNING)
        failed = MODULE.parse_report(FAILED)
        self.assertEqual(running["status"], "RUNNING")
        self.assertEqual(failed["status"], "FAIL")
        self.assertEqual(failed["reason"], "gpt_verify_failed")

    def test_every_terminal_failure_has_one_exact_classification(self) -> None:
        for reason, stage in MODULE.FAILURE_STAGE_REASONS.items():
            read_only = (
                "0"
                if reason in ("disk_not_read_only", "userdata_not_read_only")
                else "1"
            )
            payload = (
                f"ROG5_STORAGE_PREFLIGHT_V2 status=FAIL stage={stage} "
                f"reason={reason} all_read_only={read_only} block_mounts=0\n"
            ).encode("ascii")
            with self.subTest(reason=reason):
                values = MODULE.parse_report(payload)
                self.assertEqual(values["stage"], stage)
                self.assertEqual(values["reason"], reason)

    def test_failure_read_only_claim_cannot_contradict_reason(self) -> None:
        with self.assertRaisesRegex(MODULE.PreflightError, "read-only state"):
            MODULE.parse_report(FAILED.replace(b"all_read_only=1", b"all_read_only=0"))

    def test_unknown_stage_reason_pair_fails(self) -> None:
        changed = FAILED.replace(
            b"stage=S30_GPT_VERIFY reason=gpt_verify_failed",
            b"stage=S40_EXT4_CHECK reason=gpt_verify_failed",
        )
        with self.assertRaisesRegex(MODULE.PreflightError, "stage/reason"):
            MODULE.parse_report(changed)

    def test_receive_loop_waits_for_one_terminal_report(self) -> None:
        identity = MODULE.CORE.AcmIdentity("/dev/ttyACM7", LOCATION, 123)
        serial = FakeSerial([RUNNING, FAILED])
        with mock.patch.object(MODULE, "revalidate_storage_acm"):
            payload, values = MODULE.capture_report(serial, identity, 2)
        self.assertEqual(payload, FAILED)
        self.assertEqual(values["reason"], "gpt_verify_failed")

    def test_rejected_payload_is_retained_without_becoming_accepted(self) -> None:
        identity = MODULE.CORE.AcmIdentity("/dev/ttyACM7", LOCATION, 123)
        malformed = b"\r\n"
        serial = FakeSerial([malformed])
        with mock.patch.object(MODULE, "revalidate_storage_acm"):
            with self.assertRaises(MODULE.RejectedReport) as caught:
                MODULE.capture_report(serial, identity, 2)
        rejection = caught.exception
        self.assertEqual(rejection.payload, malformed)
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "rejected.json"
            MODULE.write_rejected_evidence(
                output,
                OrderedDict(
                    (
                        ("host_boot_id", "11111111-2222-4333-8444-555555555555"),
                        ("usb_location", LOCATION),
                    )
                ),
                identity,
                123,
                rejection,
            )
            document = json.loads(output.read_text(encoding="ascii"))
        self.assertEqual(document["format"], MODULE.REJECTED_FORMAT)
        self.assertEqual(document["error"], "storage-preflight report shape is not exact")
        self.assertEqual(document["payload_base64"], base64.b64encode(malformed).decode("ascii"))
        self.assertEqual(document["payload_sha256"], hashlib.sha256(malformed).hexdigest())
        self.assertEqual(document["payload_size"], len(malformed))
        self.assertNotIn("fields", document)

    def test_running_only_capture_remains_bounded(self) -> None:
        identity = MODULE.CORE.AcmIdentity("/dev/ttyACM7", LOCATION, 123)
        serial = FakeSerial([RUNNING])
        with (
            mock.patch.object(MODULE, "revalidate_storage_acm"),
            mock.patch.object(MODULE.time, "monotonic", side_effect=[0.0, 0.0, 0.0, 3.0]),
        ):
            with self.assertRaisesRegex(MODULE.PreflightError, "terminal report"):
                MODULE.capture_report(serial, identity, 2)

    def test_fixed_storage_identity_change_fails(self) -> None:
        with self.assertRaisesRegex(MODULE.PreflightError, "identity changed"):
            MODULE.parse_report(VALID.replace(b"lun_bytes=253403070464", b"lun_bytes=1"))

    def test_field_reordering_fails(self) -> None:
        changed = VALID.replace(
            b"status=PASS stage=S99_COMPLETE reason=none",
            b"status=PASS reason=none stage=S99_COMPLETE",
        )
        with self.assertRaisesRegex(MODULE.PreflightError, "field order"):
            MODULE.parse_report(changed)

    def test_extra_field_fails(self) -> None:
        with self.assertRaisesRegex(MODULE.PreflightError, "shape"):
            MODULE.parse_report(VALID[:-1] + b" extra=1\n")

    def test_missing_newline_fails(self) -> None:
        with self.assertRaisesRegex(MODULE.PreflightError, "framing"):
            MODULE.parse_report(VALID[:-1])

    def test_crlf_and_headless_fragment_remain_distinguishable(self) -> None:
        with self.assertRaisesRegex(MODULE.PreflightError, "block_mounts identity"):
            MODULE.parse_report(FAILED[:-1] + b"\r\n")
        with self.assertRaisesRegex(MODULE.PreflightError, "shape"):
            MODULE.parse_report(FAILED[40:])

    def test_noncanonical_minimum_fails(self) -> None:
        with self.assertRaisesRegex(MODULE.PreflightError, "outside policy"):
            MODULE.parse_report(
                VALID.replace(
                    b"ext4_minimum_blocks=11695396",
                    b"ext4_minimum_blocks=011695396",
                )
            )

    def test_oversized_minimum_fails(self) -> None:
        with self.assertRaisesRegex(MODULE.PreflightError, "outside policy"):
            MODULE.parse_report(
                VALID.replace(
                    b"ext4_minimum_blocks=11695396",
                    b"ext4_minimum_blocks=51124001",
                )
            )


class IdentityTests(unittest.TestCase):
    def identity(self, location: str = LOCATION) -> MODULE.CORE.AcmIdentity:
        return MODULE.CORE.AcmIdentity("/dev/ttyACM7", location, 123)

    def find(self, products: set[str], identities: list[MODULE.CORE.AcmIdentity]):
        with (
            mock.patch.object(MODULE, "storage_product_locations", return_value=products),
            mock.patch.object(MODULE, "storage_acm_identities", return_value=identities),
        ):
            return MODULE.find_storage_acm(LOCATION)

    def test_one_exact_identity_passes(self) -> None:
        identity = self.identity()
        self.assertEqual(self.find({LOCATION}, [identity]), identity)

    def test_zero_or_multiple_products_fail_closed(self) -> None:
        identity = self.identity()
        for products in (set(), {LOCATION, LOCATION + ".1"}):
            with self.subTest(products=products):
                with self.assertRaisesRegex(MODULE.PreflightError, "exactly one"):
                    self.find(products, [identity])

    def test_zero_or_multiple_acm_interfaces_fail_closed(self) -> None:
        identity = self.identity()
        for identities in ([], [identity, identity]):
            with self.subTest(count=len(identities)):
                with self.assertRaisesRegex(MODULE.PreflightError, "exactly one"):
                    self.find({LOCATION}, identities)

    def test_product_and_acm_mismatch_fails(self) -> None:
        with self.assertRaisesRegex(MODULE.PreflightError, "escaped"):
            self.find({LOCATION}, [self.identity(LOCATION + ".1")])

    def test_wrong_physical_port_fails(self) -> None:
        wrong = LOCATION + ".1"
        with self.assertRaisesRegex(MODULE.PreflightError, "another physical"):
            self.find({wrong}, [self.identity(wrong)])


if __name__ == "__main__":
    unittest.main(verbosity=2)
