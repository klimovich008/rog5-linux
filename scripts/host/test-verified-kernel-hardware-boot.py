#!/usr/bin/env python3
"""05941 admission boundaries; no real claim or transport is used."""
import importlib.util
import os
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location('kernel_hardware_boot_test',
    Path(__file__).with_name('verified-kernel-hardware-boot.py'))
M = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(M)


def encode(fields):
    return ''.join(key+'='+value+'\n' for key, value in fields.items()).encode('ascii')


class Tests(unittest.TestCase):
    def setUp(self):
        self.fields = M.expected_fields()
        self.pin = self.fields['boot_image_sha256']

    def test_real_registry_has_no_authority_and_cannot_dispatch(self):
        self.assertNotIn(M.PROFILE_ID, M.CLAIMS.CLAIMS)
        with patch.dict(os.environ, ALLOW_TEMPORARY_BOOT='1', ALLOW_HEADLESS_LIVE_GATE='1'), \
             patch.object(M.BASE, 'validate_fastboot') as validate, \
             patch.object(M, 'sealed_snapshot') as snapshot, \
             patch.object(M.subprocess, 'run') as run:
            with self.assertRaises(M.CLAIMS.ClaimError):
                M.boot(Path('/fixture'), self.pin, M.SERIAL)
            validate.assert_not_called()
            snapshot.assert_not_called()
            run.assert_not_called()

    def test_exact_claim_requires_entered_state(self):
        with patch.object(M.CLAIMS, 'expected_record', return_value=encode(self.fields)), \
             patch.object(M.CLAIMS, 'verify_entered') as entered:
            self.assertEqual(M.canonical(self.pin, M.SERIAL), self.fields)
            entered.assert_called_once_with(M.PROFILE_ID)
        with patch.object(M.CLAIMS, 'expected_record', return_value=encode(self.fields)), \
             patch.object(M.CLAIMS, 'verify_entered', side_effect=ValueError('not entered')):
            with self.assertRaises(ValueError):
                M.canonical(self.pin, M.SERIAL)

    def test_every_identity_storage_and_evidence_field_is_bound(self):
        for key in self.fields:
            for operation in ('change', 'omit'):
                fields = self.fields.copy()
                if operation == 'change':
                    fields[key] += '-wrong'
                else:
                    del fields[key]
                with self.subTest(key=key, operation=operation), \
                     patch.object(M.CLAIMS, 'expected_record', return_value=encode(fields)), \
                     patch.object(M.CLAIMS, 'verify_entered') as entered:
                    with self.assertRaises(ValueError):
                        M.canonical(self.pin, M.SERIAL)
                    entered.assert_not_called()

    def test_ambiguous_extra_and_r01_records_refuse(self):
        good = encode(self.fields)
        for raw in (good+b'candidate='+M.PROFILE_ID.encode()+b'\n', good+b'extra=value\n',
                    good+b'malformed\n', good[:-1], b'x'*8193,
                    M.CLAIMS.expected_record(M.RAM.PROFILE)):
            with self.subTest(raw=raw[:50]), \
                 patch.object(M.CLAIMS, 'expected_record', return_value=raw), \
                 patch.object(M.CLAIMS, 'verify_entered') as entered:
                with self.assertRaises(ValueError):
                    M.canonical(self.pin, M.SERIAL)
                entered.assert_not_called()

    def test_wrong_device_or_image_refuses_before_claim_access(self):
        with patch.object(M.CLAIMS, 'expected_record') as record:
            for pin, serial in ((self.pin, 'another-phone'), ('a'*64, M.SERIAL)):
                with self.assertRaises(ValueError):
                    M.canonical(pin, serial)
            record.assert_not_called()
        with patch.object(M.RAM, 'sealed_snapshot') as snapshot:
            with self.assertRaises(ValueError):
                M.sealed_snapshot(Path('/fixture'), 'a'*64)
            snapshot.assert_not_called()

    def test_profile_or_shared_primitive_drift_refuses(self):
        for obj, name, value in ((M, 'PROFILE_SHA256', 'a'*64),
                                  (M.RAM, 'IMAGE_SIZE', 100663296),
                                  (M.RAM, 'SERIAL', 'another-phone')):
            with self.subTest(name=name), patch.object(obj, name, value):
                with self.assertRaises(ValueError):
                    M.expected_fields()
        self.assertEqual(M.BASE.PARTITION_SIZE, 100663296)
        self.assertEqual(M.RAM.PROFILE, 'headless-recovery-negative-v1')

    def test_capacity_evidence_replays_raw_response_and_refuses_tampering(self):
        result = subprocess.CompletedProcess([], 0, b'', b'(bootloader) max-download-size: 536870912\n')
        with patch.object(M.BASE, 'validate_fastboot'), \
             patch.object(M.subprocess, 'run', return_value=result) as run:
            evidence = M.download_capacity(M.SERIAL)
            self.assertEqual(M.replay_capacity(evidence), 536870912)
            self.assertEqual(run.call_args.args[0],
                [str(M.BASE.FASTBOOT), '-s', M.SERIAL, 'getvar', 'max-download-size'])
            with self.assertRaises(ValueError):
                M.download_capacity('another-phone')
            self.assertEqual(run.call_count, 1)
        evidence['max_download_size'] += 1
        with self.assertRaises(ValueError):
            M.replay_capacity(evidence)

    def test_boot_uses_own_gate_once_and_closes_fd_even_on_transport_failure(self):
        for failure in (False, True):
            fd = os.memfd_create('test-kernel-hardware-boot')
            def run(argv, **kwargs):
                self.assertEqual(argv, [str(M.BASE.FASTBOOT), '-s', M.SERIAL,
                                       'boot', f'/proc/self/fd/{fd}'])
                self.assertEqual(kwargs['pass_fds'], (fd,))
                self.assertTrue(kwargs['check'])
                os.fstat(fd)
                if failure:
                    raise subprocess.CalledProcessError(1, argv)
            with self.subTest(failure=failure), \
                 patch.dict(os.environ, ALLOW_TEMPORARY_BOOT='1', ALLOW_HEADLESS_LIVE_GATE='1'), \
                 patch.object(M, 'canonical') as gate, patch.object(M.BASE, 'validate_fastboot'), \
                 patch.object(M, 'sealed_snapshot', return_value=fd), \
                 patch.object(M.subprocess, 'run', side_effect=run) as dispatch, \
                 patch.object(M.RAM, 'boot') as old_boot:
                if failure:
                    with self.assertRaises(subprocess.CalledProcessError):
                        M.boot(Path('/fixture'), self.pin, M.SERIAL)
                else:
                    M.boot(Path('/fixture'), self.pin, M.SERIAL)
                gate.assert_called_once_with(self.pin, M.SERIAL)
                self.assertEqual(dispatch.call_count, 1)
                old_boot.assert_not_called()
            with self.assertRaises(OSError):
                os.fstat(fd)

    def test_no_environment_means_no_execution(self):
        with patch.dict(os.environ, {}, clear=True), patch.object(M, 'canonical') as gate:
            with self.assertRaises(ValueError):
                M.boot(Path('/fixture'), self.pin, M.SERIAL)
            gate.assert_not_called()


if __name__ == '__main__':
    unittest.main()
