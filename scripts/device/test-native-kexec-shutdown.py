#!/usr/bin/env python3
"""Replay the exitrd dispatch without mounts, privilege or a reboot syscall."""
from pathlib import Path
import hashlib
import os
import pty
import re
import select
import signal
import shlex
import shutil
import subprocess
import tempfile
import termios
import unittest

REPO = Path(__file__).resolve().parents[2]
SOURCE = (REPO / "initramfs/persistent-root-shutdown-standalone").read_text()


class NativeKexecShutdown(unittest.TestCase):
    def test_exitrd_log_bounds_interruptible_gadget_close_wait(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            master, slave = pty.openpty()
            self.addCleanup(os.close, master)
            self.addCleanup(os.close, slave)
            binary = root / 'logger'
            subprocess.run(['cc', '-std=c11', '-O2',
                            '-DROG5_EXITRD_LOG_DEVICE="' + os.ttyname(slave) + '"',
                            str(REPO / 'tools/native_kexec/rog5-exitrd-log.c'),
                            '-o', str(binary)], check=True)
            shim = root / 'close.c'
            shim.write_text('''#define _GNU_SOURCE
#include <dlfcn.h>
#include <poll.h>
#include <unistd.h>
int close(int fd) {
    int (*real_close)(int) = dlsym(RTLD_NEXT, "close");
    if (isatty(fd)) poll(0, 0, 15000);
    return real_close(fd);
}
''')
            library = root / 'close.so'
            subprocess.run(['cc', '-shared', '-fPIC', str(shim), '-ldl', '-o', str(library)], check=True)
            # Model u_serial's interruptible 15s close wait, including an
            # inherited ignored/blocked SIGALRM. The helper must reset both.
            def inherited_alarm():
                signal.signal(signal.SIGALRM, signal.SIG_IGN)
                signal.pthread_sigmask(signal.SIG_BLOCK, {signal.SIGALRM})
            subprocess.run([str(binary), 'close-wait-test'],
                           env={**os.environ, 'LD_PRELOAD': str(library)},
                           preexec_fn=inherited_alarm,
                           check=True, timeout=1)

    def test_exitrd_serial_log_is_bounded_nonblocking_and_advisory(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            master, slave = pty.openpty()
            self.addCleanup(os.close, master)
            self.addCleanup(os.close, slave)
            device = os.ttyname(slave)
            def build(name, path):
                binary = root / name
                subprocess.run(['cc', '-std=c11', '-O2', '-Wall', '-Wextra', '-Werror',
                                '-DROG5_EXITRD_LOG_DEVICE="' + str(path) + '"',
                                str(REPO / 'tools/native_kexec/rog5-exitrd-log.c'),
                                '-o', str(binary)], check=True, timeout=20)
                return binary
            binary = build('log-tty', device)
            subprocess.run([str(binary), 'native-kexec enter'], check=True, timeout=1)
            actual = termios.tcgetattr(slave)
            self.assertFalse(actual[1] & termios.OPOST)
            self.assertFalse(actual[3] & termios.ECHO)
            self.assertTrue(select.select([master], [], [], 1)[0])
            self.assertEqual(os.read(master, 512), b'ROG5_EXITRD native-kexec enter\n')
            for message in ('', 'x' * 256, 'injected\nline', '\tcontrol'):
                subprocess.run([str(binary), message], check=True, timeout=1)
                self.assertFalse(select.select([master], [], [], 0)[0])
            # Fill the tty output buffer without a reader; the logger must return.
            os.set_blocking(slave, False)
            with self.assertRaises(BlockingIOError):
                while True:
                    os.write(slave, b'x' * 4096)
            subprocess.run([str(binary), 'must not wait'], check=True, timeout=1)
            regular = root / 'regular'
            regular.write_text('unchanged')
            link = root / 'link'
            link.symlink_to(regular)
            for name, path in (('regular', regular), ('symlink', link),
                               ('missing', root / 'missing')):
                subprocess.run([str(build('log-' + name, path)), 'ignored'], check=True, timeout=1)
            self.assertEqual(regular.read_text(), 'unchanged')
            self.assertFalse((root / 'missing').exists())

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
                self.assertEqual(result.returncode, 1)  # Non-root reboot: EPERM.

    @unittest.skipUnless(shutil.which("qemu-aarch64-static"), "qemu-user unavailable")
    def test_syscall_return_status_bounds(self):
        source = (REPO / "tools/native_kexec/rog5-kexec-exec.c").read_text()
        reboot_call = '__asm__ volatile("svc #0" : "+r"(x0)'
        self.assertEqual(source.count(reboot_call), 1)
        # Replace only the reboot instruction with a register assignment. The
        # production conversion and exit syscall still run; no reboot is issued.
        cases = ((-1, 1), (-22, 22), (-125, 125), (-126, 111), (-4095, 111),
                 (-4096, 111), (0, 111), (1, 111), (125, 111), (126, 111))
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for returned, expected in cases:
                with self.subTest(returned=returned):
                    fixture = root / f"return-{returned}.c"
                    binary = root / f"return-{returned}"
                    fixture.write_text(source.replace(
                        reboot_call, f'__asm__ volatile("mov x0, #{returned}" : "+r"(x0)', 1))
                    subprocess.run([
                        "make", "-s", "-f", str(REPO / "tools/native_kexec/Makefile"),
                        f"SOURCE={fixture}", f"OUT={binary}"], check=True, timeout=20)
                    result = subprocess.run(["qemu-aarch64-static", str(binary)], timeout=5)
                    self.assertEqual(result.returncode, expected)

    def test_teardown_and_fallback_order(self):
        tokens = ["detach_persistent_state || mark_unclean detach", "unmount_mount /oldroot || mark_unclean",
                  "try_native_kexec \"${1:-}\" || true", '"$bb" reboot -f']
        positions = [SOURCE.index(token) for token in tokens]
        self.assertEqual(positions, sorted(positions))
        self.assertEqual(len(re.findall(
            r'^\s*(?:if\s+)?/rog5-kexec-exec(?:\s|;|$)', SOURCE, re.MULTILINE)), 1)

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
            driver.write_text(f'bb={shlex.quote(str(applet))}\nclean=$1\n' +
                              'log() { printf "%s\\n" "$*"; }\n' + function +
                              'try_native_kexec "$2" || true\necho NORMAL_REBOOT\n')
            executor = root / "rog5-kexec-exec"
            checksum = root / "rog5-kexec-exec.sha256"
            return_statuses = (0, 1, 22, 111, 125, 126, 127, 255)
            skip_reasons = {
                "reboot": "action", "unclean": "unclean", "absent": "executor",
                "symlink": "executor", "non-executable": "executor",
                "wrong-digest": "digest-mismatch", "digest-absent": "digest-missing",
                "digest-symlink": "digest-missing",
            }
            cases = tuple(f"return-{status}" for status in return_statuses) + tuple(skip_reasons)
            for case in cases:
                with self.subTest(case=case):
                    executor.unlink(missing_ok=True)
                    checksum.unlink(missing_ok=True)
                    status = int(case.removeprefix("return-")) if case.startswith("return-") else 111
                    executor.write_text(f'#!/bin/sh\necho EXECUTE_ONCE\nexit {status}\n')
                    executor.chmod(0o700)
                    checksum.write_text(hashlib.sha256(executor.read_bytes()).hexdigest() +
                                        "  rog5-kexec-exec\n")
                    if case == "absent":
                        executor.unlink()
                    elif case == "symlink":
                        executor.rename(root / "elsewhere")
                        executor.symlink_to(root / "elsewhere")
                    elif case == "non-executable":
                        executor.chmod(0o600)
                    elif case == "wrong-digest":
                        checksum.write_text("0" * 64 + "  rog5-kexec-exec\n")
                    elif case.startswith("digest-"):
                        checksum.rename(root / "digest-elsewhere")
                        if case.endswith("symlink"):
                            checksum.symlink_to(root / "digest-elsewhere")
                    result = subprocess.run(["sh", str(driver), "0" if case == "unclean" else "1",
                                             "reboot" if case == "reboot" else "kexec"],
                                            capture_output=True, text=True, check=True, timeout=5)
                    self.assertEqual(result.stdout.count("EXECUTE_ONCE"),
                                     1 if case.startswith("return-") else 0)
                    self.assertTrue(result.stdout.endswith("NORMAL_REBOOT\n"))
                    records = [line for line in result.stdout.splitlines()
                               if line.startswith("native-kexec ") or
                               line in ("EXECUTE_ONCE", "NORMAL_REBOOT")]
                    expected = (["native-kexec enter", "EXECUTE_ONCE",
                                 f"native-kexec returned status={status}", "NORMAL_REBOOT"]
                                if case.startswith("return-") else
                                [f"native-kexec skip={skip_reasons[case]}", "NORMAL_REBOOT"])
                    self.assertEqual(records, expected)

    def test_top_level_teardown_calculates_clean_before_dispatch(self):
        # Replay the real top-level control flow, not a preselected clean flag.
        # Override every teardown helper and the applet dispatcher before use.
        start = "\nlog 'discarding volatile root before standalone restart'\n"
        definitions, separator, body = SOURCE.partition(start)
        self.assertTrue(separator)
        body, separator, _ = body.partition(
            "\nlog 'normal restart returned; triggering emergency reset'\n")
        self.assertTrue(separator)
        # The mocked normal reboot exits the shell. Exclude emergency reset and
        # sleep entirely so a harness mistake cannot touch sysrq or wait forever.
        body = start + body + "\nexit 99\n"
        operations = (
            "move /oldroot/.rog5/root-ro /oldsys/root-ro",
            "move /oldroot/.rog5/userdata-ro /oldsys/userdata-ro",
            "move /oldroot/.rog5/state /oldsys/state",
            *(f"move /oldroot/{api} /oldsys/{api}" for api in ("sys", "proc", "run", "dev")),
            "detach",
            "unmount /oldroot", "unmount /oldsys/state",
            "unmount /oldsys/root-ro", "unmount /oldsys/userdata-ro",
        )
        mocks = r'''
bb=mock_bb
failed_operation=$2
log() { printf '%s\n' "$*"; }
operation() {
    printf 'OP %s\n' "$*"
    [ "$*" != "$failed_operation" ]
}
move_mount() { operation move "$1" "$2"; }
unmount_mount() { operation unmount "$1"; }
detach_persistent_state() { operation detach; }
lazy_unmount() { printf 'LAZY %s\n' "$1"; }
mock_bb() {
    case "$*" in
        'mount -o remount,rw /'|'mkdir -p /oldsys') return 0 ;;
        'mountpoint -q /dev') return 1 ;;
        'mount -t devtmpfs devtmpfs /dev') printf 'API_DEV\n'; return 0 ;;
        'sha256sum -c rog5-kexec-exec.sha256') command "$@" ;;
        'reboot -f')
            printf 'FINAL_CLEAN=%s\nNORMAL_REBOOT\n' "$clean"
            exit 0 ;;
        *) printf 'UNEXPECTED_APPLET %s\n' "$*" >&2; exit 98 ;;
    esac
}
'''
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            executor = root / "rog5-kexec-exec"
            executor.write_text('#!/bin/sh\necho EXECUTE_ONCE\nexit 111\n')
            executor.chmod(0o700)
            logger = root / 'rog5-exitrd-log'
            logger.write_text('#!/bin/sh\nexit 0\n')
            logger.chmod(0o700)
            (root / "rog5-kexec-exec.sha256").write_text(
                hashlib.sha256(executor.read_bytes()).hexdigest() + "  rog5-kexec-exec\n")
            replay = definitions + "\n" + mocks + body
            replay = replay.replace("/rog5-kexec-exec", str(executor))
            replay = replay.replace("/rog5-exitrd-log", str(logger))
            replay = replay.replace("(cd / &&", f"(cd {shlex.quote(str(root))} &&")
            driver = root / "teardown.sh"
            driver.write_text(replay)
            for failure in ("", *operations):
                with self.subTest(failure=failure or "all-clean"):
                    result = subprocess.run(["sh", str(driver), "kexec", failure],
                                            capture_output=True, text=True, check=True, timeout=5)
                    lines = result.stdout.splitlines()
                    self.assertEqual([line.removeprefix("OP ") for line in lines
                                      if line.startswith("OP ")], list(operations))
                    self.assertEqual(lines.count("EXECUTE_ONCE"), 0 if failure else 1)
                    self.assertEqual(lines.count("NORMAL_REBOOT"), 1)
                    self.assertEqual(lines.count("API_DEV"), 1)
                    self.assertEqual(lines[-2:], [f"FINAL_CLEAN={0 if failure else 1}",
                                                 "NORMAL_REBOOT"])
                    self.assertEqual(
                        "clean teardown incomplete; detaching residual mounts" in lines,
                        bool(failure))
                    self.assertEqual([line for line in lines if line.startswith("teardown failed=")],
                                     [f"teardown failed={failure}"] if failure else [])


if __name__ == "__main__":
    unittest.main()
