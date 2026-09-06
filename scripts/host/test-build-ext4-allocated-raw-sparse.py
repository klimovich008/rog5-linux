#!/usr/bin/env python3
"""Hardware-free contract for allocated-block RAW Android sparse repair."""

from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest


REPO = Path(__file__).resolve().parents[2]
TOOL = REPO / "scripts/host/build-ext4-allocated-raw-sparse.py"
SPEC = importlib.util.spec_from_file_location("rog5_ext4_raw_sparse", TOOL)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("cannot import sparse builder")
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class AllocatedRawSparseTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.root.chmod(0o700)
        self.source = self.root / "source.ext4"
        self.output = self.root / "output.sparse"
        self.uuid = "12345678-1234-4321-8765-123456789abc"
        subprocess.run(["truncate", "-s", "32M", self.source], check=True)
        subprocess.run(
            [
                "/usr/bin/mkfs.ext4",
                "-q",
                "-F",
                "-b",
                "4096",
                "-L",
                "ROG5_TEST",
                "-U",
                self.uuid,
                self.source,
            ],
            check=True,
        )
        payload = self.root / "payload"
        payload.write_bytes(b"A" * 4096 + b"\0" * 4096 + b"B" * 4096)
        subprocess.run(
            ["/usr/bin/debugfs", "-w", "-R", f"write {payload} /payload", self.source],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        subprocess.run(
            ["/usr/bin/e2fsck", "-f", "-p", self.source],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        self.source.chmod(0o600)

    def run_builder(self, digest: str | None = None) -> subprocess.CompletedProcess[str]:
        source_digest = digest or hashlib.sha256(self.source.read_bytes()).hexdigest()
        return subprocess.run(
            [
                sys.executable,
                str(TOOL),
                str(self.source),
                str(self.output),
                "--expected-blocks",
                str(self.source.stat().st_size // 4096),
                "--expected-uuid",
                self.uuid,
                "--expected-label",
                "ROG5_TEST",
                "--expected-source-sha256",
                source_digest,
            ],
            text=True,
            capture_output=True,
            check=False,
        )

    def expand(self) -> tuple[bytes, list[tuple[int, int, int]]]:
        payload = self.output.read_bytes()
        magic, major, minor, file_header, chunk_header, block_size, blocks, count, checksum = struct.unpack_from(
            "<IHHHHIIII", payload
        )
        self.assertEqual(
            (magic, major, minor, file_header, chunk_header, block_size, checksum),
            (MODULE.SPARSE_MAGIC, 1, 0, 28, 12, 4096, 0),
        )
        expanded = bytearray(blocks * block_size)
        chunks = []
        cursor = 28
        block_cursor = 0
        for _ in range(count):
            kind, reserved, chunk_blocks, total_size = struct.unpack_from(
                "<HHII", payload, cursor
            )
            self.assertEqual(reserved, 0)
            cursor += 12
            chunks.append((kind, block_cursor, chunk_blocks))
            if kind == MODULE.RAW_CHUNK:
                size = chunk_blocks * block_size
                self.assertEqual(total_size, 12 + size)
                expanded[block_cursor * block_size : (block_cursor + chunk_blocks) * block_size] = payload[
                    cursor : cursor + size
                ]
                cursor += size
            else:
                self.assertEqual(kind, MODULE.DONT_CARE_CHUNK)
                self.assertEqual(total_size, 12)
            block_cursor += chunk_blocks
        self.assertEqual(cursor, len(payload))
        self.assertEqual(block_cursor, blocks)
        return bytes(expanded), chunks

    def test_allocated_blocks_are_raw_including_zero_content(self) -> None:
        result = self.run_builder()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("result=PASS", result.stdout)
        expanded, chunks = self.expand()
        self.assertEqual(expanded, self.source.read_bytes())
        self.assertTrue(any(kind == MODULE.RAW_CHUNK for kind, _first, _count in chunks))
        self.assertTrue(
            any(kind == MODULE.DONT_CARE_CHUNK for kind, _first, _count in chunks)
        )
        self.assertEqual(self.output.stat().st_mode & 0o777, 0o400)

    def test_wrong_source_hash_refuses_without_output(self) -> None:
        result = self.run_builder("0" * 64)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.output.exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
