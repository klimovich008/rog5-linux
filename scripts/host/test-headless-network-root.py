#!/usr/bin/env python3
"""Offline tests for the sealed headless network-root package."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


REPO = Path(__file__).resolve().parents[2]
TOOL_PATH = REPO / "scripts/host/headless-network-root.py"
COMMAND = REPO / "packaging/arch/rog5-headless-command-manifest"


def load_module():
    specification = importlib.util.spec_from_file_location(
        "rog5_headless_network_root_test",
        TOOL_PATH,
    )
    if specification is None or specification.loader is None:
        raise RuntimeError("cannot load headless network-root tool")
    module = importlib.util.module_from_spec(specification)
    sys.modules[specification.name] = module
    specification.loader.exec_module(module)
    return module


TOOL = load_module()


class HeadlessNetworkRootTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if shutil.which("bsdtar") is None:
            raise RuntimeError("bsdtar is required")

    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name) / "root"
        (self.root / "etc/rog5").mkdir(parents=True)
        (self.root / "usr/lib/rog5").mkdir(parents=True)
        (self.root / "etc/rog5/build").write_text(
            "profile=headless-ssh-v1\n"
            "project_commit=eb61a45938c851b1b02a2f3151db5265ab9213e7\n"
            f"rootfs_sha256={'a' * 64}\n"
            f"modules_sha256={'b' * 64}\n"
            "kernel_release=7.1.4-g7a5cef0db479\n",
            encoding="ascii",
        )
        (self.root / "usr/lib/rog5/payload").write_text(
            "fixture\n",
            encoding="ascii",
        )
        self.identity = Path(self.temporary.name) / "identity"
        self.archive = Path(self.temporary.name) / "sealed.tar"
        self.package = Path(self.temporary.name) / "manifest"

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def prepare_package(self) -> None:
        TOOL.prepare(
            self.root,
            "123",
            "c" * 64,
            COMMAND,
            self.identity,
        )
        subprocess.run(
            [
                "bsdtar",
                "--acls",
                "--xattrs",
                "--fflags",
                "-cpf",
                str(self.archive),
                "-C",
                str(self.root),
                ".",
            ],
            check=True,
        )
        TOOL.package(self.identity, self.archive, self.package)

    def test_no_workload_root_is_fully_bound(self) -> None:
        self.prepare_package()
        values = TOOL.verify(
            self.root,
            self.archive,
            self.package,
            COMMAND,
        )
        self.assertEqual(values["profile"], "network-root-v1")
        self.assertEqual(values["root_generation"], "arch-a")
        self.assertEqual(values["root_subtree"], "/")
        self.assertGreater(int(values["root_tree_entries"]), 1)
        self.assertRegex(values["root_tree_sha256"], r"^[0-9a-f]{64}$")
        self.assertRegex(values["root_seal_sha256"], r"^[0-9a-f]{64}$")
        self.assertEqual(
            (self.root / "etc/rog5/a660-command-manifest").read_text(
                encoding="ascii"
            ),
            COMMAND.read_text(encoding="ascii"),
        )

    def test_tree_archive_and_command_mutations_refuse(self) -> None:
        cases = ("tree", "archive", "command")
        for case in cases:
            with self.subTest(case=case):
                self.tearDown()
                self.setUp()
                self.prepare_package()
                if case == "tree":
                    (self.root / "usr/lib/rog5/payload").write_text(
                        "changed\n",
                        encoding="ascii",
                    )
                elif case == "archive":
                    with self.archive.open("ab") as stream:
                        stream.write(b"x")
                else:
                    installed = self.root / "etc/rog5/a660-command-manifest"
                    installed.chmod(0o600)
                    installed.write_text(
                        "format=rog5-headless-command-manifest-v1\n"
                        "workload=gpu\n",
                        encoding="ascii",
                    )
                    installed.chmod(0o400)
                with self.assertRaises(
                    (TOOL.HeadlessRootError, TOOL.ROOT_TOOL.ContractError)
                ):
                    TOOL.verify(
                        self.root,
                        self.archive,
                        self.package,
                        COMMAND,
                    )


if __name__ == "__main__":
    unittest.main()
