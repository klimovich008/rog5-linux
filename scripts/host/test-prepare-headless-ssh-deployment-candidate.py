#!/usr/bin/env python3
"""Offline tests for non-fixture package-to-candidate binding."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import shutil
import stat
import sys
import tempfile
import unittest
from unittest import mock


REPO = Path(__file__).resolve().parents[2]
TOOL_PATH = (
    REPO / "scripts/host/prepare-headless-ssh-deployment-candidate.py"
)
FIXTURE_PACKAGE = (
    REPO / "configs/network-roots/headless-ssh-network-root-v3.package"
)


def load_module():
    specification = importlib.util.spec_from_file_location(
        "rog5_deployment_candidate_test",
        TOOL_PATH,
    )
    if specification is None or specification.loader is None:
        raise RuntimeError("cannot load deployment-candidate tool")
    module = importlib.util.module_from_spec(specification)
    sys.modules[specification.name] = module
    specification.loader.exec_module(module)
    return module


TOOL = load_module()


class DeploymentCandidateTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(
            prefix="rog5-deployment-candidate-"
        )
        self.root = Path(self.temporary.name)
        self.root.chmod(0o700)
        self.package = self.root / "root.package"
        self.output = self.root / "candidate.json"
        self.values = TOOL.HEADLESS.parse_canonical_variant(
            FIXTURE_PACKAGE,
            TOOL.HEADLESS.PACKAGE_FORMATS,
            owner=FIXTURE_PACKAGE.stat().st_uid,
            mode=stat.S_IMODE(FIXTURE_PACKAGE.stat().st_mode),
        )
        self.values["authorized_key_fingerprint"] = (
            "SHA256:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
        )
        self.values["source_archive_sha256"] = "1" * 64
        self.values["sealed_archive_sha256"] = "2" * 64
        self.values["root_tree_sha256"] = "3" * 64
        self.values["root_seal_sha256"] = "4" * 64
        self.values["root_tree_entries"] = "40000"
        self.write_package()

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def write_package(self) -> None:
        if self.package.exists():
            self.package.chmod(0o600)
        self.package.write_bytes(TOOL.HEADLESS.canonical_bytes(self.values))
        self.package.chmod(0o444)

    def test_non_fixture_package_binds_exact_candidate(self) -> None:
        record, output = TOOL.prepare(self.package, self.output)
        self.assertEqual(output, self.output)
        self.assertEqual(
            stat.S_IMODE(output.stat().st_mode),
            0o444,
        )
        self.assertEqual(record["candidate"], TOOL.CANDIDATE_ID)
        self.assertEqual(record["status"], "offline")
        self.assertEqual(record["authority"], "none")
        self.assertEqual(record["profile"], "network-root-v1")
        for field in TOOL.ROOT_FIELDS:
            self.assertEqual(str(record[field]), self.values[field])
        reparsed = TOOL.CANDIDATE.load_candidate_path(
            output,
            TOOL.CANDIDATE_ID,
        )
        self.assertEqual(reparsed, record)

    def test_each_fixture_identity_is_rejected(self) -> None:
        fixture = TOOL.HEADLESS.parse_canonical_variant(
            FIXTURE_PACKAGE,
            TOOL.HEADLESS.PACKAGE_FORMATS,
            owner=FIXTURE_PACKAGE.stat().st_uid,
            mode=stat.S_IMODE(FIXTURE_PACKAGE.stat().st_mode),
        )
        for field in TOOL.FIXTURE_FIELDS:
            with self.subTest(field=field):
                self.values[field] = fixture[field]
                self.write_package()
                with self.assertRaisesRegex(
                    TOOL.DeploymentCandidateError,
                    "fixture identity",
                ):
                    TOOL.prepare(self.package, self.output)
                self.tearDown()
                self.setUp()

    def test_wrong_tuple_and_unsafe_metadata_are_rejected(self) -> None:
        cases = ("profile", "mode", "hardlink", "symlink")
        for case in cases:
            with self.subTest(case=case):
                self.tearDown()
                self.setUp()
                if case == "profile":
                    self.values["profile"] = "persistent-root-ro-v1"
                    self.write_package()
                elif case == "mode":
                    self.package.chmod(0o644)
                elif case == "hardlink":
                    self.package.with_suffix(".copy").hardlink_to(self.package)
                else:
                    real = self.root / "root.package.real"
                    self.package.rename(real)
                    self.package.symlink_to(real.name)
                with self.assertRaises(
                    (
                        TOOL.DeploymentCandidateError,
                        TOOL.HEADLESS.HeadlessRootError,
                    )
                ):
                    TOOL.prepare(self.package, self.output)

    def test_existing_output_and_repository_paths_are_rejected(self) -> None:
        self.output.write_text("occupied\n", encoding="ascii")
        with self.assertRaisesRegex(
            TOOL.DeploymentCandidateError,
            "already exists",
        ):
            TOOL.prepare(self.package, self.output)

        repository_parent = (
            REPO / "build/deployment-candidate-test-private"
        )
        repository_parent.mkdir(mode=0o700, exist_ok=True)
        repository_parent.chmod(0o700)
        repository_package = repository_parent / "root.package"
        try:
            shutil.copyfile(self.package, repository_package)
            repository_package.chmod(0o444)
            with self.assertRaisesRegex(
                TOOL.DeploymentCandidateError,
                "outside the repository",
            ):
                TOOL.parse_package(repository_package)
        finally:
            repository_package.unlink(missing_ok=True)
            repository_parent.rmdir()

    def test_failed_candidate_write_removes_owned_partial_output(self) -> None:
        payload = TOOL.canonical_payload(TOOL.candidate_record(self.values))
        with mock.patch.object(
            TOOL.os,
            "write",
            side_effect=OSError("synthetic write failure"),
        ):
            with self.assertRaises(OSError):
                TOOL.write_candidate(self.output, payload)
        self.assertFalse(self.output.exists())


if __name__ == "__main__":
    unittest.main()
