#!/usr/bin/env python3
"""Offline-root extraction must not escape through paths or archive links."""
import importlib.util
from pathlib import Path
import stat
import shutil
import tempfile
import unittest

SPEC = importlib.util.spec_from_file_location("sealed", Path(__file__).with_name("run-sealed-busybox.py"))
M = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(M)


def entry(mode, body=b""):
    fields = [0] * 13
    fields[1], fields[4] = mode, 1
    return fields, body


class Extraction(unittest.TestCase):
    @unittest.skipUnless(shutil.which("bwrap") and shutil.which("qemu-aarch64-static"),
                         "requires optional isolated ARM userspace tools")
    def test_actual_archive_ownership_is_root_inside_namespace(self):
        result, _ = M.run(
            M.REPO / "artifacts/network-root-v3/rog5-network-root-initramfs.cpio.gz",
            "7.1.4-test", ["stat", "-c", "%u:%g:%a", "/bin/busybox"],
            qemu=Path(shutil.which("qemu-aarch64-static")),
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, b"0:0:755\n")

    def test_exact_regular_payload_and_symlink_preserved(self):
        with tempfile.TemporaryDirectory() as scratch:
            root = Path(scratch)
            M.extract({"bin": entry(stat.S_IFDIR | 0o755),
                       "bin/busybox": entry(stat.S_IFREG | 0o755, b"fixture"),
                       "bin/sh": entry(stat.S_IFLNK | 0o777, b"busybox")}, root)
            self.assertEqual((root / "bin/sh").read_bytes(), b"fixture")
            self.assertTrue((root / "bin/sh").is_symlink())
            self.assertEqual((root / "bin").stat().st_mode & 0o777, 0o755)
            self.assertEqual((root / "bin/busybox").stat().st_mode & 0o777, 0o755)

    def test_rejects_host_escape_special_files_and_linked_parent_before_writing(self):
        for members in (
            {"../escape": entry(stat.S_IFREG | 0o644)},
            {"/absolute": entry(stat.S_IFREG | 0o644)},
            {"a/./b": entry(stat.S_IFREG | 0o644)},
            {"rog5-qemu": entry(stat.S_IFREG | 0o755)},
            {"device": entry(stat.S_IFBLK | 0o600)},
            {"a": entry(stat.S_IFLNK | 0o777, b"/tmp"),
             "a/escape": entry(stat.S_IFREG | 0o644)},
        ):
            with self.subTest(members=members), tempfile.TemporaryDirectory() as scratch:
                root = Path(scratch)
                with self.assertRaises(ValueError):
                    M.extract(members, root)
                self.assertEqual(list(root.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
