#!/usr/bin/env python3
"""Exercise the production RAM-trial launcher against fake sysfs, fastboot,
ssh and nmcli executables. No phone, USB device or network is touched."""
import importlib.util
import json
import os
import socket
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest

REPO = Path(__file__).resolve().parents[2]
SOURCE = REPO/'scripts/host/production-ram-trial.py'
SERIAL = 'ROG5-SERIAL-REDACTED'
# the launcher reads the real serial from outside git; pin it to the fake device
os.environ['ROG5_DEVICE_SERIAL'] = SERIAL

FASTBOOT = r'''#!/bin/sh
printf '%s\n' "$*" >>"$FAKE_LOG"
case "$*" in
	*"getvar product") echo "product: ${FAKE_PRODUCT:-lahaina}" >&2 ;;
	*"getvar current-slot") echo "current-slot: ${FAKE_SLOT:-b}" >&2 ;;
	*"getvar unlocked") echo "unlocked: ${FAKE_UNLOCKED:-yes}" >&2 ;;
	*"getvar max-download-size") echo "max-download-size: ${FAKE_MAX:-0x20000000}" >&2 ;;
	*" boot /proc/self/fd/"*) for last; do :; done; sha256sum <"$last" | cut -d' ' -f1 >"$FAKE_BOOTED"; exit "${FAKE_BOOT_RC:-0}" ;;
	*) exit 1 ;;
esac
'''
LOGGER = '#!/bin/sh\nprintf "%s %s\\n" "$(basename "$0")" "$*" >>"$FAKE_LOG"\n'


def load(env):
    os.environ.update(env)
    spec = importlib.util.spec_from_file_location('production_ram_trial_'+str(len(env)), SOURCE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Launcher(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        base = self.base = Path(self.temp.name)
        self.anchor = base/'devices/usb1/1-1/1-1.2'
        self.anchor.mkdir(parents=True)
        (base/'bus').mkdir()
        self.usb = base/'bus/1-1.2'
        self.usb.symlink_to(self.anchor)
        self.net = base/'net'
        self.net.mkdir()
        self.bin = base/'bin'
        self.bin.mkdir()
        for name, text in (('fastboot', FASTBOOT), ('ssh', LOGGER), ('nmcli', LOGGER)):
            (self.bin/name).write_text(text)
            (self.bin/name).chmod(0o755)
        self.log = base/'calls.log'
        self.booted = base/'booted'
        env = dict(ROG5_TRIAL_USB=str(self.usb), ROG5_TRIAL_ANCHOR=str(self.anchor),
                   ROG5_TRIAL_NET=str(self.net), ROG5_TRIAL_FASTBOOT=str(self.bin/'fastboot'),
                   ROG5_TRIAL_SSH=str(self.bin/'ssh'), ROG5_TRIAL_NMCLI=str(self.bin/'nmcli'),
                   ROG5_TRIAL_CLAIMS=str(base/'claims'), FAKE_LOG=str(self.log),
                   FAKE_BOOTED=str(self.booted))
        self.saved = {key: os.environ.get(key) for key in env}
        self.addCleanup(self.restore)
        self.m = load(env)
        self.image = base/'wrapper.img'
        self.image.write_bytes(b'\0'*self.m.IMAGE_SIZE)
        self.image.chmod(0o600)
        self.sha = self.m.hashlib.sha256(self.image.read_bytes()).hexdigest()

    def restore(self):
        for key, value in self.saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        for key in ('ROG5_ALLOW_RAM_TRIAL', 'FAKE_PRODUCT', 'FAKE_SLOT', 'FAKE_UNLOCKED', 'FAKE_MAX', 'FAKE_BOOT_RC'):
            os.environ.pop(key, None)

    def device(self, vendor, product_id, product='', serial=SERIAL):
        for name, value in (('idVendor', vendor), ('idProduct', product_id), ('product', product), ('serial', serial)):
            (self.anchor/name).write_text(value+'\n')

    def target_net(self):
        interface = self.net/self.m.INTERFACE
        interface.mkdir()
        (self.anchor/'1-1.2:1.0').mkdir()
        (interface/'device').symlink_to(self.anchor/'1-1.2:1.0')

    def test_usb_states_follow_the_single_approved_port(self):
        self.assertEqual(self.m.usb_state(), 'transition')  # port exists, ids unreadable
        self.device('0b05', '4daf')
        self.assertEqual(self.m.usb_state(), 'fastboot')
        self.device('0b05', '4daf', serial='OTHER')
        self.assertEqual(self.m.usb_state(), 'mismatch')
        self.device('05c6', '900e')
        self.assertEqual(self.m.usb_state(), 'crashdump')
        self.device('1d6b', '0104', 'ROG5 recovery')
        self.assertEqual(self.m.usb_state(), 'recovery')
        self.device('1d6b', '0104', 'ROG5 persistent root')
        self.assertEqual(self.m.usb_state(), 'enumerating')
        self.target_net()
        self.assertEqual(self.m.usb_state(), 'target')
        self.device('1d6b', '0104', 'Something else')
        self.assertEqual(self.m.usb_state(), 'mismatch')
        self.usb.unlink()
        self.assertEqual(self.m.usb_state(), 'absent')
        other = self.base/'devices/usb1/1-1/1-1.3'
        other.mkdir()
        self.usb.symlink_to(other)
        self.assertEqual(self.m.usb_state(), 'mismatch')

    def boot(self):
        import shutil
        evidence = self.base/'evidence'
        shutil.rmtree(evidence, ignore_errors=True)
        evidence.mkdir()
        return self.m.boot(self.image, self.sha, evidence)

    def test_boot_requires_explicit_environment_and_exact_identity(self):
        self.device('0b05', '4daf')
        with self.assertRaisesRegex(ValueError, 'ROG5_ALLOW_RAM_TRIAL'):
            self.boot()
        os.environ['ROG5_ALLOW_RAM_TRIAL'] = '1'
        for key, value, message in (('FAKE_PRODUCT', 'kona', 'product'), ('FAKE_SLOT', 'a', 'slot'),
                                    ('FAKE_UNLOCKED', 'no', 'unlocked'), ('FAKE_MAX', '0x1000', 'capacity')):
            with self.subTest(case=key):
                os.environ[key] = value
                with self.assertRaisesRegex(ValueError, message):
                    self.boot()
                del os.environ[key]
                import shutil
                shutil.rmtree(self.base/'evidence', ignore_errors=True)
        self.assertFalse(self.booted.exists())
        self.assertFalse((self.base/'claims').exists() and any((self.base/'claims').iterdir()))

    def test_boot_refuses_wrong_hash_and_replay(self):
        self.device('0b05', '4daf')
        os.environ['ROG5_ALLOW_RAM_TRIAL'] = '1'
        good = self.sha
        self.sha = '0'*64
        with self.assertRaisesRegex(ValueError, 'hash'):
            self.boot()
        self.assertFalse(self.booted.exists())
        import shutil
        shutil.rmtree(self.base/'evidence')
        self.sha = good
        record = self.boot()
        self.assertEqual(record['returncode'], 0)
        self.assertEqual(self.booted.read_text().strip(), good)
        claim = json.loads((self.base/'claims'/(good+'.entered')).read_text())
        self.assertEqual(claim['serial'], SERIAL)
        calls = self.log.read_text()
        self.assertNotIn('flash', calls)
        self.assertIn(f'-s {SERIAL} boot /proc/self/fd/', calls)
        shutil.rmtree(self.base/'evidence')
        self.booted.unlink()
        with self.assertRaises(FileExistsError):
            self.boot()
        self.assertFalse(self.booted.exists())

    def test_claim_and_its_directory_are_durable_before_fastboot_boot(self):
        from unittest import mock
        self.device('0b05', '4daf')
        os.environ['ROG5_ALLOW_RAM_TRIAL'] = '1'
        events = []
        real_fsync, real_run = os.fsync, self.m.subprocess.run

        def fsync(fd):
            events.append(('fsync', os.readlink(f'/proc/self/fd/{fd}')))
            return real_fsync(fd)

        def run(argv, *args, **kwargs):
            if 'boot' in argv:
                events.append(('boot', argv[-1]))
            return real_run(argv, *args, **kwargs)

        with mock.patch.object(self.m.os, 'fsync', fsync), mock.patch.object(self.m.subprocess, 'run', run):
            self.boot()
        claims = str(self.base/'claims')
        claim = claims+'/'+self.sha+'.entered'
        boot_at = events.index(next(e for e in events if e[0] == 'boot'))
        before = events[:boot_at]
        self.assertIn(('fsync', claim), before)
        self.assertIn(('fsync', claims), before)
        # claims/ was new: its own entry is made durable in its parent too.
        self.assertIn(('fsync', str(self.base)), before)
        # The directory sync that publishes the marker's name follows the
        # marker's own data sync.
        last_dir = max(i for i, e in enumerate(before) if e == ('fsync', claims))
        self.assertLess(before.index(('fsync', claim)), last_dir)
        self.assertEqual(os.stat(claim).st_mode & 0o777, 0o600)

    def test_claim_refuses_a_symlinked_marker(self):
        self.device('0b05', '4daf')
        os.environ['ROG5_ALLOW_RAM_TRIAL'] = '1'
        (self.base/'claims').mkdir(mode=0o700)
        (self.base/'claims'/(self.sha+'.entered')).symlink_to(self.base/'elsewhere')
        with self.assertRaises(FileExistsError):
            self.boot()
        self.assertFalse(self.booted.exists())
        self.assertFalse((self.base/'elsewhere').exists())

    def test_failed_fastboot_boot_keeps_the_claim_consumed(self):
        self.device('0b05', '4daf')
        os.environ['ROG5_ALLOW_RAM_TRIAL'] = '1'
        os.environ['FAKE_BOOT_RC'] = '1'
        with self.assertRaisesRegex(ValueError, 'claim stays consumed'):
            self.boot()
        self.assertTrue((self.base/'claims'/(self.sha+'.entered')).exists())

    def test_probe_and_reboot_need_a_running_target(self):
        self.device('0b05', '4daf')
        with self.assertRaisesRegex(ValueError, 'running target'):
            self.m.probe()
        self.assertFalse(self.log.exists() and 'ssh' in self.log.read_text())

    def test_observe_prompts_each_rescue_step_once(self):
        evidence = self.base/'observe'
        evidence.mkdir()
        self.device('05c6', '900e')  # crashdump: R2 (which ends in R1) at once
        summary = self.m.observe(evidence, seconds=0.3, interval=0.05, hang_seconds=0.1)
        self.assertEqual(summary['rescue_prompts'], ['R2'])
        self.assertEqual(summary['final_state'], 'crashdump')
        # Host-controlled fastboot never prompts a rescue.
        parked = self.base/'parked'
        parked.mkdir()
        self.device('0b05', '4daf')
        summary = self.m.observe(parked, seconds=0.3, interval=0.05, hang_seconds=0.1)
        self.assertEqual(summary['rescue_prompts'], [])
        silent = self.base/'silent'
        silent.mkdir()
        self.usb.unlink()  # nothing enumerates after the boot: R1 once
        summary = self.m.observe(silent, seconds=0.4, interval=0.05, hang_seconds=0.1)
        self.assertEqual(summary['rescue_prompts'], ['R1'])
        prompts = [json.loads(line).get('rescue_prompt') for line in
                   (silent/'transitions.jsonl').read_text().splitlines()]
        self.assertEqual([p for p in prompts if p], ['R1'])
        self.assertEqual(summary['final_state'], 'absent')

    def test_fastboot_reboot_needs_exact_identity_and_sends_only_reboot(self):
        self.device('1d6b', '0104', 'ROG5 persistent root')
        env = dict(os.environ, HOME=str(self.base))
        result = subprocess.run([sys.executable, str(SOURCE), 'fastboot-reboot', '--wait', '1'],
                                env=env, capture_output=True, text=True, timeout=30)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('not in fastboot', result.stderr)
        self.device('0b05', '4daf')
        (self.bin/'fastboot').write_text(FASTBOOT.replace('*) exit 1 ;;', '*" reboot") ;;\n\t*) exit 1 ;;'))
        result = subprocess.run([sys.executable, str(SOURCE), 'fastboot-reboot', '--wait', '1'],
                                env=env, capture_output=True, text=True, timeout=30)
        calls = self.log.read_text()
        self.assertIn(f'-s {SERIAL} reboot', calls)
        self.assertNotIn('flash', calls)
        self.assertNotIn(' boot ', calls)
        self.assertIn('did not leave fastboot', result.stderr)  # the fake phone stays put

    def test_observation_ends_when_the_trial_returns_to_fastboot(self):
        evidence = self.base/'ended'
        evidence.mkdir()
        self.device('1d6b', '0104', 'ROG5 recovery')
        states = iter([None, None, ('0b05', '4daf')])
        original = self.m.usb_state
        def scripted():
            step = next(states, ('0b05', '4daf'))
            if step:
                self.device(*step)
            return original()
        self.m.usb_state = scripted
        from unittest import mock
        patcher = mock.patch.object(self.m.time, 'sleep', lambda s: None)
        patcher.start()
        self.addCleanup(patcher.stop)
        summary = self.m.observe(evidence, seconds=5, interval=0.01, hang_seconds=100)
        self.assertEqual(summary['final_state'], 'fastboot')
        states_seen = [json.loads(l)['state'] for l in (evidence/'transitions.jsonl').read_text().splitlines()]
        self.assertEqual(states_seen, ['recovery', 'fastboot'])

    def test_to_fastboot_needs_a_mode_and_sends_only_the_chosen_command(self):
        self.device('1d6b', '0104', 'ROG5 persistent root')
        self.target_net()
        (self.bin/'nmcli').write_text('#!/bin/sh\ncase "$*" in *"device show"*) echo rog5-standalone-shared ;; esac\n')
        key = self.base/'key'
        hosts = self.base/'hosts'
        for path in (key, hosts):
            path.write_text('x')
            path.chmod(0o600)
        env = dict(os.environ, HOME=str(self.base))
        state = self.base/'.local/state'
        (state/'rog5-v13-live-inputs-20260823-r1').mkdir(parents=True)
        (state/'rog5-native-root-release-v6-20260829-r1').mkdir(parents=True)
        os.link(key, state/'rog5-v13-live-inputs-20260823-r1/deployment-ssh-key')
        os.link(hosts, state/'rog5-native-root-release-v6-20260829-r1/v7-stable-known-hosts')
        missing = subprocess.run([sys.executable, str(SOURCE), 'to-fastboot'], env=env,
                                 capture_output=True, text=True)
        self.assertNotEqual(missing.returncode, 0)
        self.assertIn('--mode', missing.stderr)
        result = subprocess.run([sys.executable, str(SOURCE), 'to-fastboot', '--mode', 'helper', '--wait', '1'],
                                env=env, capture_output=True, text=True, timeout=30)
        calls = self.log.read_text()
        self.assertIn('root@10.77.0.2 sync; sync; exec /run/initramfs/usr/libexec/rog5-reboot-bootloader', calls)
        self.assertNotIn('sed', calls)
        # The fake phone never reaches fastboot, so the command must not claim success.
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('did not reach fastboot', result.stderr)

    def test_profile_activation_is_idempotent(self):
        (self.bin/'nmcli').write_text('#!/bin/sh\nprintf "%s\\n" "$*" >>"$FAKE_LOG"\n'
                                      'case "$*" in *"device show"*) echo rog5-standalone-shared ;; esac\n')
        self.assertFalse(self.m.use_address('10.77.0.2'))
        self.assertNotIn('connection up', self.log.read_text())
        self.assertTrue(self.m.use_address('169.254.77.2'))
        self.assertIn('connection up rog5-fallback-usb-ssh ifname enp4s0f3u1u2', self.log.read_text())
        with self.assertRaisesRegex(ValueError, 'unknown target address'):
            self.m.use_address('10.0.0.2')


class Stages(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.log = self.base/'calls.log'
        bin_dir = self.base/'bin'
        bin_dir.mkdir()
        for name in ('nmcli', 'firewall-cmd'):
            (bin_dir/name).write_text('#!/bin/sh\nprintf "%s %s\\n" "$(basename "$0")" "$*" >>"$FAKE_LOG"\n'
                                      'case "$*" in *"device show"*) echo rog5-standalone-shared ;; esac\n')
            (bin_dir/name).chmod(0o755)
        with socket.socket() as probe:
            probe.bind(('127.0.0.1', 0))
            self.port = probe.getsockname()[1]
        env = dict(ROG5_TRIAL_NMCLI=str(bin_dir/'nmcli'), ROG5_TRIAL_FIREWALL=str(bin_dir/'firewall-cmd'),
                   ROG5_TRIAL_STAGE_BIND='127.0.0.1', ROG5_TRIAL_STAGE_PEER='127.0.0.1',
                   ROG5_TRIAL_STAGE_PORT=str(self.port), FAKE_LOG=str(self.log))
        saved = {key: os.environ.get(key) for key in env}
        self.addCleanup(lambda: [os.environ.pop(k, None) if v is None else os.environ.__setitem__(k, v)
                                 for k, v in saved.items()])
        self.m = load(env)

    def send(self, payload):
        with socket.create_connection(('127.0.0.1', self.port), timeout=2) as connection:
            connection.sendall(payload)

    def test_receiver_records_distinct_stage_records_from_the_peer(self):
        receiver = self.m.StageReceiver(self.base)
        receiver.start()
        record = b'format=rog5-persistent-root-stage-v2\nsequence=3\nstage=ufs-ready\nstate=PASS\ndetail=ok\n'
        for payload in (record, record, record.replace(b'sequence=3', b'sequence=4')):
            self.send(payload)
            time.sleep(0.2)
        receiver.close()
        text = (self.base/'stages.log').read_text()
        self.assertEqual(receiver.records, 2)
        self.assertEqual(text.count('stage=ufs-ready'), 2)

    def test_receiver_ignores_other_peers(self):
        self.m.STAGE_PEER = '127.0.0.2'
        receiver = self.m.StageReceiver(self.base)
        receiver.start()
        self.send(b'stage=overlay\n')
        time.sleep(0.2)
        receiver.close()
        self.assertEqual(receiver.records, 0)

    def test_stage_path_is_runtime_only_and_reversible(self):
        nmcli = self.base/'bin/nmcli'
        nmcli.write_text('#!/bin/sh\nprintf "%s %s\\n" "$(basename "$0")" "$*" >>"$FAKE_LOG"\n'
                         'case "$*" in *"connection show"*) printf "yes\\nnm-shared\\n169.254.77.1/30\\n" ;; esac\n')
        self.m.stage_path(True)
        self.m.stage_path(False)
        calls = self.log.read_text()
        self.assertIn('connection modify --temporary rog5-fallback-usb-ssh connection.autoconnect yes connection.zone nm-shared', calls)
        self.assertIn('connection modify --temporary rog5-fallback-usb-ssh connection.autoconnect no connection.zone', calls)
        self.assertIn('--timeout=2400', calls)
        self.assertIn('--remove-rich-rule=', calls)
        self.assertNotIn('--permanent', calls)
        self.assertNotIn('ipv4.addresses +', calls)

    def test_partial_stage_setup_is_reverted(self):
        # The firewall rule fails after the profile was changed: main() must
        # still run stage_path(False) (it used to sit outside the try).
        calls = []
        self.m.StageReceiver = lambda evidence: type('R', (), dict(
            start=lambda self: calls.append('start'), close=lambda self: calls.append('close')))()

        def stage_path(enable):
            calls.append(('stage', enable))
            if enable:
                raise ValueError('firewall refused')
        self.m.stage_path = stage_path
        evidence = self.base/'ev'
        argv = sys.argv
        sys.argv = ['production-ram-trial.py', 'observe', '--evidence', str(evidence), '--stage-receiver', '--seconds', '1']
        try:
            with self.assertRaisesRegex(ValueError, 'firewall refused'):
                self.m.main()
        finally:
            sys.argv = argv
        self.assertEqual(calls, [('stage', True), 'close', ('stage', False)])

    def test_stage_path_refuses_when_the_profile_does_not_take_effect(self):
        # NetworkManager 1.52 silently ignored a second address on the shared
        # profile during trial r1; a readback is now mandatory.
        nmcli = self.base/'bin/nmcli'
        nmcli.write_text('#!/bin/sh\ncase "$*" in *"connection show"*) printf "no\\n\\n169.254.77.1/30\\n" ;; esac\n')
        with self.assertRaisesRegex(ValueError, 'did not take effect'):
            self.m.stage_path(True)


if __name__ == '__main__':
    unittest.main(verbosity=2)
