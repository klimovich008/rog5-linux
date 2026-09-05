#!/usr/bin/env python3
"""Fail-closed source contract for the one-shot storage-layout stage 1."""

from __future__ import annotations

from pathlib import Path
import hashlib
import importlib.util
import re
import stat
import subprocess
import tempfile
import unittest


REPO = Path(__file__).resolve().parents[2]
EXECUTOR = REPO / "scripts/device/storage-layout-stage1"
BUILDER = REPO / "scripts/device/build-storage-layout-stage1-initramfs.sh"
WATCHDOG_DISARM = REPO / "scripts/device/disarm-recovery-layout-watchdog.sh"
INIT = REPO / "initramfs/recovery-init"
REBOOT_SOURCE = REPO / "tools/reboot_bootloader/rog5-reboot-bootloader.c"
MANIFEST = REPO / "manifests/userdata-ext4-reset-generation99.manifest"
CLAIM_CONSUMER = REPO / "scripts/host/consume-exact-boot-claim.py"
BOOT_POLICY = REPO / "manifests/userdata-ext4-reset-temporary-boot-v1.tsv"
STAGE1_BOOT_POLICY = REPO / "manifests/storage-layout-stage1-temporary-boot-v1.tsv"
CURRENT = REPO / "manifests/storage-layout-stage1-current-20260825.manifest"
CURRENT_CANDIDATE = (
    REPO / "manifests/storage-layout-stage1-current-generation165.manifest"
)
CURRENT_SUCCESSOR = (
    REPO / "manifests/storage-layout-stage1-current-generation166.manifest"
)
LOAD_BACKUP_SUCCESSOR = (
    REPO / "manifests/storage-layout-stage1-load-backup-generation167.manifest"
)
CURRENT_LOAD_BACKUP_SUCCESSOR = (
    REPO / "manifests/storage-layout-stage1-load-backup-generation168.manifest"
)
PREWRITE_OBSERVER = (
    REPO / "manifests/storage-layout-stage1-prewrite-observer-generation169.manifest"
)
CURRENT_PREWRITE_OBSERVER = (
    REPO / "manifests/storage-layout-stage1-prewrite-observer-generation170.manifest"
)
CONFIG_DIAGNOSTIC = (
    REPO / "manifests/storage-layout-stage1-config-diag-generation171.manifest"
)
PRODUCTION_SUCCESSOR = (
    REPO / "manifests/storage-layout-stage1-production-generation172.manifest"
)
FILESYSTEM_DIAGNOSTIC = (
    REPO / "manifests/storage-layout-stage1-production-generation173.manifest"
)
NO_REREAD_SUCCESSOR = (
    REPO / "manifests/storage-layout-stage1-production-generation174.manifest"
)
FIXED_REGION_SUCCESSOR = (
    REPO / "manifests/storage-layout-stage1-production-generation175.manifest"
)


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
            "/etc/rog5/storage-layout-stage1-new-primary.raw",
            "/etc/rog5/storage-layout-stage1-new-secondary.raw",
            'sgdisk --backup="$gpt_backup" "$disk"',
            '"$watchdog_disarm"',
            'blockdev --setrw "$disk"',
            'blockdev --setrw "$userdata"',
            'resize2fs "$userdata" 51124000',
            'dd if="$new_secondary" of="$disk" bs=4096 seek=61865979 count=5 conv=notrunc',
            'dd if="$new_primary" of="$disk" bs=4096 count=6 conv=notrunc',
            'sgdisk --load-backup="$gpt_backup" "$disk"',
            'blockdev --setro "$device"',
        ):
            self.assertIn(contract, source)

        backup = source.index('sgdisk --backup="$gpt_backup" "$disk"')
        ready = source.index("status=HOST_READY")
        backup_begin = source.index("status=BACKUP_BEGIN")
        ack = source.index("BACKUP_ACK")
        disarm = source.index('"$watchdog_disarm"')
        first_setrw = source.rindex('blockdev --setrw "$disk"')
        shrink = source.index('resize2fs "$userdata" 51124000')
        transaction = source.index('dd if="$new_secondary" of="$disk"')
        primary_write = source.index('dd if="$new_primary" of="$disk"')
        self.assertLess(backup, ack)
        self.assertLess(ready, backup_begin)
        self.assertLess(backup_begin, ack)
        self.assertLess(ack, disarm)
        self.assertLess(disarm, first_setrw)
        self.assertLess(first_setrw, shrink)
        self.assertLess(shrink, transaction)
        self.assertLess(transaction, primary_write)
        prewrite = source[source.index("stage_set S10_TOPOLOGY") : source.index("stage_set S30_FRESH_BACKUP")]
        self.assertIn("verify_userdata_filesystem 51124000", prewrite)
        self.assertNotIn("verify_userdata_filesystem 59513299", prewrite)
        legacy = source[source.index("stage_set S40_FILESYSTEM_CHECK") :]
        self.assertNotIn("mkfs", legacy)
        self.assertNotIn("/rog5/images/arch-local-a.ext4", legacy)
        self.assertNotIn("ROG5_LAYOUT_TEST", source)
        transaction_source = source[source.index("stage_set S60_GPT_TRANSACTION") :]
        for forbidden in (
            "--delete=",
            "--new=",
            "--set-alignment=",
            "--partition-guid=",
            "--attributes=",
        ):
            self.assertNotIn(forbidden, transaction_source)

    def test_config_failures_are_finite_specific_and_prewrite(self) -> None:
        source = self.executable_source(EXECUTOR)
        start = source.index("check_config() {")
        end = source.index("\n}\n", start) + 2
        config_check = source[start:end]
        reasons = re.findall(r"config_reason=([a-z0-9_]+)", config_check)
        self.assertGreaterEqual(len(reasons), 30)
        self.assertEqual(len(reasons), len(set(reasons)))
        self.assertTrue(all(reason.startswith("config_") for reason in reasons))
        dispatch = source.index('check_config || fail "$config_reason"')
        topology = source.index("stage_set S10_TOPOLOGY")
        self.assertLess(dispatch, topology)

    def test_filesystem_failures_are_finite_and_stage_correlated(self) -> None:
        source = self.executable_source(EXECUTOR)
        start = source.index("verify_userdata_filesystem() {")
        end = source.index("\n}\n", start) + 2
        verifier = source[start:end]
        reasons = re.findall(r"filesystem_reason=([a-z0-9_]+)", verifier)
        self.assertEqual(
            reasons,
            [
                "filesystem_dumpe2fs_failed",
                "filesystem_block_count_changed",
                "filesystem_block_size_changed",
                "filesystem_state_not_clean",
                "filesystem_uuid_changed",
                "filesystem_recovery_feature_present",
            ],
        )
        self.assertEqual(
            source.count(
                'verify_userdata_filesystem 51124000 || fail "$filesystem_reason"'
            ),
            4,
        )

    def test_post_gpt_checks_keep_the_proven_kernel_mapping_until_reboot(self) -> None:
        source = self.executable_source(EXECUTOR)
        transaction = source[source.index("stage_set S60_GPT_TRANSACTION") :]
        for forbidden in ("blockdev --rereadpt", "partprobe", "mdev -s"):
            self.assertNotIn(forbidden, transaction)
        self.assertIn("verify_old_userdata_mapping || fail old_userdata_mapping_changed", transaction)
        self.assertIn('e2fsck -fn "$userdata"', transaction)
        self.assertNotIn('e2fsck -f -p "$userdata"', transaction)

        restore_start = source.index("restore_original_gpt() {")
        restore_end = source.index("\n}\n", restore_start) + 2
        restore = source[restore_start:restore_end]
        for forbidden in ("blockdev --rereadpt", "partprobe", "mdev -s"):
            self.assertNotIn(forbidden, restore)
        self.assertIn("verify_gpt_unchanged || return 1", restore)

        old_first = new_first = 2352680
        old_last = 61865978
        new_last = 53477375
        filesystem_blocks = 51124000
        old_blocks = old_last - old_first + 1
        new_blocks = new_last - new_first + 1
        self.assertEqual(new_first, old_first)
        self.assertLessEqual(filesystem_blocks, new_blocks)
        self.assertLessEqual(new_blocks, old_blocks)
        self.assertEqual(new_blocks - filesystem_blocks, 696)

        start = source.index("verify_old_userdata_mapping() {")
        end = source.index("\n}\n", start) + 2
        verifier = source[start:end]
        for identity in (
            '"$sys_userdata/partition")" = 23',
            '"$partition_name" = userdata',
            '"$sys_userdata/dev")" = "$userdata_dev"',
            '"$sys_userdata/start")" = 18821440',
            '"$sys_userdata/size")" = 476106392',
            '"$(blockdev --getsize64 "$userdata")" = 243766472704',
            '"$(blockdev --getss "$userdata")" = 4096',
        ):
            self.assertIn(identity, verifier)

    def test_current_checkpoint_is_offline_and_current_bound(self) -> None:
        fields = dict(
            line.split("=", 1)
            for line in CURRENT.read_text(encoding="ascii").splitlines()
        )
        self.assertEqual(fields["status"], "offline-hold")
        self.assertEqual(fields["destructive_authority"], "none")
        self.assertEqual(fields["phone_boot"], "forbidden")
        self.assertEqual(
            fields["userdata_fs_uuid"],
            "0892bacf-3e02-41b0-84a4-5f05c2df7ce5",
        )
        self.assertEqual(
            fields["source_image_sha256"],
            "533973be0e0ca76c5db8645fdef9aeb64d20b8c9c98b70124a2561700f119153",
        )
        self.assertEqual(fields["rescue_slot"], "a")
        self.assertEqual(fields["accepted_generation"], "163")

    def test_current_candidate_is_exact_and_has_no_authority(self) -> None:
        fields = dict(
            line.split("=", 1)
            for line in CURRENT_CANDIDATE.read_text(encoding="ascii").splitlines()
        )
        self.assertEqual(
            fields["profile"],
            "storage-layout-stage1-current-generation165-live-v1",
        )
        self.assertEqual(fields["status"], "awaiting-final-confirmation")
        self.assertEqual(fields["destructive_authority"], "none")
        self.assertEqual(fields["phone_boot"], "forbidden")
        self.assertEqual(fields["rescue_slot"], "a")
        self.assertEqual(fields["preflight_generation"], "164")
        self.assertEqual(fields["preflight_ext4_minimum_blocks"], "1219496")
        self.assertEqual(
            fields["collector_execution_record_sha256"],
            "080aea76796bd3f0fad230796086adb14d45ca55557d6a40af2aa77b2a00b955",
        )
        self.assertEqual(
            fields["image_sha256"],
            "1a00e9061c027c804458732cfc93ba7175ee6821d821f9d86ffa079383fd5fc2",
        )
        self.assertEqual(
            fields["initramfs_sha256"],
            "b9851f3e1d901fb32f2ea32dab8042a8bdc109dd30b1d1e06a10664befae294f",
        )
        image = REPO / fields["image_path"]
        if not image.exists():
            return
        raw = image.with_name("stable-recovery-a.raw.img")
        twin = image.with_name("stable-recovery-b.avb.img")
        self.assertEqual(image.stat().st_size, int(fields["image_size"]))
        self.assertEqual(hashlib.sha256(image.read_bytes()).hexdigest(), fields["image_sha256"])
        self.assertEqual(hashlib.sha256(raw.read_bytes()).hexdigest(), fields["raw_image_sha256"])
        self.assertEqual(image.read_bytes(), twin.read_bytes())
        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run(
                [
                    "python3",
                    str(REPO / "artifacts/android-boot-tools-v1/unpack_bootimg.py"),
                    "--boot_img",
                    str(raw),
                    "--out",
                    directory,
                    "--format=mkbootimg",
                    "--null",
                ],
                check=True,
                capture_output=True,
            )
            unpacked = Path(directory)
            self.assertEqual(
                hashlib.sha256((unpacked / "kernel").read_bytes()).hexdigest(),
                fields["kernel_sha256"],
            )
            self.assertEqual(
                hashlib.sha256((unpacked / "ramdisk").read_bytes()).hexdigest(),
                fields["initramfs_sha256"],
            )
        arguments = result.stdout.split(b"\0")
        cmdline = arguments[arguments.index(b"--cmdline") + 1].decode("ascii")
        self.assertEqual(cmdline.split().count("rog5.recovery_timeout=900"), 1)
        self.assertNotIn("rog5.recovery_timeout=300", cmdline.split())

    def test_current_stage1_admission_and_claim_are_exact(self) -> None:
        manifest_sha256 = hashlib.sha256(CURRENT_CANDIDATE.read_bytes()).hexdigest()
        self.assertEqual(
            manifest_sha256,
            "7e3bb797375f5b3a38a4bf76bb57f2a51e344b36a9613e0f25cf2e6c97862215",
        )
        lines = STAGE1_BOOT_POLICY.read_text(encoding="ascii").splitlines()
        self.assertEqual(
            lines[0],
            "profile\tstatus\tcandidate_manifest_sha256\timage_path\t"
            "image_size\timage_sha256\tbasis",
        )
        self.assertEqual(len(lines), 12)
        rows = {row[0]: row for row in (line.split("\t") for line in lines[1:])}
        fields = rows["storage-layout-stage1-current-generation165-live-v1"]
        self.assertEqual(
            fields[:6],
            [
                "storage-layout-stage1-current-generation165-live-v1",
                "revoked",
                manifest_sha256,
                "build/storage-layout-stage1-current-generation165-20260825-r1/"
                "repack/stable-recovery-a.avb.img",
                "100663296",
                "1a00e9061c027c804458732cfc93ba7175ee6821d821f9d86ffa079383fd5fc2",
            ],
        )
        self.assertIn("stopped before collector", fields[6])
        self.assertIn("never retry or flash", fields[6])
        expected_claim = (
            "format=rog5-temporary-boot-consumption-v1\n"
            "recovery_profile=storage-layout-stage1-current-generation165-live-v1\n"
            "candidate=storage-layout-stage1-current\n"
            f"manifest_sha256={manifest_sha256}\n"
            "state=BOOT_CLAIMED\n"
        ).encode("ascii")
        spec = importlib.util.spec_from_file_location("stage1_claims", CLAIM_CONSUMER)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader if spec else None)
        module = importlib.util.module_from_spec(spec)
        assert spec is not None and spec.loader is not None
        spec.loader.exec_module(module)
        self.assertEqual(module.expected_record(fields[0]), expected_claim)

    def test_generation166_successor_is_exact_full_path_and_admitted_once(self) -> None:
        fields = dict(
            line.split("=", 1)
            for line in CURRENT_SUCCESSOR.read_text(encoding="ascii").splitlines()
        )
        self.assertEqual(
            hashlib.sha256(CURRENT_SUCCESSOR.read_bytes()).hexdigest(),
            "cc348a62688135492e36e02604b7a197b081cc671e0c65f48969015414963d88",
        )
        self.assertEqual(fields["predecessor_generation"], "165")
        self.assertEqual(
            fields["predecessor_outcome"],
            "consumed-pre-ack-no-write-short-usb-path",
        )
        self.assertEqual(
            fields["collector_usb_location"],
            "pci0000:00/0000:00:08.1/0000:04:00.3/usb1/1-1/1-1.2",
        )
        self.assertEqual(
            fields["raw_image_sha256"],
            "780dcfc2da571e76375f3e60eddf90e2b1a6881c5d13b5076aeec8a167ade98a",
        )
        self.assertEqual(
            fields["collector_execution_record_sha256"],
            "25b57fda9061839167c229cdf4a92dccf4b90f21b2ce7218695b698541307901",
        )
        rows = {
            row[0]: row
            for row in (
                line.split("\t")
                for line in STAGE1_BOOT_POLICY.read_text(encoding="ascii").splitlines()[1:]
            )
        }
        admitted = rows[fields["profile"]]
        self.assertEqual(admitted[1], "revoked")
        self.assertEqual(admitted[2], hashlib.sha256(CURRENT_SUCCESSOR.read_bytes()).hexdigest())
        self.assertEqual(admitted[5], fields["image_sha256"])
        self.assertIn("ext4 shrank to 51124000 blocks", admitted[6])
        self.assertIn("exact fresh GPT restoration succeeded", admitted[6])

    def test_generation167_seals_one_exact_gpt_load_and_admission(self) -> None:
        fields = dict(
            line.split("=", 1)
            for line in LOAD_BACKUP_SUCCESSOR.read_text(encoding="ascii").splitlines()
        )
        manifest_sha256 = hashlib.sha256(LOAD_BACKUP_SUCCESSOR.read_bytes()).hexdigest()
        self.assertEqual(
            manifest_sha256,
            "f9df41fb58858b9eeed9528650f1461d0a71bd2bb0bd8dd926f740ad65954ccf",
        )
        self.assertEqual(fields["gpt_transaction"], "one-sealed-sgdisk-load-backup")
        self.assertEqual(fields["current_filesystem_blocks"], "51124000")
        self.assertEqual(
            fields["sealed_new_gpt_sha256"],
            "6774a2e5aa7defcb8197910a2b56ddc61be44f2681038c400f9a5ee0eb057a0e",
        )
        self.assertEqual(
            fields["generation166_backup_set_sha256"],
            "1a6295725cb63ab27f90022e5061be6552eec7d6a4297cc4f5ff088543948679",
        )
        rows = {
            row[0]: row
            for row in (
                line.split("\t")
                for line in STAGE1_BOOT_POLICY.read_text(encoding="ascii").splitlines()[1:]
            )
        }
        admitted = rows[fields["profile"]]
        self.assertEqual(admitted[1], "revoked")
        self.assertEqual(admitted[2], manifest_sha256)
        self.assertEqual(admitted[5], fields["image_sha256"])
        self.assertIn("stale hardcoded 59513299-block filesystem", admitted[6])
        self.assertIn("before S30", admitted[6])

    def test_generation168_binds_current_filesystem_and_one_admission(self) -> None:
        fields = dict(
            line.split("=", 1)
            for line in CURRENT_LOAD_BACKUP_SUCCESSOR.read_text(encoding="ascii").splitlines()
        )
        manifest_sha256 = hashlib.sha256(CURRENT_LOAD_BACKUP_SUCCESSOR.read_bytes()).hexdigest()
        self.assertEqual(
            manifest_sha256,
            "902890bd36b067fd7a262fd71334f418766777b3c8beb47711776b251878c9ea",
        )
        self.assertEqual(fields["prewrite_expected_filesystem_blocks"], "51124000")
        self.assertEqual(fields["predecessor_generation"], "167")
        self.assertEqual(
            fields["predecessor_outcome"],
            "consumed-pre-s30-no-write-stale-filesystem-block-count",
        )
        rows = {
            row[0]: row
            for row in (
                line.split("\t")
                for line in STAGE1_BOOT_POLICY.read_text(encoding="ascii").splitlines()[1:]
            )
        }
        self.assertEqual(sum(row[1] == "allow" for row in rows.values()), 0)
        admitted = rows[fields["profile"]]
        self.assertEqual(admitted[1], "revoked")
        self.assertEqual(admitted[2], manifest_sha256)
        self.assertEqual(admitted[5], fields["image_sha256"])
        self.assertIn("no terminal stage was captured", admitted[6])

    def test_generation169_is_byte_exact_receive_only_discriminator(self) -> None:
        fields = dict(
            line.split("=", 1)
            for line in PREWRITE_OBSERVER.read_text(encoding="ascii").splitlines()
        )
        digest = hashlib.sha256(PREWRITE_OBSERVER.read_bytes()).hexdigest()
        self.assertEqual(
            digest,
            "c129243271b42c6efb38e3248d5a2ba58b11346720f8c188250efa5f8482e207",
        )
        self.assertEqual(fields["raw_identity"], "byte-identical-to-consumed-generation168")
        self.assertEqual(fields["observer_mode"], "receive-only-start-before-fastboot-boot")
        self.assertEqual(fields["readiness"], "forbidden")
        self.assertEqual(fields["backup_ack"], "forbidden")
        rows = {
            row[0]: row
            for row in (
                line.split("\t")
                for line in STAGE1_BOOT_POLICY.read_text(encoding="ascii").splitlines()[1:]
            )
        }
        self.assertEqual(sum(row[1] == "allow" for row in rows.values()), 0)
        admitted = rows[fields["profile"]]
        self.assertEqual(admitted[1], "revoked")
        self.assertEqual(admitted[2], digest)
        self.assertEqual(admitted[5], fields["image_sha256"])
        self.assertIn("expected target departure", admitted[6])
        self.assertIn("before durable evidence publication", admitted[6])

    def test_generation170_retains_receive_only_evidence_across_departure(self) -> None:
        fields = dict(
            line.split("=", 1)
            for line in CURRENT_PREWRITE_OBSERVER.read_text(encoding="ascii").splitlines()
        )
        digest = hashlib.sha256(CURRENT_PREWRITE_OBSERVER.read_bytes()).hexdigest()
        self.assertEqual(
            digest,
            "74aaa7c64929f33d1758853c0a191d6e9104f97f7f81e3d13c32095c319c9553",
        )
        self.assertEqual(fields["raw_identity"], "byte-identical-to-consumed-generations168-169")
        self.assertEqual(
            fields["observer_publication"],
            "validated-evidence-before-departure-classification",
        )
        rows = {
            row[0]: row
            for row in (
                line.split("\t")
                for line in STAGE1_BOOT_POLICY.read_text(encoding="ascii").splitlines()[1:]
            )
        }
        self.assertEqual(sum(row[1] == "allow" for row in rows.values()), 0)
        admitted = rows[fields["profile"]]
        self.assertEqual(admitted[1], "revoked")
        self.assertEqual(admitted[2], digest)
        self.assertIn("exact S00_CONFIG invalid_private_config", admitted[6])
        self.assertIn("observer sent zero bytes", admitted[6])

    def test_generation172_binds_s30_proof_gpt_load_and_fastboot_fallback(self) -> None:
        fields = dict(
            line.split("=", 1)
            for line in PRODUCTION_SUCCESSOR.read_text(encoding="ascii").splitlines()
        )
        digest = hashlib.sha256(PRODUCTION_SUCCESSOR.read_bytes()).hexdigest()
        self.assertEqual(
            digest,
            "8df8f0152e66180f368c55f31e9b788ea3d120ce87117d3386ef2cd7f46fead0",
        )
        self.assertEqual(fields["generation171_prewrite_outcome"], "exact-s00-s10-s20-s30-no-host-bytes")
        self.assertEqual(fields["gpt_transaction"], "one-sealed-sgdisk-load-backup")
        self.assertEqual(fields["fallback"], "restart2-bootloader-before-generic-reset")
        rows = {
            row[0]: row
            for row in (
                line.split("\t")
                for line in STAGE1_BOOT_POLICY.read_text(encoding="ascii").splitlines()[1:]
            )
        }
        self.assertEqual(sum(row[1] == "allow" for row in rows.values()), 0)
        admitted = rows[fields["profile"]]
        self.assertEqual(admitted[1], "revoked")
        self.assertEqual(admitted[2], digest)
        self.assertIn("sealed GPT load and new geometry", admitted[6])
        self.assertIn("restart2 returned exact fastboot automatically", admitted[6])

    def test_generation173_binds_only_the_finite_filesystem_discriminator(self) -> None:
        fields = dict(
            line.split("=", 1)
            for line in FILESYSTEM_DIAGNOSTIC.read_text(encoding="ascii").splitlines()
        )
        digest = hashlib.sha256(FILESYSTEM_DIAGNOSTIC.read_bytes()).hexdigest()
        self.assertEqual(
            digest,
            "09895a561a5086542463ba3fce4ecd4daf632fd8bb311e425ac385060cea3754",
        )
        self.assertEqual(fields["generation172_result"], "sealed-gpt-and-geometry-pass-generic-s70-filesystem-failure")
        self.assertEqual(fields["filesystem_failure_contract"], "finite-exact-post-gpt-reason")
        self.assertEqual(fields["gpt_transaction"], "one-sealed-sgdisk-load-backup")
        rows = {
            row[0]: row
            for row in (
                line.split("\t")
                for line in STAGE1_BOOT_POLICY.read_text(encoding="ascii").splitlines()[1:]
            )
        }
        self.assertEqual(sum(row[1] == "allow" for row in rows.values()), 0)
        admitted = rows[fields["profile"]]
        self.assertEqual(admitted[1], "revoked")
        self.assertEqual(admitted[2], digest)
        self.assertIn("filesystem_dumpe2fs_failed", admitted[6])
        self.assertIn("restart2 returned exact fastboot", admitted[6])

    def test_generation174_keeps_the_proven_mapping_and_requires_next_boot_gate(self) -> None:
        fields = dict(
            line.split("=", 1)
            for line in NO_REREAD_SUCCESSOR.read_text(encoding="ascii").splitlines()
        )
        digest = hashlib.sha256(NO_REREAD_SUCCESSOR.read_bytes()).hexdigest()
        self.assertEqual(digest, "e259fda8dcba14b5cfd1e53adc1dfa2e1782b548f6c7980fde994d9d1412d780")
        self.assertEqual(fields["failure_class"], "R3")
        self.assertEqual(fields["post_gpt_kernel_mapping"], "retain-exact-proven-old-p23-until-reboot")
        self.assertEqual(fields["post_gpt_filesystem_check"], "read-only-dumpe2fs-and-e2fsck-fn")
        self.assertEqual(fields["next_boot_gate"], "exact-read-only-new-p23-p24-enumeration-before-stage2")
        rows = {
            row[0]: row
            for row in (
                line.split("\t")
                for line in STAGE1_BOOT_POLICY.read_text(encoding="ascii").splitlines()[1:]
            )
        }
        self.assertEqual(sum(row[1] == "allow" for row in rows.values()), 0)
        admitted = rows[fields["profile"]]
        self.assertEqual(admitted[1], "revoked")
        self.assertEqual(admitted[2], digest)
        self.assertIn("old_userdata_mapping_changed", admitted[6])
        self.assertIn("DiskSync issues BLKRRPART", admitted[6])

    def test_generation175_binds_fixed_regions_and_exact_busybox_write_contract(self) -> None:
        fields = dict(
            line.split("=", 1)
            for line in FIXED_REGION_SUCCESSOR.read_text(encoding="ascii").splitlines()
        )
        digest = hashlib.sha256(FIXED_REGION_SUCCESSOR.read_bytes()).hexdigest()
        self.assertEqual(digest, "7dc95a58248ba2613f09da8a032449e8a8e2f0b635aee66445fd518f4494ae4f")
        self.assertEqual(fields["gpt_transaction"], "sealed-secondary-then-primary-fixed-region-writes-no-live-partitioner")
        self.assertEqual(fields["target_dd_contract"], "exact-busybox-conv-notrunc")
        self.assertEqual(fields["post_write_readback"], "exact-primary-and-secondary-regions")
        rows = {
            row[0]: row
            for row in (
                line.split("\t")
                for line in STAGE1_BOOT_POLICY.read_text(encoding="ascii").splitlines()[1:]
            )
        }
        self.assertEqual(sum(row[1] == "allow" for row in rows.values()), 0)
        admitted = rows[fields["profile"]]
        self.assertEqual(admitted[1], "revoked")
        self.assertEqual(admitted[2], digest)
        self.assertIn("Stage 1 complete", admitted[6])
        self.assertIn("automatic exact fastboot", admitted[6])

    def test_generation171_is_receive_only_exact_config_discriminator(self) -> None:
        fields = dict(
            line.split("=", 1)
            for line in CONFIG_DIAGNOSTIC.read_text(encoding="ascii").splitlines()
        )
        digest = hashlib.sha256(CONFIG_DIAGNOSTIC.read_bytes()).hexdigest()
        self.assertEqual(
            digest,
            "acee0a4e68fdc3e5e0dd60618719bb25e6a28f2afff602d1f329fead3a6d0b64",
        )
        self.assertEqual(fields["config_failure_contract"], "finite-nonsecret-exact-predicate")
        self.assertEqual(fields["readiness"], "forbidden")
        self.assertEqual(fields["backup_ack"], "forbidden")
        rows = {
            row[0]: row
            for row in (
                line.split("\t")
                for line in STAGE1_BOOT_POLICY.read_text(encoding="ascii").splitlines()[1:]
            )
        }
        self.assertEqual(sum(row[1] == "allow" for row in rows.values()), 0)
        admitted = rows[fields["profile"]]
        self.assertEqual(admitted[1], "revoked")
        self.assertEqual(admitted[2], digest)
        self.assertIn("exact ordered S00, S10, S20 and S30", admitted[6])
        self.assertIn("observer sent zero bytes", admitted[6])

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

    def test_userdata_reset_failures_emit_once_then_return_to_fastboot(self) -> None:
        source = self.executable_source(EXECUTOR)
        start = source.index("fail() {")
        end = source.index("\n}\n", start) + 2
        failure = source[start:end]
        for contract in (
            'if [ "$operation_mode" = userdata_ext4_reset ]; then',
            '"$reboot_bootloader"',
            "bootloader restart2 returned after reset failure",
            "while :; do sleep 3600; done",
        ):
            self.assertIn(contract, failure)
        self.assertEqual(failure.count('emit "$failure_record"'), 1)
        self.assertNotIn('while [ "$repeat"', failure)

    def test_reset_precondition_rejects_only_existing_ext4(self) -> None:
        source = self.executable_source(EXECUTOR)
        start = source.index("read_userdata_ext4_magic() {")
        end = source.index("\n}\n", start) + 2
        precondition = source[start:end]
        self.assertIn('skip=1080 count=2', precondition)
        self.assertIn("od -An -tx1 -v", precondition)
        self.assertNotIn("blkid", precondition)
        self.assertNotIn("f2fs", precondition)
        self.assertIn('fail userdata_already_ext4', source)

    def test_host_ready_is_exact_bounded_and_diagnostic(self) -> None:
        source = self.executable_source(EXECUTOR)
        start = source.index("host_ready_attempt=0")
        end = source.index('emit "status=BACKUP_BEGIN', start)
        rendezvous = source[start:end]
        for contract in (
            'while [ "$host_ready_attempt" -lt 4 ]; do',
            'read -r -t 30 host_ready <&3',
            'host_ready_reason=host_ready_empty',
            'host_ready_reason=host_ready_trailing_cr',
            'host_ready_reason=host_ready_leading_cr',
            'host_ready_reason=host_ready_trailing_data',
            'host_ready_reason=host_ready_leading_data',
            'host_ready_reason=host_ready_short',
            'host_ready_reason=host_ready_same_length',
            'host_ready_reason=host_ready_long',
            '[ "$host_ready_ok" = 1 ] || fail "$host_ready_reason"',
        ):
            self.assertIn(contract, rendezvous)
        for normalization in ("tr -d", "sed", "xargs", "eval"):
            self.assertNotIn(normalization, rendezvous)

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
            'kill -KILL "$watchdog_pid"',
            'mv "$lease" "$marker"',
            "trap resume_on_abort EXIT",
        ):
            self.assertIn(contract, source)
        for forbidden in ("blockdev", "resize2fs", "sgdisk", "mkfs", "dd if="):
            self.assertNotIn(forbidden, source)
        self.assertNotIn('/task/$watchdog_pid/children', source)
        self.assertLess(source.index("frozen=1"), source.index('kill -STOP "$watchdog_pid"'))
        messages = re.findall(r"fail '([^']+)'", source)
        reasons = ["watchdog_" + re.sub(r"[ -]", "_", value.lower()) for value in messages]
        self.assertGreater(len(reasons), 20)
        self.assertEqual(len(reasons), len(set(reasons)))
        self.assertTrue(all(re.fullmatch(r"watchdog_[a-z0-9_]+", value) for value in reasons))

        init = self.executable_source(INIT)
        setup_start = init.index("touch /run/rog5-recovery-armed") - 200
        setup_end = init.index("if ! snapshot_postmortem")
        setup = init[setup_start:setup_end]
        self.assertLess(
            setup.index("umask 077"),
            setup.index("touch /run/rog5-recovery-armed"),
        )

        executor = self.executable_source(EXECUTOR)
        disarm = executor[executor.index("stage_set S32_WATCHDOG_DISARM") :]
        self.assertIn("watchdog_reason=", disarm)
        self.assertIn('fail "$watchdog_reason"', disarm)
        self.assertNotIn("fail rollback_watchdog_disarm_failed", disarm)

    def test_builder_seals_mode_executor_and_private_config(self) -> None:
        source = self.executable_source(BUILDER)
        executor_sha256 = hashlib.sha256(EXECUTOR.read_bytes()).hexdigest()
        self.assertIn(f"executor_sha256={executor_sha256}", source)
        for contract in (
            "storage-layout-stage1-v1",
            "/usr/libexec/rog5-storage-layout-stage1",
            "/etc/rog5/storage-layout-stage1.conf",
            "/etc/rog5/storage-layout-stage1-new-primary.raw",
            "/etc/rog5/storage-layout-stage1-new-secondary.raw",
            'check_hash "$executor"',
            'check_hash "$watchdog_disarm" "$watchdog_disarm_sha256"',
            'check_hash "$private_config" "$private_config_sha256"',
            'check_hash "$new_primary" "$new_primary_sha256"',
            'check_hash "$new_secondary" "$new_secondary_sha256"',
            'chmod 0400 "$stage/etc/rog5/storage-layout-stage1.conf"',
            'chmod 0400 "$stage/etc/rog5/storage-layout-stage1-new-primary.raw"',
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

    def test_every_storage_layout_rollback_prefers_restart2_bootloader(self) -> None:
        source = self.executable_source(INIT)
        start = source.index("force_rollback() {")
        end = source.index("\n}\n", start) + 2
        rollback = source[start:end]
        self.assertIn("storage-layout-stage1-v1|storage-layout-stage2-v1", rollback)
        self.assertIn("/usr/libexec/rog5-reboot-bootloader", rollback)
        self.assertLess(
            rollback.index("/usr/libexec/rog5-reboot-bootloader"),
            rollback.index("reboot -f"),
        )
        self.assertIn("echo b >/proc/sysrq-trigger", rollback)

    def test_generation99_publication_is_exact_and_admitted_once(self) -> None:
        payload = MANIFEST.read_bytes()
        self.assertEqual(
            hashlib.sha256(payload).hexdigest(),
            "121adc0df0d2a395685983c573fe37ca25da8a31497c2cf9843e9372ab40a3c5",
        )
        fields = dict(line.split("=", 1) for line in payload.decode("ascii").splitlines())
        self.assertEqual(fields["profile"], "userdata-ext4-reset-generation99-live-v1")
        self.assertEqual(fields["image_sha256"], "51a51d8b985f321da26d7796f22a0c3af0e2ca0c7338489e5615a81cf1a145e2")
        self.assertEqual(fields["private_config_sha256"], "87845905422201c95e6498c04db4d127b42acfc9b45e316b53d51fc0d388f7cb")
        self.assertEqual(fields["recovery_timeout_seconds"], "900")
        self.assertEqual(fields["deployed_recovery_timeout_seconds"], "900")
        self.assertEqual(fields["watchdog_armed_marker_mode"], "0600")
        self.assertEqual(fields["watchdog_armed_marker_umask"], "077")
        self.assertEqual(fields["watchdog_proc_children_dependency"], "none")
        self.assertEqual(
            fields["watchdog_failure_reason"],
            "sealed-final-fail-line-lowercase-machine-token",
        )
        self.assertEqual(fields["watchdog_failure_reason_max_bytes"], "127")
        self.assertEqual(fields["target_partition_number"], "23")
        self.assertEqual(fields["gpt_change"], "0")
        self.assertEqual(fields["post_success_action"], "restart2-bootloader-or-remain-in-recovery")
        self.assertEqual(fields["failure_evidence_repetitions"], "1")
        self.assertEqual(fields["failure_evidence_interval_ms"], "0")
        self.assertEqual(
            fields["watchdog_exit_contract"],
            "absent-or-exact-same-parent-starttime-zombie",
        )
        self.assertEqual(
            fields["failure_transport_contract"],
            "one-terminal-record-before-restart2",
        )
        self.assertEqual(fields["post_failure_action"], "restart2-bootloader-or-remain-in-recovery")
        self.assertEqual(fields["userdata_precondition"], "readable-and-not-ext4")
        self.assertEqual(fields["backup_stream_rendezvous"], "exact-operation-bound-host-ready")
        self.assertEqual(fields["host_ready_order"], "target-s30-then-host-ready")
        self.assertEqual(fields["host_ready_separator"], "one-empty-record")
        self.assertEqual(fields["host_ready_records"], "4")
        self.assertEqual(fields["host_ready_record_timeout_seconds"], "30")
        self.assertEqual(fields["host_ready_diagnostics"], "finite-nonsecret-no-normalization")
        self.assertEqual(fields["authority"], "none")
        image = REPO / fields["image_path"]
        if image.exists():
            self.assertEqual(image.stat().st_size, int(fields["image_size"]))
            self.assertEqual(
                hashlib.sha256(image.read_bytes()).hexdigest(),
                fields["image_sha256"],
            )
            with tempfile.TemporaryDirectory() as directory:
                result = subprocess.run(
                    [
                        "python3",
                        str(REPO / "artifacts/android-boot-tools-v1/unpack_bootimg.py"),
                        "--boot_img",
                        str(image),
                        "--out",
                        directory,
                        "--format=mkbootimg",
                        "--null",
                    ],
                    check=True,
                    capture_output=True,
                )
            arguments = result.stdout.split(b"\0")
            cmdline = arguments[arguments.index(b"--cmdline") + 1].decode("ascii")
            self.assertEqual(cmdline.split().count("rog5.recovery_timeout=900"), 1)
            self.assertNotIn("rog5.recovery_timeout=300", cmdline.split())

        claim_source = CLAIM_CONSUMER.read_text(encoding="utf-8")
        self.assertIn("userdata-ext4-reset-generation99-live-v1", claim_source)
        self.assertNotIn('"userdata-ext4-reset-generation98-live-v1"', claim_source)
        self.assertNotIn('"storage-layout-stage1-v1-live-v1"', claim_source)
        lines = BOOT_POLICY.read_text(encoding="utf-8").splitlines()
        self.assertEqual(
            lines[0],
            "name\tstatus\tmanifest_sha256\timage_size\timage_sha256\tbasis",
        )
        rows = {fields[0]: fields[1:] for fields in (line.split("\t") for line in lines[1:])}
        self.assertEqual(
            {name: row[0] for name, row in rows.items()},
            {
                "userdata-ext4-reset-generation85-live-v1": "revoked",
                "userdata-ext4-reset-generation86-live-v1": "revoked",
                "userdata-ext4-reset-generation87-live-v1": "revoked",
                "userdata-ext4-reset-generation88-live-v1": "revoked",
                "userdata-ext4-reset-generation89-live-v1": "revoked",
                "userdata-ext4-reset-generation90-live-v1": "revoked",
                "userdata-ext4-reset-generation91-live-v1": "revoked",
                "userdata-ext4-reset-generation92-live-v1": "revoked",
                "userdata-ext4-reset-generation93-live-v1": "revoked",
                "userdata-ext4-reset-generation94-live-v1": "revoked",
                "userdata-ext4-reset-generation95-live-v1": "revoked",
                "userdata-ext4-reset-generation96-live-v1": "revoked",
                "userdata-ext4-reset-generation97-live-v1": "revoked",
                "userdata-ext4-reset-generation98-live-v1": "revoked",
                "userdata-ext4-reset-generation99-live-v1": "revoked",
            },
        )
        self.assertEqual(rows["userdata-ext4-reset-generation99-live-v1"][1:4], [
            "121adc0df0d2a395685983c573fe37ca25da8a31497c2cf9843e9372ab40a3c5",
            "100663296",
            "51a51d8b985f321da26d7796f22a0c3af0e2ca0c7338489e5615a81cf1a145e2",
        ])


if __name__ == "__main__":
    unittest.main()
