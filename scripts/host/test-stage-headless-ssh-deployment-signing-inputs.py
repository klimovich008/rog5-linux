#!/usr/bin/env python3
"""Offline tests for private deployment signing-input staging."""

from __future__ import annotations

import hashlib
import importlib.util
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest


REPO = Path(__file__).resolve().parents[2]
TOOL_PATH = (
    REPO / "scripts/host/stage-headless-ssh-deployment-signing-inputs.py"
)
FIXTURE_CANDIDATE = (
    REPO / "configs/recovery-candidates/headless-ssh-network-root-v3.json"
)


def load_module():
    specification = importlib.util.spec_from_file_location(
        "rog5_deployment_signing_inputs_test",
        TOOL_PATH,
    )
    if specification is None or specification.loader is None:
        raise RuntimeError("cannot load deployment signing-input tool")
    module = importlib.util.module_from_spec(specification)
    sys.modules[specification.name] = module
    specification.loader.exec_module(module)
    return module


TOOL = load_module()


class SigningInputTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(
            prefix="rog5-deployment-signing-inputs-"
        )
        self.root = Path(self.temporary.name)
        self.root.chmod(0o700)
        self.remote = self.root / "remote.git"
        self.repository = self.root / "repository"
        self.private = self.root / "private"
        self.stage = self.root / "stage"
        self.private.mkdir(mode=0o700)
        self.stage.mkdir(mode=0o700)
        self.git("init", "--bare", str(self.remote), cwd=self.root)
        self.git("clone", str(self.remote), str(self.repository), cwd=self.root)
        self.repository.chmod(0o700)
        self.git("config", "user.name", "ROG5 Test", cwd=self.repository)
        self.git(
            "config",
            "user.email",
            "rog5-test@example.invalid",
            cwd=self.repository,
        )
        (self.repository / "seed").write_text("seed\n", encoding="ascii")
        self.git("add", "seed", cwd=self.repository)
        self.git("commit", "-m", "seed", cwd=self.repository)
        self.git("push", "-u", "origin", "HEAD", cwd=self.repository)

        self.key = self.private / "recovery-signing.pem"
        self.candidate = self.private / "candidate.json"
        self.run_openssl(
            "genpkey",
            "-algorithm",
            "ED25519",
            "-out",
            str(self.key),
        )
        self.key.chmod(0o600)
        shutil.copyfile(FIXTURE_CANDIDATE, self.candidate)
        self.candidate.chmod(0o444)
        self.staged_key = self.stage / "signing.pem"
        self.staged_candidate = self.stage / "candidate.json"
        self.public = self.stage / "public.raw"

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def git(self, *arguments: str, cwd: Path) -> None:
        subprocess.run(
            ["/usr/bin/git", *arguments],
            cwd=cwd,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            env={
                "PATH": "/usr/bin:/bin",
                "LC_ALL": "C",
                "GIT_CONFIG_NOSYSTEM": "1",
            },
            timeout=15,
            check=True,
        )

    def run_openssl(self, *arguments: str) -> None:
        subprocess.run(
            ["/usr/bin/openssl", *arguments],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=15,
            check=True,
        )

    def stage_inputs(self) -> tuple[str, str, str]:
        return TOOL.stage_inputs(
            self.repository,
            self.key,
            self.candidate,
            self.staged_key,
            self.staged_candidate,
            self.public,
        )

    def reset_outputs(self) -> None:
        for path in (
            self.staged_key,
            self.staged_candidate,
            self.public,
        ):
            path.unlink(missing_ok=True)

    def replace_key(self, *openssl_arguments: str) -> None:
        self.key.chmod(0o600)
        self.key.unlink()
        self.run_openssl(*openssl_arguments, "-out", str(self.key))
        self.key.chmod(0o600)

    def test_exact_ed25519_inputs_are_snapshotted_without_source_change(
        self,
    ) -> None:
        key_before = self.key.read_bytes()
        candidate_before = self.candidate.read_bytes()
        checkpoint, candidate_sha256, public_sha256 = self.stage_inputs()
        self.assertEqual(
            checkpoint,
            subprocess.run(
                ["/usr/bin/git", "-C", str(self.repository), "rev-parse", "HEAD"],
                check=True,
                stdout=subprocess.PIPE,
                text=True,
            ).stdout.strip(),
        )
        self.assertEqual(self.staged_key.read_bytes(), key_before)
        self.assertEqual(
            self.staged_candidate.read_bytes(),
            candidate_before,
        )
        self.assertEqual(self.key.read_bytes(), key_before)
        self.assertEqual(self.candidate.read_bytes(), candidate_before)
        self.assertEqual(stat.S_IMODE(self.staged_key.stat().st_mode), 0o600)
        self.assertEqual(
            stat.S_IMODE(self.staged_candidate.stat().st_mode),
            0o444,
        )
        self.assertEqual(stat.S_IMODE(self.public.stat().st_mode), 0o400)
        self.assertEqual(len(self.public.read_bytes()), 32)
        self.assertEqual(
            public_sha256,
            hashlib.sha256(self.public.read_bytes()).hexdigest(),
        )
        self.assertEqual(
            candidate_sha256,
            hashlib.sha256(candidate_before).hexdigest(),
        )

    def test_non_ed25519_and_encrypted_keys_are_rejected(self) -> None:
        cases = (
            (
                "rsa",
                ("genpkey", "-algorithm", "RSA", "-pkeyopt", "rsa_keygen_bits:2048"),
                "not Ed25519",
            ),
            (
                "x25519",
                ("genpkey", "-algorithm", "X25519"),
                "not Ed25519",
            ),
            (
                "encrypted",
                (
                    "genpkey",
                    "-algorithm",
                    "ED25519",
                    "-aes-256-cbc",
                    "-pass",
                    "pass:test-only",
                ),
                "not unencrypted PKCS#8",
            ),
        )
        for name, command, message in cases:
            with self.subTest(name=name):
                self.reset_outputs()
                self.replace_key(*command)
                before = self.key.read_bytes()
                with self.assertRaisesRegex(TOOL.SigningInputError, message):
                    self.stage_inputs()
                self.assertEqual(self.key.read_bytes(), before)
                self.assertFalse(self.staged_key.exists())
                self.assertFalse(self.staged_candidate.exists())
                self.assertFalse(self.public.exists())

    def test_unsafe_key_and_candidate_metadata_are_rejected(self) -> None:
        cases = ("key-mode", "key-hardlink", "candidate-mode", "candidate-symlink")
        for case in cases:
            with self.subTest(case=case):
                self.tearDown()
                self.setUp()
                if case == "key-mode":
                    self.key.chmod(0o644)
                elif case == "key-hardlink":
                    self.key.with_suffix(".copy").hardlink_to(self.key)
                elif case == "candidate-mode":
                    self.candidate.chmod(0o644)
                else:
                    real = self.private / "candidate.real"
                    self.candidate.rename(real)
                    self.candidate.symlink_to(real.name)
                with self.assertRaises(
                    (OSError, TOOL.SigningInputError)
                ):
                    self.stage_inputs()

    def test_invalid_candidate_is_rejected_before_staging(self) -> None:
        self.candidate.chmod(0o600)
        self.candidate.write_text("{}\n", encoding="ascii")
        self.candidate.chmod(0o444)
        with self.assertRaises(
            (TOOL.CANDIDATE.CandidateError, TOOL.SigningInputError)
        ):
            self.stage_inputs()
        self.assertFalse(self.staged_key.exists())

    def test_dirty_unpushed_and_wrong_upstream_repositories_are_rejected(
        self,
    ) -> None:
        (self.repository / "dirty").write_text("dirty\n", encoding="ascii")
        with self.assertRaisesRegex(
            TOOL.SigningInputError,
            "must be clean",
        ):
            self.stage_inputs()
        (self.repository / "dirty").unlink()

        (self.repository / "seed").write_text("unpushed\n", encoding="ascii")
        self.git("add", "seed", cwd=self.repository)
        self.git("commit", "-m", "unpushed", cwd=self.repository)
        with self.assertRaisesRegex(
            TOOL.SigningInputError,
            "differs from its origin peer",
        ):
            self.stage_inputs()

    def test_repository_internal_credential_is_rejected(self) -> None:
        internal = self.repository / "signing.pem"
        shutil.copyfile(self.key, internal)
        internal.chmod(0o600)
        self.git("add", "signing.pem", cwd=self.repository)
        self.git("commit", "-m", "test internal input", cwd=self.repository)
        self.git("push", cwd=self.repository)
        with self.assertRaisesRegex(
            TOOL.SigningInputError,
            "outside the repository",
        ):
            TOOL.stage_inputs(
                self.repository,
                internal,
                self.candidate,
                self.staged_key,
                self.staged_candidate,
                self.public,
            )

    def test_existing_output_is_never_replaced(self) -> None:
        self.staged_key.write_text("occupied\n", encoding="ascii")
        self.staged_key.chmod(0o600)
        before = self.staged_key.read_bytes()
        with self.assertRaises(FileExistsError):
            self.stage_inputs()
        self.assertEqual(self.staged_key.read_bytes(), before)
        self.assertFalse(self.staged_candidate.exists())
        self.assertFalse(self.public.exists())


if __name__ == "__main__":
    unittest.main()
