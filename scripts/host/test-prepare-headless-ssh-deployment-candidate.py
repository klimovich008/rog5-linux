#!/usr/bin/env python3
"""Offline tests for non-fixture package-to-candidate binding."""

from __future__ import annotations

import hashlib
import importlib.util
import io
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
from contextlib import redirect_stderr


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

    def select_accepted_predecessor_root(self) -> None:
        self.values.update(
            TOOL.CANDIDATE.EXTERNAL_SUCCESSOR_ROOT_FIELDS[
                TOOL.SUCCESSOR_BUNDLE_ID
            ]
        )
        self.write_package()

    def synthetic_candidate_repository(self) -> tuple[Path, Path]:
        repository = self.root / "synthetic-repository"
        artifact_root = repository / "artifacts" / "synthetic"
        candidate_root = repository / "configs" / "recovery-candidates"
        artifact_root.mkdir(parents=True)
        candidate_root.mkdir(parents=True)
        template = TOOL.CANDIDATE.load_candidate(TOOL.CANDIDATE_ID)
        payloads = {
            "Image": b"I" * 64,
            "board.dtb": b"D" * 40,
            "initramfs.cpio.gz": b"GZ",
        }
        for name, payload in payloads.items():
            artifact = artifact_root / name
            artifact.write_bytes(payload)
            artifact.chmod(0o400)
            template["artifacts"][name] = {
                "path": f"artifacts/synthetic/{name}",
                "size": len(payload),
                "sha256": hashlib.sha256(payload).hexdigest(),
            }
        candidate = candidate_root / f"{TOOL.CANDIDATE_ID}.json"
        candidate.write_bytes(TOOL.canonical_payload(template))
        candidate.chmod(0o400)
        return repository, candidate_root

    def test_non_fixture_package_binds_exact_candidate(self) -> None:
        record, output = TOOL.prepare(self.package, self.output)
        self.assertEqual(output, self.output)
        self.assertEqual(
            stat.S_IMODE(output.stat().st_mode),
            0o444,
        )
        self.assertEqual(record["candidate"], TOOL.CANDIDATE_ID)
        self.assertEqual(record["bundle"], TOOL.BASE_BUNDLE_ID)
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

    def test_successor_changes_only_the_signed_bundle_identity(self) -> None:
        self.select_accepted_predecessor_root()
        baseline = TOOL.candidate_record(self.values)
        successor, output = TOOL.prepare(
            self.package,
            self.output,
            TOOL.SUCCESSOR_BUNDLE_ID,
        )
        self.assertEqual(output, self.output)
        self.assertEqual(successor["bundle"], TOOL.SUCCESSOR_BUNDLE_ID)
        self.assertEqual(
            {
                key: value
                for key, value in successor.items()
                if key != "bundle"
            },
            {
                key: value
                for key, value in baseline.items()
                if key != "bundle"
            },
        )
        with self.assertRaisesRegex(
            TOOL.DeploymentCandidateError,
            "bundle identity",
        ):
            TOOL.candidate_record(self.values, "headless-ssh-unknown")

    def test_successor_produces_a_distinct_signed_manifest(self) -> None:
        self.select_accepted_predecessor_root()
        repository, candidate_root = self.synthetic_candidate_repository()
        key = self.root / "signing-key.pem"
        subprocess.run(
            [
                "openssl",
                "genpkey",
                "-algorithm",
                "ED25519",
                "-out",
                str(key),
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        key.chmod(0o600)
        with (
            mock.patch.object(TOOL.CANDIDATE, "REPO", repository),
            mock.patch.object(
                TOOL.CANDIDATE,
                "CANDIDATE_ROOT",
                candidate_root,
            ),
        ):
            records = {
                TOOL.BASE_BUNDLE_ID: TOOL.candidate_record(self.values),
                TOOL.SUCCESSOR_BUNDLE_ID: TOOL.candidate_record(
                    self.values,
                    TOOL.SUCCESSOR_BUNDLE_ID,
                ),
            }
            manifests: dict[str, bytes] = {}
            hashes: dict[str, str] = {}
            for bundle, record in records.items():
                candidate = self.root / f"{bundle}.json"
                candidate.write_bytes(TOOL.canonical_payload(record))
                candidate.chmod(0o444)
                bundle_root = self.root / f"bundles-{bundle}"
                bundle_root.mkdir(mode=0o700)
                _record, manifest_hash, _trust = TOOL.CANDIDATE.prepare(
                    TOOL.CANDIDATE_ID,
                    key,
                    bundle_root,
                    candidate,
                    hashlib.sha256(candidate.read_bytes()).hexdigest(),
                )
                manifest = bundle_root / bundle / "manifest"
                manifests[bundle] = manifest.read_bytes()
                hashes[bundle] = manifest_hash
                self.assertIn(
                    f"bundle={bundle}\n".encode(),
                    manifests[bundle],
                )
        self.assertNotEqual(
            hashes[TOOL.BASE_BUNDLE_ID],
            hashes[TOOL.SUCCESSOR_BUNDLE_ID],
        )
        self.assertEqual(
            manifests[TOOL.BASE_BUNDLE_ID].replace(
                f"bundle={TOOL.BASE_BUNDLE_ID}\n".encode(),
                b"bundle=normalized\n",
            ),
            manifests[TOOL.SUCCESSOR_BUNDLE_ID].replace(
                f"bundle={TOOL.SUCCESSOR_BUNDLE_ID}\n".encode(),
                b"bundle=normalized\n",
            ),
        )

    def test_successor_rejects_every_predecessor_root_mutation(self) -> None:
        self.select_accepted_predecessor_root()
        accepted = dict(self.values)
        for field in TOOL.ROOT_FIELDS:
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
                with self.assertRaisesRegex(
                    TOOL.CANDIDATE.CandidateError,
                    "accepted predecessor root",
                ):
                    TOOL.candidate_record(
                        self.values,
                        TOOL.SUCCESSOR_BUNDLE_ID,
                    )
        self.values = accepted

    def test_cli_requires_explicit_bundle_selection(self) -> None:
        with redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                TOOL.parse_arguments(
                    [
                        "--package",
                        str(self.package),
                        "--output",
                        str(self.output),
                    ]
                )
        parsed = TOOL.parse_arguments(
            [
                "--package",
                str(self.package),
                "--bundle",
                TOOL.SUCCESSOR_BUNDLE_ID,
                "--output",
                str(self.output),
            ]
        )
        self.assertEqual(parsed.bundle, TOOL.SUCCESSOR_BUNDLE_ID)

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
