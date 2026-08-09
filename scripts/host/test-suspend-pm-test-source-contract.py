#!/usr/bin/env python3
"""Hostile tests for the pinned suspend pm_test source contract."""

from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


REPO = Path(__file__).resolve().parents[2]
VERIFIER = REPO / "scripts/host/verify-suspend-pm-test-source-contract.py"
SOURCE = REPO / "build/linux-stable-v7.1.4-source"
FILES = (
    "kernel/power/Kconfig",
    "kernel/power/main.c",
    "kernel/power/suspend.c",
    "drivers/base/power/main.c",
    "drivers/firmware/psci/psci.c",
)


class SuspendPmTestSourceContractTest(unittest.TestCase):
    def setUp(self) -> None:
        if not SOURCE.is_dir():
            self.skipTest("retained accepted Linux source is optional in CI")
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name) / "linux"
        for relative in FILES:
            target = self.root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(SOURCE / relative, target)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def run_verifier(self) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [str(VERIFIER), str(self.root)],
            cwd=REPO,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

    def mutate(self, relative: str, old: str, new: str) -> None:
        path = self.root / relative
        text = path.read_text(encoding="utf-8")
        self.assertIn(old, text)
        path.write_text(text.replace(old, new, 1), encoding="utf-8")

    def test_exact_source_contract_passes(self) -> None:
        result = self.run_verifier()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("status=devices-level-return-before-psci", result.stdout)
        self.assertIn("real_suspend=forbidden", result.stdout)

    def test_devices_intercept_cannot_move_after_suspend_enter(self) -> None:
        self.mutate(
            "kernel/power/suspend.c",
            "if (suspend_test(TEST_DEVICES))\n\t\tgoto Recover_platform;",
            "if (false)\n\t\tgoto Recover_platform;",
        )
        result = self.run_verifier()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("devices-level suspend intercept", result.stderr)

    def test_pm_test_sysfs_dependency_cannot_be_weakened(self) -> None:
        self.mutate(
            "kernel/power/Kconfig",
            "depends on PM_DEBUG && PM_SLEEP",
            "depends on PM_SLEEP",
        )
        result = self.run_verifier()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("PM_SLEEP_DEBUG dependency", result.stderr)

    def test_watchdog_must_panic_and_name_the_device(self) -> None:
        self.mutate(
            "drivers/base/power/main.c",
            'panic("%s %s: unrecoverable failure\\n",',
            'pr_err("%s %s: unrecoverable failure\\n",',
        )
        result = self.run_verifier()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("DPM watchdog panic", result.stderr)

    def test_real_psci_boundary_remains_identified(self) -> None:
        self.mutate(
            "drivers/firmware/psci/psci.c",
            "suspend_set_ops(&psci_suspend_ops);",
            "/* hostile: suspend ops omitted */",
        )
        result = self.run_verifier()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("PSCI system-suspend registration", result.stderr)


if __name__ == "__main__":
    unittest.main()
