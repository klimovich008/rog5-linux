#!/usr/bin/env python3
"""A01 profile routing and runtime-result boundaries; no VM or phone access."""
import contextlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location('release_composition', Path(__file__).with_name('check-release-composition.py'))
M = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(M)


class ReleaseCompositionTest(unittest.TestCase):
    def test_offline_profile_does_not_create_a_consumable_claim(self):
        profile = M.PROFILES.load_profile()
        candidate = profile['id']
        before = dict(M.CLAIMS.CLAIMS)
        record = M.composition_record(candidate)
        self.assertEqual(record['target_bundle'], candidate)
        self.assertNotIn('state', record)
        self.assertNotIn('attempt_limit', record)
        self.assertEqual(M.CLAIMS.CLAIMS, before)
        with self.assertRaises(M.CLAIMS.ClaimError):
            M.CLAIMS.expected_record(candidate)
        with self.assertRaises(M.Blocked):
            M.composition_record(candidate + '-unknown')

    def test_historical_claim_resolution_is_unchanged(self):
        for candidate, raw in M.CLAIMS.CLAIMS.items():
            self.assertEqual(M.composition_record(candidate),
                             dict(line.split('=', 1) for line in raw.decode().splitlines()))

    def test_hardware_pending_requires_its_exact_vm_marker(self):
        # Stub expensive artifact/metadata operations, retaining the real VM log
        # acceptance predicate and main's pending-to-PASS transition. A successful
        # core-only log must not qualify the additional hardware module.
        release = '7.1.4-g05941d04803f'
        core = dict(name='core', path='core.ko', vermagic=release+' SMP')
        hardware = dict(name='hardware', path='hardware.ko', vermagic=release+' SMP')
        profile = M.PROFILES.load_profile()
        for fault in ('', 'missing', 'duplicate', 'failed', 'wrong-identity'):
            with self.subTest(fault=fault), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp); lower = root/'lower'; upper = root/'upper'
                lower.write_bytes(b'lower'); upper.write_bytes(b'upper')
                output = root/'result'
                argv = ['a01', '--candidate', profile['id'], '--output', str(output),
                        '--root-upper-image', str(upper)]
                for option in ('kernel', 'dtb', 'target-archive', 'root-image', 'boot-image'):
                    argv += ['--'+option, str(lower)]
                target = {'sbin/rog5-load-persistent-power-usb':
                          ([], (M.C.REPO/'scripts/device/load-persistent-root-power-usb.sh').read_bytes())}
                routed = []
                def inspect(args, checks):
                    for key in checks: checks[key] = 'PASS'
                    for key in ('module_load', 'root_runtime', 'firmware', 'timing_transport'):
                        checks[key] = 'NOT RUN'
                    return dict(profile='server-runtime', artifact_hashes={k:'fixture' for k in
                                ('kernel','dtb','initramfs','boot_bundle')},
                                plan=dict(target_release=release, cmdline='fixture'),
                                timing=dict(rollback_seconds=900))
                def select(*args):
                    if fault == 'wrong-identity': raise ValueError('successor artifact mismatch')
                    return profile
                def core_members(members, kind, *, module_profile):
                    routed.append(module_profile); return members, [dict(hardware, status='NOT RUN')]
                def radio(members, rows, release, *, module_profile):
                    routed.append(module_profile)
                    return {**members, 'a01-radio-modules/fixture.ko': ([], b'guest-only')}, rows, {}
                def unchanged(members, rows, release, *, module_profile):
                    self.assertNotIn('a01-radio-modules/fixture.ko', members)
                    routed.append(module_profile); return rows, []
                def append_hardware(members, rows, release, *, module_profile):
                    self.assertNotIn('a01-radio-modules/fixture.ko', members)
                    routed.append(module_profile); return [*rows, hardware], [hardware]
                vm_calls = []
                def vm(members, rows, *args, **kwargs):
                    self.assertIn('a01-radio-modules/fixture.ko', members)
                    vm_calls.append(rows)
                    log = '\n'.join('COMPOSITION_'+name+'_PASS' for name in M.C.MARKERS)
                    log += '\nCOMPOSITION_FIRMWARE_RUNTIME_PASS\nCOMPOSITION_RADIO_FIRMWARE_PASS\n'
                    log += 'COMPOSITION_MODULE_core\n'
                    if fault != 'missing': log += 'COMPOSITION_MODULE_hardware\n'
                    if fault == 'duplicate': log += 'COMPOSITION_MODULE_hardware\n'
                    log += 'COMPOSITION_VM_COMPLETE\n'
                    passed = M.C.vm_runtime_passed(log, 1 if fault == 'failed' else 0,
                                                 rows, firmware=True, radio=True)
                    return dict(status='PASS' if passed else 'FAIL', stage_frame='fixture')
                fixture = SimpleNamespace(FixtureUnavailable=RuntimeError,
                                          load_fixture=lambda *args: (None, {}))
                edge = SimpleNamespace(EdgeUnavailable=RuntimeError, inspect_edge=lambda *args: {})
                old_mask = os.umask(0o022)
                try:
                    with contextlib.ExitStack() as stack:
                        def mock(obj, name, **kwargs):
                            return stack.enter_context(patch.object(obj, name, **kwargs))
                        mock(sys, 'argv', new=argv)
                        mock(M.shutil, 'which', return_value='/fixture/tool')
                        mock(M, 'inspect', side_effect=inspect)
                        mock(M, 'target_members', return_value=target)
                        mock(M.ROOT_HASH, 'sha_file', return_value='fixture')
                        mock(M.C.ACCEPTANCE, 'sha_file', return_value='fixture')
                        mock(M.PROFILES, 'select_profile', side_effect=select)
                        mock(M.C, 'firmware_composition', return_value={})
                        mock(M.C, 'radio_firmware_composition', return_value={})
                        mock(M.C, 'core_module_members', side_effect=core_members)
                        mock(M.C, 'module_closure', return_value=[core])
                        mock(M.C, 'radio_module_composition', side_effect=radio)
                        mock(M.C, 'board_helper_refusals', return_value=[])
                        mock(M.C, 'indicator_module_composition', side_effect=unchanged)
                        mock(M.C, 'display_module_composition', side_effect=unchanged)
                        mock(M.C, 'hardware_module_composition', side_effect=append_hardware)
                        mock(M.C, 'load', side_effect=lambda name, path: edge if 'edge' in name else fixture)
                        mock(M.C, 'vm_runtime', side_effect=vm)
                        mock(M.RECEIVER.STAGES, 'parse_stage_record', return_value=SimpleNamespace(
                            stage='runtime', state='PASS', detail='composition', sequence=1, boot_id='fixture'))
                        stack.enter_context(patch('builtins.print'))
                        code = M.main()
                    result = json.loads((output/'result.json').read_text())
                    self.assertEqual(code, 0 if not fault else 1)
                    self.assertEqual(result['a01_qualified'], not fault)
                    self.assertFalse(result['release_qualified'])
                    if fault == 'wrong-identity':
                        self.assertFalse(vm_calls)
                    else:
                        self.assertEqual(len(routed), 5)
                        self.assertTrue(all(value is profile for value in routed))
                        self.assertEqual(vm_calls, [[core, hardware]])
                    if not fault:
                        self.assertEqual(result['checks']['module_load'], 'PASS')
                        self.assertEqual(result['hardware_modules']['software_load'], 'PASS')
                        self.assertEqual(result['hardware_modules']['physical_probe'], 'NOT RUN')
                        self.assertEqual(result['hardware_modules']['touch_input'], 'NOT RUN')
                    else:
                        self.assertNotEqual(result['checks']['module_load'], 'PASS')
                finally:
                    os.umask(old_mask)


if __name__ == '__main__': unittest.main()
