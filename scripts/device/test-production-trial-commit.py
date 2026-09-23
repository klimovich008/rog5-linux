#!/usr/bin/env python3
"""Tests for the production try-once commit kit.

The commit script runs in the booted production system and marks the
selector's try-once record healthy once the P2 health gate passed. The init
function publishes the kit from the ramdisk to /run. Both run here under
`unshare -r`, so the temporary files are owned by uid 0 as on the phone; the
aarch64 trial-state helper is replaced by a stub that logs its calls.
"""
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[2]
COMMIT = REPO/'initramfs/production-trial-commit'
INIT = REPO/'initramfs/persistent-root-init'
UNIT = REPO/'configs/systemd/rog5-production-trial-commit.service'
TRIAL = 'c'*64
BOOT = '0d5c1d8e-2a4f-4b61-9d0e-3f1a2b3c4d5e'
DESCRIPTOR = f'format=rog5-persistent-wifi-health-v1\ntrial_id={TRIAL}\nprimary_bundle=production-7.2.7-r3\nmode=try-once\n'
HELPER = '''#!/bin/sh
printf '%s\\n' "$*" >>"${0%/*}/calls"
[ "$2" = TRIAL ] && [ "$3" = production-7.2.7-r3 ] || { echo mismatch >&2; exit 1; }
state=$(cat "${0%/*}/state") || exit 1
case $1 in
	state) echo "$state" ;;
	healthy) case $state in pending) echo healthy >"${0%/*}/state"; echo healthy ;;
		healthy) echo already-healthy ;; *) exit 1 ;; esac ;;
	*) exit 1 ;;
esac
'''.replace('TRIAL', TRIAL)
SSHD = '  0: 00000000:0016 00000000:0000 0A 00000000:00000000 00:00000000 00000000     0        0 1 1 0 100 0 0 10 0\n'


def target_shell(workdir):
    """The shell command: host sh, or the target ARM64 busybox (ROG5_TEST_BUSYBOX
    with ROG5_TEST_QEMU) with its applets first in PATH."""
    if not os.environ.get('ROG5_TEST_BUSYBOX'):
        return ['sh'], {}
    qemu, busybox = os.environ['ROG5_TEST_QEMU'], os.environ['ROG5_TEST_BUSYBOX']
    applets = Path(workdir)/'applets'
    applets.mkdir()
    for name in ('cat', 'cp', 'cut', 'dirname', 'grep', 'ln', 'mkdir', 'sed', 'sha256sum', 'sleep', 'stat', 'wc'):
        (applets/name).write_text(f'#!/bin/sh\nexec {qemu} {busybox} {name} "$@"\n')
        (applets/name).chmod(0o755)
    return [qemu, busybox, 'sh'], {'PATH': f'{applets}:{os.environ["PATH"]}'}


def unshare_ok():
    return subprocess.run(['unshare', '-r', 'true'], capture_output=True).returncode == 0


@unittest.skipUnless(unshare_ok(), 'user namespaces are unavailable')
class Commit(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(prefix='rog5-trial-commit-'))
        d = self.dir
        self.kit, self.run, self.sys, self.proc = d/'kit', d/'run', d/'sys', d/'proc'
        for path in (self.kit, self.run, self.proc/'sys/kernel/random', self.proc/'net',
                     self.sys/'class/power_supply/qcom-battmgr-bat'):
            path.mkdir(parents=True)
        (self.kit/'trial-descriptor').write_text(DESCRIPTOR)
        (self.kit/'trial-state').write_text(HELPER)
        (self.kit/'trial-state').chmod(0o755)
        (self.kit/'state').write_text('pending\n')
        (self.proc/'sys/kernel/random/boot_id').write_text(BOOT+'\n')
        (self.proc/'net/tcp').write_text('  sl  local_address rem_address   st\n'+SSHD)
        (self.sys/'class/power_supply/qcom-battmgr-bat/temp').write_text('300\n')
        for disk, ro in (('sda', 0), ('sda23', 0), ('sda24', 1), ('sdb', 1)):
            (self.sys/'class/block'/disk).mkdir(parents=True)
            (self.sys/'class/block'/disk/'ro').write_text(f'{ro}\n')
        self.ready()

    def tearDown(self):
        shutil.rmtree(self.dir)

    def ready(self, boot=BOOT, status='PASS'):
        for name, text in (('rog5-p2-ready', f'status={status}\nattested_boot_id={boot}\n'),
                           ('rog5-persistent-ssh-identity.record', f'identity_boot_id={boot}\n')):
            path = self.run/name
            if path.exists():
                path.chmod(0o644)
            path.write_text(text)
            path.chmod(0o444)

    def commit(self, wait=3):
        env = dict(os.environ, ROG5_TRIAL_KIT=str(self.kit), ROG5_TRIAL_RUN=str(self.run),
                   ROG5_TRIAL_SYS=str(self.sys), ROG5_TRIAL_PROC=str(self.proc),
                   ROG5_TRIAL_KMSG=str(self.dir/'kmsg'), ROG5_TRIAL_WAIT=str(wait))
        shell, extra = target_shell(tempfile.mkdtemp(dir=self.dir))
        result = subprocess.run(['unshare', '-r', *shell, str(COMMIT)], capture_output=True, text=True,
                                env=dict(env, **extra), timeout=120)
        kmsg = (self.dir/'kmsg').read_text() if (self.dir/'kmsg').exists() else ''
        return result.returncode, kmsg

    def state(self):
        return (self.kit/'state').read_text().strip()

    def calls(self):
        return (self.kit/'calls').read_text().split('\n')[:-1] if (self.kit/'calls').exists() else []

    def test_ready_boot_commits_healthy(self):
        code, kmsg = self.commit()
        self.assertEqual(code, 0, kmsg)
        self.assertEqual(self.state(), 'healthy')
        self.assertIn('rog5-production-trial: PASS production-7.2.7-r3 committed healthy', kmsg)
        self.assertEqual(self.calls(), [f'state {TRIAL} production-7.2.7-r3', f'healthy {TRIAL} production-7.2.7-r3'])

    def test_already_healthy_is_a_pass(self):
        (self.kit/'state').write_text('healthy\n')
        code, kmsg = self.commit()
        self.assertEqual(code, 0, kmsg)
        self.assertIn('committed already-healthy', kmsg)

    def test_foreign_record_is_skipped_untouched(self):
        (self.kit/'state').unlink()
        code, kmsg = self.commit()
        self.assertEqual(code, 0, kmsg)
        self.assertIn('SKIP this boot is not the selected try-once trial', kmsg)
        self.assertEqual(self.calls(), [f'state {TRIAL} production-7.2.7-r3'])

    def test_failed_record_is_skipped_untouched(self):
        (self.kit/'state').write_text('failed\n')
        code, kmsg = self.commit()
        self.assertEqual(code, 0, kmsg)
        self.assertIn('SKIP', kmsg)
        self.assertEqual(self.state(), 'failed')
        self.assertEqual(len(self.calls()), 1)

    def assert_stays_pending(self, why):
        code, kmsg = self.commit(wait=2)
        self.assertEqual(code, 1, why)
        self.assertIn('FAIL health not reached', kmsg, why)
        self.assertEqual(self.state(), 'pending', why)
        self.assertEqual(len(self.calls()), 1, why)

    def test_unhealthy_boots_stay_pending(self):
        cases = [
            ('stale p2 boot id', lambda: self.ready(boot='1'+BOOT[1:])),
            ('p2 not PASS', lambda: self.ready(status='FAIL')),
            ('p2 writable', lambda: (self.run/'rog5-p2-ready').chmod(0o644)),
            ('no sshd', lambda: (self.proc/'net/tcp').write_text('  sl\n')),
            ('extra writable disk', lambda: (self.sys/'class/block/sda24/ro').write_text('0\n')),
            ('hot battery', lambda: (self.sys/'class/power_supply/qcom-battmgr-bat/temp').write_text('455\n')),
        ]
        for why, breakit in cases:
            with self.subTest(why):
                self.tearDown()
                self.setUp()
                breakit()
                self.assert_stays_pending(why)

    def test_bad_descriptors_fail_before_the_helper(self):
        cases = [
            DESCRIPTOR.replace('mode=try-once', 'mode=always'),
            DESCRIPTOR.replace(TRIAL, TRIAL[:-1]+'C'),
            DESCRIPTOR.replace('production-7.2.7-r3', '../v11'),
            DESCRIPTOR.replace('production-7.2.7-r3', '.hidden'),
            DESCRIPTOR+'extra=1\n',
            '\n'.join(DESCRIPTOR.split('\n')[i] for i in (0, 2, 1, 3, 4)),
        ]
        for text in cases:
            with self.subTest(text):
                (self.kit/'trial-descriptor').write_text(text)
                code, kmsg = self.commit()
                self.assertEqual(code, 1, kmsg)
                self.assertIn('rog5-production-trial: FAIL ', kmsg)
                self.assertEqual(self.calls(), [])
                self.assertEqual(self.state(), 'pending')


def prepare_function(kit, run):
    text = INIT.read_text()
    body = re.search(r'^prepare_production_trial\(\) \{\n.*?^\}\n', text, re.M | re.S).group(0)
    assert body.count('\tkit=/rog5-production-trial\n') == 1 and body.count('\trun=/run\n') == 1
    return body.replace('\tkit=/rog5-production-trial\n', f'\tkit={kit}\n').replace('\trun=/run\n', f'\trun={run}\n')


@unittest.skipUnless(unshare_ok(), 'user namespaces are unavailable')
class Prepare(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(prefix='rog5-trial-prepare-'))
        self.kit, self.run = self.dir/'kit', self.dir/'run'
        self.run.mkdir()
        self.kit.mkdir(mode=0o700)
        for name, mode, source in (('trial-descriptor', 0o444, None), ('trial-state', 0o755, None),
                                   ('commit', 0o755, COMMIT), ('rog5-production-trial-commit.service', 0o644, UNIT)):
            path = self.kit/name
            path.write_bytes(source.read_bytes() if source else name.encode()+b'\n')
            path.chmod(mode)

    def tearDown(self):
        subprocess.run(['chmod', '-R', 'u+w', str(self.dir)])
        shutil.rmtree(self.dir)

    def prepare(self):
        script = prepare_function(self.kit, self.run)+'prepare_production_trial\n'
        shell, extra = target_shell(tempfile.mkdtemp(dir=self.dir))
        return subprocess.run(['unshare', '-r', *shell, '-c', script], capture_output=True, text=True,
                              env=dict(os.environ, **extra), timeout=120).returncode

    def test_kit_is_published_to_run(self):
        self.assertEqual(self.prepare(), 0)
        target = self.run/'rog5-production-trial'
        self.assertEqual(oct(target.stat().st_mode & 0o7777), '0o700')
        self.assertEqual(sorted(p.name for p in target.iterdir()), ['commit', 'trial-descriptor', 'trial-state'])
        self.assertEqual(oct((target/'trial-descriptor').stat().st_mode & 0o7777), '0o444')
        self.assertEqual((target/'commit').read_bytes(), COMMIT.read_bytes())
        unit = self.run/'systemd/system/rog5-production-trial-commit.service'
        self.assertEqual(unit.read_bytes(), UNIT.read_bytes())
        link = self.run/'systemd/system/multi-user.target.wants/rog5-production-trial-commit.service'
        self.assertEqual(os.readlink(link), '../rog5-production-trial-commit.service')

    def test_absent_kit_is_a_no_op(self):
        subprocess.run(['chmod', '-R', 'u+w', str(self.kit)])
        shutil.rmtree(self.kit)
        self.assertEqual(self.prepare(), 0)
        self.assertEqual(list(self.run.iterdir()), [])

    def test_wrong_mode_or_link_is_refused(self):
        (self.kit/'trial-descriptor').chmod(0o644)
        self.assertEqual(self.prepare(), 1)
        self.assertEqual(list(self.run.iterdir()), [])
        (self.kit/'trial-descriptor').chmod(0o444)
        os.link(self.kit/'commit', self.dir/'extra-link')
        self.assertEqual(self.prepare(), 1)
        self.assertEqual(list(self.run.iterdir()), [])

    def test_existing_target_is_refused(self):
        (self.run/'systemd/system').mkdir(parents=True)
        (self.run/'systemd/system/rog5-production-trial-commit.service').write_text('other\n')
        self.assertEqual(self.prepare(), 1)
        self.assertFalse((self.run/'rog5-production-trial').exists())


class Unit(unittest.TestCase):
    def test_unit_orders_after_the_health_gate_and_runs_the_kit(self):
        text = UNIT.read_text()
        self.assertIn('ExecStart=/run/rog5-production-trial/commit\n', text)
        for unit in ('rog5-persistent-state.service', 'rog5-persistent-ssh-identity.service'):
            self.assertIn(unit, re.search(r'^After=(.*)$', text, re.M).group(1).split())
        timeout = int(re.search(r'^TimeoutStartSec=(\d+)$', text, re.M).group(1))
        wait = int(re.search(r'ROG5_TRIAL_WAIT:-(\d+)', COMMIT.read_text()).group(1))
        self.assertGreater(timeout, wait+30)


if __name__ == '__main__':
    unittest.main(verbosity=2)
