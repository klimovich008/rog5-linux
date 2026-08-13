#!/usr/bin/env python3
"""Hostile fixtures for name-independent persistent-root storage and UDC selection."""

from __future__ import annotations

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
        size: str = "476106392",
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

    def test_usb_observability_precedes_target_identity_and_ufs(self) -> None:
        watchdog = self.source.index("\narm_watchdog\n")
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
        self.assertIn("verify_only_userdata_mount", mount_function)
        self.assertIn("verify_physical_storage_read_only", mount_function)

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
