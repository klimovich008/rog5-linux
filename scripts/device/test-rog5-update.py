#!/usr/bin/env python3
"""Tests for unattended package updates: the init's snapshot restore and the
rog5-update tool (run, commit, verify-root) on fake roots.

Everything runs under `unshare -r`, so temporary files are owned by uid 0 as
on the phone. pacman, systemctl, sshd and the other system tools the updater
calls are stubs that log their calls. The init functions are extracted from
initramfs/persistent-root-init; set ROG5_TEST_BUSYBOX/ROG5_TEST_QEMU to run
them under the target ARM64 busybox.

The pinned hashes of the SSH policy and the lower ld.so.cache are swapped for
fixture hashes in temporary copies of both scripts (same sizes as the pins).
"""
import hashlib
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[2]
INIT = REPO/'initramfs/persistent-root-init'
UPDATE = REPO/'initramfs/rog5-update'
UNITS = ('rog5-update.service', 'rog5-update.timer', 'rog5-update-commit.service')
BOOT = '0d5c1d8e-2a4f-4b61-9d0e-3f1a2b3c4d5e'
BOOT2 = '1e6d2e9f-3b5a-4c72-8e1f-4a2b3c4d5e6f'
UID = '20260926T031500Z-1a2b3c4d'
ORIGINAL_PIN = 'c6b01ef801333ee11bb8805a250df2c4f02f38f0015df1449dadb66490e43693'
VOLATILE_PIN = '37372388916a09c2457c3bf612de9bfe9b5bcba0fe9e01d1e3aa5b98dc903db1'
CACHE_PIN = 'ae57b0740e33f19b3f748bdf8e159a65ecfb828f1339f093d91ec9ef4b8e89ed'
POLICY_LINES = ('HostKey /etc/ssh/ssh_host_ed25519_key\nPasswordAuthentication no\n'
                'PermitRootLogin prohibit-password\nPubkeyAuthentication yes\n')
POLICY = (POLICY_LINES + '#' * (200 - len(POLICY_LINES)) + '\n').encode()
VOLATILE = POLICY + b'UsePAM no\n'
CACHE = b'ld.so-1.7.0' + b'\0' * 20196
MARKER = ('# This file was created by systemd-update-done. The timestamp below is the\n'
          '# modification time of /usr/ for which the most recent updates of /{} have\n'
          '# been applied. See man:systemd-update-done.service(8) for details.\n'
          'TIMESTAMP_NSEC=1790000000000000000\n')
OLD_MARKER = ('# This file was created by systemd-update-done. Its only \n'
              '# purpose is to hold a timestamp of the time this directory\n'
              '# was updated. See man:systemd-update-done.service(8).\n'
              'TIMESTAMP_NSEC=1790000000000000000\n')
TEMPLATE = (b'\0# This file was created by systemd-update-done. The timestamp below is the\n'
            b'# modification time of /usr/ for which the most recent updates of %s have\n'
            b'# been applied. See man:systemd-update-done.service(8) for details.\n'
            b'TIMESTAMP_NSEC=%lu\n\0')
SSHD_T = ('port 22\npasswordauthentication no\npermitrootlogin without-password\n'
          'pubkeyauthentication yes\nkbdinteractiveauthentication no\nusepam no\n')
PLAN = 'openssh 10.1p1-1\nsystemd 262-1\n'
INSTALLED = 'openssh 10.0p1-1\nsystemd 261.3-1\n'
APPLETS = ('awk', 'cat', 'chmod', 'chown', 'cmp', 'cp', 'cut', 'find', 'grep', 'ln', 'mkdir', 'mv',
           'readlink', 'rm', 'sed', 'sha256sum', 'sort', 'stat', 'sync', 'touch', 'wc')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def unshare_ok():
    return subprocess.run(['unshare', '-r', 'true'], capture_output=True).returncode == 0


def function(text, name):
    match = re.search(rf'^{name}\(\) \{{\n.*?^\}}\n', text, re.M | re.S)
    assert match, name
    return match.group(0)


def patched(text, replacements):
    for old, new in replacements:
        assert text.count(old) >= 1, old
        text = text.replace(old, new)
    return text


PINS = ((ORIGINAL_PIN, sha(POLICY)), (VOLATILE_PIN, sha(VOLATILE)))
INIT_FUNCTIONS = ('update_record_exact', 'update_pending_fields', 'update_restoring_fields',
                  'write_update_record', 'update_tree_names', 'verify_update_snapshot',
                  'restore_update_snapshot', 'apply_update_rollback', 'verify_exact_regular',
                  'prepare_volatile_root_account', 'prepare_volatile_ssh_policy',
                  'verify_systemd_update_marker', 'prepare_volatile_systemd_state')


def init_library(logfile):
    text = INIT.read_text()
    body = ''.join(function(text, name) for name in INIT_FUNCTIONS)
    body = patched(body, PINS + ((CACHE_PIN, sha(CACHE)), ('expected_cache_size=20207', f'expected_cache_size={len(CACHE)}')))
    return (f'set -u\ntarget_boot_id=${{TEST_BOOT_ID:-{BOOT}}}\nexpected_persistent_overlay_mode=1\n'
            f'expected_ssh_diagnostic_mode=0\nlog() {{ printf "%s\\n" "$*" >>{logfile}; }}\n' + body)


class Base(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(prefix='rog5-update-'))
        d = self.dir
        self.bin, self.root, self.lower, self.state = d/'bin', d/'root', d/'lower', d/'state'
        self.run, self.sys, self.proc = d/'run', d/'sys', d/'proc'
        self.upper = self.state/'upper'
        for path in (self.bin, self.run, self.proc/'sys/kernel/random', self.proc/'net', self.upper,
                     self.state/'work', self.sys/'class/backlight/panel',
                     self.sys/'class/power_supply/qcom-battmgr-bat', self.sys/'class/power_supply/qcom-battmgr-usb'):
            path.mkdir(parents=True, exist_ok=True)
        self.upper.chmod(0o755)
        self.shell, self.env = ['sh'], dict(os.environ)
        if os.environ.get('ROG5_TEST_BUSYBOX'):
            qemu, busybox = os.environ['ROG5_TEST_QEMU'], os.environ['ROG5_TEST_BUSYBOX']
            applets = d/'applets'
            applets.mkdir()
            for name in APPLETS:
                (applets/name).write_text(f'#!/bin/sh\nexec {qemu} {busybox} {name} "$@"\n')
                (applets/name).chmod(0o755)
            self.shell, self.env['PATH'] = [qemu, busybox, 'sh'], f'{applets}:{os.environ["PATH"]}'
        self.make_root()
        self.make_system()

    def tearDown(self):
        subprocess.run(['chmod', '-R', 'u+w', str(self.dir)])
        shutil.rmtree(self.dir)

    def write(self, path, data, mode=0o644):
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists() or path.is_symlink():
            path.unlink()
        if isinstance(data, str):
            data = data.encode()
        path.write_bytes(data)
        path.chmod(mode)

    def make_root(self):
        """A merged root that passes every check, its lower and its upper."""
        for base in (self.root, self.lower):
            self.write(base/'etc/ssh/sshd_config.d/10-rog5-server.conf', POLICY)
            self.write(base/'etc/ld.so.cache', CACHE)
        self.write(self.lower/'etc/shadow', 'root:!*:19000::::::\nbin:!*:19000::::::\n', 0o600)
        (self.lower/'var').mkdir(exist_ok=True)
        self.write(self.root/'etc/shadow', 'root:x:19000::::::\nbin:!*:19000::::::\n', 0o600)
        self.write(self.root/'etc/ssh/sshd_config.d/10-rog5-server.conf', VOLATILE)
        for subtree in ('etc', 'var'):
            for base in (self.root, self.upper):
                self.write(base/subtree/'.updated', MARKER.format(subtree + '/'))
        systemd = self.root/'usr/lib/systemd'
        self.write(systemd/'systemd', '#!/bin/sh\nexit 0\n', 0o755)
        self.write(systemd/'systemd-update-done', TEMPLATE, 0o755)
        (self.root/'sbin').mkdir()
        (self.root/'sbin/init').symlink_to('../lib/systemd/systemd')
        (self.root/'lib').symlink_to('usr/lib')
        self.write(self.root/'usr/bin/sshd', '#!/bin/sh\n', 0o755)
        for suffix in ('.gpg', '-trusted', '-revoked'):
            self.write(self.root/f'usr/share/pacman/keyrings/archlinuxarm{suffix}', 'key\n')
        self.write(self.root/'etc/ssh/ssh_host_ed25519_key', 'private\n', 0o600)
        self.write(self.root/'etc/ssh/ssh_host_ed25519_key.pub', 'ssh-ed25519 AAAA root\n')
        (self.root/'var/lib/pacman').mkdir(parents=True)
        (self.root/'var/cache/pacman/pkg').mkdir(parents=True)
        self.write(self.upper/'etc/pacman.conf', 'upper-v1\n')
        self.write(self.upper/'usr/bin/tool', 'old\n', 0o755)

    def stub(self, name, body):
        self.write(self.bin/name, f'#!/bin/sh\nD={self.dir}\n{body}\n', 0o755)

    def make_system(self):
        d = self.dir
        for tool in ('blkid', 'findmnt', 'dmesg', 'ip', 'gpg'):
            self.stub(tool, 'exit 0')
        self.stub('sshd', f'''case "$1" in -t) exit 0 ;; -T) cat $D/sshd-T 2>/dev/null || printf '{SSHD_T}' ;; esac''')
        self.stub('ssh-keygen', '''case "$*" in
	"-y -f "*) echo "ssh-ed25519 AAAA" ;;
	"-E sha256 -lf "*) echo "256 SHA256:abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQ root (ED25519)" ;;
	*) exit 1 ;;
esac''')
        self.stub('systemctl', '''echo "systemctl $*" >>$D/calls
case "$1" in
	is-active) [ ! -e $D/keyring-inactive ] ;;
	reboot) [ ! -e $D/reboot-fails ] ;;
	*) exit 0 ;;
esac''')
        self.stub('pacman', '''echo "pacman $*" >>$D/calls
case "$*" in
	"-V") exit 0 ;;
	"-Q") cat $D/installed ;;
	"-Sy --noconfirm") exit "$(cat $D/sy-rc 2>/dev/null || echo 0)" ;;
	"-Su --print"*) cat $D/plan ;;
	"-S --needed --noconfirm archlinuxarm-keyring"|"-Su --noconfirm"*)
		case "$*" in -Su*) [ ! -x $D/effect ] || $D/effect ;; esac
		[ ! -f $D/new-installed ] || cp $D/new-installed $D/installed
		exit "$(cat $D/su-rc 2>/dev/null || echo 0)" ;;
	*) exit 2 ;;
esac''')
        self.write(d/'installed', INSTALLED)
        self.write(d/'plan', '')
        self.write(self.proc/'sys/kernel/random/boot_id', BOOT + '\n')
        self.write(self.proc/'net/route', 'Iface\tDestination\tGateway\tFlags\tRefCnt\tUse\tMetric\tMask\n'
                   'wlan0\t00000000\t0101A8C0\t0003\t0\t0\t600\t00000000\t0\t0\t0\n')
        self.write(self.proc/'net/tcp', '  sl  local_address rem_address   st\n'
                   '  0: 00000000:0016 00000000:0000 0A 00000000:00000000 00:00000000 00000000 0 0 1\n')
        self.write(d/'mounts', f'overlay / overlay rw,relatime,lowerdir=/mnt/root-ro,upperdir=/mnt/state/upper,'
                   f'workdir=/mnt/state/work 0 0\n/dev/loop5 {self.state} ext4 rw,nosuid,nodev,noatime 0 0\n')
        self.write(self.sys/'class/backlight/panel/brightness', '0\n')
        battery, usb = self.sys/'class/power_supply/qcom-battmgr-bat', self.sys/'class/power_supply/qcom-battmgr-usb'
        self.write(battery/'type', 'Battery\n')
        self.write(battery/'capacity', '80\n')
        self.write(battery/'temp', '300\n')
        self.write(usb/'type', 'USB\n')
        self.write(usb/'online', '0\n')
        for disk, ro in (('sda', 0), ('sda23', 0), ('sda24', 1)):
            self.write(self.sys/'class/block'/disk/'ro', f'{ro}\n')
        script = patched(UPDATE.read_text(), PINS)
        self.update = d/'rog5-update'
        self.write(self.update, script, 0o755)

    # -- running

    def rollback(self, boot=BOOT):
        """The init's apply_update_rollback on the fake overlay filesystem."""
        script = init_library(self.dir/'init.log') + f'apply_update_rollback {self.state}\n'
        env = dict(self.env, TEST_BOOT_ID=boot)
        return subprocess.run(['unshare', '-r', *self.shell, '-c', script], capture_output=True,
                              text=True, env=env, timeout=300).returncode

    def updater(self, action, **extra):
        env = dict(os.environ, PATH=f'{self.bin}:{os.environ["PATH"]}', ROG5_UPDATE_ROOT=str(self.root),
                   ROG5_UPDATE_LOWER=str(self.lower), ROG5_UPDATE_STATE=str(self.state),
                   ROG5_UPDATE_RUN=str(self.run), ROG5_UPDATE_SYS=str(self.sys),
                   ROG5_UPDATE_PROC=str(self.proc), ROG5_UPDATE_MOUNTS=str(self.dir/'mounts'),
                   ROG5_UPDATE_KMSG=str(self.dir/'kmsg'), ROG5_UPDATE_RESERVE_MIB='1', ROG5_UPDATE_WAIT='2',
                   ROG5_UPDATE_INHIBIT_CMD='')
        env.update(extra)
        result = subprocess.run(['unshare', '-r', 'sh', str(self.update), action], capture_output=True,
                                text=True, env=env, timeout=120)
        self.output = result.stdout
        return result.returncode

    def kmsg(self):
        path = self.dir/'kmsg'
        return path.read_text() if path.exists() else ''

    def calls(self):
        path = self.dir/'calls'
        return path.read_text().splitlines() if path.exists() else []

    def reboots(self):
        return self.calls().count('systemctl reboot')

    # -- state helpers

    @property
    def udir(self):
        return self.state/'rog5-update'

    def record(self, name, lines, mode=0o444):
        self.udir.mkdir(mode=0o700, exist_ok=True)
        self.write(self.udir/name, ''.join(line + '\n' for line in lines), mode)

    def pending(self, action='verify', uid=UID):
        self.record('pending', ['format=rog5-update-pending-v1', f'update_id={uid}', f'action={action}'])

    def fields(self, name):
        return dict(line.split('=', 1) for line in (self.udir/name).read_text().splitlines())

    def snapshot(self, uid=UID, tamper=False):
        """A sealed snapshot of an older upper (what rog5-update run makes)."""
        base = self.state/'snapshots'
        base.mkdir(mode=0o700, exist_ok=True)
        snap = base/uid
        snap.mkdir(mode=0o700)
        copy = snap/'upper'
        copy.mkdir(mode=0o755)
        self.write(copy/'etc/pacman.conf', 'upper-v0\n')
        self.write(copy/'usr/bin/tool', 'older\n', 0o755)
        for subtree in ('etc', 'var'):
            self.write(copy/subtree/'.updated', MARKER.format(subtree + '/'))
        names = subprocess.run(f'cd {copy} && find . -mindepth 1 | LC_ALL=C sort', shell=True,
                               capture_output=True, text=True, check=True).stdout
        self.write(snap/'seal', f'format=rog5-overlay-snapshot-v1\nupdate_id={uid}\n'
                   f'entries={len(names.splitlines())}\nnames_sha256={sha(names.encode())}\n', 0o444)
        if tamper:
            self.write(copy/'extra', 'x\n')
        return snap


@unittest.skipUnless(unshare_ok(), 'user namespaces are unavailable')
class InitRollback(Base):
    def test_no_update_state_is_a_no_op(self):
        self.assertEqual(self.rollback(), 0)
        self.assertEqual((self.upper/'etc/pacman.conf').read_text(), 'upper-v1\n')
        self.assertFalse(self.udir.exists())

    def test_first_boot_records_one_attempt_and_keeps_the_update(self):
        self.snapshot()
        self.pending()
        self.assertEqual(self.rollback(), 0)
        self.assertEqual(self.fields('attempt'), {'format': 'rog5-update-attempt-v1', 'update_id': UID, 'boot_id': BOOT})
        self.assertEqual(oct((self.udir/'attempt').stat().st_mode & 0o777), '0o444')
        self.assertEqual((self.upper/'etc/pacman.conf').read_text(), 'upper-v1\n')
        self.assertTrue((self.udir/'pending').exists())

    def test_second_boot_without_commit_restores_the_snapshot(self):
        snap = self.snapshot()
        self.pending()
        self.assertEqual(self.rollback(), 0)
        self.assertEqual(self.rollback(BOOT2), 0)
        self.assertEqual((self.upper/'etc/pacman.conf').read_text(), 'upper-v0\n')
        self.assertEqual((self.upper/'usr/bin/tool').read_text(), 'older\n')
        self.assertEqual((snap/'failed-upper/etc/pacman.conf').read_text(), 'upper-v1\n')
        self.assertFalse((snap/'upper').exists())
        self.assertEqual(self.fields('last-result'), {'format': 'rog5-update-result-v1', 'update_id': UID,
                                                      'result': 'rolled-back', 'reason': 'boot-not-committed',
                                                      'boot_id': BOOT2})
        for name in ('pending', 'attempt', 'restoring'):
            self.assertFalse((self.udir/name).exists(), name)
        self.assertIn(f'update {UID} rolled back (boot-not-committed)', (self.dir/'init.log').read_text())
        # The restored root boots normally afterwards.
        self.assertEqual(self.rollback(), 0)
        self.assertEqual((self.upper/'etc/pacman.conf').read_text(), 'upper-v0\n')

    def test_requested_restore_happens_on_the_first_boot(self):
        self.snapshot()
        self.pending('restore')
        self.assertEqual(self.rollback(), 0)
        self.assertEqual((self.upper/'etc/pacman.conf').read_text(), 'upper-v0\n')
        self.assertEqual(self.fields('last-result')['reason'], 'restore-requested')

    def test_a_snapshot_that_does_not_match_its_seal_is_never_restored(self):
        snap = self.snapshot(tamper=True)
        self.pending('restore')
        self.assertEqual(self.rollback(), 0)
        self.assertEqual((self.upper/'etc/pacman.conf').read_text(), 'upper-v1\n')
        self.assertTrue((snap/'upper').exists())
        self.assertFalse((snap/'failed-upper').exists())
        self.assertEqual(self.fields('last-result')['result'], 'restore-refused')
        self.assertFalse((self.udir/'pending').exists())
        self.assertFalse((self.udir/'restoring').exists())

    def test_seal_record_and_directory_modes_are_exact(self):
        for label, mutate in (('seal mode', lambda s: (s/'seal').chmod(0o644)),
                              ('snapshot mode', lambda s: s.chmod(0o755)),
                              ('upper mode', lambda s: (s/'upper').chmod(0o700)),
                              ('seal id', lambda s: self.write(s/'seal', (s/'seal').read_text().replace(UID, UID[:-1] + 'e'), 0o444))):
            with self.subTest(label):
                subprocess.run(['chmod', '-R', 'u+w', str(self.state)])
                shutil.rmtree(self.state/'snapshots', ignore_errors=True)
                shutil.rmtree(self.udir, ignore_errors=True)
                snap = self.snapshot()
                mutate(snap)
                self.pending('restore')
                self.assertEqual(self.rollback(), 0)
                self.assertEqual((self.upper/'etc/pacman.conf').read_text(), 'upper-v1\n')
                self.assertEqual(self.fields('last-result')['result'], 'restore-refused')

    def test_inexact_records_are_ignored(self):
        self.snapshot()
        cases = (('mode', ['format=rog5-update-pending-v1', f'update_id={UID}', 'action=restore'], 0o644),
                 ('id', ['format=rog5-update-pending-v1', 'update_id=../../x', 'action=restore'], 0o444),
                 ('action', ['format=rog5-update-pending-v1', f'update_id={UID}', 'action=rm'], 0o444),
                 ('extra line', ['format=rog5-update-pending-v1', f'update_id={UID}', 'action=restore', 'x=y'], 0o444),
                 ('format', ['format=rog5-update-pending-v2', f'update_id={UID}', 'action=restore'], 0o444))
        for label, lines, mode in cases:
            with self.subTest(label):
                self.record('pending', lines, mode)
                self.assertEqual(self.rollback(), 0)
                self.assertEqual((self.upper/'etc/pacman.conf').read_text(), 'upper-v1\n')
                self.assertFalse((self.udir/'attempt').exists())
                self.assertIn('pending record is not exact', (self.dir/'init.log').read_text())
        (self.udir/'pending').unlink()
        (self.udir/'pending').symlink_to('/etc/passwd')
        self.assertEqual(self.rollback(), 0)
        self.assertEqual((self.upper/'etc/pacman.conf').read_text(), 'upper-v1\n')

    def test_an_inexact_state_directory_is_ignored(self):
        self.snapshot()
        self.pending('restore')
        self.udir.chmod(0o755)
        self.assertEqual(self.rollback(), 0)
        self.assertEqual((self.upper/'etc/pacman.conf').read_text(), 'upper-v1\n')
        self.assertIn('update state directory is not exact', (self.dir/'init.log').read_text())

    def journal(self, reason='boot-not-committed'):
        self.record('restoring', ['format=rog5-update-restoring-v1', f'update_id={UID}', f'reason={reason}'])

    def test_a_restore_interrupted_between_renames_is_finished(self):
        snap = self.snapshot()
        self.pending()
        self.journal()
        self.upper.rename(snap/'failed-upper')
        self.assertEqual(self.rollback(), 0)
        self.assertEqual((self.upper/'etc/pacman.conf').read_text(), 'upper-v0\n')
        self.assertEqual(self.fields('last-result')['result'], 'rolled-back')
        self.assertFalse((self.udir/'restoring').exists())
        self.assertFalse((self.udir/'pending').exists())

    def test_a_restore_interrupted_after_its_journal_is_finished(self):
        self.snapshot()
        self.pending()
        self.journal()
        self.assertEqual(self.rollback(), 0)
        self.assertEqual((self.upper/'etc/pacman.conf').read_text(), 'upper-v0\n')

    def test_an_interrupted_restore_with_a_bad_snapshot_puts_the_update_back(self):
        snap = self.snapshot(tamper=True)
        self.pending()
        self.journal()
        self.upper.rename(snap/'failed-upper')
        self.assertEqual(self.rollback(), 0)
        self.assertEqual((self.upper/'etc/pacman.conf').read_text(), 'upper-v1\n')
        self.assertEqual(self.fields('last-result')['result'], 'restore-refused')
        self.assertFalse((self.udir/'restoring').exists())

    def test_an_inexact_journal_stops_the_boot(self):
        self.snapshot()
        self.record('restoring', ['format=rog5-update-restoring-v1', f'update_id={UID}', 'reason=Bad Reason'])
        self.assertNotEqual(self.rollback(), 0)


@unittest.skipUnless(unshare_ok(), 'user namespaces are unavailable')
class VerifyRootMatchesTheBootVerifiers(Base):
    """verify-root must reject every root the init rejects, plus the root
    accounts the P2 attestor rejects (a crypt hash instead of x)."""

    def reset(self):
        subprocess.run(['rm', '-rf', str(self.root), str(self.upper), str(self.lower), str(self.bin)])
        self.upper.mkdir(mode=0o755)
        self.bin.mkdir()
        (self.dir/'sshd-T').unlink(missing_ok=True)
        self.make_root()
        self.make_system()

    def init_accepts(self):
        """(init accepts, P2 attestor accepts the root account the init left)"""
        runtime = self.dir/'runtime'
        shutil.rmtree(runtime, ignore_errors=True)
        (runtime/'systemd/system/sysinit.target.wants').mkdir(parents=True)
        work = self.dir/'init-root'
        subprocess.run(['rm', '-rf', str(work)])
        shutil.copytree(self.root, work, symlinks=True)
        script = init_library(self.dir/'init.log') + (
            f'prepare_volatile_root_account {work} {self.lower} && '
            f'prepare_volatile_ssh_policy {work} {self.lower} && '
            f'prepare_volatile_systemd_state {work} {self.lower} {self.upper} {runtime}\n')
        result = subprocess.run(['unshare', '-r', *self.shell, '-c', script], capture_output=True,
                                text=True, env=self.env, timeout=120)
        if result.returncode:
            return False, False
        return True, re.search(r'^root:x:[0-9]+:{6}$', (work/'etc/shadow').read_text(), re.M) is not None

    def test_matrix(self):
        shadow = self.root/'etc/shadow'
        policy = self.root/'etc/ssh/sshd_config.d/10-rog5-server.conf'
        cache = self.root/'etc/ld.so.cache'
        cases = (
            ('baseline', lambda: None, True),
            ('shadow mode', lambda: shadow.chmod(0o644), False),
            ('shadow crypt hash (attestor)', lambda: shadow.write_text('root:$6$salt$hash:19000::::::\n'), False),
            ('shadow unlocked empty', lambda: shadow.write_text('root::19000::::::\n'), False),
            ('shadow two roots', lambda: shadow.write_text('root:x:19000::::::\nroot:x:1::::::\n'), False),
            ('shadow same as lower', lambda: shadow.write_text('root:!*:19000::::::\n'), True),
            ('shadow extra field', lambda: shadow.write_text('root:x:19000:::::::\n'), False),
            ('policy original', lambda: policy.write_bytes(POLICY), True),
            ('policy edited', lambda: policy.write_bytes(VOLATILE.replace(b'#', b'%', 1)), False),
            ('policy mode', lambda: policy.chmod(0o600), False),
            ('cache mode', lambda: cache.chmod(0o600), False),
            ('cache empty', lambda: cache.write_bytes(b''), False),
            ('cache too large', lambda: cache.write_bytes(b'\0' * 1048577), False),
            ('marker wording', lambda: [p.write_text(OLD_MARKER) for p in (self.root/'etc/.updated', self.upper/'etc/.updated')], False),
            ('marker mismatch', lambda: (self.upper/'var/.updated').write_text(MARKER.format('var/').replace('179', '178')), False),
            ('marker mode', lambda: [p.chmod(0o600) for p in (self.root/'var/.updated', self.upper/'var/.updated')], False),
            ('markers empty', lambda: [p.write_text('') for p in (self.root/'etc/.updated', self.upper/'etc/.updated')], True),
            ('marker only merged', lambda: (self.upper/'etc/.updated').unlink(), False),
        )
        for label, mutate, expected in cases:
            with self.subTest(label):
                self.reset()
                mutate()
                init, attestor = self.init_accepts()
                self.assertEqual(self.updater('verify-root') == 0, init and attestor)
                self.assertEqual(init and attestor, expected)
                # The init alone keeps a user crypt hash; only P2 rejects it.
                self.assertEqual(init, expected or 'attestor' in label)

    def test_absent_markers_are_accepted(self):
        # The init creates both on the overlay; separate fake trees cannot show it.
        for path in (self.root/'etc/.updated', self.upper/'etc/.updated'):
            path.unlink()
        self.assertEqual(self.updater('verify-root'), 0, self.output)

    def test_runtime_checks(self):
        self.assertEqual(self.updater('verify-root'), 0, self.output)
        for label, mutate in (
                ('update-done template', lambda: (self.root/'usr/lib/systemd/systemd-update-done').write_bytes(OLD_MARKER.encode())),
                ('sshd policy', lambda: self.write(self.dir/'sshd-T', SSHD_T.replace('usepam no', 'usepam yes'))),
                ('sshd duplicate', lambda: self.write(self.dir/'sshd-T', SSHD_T + 'usepam no\n')),
                ('broken tool', lambda: self.stub('blkid', 'exit 127')),
                ('systemd binary', lambda: self.write(self.root/'usr/lib/systemd/systemd', '#!/bin/sh\nexit 1\n', 0o755)),
                ('keyring mode', lambda: (self.root/'usr/share/pacman/keyrings/archlinuxarm.gpg').chmod(0o600)),
                ('host key', lambda: self.stub('ssh-keygen', 'echo "256 SHA256:short x"')),
                ('upper mode', lambda: self.upper.chmod(0o700))):
            with self.subTest(label):
                mutate()
                self.assertEqual(self.updater('verify-root'), 1)
                self.assertIn('FAIL verify-root', self.output)
                self.reset()
                self.assertEqual(self.updater('verify-root'), 0, self.output)

    def test_template_with_literal_directories_is_accepted(self):
        (self.root/'usr/lib/systemd/systemd-update-done').write_bytes(
            TEMPLATE.replace(b'%s', b'/etc/') + TEMPLATE.replace(b'%s', b'/var/'))
        self.assertEqual(self.updater('verify-root'), 0, self.output)


@unittest.skipUnless(unshare_ok(), 'user namespaces are unavailable')
class Run(Base):
    def start(self, plan=PLAN, **extra):
        self.write(self.dir/'plan', plan)
        return self.updater('run', **extra)

    def test_up_to_date_takes_no_snapshot(self):
        self.assertEqual(self.start(''), 0, self.kmsg())
        self.assertIn('PASS up to date', self.kmsg())
        self.assertFalse((self.state/'snapshots').exists())
        self.assertTrue((self.udir/'last-check').exists())
        self.assertNotIn('pacman -Su --noconfirm', self.calls())

    def test_verified_update_snapshots_upgrades_and_reboots_when_idle(self):
        self.write(self.dir/'new-installed', PLAN)
        self.assertEqual(self.start(), 0, self.kmsg())
        calls = self.calls()
        self.assertLess(calls.index('pacman -Sy --noconfirm'), calls.index('pacman -Su --noconfirm'))
        pending = self.fields('pending')
        self.assertEqual(pending['action'], 'verify')
        uid = pending['update_id']
        self.assertRegex(uid, r'^[0-9]{8}T[0-9]{6}Z-[0-9a-f]{8}$')
        snap = self.state/'snapshots'/uid
        self.assertEqual((snap/'upper/etc/pacman.conf').read_text(), 'upper-v1\n')
        self.assertFalse((snap/'upper/var/lib/pacman/db.lck').exists())
        self.assertFalse((self.root/'var/lib/pacman/db.lck').exists())
        self.assertEqual(oct(snap.stat().st_mode & 0o777), '0o700')
        self.assertEqual(self.reboots(), 1)
        self.assertEqual((self.udir/'targets').read_text().splitlines()[2:], sorted(PLAN.splitlines()))
        # The init accepts the updater's pending record and seal: the first
        # boot keeps the update, a second uncommitted boot restores upper.
        self.assertEqual(self.rollback(), 0)
        self.assertEqual(self.fields('attempt')['update_id'], uid)
        self.write(self.upper/'etc/pacman.conf', 'upper-v2\n')
        self.assertEqual(self.rollback(BOOT2), 0)
        self.assertEqual((self.upper/'etc/pacman.conf').read_text(), 'upper-v1\n')
        self.assertEqual(self.fields('last-result')['result'], 'rolled-back')

    def test_display_on_defers_the_verification_reboot(self):
        self.write(self.sys/'class/backlight/panel/brightness', '120\n')
        self.assertEqual(self.start(), 0, self.kmsg())
        self.assertEqual(self.fields('pending')['action'], 'verify')
        self.assertEqual(self.reboots(), 0)
        self.assertEqual(self.updater('run'), 0)
        self.assertEqual(self.reboots(), 0)
        self.assertIn('waits for its verify reboot', self.kmsg())
        self.write(self.sys/'class/backlight/panel/brightness', '0\n')
        self.assertEqual(self.updater('run'), 0)
        self.assertEqual(self.reboots(), 1)
        self.assertEqual(self.calls().count('pacman -Su --noconfirm'), 1)

    # /proc/net/tcp rows: sl local rem st ... ; addresses little-endian hex.
    TCP_HEAD = '  sl  local_address rem_address   st tx_queue rx_queue tr tm->when retrnsmt   uid  timeout inode\n'
    SSH_LISTEN = '   0: 00000000:0016 00000000:0000 0A 00000000:00000000 00:00000000 00000000     0        0 1\n'

    def assert_busy_defers_reboot(self, reason, **extra):
        self.assertEqual(self.start(**extra), 0, self.kmsg())
        self.assertEqual(self.fields('pending')['action'], 'verify')
        self.assertEqual(self.reboots(), 0)
        self.assertIn(f'reboot deferred: {reason}', self.kmsg())

    def test_remote_client_defers_the_verification_reboot(self):
        self.write(self.proc/'net/tcp', self.TCP_HEAD + self.SSH_LISTEN +
                   '   1: 5301A8C0:0016 D001A8C0:C350 01 00000000:00000000 00:00000000 00000000     0        0 2\n')
        self.assert_busy_defers_reboot('a remote client is connected')
        self.write(self.proc/'net/tcp', self.TCP_HEAD + self.SSH_LISTEN)
        self.assertEqual(self.updater('run'), 0)
        self.assertEqual(self.reboots(), 1)

    def test_loopback_client_does_not_defer_the_reboot(self):
        self.write(self.proc/'net/tcp', self.TCP_HEAD + self.SSH_LISTEN +
                   '   1: 0100007F:0016 0100007F:C350 01 00000000:00000000 00:00000000 00000000     0        0 2\n')
        self.write(self.proc/'net/tcp6', self.TCP_HEAD +
                   '   0: 00000000000000000000000000000000:0016 00000000000000000000000000000000:0000 0A 0 0 0 0 0 1\n'
                   '   1: 0000000000000000FFFF00000100007F:0016 0000000000000000FFFF00000100007F:C351 01 0 0 0 0 0 2\n')
        self.assertEqual(self.start(), 0, self.kmsg())
        self.assertEqual(self.reboots(), 1)

    def test_external_display_defers_the_verification_reboot(self):
        self.write(self.sys/'class/drm/card1-DP-1/enabled', 'enabled\n')
        self.assert_busy_defers_reboot('an external display is in use')

    def test_shutdown_inhibitor_defers_the_verification_reboot(self):
        stub = self.bin/'fake-inhibit'
        self.write(stub, '#!/bin/sh\necho "backup 0 root 42 rsync shutdown:sleep nightly backup block"\n', 0o755)
        self.assert_busy_defers_reboot('a shutdown inhibitor is active', ROG5_UPDATE_INHIBIT_CMD='fake-inhibit')

    def test_never_policy_leaves_the_reboot_to_the_user(self):
        self.assertEqual(self.start(ROG5_UPDATE_REBOOT='never'), 0, self.kmsg())
        self.assertEqual(self.reboots(), 0)

    def test_an_update_that_breaks_a_boot_verifier_arms_a_restore(self):
        self.write(self.dir/'effect', f'#!/bin/sh\nprintf "root:\\$6\\$s\\$h:19000::::::\\n" >{self.root}/etc/shadow\n', 0o755)
        self.write(self.dir/'new-installed', PLAN)
        self.assertEqual(self.start(), 1)
        self.assertEqual(self.fields('pending')['action'], 'restore')
        self.assertIn('shadow', self.kmsg())
        self.assertEqual(self.reboots(), 1)
        self.assertEqual(self.rollback(), 0)
        self.assertEqual(self.fields('last-result')['reason'], 'restore-requested')

    def test_a_failed_transaction_that_changed_packages_arms_a_restore(self):
        self.write(self.dir/'new-installed', 'openssh 10.1p1-1\nsystemd 261.3-1\n')
        self.write(self.dir/'su-rc', '1')
        self.assertEqual(self.start(), 1)
        self.assertEqual(self.fields('pending')['action'], 'restore')
        self.assertEqual(self.reboots(), 1)

    def test_a_transaction_that_changed_nothing_is_discarded(self):
        self.write(self.dir/'su-rc', '1')
        self.assertEqual(self.start(), 1)
        self.assertIn('pacman failed before changing packages', self.kmsg())
        self.assertFalse((self.udir/'pending').exists())
        self.assertEqual([p.name for p in (self.state/'snapshots').iterdir()], [])
        self.assertEqual(self.reboots(), 0)

    def test_keyring_is_upgraded_first(self):
        self.start('archlinuxarm-keyring 20260901-1\n' + PLAN)
        calls = self.calls()
        self.assertLess(calls.index('pacman -S --needed --noconfirm archlinuxarm-keyring'),
                        calls.index('pacman -Su --noconfirm'))

    def test_held_packages_are_ignored_and_block_a_plan_that_needs_them(self):
        self.assertEqual(self.start(ROG5_UPDATE_HOLD='systemd systemd-libs'), 0)
        self.assertIn('pacman -Su --print --print-format %n %v --noconfirm --ignore systemd --ignore systemd-libs',
                      self.calls())
        self.assertIn('SKIP held package systemd', self.kmsg())
        self.assertFalse((self.state/'snapshots').exists())
        self.assertEqual(self.updater('run', ROG5_UPDATE_HOLD='bad;name'), 1)

    def test_conditions(self):
        usb, battery = self.sys/'class/power_supply/qcom-battmgr-usb', self.sys/'class/power_supply/qcom-battmgr-bat'
        self.write(battery/'capacity', '50\n')
        self.assertEqual(self.start(), 0)
        self.assertIn('SKIP needs external power', self.kmsg())
        self.write(usb/'online', '1\n')
        self.write(battery/'temp', '460\n')
        self.assertEqual(self.start(), 0)
        self.assertEqual(self.kmsg().count('SKIP needs external power'), 2)
        self.write(battery/'temp', '300\n')
        self.write(self.proc/'net/route', 'Iface\tDestination\tGateway\n')
        self.assertEqual(self.start(), 0)
        self.assertIn('SKIP no default route', self.kmsg())
        self.write(self.proc/'net/route', 'Iface\tDestination\tGateway\tFlags\tRefCnt\tUse\tMetric\tMask\n'
                   'usb0\t00000000\t0100000A\t0003\t0\t0\t0\t00000000\n')
        (self.dir/'keyring-inactive').touch()
        self.assertEqual(self.start(), 0)
        self.assertIn('SKIP package keyring is not active', self.kmsg())
        (self.dir/'keyring-inactive').unlink()
        (self.root/'var/lib/pacman/db.lck').touch()
        self.assertEqual(self.start(), 0)
        self.assertIn('SKIP pacman is locked', self.kmsg())
        (self.root/'var/lib/pacman/db.lck').unlink()
        self.assertNotIn('pacman -Sy --noconfirm', self.calls())
        self.assertEqual(self.start(), 0, self.kmsg())
        self.assertIn('pacman -Su --noconfirm', self.calls())

    def test_at_most_one_attempt_per_interval(self):
        self.assertEqual(self.start(''), 0)
        self.assertEqual(self.start(''), 0)
        self.assertEqual(self.calls().count('pacman -Sy --noconfirm'), 1)
        self.assertEqual(self.start('', ROG5_UPDATE_INTERVAL='0'), 0)
        self.assertEqual(self.calls().count('pacman -Sy --noconfirm'), 2)
        self.write(self.dir/'sy-rc', '1')
        self.assertEqual(self.start('', ROG5_UPDATE_INTERVAL='0'), 1)
        self.assertFalse((self.udir/'last-check').exists())

    def test_a_root_that_already_fails_is_not_updated(self):
        (self.root/'etc/shadow').chmod(0o644)
        self.assertEqual(self.start(), 1)
        self.assertIn('already fails verify-root (shadow)', self.kmsg())
        self.assertNotIn('pacman -Sy --noconfirm', self.calls())

    def test_an_unexpected_root_mount_is_refused(self):
        self.write(self.dir/'mounts', (self.dir/'mounts').read_text().replace('workdir', 'index=on,workdir'))
        self.assertEqual(self.start(), 1)
        self.assertIn('not the expected persistent overlay', self.kmsg())

    def test_not_enough_space_is_refused(self):
        self.assertEqual(self.start(ROG5_UPDATE_RESERVE_MIB='999999999'), 1)
        self.assertIn('not enough space', self.kmsg())
        self.assertFalse((self.udir/'pending').exists())

    def test_repeated_failures_wait_for_new_versions_then_pause(self):
        def fail_once(plan):
            self.write(self.dir/'su-rc', '1')
            self.write(self.dir/'new-installed', 'changed 1\n')
            self.assertEqual(self.start(plan, ROG5_UPDATE_INTERVAL='0'), 1)
            self.assertEqual(self.rollback(), 0)   # restore-requested at the next boot
            self.write(self.dir/'installed', INSTALLED)
        fail_once(PLAN)
        fail_once(PLAN)
        self.assertEqual(self.start(PLAN + 'zlib 1.3-2\n', ROG5_UPDATE_INTERVAL='0'), 0)
        self.assertIn('waiting for new package versions', self.kmsg())
        self.assertEqual((self.udir/'failures').read_text(), '2\n')
        fail_once('openssh 10.1p1-2\nsystemd 262-1\n')
        self.assertEqual(self.start('other 1-1\n', ROG5_UPDATE_INTERVAL='0'), 0)
        self.assertIn('paused after repeated rollbacks', self.kmsg())
        self.assertEqual(self.updater('resume'), 0)
        self.assertFalse((self.udir/'failures').exists())


@unittest.skipUnless(unshare_ok(), 'user namespaces are unavailable')
class Commit(Base):
    def ready(self):
        self.write(self.run/'rog5-p2-ready', f'status=PASS\nattested_boot_id={BOOT}\n', 0o444)
        self.write(self.run/'rog5-persistent-ssh-identity.record',
                   f'format=rog5-persistent-ssh-identity-v1\nidentity_boot_id={BOOT}\n', 0o444)

    def booted_update(self):
        self.snapshot()
        (self.state/'snapshots/20260101T000000Z-00000000').mkdir(mode=0o700)
        self.pending()
        self.assertEqual(self.rollback(), 0)
        self.write(self.root/'var/cache/pacman/pkg/systemd-262-1-aarch64.pkg.tar.xz', 'pkg')

    def test_no_pending_update_is_a_skip(self):
        self.assertEqual(self.updater('commit'), 0)
        self.assertIn('SKIP no pending package update', self.kmsg())

    def test_healthy_boot_commits_and_keeps_only_this_snapshot(self):
        self.booted_update()
        self.ready()
        self.assertEqual(self.updater('commit'), 0, self.kmsg())
        self.assertIn(f'PASS update {UID} committed healthy', self.kmsg())
        self.assertEqual(self.fields('last-result')['result'], 'committed')
        for name in ('pending', 'attempt'):
            self.assertFalse((self.udir/name).exists())
        self.assertEqual([p.name for p in (self.state/'snapshots').iterdir()], [UID])
        self.assertEqual(list((self.root/'var/cache/pacman/pkg').iterdir()), [])
        # The kept snapshot can be restored by hand.
        self.assertEqual(self.updater('rollback'), 0, self.kmsg())
        self.assertEqual(self.fields('pending')['action'], 'restore')
        self.assertEqual(self.rollback(BOOT2), 0)
        self.assertEqual((self.upper/'etc/pacman.conf').read_text(), 'upper-v0\n')

    def test_health_timeout_leaves_the_update_for_the_next_boot_to_restore(self):
        self.booted_update()
        self.assertEqual(self.updater('commit'), 1)
        self.assertIn('health not reached', self.kmsg())
        self.assertTrue((self.run/'rog5-update-commit.failed').exists())
        self.assertEqual(self.fields('pending')['action'], 'verify')
        # The hourly run then reboots once the display is off.
        self.assertEqual(self.updater('run'), 0)
        self.assertEqual(self.reboots(), 1)

    def test_a_boot_the_init_did_not_count_is_not_committed(self):
        self.snapshot()
        self.pending()
        self.ready()
        self.assertEqual(self.updater('commit'), 1)
        self.assertIn('no exact attempt record', self.kmsg())
        self.assertEqual(self.rollback(BOOT2), 0)
        self.write(self.proc/'sys/kernel/random/boot_id', BOOT + '\n')
        self.assertEqual(self.updater('commit'), 1)
        self.assertIn('started by another boot', self.kmsg())

    def test_markers_rewritten_by_the_new_systemd_arm_a_restore(self):
        self.booted_update()
        self.ready()
        for path in (self.root/'etc/.updated', self.upper/'etc/.updated'):
            path.write_text(OLD_MARKER)
        self.assertEqual(self.updater('commit'), 1)
        self.assertIn('verify-root fails (update_markers)', self.kmsg())
        self.assertEqual(self.fields('pending')['action'], 'restore')
        self.assertEqual(self.reboots(), 1)
        self.assertEqual(self.rollback(BOOT2), 0)
        self.assertEqual((self.upper/'etc/pacman.conf').read_text(), 'upper-v0\n')


@unittest.skipUnless(unshare_ok(), 'user namespaces are unavailable')
class Publish(Base):
    def prepare(self, overlay=1):
        body = function(INIT.read_text(), 'prepare_update_services')
        body = body.replace('\tkit=/rog5-update\n', f'\tkit={self.dir/"kit"}\n').replace('\trun=/run\n', f'\trun={self.run}\n')
        script = f'expected_persistent_overlay_mode={overlay}\n' + body + 'prepare_update_services\n'
        return subprocess.run(['unshare', '-r', *self.shell, '-c', script], capture_output=True,
                              text=True, env=self.env, timeout=120).returncode

    def kit(self):
        kit = self.dir/'kit'
        kit.mkdir(mode=0o700)
        self.write(kit/'rog5-update', UPDATE.read_bytes(), 0o755)
        for unit in UNITS:
            self.write(kit/unit, (REPO/'configs/systemd'/unit).read_bytes())
        return kit

    def test_absent_kit_is_a_no_op(self):
        self.assertEqual(self.prepare(), 0)
        self.assertEqual(list(self.run.iterdir()), [])

    def test_kit_is_published_and_enabled(self):
        self.kit()
        self.assertEqual(self.prepare(), 0)
        self.assertEqual((self.run/'rog5-update/rog5-update').read_bytes(), UPDATE.read_bytes())
        system = self.run/'systemd/system'
        self.assertEqual(os.readlink(system/'timers.target.wants/rog5-update.timer'), '../rog5-update.timer')
        self.assertEqual(os.readlink(system/'multi-user.target.wants/rog5-update-commit.service'),
                         '../rog5-update-commit.service')
        for unit in UNITS:
            self.assertEqual((system/unit).read_bytes(), (REPO/'configs/systemd'/unit).read_bytes())

    def test_inexact_kit_or_composition_is_refused(self):
        kit = self.kit()
        self.assertEqual(self.prepare(overlay=0), 1)
        (kit/'rog5-update').chmod(0o775)
        self.assertEqual(self.prepare(), 1)
        (kit/'rog5-update').chmod(0o755)
        (kit/'extra').write_text('x')
        self.assertEqual(self.prepare(), 1)
        self.assertFalse((self.run/'rog5-update').exists())


class Contracts(unittest.TestCase):
    def test_rollback_runs_before_the_overlay_tree_is_verified_and_mounted(self):
        body = function(INIT.read_text(), 'prepare_persistent_overlay_inner')
        order = [body.index(s) for s in ('verify_exact_rw_exec_mount "$overlay_loop" /mnt/state',
                                         'apply_update_rollback /mnt/state || return 1',
                                         'verify_persistent_overlay_tree /mnt/state',
                                         'verify_overlay_workdir_pre_mount /mnt/state')]
        self.assertEqual(order, sorted(order))
        runtime = function(INIT.read_text(), 'prepare_runtime')
        self.assertLess(runtime.index('prepare_production_trial'), runtime.index('prepare_update_services'))

    def test_updater_and_init_share_the_pinned_policy_and_marker_template(self):
        init, update = INIT.read_text(), UPDATE.read_text()
        for pin in (ORIGINAL_PIN, VOLATILE_PIN):
            self.assertIn(pin, init)
            self.assertIn(pin, update)
        for line in ('# This file was created by systemd-update-done. The timestamp below is the',
                     '# been applied. See man:systemd-update-done.service(8) for details.',
                     "grep -Eq '^root:x:[0-9]+:{6}$'"):
            self.assertIn(line, update)
        self.assertIn("grep -Eq '^root:x:[0-9]+:{6}$' /etc/shadow", (REPO/'initramfs/persistent-root-attest').read_text())
        for grammar in ('^update_id=[0-9]{8}T[0-9]{6}Z-[0-9a-f]{8}$', 'format=rog5-overlay-snapshot-v1',
                        '^names_sha256=[0-9a-f]{64}$'):
            self.assertIn(grammar, init)
            self.assertIn(grammar, update)

    def test_units(self):
        commit = (REPO/'configs/systemd/rog5-update-commit.service').read_text()
        after = re.search(r'^After=(.*)$', commit, re.M).group(1).split()
        for unit in ('rog5-production-trial-commit.service', 'systemd-update-done.service',
                     'rog5-persistent-ssh-identity.service'):
            self.assertIn(unit, after)
        self.assertIn('ExecStart=/run/rog5-update/rog5-update commit', commit)
        service = (REPO/'configs/systemd/rog5-update.service').read_text()
        self.assertIn('ExecStart=/run/rog5-update/rog5-update run', service)
        self.assertIn('rog5-update-commit.service', re.search(r'^After=(.*)$', service, re.M).group(1))
        self.assertIn('OnUnitActiveSec=1h', (REPO/'configs/systemd/rog5-update.timer').read_text())


if __name__ == '__main__':
    unittest.main(verbosity=2)
