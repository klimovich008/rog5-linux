#!/usr/bin/env python3
"""Offline tests for exact diagnostic deployment-candidate preparation."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import stat
import sys
import tempfile
import unittest


REPO = Path(__file__).resolve().parents[2]
TOOL_PATH = (
    REPO
    / "scripts/host/prepare-early-target-diagnostic-deployment-candidate.py"
)
FIXTURE_PACKAGE = (
    REPO / "configs/network-roots/headless-ssh-network-root-v3.package"
)


def load_module():
    specification = importlib.util.spec_from_file_location(
        "rog5_diagnostic_deployment_candidate_test",
        TOOL_PATH,
    )
    if specification is None or specification.loader is None:
        raise RuntimeError("cannot load diagnostic candidate tool")
    module = importlib.util.module_from_spec(specification)
    sys.modules[specification.name] = module
    specification.loader.exec_module(module)
    return module


TOOL = load_module()


class DiagnosticDeploymentCandidateTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(
            prefix="rog5-diagnostic-deployment-candidate-"
        )
        self.root = Path(self.temporary.name)
        self.root.chmod(0o700)
        self.package = self.root / "root.package"
        self.output = self.root / "candidate.json"
        self.values = TOOL.DEPLOYMENT.HEADLESS.parse_canonical_variant(
            FIXTURE_PACKAGE,
            TOOL.DEPLOYMENT.HEADLESS.PACKAGE_FORMATS,
            owner=FIXTURE_PACKAGE.stat().st_uid,
            mode=stat.S_IMODE(FIXTURE_PACKAGE.stat().st_mode),
        )
        self.values["authorized_key_fingerprint"] = (
            "SHA256:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
        )
        self.values["source_archive_sha256"] = "1" * 64
        self.values["sealed_archive_sha256"] = "2" * 64
        template = TOOL.DEPLOYMENT.CANDIDATE.load_candidate(TOOL.CANDIDATE_ID)
        for field in TOOL.DEPLOYMENT.ROOT_FIELDS:
            self.values[field] = str(template[field])
        self.write_package()

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def write_package(self) -> None:
        if self.package.exists():
            self.package.chmod(0o600)
        payload = TOOL.DEPLOYMENT.HEADLESS.canonical_bytes(self.values)
        self.package.write_bytes(payload)
        self.package.chmod(0o444)

    def test_exact_nonfixture_package_materializes_pinned_candidate(
        self,
    ) -> None:
        record, output, digest = TOOL.prepare(self.package, self.output)
        self.assertEqual(record["candidate"], TOOL.CANDIDATE_ID)
        self.assertEqual(record["bundle"], TOOL.CANDIDATE_ID)
        self.assertEqual(digest, TOOL.EXPECTED_SHA256)
        self.assertEqual(stat.S_IMODE(output.stat().st_mode), 0o444)
        self.assertEqual(
            output.read_bytes(),
            (
                REPO
                / "configs/recovery-candidates/"
                "headless-netroot-early-diag-v2.json"
            ).read_bytes(),
        )

    def test_every_root_mismatch_is_rejected_without_output(self) -> None:
        accepted = dict(self.values)
        for field in TOOL.DEPLOYMENT.ROOT_FIELDS:
            with self.subTest(field=field):
                self.values = dict(accepted)
                self.values[field] = (
                    "arch-b"
                    if field == "root_generation"
                    else "/changed"
                    if field == "root_subtree"
                    else "37736"
                    if field == "root_tree_entries"
                    else "f" * 64
                )
                self.write_package()
                with self.assertRaises(
                    (
                        TOOL.DiagnosticCandidateError,
                        TOOL.DEPLOYMENT.HEADLESS.HeadlessRootError,
                    )
                ):
                    TOOL.prepare(self.package, self.output)
                self.assertFalse(self.output.exists())
        self.values = accepted

    def test_fixture_identity_and_existing_output_are_rejected(self) -> None:
        fixture = TOOL.DEPLOYMENT.HEADLESS.parse_canonical_variant(
            FIXTURE_PACKAGE,
            TOOL.DEPLOYMENT.HEADLESS.PACKAGE_FORMATS,
            owner=FIXTURE_PACKAGE.stat().st_uid,
            mode=stat.S_IMODE(FIXTURE_PACKAGE.stat().st_mode),
        )
        accepted_fingerprint = self.values["authorized_key_fingerprint"]
        self.values["authorized_key_fingerprint"] = fixture[
            "authorized_key_fingerprint"
        ]
        self.write_package()
        with self.assertRaisesRegex(
            TOOL.DEPLOYMENT.DeploymentCandidateError,
            "fixture identity",
        ):
            TOOL.prepare(self.package, self.output)
        self.assertFalse(self.output.exists())

        self.values["authorized_key_fingerprint"] = accepted_fingerprint
        self.write_package()
        self.output.write_text("occupied\n", encoding="ascii")
        occupied = self.output.read_bytes()
        with self.assertRaisesRegex(
            TOOL.DEPLOYMENT.DeploymentCandidateError,
            "already exists",
        ):
            TOOL.prepare(self.package, self.output)
        self.assertEqual(self.output.read_bytes(), occupied)


if __name__ == "__main__":
    unittest.main()
