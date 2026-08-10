#!/usr/bin/env python3
"""Hostile tests for the offline retention-cycle transaction journal."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest


REPO = Path(__file__).resolve().parents[2]
SOURCE = REPO / "scripts/host/retention-cycle-transaction.py"
REFERENCE_SOURCE = (
    REPO / "scripts/host/retention-cycle-sequence-reference.py"
)


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


MODULE = load_module("rog5_retention_cycle_transaction", SOURCE)
REFERENCE = load_module("rog5_retention_cycle_reference_for_journal", REFERENCE_SOURCE)

HOST_BOOT_ID = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
TARGET_BOOT_ID = "01234567-89ab-cdef-0123-456789abcdef"
FALLBACK_BOOT_ID = "fedcba98-7654-3210-fedc-ba9876543210"
USB_LOCATION = "pci0000:00/0000:00:14.0/usb1/1-3"
FASTBOOT_SERIAL = "M1AIB760D093XYZ"


class RetentionCycleTransactionTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.base = Path(self.temporary.name)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def root(self, name: str = "state") -> Path:
        root = self.base / name
        root.mkdir(mode=0o700)
        return root

    def create(self, name: str = "state"):
        return MODULE.CycleJournal.create(
            self.root(name), HOST_BOOT_ID, USB_LOCATION
        )

    def exact_steps(self, journal):
        return (
            journal.execution_claim_intent,
            lambda: journal.execution_claim_entered(
                REFERENCE.EXECUTION_CLAIM.identifier,
                REFERENCE.EXECUTION_CLAIM.sha256,
            ),
            lambda: journal.execution_boot_intent(
                REFERENCE.EXECUTION_RECOVERY_SHA256,
                USB_LOCATION,
                True,
            ),
            lambda: journal.execution_recovery_observed(
                REFERENCE.EXECUTION_RECOVERY_SHA256,
                USB_LOCATION,
                True,
            ),
            lambda: journal.target_observed(
                REFERENCE.CANDIDATE, TARGET_BOOT_ID, USB_LOCATION
            ),
            lambda: journal.fallback_observed(
                REFERENCE.CANDIDATE,
                TARGET_BOOT_ID,
                FALLBACK_BOOT_ID,
                USB_LOCATION,
                "1d6b:0104",
                "ROG5LINUX",
                True,
                True,
            ),
            lambda: journal.retention_preflight(
                FALLBACK_BOOT_ID, USB_LOCATION, True, True
            ),
            lambda: journal.bootloader_transition_intent(
                FALLBACK_BOOT_ID, USB_LOCATION
            ),
            lambda: journal.bootloader_observed(
                USB_LOCATION, "0b05:4daf", FASTBOOT_SERIAL
            ),
            journal.observer_claim_intent,
            lambda: journal.observer_claim_entered(
                REFERENCE.OBSERVER_CLAIM.identifier,
                REFERENCE.OBSERVER_CLAIM.sha256,
            ),
            lambda: journal.observer_boot_intent(
                REFERENCE.OBSERVER_RECOVERY_SHA256,
                USB_LOCATION,
                FASTBOOT_SERIAL,
                True,
            ),
            lambda: journal.observer_recovery_observed(
                REFERENCE.OBSERVER_RECOVERY_SHA256,
                USB_LOCATION,
                FASTBOOT_SERIAL,
                True,
            ),
            lambda: journal.postmortem_read_intent(
                REFERENCE.CANDIDATE, TARGET_BOOT_ID
            ),
            lambda: journal.postmortem_result(
                REFERENCE.CANDIDATE, TARGET_BOOT_ID, "MATCH", 1
            ),
            journal.finish,
        )

    def advance(self, journal, count: int) -> None:
        for step in self.exact_steps(journal)[:count]:
            step()

    def test_happy_path_is_private_hash_chained_and_reloadable(self) -> None:
        root = self.root()
        with MODULE.CycleJournal.create(
            root, HOST_BOOT_ID, USB_LOCATION
        ) as journal:
            self.advance(journal, len(self.exact_steps(journal)))
            snapshot = journal.snapshot()
            self.assertEqual(snapshot["phase"], "complete")
            self.assertEqual(snapshot["execution_claim"], "consumed")
            self.assertEqual(snapshot["observer_claim"], "consumed")
            self.assertEqual(snapshot["postmortem_reads"], 1)
            self.assertEqual(snapshot["lineage_result"], "LINEAGE_RETAINED")
            self.assertEqual(snapshot["retry"], "forbidden")
            event_paths = journal.event_paths()

        previous = "0" * 64
        for index, path in enumerate(event_paths):
            metadata = path.lstat()
            self.assertEqual(metadata.st_uid, os.geteuid())
            self.assertEqual(metadata.st_mode & 0o777, 0o600)
            self.assertEqual(metadata.st_nlink, 1)
            payload = path.read_bytes()
            self.assertTrue(payload.endswith(b"\n"))
            value = json.loads(payload)
            self.assertEqual(
                payload,
                (
                    json.dumps(
                        value,
                        sort_keys=True,
                        separators=(",", ":"),
                        ensure_ascii=True,
                    )
                    + "\n"
                ).encode("ascii"),
            )
            self.assertEqual(value["index"], index)
            self.assertEqual(value["previous_sha256"], previous)
            previous = hashlib.sha256(payload).hexdigest()

        with MODULE.CycleJournal.open(root) as reloaded:
            self.assertEqual(reloaded.snapshot(), snapshot)
            with self.assertRaisesRegex(
                MODULE.TransactionError, "already terminal"
            ):
                reloaded.finish()

    def test_every_crash_prefix_reconstructs_exact_claim_disposition(self) -> None:
        for count in range(17):
            with self.subTest(count=count):
                root = self.root(f"prefix-{count}")
                with MODULE.CycleJournal.create(
                    root, HOST_BOOT_ID, USB_LOCATION
                ) as journal:
                    self.advance(journal, count)
                    before = journal.snapshot()
                with MODULE.CycleJournal.open(root) as reloaded:
                    after = reloaded.snapshot()
                    self.assertEqual(after, before)
                    expected_execution = (
                        "consumed"
                        if count >= 2
                        else "unknown" if count >= 1 else "absent"
                    )
                    expected_observer = (
                        "consumed"
                        if count >= 11
                        else "unknown" if count >= 10 else "absent"
                    )
                    self.assertEqual(
                        after["execution_claim"], expected_execution
                    )
                    self.assertEqual(after["observer_claim"], expected_observer)
                    if count >= 2:
                        self.assertEqual(after["retry"], "forbidden")

    def test_reopened_action_intent_is_terminal_not_retried(self) -> None:
        intent_counts = (1, 3, 8, 10, 12, 14)
        for count in intent_counts:
            with self.subTest(count=count):
                root = self.root(f"intent-{count}")
                with MODULE.CycleJournal.create(
                    root, HOST_BOOT_ID, USB_LOCATION
                ) as journal:
                    self.advance(journal, count)
                with MODULE.CycleJournal.open(root) as reloaded:
                    next_step = self.exact_steps(reloaded)[count]
                    with self.assertRaisesRegex(
                        MODULE.TransactionError,
                        "ambiguous action intent",
                    ):
                        next_step()
                    terminal = reloaded.terminate("host-process-lost")
                    self.assertEqual(terminal["phase"], "terminated")
                    self.assertEqual(terminal["retry"], "forbidden")

    def test_postmortem_read_intent_consumes_the_only_read_budget(self) -> None:
        root = self.root()
        with MODULE.CycleJournal.create(
            root, HOST_BOOT_ID, USB_LOCATION
        ) as journal:
            self.advance(journal, 14)
            self.assertEqual(journal.snapshot()["postmortem_reads"], "unknown")
        with MODULE.CycleJournal.open(root) as reloaded:
            with self.assertRaisesRegex(
                MODULE.TransactionError, "ambiguous action intent"
            ):
                reloaded.postmortem_result(
                    REFERENCE.CANDIDATE, TARGET_BOOT_ID, "MATCH", 1
                )
            terminal = reloaded.terminate("postmortem-result-lost")
            self.assertEqual(terminal["lineage_result"], "INCONCLUSIVE")
            self.assertEqual(terminal["postmortem_reads"], "unknown")

    def test_port_serial_boot_ids_and_rollback_are_immutable(self) -> None:
        with self.create() as journal:
            self.advance(journal, 2)
            for recovery, location, rollback in (
                (REFERENCE.OBSERVER_RECOVERY_SHA256, USB_LOCATION, True),
                (REFERENCE.EXECUTION_RECOVERY_SHA256, "1-9", True),
                (REFERENCE.EXECUTION_RECOVERY_SHA256, USB_LOCATION, False),
            ):
                with self.assertRaises(MODULE.TransactionError):
                    journal.execution_boot_intent(
                        recovery, location, rollback
                    )
            self.exact_steps(journal)[2]()
            self.exact_steps(journal)[3]()
            self.exact_steps(journal)[4]()
            for fallback_id, location, product, serial in (
                (TARGET_BOOT_ID, USB_LOCATION, "1d6b:0104", "ROG5LINUX"),
                (FALLBACK_BOOT_ID, "1-9", "1d6b:0104", "ROG5LINUX"),
                (FALLBACK_BOOT_ID, USB_LOCATION, "0b05:4daf", "ROG5LINUX"),
                (FALLBACK_BOOT_ID, USB_LOCATION, "1d6b:0104", "replacement"),
            ):
                with self.assertRaises(MODULE.TransactionError):
                    journal.fallback_observed(
                        REFERENCE.CANDIDATE,
                        TARGET_BOOT_ID,
                        fallback_id,
                        location,
                        product,
                        serial,
                        True,
                        True,
                    )
            self.exact_steps(journal)[5]()
            for step in self.exact_steps(journal)[6:8]:
                step()
            for location, product, serial in (
                ("1-9", "0b05:4daf", FASTBOOT_SERIAL),
                (USB_LOCATION, "0b05:0000", FASTBOOT_SERIAL),
                (USB_LOCATION, "0b05:4daf", "bad serial with spaces"),
            ):
                with self.assertRaises(MODULE.TransactionError):
                    journal.bootloader_observed(location, product, serial)

    def test_tampering_links_unknown_entries_and_weak_modes_fail_closed(self) -> None:
        root = self.root("tamper")
        with MODULE.CycleJournal.create(
            root, HOST_BOOT_ID, USB_LOCATION
        ) as journal:
            first = journal.event_paths()[0]
        first.write_bytes(first.read_bytes().replace(b"none", b"NONE", 1))
        with self.assertRaises(MODULE.TransactionError):
            MODULE.CycleJournal.open(root)

        root = self.root("hardlink")
        with MODULE.CycleJournal.create(
            root, HOST_BOOT_ID, USB_LOCATION
        ) as journal:
            first = journal.event_paths()[0]
        os.link(first, self.base / "alias")
        with self.assertRaises(MODULE.TransactionError):
            MODULE.CycleJournal.open(root)

        root = self.root("unknown")
        with MODULE.CycleJournal.create(
            root, HOST_BOOT_ID, USB_LOCATION
        ) as journal:
            cycle = journal.cycle_path
        (cycle / "unexpected").write_text("x", encoding="ascii")
        with self.assertRaises(MODULE.TransactionError):
            MODULE.CycleJournal.open(root)

        root = self.root("weak")
        with MODULE.CycleJournal.create(
            root, HOST_BOOT_ID, USB_LOCATION
        ):
            pass
        root.chmod(0o755)
        with self.assertRaises(MODULE.TransactionError):
            MODULE.CycleJournal.open(root)

    def test_gaps_reordering_and_noncanonical_json_fail_closed(self) -> None:
        root = self.root("gap")
        with MODULE.CycleJournal.create(
            root, HOST_BOOT_ID, USB_LOCATION
        ) as journal:
            journal.execution_claim_intent()
            paths = journal.event_paths()
        paths[1].rename(paths[1].with_name("02-execution-claim-entered.json"))
        with self.assertRaises(MODULE.TransactionError):
            MODULE.CycleJournal.open(root)

        root = self.root("json")
        with MODULE.CycleJournal.create(
            root, HOST_BOOT_ID, USB_LOCATION
        ) as journal:
            first = journal.event_paths()[0]
        value = json.loads(first.read_text(encoding="ascii"))
        first.write_text(json.dumps(value) + "\n", encoding="ascii")
        with self.assertRaises(MODULE.TransactionError):
            MODULE.CycleJournal.open(root)

    def test_concurrent_open_and_path_replacement_are_refused(self) -> None:
        root = self.root()
        journal = MODULE.CycleJournal.create(
            root, HOST_BOOT_ID, USB_LOCATION
        )
        try:
            with self.assertRaisesRegex(
                MODULE.TransactionError, "transaction is already open"
            ):
                MODULE.CycleJournal.open(root)
            displaced = self.base / "displaced"
            root.rename(displaced)
            root.mkdir(mode=0o700)
            with self.assertRaisesRegex(
                MODULE.TransactionError, "root changed"
            ):
                journal.execution_claim_intent()
        finally:
            journal.close()

    def test_source_has_no_live_device_credential_or_claim_surface(self) -> None:
        source = SOURCE.read_text(encoding="utf-8")
        for token in (
            "subprocess",
            "socket",
            "paramiko",
            "/usr/bin/fastboot",
            "fastboot boot",
            "ssh ",
            "SSH_KEY",
            "KNOWN_HOSTS",
            "consume-exact-boot-claim.py",
            "ALLOW_TEMPORARY_BOOT",
            "/sys/",
            "/dev/",
        ):
            self.assertNotIn(token, source)
        self.assertNotIn("if __name__ ==", source)
        self.assertEqual(MODULE.CYCLE_SHA256, REFERENCE.CYCLE_SHA256)
        self.assertEqual(
            MODULE.EXECUTION_CLAIM_SHA256,
            REFERENCE.EXECUTION_CLAIM.sha256,
        )
        self.assertEqual(
            MODULE.OBSERVER_CLAIM_SHA256,
            REFERENCE.OBSERVER_CLAIM.sha256,
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
