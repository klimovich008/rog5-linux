#!/usr/bin/env python3
"""Hardware-free checks for the journaled retention-cycle runner."""

from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import stat
import sys
import tempfile
import unittest
from unittest import mock


REPO = Path(__file__).resolve().parents[2]
SOURCE = REPO / "scripts/host/run-retention-cycle-live.py"
SPEC = importlib.util.spec_from_file_location(
    "rog5_retention_cycle_live_test_subject", SOURCE
)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("cannot load retention-cycle live runner")
LIVE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = LIVE
SPEC.loader.exec_module(LIVE)


class RetentionCycleLiveTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.state = Path(self.temporary.name) / "state"
        self.root = self.state / "rog5-temporary-boot-consumption"

    def claim_paths(self, identifier: str) -> tuple[Path, Path, Path]:
        source = self.root / f"{identifier}.record"
        return (
            source,
            Path(f"{source}.entered"),
            self.state
            / f".rog5-temporary-boot-consumption.{identifier}.entered",
        )

    def test_prepare_is_all_or_none_before_first_publication(self) -> None:
        self.root.mkdir(parents=True, mode=0o700)
        observer_source, _entered, _guard = self.claim_paths(LIVE.OBSERVER_ID)
        observer_source.write_bytes(LIVE.CLAIMS.expected_record(LIVE.OBSERVER_ID))
        observer_source.chmod(0o600)
        with (
            mock.patch.object(
                LIVE.CLAIMS, "canonical_claim_root", return_value=self.root
            ),
            self.assertRaisesRegex(LIVE.LiveCycleError, "already exists"),
        ):
            LIVE.prepare_claims()
        execution_source, _entered, _guard = self.claim_paths(LIVE.EXECUTION_ID)
        self.assertFalse(execution_source.exists())

    def test_prepare_publishes_both_exact_sources_once(self) -> None:
        with mock.patch.object(
            LIVE.CLAIMS, "canonical_claim_root", return_value=self.root
        ):
            LIVE.prepare_claims()
            with self.assertRaisesRegex(LIVE.LiveCycleError, "already exists"):
                LIVE.prepare_claims()
        for identifier in (LIVE.EXECUTION_ID, LIVE.OBSERVER_ID):
            source, entered, guard = self.claim_paths(identifier)
            self.assertEqual(
                source.read_bytes(), LIVE.CLAIMS.expected_record(identifier)
            )
            self.assertEqual(stat.S_IMODE(source.stat().st_mode), 0o600)
            self.assertFalse(entered.exists())
            self.assertFalse(guard.exists())

    def test_private_input_modes_are_role_exact(self) -> None:
        private = Path(self.temporary.name) / "private"
        private.mkdir(mode=0o700)
        paths = {
            "SSH_KEY": private / "key",
            "HEADLESS_ROOT_PACKAGE": private / "package",
            "RECOVERY_CANDIDATE_RECORD": private / "candidate",
            "FALLBACK_KNOWN_HOSTS": private / "known-hosts",
        }
        for name, path in paths.items():
            path.write_text(f"{name}\n", encoding="ascii")
            path.chmod(0o444 if name in {
                "HEADLESS_ROOT_PACKAGE", "RECOVERY_CANDIDATE_RECORD"
            } else 0o600)
        evidence = private / "evidence"
        journal = private / "journal"
        evidence.mkdir(mode=0o700)
        journal.mkdir(mode=0o700)
        environment = {
            "FASTBOOT_SERIAL": "M1AIB760D093XYZ",
            "ROG5_EXPECTED_USB_LOCATION": "pci-0000:04:00.3-usb-0:1.2",
            **{name: str(path) for name, path in paths.items()},
            "EVIDENCE_DIR": str(evidence),
            "ROG5_RETENTION_JOURNAL_ROOT": str(journal),
        }
        with mock.patch.dict(os.environ, environment, clear=True):
            self.assertEqual(LIVE.require_inputs(), environment)
        paths["RECOVERY_CANDIDATE_RECORD"].chmod(0o600)
        with (
            mock.patch.dict(os.environ, environment, clear=True),
            self.assertRaisesRegex(LIVE.LiveCycleError, "metadata is unsafe"),
        ):
            LIVE.require_inputs()

    def test_adapter_order_and_result_parser_are_exact(self) -> None:
        self.assertEqual(
            tuple(item.name for item in LIVE.ADAPTER.INVOCATIONS),
            (
                "execution-claim",
                "execution-boot",
                "fallback-reboot",
                "observer-claim",
                "observer-boot",
                "postmortem-read",
            ),
        )
        parsed = LIVE.parse_single_result(
            "ROG5_RETENTION_BOOT_RESULT_V1 action=observer-boot "
            "rollback_armed=1 usb_location=pci-0000:04:00.3-usb-0:1.2\n",
            "observer-boot",
        )
        self.assertEqual(parsed["rollback_armed"], "1")
        with self.assertRaisesRegex(LIVE.LiveCycleError, "no unique result"):
            LIVE.parse_single_result("", "observer-boot")


if __name__ == "__main__":
    unittest.main(verbosity=2)
