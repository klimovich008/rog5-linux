#!/usr/bin/env python3
"""Hostile tests for the callback-only retention-cycle adapter."""

from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest


REPO = Path(__file__).resolve().parents[2]
ADAPTER_SOURCE = REPO / "scripts/host/retention-cycle-adapter.py"
JOURNAL_SOURCE = REPO / "scripts/host/retention-cycle-transaction.py"
REFERENCE_SOURCE = (
    REPO / "scripts/host/retention-cycle-sequence-reference.py"
)
PROFILE = (
    REPO
    / "configs/retention-cycles/host-rendezvous-v3-observer-v1.json"
)
POLICY = REPO / "manifests/temporary-boot-images.tsv"
CONSUMER = REPO / "scripts/host/consume-exact-boot-claim.py"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


ADAPTER = load_module("rog5_retention_cycle_adapter", ADAPTER_SOURCE)
JOURNAL = load_module("rog5_retention_cycle_journal_for_adapter", JOURNAL_SOURCE)
REFERENCE = load_module("rog5_retention_cycle_reference_for_adapter", REFERENCE_SOURCE)

HOST_BOOT_ID = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
TARGET_BOOT_ID = "01234567-89ab-cdef-0123-456789abcdef"
FALLBACK_BOOT_ID = "fedcba98-7654-3210-fedc-ba9876543210"
USB_LOCATION = "pci0000:00/0000:00:14.0/usb1/1-3"
FASTBOOT_SERIAL = "M1AIB760D093XYZ"


class RecordingExecutor:
    def __init__(self, journal, *, fail_at: int | None = None) -> None:
        self.journal = journal
        self.fail_at = fail_at
        self.calls: list[tuple[object, dict[str, object], bytes]] = []

    def __call__(self, invocation):
        snapshot = self.journal.snapshot()
        last_event = self.journal.event_paths()[-1].read_bytes()
        self.calls.append((invocation, snapshot, last_event))
        if self.fail_at == len(self.calls) - 1:
            raise RuntimeError("injected fixture failure")
        return exact_result(invocation.name)


def exact_result(name: str) -> dict[str, object]:
    values = {
        "execution-claim": {
            "identifier": REFERENCE.EXECUTION_CLAIM.identifier,
            "record_sha256": REFERENCE.EXECUTION_CLAIM.sha256,
            "state": "consumed",
        },
        "execution-boot": {
            "recovery_sha256": REFERENCE.EXECUTION_RECOVERY_SHA256,
            "rollback_armed": True,
            "usb_location": USB_LOCATION,
        },
        "fallback-reboot": {
            "fastboot_serial": FASTBOOT_SERIAL,
            "product": "0b05:4daf",
            "usb_location": USB_LOCATION,
        },
        "observer-claim": {
            "identifier": REFERENCE.OBSERVER_CLAIM.identifier,
            "record_sha256": REFERENCE.OBSERVER_CLAIM.sha256,
            "state": "consumed",
        },
        "observer-boot": {
            "fastboot_serial": FASTBOOT_SERIAL,
            "recovery_sha256": REFERENCE.OBSERVER_RECOVERY_SHA256,
            "rollback_armed": True,
            "usb_location": USB_LOCATION,
        },
        "postmortem-read": {
            "candidate": REFERENCE.CANDIDATE,
            "classification": "MATCH",
            "reads": 1,
            "target_boot_id": TARGET_BOOT_ID,
        },
    }
    return dict(values[name])


class RetentionCycleAdapterTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name) / "state"
        self.root.mkdir(mode=0o700)
        self.journal = JOURNAL.CycleJournal.create(
            self.root, HOST_BOOT_ID, USB_LOCATION
        )
        self.evidence = ADAPTER.CycleEvidence(
            target_boot_id=TARGET_BOOT_ID,
            fallback_boot_id=FALLBACK_BOOT_ID,
            usb_location=USB_LOCATION,
            fastboot_serial=FASTBOOT_SERIAL,
            postmortem_classification="MATCH",
        )

    def tearDown(self) -> None:
        self.journal.close()
        self.temporary.cleanup()

    def test_exact_callbacks_follow_durable_intents(self) -> None:
        executor = RecordingExecutor(self.journal)
        result = ADAPTER.CycleAdapter(self.journal, executor).run(
            self.evidence
        )
        expected_names = (
            "execution-claim",
            "execution-boot",
            "fallback-reboot",
            "observer-claim",
            "observer-boot",
            "postmortem-read",
        )
        expected_phases = (
            "execution-claim-intent",
            "execution-boot-intent",
            "bootloader-transition-intent",
            "observer-claim-intent",
            "observer-boot-intent",
            "postmortem-read-intent",
        )
        self.assertEqual(
            tuple(call[0].name for call in executor.calls), expected_names
        )
        self.assertEqual(
            tuple(call[1]["phase"] for call in executor.calls),
            expected_phases,
        )
        for (_, snapshot, payload), expected in zip(
            executor.calls, expected_phases, strict=True
        ):
            event = json.loads(payload)
            self.assertEqual(event["name"], expected)
            self.assertEqual(snapshot["phase"], expected)
        self.assertEqual(result["phase"], "complete")
        self.assertEqual(result["lineage_result"], "LINEAGE_RETAINED")
        self.assertEqual(result["postmortem_reads"], 1)
        self.assertEqual(len(executor.calls), 6)

    def test_every_callback_failure_leaves_one_nonretryable_intent(self) -> None:
        for failure in range(6):
            with self.subTest(failure=failure):
                if failure:
                    self.journal.close()
                    self.temporary.cleanup()
                    self.setUp()
                executor = RecordingExecutor(
                    self.journal, fail_at=failure
                )
                with self.assertRaisesRegex(
                    ADAPTER.AdapterError, "fixture callback failed"
                ):
                    ADAPTER.CycleAdapter(self.journal, executor).run(
                        self.evidence
                    )
                phase = self.journal.snapshot()["phase"]
                self.assertEqual(
                    phase,
                    ADAPTER.INVOCATIONS[failure].required_intent,
                )
                self.journal.close()
                reopened = JOURNAL.CycleJournal.open(self.root)
                try:
                    second = RecordingExecutor(reopened)
                    with self.assertRaisesRegex(
                        ADAPTER.AdapterError, "fresh cycle-opened"
                    ):
                        ADAPTER.CycleAdapter(reopened, second).run(
                            self.evidence
                        )
                    self.assertEqual(second.calls, [])
                    terminal = reopened.terminate("fixture-callback-lost")
                    self.assertEqual(terminal["phase"], "terminated")
                    self.assertEqual(terminal["lineage_result"], "INCONCLUSIVE")
                finally:
                    reopened.close()
                self.journal = reopened

    def test_hostile_results_never_cross_the_intent_boundary(self) -> None:
        mutations = (
            {},
            {"unexpected": True},
            {
                "identifier": REFERENCE.EXECUTION_CLAIM.identifier,
                "record_sha256": REFERENCE.EXECUTION_CLAIM.sha256,
                "state": "pending",
            },
            {
                "identifier": REFERENCE.EXECUTION_CLAIM.identifier,
                "record_sha256": REFERENCE.EXECUTION_CLAIM.sha256,
                "state": b"consumed",
            },
        )
        for index, mutation in enumerate(mutations):
            with self.subTest(index=index):
                if index:
                    self.journal.close()
                    self.temporary.cleanup()
                    self.setUp()

                class HostileExecutor:
                    def __init__(self) -> None:
                        self.calls = 0

                    def __call__(self, invocation):
                        self.calls += 1
                        return mutation

                executor = HostileExecutor()
                with self.assertRaises(ADAPTER.AdapterError):
                    ADAPTER.CycleAdapter(self.journal, executor).run(
                        self.evidence
                    )
                self.assertEqual(executor.calls, 1)
                self.assertEqual(
                    self.journal.snapshot()["phase"],
                    "execution-claim-intent",
                )

    def test_invalid_evidence_fails_before_any_intent_or_callback(self) -> None:
        hostile = (
            {"target_boot_id": "bad"},
            {"fallback_boot_id": TARGET_BOOT_ID},
            {"usb_location": "1-9"},
            {"fastboot_serial": "bad serial"},
            {"postmortem_classification": "NO_CRASH"},
        )
        for index, changes in enumerate(hostile):
            with self.subTest(changes=changes):
                if index:
                    self.journal.close()
                    self.temporary.cleanup()
                    self.setUp()
                values = {
                    "target_boot_id": TARGET_BOOT_ID,
                    "fallback_boot_id": FALLBACK_BOOT_ID,
                    "usb_location": USB_LOCATION,
                    "fastboot_serial": FASTBOOT_SERIAL,
                    "postmortem_classification": "MATCH",
                }
                values.update(changes)
                evidence = ADAPTER.CycleEvidence(**values)
                executor = RecordingExecutor(self.journal)
                with self.assertRaises(ADAPTER.AdapterError):
                    ADAPTER.CycleAdapter(self.journal, executor).run(evidence)
                self.assertEqual(executor.calls, [])
                self.assertEqual(
                    self.journal.snapshot()["phase"], "cycle-opened"
                )

    def test_boolean_integer_alias_cannot_satisfy_a_result(self) -> None:
        class BooleanAliasExecutor:
            def __init__(self) -> None:
                self.calls = 0

            def __call__(self, invocation):
                self.calls += 1
                result = exact_result(invocation.name)
                if invocation.name == "execution-boot":
                    result["rollback_armed"] = 1
                return result

        executor = BooleanAliasExecutor()
        with self.assertRaisesRegex(
            ADAPTER.AdapterError, "result is not exact: execution-boot"
        ):
            ADAPTER.CycleAdapter(self.journal, executor).run(self.evidence)
        self.assertEqual(executor.calls, 2)
        self.assertEqual(
            self.journal.snapshot()["phase"], "execution-boot-intent"
        )

    def test_invocation_descriptors_are_exact_and_repository_owned(self) -> None:
        expected = (
            (
                "execution-claim",
                "scripts/host/consume-exact-boot-claim.py",
                (REFERENCE.EXECUTION_CLAIM.identifier,),
                "execution-claim-intent",
            ),
            (
                "execution-boot",
                "scripts/host/run-stable-recovery-live-gate.sh",
                ("boot",),
                "execution-boot-intent",
            ),
            (
                "fallback-reboot",
                "scripts/host/fallback-acm-control.py",
                ("reboot", ADAPTER.FALLBACK_PIN_TOKEN),
                "bootloader-transition-intent",
            ),
            (
                "observer-claim",
                "scripts/host/consume-exact-boot-claim.py",
                (REFERENCE.OBSERVER_CLAIM.identifier,),
                "observer-claim-intent",
            ),
            (
                "observer-boot",
                "scripts/host/run-observation-recovery-live-gate.sh",
                ("boot",),
                "observer-boot-intent",
            ),
            (
                "postmortem-read",
                "scripts/host/stable-recovery-control.py",
                (
                    "postmortem-status",
                    REFERENCE.CANDIDATE,
                    TARGET_BOOT_ID,
                ),
                "postmortem-read-intent",
            ),
        )
        observed = tuple(
            (
                item.name,
                item.program,
                item.resolve_arguments(TARGET_BOOT_ID),
                item.required_intent,
            )
            for item in ADAPTER.INVOCATIONS
        )
        self.assertEqual(observed, expected)
        for _, program, _, _ in expected:
            path = REPO / program
            self.assertTrue(path.is_file())
            self.assertFalse(path.is_symlink())

    def test_adapter_is_offline_only_and_hold_remains_exact(self) -> None:
        source = ADAPTER_SOURCE.read_text(encoding="utf-8")
        for token in (
            "subprocess",
            "socket",
            "Popen",
            "os.system",
            "SSH_KEY",
            "KNOWN_HOSTS",
            "ALLOW_TEMPORARY_BOOT",
            "/sys/",
            "/dev/",
        ):
            self.assertNotIn(token, source)
        self.assertNotIn("if __name__ ==", source)
        profile = json.loads(PROFILE.read_text(encoding="utf-8"))
        self.assertEqual(profile["state"], "hold")
        self.assertEqual(profile["authority"], "none")
        self.assertEqual(profile["boot_authority"], "none")
        self.assertEqual(profile["claims"]["execution"], "not-defined")
        self.assertEqual(profile["claims"]["observer"], "not-defined")
        rows = [
            line.split("\t")
            for line in POLICY.read_text(encoding="utf-8").splitlines()[1:]
            if line
        ]
        self.assertEqual(
            sum(
                row[0]
                == "build/observation-recovery-mainline-udc-v11-generation10-20260811-r1/repack/stable-recovery-a.avb.img"
                and row[1] == "allow"
                for row in rows
            ),
            1,
        )
        consumer = CONSUMER.read_text(encoding="utf-8")
        self.assertIn(
            REFERENCE.EXECUTION_CLAIM.identifier, consumer
        )
        self.assertIn(REFERENCE.OBSERVER_CLAIM.identifier, consumer)


if __name__ == "__main__":
    unittest.main(verbosity=2)
