#!/usr/bin/env python3
"""Hostile tests for the stable-recovery wrapper config slimming audit."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import unittest


AUDITOR = Path(__file__).with_name("verify-stable-wrapper-slim-config.py")


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class StableWrapperSlimConfigTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.baseline = self.root / "baseline.config"
        self.candidate = self.root / "candidate.config"
        baseline = (
            b"CONFIG_ARM64=y\n"
            b"CONFIG_NR_CPUS=8\n"
            b"CONFIG_OLD_A=y\n"
            b"CONFIG_OLD_B=y\n"
            b"# CONFIG_USB_DWC3_GADGET is not set\n"
        )
        candidate = (
            b"CONFIG_ARM64=y\n"
            b"CONFIG_NR_CPUS=8\n"
            b"# CONFIG_OLD_A is not set\n"
            b"# CONFIG_OLD_B is not set\n"
            b"CONFIG_USB_DWC3_GADGET=y\n"
        )
        self.baseline.write_bytes(baseline)
        self.candidate.write_bytes(candidate)
        self.profile = {
            "format": "rog5-stable-wrapper-slim-profile-v1",
            "status": "experiment",
            "authority": "none",
            "baseline_config_sha256": sha256(baseline),
            "fragment_sha256": sha256(b"fragment"),
            "candidate_config_sha256": sha256(candidate),
            "source_tree_sha256": sha256(b"source"),
            "builder_id": sha256(b"builder"),
            "builder_digest": f"sha256:{sha256(b'digest')}",
            "minimum_builtin_reduction": 1,
            "minimum_active_reduction": 1,
            "minimum_integer_config": {
                "CONFIG_NR_CPUS": 8,
            },
            "allowed_enabled_additions": [
                "CONFIG_USB_DWC3_GADGET",
            ],
            "allowed_builtin_promotions": [],
            "candidate_required": {
                "CONFIG_ARM64": "y",
                "CONFIG_USB_DWC3_GADGET": "y",
            },
            "forbidden_config": [
                "CONFIG_OLD_A",
                "CONFIG_OLD_B",
            ],
        }
        self.profile_path = self.root / "profile.json"
        self.write_profile()

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def write_profile(self) -> None:
        self.profile_path.write_text(
            json.dumps(self.profile, indent=2) + "\n",
            encoding="ascii",
        )

    def invoke(self, *, check: bool = True) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                "python3",
                str(AUDITOR),
                "--profile",
                str(self.profile_path),
                "--baseline",
                str(self.baseline),
                "--candidate",
                str(self.candidate),
            ],
            check=check,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

    def invoke_failure(self, expected: str) -> None:
        result = self.invoke(check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(expected, result.stderr)

    def write_candidate(self, text: str) -> None:
        self.candidate.write_text(text, encoding="ascii")
        self.profile["candidate_config_sha256"] = sha256(
            self.candidate.read_bytes()
        )
        self.write_profile()

    def test_valid_reduction_passes_without_authority(self) -> None:
        result = self.invoke()
        self.assertIn("builtin_reduction=1", result.stdout)
        self.assertIn("active_reduction=1", result.stdout)
        self.assertIn("status=experiment", result.stdout)
        self.assertIn("authority=none", result.stdout)

    def test_required_and_minimum_mutations_fail(self) -> None:
        original = self.candidate.read_text(encoding="ascii")
        for changed, message in (
            (
                original.replace(
                    "CONFIG_ARM64=y", "# CONFIG_ARM64 is not set"
                ),
                "candidate requirement changed",
            ),
            (
                original.replace("CONFIG_NR_CPUS=8", "CONFIG_NR_CPUS=7"),
                "candidate integer is below minimum",
            ),
            (
                original.replace(
                "CONFIG_USB_DWC3_GADGET=y",
                "# CONFIG_USB_DWC3_GADGET is not set",
                ),
                "candidate requirement changed",
            ),
        ):
            self.write_candidate(changed)
            self.invoke_failure(message)
        self.write_candidate(original)

    def test_forbidden_and_unreviewed_additions_fail(self) -> None:
        original = self.candidate.read_text(encoding="ascii")
        self.write_candidate(
            original.replace("# CONFIG_OLD_A is not set", "CONFIG_OLD_A=y"),
        )
        self.invoke_failure("candidate retained forbidden config")
        self.write_candidate(original + "CONFIG_UNREVIEWED=y\n")
        self.invoke_failure("candidate enabled unreviewed config")
        self.write_candidate(original)

    def test_unreviewed_module_to_builtin_promotion_fails(self) -> None:
        baseline = self.baseline.read_text(encoding="ascii").replace(
            "CONFIG_OLD_A=y", "CONFIG_OLD_A=m"
        )
        self.baseline.write_text(baseline, encoding="ascii")
        self.profile["baseline_config_sha256"] = sha256(
            self.baseline.read_bytes()
        )
        self.profile["forbidden_config"].remove("CONFIG_OLD_A")
        candidate = self.candidate.read_text(encoding="ascii").replace(
            "# CONFIG_OLD_A is not set", "CONFIG_OLD_A=y"
        )
        self.write_candidate(candidate)
        self.invoke_failure("candidate promoted unreviewed module to builtin")

    def test_reduction_thresholds_fail_closed(self) -> None:
        self.profile["minimum_builtin_reduction"] = 2
        self.write_profile()
        self.invoke_failure(
            "candidate builtin reduction is below the profile threshold"
        )
        self.profile["minimum_builtin_reduction"] = 1
        self.profile["minimum_active_reduction"] = 2
        self.write_profile()
        self.invoke_failure(
            "candidate active reduction is below the profile threshold"
        )

    def test_profile_identity_state_and_canonical_form_are_enforced(self) -> None:
        original = self.profile_path.read_text(encoding="ascii")
        for key, value, message in (
            ("authority", "live", "claims non-experimental state"),
            ("status", "accepted", "claims non-experimental state"),
            (
                "baseline_config_sha256",
                "0" * 64,
                "accepted baseline config identity changed",
            ),
        ):
            self.profile[key] = value
            self.write_profile()
            self.invoke_failure(message)
            self.profile = json.loads(original)
        self.profile_path.write_text(original.rstrip() + " \n", encoding="ascii")
        self.invoke_failure("profile JSON is not canonical")

    def test_duplicate_profile_and_config_symbols_are_rejected(self) -> None:
        profile = self.profile_path.read_text(encoding="ascii")
        self.profile_path.write_text(
            profile.replace(
                '  "format":',
                '  "format": "duplicate",\n  "format":',
                1,
            ),
            encoding="ascii",
        )
        self.invoke_failure("duplicate JSON field")
        self.write_profile()
        self.write_candidate(
            self.candidate.read_text(encoding="ascii") + "CONFIG_ARM64=y\n"
        )
        self.invoke_failure("candidate config contains duplicate symbol")

    def test_symlinked_inputs_are_rejected(self) -> None:
        linked = self.root / "linked.config"
        linked.symlink_to(self.candidate)
        original = self.candidate
        self.candidate = linked
        try:
            self.invoke_failure("input is not a single-link regular file")
        finally:
            self.candidate = original


if __name__ == "__main__":
    unittest.main()
