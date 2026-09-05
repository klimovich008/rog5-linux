#!/usr/bin/env python3
"""Offline fixture/gate checks. Actual Arch execution is a separate artifact run."""
import copy
import importlib.util
import json
from pathlib import Path
import stat
import subprocess
import tempfile
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location('composition', Path(__file__).with_name('check-rescue-root-composition.py'))
M = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(M)


class CompositionTest(unittest.TestCase):
    def test_sealed_module_load_order_and_dependency_refusals(self):
        item = lambda data: ([0, stat.S_IFREG | 0o644, 0, 0, 1], data)
        elf = bytearray(64)
        elf[:6] = b'\x7fELF\x02\x01'
        elf[16:20] = b'\x01\x00\xb7\x00'
        members = {
            'init': item(b'insmod /rog5-ufs-modules/core.ko || return 1\n'
                         b'if ! power_usb_failure=$(/sbin/rog5-load-persistent-power-usb); then\n'
                         b' :\nfi\nload_deferred_ufs_modules\n'),
            'sbin/rog5-load-persistent-power-usb': item(
                b'load_module power.ko power power\n'),
            'rog5-ufs-modules/core.ko': item(bytes(elf)),
            'rog5-power-usb-modules/power.ko': item(bytes(elf)),
        }
        release='7.1.4-g359318de534f'
        invalid_dependency=''
        def inspect(argv, **kwargs):
            name=Path(argv[-1]).stem
            return {'name':name, 'vermagic':release+' SMP preempt mod_unload aarch64',
                    'depends':invalid_dependency or ('power' if name=='core' else '')}[argv[2]]+'\n'
        with patch.object(M.subprocess,'check_output',side_effect=inspect):
            result=M.module_closure(members,release)
            self.assertEqual([row['name'] for row in result],['power','core'])
            for mutation in ('missing','extra','alias','wrong-arch','wrong-release','order'):
                changed=copy.deepcopy(members)
                expected=release
                if mutation=='missing': del changed['rog5-ufs-modules/core.ko']
                if mutation=='extra': changed['rog5-ufs-modules/extra.ko']=item(bytes(elf))
                if mutation=='alias': changed['rog5-ufs-modules/core.ko'][0][1]=stat.S_IFLNK|0o777
                if mutation=='wrong-arch': changed['rog5-ufs-modules/core.ko']=item(b'not ARM ELF')
                if mutation=='wrong-release': expected=release+'wrong'
                if mutation=='order':
                    changed['init']=item(b'insmod /rog5-power-usb-modules/power.ko || return 1\n')
                    changed['sbin/rog5-load-persistent-power-usb']=item(b'load_module core.ko core core\n')
                with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                    M.module_closure(changed,expected)
            for invalid_dependency in ('missing', 'core', '../power', 'power\ncore'):
                with self.subTest(dependency=invalid_dependency), self.assertRaisesRegex(
                        ValueError,'dependency absent or loaded too late'):
                    M.module_closure(members,release)
            with patch.object(M.time,'monotonic',side_effect=[0,11]), self.assertRaisesRegex(
                    ValueError,'metadata deadline exceeded'):
                M.module_closure(members,release)

    def members(self):
        values = dict(KERNEL_RELEASE='7.1.4-g359318de534f', UFS_STORAGE_MODE='read-only',
                      PROBE_BOOT_ID='staged-seal', NATIVE_ROOT_MODE='1',
                      SSH_DIAGNOSTIC_MODE='0', PERSISTENT_OVERLAY_MODE='0')
        item = lambda data: ([0, stat.S_IFREG | 0o755], data)
        return {
            'init': item(M.SEALED.ARCHIVE.render_boot_template(M.REPO/'initramfs/persistent-root-init', values)),
            'usr/local/sbin/rog5-p2-attest': item(M.SEALED.ARCHIVE.render_boot_template(
                M.REPO/'initramfs/persistent-root-attest', {k: values[k] for k in (
                    'UFS_STORAGE_MODE', 'PROBE_BOOT_ID', 'NATIVE_ROOT_MODE', 'PERSISTENT_OVERLAY_MODE')})),
            'sbin/rog5-load-persistent-power-usb': item((M.REPO/'scripts/device/load-persistent-root-power-usb.sh').read_bytes()),
        }

    def test_paired_archive_and_stale_producer_consumer(self):
        members = self.members()
        self.assertEqual(M.archive_parameters(members)['NATIVE_ROOT_MODE'], '1')
        for name in members:
            changed = copy.deepcopy(members)
            changed[name] = (changed[name][0], changed[name][1] + b'\n# stale\n')
            with self.subTest(member=name), self.assertRaises(ValueError):
                M.archive_parameters(changed)

    def test_unresolved_parameter_optional_radio_and_wrong_profile(self):
        for name, data in (('extra', b'@OUTER_SECONDS@'),
                           ('rog5-native-wifi/init', b'activation')):
            members = self.members()
            members[name] = ([0, stat.S_IFREG | 0o755], data)
            with self.subTest(name=name), self.assertRaises(ValueError):
                M.archive_parameters(members)
        members = self.members()
        fields, data = members['init']
        members['init'] = fields, data.replace(b'expected_native_root_mode=1', b'expected_native_root_mode=0')
        with self.assertRaises(ValueError):
            M.archive_parameters(members)

    def test_driver_uses_sealed_functions_and_rejects_missing_or_duplicate(self):
        sealed = ''.join(name+'() {\n echo sealed-'+name+'\n}\n' for name in M.FUNCTIONS)
        result = M.driver(sealed)
        for name in M.FUNCTIONS:
            self.assertIn('echo sealed-'+name, result)
        self.assertNotIn('switch_root', result)
        for broken in ('', sealed + sealed):
            with self.assertRaises(ValueError):
                M.driver(broken)

    def test_driver_supplies_observer_lifetime_without_claiming_deployed_timing(self):
        sealed = ''.join(name+'() {\n :\n}\n' for name in M.FUNCTIONS if name != 'prepare_runtime')
        sealed += 'prepare_runtime() {\n test "$recovery_timeout" -gt 0\n}\n'
        script = M.driver(sealed).split('echo COMPOSITION_PREPARE_PASS')[0]
        result = subprocess.run(['sh','-c',script],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertIn('fixture, not deployed timing',script)

    def test_driver_verifies_present_observer_and_rejects_stale_observer_bytes(self):
        members=self.members()
        fields=[0, stat.S_IFREG | 0o755]
        members['usr/local/sbin/rog5-startup-observer']=(fields,b'#!/bin/sh\nexit 0\n')
        with self.assertRaises(ValueError): M.archive_parameters(members)
        self.assertIn('/run/systemd/system/rog5-startup-observer.service',
                      M.driver(members['init'][1].decode()))

    def test_mount_requires_exact_ro_loop_backing_and_no_recovery(self):
        entry = dict(target='/private/root', source='/dev/loop7', fstype='ext4',
                     options='ro,nodev,nosuid,noexec,norecovery')
        def check(record=entry, backing='/private/root.ext4\n', ro='1\n'):
            outputs = [json.dumps({'filesystems': [record]}), backing, ro]
            with patch.object(M.subprocess, 'check_output', side_effect=outputs):
                return M.verify_mount(Path('/private/root'), Path('/private/root.ext4'))
        self.assertEqual(check(), entry)
        for field, value in (('source', '/dev/sda'), ('target', '/private'),
                             ('fstype', 'overlay'), ('options', 'rw,nodev,nosuid,norecovery'),
                             ('options', 'ro,nodev,nosuid'), ('options', 'ro,nosuid,norecovery')):
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                check(dict(entry, **{field: value}))
        for backing, ro in (('/wrong/image\n', '1\n'), ('/private/root.ext4\n', '0\n')):
            with self.assertRaises(ValueError):
                check(backing=backing, ro=ro)

    def test_component_receipt_cannot_qualify_full_release(self):
        with tempfile.TemporaryDirectory() as tmp:
            artifact = Path(tmp)/'artifact'
            artifact.write_bytes(b'fixture')
            roles = M.ACCEPTANCE.ARTIFACT_ROLES - {'boot_bundle'}
            record = dict(format='rog5-release-inputs-v1', candidate_id='component-only',
                          source_revision='a'*40, artifacts={role: dict(path=str(artifact),
                          size=7, sha256=M.ACCEPTANCE.sha_file(artifact)) for role in roles})
            receipt = Path(tmp)/'receipt.json'; receipt.write_text(json.dumps(record))
            self.assertEqual(set(M.ACCEPTANCE.verify_release(receipt, required_roles=roles)['artifacts']), roles)
            for required in (None, set(), {'unknown'}):
                with self.assertRaises(ValueError):
                    M.ACCEPTANCE.verify_release(receipt, required_roles=required)


if __name__ == '__main__':
    unittest.main(verbosity=2)
