#!/usr/bin/env python3
"""Hostile fixtures for name-independent persistent-root storage and UDC selection."""

from __future__ import annotations

import hashlib
from pathlib import Path
import subprocess
import tempfile
import unittest


REPO = Path(__file__).resolve().parents[2]
INIT = REPO / "initramfs/persistent-root-init"
ATTEST = REPO / "initramfs/persistent-root-attest"


def function(source: str, name: str) -> str:
    marker = f"{name}() {{\n"
    start = source.find(marker)
    if start < 0:
        raise AssertionError(f"missing function {name}")
    end = source.find("\n}\n", start)
    if end < 0:
        raise AssertionError(f"unterminated function {name}")
    return source[start : end + 3]


class PersistentRootStorageResolutionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source = INIT.read_text(encoding="utf-8")
        cls.resolver = function(cls.source, "find_exact_userdata")
        cls.udc_functions = "\n".join(
            function(cls.source, name)
            for name in (
                "udc_candidate_count",
                "validate_expected_udc_once",
                "validate_expected_udc",
                "select_expected_udc",
            )
        )
        cls.rendezvous = function(cls.source, "wait_for_deferred_ufs_rendezvous")
        cls.exact_regular = function(cls.source, "verify_exact_regular")
        cls.volatile_state = "\n".join(
            function(cls.source, name)
            for name in (
                "verify_systemd_update_marker",
                "prepare_volatile_systemd_state",
            )
        )
        cls.write_probe = function(
            cls.source, "write_exact_local_image_probe"
        )
        cls.verify_write_probe = function(
            cls.source, "verify_exact_local_image_probe"
        )

    def add_disk(
        self,
        root: Path,
        disk: str,
        *,
        label: str = "userdata",
        disk_size: str = "494927872",
        logical: str = "4096",
        partition: str = "23",
        start: str = "18821440",
        size: str = "408997568",
        readonly: str = "1",
        devname: str | None = None,
    ) -> Path:
        disk_dir = root / disk
        disk_dir.mkdir()
        (disk_dir / "device").touch()
        (disk_dir / "size").write_text(disk_size + "\n")
        (disk_dir / "queue").mkdir()
        (disk_dir / "queue/logical_block_size").write_text(logical + "\n")
        node = f"{disk}{partition}"
        part = disk_dir / node
        part.mkdir()
        (part / "partition").write_text(partition + "\n")
        (part / "start").write_text(start + "\n")
        (part / "size").write_text(size + "\n")
        (part / "ro").write_text(readonly + "\n")
        (part / "uevent").write_text(
            f"DEVNAME={devname or node}\nPARTNAME={label}\n"
        )
        return part

    def resolve(self, root: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["sh", "-c", self.resolver + '\nfind_exact_userdata "$1" /dev', "sh", str(root)],
            text=True,
            capture_output=True,
            check=False,
        )

    def test_device_letter_is_not_identity(self) -> None:
        for disk in ("sda", "sdg"):
            with self.subTest(disk=disk), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                self.add_disk(root, disk)
                result = self.resolve(root)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stdout, f"/dev/{disk}23\n")

    def test_every_geometry_and_identity_mutation_fails(self) -> None:
        mutations = {
            "label": {"label": "metadata"},
            "disk-size": {"disk_size": "494927871"},
            "logical": {"logical": "512"},
            "partition": {"partition": "22"},
            "start": {"start": "18821441"},
            "size": {"size": "476106391"},
            "writable": {"readonly": "0"},
            "devname": {"devname": "sda22"},
        }
        for name, mutation in mutations.items():
            with self.subTest(name=name), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                self.add_disk(root, "sda", **mutation)
                self.assertNotEqual(self.resolve(root).returncode, 0)

    def test_duplicate_userdata_anywhere_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.add_disk(root, "sda")
            self.add_disk(root, "sdg", disk_size="16")
            self.assertNotEqual(self.resolve(root).returncode, 0)

    def run_udc(self, names: tuple[str, ...]) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name in names:
                (root / name).touch()
            script = (
                "set -u\n"
                + self.udc_functions
                + '\nexpected_udc=a600000.usb\nudc_poll_attempts=1\nudc_class_dir="$1"\n'
                + "select_expected_udc\n"
            )
            return subprocess.run(
                ["sh", "-c", script, "sh", str(root)],
                text=True,
                capture_output=True,
                check=False,
            )

    def test_udc_requires_one_exact_candidate(self) -> None:
        exact = self.run_udc(("a600000.usb",))
        self.assertEqual(exact.returncode, 0, exact.stderr)
        self.assertEqual(exact.stdout, "a600000.usb\n")
        for candidates in (
            (),
            ("wrong.udc",),
            ("renamed-a600000.usb",),
            ("a600000.usb", "wrong.udc"),
        ):
            with self.subTest(candidates=candidates):
                self.assertNotEqual(self.run_udc(candidates).returncode, 0)

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "a600000.usb").touch()
            sequence = root / "sequence"
            sequence.write_text("0\n")
            script = (
                "set -u\n"
                + self.udc_functions
                + '\nexpected_udc=a600000.usb\nudc_poll_attempts=1\n'
                + 'udc_class_dir="$1"\nsequence_file="$2"\n'
                + "validate_expected_udc() {\n"
                + '  value=$(cat "$sequence_file")\n'
                + '  if [ "$value" = 0 ]; then\n'
                + '    printf "%s\\n" 1 >"$sequence_file"\n'
                + '    printf "%s\\n" a600000.usb\n'
                + "  else\n"
                + '    printf "%s\\n" wrong.udc\n'
                + "  fi\n"
                + "}\nselect_expected_udc\n"
            )
            changing = subprocess.run(
                ["sh", "-c", script, "sh", str(root), str(sequence)],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertNotEqual(changing.returncode, 0)

    def test_attestation_uses_the_resolved_runtime_device(self) -> None:
        attest = ATTEST.read_text(encoding="utf-8")
        self.assertIn("userdata_record=/run/rog5-p2-userdata-device", attest)
        self.assertIn('awk -v userdata="$userdata"', attest)
        self.assertNotIn("/dev/sda23", attest)
        self.assertNotIn("/sys/class/block/sda23", attest)
        self.assertNotIn("userdata=/dev/sda23", self.source)
        self.assertNotIn("[ \"$found\" = sda23 ]", self.source)
        self.assertGreaterEqual(self.source.count("expected_udc_is_bound"), 3)
        self.assertIn(
            "PASS sealed local image matches exact boot-critical identities",
            attest,
        )
        self.assertIn("loop_record=/run/rog5-p2-root-loop-device", attest)
        self.assertIn("local_image_mount=ro-noload", attest)
        self.assertNotIn(
            "PASS previously sealed root matches exact boot-critical identities",
            attest,
        )

    def test_post_handoff_storage_sweep_uses_retained_runtime_loader(self) -> None:
        attest = ATTEST.read_text(encoding="utf-8")
        start = attest.index("\nphysical_count=0\n")
        end = attest.index("\nblocked_query_count=", start)
        sweep = attest[start:end]
        self.assertIn(
            "runtime_busybox=/run/initramfs/bin/busybox", attest
        )
        self.assertIn(
            "runtime_loader=/run/initramfs/lib/ld-musl-aarch64.so.1",
            attest,
        )
        self.assertIn(
            '"$runtime_loader" "$runtime_busybox" blockdev "$@"', attest
        )
        self.assertIn("disk=${sys_disk##*/}", sweep)
        self.assertIn('IFS= read -r readonly <"$sys_block/ro"', sweep)
        self.assertIn('runtime_blockdev --getro "$device"', sweep)
        self.assertEqual(attest.count('"$runtime_busybox" blockdev'), 1)
        self.assertNotIn("basename", sweep)
        self.assertNotIn("cat ", sweep)
        self.assertEqual(sweep.count("blockdev --getro"), 1)
        markers = (
            "progress start",
            "progress mounts-pass",
            "progress physical-readonly-pass",
            "progress ufs-health-pass",
            "progress ssh-policy-pass",
        )
        self.assertEqual(
            [attest.index(marker) for marker in markers],
            sorted(attest.index(marker) for marker in markers),
        )

    def test_usb_observability_precedes_target_identity_and_ufs(self) -> None:
        watchdog = self.source.index("\narm_watchdog || force_rollback\n")
        usb = self.source.index("\nif ! configure_usb; then\n")
        command_line = self.source.index(
            '\nif [ "$persistent_count" -ne 1 ] || '
        )
        release = self.source.index(
            '\nif ! IFS= read -r running_kernel_release '
        )
        rendezvous = self.source.index(
            "\nif deferred_ufs_modules_present; then\n"
        )
        module_load = self.source.index(
            "\n\tload_deferred_ufs_modules\n"
        )
        discovery = self.source.index(
            "\nlog 'waiting for stable UFS discovery'\n"
        )
        self.assertLess(watchdog, usb)
        self.assertLess(usb, command_line)
        self.assertLess(command_line, release)
        self.assertLess(release, rendezvous)
        self.assertLess(rendezvous, module_load)
        self.assertLess(module_load, discovery)

    def test_deferred_ufs_consumer_loads_exact_module_chain(self) -> None:
        loader = function(self.source, "load_deferred_ufs_modules")
        self.assertEqual(
            [
                line.strip().removeprefix("insmod ").split()[0]
                for line in loader.splitlines()
                if line.strip().startswith("insmod ")
            ],
            [
                "/rog5-ufs-modules/phy-qcom-qmp-ufs.ko",
                "/rog5-ufs-modules/ufshcd-core.ko",
                "/rog5-ufs-modules/ufshcd-pltfrm.ko",
                "/rog5-ufs-modules/ufs-qcom.ko",
            ],
        )
        self.assertNotIn("modprobe", loader)
        self.assertNotIn("*", loader)
        self.assertNotIn("return 2", loader)

    def test_deferred_ufs_consumer_loads_and_proves_each_exact_module(self) -> None:
        loader = function(self.source, "load_deferred_ufs_modules")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            module_dir = root / "modules"
            module_dir.mkdir()
            for name in (
                "phy-qcom-qmp-ufs.ko",
                "ufshcd-core.ko",
                "ufshcd-pltfrm.ko",
                "ufs-qcom.ko",
            ):
                (module_dir / name).touch()
            modules = root / "proc-modules"
            modules.write_text("")
            calls = root / "calls"
            fixture = loader.replace(
                "module_dir=/rog5-ufs-modules", 'module_dir="$1"'
            ).replace("/proc/modules", '"$modules_file"')
            script = (
                "set -u\n"
                + fixture
                + '\nmodules_file="$2"\ncall_log="$3"\n'
                + "log() { :; }\n"
                + 'insmod() { printf "%s\\n" "$1" >>"$call_log"; '
                + 'case "$1" in '
                + '*phy-qcom-qmp-ufs.ko) name=phy_qcom_qmp_ufs ;; '
                + '*ufshcd-core.ko) name=ufshcd_core ;; '
                + '*ufshcd-pltfrm.ko) name=ufshcd_pltfrm ;; '
                + '*ufs-qcom.ko) name=ufs_qcom ;; esac; '
                + 'printf "%s 1 0 - Live 0x0\\n" "$name" >>"$modules_file"; }\n'
                + 'load_deferred_ufs_modules "$@"\n'
            )
            result = subprocess.run(
                [
                    "sh",
                    "-c",
                    script,
                    "sh",
                    str(module_dir),
                    str(modules),
                    str(calls),
                ],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(
                calls.read_text().splitlines(),
                [
                    "/rog5-ufs-modules/phy-qcom-qmp-ufs.ko",
                    "/rog5-ufs-modules/ufshcd-core.ko",
                    "/rog5-ufs-modules/ufshcd-pltfrm.ko",
                    "/rog5-ufs-modules/ufs-qcom.ko",
                ],
            )

    def test_readonly_inventory_advances_directly_to_the_local_root(self) -> None:
        inventory = self.source.index("\nif ! write_ufs_inventory; then\n")
        mount = self.source.index("\nif ! mount_persistent_root; then\n")
        verify = self.source.index("\nif ! verify_persistent_root; then\n")
        self.assertLess(inventory, mount)
        self.assertLess(mount, verify)
        between = self.source[inventory:mount]
        self.assertNotIn("deliver_readonly_ufs_proof", between)
        self.assertNotIn("ufs-readonly-control", between)
        self.assertNotIn("read-only UFS enumeration completed", between)
        self.assertIn("verify_physical_storage_read_only", between)
        self.assertIn("verify_ufs_power_containment", between)
        mount_function = function(self.source, "mount_persistent_root")
        self.assertIn('mount -t ext4 -o ro,noload "$userdata" /mnt/userdata', mount_function)
        self.assertIn(
            "mkdir -p /mnt/userdata /mnt/root-ro /mnt/probe-root /mnt/state /newroot",
            mount_function,
        )
        self.assertIn("verify_only_userdata_mount", mount_function)
        self.assertIn("verify_physical_storage_read_only", mount_function)

    def test_local_image_write_probe_is_exact_and_one_shot(self) -> None:
        write_probe = self.write_probe.replace(
            "probe_root=/mnt/probe-root", 'probe_root=$1'
        )
        verify_write_probe = self.verify_write_probe.replace(
            "\tcase $probe_root in\n"
            "\t\t/mnt/probe-root|/mnt/root-ro|/.rog5/root-ro) ;;\n"
            "\t\t*) return 1 ;;\n"
            "\tesac\n",
            "",
        ).replace(
            '"0:0:444:$expected_probe_bytes:1"',
            '"$(id -u):$(id -g):444:$expected_probe_bytes:1"',
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "var/lib").mkdir(parents=True)
            script = (
                "set -u\n"
                + write_probe
                + verify_write_probe
                + '\nrunning_kernel_release=7.1.4-gae717d919f87\n'
                + 'expected_image_uuid=598a876b-a8db-4859-a01a-1b864b0a87f4\n'
                + 'expected_probe_bytes=132\n'
                + 'expected_ufs_storage_mode=local-write\n'
                + 'expected_probe_boot_id=current\n'
                + 'target_boot_id=11111111-2222-3333-4444-555555555555\n'
                + 'write_exact_local_image_probe "$1" || exit 1\n'
                + 'verify_exact_local_image_probe "$1"\n'
            )
            first = subprocess.run(
                ["sh", "-c", script, "sh", str(root)],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(first.returncode, 0, first.stderr)
            marker = root / "var/lib/rog5/local-image-write-probe-v1"
            self.assertEqual(
                marker.read_text(),
                "format=rog5-local-image-write-probe-v1\n"
                "image_uuid=598a876b-a8db-4859-a01a-1b864b0a87f4\n"
                "boot_id=11111111-2222-3333-4444-555555555555\n",
            )
            self.assertEqual(marker.stat().st_mode & 0o777, 0o444)
            repeated = subprocess.run(
                ["sh", "-c", script, "sh", str(root)],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertNotEqual(repeated.returncode, 0)

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "var/lib").mkdir(parents=True)
            (root / "var/lib/rog5").symlink_to("elsewhere")
            linked = subprocess.run(
                ["sh", "-c", script, "sh", str(root)],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertNotEqual(linked.returncode, 0)

    def test_readonly_probe_is_bound_to_the_distinct_writer_boot(self) -> None:
        verify_write_probe = self.verify_write_probe.replace(
            "\tcase $probe_root in\n"
            "\t\t/mnt/probe-root|/mnt/root-ro|/.rog5/root-ro) ;;\n"
            "\t\t*) return 1 ;;\n"
            "\tesac\n",
            "",
        ).replace(
            '"0:0:444:$expected_probe_bytes:1"',
            '"$(id -u):$(id -g):444:$expected_probe_bytes:1"',
        )
        writer = "7c3afb64-8e84-4f4b-87f4-88d19c2646de"
        current = "11111111-2222-3333-4444-555555555555"
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            marker = root / "var/lib/rog5/local-image-write-probe-v1"
            marker.parent.mkdir(parents=True)
            marker.write_text(
                "format=rog5-local-image-write-probe-v1\n"
                "image_uuid=598a876b-a8db-4859-a01a-1b864b0a87f4\n"
                f"boot_id={writer}\n"
            )
            marker.chmod(0o444)

            def verify(mode: str, expected: str, boot_id: str = current) -> int:
                script = (
                    "set -u\n"
                    + verify_write_probe
                    + '\nexpected_image_uuid=598a876b-a8db-4859-a01a-1b864b0a87f4\n'
                    + 'expected_probe_bytes=132\n'
                    + f'expected_ufs_storage_mode={mode}\n'
                    + f'expected_probe_boot_id={expected}\n'
                    + f'target_boot_id={boot_id}\n'
                    + 'verify_exact_local_image_probe "$1"\n'
                )
                return subprocess.run(
                    ["sh", "-c", script, "sh", str(root)],
                    text=True,
                    capture_output=True,
                    check=False,
                ).returncode

            self.assertEqual(verify("read-only", writer), 0)
            self.assertNotEqual(verify("read-only", current), 0)
            self.assertNotEqual(verify("local-write", writer), 0)
            self.assertNotEqual(verify("read-only", writer, writer), 0)

            marker.chmod(0o644)
            marker.write_text(
                "format=rog5-local-image-write-probe-v1\n"
                "image_uuid=598a876b-a8db-4859-a01a-1b864b0a87f4\n"
                f"boot_id={current}\n"
            )
            marker.chmod(0o444)
            self.assertEqual(verify("local-write", "current"), 0)

    def test_write_window_relocks_every_physical_node_before_boot(self) -> None:
        open_window = function(self.source, "open_exact_userdata_write_window")
        close_window = function(self.source, "close_exact_userdata_write_window")
        write_cycle = function(self.source, "run_local_image_write_probe")
        self.assertEqual(open_window.count("blockdev --setrw"), 2)
        self.assertIn('blockdev --setrw "$userdata_disk"', open_window)
        self.assertIn('blockdev --setrw "$userdata"', open_window)
        self.assertNotIn("/sys/class/block/*", open_window)
        self.assertNotIn("blockdev --setrw /dev/", open_window)
        self.assertIn("verify_exact_userdata_write_window", open_window)
        self.assertIn('blockdev --setro "$userdata"', close_window)
        self.assertIn('blockdev --setro "$userdata_disk"', close_window)
        self.assertIn("verify_physical_storage_read_only", close_window)
        self.assertIn(
            'mount -t ext4 -o rw,nodev,nosuid,noexec,noatime \\\n'
            '\t\t"$userdata" /mnt/userdata',
            write_cycle,
        )
        self.assertIn('losetup "$probe_loop" "$root_image"', write_cycle)
        self.assertIn(
            "[ -d /mnt/probe-root ] && [ ! -L /mnt/probe-root ]",
            write_cycle,
        )
        self.assertLess(
            write_cycle.index("[ -d /mnt/probe-root ]"),
            write_cycle.index("umount /mnt/userdata"),
        )
        self.assertIn("arch-local-a.ext4", write_cycle)
        self.assertIn('blkid "$probe_loop"', write_cycle)
        self.assertIn("$expected_image_uuid", write_cycle)
        self.assertIn("$expected_image_label", write_cycle)
        self.assertIn(
            'mount -t ext4 -o rw,nodev,nosuid,noexec,noatime \\\n'
            '\t\t"$probe_loop" /mnt/probe-root',
            write_cycle,
        )
        self.assertIn("write_exact_local_image_probe || probe_status=1", write_cycle)
        self.assertIn("sync", write_cycle)
        self.assertIn("close_exact_userdata_write_window", write_cycle)
        write_surface = "\n".join(
            (
                write_cycle,
                function(self.source, "open_exact_userdata_write_window"),
                function(self.source, "verify_exact_userdata_write_window"),
            )
        )
        for failure_stage in (
            "userdata-unmount",
            "write-window-precheck",
            "userdata-partition-rw",
            "userdata-disk-rw",
            "write-window-count",
            "userdata-rw",
            "image-loop-rw",
            "image-fs-rw",
            "image-probe",
            "storage-relock",
        ):
            self.assertIn(
                f"image_write_failure_stage={failure_stage}", write_surface
            )
        for forbidden in ("mkfs", "dd ", "blkdiscard", "sgdisk", "parted"):
            self.assertNotIn(forbidden, write_cycle)

        write_stage = self.source.index(
            "publish_or_rollback image-write ENTER"
        )
        read_mount = self.source.index("if ! mount_local_root_image; then")
        self.assertLess(write_stage, read_mount)
        self.assertIn("publish_or_rollback image-write PASS", self.source)
        self.assertIn(
            'fail_local_stage "$image_write_failure_stage"', self.source
        )
        self.assertIn(
            "verify_exact_local_image_probe \"$root\"",
            function(self.source, "verify_persistent_root"),
        )

    def test_write_window_classifies_effective_readonly_mismatch(self) -> None:
        verifier = function(self.source, "verify_exact_userdata_write_window")
        for device_class in (
            "selected-disk",
            "selected-part",
            "other-disk",
            "other-part",
        ):
            self.assertIn(
                f"write-window-{device_class}-blockdev", verifier
            )
            self.assertIn(f"write-window-{device_class}-sysfs", verifier)
        self.assertNotIn("write-window-blockdev", verifier)
        self.assertNotIn("write-window-sysfs", verifier)

    def test_boot_verification_is_bounded_to_exact_critical_files(self) -> None:
        verifier = function(self.source, "verify_persistent_root")
        self.assertNotIn("persistent-root-verify", verifier)
        self.assertNotIn("find ", verifier)
        self.assertNotIn("for ", verifier)
        for identity in (
            ".rog5-persistent-seal",
            "usr/lib/systemd/systemd",
            "usr/bin/sshd",
            "root/.ssh/authorized_keys",
            "etc/ssh/sshd_config.d/10-rog5-server.conf",
        ):
            self.assertIn(identity, verifier)

    def test_exact_regular_rejects_content_metadata_and_links(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "critical"
            path.write_bytes(b"critical\n")
            path.chmod(0o600)
            script = (
                "set -u\n"
                + self.exact_regular
                + '\nverify_exact_regular "$1" "$(id -u)" "$(id -g)" 600 9 '
                + "f8fe9deaf27e9f2bf3ab8d995936047da665b94e17170807ea0d77bc130816d0\n"
            )
            pristine = subprocess.run(
                ["sh", "-c", script, "sh", str(path)],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(pristine.returncode, 0, pristine.stderr)

            path.write_bytes(b"mutation\n")
            self.assertNotEqual(
                subprocess.run(
                    ["sh", "-c", script, "sh", str(path)],
                    check=False,
                ).returncode,
                0,
            )
            path.write_bytes(b"critical\n")
            path.chmod(0o644)
            self.assertNotEqual(
                subprocess.run(
                    ["sh", "-c", script, "sh", str(path)],
                    check=False,
                ).returncode,
                0,
            )
            path.unlink()
            path.symlink_to("elsewhere")
            self.assertNotEqual(
                subprocess.run(
                    ["sh", "-c", script, "sh", str(path)],
                    check=False,
                ).returncode,
                0,
            )

    def run_volatile_state(
        self, mutation: str = "none", persistent_overlay: bool = False
    ) -> tuple[subprocess.CompletedProcess[str], Path | None]:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        base = Path(tmp.name)
        root = base / "root"
        lower = base / "lower"
        upper = base / "upper"
        runtime = base / "run"
        for directory in (
            root / "etc",
            root / "var",
            root / "usr",
            lower / "etc",
            lower / "var",
            upper,
            runtime / "systemd" / "system",
            runtime / "systemd" / "system" / "sysinit.target.wants",
        ):
            directory.mkdir(parents=True, exist_ok=True)
        cache = root / "etc" / "ld.so.cache"
        cache.write_bytes(b"updated-cache\n" if persistent_overlay else b"cache\n")
        cache.chmod(0o644)
        lower_cache = lower / "etc" / "ld.so.cache"
        lower_cache.write_bytes(b"cache\n")
        lower_cache.chmod(0o644)
        if persistent_overlay:
            for subtree in ("etc", "var"):
                upper_subtree = upper / subtree
                upper_subtree.mkdir()
                (root / subtree / ".updated").touch()
                (upper_subtree / ".updated").touch()
            if mutation in (
                "systemd-update-markers",
                "systemd-update-marker-bad-comment",
                "systemd-update-marker-mismatched-time",
                "systemd-update-marker-etc-only",
                "systemd-update-marker-var-only",
                "systemd-update-marker-bad-timestamp",
                "systemd-update-marker-upper-mismatch",
                "systemd-update-marker-symlink",
                "systemd-update-marker-mode",
            ):
                for subtree in ("etc", "var"):
                    if mutation.endswith("-only") and not mutation.endswith(
                        f"-{subtree}-only"
                    ):
                        continue
                    timestamp = (
                        "1788332957852528814"
                        if mutation == "systemd-update-marker-mismatched-time"
                        and subtree == "var"
                        else "1788332957852528813"
                    )
                    if mutation == "systemd-update-marker-bad-timestamp":
                        timestamp = "not-a-timestamp"
                    first = (
                        "# Wrong marker format"
                        if mutation == "systemd-update-marker-bad-comment"
                        and subtree == "etc"
                        else "# This file was created by systemd-update-done. "
                        "The timestamp below is the"
                    )
                    marker = (
                        f"{first}\n"
                        f"# modification time of /usr/ for which the most "
                        f"recent updates of /{subtree}/ have\n"
                        "# been applied. See man:systemd-update-done.service(8) "
                        "for details.\n"
                        f"TIMESTAMP_NSEC={timestamp}\n"
                    )
                    (root / subtree / ".updated").write_text(marker)
                    (upper / subtree / ".updated").write_text(marker)
                if mutation == "systemd-update-marker-upper-mismatch":
                    (upper / "etc/.updated").write_text("")
                elif mutation == "systemd-update-marker-symlink":
                    marker_path = root / "etc/.updated"
                    marker_path.unlink()
                    marker_path.symlink_to(upper / "etc/.updated")
                elif mutation == "systemd-update-marker-mode":
                    (upper / "etc/.updated").chmod(0o666)
        if mutation == "wrong-cache":
            cache.write_bytes(b"wrong\n")
        elif mutation == "linked-cache":
            cache.unlink()
            cache.symlink_to(root / "usr")
        elif mutation == "lower-marker":
            (lower / "etc" / ".updated").touch()
        elif mutation == "upper-marker":
            (upper / "etc").mkdir()
            (upper / "etc" / ".updated").touch()
        elif mutation == "keygen-mask":
            (
                runtime
                / "systemd"
                / "system"
                / "sshdgenkeys.service"
            ).symlink_to("/dev/null")
        elif mutation == "ed25519-unit":
            (
                runtime
                / "systemd"
                / "system"
                / "rog5-sshd-ed25519-key.service"
            ).touch()
        elif mutation == "stock-sshd-mask":
            (runtime / "systemd" / "system" / "sshd.service").symlink_to(
                "/dev/null"
            )
        elif mutation == "early-sshd-unit":
            (
                runtime / "systemd" / "system" / "rog5-early-sshd.service"
            ).touch()
        elif mutation == "early-sshd-wants":
            (
                runtime
                / "systemd"
                / "system"
                / "sysinit.target.wants"
                / "rog5-early-sshd.service"
            ).symlink_to("../wrong.service")

        cache_hash = hashlib.sha256(b"cache\n").hexdigest()
        helper = self.volatile_state.replace(
            "expected_cache_size=20207", "expected_cache_size=6"
        ).replace(
            "expected_cache_sha256="
            "ae57b0740e33f19b3f748bdf8e159a65ecfb828f1339f093d91ec9ef4b8e89ed",
            f"expected_cache_sha256={cache_hash}",
        )
        verifier = r'''
verify_exact_regular() {
	path=$1
	mode=$4
	size=$5
	hash=$6
	[ -f "$path" ] && [ ! -L "$path" ] || return 1
	[ "$(stat -c '%a:%s:%h' "$path")" = "$mode:$size:1" ] || return 1
	[ "$(sha256sum "$path" | cut -d ' ' -f 1)" = "$hash" ]
}
stat() {
	if [ "$1:$2:$3" = "-c:%u:%g:%a:%h:$fixture_root/etc/ld.so.cache" ]; then
		printf '0:0:644:1\n'
	else
		command stat "$@"
	fi
}
chown() { :; }
touch() {
	command touch "$@" || return 1
	case ${3-} in
		"$fixture_root/etc/.updated")
			mkdir -p "$fixture_upper/etc"
			command touch -r "$fixture_root/usr" \
				"$fixture_upper/etc/.updated"
			;;
		"$fixture_root/var/.updated")
			mkdir -p "$fixture_upper/var"
			command touch -r "$fixture_root/usr" \
				"$fixture_upper/var/.updated"
			;;
	esac
}
chmod() {
	command chmod "$@" || return 1
	case $2 in
		"$fixture_root/etc/.updated")
			command chmod "$1" "$fixture_upper/etc/.updated" ;;
		"$fixture_root/var/.updated")
			command chmod "$1" "$fixture_upper/var/.updated" ;;
	esac
}
'''
        script = (
            "set -u\n"
            + "expected_ssh_diagnostic_mode=0\n"
            + f"expected_persistent_overlay_mode={int(persistent_overlay)}\n"
            + helper
            + verifier
            + '\nfixture_root="$1"\nfixture_lower="$2"\n'
            + 'fixture_upper="$3"\nfixture_runtime="$4"\n'
            + "prepare_volatile_systemd_state "
            + '"$fixture_root" "$fixture_lower" '
            + '"$fixture_upper" "$fixture_runtime"\n'
        )
        result = subprocess.run(
            [
                "sh",
                "-c",
                script,
                "sh",
                str(root),
                str(lower),
                str(upper),
                str(runtime),
            ],
            text=True,
            capture_output=True,
            check=False,
        )
        return result, base

    def test_persistent_systemd_state_accepts_existing_upper_markers(self) -> None:
        result, base = self.run_volatile_state(persistent_overlay=True)
        assert base is not None
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((base / "root/etc/ld.so.cache").read_bytes(), b"updated-cache\n")
        for subtree in ("etc", "var"):
            self.assertTrue((base / "root" / subtree / ".updated").is_file())
            self.assertTrue((base / "upper" / subtree / ".updated").is_file())
            self.assertFalse((base / "lower" / subtree / ".updated").exists())

    def test_persistent_systemd_state_accepts_systemd_update_done_markers(self) -> None:
        result, _ = self.run_volatile_state(
            mutation="systemd-update-markers", persistent_overlay=True
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_persistent_systemd_state_rejects_hostile_update_done_markers(self) -> None:
        for mutation in (
            "systemd-update-marker-bad-comment",
            "systemd-update-marker-bad-timestamp",
            "systemd-update-marker-upper-mismatch",
            "systemd-update-marker-symlink",
            "systemd-update-marker-mode",
        ):
            with self.subTest(mutation=mutation):
                result, _ = self.run_volatile_state(
                    mutation=mutation, persistent_overlay=True
                )
                self.assertNotEqual(result.returncode, 0)

    def test_interrupted_systemd_update_preserves_independent_markers(self) -> None:
        # systemd 260.2 saves /etc/.updated then /var/.updated separately.
        # A reset between these writes is not evidence of damaged storage.
        for mutation in (
            "systemd-update-marker-mismatched-time",
            "systemd-update-marker-etc-only",
            "systemd-update-marker-var-only",
        ):
            with self.subTest(mutation=mutation):
                result, base = self.run_volatile_state(
                    mutation=mutation, persistent_overlay=True
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                assert base is not None
                for subtree in ("etc", "var"):
                    merged = (base / "root" / subtree / ".updated").read_bytes()
                    physical = (base / "upper" / subtree / ".updated").read_bytes()
                    self.assertEqual(merged, physical)
                    if mutation.endswith("-only") and not mutation.endswith(
                        f"-{subtree}-only"
                    ):
                        self.assertEqual(merged, b"")
                    else:
                        timestamp = (
                            b"1788332957852528814"
                            if mutation.endswith("mismatched-time") and subtree == "var"
                            else b"1788332957852528813"
                        )
                        self.assertTrue(
                            merged.endswith(b"TIMESTAMP_NSEC=" + timestamp + b"\n")
                        )
                    self.assertFalse((base / "lower" / subtree / ".updated").exists())

    def test_volatile_systemd_state_is_exact_and_tmpfs_only(self) -> None:
        helper = self.volatile_state
        self.assertIn("expected_cache_size=20207", helper)
        self.assertIn(
            "expected_cache_sha256="
            "ae57b0740e33f19b3f748bdf8e159a65ecfb828f1339f093d91ec9ef4b8e89ed",
            helper,
        )
        self.assertIn(
            'verify_exact_regular "$root/etc/ld.so.cache" 0 0 644', helper
        )
        self.assertIn('touch -r "$root/usr" "$merged_marker"', helper)
        self.assertIn("systemd-vconsole-setup.service", helper)
        self.assertIn('ln -s /dev/null "$vconsole_mask"', helper)
        self.assertIn("sshdgenkeys.service", helper)
        self.assertIn('ln -s /dev/null "$sshdgenkeys_mask"', helper)
        self.assertIn('ln -s /dev/null "$stock_sshd_mask"', helper)
        self.assertIn("rog5-sshd-ed25519-key.service", helper)
        self.assertIn(
            "early_sshd_unit=$runtime/systemd/system/rog5-early-sshd.service",
            helper,
        )
        self.assertIn(
            'ExecStart=/usr/bin/ssh-keygen -q -t ed25519 -N "" '
            "-f /etc/ssh/ssh_host_ed25519_key",
            helper,
        )
        verification = function(self.source, "verify_persistent_root")
        self.assertIn(
            'verify_exact_regular "$root/usr/bin/ssh-keygen" 0 0 755 526688',
            verification,
        )
        self.assertIn(
            "e238ce08e1a4fa0d9d8fe5022e47bf9a841de23370b043c457e13f45e9d90d4e",
            verification,
        )
        self.assertIn(
            "HostKey /etc/ssh/ssh_host_ed25519_key", verification
        )
        runtime = function(self.source, "prepare_runtime")
        self.assertIn("prepare_volatile_systemd_state", runtime)
        self.assertIn("/newroot /mnt/root-ro /mnt/state/upper /run", runtime)
        self.assertIn("DefaultDependencies=no", runtime)
        self.assertIn("Wants=rog5-early-sshd.service", runtime)
        self.assertIn("WantedBy=sysinit.target", runtime)
        self.assertIn("sysinit.target.wants/rog5-p2-ready.service", runtime)

        result, base = self.run_volatile_state()
        assert base is not None
        self.assertEqual(result.returncode, 0, result.stderr)
        for subtree in ("etc", "var"):
            marker = base / "root" / subtree / ".updated"
            upper_marker = base / "upper" / subtree / ".updated"
            self.assertTrue(marker.is_file())
            self.assertTrue(upper_marker.is_file())
            self.assertEqual(marker.stat().st_size, 0)
            self.assertEqual(
                marker.stat().st_mtime_ns,
                (base / "root" / "usr").stat().st_mtime_ns,
            )
            self.assertFalse((base / "lower" / subtree / ".updated").exists())
        mask = (
            base
            / "run"
            / "systemd"
            / "system"
            / "systemd-vconsole-setup.service"
        )
        self.assertTrue(mask.is_symlink())
        self.assertEqual(mask.readlink(), Path("/dev/null"))
        keygen_mask = (
            base / "run" / "systemd" / "system" / "sshdgenkeys.service"
        )
        self.assertTrue(keygen_mask.is_symlink())
        self.assertEqual(keygen_mask.readlink(), Path("/dev/null"))
        stock_sshd_mask = (
            base / "run" / "systemd" / "system" / "sshd.service"
        )
        self.assertTrue(stock_sshd_mask.is_symlink())
        self.assertEqual(stock_sshd_mask.readlink(), Path("/dev/null"))
        key_unit = (
            base
            / "run"
            / "systemd"
            / "system"
            / "rog5-sshd-ed25519-key.service"
        )
        self.assertEqual(
            key_unit.read_text(),
            "[Unit]\n"
            "Description=Generate one volatile Ed25519 SSH host key\n"
            "DefaultDependencies=no\n"
            "Before=rog5-early-sshd.service\n"
            "ConditionPathExists=!/etc/ssh/ssh_host_ed25519_key\n"
            "\n"
            "[Service]\n"
            "Type=oneshot\n"
            'ExecStart=/usr/bin/ssh-keygen -q -t ed25519 -N "" '
            "-f /etc/ssh/ssh_host_ed25519_key\n",
        )
        early_sshd = (
            base / "run" / "systemd" / "system" / "rog5-early-sshd.service"
        )
        self.assertEqual(
            early_sshd.read_text(),
            "[Unit]\n"
            "Description=Start strict SSH before the general Arch boot transaction\n"
            "DefaultDependencies=no\n"
            "Requires=rog5-sshd-ed25519-key.service\n"
            "After=rog5-sshd-ed25519-key.service\n"
            "Before=basic.target\n"
            "\n"
            "[Service]\n"
            "ExecStart=/usr/bin/sshd -D\n"
            "KillMode=process\n"
            "Restart=on-failure\n"
            "RestartSec=2s\n"
            "RuntimeDirectory=sshd\n"
            "RuntimeDirectoryMode=0755\n"
            "\n"
            "[Install]\n"
            "WantedBy=sysinit.target\n",
        )
        early_wants = (
            base
            / "run"
            / "systemd"
            / "system"
            / "sysinit.target.wants"
            / "rog5-early-sshd.service"
        )
        self.assertTrue(early_wants.is_symlink())
        self.assertEqual(early_wants.readlink(), Path("../rog5-early-sshd.service"))
        self.assertEqual(key_unit.stat().st_mode & 0o777, 0o644)
        self.assertEqual(early_sshd.stat().st_mode & 0o777, 0o644)

    def test_volatile_systemd_state_rejects_hostile_inputs(self) -> None:
        for mutation in (
            "wrong-cache",
            "linked-cache",
            "lower-marker",
            "upper-marker",
            "keygen-mask",
            "ed25519-unit",
            "stock-sshd-mask",
            "early-sshd-unit",
            "early-sshd-wants",
        ):
            with self.subTest(mutation=mutation):
                result, _base = self.run_volatile_state(mutation)
                self.assertNotEqual(result.returncode, 0, result.stderr)

    def test_local_root_stages_are_fixed_receive_only_heartbeats(self) -> None:
        reporter = function(self.source, "start_stage_reporter")
        sender = function(self.source, "send_stage_record")
        one_shot = function(self.source, "report_current_stage_once")
        publisher = function(self.source, "publish_stage")
        self.assertIn("send_stage_record", reporter)
        self.assertIn("nc -n -w 1 -s 169.254.77.2", sender)
        self.assertIn("169.254.77.1 8079", sender)
        self.assertIn('send_stage_record <"$stage_record"', one_shot)
        self.assertIn('sleep 1', reporter)
        self.assertIn('format=rog5-persistent-root-stage-v2', publisher)
        self.assertIn('"sequence=$stage_sequence"', publisher)
        self.assertIn('"detail=$stage_detail"', publisher)
        self.assertIn('stage_detail=${3:-none}', publisher)
        self.assertIn('[ "${#stage_detail}" -le 128 ]', publisher)
        for transport in (reporter, sender, one_shot):
            self.assertNotIn("-l", transport)
            self.assertNotIn("sh -c", transport)
            self.assertNotIn("eval", transport)

        ordered = (
            "kernel-verified",
            "ufs-ready",
            "storage-locked",
            "userdata-resolved",
            "userdata-mount",
            "image-resolved",
            "image-write",
            "image-mount",
            "root-verify",
            "ufs-health",
            "overlay",
            "runtime",
            "final-storage",
            "switch-root",
        )
        positions = []
        for stage in ordered:
            position = self.source.find(f"publish_or_rollback {stage} ")
            if position < 0:
                position = self.source.find(f"publish_stage {stage} ")
            self.assertGreaterEqual(position, 0, stage)
            positions.append(position)
        self.assertEqual(positions, sorted(positions))
        self.assertIn("publish_or_rollback root-verify ENTER", self.source)
        self.assertIn("publish_or_rollback root-verify PASS", self.source)
        fail_local = function(self.source, "fail_local_stage")
        self.assertIn('publish_stage "$1" FAIL', fail_local)
        self.assertIn("fail_local_stage root-verify", self.source)

        final_publish = self.source.index(
            "publish_or_rollback switch-root ENTER"
        )
        handoff = self.source.index("if ! handoff_persistent_root; then")
        self.assertLess(final_publish, handoff)
        self.assertIn("sleep 2", self.source[final_publish:handoff])

    def run_rendezvous(
        self, carrier: str
    ) -> tuple[subprocess.CompletedProcess[str], str, list[str]]:
        with tempfile.TemporaryDirectory() as tmp:
            calls = Path(tmp) / "calls"
            sleeps = Path(tmp) / "sleeps"
            script = (
                "set -u\n"
                + self.rendezvous
                + '\ncall_log="$1"\nsleep_log="$2"\ncarrier="$3"\n'
                + 'cat() { printf x >>"$call_log"; printf "%s\\n" "$carrier"; }\n'
                + 'sleep() { printf "%s\\n" "$1" >>"$sleep_log"; }\n'
                + "wait_for_deferred_ufs_rendezvous\n"
            )
            result = subprocess.run(
                ["sh", "-c", script, "sh", str(calls), str(sleeps), carrier],
                text=True,
                capture_output=True,
                check=False,
            )
            return (
                result,
                calls.read_text() if calls.exists() else "",
                sleeps.read_text().splitlines() if sleeps.exists() else [],
            )

    def test_deferred_ufs_rendezvous_is_stable_and_bounded(self) -> None:
        ready, calls, sleeps = self.run_rendezvous("1")
        self.assertEqual(ready.returncode, 0, ready.stderr)
        self.assertEqual(len(calls), 10)
        self.assertEqual(sleeps, ["0.1"] * 9 + ["3"])

        absent, calls, sleeps = self.run_rendezvous("0")
        self.assertNotEqual(absent.returncode, 0)
        self.assertEqual(len(calls), 150)
        self.assertEqual(sleeps, ["0.1"] * 150)


if __name__ == "__main__":
    unittest.main(verbosity=2)
