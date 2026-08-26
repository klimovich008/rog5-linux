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
CURRENT = REPO / "manifests/storage-layout-stage2-current-20260825.manifest"
PREFLIGHT = REPO / "manifests/storage-layout-stage2-preflight-generation176.manifest"
PREFLIGHT_SUCCESSOR = REPO / "manifests/storage-layout-stage2-preflight-generation177.manifest"
PREFLIGHT_TOPOLOGY = REPO / "manifests/storage-layout-stage2-preflight-generation178.manifest"
PREFLIGHT_POST_USB = REPO / "manifests/storage-layout-stage2-preflight-generation179.manifest"
PREFLIGHT_USB_FIRST = REPO / "manifests/storage-layout-stage2-preflight-generation180.manifest"
PREFLIGHT_EXACT_FIELDS = REPO / "manifests/storage-layout-stage2-preflight-generation181.manifest"
PREFLIGHT_STABLE_IMAGE = REPO / "manifests/storage-layout-stage2-preflight-generation182.manifest"
PREFLIGHT_CORRECTED = REPO / "manifests/storage-layout-stage2-preflight-generation183.manifest"
PREFLIGHT_DURABLE = REPO / "manifests/storage-layout-stage2-preflight-generation184.manifest"
PREFLIGHT_INITIALIZED = REPO / "manifests/storage-layout-stage2-preflight-generation185.manifest"
BOOT_POLICY = REPO / "manifests/storage-layout-stage2-temporary-boot-v1.tsv"


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

    def test_builder_pins_the_current_executor(self) -> None:
        builder = self.executable_source(BUILDER)
        digest = hashlib.sha256(EXECUTOR.read_bytes()).hexdigest()
        self.assertIn(f"executor_sha256={digest}", builder)

    def test_current_checkpoint_is_offline_and_current_bound(self) -> None:
        fields = dict(
            line.split("=", 1)
            for line in CURRENT.read_text(encoding="ascii").splitlines()
        )
        self.assertEqual(fields["status"], "offline-hold")
        self.assertEqual(fields["destructive_authority"], "none")
        self.assertEqual(fields["phone_boot"], "forbidden")
        self.assertEqual(
            fields["source_image_sha256"],
            "533973be0e0ca76c5db8645fdef9aeb64d20b8c9c98b70124a2561700f119153",
        )
        self.assertEqual(
            fields["source_tree_sha256"],
            "4701c23b93624bf894bb76331c165b650c9a2aecb99273a4e6d37c20ac3ef167",
        )
        self.assertEqual(fields["rescue_slot"], "a")
        self.assertEqual(fields["accepted_generation"], "163")

    def test_executor_classifies_partial_before_clone(self) -> None:
        source = self.executable_source(EXECUTOR)
        partial = source.index("target_state=partial", source.index("stage_set S40_CLONE"))
        clone = source.index('dd if="$source_image" of="$arch_root"')
        self.assertLess(partial, clone)
        for state in ("untouched", "partial", "cloned", "native", "final"):
            self.assertIn(f"target_state={state}", source)

    def test_read_only_preflight_exits_before_watchdog_or_write_window(self) -> None:
        source = self.executable_source(EXECUTOR)
        start = source.index(
            'if [ "$operation_mode" = read_only_preflight ]; then',
            source.index("gpt_before="),
        )
        end = source.index("\nfi\n", start) + 4
        preflight = source[start:end]
        for contract in (
            "verify_safe_temperature",
            "no_physical_mounts",
            "lock_storage",
            "resolve_exact_storage",
            "wrapper_physical_count=",
            "userdata_blocks=51124000",
            "arch_root_empty=1",
            "all_read_only=1",
            "block_mounts=0",
            "sleep 3",
            "exit 0",
        ):
            self.assertIn(contract, preflight)
        for forbidden in (
            "watchdog_disarm",
            "open_write_window",
            "blockdev --setrw",
            "dd if=",
            "tune2fs",
            "resize2fs",
            "mount ",
        ):
            self.assertNotIn(forbidden, preflight)

        self.assertIn("recovery_guard_report_invalid", source)
        self.assertIn('emit "status=GUARDS $guard_fields"', source)
        self.assertIn("emit_partition_observation 24", source)
        self.assertIn('status=PARTITION number=$number', source)
        self.assertIn("arch_root_a 0004000000000000", source)

        collector = self.executable_source(COLLECTOR)
        self.assertIn('choices=("clone", "preflight")', collector)
        self.assertIn("Stage-2 preflight PASS identity or sequence changed", collector)
        self.assertIn("Stage-2 preflight wrapper count is invalid", collector)
        self.assertIn("unexpected Stage-2 guard record", collector)
        self.assertIn("Stage-2 guard classification changed", collector)
        self.assertIn("Stage-2 partition classification changed", collector)
        self.assertIn('options.output / "transcript.partial"', collector)
        self.assertIn("os.fsync(partial_fd)", collector)

    def test_native_seal_is_the_refreshed_tree(self) -> None:
        payload = SEAL.read_bytes()
        self.assertFalse(
            SEAL.stat().st_mode
            & (stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        )
        self.assertEqual(len(payload), 430)
        self.assertEqual(
            hashlib.sha256(payload).hexdigest(),
            "02231e86746fbc656090f52c96d7e0c968c7ca86ba7449c306f611ea20c6a876",
        )
        lines = payload.decode("ascii").splitlines()
        self.assertEqual(len(lines), 13)
        self.assertIn("tree_entries=37736", lines)
        self.assertIn("tree_regular_files=27604", lines)
        self.assertIn("tree_directories=1902", lines)
        self.assertIn(
            "tree_sha256=4701c23b93624bf894bb76331c165b650c9a2aecb99273a4e6d37c20ac3ef167",
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
            'check_hash "$reboot_bootloader" "$reboot_bootloader_sha256"',
            'install -m 0755 "$reboot_bootloader" "$stage/usr/libexec/rog5-reboot-bootloader"',
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

    def test_generation176_is_one_exact_read_only_admission(self) -> None:
        fields = dict(
            line.split("=", 1)
            for line in PREFLIGHT.read_text(encoding="ascii").splitlines()
        )
        digest = hashlib.sha256(PREFLIGHT.read_bytes()).hexdigest()
        self.assertEqual(digest, "3ee8244a6ccef26f594cf4aceecb2efc1e27b731fa7bdfc03917602def1b9f8d")
        self.assertEqual(fields["mode"], "read_only_preflight")
        self.assertEqual(fields["storage_write"], "forbidden")
        self.assertEqual(fields["watchdog_disarm"], "forbidden")
        rows = [line.split("\t") for line in BOOT_POLICY.read_text(encoding="ascii").splitlines()[1:]]
        self.assertEqual(len(rows), 10)
        self.assertEqual(rows[0][0], fields["profile"])
        self.assertEqual(rows[0][1], "revoked")
        self.assertEqual(rows[0][2], digest)
        self.assertIn("no write path was reachable", rows[0][6])

    def test_generation177_binds_delivery_hold_helper_and_one_admission(self) -> None:
        fields = dict(
            line.split("=", 1)
            for line in PREFLIGHT_SUCCESSOR.read_text(encoding="ascii").splitlines()
        )
        digest = hashlib.sha256(PREFLIGHT_SUCCESSOR.read_bytes()).hexdigest()
        self.assertEqual(digest, "8764447295144136ef58f759ca2f118da36025a49bdc2e13c918cd2a97a48381")
        self.assertEqual(fields["terminal_delivery_hold_seconds"], "3")
        self.assertEqual(fields["fallback"], "restart2-bootloader-before-generic-reset")
        rows = [line.split("\t") for line in BOOT_POLICY.read_text(encoding="ascii").splitlines()[1:]]
        self.assertEqual(sum(row[1] == "allow" for row in rows), 1)
        admitted = next(row for row in rows if row[0] == fields["profile"])
        self.assertEqual(admitted[1], "revoked")
        self.assertEqual(admitted[2], digest)
        self.assertIn("physical count 117", admitted[6])

    def test_generation178_binds_mode_specific_topology_and_one_admission(self) -> None:
        fields = dict(
            line.split("=", 1)
            for line in PREFLIGHT_TOPOLOGY.read_text(encoding="ascii").splitlines()
        )
        digest = hashlib.sha256(PREFLIGHT_TOPOLOGY.read_bytes()).hexdigest()
        self.assertEqual(digest, "5d2a7541fc708a76e19afa2252460f12c9cceb5d766a9f35af07b172b9379d85")
        self.assertEqual(fields["wrapper_physical_count"], "117")
        self.assertEqual(fields["stage1_wrapper_physical_count"], "116")
        rows = [line.split("\t") for line in BOOT_POLICY.read_text(encoding="ascii").splitlines()[1:]]
        self.assertEqual(sum(row[1] == "allow" for row in rows), 1)
        admitted = next(row for row in rows if row[0] == fields["profile"])
        self.assertEqual(admitted[1], "revoked")
        self.assertEqual(admitted[2], digest)
        self.assertIn("another pre-USB guard remains", admitted[6])

    def test_generation179_defers_only_read_only_aggregate_count(self) -> None:
        fields = dict(
            line.split("=", 1)
            for line in PREFLIGHT_POST_USB.read_text(encoding="ascii").splitlines()
        )
        digest = hashlib.sha256(PREFLIGHT_POST_USB.read_bytes()).hexdigest()
        self.assertEqual(digest, "707cae20d3ed363599fbae4174a0081485f26ca213decd4b52a39f24b61dbaaa")
        self.assertEqual(fields["pre_usb_aggregate_count"], "deferred-for-read-only-preflight-only")
        self.assertEqual(fields["exact_storage_resolver"], "required")
        rows = [line.split("\t") for line in BOOT_POLICY.read_text(encoding="ascii").splitlines()[1:]]
        self.assertEqual(sum(row[1] == "allow" for row in rows), 1)
        admitted = next(row for row in rows if row[0] == fields["profile"])
        self.assertEqual(admitted[1], "revoked")
        self.assertEqual(admitted[2], digest)
        self.assertIn("earlier UFS discovery/isolation/power/inventory guard", admitted[6])

    def test_generation180_binds_usb_first_read_only_guard_report(self) -> None:
        fields = dict(
            line.split("=", 1)
            for line in PREFLIGHT_USB_FIRST.read_text(encoding="ascii").splitlines()
        )
        digest = hashlib.sha256(PREFLIGHT_USB_FIRST.read_bytes()).hexdigest()
        self.assertEqual(digest, "827e5b67f6e2c876af21fbc01c79ee79025f03a59d21639e25df3d8cf0b305a4")
        self.assertEqual(fields["usb_order"], "bind-before-deferred-ufs-guards")
        self.assertEqual(fields["clone_mode_order"], "unchanged-pre-usb-fail-closed")
        rows = [line.split("\t") for line in BOOT_POLICY.read_text(encoding="ascii").splitlines()[1:]]
        self.assertEqual(sum(row[1] == "allow" for row in rows), 1)
        admitted = next(row for row in rows if row[0] == fields["profile"])
        self.assertEqual(admitted[1], "revoked")
        self.assertEqual(admitted[2], digest)

    def test_generation181_binds_exact_guard_and_partition_fields(self) -> None:
        fields = dict(
            line.split("=", 1)
            for line in PREFLIGHT_EXACT_FIELDS.read_text(encoding="ascii").splitlines()
        )
        digest = hashlib.sha256(PREFLIGHT_EXACT_FIELDS.read_bytes()).hexdigest()
        self.assertEqual(digest, "ba2fa54f3e343e3e0a7921281ab5f0f7219723deb6c0b49f687e86f51e272bb8")
        self.assertIn("auto_markers", fields["guard_record"])
        self.assertEqual(fields["partition_record"], "number,read,first,last,type,unique,name,attrs")
        rows = [line.split("\t") for line in BOOT_POLICY.read_text(encoding="ascii").splitlines()[1:]]
        self.assertEqual(sum(row[1] == "allow" for row in rows), 1)
        admitted = next(row for row in rows if row[0] == fields["profile"])
        self.assertEqual(admitted[1], "revoked")
        self.assertEqual(admitted[2], digest)

    def test_generation182_reuses_the_live_proven_wrapper_image(self) -> None:
        fields = dict(
            line.split("=", 1)
            for line in PREFLIGHT_STABLE_IMAGE.read_text(encoding="ascii").splitlines()
        )
        digest = hashlib.sha256(PREFLIGHT_STABLE_IMAGE.read_bytes()).hexdigest()
        self.assertEqual(digest, "35590291bdacb3a8dc198c27a38b8a41333d49d6f72f5c6bb74b6d81bcd65747")
        self.assertEqual(fields["wrapper_mode"], "live-proven-kernel-external-ramdisk")
        self.assertEqual(fields["kernel_sha256"], fields["predecessor_kernel_sha256"])
        self.assertEqual(fields["kernel_rebuild"], "forbidden")
        self.assertEqual(fields["recovery_timeout_seconds"], "900")
        rows = [line.split("\t") for line in BOOT_POLICY.read_text(encoding="ascii").splitlines()[1:]]
        self.assertEqual(sum(row[1] == "allow" for row in rows), 1)
        admitted = next(row for row in rows if row[0] == fields["profile"])
        self.assertEqual(admitted[1], "revoked")
        self.assertEqual(admitted[2], digest)

    def test_generation183_accepts_exact_observed_wrapper_state(self) -> None:
        fields = dict(
            line.split("=", 1)
            for line in PREFLIGHT_CORRECTED.read_text(encoding="ascii").splitlines()
        )
        digest = hashlib.sha256(PREFLIGHT_CORRECTED.read_bytes()).hexdigest()
        self.assertEqual(digest, "ab476c8cca14aff156943ff72e6fd2bf702df02b2069f191cedc2c93f757d2ba")
        self.assertEqual(fields["power_marker_status"], "unsupported-on-stable-wrapper")
        self.assertEqual(fields["expected_arch_root_attrs"], "0004000000000000")
        self.assertEqual(fields["kernel_rebuild"], "forbidden")
        rows = [line.split("\t") for line in BOOT_POLICY.read_text(encoding="ascii").splitlines()[1:]]
        self.assertEqual(sum(row[1] == "allow" for row in rows), 1)
        admitted = next(row for row in rows if row[0] == fields["profile"])
        self.assertEqual(admitted[1], "revoked")
        self.assertEqual(admitted[2], digest)

    def test_generation184_retains_progress_before_fallback(self) -> None:
        fields = dict(
            line.split("=", 1)
            for line in PREFLIGHT_DURABLE.read_text(encoding="ascii").splitlines()
        )
        digest = hashlib.sha256(PREFLIGHT_DURABLE.read_bytes()).hexdigest()
        self.assertEqual(digest, "c11a8e0ce53f29188b845fdaa471163319e3c02c2771488f06c3f4ddd25548e6")
        self.assertEqual(fields["collector_hold_seconds"], "1")
        self.assertEqual(fields["partial_transcript"], "fsync-each-validated-record")
        self.assertEqual(fields["kernel_rebuild"], "forbidden")
        rows = [line.split("\t") for line in BOOT_POLICY.read_text(encoding="ascii").splitlines()[1:]]
        self.assertEqual(sum(row[1] == "allow" for row in rows), 1)
        admitted = next(row for row in rows if row[0] == fields["profile"])
        self.assertEqual(admitted[1], "revoked")
        self.assertEqual(admitted[2], digest)

    def test_generation185_initializes_unsupported_evidence(self) -> None:
        fields = dict(
            line.split("=", 1)
            for line in PREFLIGHT_INITIALIZED.read_text(encoding="ascii").splitlines()
        )
        digest = hashlib.sha256(PREFLIGHT_INITIALIZED.read_bytes()).hexdigest()
        self.assertEqual(digest, "39ac9cde4c24d0aefca63ff231113bc4b7a6ab72eaa243d83895ccdb934d2659")
        self.assertEqual(fields["deferred_guard_counts"], "initialized-before-optional-probe")
        self.assertEqual(fields["partial_transcript"], "fsync-each-validated-record")
        rows = [line.split("\t") for line in BOOT_POLICY.read_text(encoding="ascii").splitlines()[1:]]
        self.assertEqual(sum(row[1] == "allow" for row in rows), 1)
        admitted = next(row for row in rows if row[0] == fields["profile"])
        self.assertEqual(admitted[1], "allow")
        self.assertEqual(admitted[2], digest)


if __name__ == "__main__":
    unittest.main()
