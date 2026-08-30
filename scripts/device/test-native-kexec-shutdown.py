#!/usr/bin/env python3
"""Replay the exitrd dispatch without mounts, privilege or a reboot syscall."""
from pathlib import Path
import hashlib
import os
import shutil
import subprocess
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[2]
SOURCE = (REPO / "initramfs/persistent-root-shutdown-standalone").read_text()


class NativeKexecShutdown(unittest.TestCase):
    def test_syscall_executor_is_static_and_reproducible(self):
        with tempfile.TemporaryDirectory() as temp:
            paths = [Path(temp) / name for name in ("first", "second")]
            for path in paths:
                subprocess.run(["make", "-s", "-f", str(REPO / "tools/native_kexec/Makefile"),
                                f"OUT={path}"], check=True)
            self.assertEqual(paths[0].read_bytes(), paths[1].read_bytes())
            elf = subprocess.check_output(["readelf", "-l", str(paths[0])], text=True)
            self.assertNotIn("INTERP", elf)
            if shutil.which("qemu-aarch64-static") and os.geteuid() != 0:
                result = subprocess.run(["qemu-aarch64-static", str(paths[0])], timeout=5)
                self.assertEqual(result.returncode, 111)

    def test_teardown_and_fallback_order(self):
        tokens = ["detach_persistent_state || clean=0", "unmount_mount /oldroot || clean=0",
                  "try_native_kexec \"${1:-}\" || true", '"$bb" reboot -f']
        positions = [SOURCE.index(token) for token in tokens]
        self.assertEqual(positions, sorted(positions))
        self.assertEqual(SOURCE.count("\n\t/rog5-kexec-exec\n"), 1)

    def test_dispatch(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            function = SOURCE.split("try_native_kexec() {", 1)[1].split("\n}\n", 1)[0]
            function = "try_native_kexec() {" + function + "\n}\n"
            function = function.replace("/rog5-kexec-exec", f"{root}/rog5-kexec-exec")
            function = function.replace("(cd / &&", f"(cd {root} &&")
            # Coreutils is the unprivileged host applet dispatcher. An exact
            # sealed BusyBox command can also be supplied by the artifact test.
            applet = root / "applets"
            applet.write_text('#!/bin/sh\nexec "$@"\n')
            applet.chmod(0o700)
            driver = root / "driver.sh"
            driver.write_text(f'bb={applet}\nclean=$1\n' + function +
                              'try_native_kexec "$2" || true\necho NORMAL_REBOOT\n')
            executor = root / "rog5-kexec-exec"
            checksum = root / "rog5-kexec-exec.sha256"
            for case in ("return-failure", "return-zero", "reboot", "unclean", "absent",
                         "symlink", "wrong-digest", "digest-absent", "digest-symlink"):
                with self.subTest(case=case):
                    executor.unlink(missing_ok=True)
                    checksum.unlink(missing_ok=True)
                    executor.write_text(f'#!/bin/sh\necho EXECUTE_ONCE\nexit {0 if case == "return-zero" else 111}\n')
                    executor.chmod(0o700)
                    checksum.write_text(hashlib.sha256(executor.read_bytes()).hexdigest() +
                                        "  rog5-kexec-exec\n")
                    if case == "absent":
                        executor.unlink()
                    elif case == "symlink":
                        executor.rename(root / "elsewhere")
                        executor.symlink_to(root / "elsewhere")
                    elif case == "wrong-digest":
                        checksum.write_text("0" * 64 + "  rog5-kexec-exec\n")
                    elif case.startswith("digest-"):
                        checksum.rename(root / "digest-elsewhere")
                        if case.endswith("symlink"):
                            checksum.symlink_to(root / "digest-elsewhere")
                    result = subprocess.run(["sh", str(driver), "0" if case == "unclean" else "1",
                                             "reboot" if case == "reboot" else "kexec"],
                                            capture_output=True, text=True, check=True)
                    self.assertEqual(result.stdout.count("EXECUTE_ONCE"),
                                     1 if case.startswith("return-") else 0)
                    self.assertTrue(result.stdout.endswith("NORMAL_REBOOT\n"))


if __name__ == "__main__":
    unittest.main()
