#!/usr/bin/env python3
"""Hostile tests for root-archive semantic inventory comparison."""

from __future__ import annotations

from io import BytesIO
import importlib.util
from pathlib import Path
import sys
import tarfile
import tempfile
import unittest


REPO = Path(__file__).resolve().parents[2]
TOOL_PATH = REPO / "scripts/host/compare-root-archives.py"


def load_module():
    specification = importlib.util.spec_from_file_location(
        "rog5_compare_root_archives_test",
        TOOL_PATH,
    )
    if specification is None or specification.loader is None:
        raise RuntimeError("cannot load archive-comparison tool")
    module = importlib.util.module_from_spec(specification)
    sys.modules[specification.name] = module
    specification.loader.exec_module(module)
    return module


TOOL = load_module()


class RootArchiveComparisonTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.source = self.root / "source.tar"
        self.normalized = self.root / "normalized.tar"

    def tearDown(self) -> None:
        self.temporary.cleanup()

    @staticmethod
    def write_archive(
        path: Path,
        *,
        extra: bool = False,
        flags: str = "nocow",
        independent_copy: bool = False,
        unsafe: bool = False,
    ) -> None:
        with tarfile.open(path, mode="w", format=tarfile.PAX_FORMAT) as archive:
            directory = tarfile.TarInfo("./state/")
            directory.type = tarfile.DIRTYPE
            directory.mode = 0o755
            if flags:
                directory.pax_headers["SCHILY.fflags"] = flags
            archive.addfile(directory)

            payload = b"fixed\n"
            regular = tarfile.TarInfo("./state/value")
            regular.size = len(payload)
            regular.mode = 0o444
            archive.addfile(regular, BytesIO(payload))

            duplicate = tarfile.TarInfo("./state/copy")
            duplicate.mode = 0o444
            if independent_copy:
                duplicate.size = len(payload)
                archive.addfile(duplicate, BytesIO(payload))
            else:
                duplicate.type = tarfile.LNKTYPE
                duplicate.linkname = "./state/value"
                archive.addfile(duplicate)

            if extra:
                added = tarfile.TarInfo("./unexpected")
                added.size = 1
                archive.addfile(added, BytesIO(b"x"))
            if unsafe:
                escaped = tarfile.TarInfo("../escape")
                escaped.size = 1
                archive.addfile(escaped, BytesIO(b"x"))

    def test_exact_inventory_flags_and_hardlinks_pass(self) -> None:
        self.write_archive(self.source)
        self.write_archive(self.normalized)
        TOOL.compare(self.source, self.normalized)

    def test_added_path_is_rejected(self) -> None:
        self.write_archive(self.source)
        self.write_archive(self.normalized, extra=True)
        with self.assertRaises(TOOL.ArchiveComparisonError):
            TOOL.compare(self.source, self.normalized)

    def test_inode_flag_loss_is_rejected(self) -> None:
        self.write_archive(self.source)
        self.write_archive(self.normalized, flags="")
        with self.assertRaises(TOOL.ArchiveComparisonError):
            TOOL.compare(self.source, self.normalized)

    def test_hardlink_topology_change_is_rejected(self) -> None:
        self.write_archive(self.source)
        self.write_archive(self.normalized, independent_copy=True)
        with self.assertRaises(TOOL.ArchiveComparisonError):
            TOOL.compare(self.source, self.normalized)

    def test_unsafe_path_is_rejected(self) -> None:
        self.write_archive(self.source)
        self.write_archive(self.normalized, unsafe=True)
        with self.assertRaises(TOOL.ArchiveComparisonError):
            TOOL.compare(self.source, self.normalized)


if __name__ == "__main__":
    unittest.main()
