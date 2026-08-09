#!/usr/bin/env python3
"""Hostile tests for the fallback ramoops transition preflight."""

from __future__ import annotations

from contextlib import redirect_stderr
import importlib.util
import io
import os
import shutil
from pathlib import Path
import struct
import subprocess
import tempfile
import unittest


REPO = Path(__file__).resolve().parents[2]
HELPER = REPO / "scripts/host/reboot-fallback-to-fastboot.sh"
BEGIN = "# BEGIN FALLBACK_RAMOOPS_TRANSITION_VERIFIER\n"
END = "# END FALLBACK_RAMOOPS_TRANSITION_VERIFIER\n"
RESERVED = "sys/firmware/devicetree/base/reserved-memory"


def verifier_source() -> str:
    source = HELPER.read_text(encoding="utf-8")
    try:
        return source.split(BEGIN, 1)[1].split(END, 1)[0]
    except IndexError as error:
        raise AssertionError("fallback ramoops verifier is absent") from error


class FallbackRamoopsTransitionPreflightTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name) / "root"
        self.verifier = Path(self.temporary.name) / "verifier.py"
        self.verifier.write_text(verifier_source(), encoding="utf-8")
        self.build_fixture()

    def write_property(self, relative: str, payload: bytes) -> Path:
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
        return path

    def build_fixture(self) -> None:
        shutil.rmtree(self.root, ignore_errors=True)
        self.write_property(
            "proc/cmdline",
            (
                b"console=ttyMSM0,115200n8 "
                b"ramoops.mem_address=0x9b800000 "
                b"ramoops.mem_size=0x400000 "
                b"ramoops.record_size=0x100000 "
                b"ramoops.console_size=0x300000 "
                b"ramoops.pmsg_size=0 "
                b"ramoops.ftrace_size=0 "
                b"ramoops.dump_oops=1\n"
            ),
        )
        reserved = RESERVED
        self.write_property(f"{reserved}/#address-cells", struct.pack(">I", 2))
        self.write_property(f"{reserved}/#size-cells", struct.pack(">I", 2))
        self.write_property(f"{reserved}/ranges", b"")
        self.write_property(
            f"{reserved}/memory@9b800000/reg",
            struct.pack(">QQ", 0x9B800000, 0x400000),
        )
        self.write_property(
            f"{reserved}/other@a0000000/reg",
            struct.pack(">QQ", 0xA0000000, 0x100000),
        )
        for relative in (
            "sys/bus/platform/devices",
            "sys/bus/platform/drivers",
            "sys/devices/platform",
            "sys/fs/pstore",
            "mnt/pstore",
        ):
            (self.root / relative).mkdir(parents=True, exist_ok=True)

    def run_verifier(self) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["python3", str(self.verifier), str(self.root)],
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

    def load_verifier_module(self, module_name: str) -> object:
        module_path = Path(self.temporary.name) / f"{module_name}.py"
        module_path.write_text(verifier_source(), encoding="utf-8")
        spec = importlib.util.spec_from_file_location(module_name, module_path)
        if spec is None or spec.loader is None:
            self.fail("cannot load extracted fallback verifier")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def assert_module_rejected(self, module: object, message: str) -> None:
        stderr = io.StringIO()
        with (
            redirect_stderr(stderr),
            self.assertRaisesRegex(SystemExit, "1"),
        ):
            module.main([str(self.root)])
        self.assertIn(message, stderr.getvalue())

    def assert_rejected(self, message: str) -> None:
        result = self.run_verifier()
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertIn(message, result.stderr)

    def test_exact_transition_reservation_passes(self) -> None:
        before = self.tree_identity()
        result = self.run_verifier()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            result.stdout,
            "PASS fallback ramoops transition reservation is exact, "
            "unconsumed, and empty\n",
        )
        self.assertEqual(self.tree_identity(), before)

    def tree_identity(self) -> tuple[tuple[str, str, int, bytes | str], ...]:
        entries = []
        for path in sorted(self.root.rglob("*")):
            metadata = path.lstat()
            relative = path.relative_to(self.root).as_posix()
            mode = metadata.st_mode & 0o7777
            if path.is_symlink():
                entries.append((relative, "symlink", mode, os.readlink(path)))
            elif path.is_file():
                entries.append((relative, "file", mode, path.read_bytes()))
            else:
                entries.append((relative, "directory", mode, b""))
        return tuple(entries)

    def test_command_line_missing_duplicate_and_unknown_tokens_fail(self) -> None:
        cmdline = self.root / "proc/cmdline"
        baseline = cmdline.read_text(encoding="ascii")
        cases = {
            "missing": baseline.replace("ramoops.dump_oops=1", ""),
            "duplicate": baseline + "ramoops.mem_size=0x400000\n",
            "unknown": baseline + "ramoops.ecc=1\n",
            "wrong": baseline.replace("0x400000", "0x200000", 1),
        }
        for name, payload in cases.items():
            with self.subTest(name=name):
                self.build_fixture()
                cmdline = self.root / "proc/cmdline"
                cmdline.write_text(payload, encoding="ascii")
                self.assert_rejected("fallback ramoops command line is not exact")

    def test_reserved_memory_shape_and_exact_tuple_fail_closed(self) -> None:
        reserved = self.root / RESERVED
        cases = ("address-cells", "size-cells", "ranges", "reg", "missing")
        for name in cases:
            with self.subTest(name=name):
                self.build_fixture()
                reserved = self.root / RESERVED
                if name == "address-cells":
                    (reserved / "#address-cells").write_bytes(struct.pack(">I", 1))
                elif name == "size-cells":
                    (reserved / "#size-cells").write_bytes(struct.pack(">I", 1))
                elif name == "ranges":
                    (reserved / "ranges").write_bytes(b"not-empty")
                elif name == "reg":
                    (reserved / "memory@9b800000/reg").write_bytes(
                        struct.pack(">QQ", 0x9B800000, 0x200000)
                    )
                else:
                    shutil.rmtree(reserved / "memory@9b800000")
                self.assert_rejected("fallback ramoops reserved-memory contract")

    def test_overlap_overflow_multiple_tuple_and_boundaries(self) -> None:
        cases = {
            "inside": ((0x9B900000, 0x100000),),
            "encloses": ((0x9B700000, 0x600000),),
            "multiple": ((0xA1000000, 0x1000), (0x9BB00000, 0x200000)),
        }
        for name, ranges in cases.items():
            with self.subTest(name=name):
                self.build_fixture()
                payload = b"".join(struct.pack(">QQ", *item) for item in ranges)
                self.write_property(f"{RESERVED}/overlap/reg", payload)
                self.assert_rejected("fallback reserved-memory node overlaps ramoops")

        for name, size in (("past-limit", 0x2000), ("at-limit", 0x1000)):
            with self.subTest(name=name):
                self.build_fixture()
                self.write_property(
                    f"{RESERVED}/overflow/reg",
                    struct.pack(">QQ", 0xFFFFFFFFFFFFF000, size),
                )
                self.assert_rejected("fallback reserved-memory child is malformed")

        for name, start in (
            ("adjacent-before", 0x9B700000),
            ("adjacent-after", 0x9BC00000),
        ):
            with self.subTest(name=name):
                self.build_fixture()
                size = 0x100000
                self.write_property(
                    f"{RESERVED}/{name}/reg",
                    struct.pack(">QQ", start, size),
                )
                result = self.run_verifier()
                self.assertEqual(result.returncode, 0, result.stderr)

    def test_malformed_or_symlinked_reserved_child_is_rejected(self) -> None:
        reserved = self.root / RESERVED
        malformed = reserved / "malformed"
        malformed.mkdir()
        (malformed / "reg").write_bytes(b"short")
        self.assert_rejected("fallback reserved-memory child is malformed")

        self.build_fixture()
        reserved = self.root / RESERVED
        target = reserved / "memory@9b800000"
        outside = self.root / "outside-ramoops"
        target.rename(outside)
        target.symlink_to(outside, target_is_directory=True)
        self.assert_rejected("fallback reserved-memory child is malformed")

        self.build_fixture()
        reserved = self.root / RESERVED
        (reserved / "broken-child").symlink_to(reserved / "absent")
        self.assert_rejected("fallback reserved-memory child is malformed")

    def test_bound_consumer_is_rejected(self) -> None:
        cases = (
            "sys/bus/platform/devices/ramoops",
            "sys/devices/platform/ramoops",
        )
        for relative in cases:
            with self.subTest(relative=relative):
                self.build_fixture()
                (self.root / relative).mkdir()
                self.assert_rejected("fallback ramoops consumer is present")

        self.build_fixture()
        driver = self.root / "sys/bus/platform/drivers/ramoops"
        driver.mkdir()
        device = self.root / "sys/bus/platform/devices/ramoops.0"
        device.mkdir()
        (driver / "ramoops.0").symlink_to(device, target_is_directory=True)
        self.assert_rejected("fallback ramoops consumer is present")

        self.build_fixture()
        driver = self.root / "sys/bus/platform/drivers/ramoops"
        driver.symlink_to(self.root / "absent-driver", target_is_directory=True)
        self.assert_rejected("fallback ramoops driver is unsafe or absent")

        for relative in (
            "sys/bus/platform/devices/9b800000.ramoops",
            "sys/devices/platform/soc:ramoops",
        ):
            with self.subTest(relative=relative):
                self.build_fixture()
                (self.root / relative).mkdir()
                self.assert_rejected("fallback ramoops consumer is present")

        self.build_fixture()
        self.write_property(
            f"{RESERVED}/logger@a1000000/reg",
            struct.pack(">QQ", 0xA1000000, 0x100000),
        )
        self.write_property(
            f"{RESERVED}/logger@a1000000/compatible",
            b"ramoops\0",
        )
        self.assert_rejected("fallback ramoops consumer is present")

    def test_missing_and_replaced_runtime_paths_fail_closed(self) -> None:
        shutil.rmtree(self.root / "sys/bus/platform/devices")
        self.assert_rejected("fallback platform devices is unsafe or absent")

        self.build_fixture()
        module = self.load_verifier_module("fallback_verifier")
        original = module.read_regular_at
        replaced = False

        def replace_reserved(*args: object, **kwargs: object) -> object:
            nonlocal replaced
            if (
                not replaced
                and len(args) >= 3
                and args[2] == "fallback reserved-memory address cells"
            ):
                replaced = True
                reserved = self.root / RESERVED
                moved = reserved.with_name("reserved-memory-opened")
                reserved.rename(moved)
                shutil.copytree(moved, reserved)
            return original(*args, **kwargs)

        module.read_regular_at = replace_reserved
        self.assert_module_rejected(
            module,
            "fallback reserved-memory contract changed during verification",
        )

        self.build_fixture()
        changing_module = self.load_verifier_module("changing_fallback_verifier")
        original_names = changing_module.directory_names
        changed = False

        def add_consumer_after_snapshot(
            directory: int,
            label: str,
        ) -> tuple[str, ...]:
            nonlocal changed
            names = original_names(directory, label)
            if not changed and label == "fallback platform devices":
                changed = True
                (self.root / "sys/bus/platform/devices/9b800000.ramoops").mkdir()
            return names

        changing_module.directory_names = add_consumer_after_snapshot
        self.assert_module_rejected(
            changing_module,
            "fallback platform devices changed during verification",
        )

    def test_optional_absence_inventories_are_revalidated(self) -> None:
        module = self.load_verifier_module("changing_reserved_child")
        original_read = module.read_regular_at
        changed = False

        def add_compatible_after_absence(
            directory: int,
            name: str,
            label: str,
            *,
            optional: bool = False,
        ) -> bytes | None:
            nonlocal changed
            result = original_read(
                directory,
                name,
                label,
                optional=optional,
            )
            if (
                not changed
                and label == "fallback reserved-memory compatible"
                and result is None
            ):
                changed = True
                self.write_property(
                    f"{RESERVED}/memory@9b800000/compatible",
                    b"ramoops\0",
                )
            return result

        module.read_regular_at = add_compatible_after_absence
        self.assert_module_rejected(
            module,
            "fallback reserved-memory child changed during verification",
        )

        self.build_fixture()
        module = self.load_verifier_module("changing_driver_inventory")
        original_names = module.directory_names
        changed = False

        def add_driver_after_snapshot(
            directory: int,
            label: str,
        ) -> tuple[str, ...]:
            nonlocal changed
            names = original_names(directory, label)
            if not changed and label == "fallback platform drivers":
                changed = True
                (self.root / "sys/bus/platform/drivers/ramoops").mkdir()
            return names

        module.directory_names = add_driver_after_snapshot
        self.assert_module_rejected(
            module,
            "fallback platform drivers changed during verification",
        )

        self.build_fixture()
        shutil.rmtree(self.root / "mnt/pstore")
        module = self.load_verifier_module("changing_mount_inventory")
        original_names = module.directory_names
        changed = False

        def add_mount_after_snapshot(
            directory: int,
            label: str,
        ) -> tuple[str, ...]:
            nonlocal changed
            names = original_names(directory, label)
            if not changed and label == "fallback mount root":
                changed = True
                (self.root / "mnt/pstore").mkdir()
            return names

        module.directory_names = add_mount_after_snapshot
        self.assert_module_rejected(
            module,
            "fallback mount root changed during verification",
        )

    def test_any_pstore_entry_or_unsafe_directory_is_rejected(self) -> None:
        (self.root / "sys/fs/pstore/console-ramoops-0").write_bytes(b"retained")
        self.assert_rejected("fallback pstore is not empty")

        self.build_fixture()
        pstore = self.root / "sys/fs/pstore"
        outside = self.root / "outside-pstore"
        pstore.rename(outside)
        pstore.symlink_to(outside, target_is_directory=True)
        self.assert_rejected("fallback pstore is unsafe or absent")

    def test_helper_exposes_read_only_retention_action(self) -> None:
        source = HELPER.read_text(encoding="utf-8")
        self.assertIn("retention-preflight)", source)
        self.assertIn(
            "PASS exact fallback ramoops retention preflight",
            source,
        )
        retention_case = source.split("retention-preflight)", 1)[1].split(
            ";;", 1
        )[0]
        self.assertNotIn("ALLOW_FALLBACK_BOOTLOADER_REBOOT", retention_case)
        action = source.split(
            'if [ "$action" = retention-preflight ]; then\n', 1
        )[1].split("\nfi\n", 1)[0]
        prefix, remainder = action.split("\tpython3 -B - / <<'PY'\n", 1)
        _python, suffix = remainder.split("\nPY\n", 1)
        self.assertEqual(prefix, "")
        self.assertEqual(
            suffix,
            "\techo 'PASS exact fallback ramoops retention preflight'\n"
            "\texit 0",
        )
        reboot_guard = (
            '[ "$action" = reboot ] || '
            "fail 'non-reboot action reached reboot boundary'"
        )
        self.assertIn(reboot_guard, source)
        self.assertLess(source.index(reboot_guard), source.index("LINUX_REBOOT_MAGIC1"))
        guard_result = subprocess.run(
            [
                "sh",
                "-c",
                "action=retention-preflight; "
                "fail() { echo \"$1\" >&2; exit 97; }; "
                f"{reboot_guard}; echo REBOOT_REACHED",
            ],
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        self.assertEqual(guard_result.returncode, 97)
        self.assertNotIn("REBOOT_REACHED", guard_result.stdout)
        verifier = verifier_source()
        for mutation in (
            "O_WRONLY",
            "O_RDWR",
            "write_bytes",
            "write_text",
            "unlink(",
            "rename(",
            "replace(",
        ):
            with self.subTest(mutation=mutation):
                self.assertNotIn(mutation, verifier)


if __name__ == "__main__":
    unittest.main(verbosity=2)
