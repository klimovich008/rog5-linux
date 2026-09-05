#!/usr/bin/env python3
"""Exercise the real standalone archive builder on disposable nonbootable input."""
import gzip
import configparser
import importlib.util
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location('composer', REPO/'scripts/device/build-native-wifi-boot-initramfs.py')
M = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(M)


class RescueComposition(unittest.TestCase):
    def test_final_archive_refreshes_power_watchdog_and_attestation_together(self):
        members = {}
        for name in ('init', 'shutdown', 'sbin/rog5-load-persistent-power-usb',
                     'usr/local/sbin/rog5-p2-attest'):
            M.add(members, name, b'#!/bin/sh\necho historical\n', 0o100755)
        M.add(members, 'opt/preserved-firmware', b'unchanged-fixture', 0o100644)
        base = gzip.compress(M.encode(members), mtime=0)
        with tempfile.TemporaryDirectory(prefix='rog5-rescue-composition-') as temp:
            root = Path(temp)
            source, output = root/'base.gz', root/'output.gz'
            source.write_bytes(base)
            subprocess.run(['sh', str(REPO/'scripts/device/build-persistent-root-standalone-initramfs.sh'),
                            str(source), str(output)], check=True, capture_output=True,
                           env=dict(os.environ, EXPECTED_STANDALONE_BASE_SHA256=M.sha(base)), timeout=30)
            built = M.entries(gzip.decompress(output.read_bytes()))
            built = {name.removeprefix('./'): value for name, value in built.items()}
            self.assertEqual(built['sbin/rog5-load-persistent-power-usb'][1],
                             (REPO/'scripts/device/load-persistent-root-power-usb.sh').read_bytes())
            self.assertIn(b'battery_health', built['sbin/rog5-load-persistent-power-usb'][1])
            self.assertIn(b'attested_boot_id=$watchdog_boot_id', built['init'][1])
            self.assertIn(b'identity_boot_id=', built['init'][1])
            self.assertEqual(built['usr/local/sbin/rog5-persistent-ssh-identity'][1],
                             (REPO/'initramfs/persistent-ssh-identity').read_bytes())
            self.assertIn(b'attested_boot_id=$current_boot_id', built['usr/local/sbin/rog5-p2-attest'][1])
            for name in ('init', 'usr/local/sbin/rog5-p2-attest'):
                self.assertNotIn(b'@EXPECTED_', built[name][1])
            self.assertEqual(built['opt/preserved-firmware'][1], b'unchanged-fixture')
            self.assertEqual(built['usr/local/sbin/rog5-startup-observer'][1],
                             (REPO/'initramfs/persistent-startup-observer').read_bytes())
            self.assertIn(b'RuntimeMaxSec=$recovery_timeout', built['init'][1])
            observer_exec, = [line for line in (REPO/'initramfs/persistent-root-init').read_bytes().splitlines()
                              if line.startswith(b'ExecStart=/run/rog5-startup-observer ')]
            # Behavior/deadline tests render this generator. Here prove the
            # assembled archive carries that exact line, not an older copy.
            self.assertTrue(observer_exec in built['init'][1], 'assembled observer invocation is stale')
            def unit(name):
                marker=f"cat >/run/systemd/system/{name}.service <<'EOF'\n"
                text=built['init'][1].decode()
                self.assertEqual(text.count(marker),1)
                parsed=configparser.ConfigParser(interpolation=None)
                parsed.read_string(text.split(marker,1)[1].split('\nEOF',1)[0])
                return parsed['Unit']
            p2=unit('rog5-p2-ready')
            identity=unit('rog5-persistent-ssh-identity')
            for dependent in (p2,identity):
                self.assertIn('rog5-early-sshd.service',dependent['Wants'].split())
                self.assertIn('rog5-early-sshd.service',dependent['After'].split())
                self.assertNotIn('rog5-early-sshd.service',dependent.get('Requires','').split())
            self.assertEqual(unit('rog5-persistent-state')['Requires'],'rog5-p2-ready.service')
            self.assertEqual(identity['Requires'],'rog5-persistent-state.service')
            self.assertEqual(unit('rog5-tailscaled')['Requires'],'rog5-persistent-state.service')
            self.assertTrue(b"systemctl is-active --quiet rog5-early-sshd.service ||" in
                            built['usr/local/sbin/rog5-p2-attest'][1], 'initial SSH gate removed')


if __name__ == '__main__':
    unittest.main(verbosity=2)
