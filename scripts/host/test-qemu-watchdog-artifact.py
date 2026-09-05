#!/usr/bin/env python3
"""Offline archive-selection regressions. Mocked guest logs are never QEMU proof."""
import contextlib
import gzip
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import runpy
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

REPO = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "watchdog_handoff", Path(__file__).with_name("test-qemu-watchdog-handoff.py"))
M = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(M)
ARCHIVE = runpy.run_path(str(REPO / "scripts/device/build-native-wifi-boot-initramfs.py"))
SOURCE = (REPO / "initramfs/persistent-root-init").read_bytes()
RUN = subprocess.run


def members(init=SOURCE):
    target = {}
    if init is not None:
        ARCHIVE["add"](target, "init", init, stat.S_IFREG | 0o755)
    return target


def altered_init():
    before = b'./initramfs/lib/ld-musl-aarch64.so.1 ./initramfs/bin/busybox "$@"'
    assert SOURCE.count(before) == 1
    return SOURCE.replace(before, b"return 43 # ARCHIVE_ONLY_WATCHDOG")


class WatchdogArtifactTest(unittest.TestCase):
    def test_exact_archive_bytes_and_behavior_not_repository(self):
        init = altered_init()
        start = init.index(b"watchdog_bb() {\n")
        expected = init[start:init.index(b"physical_topology_count() {\n", start)]
        with mock.patch.object(M, "REPO", Path("/nonexistent-repository")):
            block = M.watchdog_functions(members(init))
        self.assertEqual(block.encode(), expected)
        self.assertNotEqual(block, M.watchdog_functions(members()))
        # Execute only our harmless changed function, never archive init.
        result = RUN(["/bin/sh", "-c", block + "\nwatchdog_bb\n"], timeout=5)
        self.assertEqual(result.returncode, 43)

    def test_missing_init_refuses_without_source_fallback(self):
        with self.assertRaisesRegex(ValueError, "missing init.*no repository-source fallback"):
            M.watchdog_functions(members(None))

    def test_invalid_init_member_metadata(self):
        for mode, links in ((stat.S_IFLNK | 0o777, 1), (stat.S_IFDIR | 0o755, 1),
                            (stat.S_IFREG | 0o644, 1), (stat.S_IFREG | 0o755, 2)):
            target = members()
            target["init"][0][1] = mode
            target["init"][0][4] = links
            with self.subTest(mode=mode, links=links), self.assertRaisesRegex(
                    ValueError, "single-link executable regular file"):
                M.watchdog_functions(target)

    def test_legacy_disarm_style_refused_even_with_new_functions(self):
        for init in (b"#!/bin/sh\narm_watchdog() { :; }\ndisarm_watchdog() { :; }\n",
                     SOURCE + b"\ndisarm_watchdog\n"):
            with self.subTest(init=init[:40]), self.assertRaisesRegex(
                    ValueError, "legacy disarm-style.*no repository-source fallback"):
                M.watchdog_functions(members(init))

    def test_missing_duplicate_and_malformed_boundaries(self):
        for name in (b"watchdog_bb", b"watchdog_acknowledged", b"watchdog_expired",
                     b"arm_watchdog", b"physical_topology_count"):
            for init in (SOURCE.replace(name + b"() {\n", name + b"_missing() {\n"),
                         SOURCE + b"\n" + name + b"() {\n :\n}\n",
                         SOURCE.replace(name + b"() {\n", name + b"() { ")):
                with self.subTest(name=name), self.assertRaisesRegex(
                        ValueError, "missing, duplicate or malformed"):
                    M.watchdog_functions(members(init))

    def test_bad_order_and_shell_syntax_refused(self):
        reordered = SOURCE.replace(b"watchdog_bb()", b"TEMP()")
        reordered = reordered.replace(b"watchdog_expired()", b"watchdog_bb()")
        reordered = reordered.replace(b"TEMP()", b"watchdog_expired()")
        for init, error in ((reordered, "function order"),
                            (SOURCE.replace(b"watchdog_bb() {\n", b"watchdog_bb() {\nif\n"),
                             "malformed shell syntax"),
                            (SOURCE + b"\nif\n", "malformed shell syntax"),
                            (SOURCE + b"\xff", "invalid UTF-8"),
                            (SOURCE + b"\0", "malformed shell text"),
                            (SOURCE.replace(b"\n", b"\r\n"), "malformed shell text")):
            with self.subTest(error=error), self.assertRaisesRegex(ValueError, error):
                M.watchdog_functions(members(init))

    def test_cli_refuses_bad_archive_before_output_kernel_or_qemu(self):
        fixtures = (b"not gzip", bytes.fromhex("1f8b080000000000000307"),
                    gzip.compress(b"not newc"),
                    gzip.compress(ARCHIVE["encode"](members(None))),
                    gzip.compress(ARCHIVE["encode"](members(b"#!/bin/sh\n: \n"))),
                    gzip.compress(ARCHIVE["encode"](members(SOURCE + b"\ndisarm_watchdog\n"))))
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            archive = root / "input.cpio.gz"
            output = root / "must-not-exist"
            for blob in fixtures:
                archive.write_bytes(blob)
                argv = ["handoff", "--target-archive", str(archive), "--kernel",
                        str(root / "missing-kernel"), "--output", str(output)]
                with self.subTest(blob=blob[:10]), mock.patch.object(sys, "argv", argv), \
                        mock.patch.object(M.subprocess, "run") as run, \
                        mock.patch.object(M.subprocess, "check_output") as inspect, \
                        contextlib.redirect_stderr(io.StringIO()) as stderr:
                    with self.assertRaises(SystemExit) as refusal:
                        M.main()
                    self.assertEqual(refusal.exception.code, 2)
                    self.assertIn("target archive refused", stderr.getvalue())
                    run.assert_not_called()
                    inspect.assert_not_called()
                    self.assertFalse(output.exists())

    def test_mocked_harness_embeds_archive_block_and_records_provenance(self):
        init = altered_init()
        target = members(init)
        for name in ("bin/busybox", "lib/ld-musl-aarch64.so.1",
                     "usr/libexec/rog5-reboot-bootloader"):
            ARCHIVE["add"](target, name, b"offline fixture: " + name.encode(),
                           stat.S_IFREG | 0o755)
        blob = gzip.compress(ARCHIVE["encode"](target), mtime=0)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            archive, kernel, output = root / "target.gz", root / "Image", root / "output"
            archive.write_bytes(blob)
            kernel.write_bytes(b"offline kernel fixture, never booted")
            runtime = root / "artifacts/qemu-systemd-arm64-v1/runtime.cpio.gz"
            runtime.parent.mkdir(parents=True)
            runtime.write_bytes(gzip.compress(ARCHIVE["encode"]({})))
            # Intentionally different source exists beside the supplied archive.
            source = root / "initramfs/persistent-root-init"
            source.parent.mkdir()
            source.write_bytes(SOURCE)
            seen = []

            def simulated_run(command, **kwargs):
                if command == ["/bin/sh", "-n"]:
                    return RUN(command, **kwargs)
                if command[0] == "podman":
                    mode = Path(kwargs["stdout"].name).stem
                    seen.append(mode)
                    log = "HANDOFF_SWITCH_ROOT\nHANDOFF_NEW_INIT\nHANDOFF_OLD_PATH_GONE\n"
                    if mode == "systemd-ack":
                        log += ("watchdog acknowledged by current-boot P2 readiness\n"
                                "HANDOFF_OBSERVATION_END\n")
                    elif mode == "failed-init":
                        log += "can't execute '/missing-init'\nKernel panic\n"
                    else:
                        log += ("HANDOFF_ARM_FAILED_ROLLBACK\nsysrq: Resetting\n"
                                "reboot: Restarting system with command 'bootloader'\n")
                    kwargs["stdout"].write(log.encode())
                else:
                    self.assertTrue(command[0].endswith("verify-qemu-systemd-runtime.sh"))
                return subprocess.CompletedProcess(command, 0)

            argv = ["handoff", "--kernel", str(kernel), "--target-archive", str(archive),
                    "--output", str(output)]
            with mock.patch.object(M, "REPO", root), mock.patch.object(sys, "argv", argv), \
                    mock.patch.object(M.runpy, "run_path", return_value=ARCHIVE), \
                    mock.patch.object(M.subprocess, "run", side_effect=simulated_run), \
                    mock.patch.object(M.subprocess, "check_output", return_value="offline-image"), \
                    contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(M.main(), 0)
            self.assertEqual(len(seen), 7)
            block = M.watchdog_functions(target).encode()
            for mode in seen:
                guest = ARCHIVE["entries"](gzip.decompress((output / (mode + ".cpio.gz")).read_bytes()))
                self.assertIn(block, guest["init"][1])
                self.assertEqual(guest["init"][1].count(b"ARCHIVE_ONLY_WATCHDOG"), 1)
                for name in ("bin/busybox", "lib/ld-musl-aarch64.so.1",
                             "usr/libexec/rog5-reboot-bootloader"):
                    self.assertEqual(guest[name][1], target[name][1])
            record = json.loads((output / "result.json").read_text())
            self.assertEqual(record["watchdog_source_origin"], "target-archive:init")
            for key, data in (("target_init_sha256", init), ("target_archive_sha256", blob),
                              ("watchdog_source_sha256", block)):
                self.assertEqual(record[key], hashlib.sha256(data).hexdigest())
            self.assertIn("not full deployed composition", record["scope"])


if __name__ == "__main__":
    unittest.main()
