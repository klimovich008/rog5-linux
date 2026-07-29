#!/usr/bin/env python3
"""Offline tests for the strict candidate-to-bundle adapter."""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


REPO = Path(__file__).resolve().parents[2]
RUNNER_PATH = REPO / "scripts" / "host" / "prepare-recovery-candidate.py"


def load_module():
    specification = importlib.util.spec_from_file_location(
        "rog5_candidate_runner_test",
        RUNNER_PATH,
    )
    if specification is None or specification.loader is None:
        raise RuntimeError("cannot load candidate runner")
    module = importlib.util.module_from_spec(specification)
    sys.modules[specification.name] = module
    specification.loader.exec_module(module)
    return module


RUNNER = load_module()


def sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


class RecoveryCandidateTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if shutil.which("openssl") is None:
            raise RuntimeError("openssl is required")
        cls.original_repo = RUNNER.REPO
        cls.original_candidate_root = RUNNER.CANDIDATE_ROOT

    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.repo = self.root / "repo"
        self.candidates = self.repo / "configs" / "recovery-candidates"
        self.artifacts = self.repo / "artifacts" / "fixture"
        self.candidates.mkdir(parents=True)
        self.artifacts.mkdir(parents=True)
        self.payloads = {
            "Image": bytes(range(64)),
            "board.dtb": b"D" * 40,
            "initramfs.cpio.gz": b"\x1f\x8b",
        }
        self.paths = {
            "Image": "artifacts/fixture/Image",
            "board.dtb": "artifacts/fixture/board.dtb",
            "initramfs.cpio.gz": "artifacts/fixture/initramfs.cpio.gz",
        }
        for name, payload in self.payloads.items():
            destination = self.repo / self.paths[name]
            destination.write_bytes(payload)
            destination.chmod(0o444)
        self.record = {
            "format": "rog5-recovery-candidate-v1",
            "candidate": "fixture",
            "status": "consumed",
            "authority": "none",
            "bundle": "fixture",
            "profile": "persistent-root-ro-v1",
            "target_id": "fixture",
            "target_release": "7.1.4-test",
            "rollback_timeout": "600",
            "target_timeout": "480",
            "a660_command_manifest_sha256": "0" * 64,
            "root_generation": "none",
            "root_tree_sha256": "0" * 64,
            "root_seal_sha256": "0" * 64,
            "root_tree_entries": "0",
            "root_subtree": "none",
            "artifacts": {
                name: {
                    "path": self.paths[name],
                    "size": len(self.payloads[name]),
                    "sha256": sha256(self.payloads[name]),
                }
                for name in RUNNER.ARTIFACT_NAMES
            },
        }
        self.write_record(self.record)
        self.private_key = self.root / "test-ed25519.pem"
        subprocess.run(
            [
                "openssl",
                "genpkey",
                "-algorithm",
                "ED25519",
                "-out",
                str(self.private_key),
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        self.private_key.chmod(0o600)
        self.bundle_root = self.root / "bundles"
        self.bundle_root.mkdir(mode=0o700)
        RUNNER.REPO = self.repo
        RUNNER.CANDIDATE_ROOT = self.candidates

    def tearDown(self) -> None:
        RUNNER.REPO = self.original_repo
        RUNNER.CANDIDATE_ROOT = self.original_candidate_root
        self.temporary.cleanup()

    def write_record(self, record: dict) -> None:
        path = self.candidates / f"{record['candidate']}.json"
        path.write_text(
            json.dumps(record, indent=2) + "\n",
            encoding="ascii",
        )
        path.chmod(0o644)

    def test_consumed_candidate_packages_offline(self) -> None:
        record, manifest_hash, trust_hash = RUNNER.prepare(
            "fixture",
            self.private_key,
            self.bundle_root,
        )
        self.assertEqual(record["authority"], "none")
        self.assertRegex(manifest_hash, r"^[0-9a-f]{64}$")
        self.assertRegex(trust_hash, r"^[0-9a-f]{64}$")
        bundle = self.bundle_root / "fixture"
        self.assertEqual(
            {path.name for path in bundle.iterdir()},
            {
                "Image",
                "board.dtb",
                "initramfs.cpio.gz",
                "manifest",
                "manifest.sig",
            },
        )
        manifest = (bundle / "manifest").read_text(encoding="ascii")
        self.assertIn("profile=persistent-root-ro-v1\n", manifest)
        self.assertIn("target_id=fixture\n", manifest)
        self.assertEqual((bundle / "manifest.sig").stat().st_size, 64)

    def test_live_authority_and_unknown_fields_refuse(self) -> None:
        for mutation in ("authority", "unknown"):
            record = copy.deepcopy(self.record)
            if mutation == "authority":
                record["authority"] = "live"
            else:
                record["extra"] = "no"
            self.write_record(record)
            with self.assertRaises(RUNNER.CandidateError):
                RUNNER.load_candidate("fixture")

    def test_artifact_identity_change_refuses(self) -> None:
        (self.repo / self.paths["Image"]).chmod(0o644)
        (self.repo / self.paths["Image"]).write_bytes(b"X" * 64)
        (self.repo / self.paths["Image"]).chmod(0o444)
        with self.assertRaises(RUNNER.CandidateError):
            RUNNER.prepare("fixture", self.private_key, self.bundle_root)

    def test_tracked_parity_record_matches_inventory(self) -> None:
        RUNNER.REPO = self.original_repo
        RUNNER.CANDIDATE_ROOT = self.original_candidate_root
        record = RUNNER.load_candidate("persistent-root-p2-parity")
        inventory = {}
        for line in (REPO / "manifests" / "artifacts.tsv").read_text().splitlines():
            fields = line.split("\t")
            if len(fields) >= 3 and fields[1].isdecimal():
                inventory[fields[0]] = (int(fields[1]), fields[2])
        for artifact in record["artifacts"].values():
            self.assertEqual(
                (artifact["size"], artifact["sha256"]),
                inventory[artifact["path"]],
            )

    def test_adapter_has_no_live_transport(self) -> None:
        source = RUNNER_PATH.read_text(encoding="utf-8")
        for token in (
            "fastboot",
            "adb",
            "rog5-recovery-bundle-controller",
            "run-recovery-bundle-server",
            "systemctl",
        ):
            self.assertNotIn(token, source)


if __name__ == "__main__":
    unittest.main()
