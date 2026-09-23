#!/usr/bin/env python3
"""Exercise the production RAM-trial launcher against fake sysfs, fastboot,
ssh and nmcli executables. No phone, USB device or network is touched."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[2]
SOURCE = REPO/'scripts/host/production-ram-trial.py'
SERIAL = 'ROG5-SERIAL-REDACTED'

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
        silent = self.base/'silent'
        silent.mkdir()
        self.usb.unlink()  # nothing enumerates after the boot: R1 once
        summary = self.m.observe(silent, seconds=0.4, interval=0.05, hang_seconds=0.1)
        self.assertEqual(summary['rescue_prompts'], ['R1'])
        prompts = [json.loads(line).get('rescue_prompt') for line in
                   (silent/'transitions.jsonl').read_text().splitlines()]
        self.assertEqual([p for p in prompts if p], ['R1'])
        self.assertEqual(summary['final_state'], 'absent')

    def test_profile_activation_is_idempotent(self):
        (self.bin/'nmcli').write_text('#!/bin/sh\nprintf "%s\\n" "$*" >>"$FAKE_LOG"\n'
                                      'case "$*" in *"device show"*) echo rog5-standalone-shared ;; esac\n')
        self.assertFalse(self.m.use_address('10.77.0.2'))
        self.assertNotIn('connection up', self.log.read_text())
        self.assertTrue(self.m.use_address('169.254.77.2'))
        self.assertIn('connection up rog5-fallback-usb-ssh ifname enp4s0f3u1u2', self.log.read_text())
        with self.assertRaisesRegex(ValueError, 'unknown target address'):
            self.m.use_address('10.0.0.2')


if __name__ == '__main__':
    unittest.main(verbosity=2)
