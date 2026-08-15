#!/usr/bin/env python3
"""Fail-closed source contract for the one-shot storage-layout stage 1."""

from __future__ import annotations

from pathlib import Path
import stat
import unittest


REPO = Path(__file__).resolve().parents[2]
EXECUTOR = REPO / "scripts/device/storage-layout-stage1"
BUILDER = REPO / "scripts/device/build-storage-layout-stage1-initramfs.sh"
WATCHDOG_DISARM = REPO / "scripts/device/disarm-recovery-layout-watchdog.sh"
INIT = REPO / "initramfs/recovery-init"


class StorageLayoutStage1ContractTest(unittest.TestCase):
    def executable_source(self, path: Path) -> str:
        self.assertTrue(path.is_file(), f"missing {path.relative_to(REPO)}")
        self.assertFalse(path.is_symlink())
        self.assertTrue(path.stat().st_mode & stat.S_IXUSR)
        return path.read_text(encoding="utf-8")

    def test_executor_has_one_exact_mutation_boundary(self) -> None:
        source = self.executable_source(EXECUTOR)
        for contract in (
            "/etc/rog5/storage-layout-stage1.conf",
            "253403070464",
            "2352680",
            "61865978",
            "51124000",
            "53477375",
            "53477376",
            "--set-alignment=1",
            'sgdisk --backup="$gpt_backup" "$disk"',
            '"$watchdog_disarm"',
            'blockdev --setrw "$disk"',
            'blockdev --setrw "$userdata"',
            'resize2fs "$userdata" 51124000',
            "--delete=23",
            "--new=23:2352680:53477375",
            "--new=24:53477376:61865978",
            'sgdisk --load-backup="$gpt_backup" "$disk"',
            'blockdev --setro "$device"',
        ):
            self.assertIn(contract, source)

        backup = source.index('sgdisk --backup="$gpt_backup" "$disk"')
        ack = source.index("BACKUP_ACK")
        disarm = source.index('"$watchdog_disarm"')
        first_setrw = source.rindex('blockdev --setrw "$disk"')
        shrink = source.index('resize2fs "$userdata" 51124000')
        transaction = source.index("--delete=23")
        self.assertLess(backup, ack)
        self.assertLess(ack, disarm)
        self.assertLess(disarm, first_setrw)
        self.assertLess(first_setrw, shrink)
        self.assertLess(shrink, transaction)
        self.assertNotIn("mkfs", source)
        self.assertNotIn("/rog5/images/arch-local-a.ext4", source)
        self.assertNotIn("ROG5_LAYOUT_TEST", source)

    def test_recovery_dispatches_only_the_sealed_executor(self) -> None:
        source = self.executable_source(INIT)
        mode = "storage-layout-stage1-v1"
        executor = "/usr/libexec/rog5-storage-layout-stage1"
        self.assertEqual(source.count(f"\t{mode})"), 1)
        self.assertEqual(source.count(executor), 4)
        self.assertEqual(source.count(f"if ! {executor}; then"), 1)
        self.assertIn(f'if [ "$recovery_mode" = {mode} ]; then', source)
        self.assertNotIn("resize2fs \"$userdata\" 51124000", source)
        self.assertNotIn("--delete=23", source)
        self.assertIn(
            'if [ "$recovery_mode" = storage-layout-stage1-v1 ] && [ "$timeout" != 900 ]; then',
            source,
        )

    def test_watchdog_disarm_is_exact_and_prewrite(self) -> None:
        source = self.executable_source(WATCHDOG_DISARM)
        for contract in (
            "lease=/run/rog5-recovery-watchdog.lease",
            "armed=/run/rog5-recovery-armed",
            "marker=/run/rog5-recovery-watchdog.disarmed",
            'kill -STOP "$watchdog_pid"',
            'watchdog timer child count changed',
            'kill -KILL "$timer_pid"',
            'kill -KILL "$watchdog_pid"',
            'mv "$lease" "$marker"',
            "trap resume_on_abort EXIT",
        ):
            self.assertIn(contract, source)
        for forbidden in ("blockdev", "resize2fs", "sgdisk", "mkfs", "dd if="):
            self.assertNotIn(forbidden, source)
        self.assertLess(source.index("frozen=1"), source.index('kill -STOP "$watchdog_pid"'))

    def test_builder_seals_mode_executor_and_private_config(self) -> None:
        source = self.executable_source(BUILDER)
        for contract in (
            "storage-layout-stage1-v1",
            "/usr/libexec/rog5-storage-layout-stage1",
            "/etc/rog5/storage-layout-stage1.conf",
            'check_hash "$executor"',
            'check_hash "$watchdog_disarm" "$watchdog_disarm_sha256"',
            'check_hash "$private_config" "$private_config_sha256"',
            'chmod 0400 "$stage/etc/rog5/storage-layout-stage1.conf"',
            "find . -mindepth 1 -print0 | sort -z",
            "cpio --null -o --quiet --format=newc --owner=0:0 --reproducible",
            "gzip -n",
        ):
            self.assertIn(contract, source)


if __name__ == "__main__":
    unittest.main()
