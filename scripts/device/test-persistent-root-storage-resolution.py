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
        discovery = self.source.index(
            "\nlog 'waiting for stable UFS discovery'\n"
        )
        self.assertLess(watchdog, usb)
        self.assertLess(usb, command_line)
        self.assertLess(command_line, release)
        self.assertLess(usb, discovery)


if __name__ == "__main__":
    unittest.main(verbosity=2)
