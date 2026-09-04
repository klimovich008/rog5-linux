#!/usr/bin/env python3
"""Offline boot-watchdog acknowledgement contracts; no devices or mounts."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[2]
INIT = REPO / "initramfs/persistent-root-init"
BOOT = "01234567-89ab-cdef-0123-456789abcdef"


def function(source, name):
    start = source.index(name + "() {\n")
    return source[start:source.index("\n}\n", start) + 3]


class BootWatchdog(unittest.TestCase):
    def test_retained_helper_failure_still_tries_pre_handoff_helper(self):
        source = function(INIT.read_text(), "watchdog_expired")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            helper = root / "reboot-fixture"
            helper.write_text("#!/bin/sh\necho ABSOLUTE_HELPER_TRIED\nexit 1\n")
            helper.chmod(0o755)
            retained = root / "initramfs" / str(helper).lstrip("/")
            retained.parent.mkdir(parents=True)
            retained.write_text("#!/rog5-test-missing-interpreter\n")
            retained.chmod(0o755)
            script = source + '''
watchdog_acknowledged() { return 1; }
reboot_helper=$1
watchdog_expired 8>log 9>sysrq
'''
            result = subprocess.run(["sh", "-c", script, "sh", str(helper)],
                cwd=root, capture_output=True, text=True)
            self.assertIn("ABSOLUTE_HELPER_TRIED", result.stdout)
            self.assertEqual((root / "sysrq").read_text(), "b")

    def test_fd_open_failure_returns_to_rollback_caller(self):
        source = function(INIT.read_text(), "arm_watchdog")
        with tempfile.TemporaryDirectory() as tmp:
            script = source + '''
watchdog_kmsg="$1/missing/kmsg"
watchdog_sysrq="$1/sysrq"
arm_watchdog || exit 77
exit 78
'''
            result = subprocess.run(["sh", "-c", script, "sh", tmp],
                capture_output=True, text=True)
            self.assertEqual(result.returncode, 77, result.stderr)

    def test_handoff_does_not_disarm_before_successor_exec(self):
        source = INIT.read_text()
        tail = source[source.index("publish_or_rollback switch-root ENTER"):]
        self.assertNotIn("disarm_watchdog", tail)
        self.assertIn("exec switch_root /newroot /sbin/init", tail)

    def test_attestation_binds_acknowledgement_to_current_boot(self):
        source = (REPO / "initramfs/persistent-root-attest").read_text()
        final = source[source.index("temporary=/run/.rog5-p2-ready."):]
        self.assertIn('"attested_boot_id=$current_boot_id"', final)
        # Historical collectors independently print boot_id before catting
        # this record. Keep the attested identity distinct from that sample.
        self.assertNotIn('"boot_id=$current_boot_id"', final)

    def test_acknowledgement_validation(self):
        source = function(INIT.read_text(), "watchdog_acknowledged")
        valid = f"status=PASS\nattested_boot_id={BOOT}\nssh=strict-key-only\n"
        cases = {
            "valid": (valid, 0o444, "0:0", 0),
            "stale": (valid.replace(BOOT, "0" * 36), 0o444, "0:0", 1),
            "failed": (valid.replace("PASS", "FAIL"), 0o444, "0:0", 1),
            "duplicate-boot": (valid + f"attested_boot_id={BOOT}\n", 0o444, "0:0", 1),
            "conflicting-status": (valid + "status=FAIL\n", 0o444, "0:0", 1),
            "writable": (valid, 0o644, "0:0", 1),
            "wrong-owner": (valid, 0o444, "1000:0", 1),
            "empty": ("", 0o444, "0:0", 1),
            "oversized": (valid + "x" * 4096, 0o444, "0:0", 1),
            "missing": (None, 0o444, "0:0", 1),
            "symlink": (valid, 0o444, "0:0", 1),
            "hardlink": (valid, 0o444, "0:0", 1),
        }
        command_failures = {
            "metadata-error": "stat:-c:%u:%g:%a:%h",
            "size-error": "stat:-c:%s",
            "status-count-error": "grep:-c:^status=",
            "boot-count-error": "grep:-c:^attested_boot_id=",
        }
        cases.update({name: (valid, 0o444, "0:0", 1) for name in command_failures})
        for name, (content, mode, owner, expected) in cases.items():
            with self.subTest(name=name), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                ack = root / "rog5-p2-ready"
                if content is not None:
                    ack.write_text(content)
                    ack.chmod(mode)
                if name == "symlink":
                    ack.rename(root / "other")
                    ack.symlink_to("other")
                elif name == "hardlink":
                    os.link(ack, root / "other")
                # Host fixtures model uid/gid; mode, size, links and contents
                # are real. The full-system replay validates real root ownership.
                script = r'''
watchdog_bb() {
    if [ "$1:$2:$3" = stat:-c:%u:%g:%a:%h ]; then
        printf '%s:%s\n' "$FIXTURE_OWNER" "$(stat -c '%a:%h' "$4")"
    else
        "$@"
    fi
    result=$?
    [ "$FIXTURE_COMMAND_FAILURE" != "$1:$2:$3" ] || return 2
    return "$result"
}
''' + source + "\nwatchdog_acknowledged\n"
                result = subprocess.run(["sh", "-c", script], cwd=root,
                    env={**os.environ, "FIXTURE_OWNER": owner,
                         "FIXTURE_COMMAND_FAILURE": command_failures.get(name, ""),
                         "watchdog_boot_id": BOOT}, capture_output=True, text=True)
                self.assertEqual(result.returncode, expected, result.stderr)


if __name__ == "__main__":
    unittest.main()
