#!/usr/bin/env python3
"""Hardware-free tests for the generic exact-record boot-claim consumer."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import importlib.util
import os
from pathlib import Path
import stat
import tempfile
import unittest
from unittest import mock


REPO = Path(__file__).resolve().parents[2]
CONSUMER = REPO / "scripts/host/consume-exact-boot-claim.py"
GATE = REPO / "scripts/host/run-stable-recovery-live-gate.sh"
PROFILES = {
    "headless-diagnostic-generation11-live-v1": (
        "4eacb90f08a80af1bdfed704c4a5e0d8eff600e94191c18c066b23b1228f7e76"
    ),
    "headless-diagnostic-generation12-live-v1": (
        "4eacb90f08a80af1bdfed704c4a5e0d8eff600e94191c18c066b23b1228f7e76"
    ),
}

SPEC = importlib.util.spec_from_file_location("consume_exact_boot_claim", CONSUMER)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("cannot load generic exact-record claim consumer")
CLAIMS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CLAIMS)


class ExactClaimConsumerTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.state = Path(self.temporary.name) / "state"
        self.root = self.state / "rog5-temporary-boot-consumption"
        self.root.mkdir(parents=True, mode=0o700)

    def expected(self, profile: str) -> bytes:
        return (
            "format=rog5-temporary-boot-consumption-v1\n"
            f"recovery_profile={profile}\n"
            "candidate=headless-netroot-early-diag-v1\n"
            f"manifest_sha256={PROFILES[profile]}\n"
            "state=BOOT_CLAIMED\n"
        ).encode("ascii")

    def paths(self, profile: str) -> tuple[Path, Path]:
        record = self.root / f"{profile}.record"
        return record, record.with_name(record.name + ".entered")

    def write_record(self, profile: str, payload: bytes | None = None) -> Path:
        record, _entered = self.paths(profile)
        record.write_bytes(payload if payload is not None else self.expected(profile))
        record.chmod(0o600)
        return record

    def test_repository_lookup_admits_only_historical_exact_records(self) -> None:
        self.assertEqual(set(CLAIMS.CLAIMS), set(PROFILES))
        self.assertNotIn("generation13", CONSUMER.read_text(encoding="utf-8"))
        for profile in PROFILES:
            with self.subTest(profile=profile):
                self.write_record(profile)
                CLAIMS.consume(profile, self.root)
                record, entered = self.paths(profile)
                self.assertFalse(record.exists())
                self.assertEqual(entered.read_bytes(), self.expected(profile))
                entered.unlink()
        with self.assertRaisesRegex(CLAIMS.ClaimError, "not repository-owned"):
            CLAIMS.consume("headless-diagnostic-generation13-live-v1", self.root)

    def test_wrong_content_owner_mode_link_and_symlink_fail_closed(self) -> None:
        profile = next(iter(PROFILES))
        cases = ("content", "mode", "hardlink", "symlink")
        for case in cases:
            with self.subTest(case=case):
                record, entered = self.paths(profile)
                record.unlink(missing_ok=True)
                entered.unlink(missing_ok=True)
                record = self.write_record(profile)
                if case == "content":
                    record.write_bytes(self.expected(profile) + b"extra=1\n")
                elif case == "mode":
                    record.chmod(0o644)
                elif case == "hardlink":
                    os.link(record, record.with_suffix(".copy"))
                else:
                    target = self.state / "outside-record"
                    record.replace(target)
                    record.symlink_to(target)
                with self.assertRaises(CLAIMS.ClaimError):
                    CLAIMS.consume(profile, self.root)
                self.assertFalse(entered.exists())

    def test_root_metadata_and_symlink_fail_closed(self) -> None:
        profile = next(iter(PROFILES))
        self.write_record(profile)
        self.root.chmod(0o755)
        with self.assertRaisesRegex(CLAIMS.ClaimError, "root is unsafe"):
            CLAIMS.consume(profile, self.root)
        self.root.chmod(0o700)
        moved = self.state / "moved"
        self.root.rename(moved)
        self.root.symlink_to(moved, target_is_directory=True)
        with self.assertRaisesRegex(CLAIMS.ClaimError, "root is unsafe"):
            CLAIMS.consume(profile, self.root)

    def test_wrong_record_owner_fails_before_entry(self) -> None:
        profile = next(iter(PROFILES))
        self.write_record(profile)
        _record, entered = self.paths(profile)
        original_fstat = os.fstat

        def wrong_regular_owner(descriptor: int) -> os.stat_result:
            metadata = original_fstat(descriptor)
            if not stat.S_ISREG(metadata.st_mode):
                return metadata
            fields = list(metadata)
            fields[stat.ST_UID] = metadata.st_uid + 1
            return os.stat_result(fields)

        with mock.patch.object(
            CLAIMS.os,
            "fstat",
            side_effect=wrong_regular_owner,
        ):
            with self.assertRaisesRegex(CLAIMS.ClaimError, "record is unsafe"):
                CLAIMS.consume(profile, self.root)
        self.assertFalse(entered.exists())

    def test_pathname_replacement_cannot_poison_irreversible_entry(
        self,
    ) -> None:
        profile = next(iter(PROFILES))
        record = self.write_record(profile)
        _record, entered = self.paths(profile)
        original_create = CLAIMS.create_entered_record

        def replace_then_create(*args: object, **kwargs: object) -> int:
            record.unlink()
            self.write_record(
                profile,
                self.expected(profile).replace(b"BOOT_CLAIMED", b"UNVALIDATED"),
            )
            return original_create(*args, **kwargs)

        with mock.patch.object(
            CLAIMS,
            "create_entered_record",
            side_effect=replace_then_create,
        ):
            with self.assertRaisesRegex(
                CLAIMS.ClaimError,
                "source BOOT_CLAIMED record changed during entry",
            ):
                CLAIMS.consume(profile, self.root)
        self.assertTrue(entered.exists())
        self.assertEqual(entered.read_bytes(), self.expected(profile))
        with self.assertRaisesRegex(CLAIMS.ClaimError, "already entered"):
            CLAIMS.consume(profile, self.root)

    def test_fsync_and_final_root_revalidation_preserve_at_most_once(self) -> None:
        profile = next(iter(PROFILES))
        self.write_record(profile)
        original_fsync = os.fsync
        calls = 0

        def replace_after_final_fsync(descriptor: int) -> None:
            nonlocal calls
            original_fsync(descriptor)
            calls += 1
            if calls == 3:
                moved = self.state / "entered-root"
                self.root.rename(moved)
                self.root.mkdir(mode=0o700)

        with mock.patch.object(CLAIMS.os, "fsync", side_effect=replace_after_final_fsync):
            with self.assertRaisesRegex(CLAIMS.ClaimError, "changed during entry"):
                CLAIMS.consume(profile, self.root)
        self.assertEqual(calls, 3)
        self.assertTrue(
            (self.state / "entered-root" / f"{profile}.record.entered").exists()
        )

    def test_concurrent_consumers_admit_exactly_one(self) -> None:
        profile = next(iter(PROFILES))
        self.write_record(profile)

        def attempt() -> bool:
            try:
                CLAIMS.consume(profile, self.root)
            except (CLAIMS.ClaimError, OSError):
                return False
            return True

        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(lambda _index: attempt(), range(2)))
        self.assertEqual(sorted(results), [False, True])
        _record, entered = self.paths(profile)
        self.assertEqual(entered.read_bytes(), self.expected(profile))

    def test_generic_consumer_replaces_future_copying_and_retains_history(
        self,
    ) -> None:
        source = GATE.read_text(encoding="utf-8")
        self.assertNotIn("consume-exact-boot-claim.py", source)
        self.assertNotIn("claim_consumer=$repo/scripts/host/consume-generation12", source)
        self.assertTrue(CONSUMER.is_file())
        self.assertTrue(os.access(CONSUMER, os.X_OK))
        for generation in (11, 12):
            historical = REPO / f"scripts/host/consume-generation{generation}-boot-claim.py"
            self.assertTrue(historical.is_file())


if __name__ == "__main__":
    unittest.main(verbosity=2)
