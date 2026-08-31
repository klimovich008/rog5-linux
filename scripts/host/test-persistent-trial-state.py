#!/usr/bin/env python3
"""Hostile offline tests for the bounded persistent Wi-Fi trial record."""

import concurrent.futures
import os
from pathlib import Path
import stat
import subprocess
import tempfile
import unittest


REPO = Path(__file__).resolve().parents[2]
SOURCE = REPO / "tools/persistent_trial_state/rog5-persistent-trial-state.c"
BUILDER = REPO / "scripts/device/build-persistent-trial-state.sh"
TRIAL = "1" * 64
PRIMARY = "persistent-native-root-wifi"
PRIMARY_HASH = "2" * 64
FALLBACK = "persistent-native-root-v11"
FALLBACK_HASH = "a684bad14f84251ba342a87bde07da1f7b9aea412275ad124f7000716e94bbe2"


class PersistentTrialState(unittest.TestCase):
    def test_production_builder_is_fixed_and_hardened(self):
        source = BUILDER.read_text()
        for contract in (
            '"$(uname -m)" = aarch64',
            "cc -std=c11 -O2 -static -fPIE -pie -fstack-protector-strong",
            "-Wl,-z,relro,-z,now,-z,noexecstack,--build-id=none -s",
            "ROG5_TRIAL_TEST",
            "persistent trial helper has a dynamic interpreter",
        ):
            self.assertIn(contract, source)
        self.assertNotIn("curl", source)
        self.assertNotIn("wget", source)

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name) / "root"
        self.rog5 = self.root / "rog5"
        self.root.mkdir(mode=0o755)
        self.rog5.mkdir(mode=0o700)
        self.binary = Path(self.temporary.name) / "trial-state"
        root_literal = str(self.root).replace('"', '\\"')
        subprocess.run(
            [
                "cc", "-std=c11", "-O2", "-Wall", "-Wextra", "-Werror",
                f'-DROG5_DECIDE_ROOT="{root_literal}"',
                f'-DROG5_HEALTHY_ROOT="{root_literal}"',
                str(SOURCE), "-o", str(self.binary),
            ],
            check=True,
        )

    def command(self, action="decide", *, trial=TRIAL, primary=PRIMARY,
                primary_hash=PRIMARY_HASH, fallback=FALLBACK,
                fallback_hash=FALLBACK_HASH, check=True):
        arguments = ([str(self.binary), action, trial, primary]
                     if action == "healthy" else
                     [str(self.binary), action, trial, primary, primary_hash,
                      fallback, fallback_hash])
        return subprocess.run(
            arguments,
            text=True, capture_output=True, check=check, timeout=5,
        )

    @property
    def record(self):
        return self.rog5 / "boot" / "wifi-trial-state"

    def test_first_boot_is_primary_then_pending_falls_back(self):
        self.assertEqual(self.command().stdout, PRIMARY + "\n")
        self.assertEqual(stat.S_IMODE(self.record.stat().st_mode), 0o600)
        self.assertEqual(self.record.stat().st_nlink, 1)
        self.assertTrue(self.record.read_text().endswith("state=pending\n"))
        self.assertEqual(self.command().stdout, FALLBACK + "\n")

    def test_healthy_commit_is_atomic_and_idempotent(self):
        self.command()
        self.assertNotEqual(self.command("healthy", trial="4" * 64,
                                         check=False).returncode, 0)
        self.assertNotEqual(self.command("healthy", primary="wrong-bundle",
                                         check=False).returncode, 0)
        self.assertEqual(self.command("healthy").stdout, "healthy\n")
        self.assertTrue(self.record.read_text().endswith("state=healthy\n"))
        self.assertEqual(self.command().stdout, PRIMARY + "\n")
        self.assertEqual(self.command("healthy").stdout, "already-healthy\n")

    def test_identity_change_and_malformed_state_fail_closed(self):
        self.command()
        for mutation in (
            lambda: self.command(trial="3" * 64, check=False),
            lambda: self.command(primary_hash="4" * 64, check=False),
        ):
            result = mutation()
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(result.stdout, "")
        self.record.write_text("format=wrong\n")
        self.record.chmod(0o600)
        result = self.command(check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "")

    def test_hostile_record_metadata_is_rejected(self):
        self.command()
        original = self.record.read_bytes()
        for case in ("writable", "hardlink", "symlink"):
            with self.subTest(case=case):
                self.record.unlink(missing_ok=True)
                self.record.write_bytes(original)
                self.record.chmod(0o600)
                if case == "writable":
                    self.record.chmod(0o644)
                elif case == "hardlink":
                    os.link(self.record, self.record.with_name("other"))
                else:
                    target = self.record.with_name("target")
                    self.record.rename(target)
                    self.record.symlink_to(target)
                result = self.command(check=False)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(result.stdout, "")
                for path in self.record.parent.iterdir():
                    if path.is_symlink() or path.is_file():
                        path.unlink()

    def test_stale_temporary_refuses_publication(self):
        boot = self.rog5 / "boot"
        boot.mkdir(mode=0o700)
        temporary = boot / ".wifi-trial-state.next"
        temporary.write_text("stale\n")
        temporary.chmod(0o600)
        result = self.command(check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.record.exists())
        self.assertEqual(temporary.read_text(), "stale\n")

    def test_concurrent_healthy_commit_has_one_writer(self):
        self.command()
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(lambda _: self.command("healthy", check=False), range(8)))
        successes = [result for result in results if result.returncode == 0]
        self.assertGreaterEqual(len(successes), 1)
        self.assertTrue(all(result.stdout in ("healthy\n", "already-healthy\n")
                            for result in successes))
        self.assertEqual(sum(result.stdout == "healthy\n" for result in successes), 1)
        self.assertTrue(self.record.read_text().endswith("state=healthy\n"))

    def test_argument_language_is_bounded(self):
        cases = (
            {"trial": "A" * 64},
            {"primary": "../escape"},
            {"primary": "UPPER"},
            {"primary_hash": "0" * 63},
            {"fallback": PRIMARY},
        )
        for values in cases:
            with self.subTest(values=values):
                result = self.command(check=False, **values)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(result.stdout, "")


if __name__ == "__main__":
    unittest.main()
