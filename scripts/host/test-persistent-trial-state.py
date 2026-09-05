#!/usr/bin/env python3
"""Hostile offline tests for the bounded persistent Wi-Fi trial record."""

import concurrent.futures
import hashlib
import os
from pathlib import Path
import shutil
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
    def test_active_compositions_share_one_verified_helper(self):
        pointer = REPO / "configs/persistent-trial-helper.path"
        relative = pointer.read_text().strip()
        self.assertRegex(
            relative,
            r"\Aartifacts/persistent-trial-state-v[1-9][0-9]*/rog5-persistent-trial-state\Z",
        )
        artifact = REPO / relative
        metadata = dict(line.split("=", 1) for line in
                        (artifact.parent / "build-meta.txt").read_text().splitlines())
        self.assertFalse(artifact.is_symlink())
        self.assertEqual(metadata["source_sha256"], hashlib.sha256(SOURCE.read_bytes()).hexdigest())
        self.assertEqual(metadata["builder_sha256"], hashlib.sha256(BUILDER.read_bytes()).hexdigest())
        self.assertEqual(metadata["output_size"], str(artifact.stat().st_size))
        self.assertEqual(metadata["output_sha256"], hashlib.sha256(artifact.read_bytes()).hexdigest())
        self.assertEqual(
            (artifact.parent / "SHA256SUMS").read_text(),
            metadata["output_sha256"] + "  rog5-persistent-trial-state\n",
        )
        for consumer in (
            "scripts/device/build-persistent-slotb-loader-initramfs.sh",
            "scripts/device/build-persistent-slotb-recovery-initramfs.sh",
            "scripts/device/build-native-wifi-boot-initramfs.py",
        ):
            source = (REPO / consumer).read_text()
            self.assertIn("configs/persistent-trial-helper.path", source)
            self.assertNotRegex(source, r"persistent-trial-state-v[0-9]+/")
        replay = (REPO / "scripts/host/test-persistent-trial-state-aarch64.sh").read_text()
        self.assertIn('ROG5_TRIAL_TEST_ARM64=1 python3 "$repo/scripts/host/test-persistent-trial-state.py"', replay)

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
        # Explicit offline replay of the release binary at its fixed paths.
        # Only this disposable state tree is writable; no host devices/network.
        self.arm64 = os.environ.get("ROG5_TRIAL_TEST_ARM64") == "1"
        if self.arm64:
            self.binary = REPO / (REPO / "configs/persistent-trial-helper.path").read_text().strip()
            self.qemu = REPO / "artifacts/host-tools/qemu-aarch64-static"
            self.assertTrue(shutil.which("bwrap"), "ARM replay requires bubblewrap")
            self.assertTrue(self.qemu.is_file(), "ARM replay requires qualified QEMU")
            return
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
                fallback_hash=FALLBACK_HASH, check=True, stdout=subprocess.PIPE):
        arguments = ([str(self.binary), action, trial, primary]
                     if action == "healthy" else
                     [str(self.binary), action, trial, primary, primary_hash,
                      fallback, fallback_hash])
        if self.arm64:
            arguments = [
                "bwrap", "--unshare-all", "--die-with-parent", "--new-session",
                "--uid", "0", "--gid", "0", "--tmpfs", "/",
                "--bind", str(self.root), "/mnt/userdata",
                "--bind", str(self.root), "/.rog5/userdata-rw",
                "--ro-bind", str(self.binary), "/trial-state",
                "--ro-bind", str(self.qemu), "/qemu",
                "--dev", "/dev", "--clearenv", "--chdir", "/",
                "/qemu", "/trial-state", *arguments[1:],
            ]
        return subprocess.run(
            arguments,
            text=True, stdout=stdout, stderr=subprocess.PIPE,
            check=check, timeout=5,
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

    def test_health_without_selector_preparation_is_refused(self):
        (self.rog5 / "boot").mkdir(mode=0o700)
        result = self.command("healthy", check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "")
        self.assertIn("pending trial record is absent", result.stderr)
        self.assertFalse(self.record.exists())

    def test_old_healthy_record_cannot_acknowledge_a_new_ram_trial(self):
        self.command()
        self.command("healthy")
        old = self.record.read_bytes()
        result = self.command("healthy", trial="3" * 64, check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "")
        self.assertIn("running trial identity does not match pending state", result.stderr)
        self.assertEqual(self.record.read_bytes(), old)

    def test_healthy_commit_is_atomic_and_idempotent(self):
        self.command()
        self.assertNotEqual(self.command("healthy", trial="4" * 64,
                                         check=False).returncode, 0)
        self.assertNotEqual(self.command("healthy", primary="wrong-bundle",
                                         check=False).returncode, 0)
        self.assertEqual(self.command("healthy").stdout, "healthy\n")
        self.assertTrue(self.record.read_text().endswith("state=healthy\n"))
        self.assertEqual(self.command("healthy").stdout, "already-healthy\n")

    def test_each_accepted_primary_boot_needs_a_fresh_health_ack(self):
        self.command()
        self.command("healthy")
        for _ in range(3):
            self.assertEqual(self.command().stdout, PRIMARY + "\n")
            self.assertTrue(self.record.read_text().endswith("state=pending\n"))
            self.assertEqual(self.command("healthy").stdout, "healthy\n")
        self.assertEqual(self.command().stdout, PRIMARY + "\n")
        for _ in range(4):
            self.assertEqual(self.command().stdout, FALLBACK + "\n")

    def test_retained_v1_target_can_acknowledge_v2_recovery(self):
        if not self.arm64:
            self.skipTest("requires explicit retained ARM binary replay")
        current = self.binary
        legacy = REPO / "artifacts/persistent-trial-state-v1/rog5-persistent-trial-state"
        for _ in range(2):
            self.assertEqual(self.command().stdout, PRIMARY + "\n")
            self.assertTrue(self.record.read_text().endswith("state=pending\n"))
            self.binary = legacy
            try:
                self.assertEqual(self.command("healthy").stdout, "healthy\n")
            finally:
                self.binary = current
        self.assertEqual(self.command().stdout, PRIMARY + "\n")
        self.assertEqual(self.command().stdout, FALLBACK + "\n")

    def test_concurrent_rearm_selects_primary_at_most_once(self):
        self.command()
        self.command("healthy")
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(lambda _: self.command(check=False), range(8)))
        primary_count = sum(result.stdout == PRIMARY + "\n" for result in results)
        # The publisher must reacquire the replaced inode for revalidation.
        # A concurrent fallback reader may hold it, safely refusing even the
        # publisher. At-most-once does not promise one successful publication.
        self.assertLessEqual(primary_count, 1)
        allowed_refusals = {
            "FAIL persistent trial state: concurrent trial record operation\n",
            "FAIL persistent trial state: trial record pathname changed\n",
        }
        for result in results:
            if result.returncode == 0:
                self.assertIn(result.stdout, (PRIMARY + "\n", FALLBACK + "\n"))
            else:
                self.assertEqual(result.stdout, "")
                self.assertIn(result.stderr, allowed_refusals)
        if primary_count == 0:
            self.assertTrue(any(
                result.stderr == "FAIL persistent trial state: concurrent trial record operation\n"
                for result in results
            ))
        self.assertTrue(self.record.read_text().endswith("state=pending\n"))
        self.assertEqual(self.command().stdout, FALLBACK + "\n")

    def test_ambiguous_rearm_reply_never_selects_primary_again(self):
        self.command()
        self.command("healthy")
        with open("/dev/full", "w") as full:
            result = self.command(stdout=full, check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("cannot write result", result.stderr)
        self.assertTrue(self.record.read_text().endswith("state=pending\n"))
        self.assertEqual(self.command().stdout, FALLBACK + "\n")

    def test_rearm_temporary_collision_refuses_without_primary_output(self):
        self.command()
        self.command("healthy")
        previous = self.record.read_bytes()
        temporary = self.record.with_name(".wifi-trial-state.next")
        temporary.write_text("preserve ambiguous state\n")
        temporary.chmod(0o600)
        result = self.command(check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "")
        self.assertEqual(self.record.read_bytes(), previous)
        self.assertEqual(temporary.read_text(), "preserve ambiguous state\n")

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

    def test_concurrent_healthy_commit_is_durable_and_at_most_once(self):
        self.command()
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(lambda _: self.command("healthy", check=False), range(8)))
        successes = [result for result in results if result.returncode == 0]
        failures = [result for result in results if result.returncode != 0]
        self.assertGreaterEqual(len(successes), 1)
        self.assertTrue(all(result.stdout in ("healthy\n", "already-healthy\n")
                            for result in successes))
        self.assertLessEqual(
            sum(result.stdout == "healthy\n" for result in successes), 1,
        )
        allowed = {
            "FAIL persistent trial state: concurrent trial record operation\n",
            "FAIL persistent trial state: trial record pathname changed\n",
        }
        self.assertTrue(all(not result.stdout and result.stderr in allowed
                            for result in failures))
        self.assertTrue(self.record.read_text().endswith("state=healthy\n"))
        self.assertEqual(stat.S_IMODE(self.record.stat().st_mode), 0o600)
        self.assertEqual(self.record.stat().st_nlink, 1)

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
