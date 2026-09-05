#!/usr/bin/env python3
"""Hardware-free tests for irreversible Generation-11 boot-claim entry."""

from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock


REPO = Path(__file__).resolve().parents[2]
CONSUMER = REPO / "scripts/host/consume-generation11-boot-claim.py"
PROFILE = "headless-diagnostic-generation11-live-v1"
RECORD = f"{PROFILE}.record"
EXPECTED = (
    "format=rog5-temporary-boot-consumption-v1\n"
    f"recovery_profile={PROFILE}\n"
    "candidate=headless-netroot-early-diag-v1\n"
    "manifest_sha256="
    "4eacb90f08a80af1bdfed704c4a5e0d8eff600e94191c18c066b23b1228f7e76\n"
    "state=BOOT_CLAIMED\n"
)

CONSUMER_SPEC = importlib.util.spec_from_file_location(
    "consume_generation11_boot_claim", CONSUMER
)
assert CONSUMER_SPEC is not None and CONSUMER_SPEC.loader is not None
CLAIM_CONSUMER = importlib.util.module_from_spec(CONSUMER_SPEC)
CONSUMER_SPEC.loader.exec_module(CLAIM_CONSUMER)


class ClaimConsumerTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.state = Path(self.temporary.name) / "state"
        self.root = self.state / "rog5-temporary-boot-consumption"
        self.root.mkdir(parents=True, mode=0o700)
        self.record = self.root / RECORD
        self.entered = self.root / f"{RECORD}.entered"
        self.environment = {
            "HOME": self.temporary.name,
            "PATH": os.environ["PATH"],
            "XDG_STATE_HOME": str(self.state),
        }

    def write_record(self, content: str = EXPECTED) -> None:
        self.record.write_text(content, encoding="ascii")
        self.record.chmod(0o600)

    def run_consumer(self) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [str(CONSUMER)],
            check=False,
            capture_output=True,
            text=True,
            env=self.environment,
        )

    def test_exact_claim_is_irreversibly_entered_once(self) -> None:
        self.write_record()
        first = self.run_consumer()
        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertFalse(self.record.exists())
        self.assertEqual(self.entered.read_text(encoding="ascii"), EXPECTED)
        self.assertEqual(self.entered.stat().st_mode & 0o777, 0o600)

        second = self.run_consumer()
        self.assertNotEqual(second.returncode, 0)
        self.assertIn("already entered", second.stderr)

    def test_wrong_or_extra_record_content_is_rejected(self) -> None:
        for content in (
            EXPECTED.replace("state=BOOT_CLAIMED", "state=READY"),
            EXPECTED + "extra=field\n",
            EXPECTED[:-1],
        ):
            with self.subTest(content=content[-24:]):
                if self.record.exists():
                    self.record.unlink()
                self.write_record(content)
                result = self.run_consumer()
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("is not exact", result.stderr)
                self.assertFalse(self.entered.exists())

    def test_unsafe_record_metadata_is_rejected(self) -> None:
        self.write_record()
        self.record.chmod(0o644)
        result = self.run_consumer()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("unsafe or absent", result.stderr)
        self.assertFalse(self.entered.exists())

    def test_symlinked_record_is_rejected(self) -> None:
        target = Path(self.temporary.name) / "claim"
        target.write_text(EXPECTED, encoding="ascii")
        target.chmod(0o600)
        self.record.symlink_to(target)
        result = self.run_consumer()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("unsafe or absent", result.stderr)
        self.assertFalse(self.entered.exists())

    def test_unsafe_or_symlinked_root_is_rejected(self) -> None:
        self.write_record()
        self.root.chmod(0o755)
        result = self.run_consumer()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("claim root is unsafe", result.stderr)

        self.root.chmod(0o700)
        moved = self.state / "real-root"
        self.root.rename(moved)
        self.root.symlink_to(moved, target_is_directory=True)
        result = self.run_consumer()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("claim root is unsafe", result.stderr)

    def test_preexisting_entered_record_fails_closed(self) -> None:
        self.write_record()
        self.entered.write_text(EXPECTED, encoding="ascii")
        self.entered.chmod(0o600)
        result = self.run_consumer()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("already entered", result.stderr)
        self.assertTrue(self.record.exists())

    def test_pathname_replacement_after_validation_fails_closed(self) -> None:
        self.write_record()
        original_link = os.link

        def replace_then_link(*args: object, **kwargs: object) -> None:
            self.record.unlink()
            self.write_record(
                EXPECTED.replace("state=BOOT_CLAIMED", "state=UNVALIDATED")
            )
            original_link(*args, **kwargs)

        with mock.patch.dict(os.environ, self.environment, clear=True):
            with mock.patch.object(
                CLAIM_CONSUMER.os,
                "link",
                side_effect=replace_then_link,
            ):
                with self.assertRaisesRegex(
                    CLAIM_CONSUMER.ClaimError,
                    "does not match the validated claim",
                ):
                    CLAIM_CONSUMER.consume()

        self.assertTrue(self.record.exists())
        self.assertTrue(self.entered.exists())
        self.assertIn("state=UNVALIDATED", self.entered.read_text(encoding="ascii"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
