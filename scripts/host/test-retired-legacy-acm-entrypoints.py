#!/usr/bin/env python3
"""Prove superseded interactive ACM entry points are evidence-only."""

from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import re
import subprocess
import sys
import unittest
from unittest import mock


sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
RETIRED_MESSAGE = (
    "legacy interactive ACM execution is retired; "
    "use the framed stable-recovery lifecycle"
)
PYTHON_ENTRYPOINTS = (
    ROOT / "scripts/host/network-root-acm.py",
    ROOT / "scripts/host/persistent-root-acm.py",
    ROOT / "scripts/host/persistent-root-entry-acm.py",
)
SHELL_ENTRYPOINTS = (
    ROOT / "scripts/host/run-persistent-root-p2-live-gate.sh",
    ROOT / "scripts/host/run-persistent-root-entry-live-gate.sh",
)


def load(path: Path):
    spec = importlib.util.spec_from_file_location(
        f"retired_{path.stem.replace('-', '_')}", path
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ForbiddenEnvironment:
    def get(self, *args, **kwargs):
        raise AssertionError(f"retired entry point inspected environment: {args!r}")


class RetiredLegacyAcmEntrypointsTest(unittest.TestCase):
    def test_python_entrypoints_refuse_before_host_or_device_inspection(self) -> None:
        for path in PYTHON_ENTRYPOINTS:
            with self.subTest(path=path.name):
                module = load(path)
                self.assertEqual(module.RETIRED_MESSAGE, RETIRED_MESSAGE)
                with (
                    mock.patch.object(module.os, "environ", ForbiddenEnvironment()),
                    mock.patch.object(module.os, "uname") as uname,
                    mock.patch.object(module.shutil, "which") as which,
                    mock.patch.object(module.subprocess, "run") as run,
                ):
                    with self.assertRaisesRegex(
                        RuntimeError,
                        f"^{re.escape(RETIRED_MESSAGE)}$",
                    ):
                        module.main(["execute"])
                uname.assert_not_called()
                which.assert_not_called()
                run.assert_not_called()

    def test_shell_live_gates_refuse_before_authority_or_host_inspection(self) -> None:
        marker = f"fail '{RETIRED_MESSAGE}'"
        for path in SHELL_ENTRYPOINTS:
            with self.subTest(path=path.name):
                source = path.read_text()
                self.assertIn(marker, source)
                self.assertLess(source.index(marker), source.index("[[ ${ALLOW_"))
                self.assertLess(source.index(marker), source.index("repo=$("))

                result = subprocess.run(
                    [path],
                    check=False,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    env={**os.environ, "PATH": os.environ.get("PATH", "")},
                    text=True,
                )
                self.assertEqual(result.returncode, 1)
                self.assertEqual(result.stdout, "")
                self.assertEqual(result.stderr, f"FAIL {RETIRED_MESSAGE}\n")

    def test_historical_sources_remain_present(self) -> None:
        for path in (*PYTHON_ENTRYPOINTS, *SHELL_ENTRYPOINTS):
            with self.subTest(path=path.name):
                self.assertTrue(path.is_file())


if __name__ == "__main__":
    unittest.main(verbosity=2)
