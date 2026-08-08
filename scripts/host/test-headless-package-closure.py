#!/usr/bin/env python3
"""Hostile tests for the exact minimal-server package closure."""

from __future__ import annotations

import hashlib
from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
VERIFIER = ROOT / "scripts/device/verify-exact-package-closure.sh"
CLOSURE = ROOT / "packaging/arch/headless-package-closure.txt"
STAGED_VERIFIER = ROOT / "scripts/device/verify-staged-arch-headless-rootfs.sh"
EXPECTED_SHA256 = "135862912935df91bb3305302e959498f9d5cf240a0ee74283abbf0bfa251f8b"
EXPECTED_COUNT = 152


class HeadlessPackageClosureTest(unittest.TestCase):
    def run_verifier(
        self,
        expected: Path,
        actual: Path,
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["bash", VERIFIER, expected, actual],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

    def test_tracked_closure_is_exact_and_wired_into_staging(self) -> None:
        payload = CLOSURE.read_bytes()
        self.assertEqual(hashlib.sha256(payload).hexdigest(), EXPECTED_SHA256)
        self.assertEqual(len(payload.splitlines()), EXPECTED_COUNT)
        source = STAGED_VERIFIER.read_text()
        self.assertIn("headless-package-closure.txt", source)
        self.assertIn("verify-exact-package-closure.sh", source)
        self.assertIn(
            'LC_ALL=C pacman -Q | LC_ALL=C sort >"$actual_packages"',
            source,
        )

    def test_exact_closure_passes(self) -> None:
        result = self.run_verifier(CLOSURE, CLOSURE)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            result.stdout,
            "PASS exact package closure count=152 "
            f"sha256={EXPECTED_SHA256}\n",
        )

    def test_package_add_remove_version_and_order_mutations_fail(self) -> None:
        canonical = CLOSURE.read_text().splitlines()
        mutations = {
            "added": [*canonical, "xorg-server 99-1"],
            "removed": canonical[:-1],
            "version": [
                *(canonical[:-1]),
                canonical[-1].rsplit("-", 1)[0] + "-99",
            ],
            "reordered": [canonical[1], canonical[0], *canonical[2:]],
            "duplicate": [canonical[0], *canonical],
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name, lines in mutations.items():
                with self.subTest(name=name):
                    actual = root / name
                    actual.write_text("\n".join(lines) + "\n")
                    result = self.run_verifier(CLOSURE, actual)
                    self.assertNotEqual(result.returncode, 0)

    def test_malformed_and_linked_inventories_fail(self) -> None:
        canonical = CLOSURE.read_text()
        malformed = {
            "blank": canonical + "\n",
            "comment": canonical + "# hidden\n",
            "extra-field": canonical + "xorg-server 1-1 hidden\n",
            "bad-name": canonical + "Xorg 1-1\n",
            "carriage-return": canonical.replace("\n", "\r\n", 1),
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name, payload in malformed.items():
                with self.subTest(name=name):
                    actual = root / name
                    actual.write_text(payload)
                    result = self.run_verifier(CLOSURE, actual)
                    self.assertNotEqual(result.returncode, 0)

            actual_link = root / "actual-link"
            actual_link.symlink_to(CLOSURE)
            self.assertNotEqual(
                self.run_verifier(CLOSURE, actual_link).returncode,
                0,
            )
            expected_link = root / "expected-link"
            expected_link.symlink_to(CLOSURE)
            self.assertNotEqual(
                self.run_verifier(expected_link, CLOSURE).returncode,
                0,
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
