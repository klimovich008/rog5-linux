#!/usr/bin/env python3
"""Regression tests for the Phase-3 ROG5 partition proposal."""

from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


REPO = Path(__file__).resolve().parents[2]
SOURCE = Path(__file__).with_name("verify-dedicated-linux-layout.py")
CONFIG = REPO / "configs/storage/rog5-dedicated-linux-v1.json"
SPEC = importlib.util.spec_from_file_location("rog5_dedicated_linux_layout", SOURCE)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class DedicatedLinuxLayoutTest(unittest.TestCase):
    def setUp(self) -> None:
        self.layout = json.loads(CONFIG.read_text(encoding="ascii"))

    def verify(self, mutation) -> dict[str, int]:
        candidate = copy.deepcopy(self.layout)
        mutation(candidate)
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "layout.json"
            path.write_text(json.dumps(candidate), encoding="ascii")
            return MODULE.verify(path)

    def rejected(self, mutation, message: str) -> None:
        with self.assertRaisesRegex(MODULE.LayoutError, message):
            self.verify(mutation)

    def test_current_proposal_is_exact(self) -> None:
        result = MODULE.verify(CONFIG)
        self.assertEqual(result["userdata_bytes"], 209406754816)
        self.assertEqual(result["arch_root_bytes"], 34359717888)
        self.assertEqual(result["ext4_headroom_bytes"], 161486983168)

    def test_overlap_or_gap_is_rejected(self) -> None:
        self.rejected(
            lambda data: data["proposal"]["arch_root_a"].update(first_lba=53477375, size_lba=8388604),
            "overlap or leave a gap",
        )

    def test_unaligned_root_is_rejected(self) -> None:
        def mutate(data):
            data["proposal"]["userdata"].update(last_lba=53477376, size_lba=51124697)
            data["proposal"]["arch_root_a"].update(first_lba=53477377, size_lba=8388602)

        self.rejected(mutate, "not 1 MiB aligned")

    def test_changed_protected_set_is_rejected(self) -> None:
        self.rejected(
            lambda data: data["proposal"]["unchanged_partition_numbers"].pop(),
            "protected partition set changed",
        )

    def test_ext4_minimum_without_headroom_is_rejected(self) -> None:
        self.rejected(
            lambda data: data["ext4_checkpoint"].update(estimated_minimum_blocks=51124000),
            "no measured ext4 headroom",
        )

    def test_pre_shrink_without_boundary_margin_is_rejected(self) -> None:
        self.rejected(
            lambda data: data["proposal"]["userdata"].update(pre_shrink_filesystem_blocks=51124695),
            "lacks a partition-boundary margin",
        )

    def test_changed_tail_or_entry_is_rejected(self) -> None:
        self.rejected(
            lambda data: data["proposal"]["arch_root_a"].update(last_lba=61865977, size_lba=8388602),
            "existing last usable LBA",
        )
        self.rejected(
            lambda data: data["proposal"]["arch_root_a"].update(number=33),
            "GPT entry is unavailable",
        )

    def test_wrong_root_identity_is_rejected(self) -> None:
        self.rejected(
            lambda data: data["proposal"]["arch_root_a"].update(type_guid="deadbeef"),
            "GPT identity changed",
        )
        self.rejected(
            lambda data: data["proposal"]["arch_root_a"].update(filesystem_label="root"),
            "filesystem identity changed",
        )


if __name__ == "__main__":
    unittest.main()
