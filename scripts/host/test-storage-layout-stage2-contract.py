#!/usr/bin/env python3
"""Focused source contract for the separately gated native-root Stage 2."""

from __future__ import annotations

import hashlib
from pathlib import Path
import stat
import unittest


REPO = Path(__file__).resolve().parents[2]
EXECUTOR = REPO / "scripts/device/storage-layout-stage2"
BUILDER = REPO / "scripts/device/build-storage-layout-stage2-initramfs.sh"
COLLECTOR = REPO / "scripts/host/collect-storage-layout-stage2.py"
SEAL = REPO / "configs/storage/rog5-native-root-v1.seal"
INIT = REPO / "initramfs/recovery-init"


class StorageLayoutStage2ContractTest(unittest.TestCase):
    def executable_source(self, path: Path) -> str:
        self.assertTrue(path.is_file(), f"missing {path.relative_to(REPO)}")
        self.assertFalse(path.is_symlink())
        self.assertTrue(path.stat().st_mode & stat.S_IXUSR)
        return path.read_text(encoding="utf-8")

    def test_executor_has_one_exact_clone_boundary(self) -> None:
        source = self.executable_source(EXECUTOR)
        for contract in (
            "/etc/rog5/storage-layout-stage2.conf",
            "253403070464",
            "408997568",
            "427819008",
            "67108824",
            'source_image=/mnt/userdata/rog5/images/arch-local-a.ext4',
            'dd if="$source_image" of="$arch_root" bs=4194304 count=4096 conv=fsync',
            'dd if="$arch_root" bs=4194304 count=4096',
            'tune2fs -U "$expected_target_uuid" "$arch_root"',
            'resize2fs "$arch_root"',
            '51124000 rog5-linux',
            '"$source_blocks" ROG5_ARCH_A',
            'mv -f "$seal_next" "$seal_path"',
            '"$verifier" "$target_mount" "$seal_path" "$native_seal_sha256"',
            "verify_safe_temperature",
            "battery_temp\" -lt 500",
            "thermal_temp\" -lt 65000",
            'blockdev --setrw "$arch_root"',
            'blockdev --setro "$disk"',
            'trap - HUP INT TERM',
            '"$expected_userdata_fs_uuid" != "$expected_target_uuid"',
            'e2fsck -f -p "$device"',
        ):
            self.assertIn(contract, source)

        main = source.index("stage_set S00_CONFIG")
        source_hash = source.index('sha256sum "$source_image"', main)
        final_temperature = source.index(
            "verify_safe_temperature", source.index("stage_set S30_WATCHDOG_DISARM")
        )
        disarm = source.index('"$watchdog_disarm"', source.index("stage_set S30_WATCHDOG_DISARM"))
        first_setrw = source.index("open_write_window", source.index("stage_set S40_CLONE"))
        clone = source.index('dd if="$source_image" of="$arch_root"')
        prefix = source.index('dd if="$arch_root" bs=4194304 count=4096')
        uuid = source.index('tune2fs -U "$expected_target_uuid"')
        grow = source.index('resize2fs "$arch_root"')
        seal = source.index('mv -f "$seal_next" "$seal_path"')
        restore_mtime = source.index('touch -d @1681862400 "$target_mount"')
        final_verify = source.index(
            '"$verifier" "$target_mount" "$seal_path" "$native_seal_sha256"'
        )
        self.assertLess(source_hash, disarm)
        self.assertLess(final_temperature, disarm)
        self.assertLess(disarm, first_setrw)
        self.assertLess(first_setrw, clone)
        self.assertLess(clone, prefix)
        self.assertLess(prefix, uuid)
        self.assertLess(uuid, grow)
        self.assertLess(grow, seal)
        self.assertLess(seal, restore_mtime)
        self.assertLess(restore_mtime, final_verify)
        self.assertNotIn("mkfs", source)
        self.assertNotIn("sgdisk --delete", source)
        self.assertNotIn("fastboot", source)
        self.assertNotIn("ROG5_LAYOUT_TEST", source)
        self.assertNotIn('"$status" -eq 1', source)

    def test_executor_classifies_partial_before_clone(self) -> None:
        source = self.executable_source(EXECUTOR)
        partial = source.index("target_state=partial", source.index("stage_set S40_CLONE"))
        clone = source.index('dd if="$source_image" of="$arch_root"')
        self.assertLess(partial, clone)
        for state in ("untouched", "partial", "cloned", "native", "final"):
            self.assertIn(f"target_state={state}", source)

    def test_native_seal_is_the_refreshed_tree(self) -> None:
        payload = SEAL.read_bytes()
        self.assertFalse(
            SEAL.stat().st_mode
            & (stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        )
        self.assertEqual(len(payload), 430)
        self.assertEqual(
            hashlib.sha256(payload).hexdigest(),
            "8dbc66163adde6919d9e48974a035e1a3d27c8d0304befbc806cd284d167be68",
        )
        lines = payload.decode("ascii").splitlines()
        self.assertEqual(len(lines), 13)
        self.assertIn("tree_entries=37738", lines)
        self.assertIn("tree_regular_files=27605", lines)
        self.assertIn("tree_directories=1903", lines)
        self.assertIn(
            "tree_sha256=c804445418eea694667f6529086d7eeaa8e4a82293c86c692e0ebc379fd28e38",
            lines,
        )

    def test_recovery_dispatch_is_sealed_and_requires_900_seconds(self) -> None:
        source = self.executable_source(INIT)
        mode = "storage-layout-stage2-v1"
        executor = "/usr/libexec/rog5-storage-layout-stage2"
        self.assertEqual(source.count(f"\t{mode})"), 1)
        self.assertEqual(source.count(executor), 4)
        self.assertEqual(source.count(f"if ! {executor}; then"), 1)
        self.assertIn(
            'if [ "$recovery_mode" = storage-layout-stage2-v1 ] && [ "$timeout" != 900 ]; then',
            source,
        )
        self.assertNotIn('dd if="$source_image" of="$arch_root"', source)
        self.assertNotIn("tune2fs -U", source)

    def test_builder_seals_every_stage2_input(self) -> None:
        source = self.executable_source(BUILDER)
        for contract in (
            "storage-layout-stage2-v1",
            "/usr/libexec/rog5-storage-layout-stage2",
            "/usr/libexec/rog5-persistent-root-verify",
            "/etc/rog5/storage-layout-stage2.conf",
            "/etc/rog5/native-root-v1.seal",
            'check_hash "$executor" "$executor_sha256"',
            'check_hash "$private_config" "$private_config_sha256"',
            'check_hash "$native_seal" "$native_seal_sha256"',
            'install -m 0444 "$native_seal" "$stage/etc/rog5/native-root-v1.seal"',
            'check_hash "$verifier" "$verifier_sha256"',
            "find . -mindepth 1 -print0 | sort -z",
            "gzip -n",
        ):
            self.assertIn(contract, source)

    def test_collector_is_fixed_to_stage2_acm(self) -> None:
        source = self.executable_source(COLLECTOR)
        for contract in (
            'PREFIX = "ROG5_LAYOUT_STAGE2_V1"',
            '"S40_CLONE"',
            '"S60_NATIVE_SEAL"',
            '"target_blocks": "8388603"',
            "wait_storage_acm",
            "revalidate_storage_acm",
        ):
            self.assertIn(contract, source)


if __name__ == "__main__":
    unittest.main()
