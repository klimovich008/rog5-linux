#!/usr/bin/env python3
"""Fail-closed source contract for the one-shot storage-layout stage 1."""

from __future__ import annotations

from pathlib import Path
import hashlib
import stat
import unittest


REPO = Path(__file__).resolve().parents[2]
EXECUTOR = REPO / "scripts/device/storage-layout-stage1"
BUILDER = REPO / "scripts/device/build-storage-layout-stage1-initramfs.sh"
WATCHDOG_DISARM = REPO / "scripts/device/disarm-recovery-layout-watchdog.sh"
INIT = REPO / "initramfs/recovery-init"
REBOOT_SOURCE = REPO / "tools/reboot_bootloader/rog5-reboot-bootloader.c"
MANIFEST = REPO / "manifests/userdata-ext4-reset-generation86.manifest"
CLAIM_CONSUMER = REPO / "scripts/host/consume-exact-boot-claim.py"
BOOT_POLICY = REPO / "manifests/userdata-ext4-reset-temporary-boot-v1.tsv"


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
        legacy = source[source.index("stage_set S40_FILESYSTEM_CHECK") :]
        self.assertNotIn("mkfs", legacy)
        self.assertNotIn("/rog5/images/arch-local-a.ext4", legacy)
        self.assertNotIn("ROG5_LAYOUT_TEST", source)

    def test_userdata_reset_is_backup_gated_and_never_changes_gpt(self) -> None:
        source = self.executable_source(EXECUTOR)
        start = source.index("run_userdata_ext4_reset() {")
        end = source.index("\n}\n", start) + 2
        reset = source[start:end]
        for contract in (
            'mkfs.ext4 -F -b 4096 -L rog5-linux',
            '-U "$expected_userdata_fs_uuid"',
            '-O ^casefold,^encrypt,^verity,^quota,^project',
            '-E lazy_itable_init=0,lazy_journal_init=0',
            'verify_partition 23 2352680 61865978',
            'partition_absent 24',
            'gpt_changed=0',
            'blockdev --setro "$userdata"',
            '"$reboot_bootloader"',
            "bootloader restart2 returned; remaining in sealed recovery",
            "while :; do sleep 3600; done",
        ):
            self.assertIn(contract, reset)
        for forbidden in (
            "--delete=",
            "--new=",
            "--zap",
            "--load-backup",
            "resize2fs",
            "partprobe",
            "blockdev --rereadpt",
        ):
            self.assertNotIn(forbidden, reset)

        ack = source.index("BACKUP_ACK")
        disarm = source.index('"$watchdog_disarm"')
        dispatch = source.index("run_userdata_ext4_reset", end)
        self.assertLess(ack, disarm)
        self.assertLess(disarm, dispatch)

    def test_userdata_reset_failures_repeat_then_return_to_fastboot(self) -> None:
        source = self.executable_source(EXECUTOR)
        start = source.index("fail() {")
        end = source.index("\n}\n", start) + 2
        failure = source[start:end]
        for contract in (
            'if [ "$operation_mode" = userdata_ext4_reset ]; then',
            'while [ "$repeat" -lt 40 ]; do',
            'sleep 0.5',
            'emit "$failure_record"',
            '"$reboot_bootloader"',
            "bootloader restart2 returned after reset failure",
            "while :; do sleep 3600; done",
        ):
            self.assertIn(contract, failure)

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
            "sbin/mkfs.ext4",
            "rog5-userdata-ext4-reset-v1",
            "usr/libexec/rog5-reboot-bootloader",
            'check_hash "$reboot_bootloader"',
        ):
            self.assertIn(contract, source)

    def test_reboot_helper_is_fixed_restart2_only(self) -> None:
        source = REBOOT_SOURCE.read_text(encoding="utf-8")
        for contract in (
            "LINUX_REBOOT_CMD_RESTART2",
            'static const char command[] = "bootloader"',
            "NR_REBOOT 142UL",
            "Success never returns",
        ):
            self.assertIn(contract, source)

    def test_generation86_publication_is_exact_and_admitted_once(self) -> None:
        payload = MANIFEST.read_bytes()
        self.assertEqual(
            hashlib.sha256(payload).hexdigest(),
            "0b008ecf596f27741087839d5d97a93c3b3b9abb29f7e1091e412310c67a3ef9",
        )
        fields = dict(line.split("=", 1) for line in payload.decode("ascii").splitlines())
        self.assertEqual(fields["profile"], "userdata-ext4-reset-generation86-live-v1")
        self.assertEqual(fields["image_sha256"], "05aac000530d559b5d0c52e7054354ea72ae7434431bdc7fc2797f0ea7cc6f93")
        self.assertEqual(fields["private_config_sha256"], "87845905422201c95e6498c04db4d127b42acfc9b45e316b53d51fc0d388f7cb")
        self.assertEqual(fields["recovery_timeout_seconds"], "900")
        self.assertEqual(fields["target_partition_number"], "23")
        self.assertEqual(fields["gpt_change"], "0")
        self.assertEqual(fields["post_success_action"], "restart2-bootloader-or-remain-in-recovery")
        self.assertEqual(fields["authority"], "none")
        image = REPO / fields["image_path"]
        if image.exists():
            self.assertEqual(image.stat().st_size, int(fields["image_size"]))
            self.assertEqual(
                hashlib.sha256(image.read_bytes()).hexdigest(),
                fields["image_sha256"],
            )

        claim_source = CLAIM_CONSUMER.read_text(encoding="utf-8")
        self.assertIn("userdata-ext4-reset-generation86-live-v1", claim_source)
        self.assertNotIn('"userdata-ext4-reset-generation85-live-v1"', claim_source)
        self.assertNotIn('"storage-layout-stage1-v1-live-v1"', claim_source)
        self.assertEqual(
            BOOT_POLICY.read_text(encoding="utf-8").splitlines(),
            [
                "name\tstatus\tmanifest_sha256\timage_size\timage_sha256\tbasis",
                "userdata-ext4-reset-generation85-live-v1\trevoked\t"
                "910cb4d733217bad2d9b243cfd98dd167033689ecce04a31db1366a7a39dfb1f\t"
                "100663296\taf58eb329bcaf1c3796dfd6c02eb5f794b538f3ca0c552b93ea3c23047c23bd5\t"
                "unbooted and superseded before claim entry because normal post-success "
                "reboot could let stock Android reformat Linux ext4; never boot or flash",
                "userdata-ext4-reset-generation86-live-v1\tallow\t"
                "0b008ecf596f27741087839d5d97a93c3b3b9abb29f7e1091e412310c67a3ef9\t"
                "100663296\t05aac000530d559b5d0c52e7054354ea72ae7434431bdc7fc2797f0ea7cc6f93\t"
                "one exact owner-confirmed RAM-only format of only unchanged userdata "
                "partition 23; fresh host-fsynced GPT backup ACK and external one-use "
                "claim required; exact restart2 bootloader return; GPT and every other "
                "partition immutable; never flash or retry after claim entry",
            ],
        )


if __name__ == "__main__":
    unittest.main()
