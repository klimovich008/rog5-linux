#!/usr/bin/env python3
"""Offline boot-watchdog acknowledgement contracts; no devices or mounts.

Set ROG5_TEST_BUSYBOX/ROG5_TEST_QEMU to run the reset-path cases under the
target ARM64 busybox ash (its background-job and pipe semantics matter there).
"""
import os
from pathlib import Path
import signal
import subprocess
import tempfile
import time
import unittest

REPO = Path(__file__).resolve().parents[2]
INIT = REPO / "initramfs/persistent-root-init"
BOOT = "01234567-89ab-cdef-0123-456789abcdef"
IDENTITY = ("format=rog5-persistent-ssh-identity-v1\nmode=load\n"
            "fingerprint=SHA256:" + "A" * 43 + "\nidentity_boot_id=" + BOOT + "\n")


def function(source, name):
    start = source.index(name + "() {\n")
    return source[start:source.index("\n}\n", start) + 3]


def target_shell():
    if os.environ.get("ROG5_TEST_BUSYBOX"):
        return [os.environ["ROG5_TEST_QEMU"], os.environ["ROG5_TEST_BUSYBOX"], "sh"]
    return ["sh"]


def unshare_ok():
    return subprocess.run(["unshare", "-rm", "true"], capture_output=True).returncode == 0


BLOCKING_HELPER = "#!/bin/sh\n: >\"$0.started\"\nexec sleep 1000\n"


class ResetPath(unittest.TestCase):
    """A restart2 request that never returns must not hold off SysRq b."""

    def run_group(self, argv, cwd, deadline):
        """Run argv in its own session; the blocked helper keeps running, so
        wait for the shell only and then kill whatever is left."""
        with tempfile.TemporaryFile(mode="w+") as err:
            process = subprocess.Popen(argv, cwd=cwd, stdin=subprocess.DEVNULL,
                                       stdout=subprocess.DEVNULL, stderr=err,
                                       start_new_session=True)
            try:
                code = process.wait(timeout=deadline)
            except subprocess.TimeoutExpired:
                code = None
            finally:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                process.wait()
            err.seek(0)
            return code, err.read()

    def watchdog(self, root, acknowledged, prelude=''):
        source = INIT.read_text()
        helper = root / "helper"
        helper.write_text(BLOCKING_HELPER)
        helper.chmod(0o755)
        (root / "run").mkdir()
        body = "".join(function(source, name) for name in (
            "watchdog_expired", "watchdog_backstop", "arm_watchdog"))
        self.assertEqual(body.count("cd /run ||"), 2)
        body = body.replace("cd /run ||", 'cd "$FIXTURE_RUN" ||')
        script = f"""
set -u
FIXTURE_RUN={root}/run
reboot_helper={helper}
reboot_helper_grace=2
recovery_timeout=1
watchdog_kmsg={root}/kmsg
watchdog_sysrq={root}/sysrq
watchdog_pid_file={root}/watchdog.pid
watchdog_bb() {{ return 127; }}
watchdog_acknowledged() {{ return {0 if acknowledged else 1}; }}
log() {{ :; }}
{body}
arm_watchdog || exit 77
{prelude}
# Wait for the watchdog group (sleep + expiry + backstop).
wait
"""
        return script

    def test_blocked_restart2_is_followed_by_sysrq_after_the_grace(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            script = self.watchdog(root, acknowledged=False)
            code, err = self.run_group(target_shell() + ["-c", script], root, 12)
            # wait never returns while the helper blocks; the group is killed
            # at the deadline. The reset must have come long before.
            self.assertTrue((root / "helper.started").exists(), err)
            self.assertEqual((root / "sysrq").read_text(), "b", err)
            self.assertIn("restart2 did not complete; watchdog emergency reset",
                          (root / "kmsg").read_text())
            self.assertNotIn("watchdog reset requests returned", (root / "kmsg").read_text())
            sysrq_time = (root / "sysrq").stat().st_mtime
            self.assertLess(sysrq_time - (root / "helper.started").stat().st_mtime, 6)

    def test_acknowledged_boot_never_resets(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            script = self.watchdog(root, acknowledged=True)
            code, err = self.run_group(target_shell() + ["-c", script], root, 15)
            self.assertEqual(code, 0, err)
            self.assertEqual((root / "sysrq").read_text(), "")
            self.assertFalse((root / "helper.started").exists())
            self.assertIn("watchdog acknowledged", (root / "kmsg").read_text())

    def test_returning_restart2_resets_at_once(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            script = self.watchdog(root, acknowledged=False)
            (root / "helper").write_text("#!/bin/sh\n: >\"$0.started\"\nexit 1\n")
            code, err = self.run_group(target_shell() + ["-c", script], root, 15)
            self.assertIn("watchdog reset requests returned", (root / "kmsg").read_text(), err)
            self.assertTrue((root / "sysrq").read_text().startswith("b"))

    @unittest.skipUnless(unshare_ok(), "unshare -rm unavailable")
    def test_expiry_after_switch_root_needs_no_dev_null(self):
        # After switch_root the watchdog's root (the old rootfs) has an empty
        # /dev: ash cannot open /dev/null for a background job there. Model
        # it by hiding /dev in a private mount namespace after arming.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            script = self.watchdog(root, acknowledged=False,
                                   prelude="mount -t tmpfs tmpfs /dev || exit 76\n"
                                           "[ ! -e /dev/null ] || exit 75\n")
            code, err = self.run_group(
                ["unshare", "-rm"] + target_shell() + ["-c", script], root, 20)
            self.assertNotIn(code, (75, 76, 77), err)
            self.assertTrue((root / "helper.started").exists(), err)
            self.assertEqual((root / "sysrq").read_text(), "b", err)

    def test_force_rollback_resets_while_restart2_blocks(self):
        source = function(INIT.read_text(), "force_rollback")
        self.assertEqual(source.count("printf b >/proc/sysrq-trigger 2>/dev/null || true"), 1)
        source = source.replace("printf b >/proc/sysrq-trigger 2>/dev/null || true",
                                'printf b >>"$FIXTURE_SYSRQ"; exit 42')
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            helper = root / "helper"
            helper.write_text(BLOCKING_HELPER)
            helper.chmod(0o755)
            script = f"""
set -u
FIXTURE_SYSRQ={root}/sysrq
reboot_helper={helper}
reboot_helper_grace=1
log() {{ printf '%s\\n' "$*" >>{root}/log; }}
{source}
force_rollback
"""
            started = time.monotonic()
            code, err = self.run_group(target_shell() + ["-c", script], root, 15)
            self.assertEqual(code, 42, err)
            self.assertLess(time.monotonic() - started, 10)
            self.assertTrue((root / "helper.started").exists(), err)
            self.assertEqual((root / "sysrq").read_text(), "b")
            self.assertIn("did not complete; forcing emergency reset", (root / "log").read_text())


class BootWatchdog(unittest.TestCase):
    def test_preflight_and_failed_apply_never_publish_identity(self):
        source = (REPO / 'initramfs/persistent-ssh-identity').read_text()
        tail = source[source.index("verify_contract || fail 'identity preflight failed'"):]
        fail = function(source, 'fail').replace('>/dev/kmsg 2>/dev/null', '>/dev/null')
        for failure in ('preflight', 'verify_contract', 'load_identity',
                        'verify_key_pair', 'verify_sshd_listener'):
            with self.subTest(failure=failure), tempfile.TemporaryDirectory() as tmp:
                script = r'''
set -eu
action=apply
[ "$FAILURE" != preflight ] || action=preflight
verify_contract() { identity_mode=load; [ "$FAILURE" != verify_contract ]; }
load_identity() { [ "$FAILURE" != load_identity ]; }
verify_key_pair() { [ "$FAILURE" != verify_key_pair ]; }
verify_sshd_listener() { [ "$FAILURE" != verify_sshd_listener ]; }
runtime_private=fixture-private
runtime_public=fixture-public
fixture_output=$1
publish_identity() { : >"$fixture_output/unexpected-publication"; }
kill() { exit 98; } # No host signals may be reached in these failure cases.
''' + fail + '\n' + tail
                result = subprocess.run(['sh', '-c', script, 'fixture', tmp],
                    env={**os.environ, 'FAILURE': failure}, capture_output=True, text=True)
                self.assertEqual(result.returncode, 0 if failure == 'preflight' else 1,
                                 result.stderr)
                self.assertEqual(list(Path(tmp).iterdir()), [])

    def test_identity_publication_is_current_boot_and_once_only(self):
        source = function((REPO / 'initramfs/persistent-ssh-identity').read_text(),
                          'publish_identity')
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            script = r'''
set -eu
bb() {
    case "$1" in
        cat) printf '%s\n' "$FIXTURE_BOOT" ;;
        chown) : ;; # No host ownership changes; mode/content are real.
        *) "$@" ;;
    esac
}
identity_record=$1/identity.record
identity_mode=load
fingerprint=SHA256:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
''' + source + '\npublish_identity\n'
            for boot, expected in (('invalid', 1), (BOOT, 0), (BOOT, 1)):
                result = subprocess.run(['sh', '-c', script, 'fixture', str(root)],
                    env={**os.environ, 'FIXTURE_BOOT': boot}, capture_output=True, text=True)
                self.assertEqual(result.returncode, expected, result.stderr)
                if boot == 'invalid':
                    self.assertFalse((root / 'identity.record').exists())
                    self.assertFalse((root / 'identity.record.next').exists())
                else:
                    record = root / 'identity.record'
                    self.assertEqual(record.read_text(), IDENTITY)
                    self.assertEqual(record.stat().st_mode & 0o777, 0o444)
                    self.assertFalse((root / 'identity.record.next').exists())

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
                identity = root / "rog5-persistent-ssh-identity.record"
                identity.write_text(IDENTITY)
                identity.chmod(0o444)
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

    def test_p2_without_current_identity_cannot_cancel_rollback(self):
        source = function(INIT.read_text(), "watchdog_acknowledged")
        cases = {
            "missing": (None, 0o444, 1),
            "old-producer": (IDENTITY.split('identity_boot_id=')[0], 0o444, 1),
            "stale": (IDENTITY.replace(BOOT, '0' * 36), 0o444, 1),
            "duplicate-boot": (IDENTITY + f'identity_boot_id={BOOT}\n', 0o444, 1),
            "invalid-mode": (IDENTITY.replace('mode=load', 'mode=unknown'), 0o444, 1),
            "invalid-key": (IDENTITY.replace('SHA256:', 'MD5:'), 0o444, 1),
            "wrong-format": (IDENTITY.replace('-v1', '-v0'), 0o444, 1),
            "extra-field": (IDENTITY + 'result=PASS\n', 0o444, 1),
            "oversized": (IDENTITY + 'x' * 256, 0o444, 1),
            "writable": (IDENTITY, 0o644, 1),
            "wrong-owner": (IDENTITY, 0o444, 1),
            "metadata-error": (IDENTITY, 0o444, 1),
            "symlink": (IDENTITY, 0o444, 1),
            "hardlink": (IDENTITY, 0o444, 1),
            "load-latched": (IDENTITY, 0o444, 0),
            "seed-latched": (IDENTITY.replace('mode=load', 'mode=seed'), 0o444, 0),
        }
        for name, (content, mode, expected) in cases.items():
            with self.subTest(name=name), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                ack = root / 'rog5-p2-ready'
                ack.write_text(f'status=PASS\nattested_boot_id={BOOT}\n')
                ack.chmod(0o444)
                identity = root / 'rog5-persistent-ssh-identity.record'
                if content is not None:
                    identity.write_text(content)
                    identity.chmod(mode)
                if name == 'symlink':
                    identity.rename(root / 'other')
                    identity.symlink_to('other')
                elif name == 'hardlink':
                    os.link(identity, root / 'other')
                script = r'''
watchdog_bb() {
    if [ "$1:$2:$3" = stat:-c:%u:%g:%a:%h ]; then
        if [ "$4" = ./rog5-persistent-ssh-identity.record ]; then
            case "$FIXTURE_IDENTITY_CASE" in
                wrong-owner) printf '1000:0:444:1\n'; return ;;
                metadata-error) printf '0:0:444:1\n'; return 2 ;;
            esac
        fi
        printf '0:0:%s\n' "$(stat -c '%a:%h' "$4")"
    else
        "$@"
    fi
}
# There is no live SSH listener in this fixture. Once published, the valid
# initial-success latch must not turn later SSH downtime into boot rollback.
''' + source + '\nwatchdog_acknowledged\n'
                result = subprocess.run(['sh', '-c', script], cwd=root,
                    env={**os.environ, 'watchdog_boot_id': BOOT,
                         'FIXTURE_IDENTITY_CASE': name},
                    capture_output=True, text=True)
                self.assertEqual(result.returncode, expected, result.stderr)


if __name__ == "__main__":
    unittest.main()
