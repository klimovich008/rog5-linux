#!/usr/bin/env python3
"""Hostile tests for the authority-free retention-sequence reference."""

from __future__ import annotations

import ast
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import unittest


REPO = Path(__file__).resolve().parents[2]
REFERENCE = REPO / "scripts/host/retention-cycle-sequence-reference.py"
PROFILE = (
    REPO
    / "configs/retention-cycles/host-rendezvous-v3-observer-v1.json"
)
CONSUMER = REPO / "scripts/host/consume-exact-boot-claim.py"
POLICY = REPO / "manifests/temporary-boot-images.tsv"

SPEC = importlib.util.spec_from_file_location(
    "rog5_retention_cycle_sequence_reference", REFERENCE
)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("cannot load retention-cycle sequence reference")
REFERENCE_MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = REFERENCE_MODULE
SPEC.loader.exec_module(REFERENCE_MODULE)


BOOT_ID = "01234567-89ab-cdef-0123-456789abcdef"
FASTBOOT_SERIAL = "M1AIB760D093XYZ"


class RetentionSequenceReferenceTest(unittest.TestCase):
    def new_sequence(self):
        return REFERENCE_MODULE.RetentionSequence()

    def exact_steps(self, sequence):
        return (
            lambda: sequence.preflight(
                execution_exact=True,
                observer_exact=True,
                policy_allow_rows=0,
                claims_registered=False,
            ),
            lambda: sequence.enter_execution_claim(
                REFERENCE_MODULE.EXECUTION_CLAIM.identifier,
                REFERENCE_MODULE.EXECUTION_CLAIM.record,
            ),
            lambda: sequence.boot_execution_recovery(
                REFERENCE_MODULE.EXECUTION_RECOVERY_SHA256,
                rollback_armed=True,
            ),
            lambda: sequence.observe_target(
                REFERENCE_MODULE.CANDIDATE, BOOT_ID
            ),
            lambda: sequence.prove_fallback(
                candidate=REFERENCE_MODULE.CANDIDATE,
                boot_id=BOOT_ID,
                exact_identity=True,
                intent_resolved=True,
            ),
            lambda: sequence.retention_preflight(
                ramoops_exact=True, pstore_empty=True
            ),
            lambda: sequence.prove_bootloader(
                same_port=True,
                product="0b05:4daf",
                anchored_serial=FASTBOOT_SERIAL,
                observed_serial=FASTBOOT_SERIAL,
            ),
            lambda: sequence.enter_observer_claim(
                REFERENCE_MODULE.OBSERVER_CLAIM.identifier,
                REFERENCE_MODULE.OBSERVER_CLAIM.record,
            ),
            lambda: sequence.boot_observer_recovery(
                REFERENCE_MODULE.OBSERVER_RECOVERY_SHA256,
                same_port=True,
                observed_serial=FASTBOOT_SERIAL,
                rollback_armed=True,
            ),
            lambda: sequence.read_postmortem(
                REFERENCE_MODULE.CANDIDATE, BOOT_ID, "MATCH"
            ),
        )

    def advance(self, sequence, count: int) -> None:
        for step in self.exact_steps(sequence)[:count]:
            step()

    def test_reference_binds_current_hold_profile_without_authority(self) -> None:
        profile = json.loads(PROFILE.read_text(encoding="utf-8"))
        self.assertEqual(
            REFERENCE_MODULE.RETENTION_PROFILE, profile["profile"]
        )
        self.assertEqual(
            REFERENCE_MODULE.CANDIDATE, profile["execution"]["candidate"]
        )
        self.assertEqual(
            REFERENCE_MODULE.MANIFEST_SHA256,
            profile["execution"]["runtime_manifest"]["sha256"],
        )
        self.assertEqual(
            REFERENCE_MODULE.EXECUTION_RECOVERY_SHA256,
            profile["execution"]["unsigned_avb"]["sha256"],
        )
        self.assertEqual(
            REFERENCE_MODULE.OBSERVER_RECOVERY_SHA256,
            profile["observer"]["unsigned_avb"]["sha256"],
        )
        self.assertEqual(
            REFERENCE_MODULE.PHYSICAL_SEQUENCE, tuple(profile["sequence"])
        )
        self.assertEqual(profile["claims"]["execution"], "not-defined")
        self.assertEqual(profile["claims"]["observer"], "not-defined")
        self.assertEqual(profile["authority"], "none")
        self.assertEqual(profile["boot_authority"], "none")

        consumer_source = CONSUMER.read_text(encoding="utf-8")
        self.assertNotIn(
            REFERENCE_MODULE.EXECUTION_CLAIM.identifier, consumer_source
        )
        self.assertNotIn(
            REFERENCE_MODULE.OBSERVER_CLAIM.identifier, consumer_source
        )
        rows = [
            line.split("\t")
            for line in POLICY.read_text(encoding="utf-8").splitlines()[1:]
            if line
        ]
        self.assertEqual(sum(row[1] == "allow" for row in rows), 0)

    def test_draft_claims_are_distinct_exact_and_pair_bound(self) -> None:
        execution = REFERENCE_MODULE.EXECUTION_CLAIM
        observer = REFERENCE_MODULE.OBSERVER_CLAIM
        self.assertNotEqual(execution.identifier, observer.identifier)
        self.assertNotEqual(execution.record, observer.record)
        self.assertEqual(
            hashlib.sha256(execution.record).hexdigest(), execution.sha256
        )
        self.assertEqual(
            hashlib.sha256(observer.record).hexdigest(), observer.sha256
        )
        common = {
            "format": "rog5-retention-boot-consumption-v1",
            "retention_profile": REFERENCE_MODULE.RETENTION_PROFILE,
            "cycle_sha256": REFERENCE_MODULE.CYCLE_SHA256,
            "candidate": REFERENCE_MODULE.CANDIDATE,
            "manifest_sha256": REFERENCE_MODULE.MANIFEST_SHA256,
            "state": "BOOT_CLAIMED",
        }
        for claim, role, recovery, peer in (
            (
                execution,
                "execution",
                REFERENCE_MODULE.EXECUTION_RECOVERY_SHA256,
                REFERENCE_MODULE.OBSERVER_RECOVERY_SHA256,
            ),
            (
                observer,
                "observer",
                REFERENCE_MODULE.OBSERVER_RECOVERY_SHA256,
                REFERENCE_MODULE.EXECUTION_RECOVERY_SHA256,
            ),
        ):
            fields = dict(
                line.split("=", 1)
                for line in claim.record.decode("ascii").splitlines()
            )
            self.assertEqual(
                list(fields),
                [
                    "format",
                    "retention_profile",
                    "cycle_sha256",
                    "claim_role",
                    "recovery_profile",
                    "recovery_sha256",
                    "peer_recovery_sha256",
                    "candidate",
                    "manifest_sha256",
                    "state",
                ],
            )
            self.assertEqual(
                {key: fields[key] for key in common}, common
            )
            self.assertEqual(fields["claim_role"], role)
            self.assertEqual(fields["recovery_profile"], claim.identifier)
            self.assertEqual(fields["recovery_sha256"], recovery)
            self.assertEqual(fields["peer_recovery_sha256"], peer)

        descriptor = REFERENCE_MODULE.CYCLE_DESCRIPTOR.decode("ascii")
        self.assertTrue(descriptor.endswith("\n"))
        self.assertEqual(
            hashlib.sha256(REFERENCE_MODULE.CYCLE_DESCRIPTOR).hexdigest(),
            REFERENCE_MODULE.CYCLE_SHA256,
        )
        self.assertIn(
            f"execution_recovery_sha256={REFERENCE_MODULE.EXECUTION_RECOVERY_SHA256}\n",
            descriptor,
        )
        self.assertIn(
            f"observer_recovery_sha256={REFERENCE_MODULE.OBSERVER_RECOVERY_SHA256}\n",
            descriptor,
        )

    def test_happy_path_requires_every_transition_once(self) -> None:
        sequence = self.new_sequence()
        self.advance(sequence, len(self.exact_steps(sequence)))
        report = sequence.finish()
        self.assertEqual(report["phase"], "complete")
        self.assertEqual(report["execution_claim"], "consumed")
        self.assertEqual(report["observer_claim"], "consumed")
        self.assertEqual(report["postmortem_reads"], 1)
        self.assertEqual(report["lineage_result"], "LINEAGE_RETAINED")
        self.assertEqual(report["retry"], "forbidden")
        with self.assertRaisesRegex(
            REFERENCE_MODULE.SequenceError, "sequence is already terminal"
        ):
            sequence.finish()

    def test_every_transition_rejects_wrong_or_weak_evidence(self) -> None:
        sequence = self.new_sequence()
        cases = (
            lambda: sequence.preflight(True, True, 1, False),
            lambda: sequence.preflight(True, True, 0, True),
            lambda: sequence.preflight(False, True, 0, False),
        )
        for attempt in cases:
            with self.assertRaises(REFERENCE_MODULE.SequenceError):
                attempt()
        self.exact_steps(sequence)[0]()

        for identifier, record in (
            (
                REFERENCE_MODULE.OBSERVER_CLAIM.identifier,
                REFERENCE_MODULE.EXECUTION_CLAIM.record,
            ),
            (
                REFERENCE_MODULE.EXECUTION_CLAIM.identifier,
                REFERENCE_MODULE.EXECUTION_CLAIM.record + b"extra=1\n",
            ),
        ):
            with self.assertRaises(REFERENCE_MODULE.SequenceError):
                sequence.enter_execution_claim(identifier, record)
        self.exact_steps(sequence)[1]()
        with self.assertRaises(REFERENCE_MODULE.SequenceError):
            sequence.boot_execution_recovery(
                REFERENCE_MODULE.OBSERVER_RECOVERY_SHA256, True
            )
        with self.assertRaises(REFERENCE_MODULE.SequenceError):
            sequence.boot_execution_recovery(
                REFERENCE_MODULE.EXECUTION_RECOVERY_SHA256, False
            )
        self.exact_steps(sequence)[2]()
        for candidate, boot_id in (
            ("wrong", BOOT_ID),
            (REFERENCE_MODULE.CANDIDATE, "not-a-boot-id"),
        ):
            with self.assertRaises(REFERENCE_MODULE.SequenceError):
                sequence.observe_target(candidate, boot_id)
        self.exact_steps(sequence)[3]()
        for exact, resolved in ((False, True), (True, False)):
            with self.assertRaises(REFERENCE_MODULE.SequenceError):
                sequence.prove_fallback(
                    candidate=REFERENCE_MODULE.CANDIDATE,
                    boot_id=BOOT_ID,
                    exact_identity=exact,
                    intent_resolved=resolved,
                )
        self.exact_steps(sequence)[4]()
        for ramoops, empty in ((False, True), (True, False)):
            with self.assertRaises(REFERENCE_MODULE.SequenceError):
                sequence.retention_preflight(ramoops, empty)
        self.exact_steps(sequence)[5]()
        for same_port, product, observed in (
            (False, "0b05:4daf", FASTBOOT_SERIAL),
            (True, "0b05:0000", FASTBOOT_SERIAL),
            (True, "0b05:4daf", "replacement"),
        ):
            with self.assertRaises(REFERENCE_MODULE.SequenceError):
                sequence.prove_bootloader(
                    same_port,
                    product,
                    FASTBOOT_SERIAL,
                    observed,
                )
        self.exact_steps(sequence)[6]()
        for identifier, record in (
            (
                REFERENCE_MODULE.EXECUTION_CLAIM.identifier,
                REFERENCE_MODULE.OBSERVER_CLAIM.record,
            ),
            (
                REFERENCE_MODULE.OBSERVER_CLAIM.identifier,
                REFERENCE_MODULE.OBSERVER_CLAIM.record + b"extra=1\n",
            ),
        ):
            with self.assertRaises(REFERENCE_MODULE.SequenceError):
                sequence.enter_observer_claim(identifier, record)
        self.exact_steps(sequence)[7]()
        for recovery, same_port, serial, rollback in (
            (
                REFERENCE_MODULE.EXECUTION_RECOVERY_SHA256,
                True,
                FASTBOOT_SERIAL,
                True,
            ),
            (
                REFERENCE_MODULE.OBSERVER_RECOVERY_SHA256,
                False,
                FASTBOOT_SERIAL,
                True,
            ),
            (
                REFERENCE_MODULE.OBSERVER_RECOVERY_SHA256,
                True,
                "replacement",
                True,
            ),
            (
                REFERENCE_MODULE.OBSERVER_RECOVERY_SHA256,
                True,
                FASTBOOT_SERIAL,
                False,
            ),
        ):
            with self.assertRaises(REFERENCE_MODULE.SequenceError):
                sequence.boot_observer_recovery(
                    recovery, same_port, serial, rollback
                )
        self.exact_steps(sequence)[8]()
        for candidate, boot_id, classification in (
            ("wrong", BOOT_ID, "MATCH"),
            (REFERENCE_MODULE.CANDIDATE, "wrong", "MATCH"),
            (REFERENCE_MODULE.CANDIDATE, BOOT_ID, "SUCCESS"),
        ):
            with self.assertRaises(REFERENCE_MODULE.SequenceError):
                sequence.read_postmortem(candidate, boot_id, classification)
        self.exact_steps(sequence)[9]()

    def test_out_of_order_duplicate_and_retry_paths_are_absent(self) -> None:
        sequence = self.new_sequence()
        with self.assertRaisesRegex(
            REFERENCE_MODULE.SequenceError, "expected preflight"
        ):
            sequence.enter_execution_claim(
                REFERENCE_MODULE.EXECUTION_CLAIM.identifier,
                REFERENCE_MODULE.EXECUTION_CLAIM.record,
            )
        self.exact_steps(sequence)[0]()
        with self.assertRaisesRegex(
            REFERENCE_MODULE.SequenceError, "expected execution-claim"
        ):
            sequence.enter_observer_claim(
                REFERENCE_MODULE.OBSERVER_CLAIM.identifier,
                REFERENCE_MODULE.OBSERVER_CLAIM.record,
            )
        self.exact_steps(sequence)[1]()
        with self.assertRaisesRegex(
            REFERENCE_MODULE.SequenceError, "expected execution-recovery"
        ):
            sequence.enter_execution_claim(
                REFERENCE_MODULE.EXECUTION_CLAIM.identifier,
                REFERENCE_MODULE.EXECUTION_CLAIM.record,
            )

    def test_each_failure_boundary_has_exact_irreversible_disposition(self) -> None:
        for completed_steps in range(11):
            with self.subTest(completed_steps=completed_steps):
                sequence = self.new_sequence()
                self.advance(sequence, completed_steps)
                terminal = sequence.terminate("injected-offline-failure")
                execution = "consumed" if completed_steps >= 2 else "absent"
                observer = "consumed" if completed_steps >= 8 else "absent"
                result = "UNKNOWN" if completed_steps >= 2 else "NO_BOOT"
                retry = (
                    "forbidden" if completed_steps >= 2 else "not-applicable"
                )
                self.assertEqual(terminal["execution_claim"], execution)
                self.assertEqual(terminal["observer_claim"], observer)
                self.assertEqual(terminal["retry"], retry)
                self.assertEqual(terminal["result"], result)
                with self.assertRaisesRegex(
                    REFERENCE_MODULE.SequenceError,
                    "sequence is already terminal",
                ):
                    sequence.terminate("second-failure")

    def test_missing_or_ambiguous_pstore_remains_inconclusive(self) -> None:
        classifications = {
            "UNAVAILABLE": "INCONCLUSIVE",
            "NO_RECORDS": "INCONCLUSIVE",
            "NO_MARKER": "INCONCLUSIVE",
            "AMBIGUOUS": "INCONCLUSIVE",
            "DIFFERENT_MARKER": "INCONCLUSIVE",
            "MATCH": "LINEAGE_RETAINED",
            "MATCH_REPEATED": "LINEAGE_RETAINED",
        }
        for classification, expected in classifications.items():
            with self.subTest(classification=classification):
                sequence = self.new_sequence()
                self.advance(sequence, 9)
                sequence.read_postmortem(
                    REFERENCE_MODULE.CANDIDATE,
                    BOOT_ID,
                    classification,
                )
                report = sequence.finish()
                self.assertEqual(report["lineage_result"], expected)
                self.assertNotIn("NO_CRASH", report.values())

    def test_reference_has_no_device_credential_or_execution_surface(self) -> None:
        source = REFERENCE.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(REFERENCE))
        imported = set()
        for node in tree.body:
            if isinstance(node, ast.Import):
                imported.update(
                    alias.name.split(".", 1)[0] for alias in node.names
                )
            elif isinstance(node, ast.ImportFrom):
                imported.add((node.module or "").split(".", 1)[0])
        self.assertTrue(
            imported <= {"__future__", "dataclasses", "hashlib", "json", "re", "sys"}
        )
        for token in (
            "subprocess",
            "os.system",
            "Popen",
            "ssh ",
            "/usr/bin/fastboot",
            "consume-exact-boot-claim.py",
        ):
            self.assertNotIn(token, source)
        result = subprocess.run(
            [sys.executable, str(REFERENCE), "plan"],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        plan = json.loads(result.stdout)
        self.assertEqual(plan["implementation"], "reference-only")
        self.assertEqual(plan["authority"], "none")
        self.assertEqual(plan["boot_authority"], "none")
        self.assertFalse(plan["claims_registered"])
        self.assertEqual(plan["policy_allow_rows"], 0)
        self.assertEqual(result.stderr, "")


if __name__ == "__main__":
    unittest.main(verbosity=2)
