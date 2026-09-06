#!/usr/bin/env python3
"""Bounded H03 replay; no credentials, network or phone endpoints."""
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest import mock
import subprocess
import os
import json
import hashlib
import gzip
import shutil
import contextlib
import io
import sys

spec = importlib.util.spec_from_file_location('charging', Path(__file__).with_name('check-charging-regulation.py'))
M = importlib.util.module_from_spec(spec)
spec.loader.exec_module(M)

IDENTITY = dict(boot_id='11111111-1111-4111-8111-111111111111',
                release='7.1.4-g123456789abc', bundle='fixture', serial='fixture')


def frame(**overrides):
    values = dict(boot_before=IDENTITY['boot_id'], boot_after=IDENTITY['boot_id'],
                  kernel=IDENTITY['release'], cmdline='rog5.bundle=fixture rog5.recovery_timeout=900',
                  wifi='inactive', uptime_before='1000.00', uptime_after='1000.10',
                  capacity='100', current_ua='0', counter_uah='3000000', voltage_uv='8590000',
                  voltage_max_uv='8900000', temp_dc='299', usb_online='1', usb_voltage_uv='5000000',
                  usb_current_ua='350000', input_limit_ua='500000', status='Full', health='Good',
                  data_role='host [device]', power_role='source [sink]')
    values.update(overrides)
    return b''.join((key+'\0present\0'+values[key]+'\0').encode() for key in M.FIELD_NAMES)


class Clock:
    def __init__(self): self.now=100.0
    def __call__(self): return self.now
    def sleep(self, seconds): self.now += seconds


class Tests(unittest.TestCase):
    @unittest.skipUnless(os.environ.get('ROG5_H03_TEST_ARCHIVE'),
                         'exact sealed archive integration is explicitly selected')
    def test_exact_sealed_probe(self):
        sealed=M.load('charging_sealed','run-sealed-busybox.py')
        archive=Path(os.environ['ROG5_H03_TEST_ARCHIVE'])
        compressed=archive.read_bytes()
        members=sealed.ARCHIVE.entries(gzip.decompress(compressed))
        composition=M.load('charging_composition_test','check-rescue-root-composition.py')
        release=composition.archive_parameters(members)['KERNEL_RELEASE']
        script,firmware=M.firmware_probe(archive,dict(IDENTITY,release=release),
            dict(initramfs_size=str(len(compressed)),initramfs_sha256=hashlib.sha256(compressed).hexdigest(),
                 target_release=release))
        self.assertEqual(len(firmware['files']),29)
        self.assertIn('/run/rog5-charge-firmware',script)
        qemu=shutil.which('qemu-aarch64-static')
        self.assertIsNotNone(qemu)
        values=frame().decode().split('\0')
        values=dict(zip(values[::3],values[2::3]))
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/'root';root.mkdir()
            sealed.extract(members,root)
            (root/'rog5-qemu').touch()
            fixture=Path(tmp)/'fixture'
            fields={'proc/sys/kernel/random/boot_id':IDENTITY['boot_id'],
                    'proc/cmdline':values['cmdline'],'proc/uptime':'1000.00 0.00',
                    'sys/class/typec/port0/data_role':values['data_role'],
                    'sys/class/typec/port0/power_role':values['power_role']}
            fields.update({'sys/class/power_supply/'+path:values[name]
                           for name,path in M.ATTRIBUTES.items()})
            for path,value in fields.items():
                target=fixture/path;target.parent.mkdir(parents=True,exist_ok=True)
                target.write_text(value+'\n')
            command=['bwrap','--unshare-all','--die-with-parent','--new-session',
                     '--ro-bind',str(root),'/', '--ro-bind',qemu,'/rog5-qemu',
                     '--ro-bind',str(fixture/'proc'),'/proc',
                     '--ro-bind',str(fixture/'sys'),'/sys',
                     '--clearenv','--setenv','QEMU_UNAME',IDENTITY['release'],
                     '/rog5-qemu','-r',IDENTITY['release'],'/bin/busybox','sh','-s']
            result=subprocess.run(command,input=M.sample_script().encode(),capture_output=True,timeout=15)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertFalse(result.stderr)
            self.assertEqual(M.parse_frame(result.stdout,IDENTITY,900)['capacity'],100)
            # Missing and unreadable sysfs simulation must survive shell framing,
            # but cannot qualify as a complete H03 measurement.
            target=fixture/'sys/class/power_supply/qcom-battmgr-bat/capacity'
            target.unlink()
            for state in ('absent','error'):
                if state=='error': target.mkdir()
                result=subprocess.run(command,input=M.sample_script().encode(),capture_output=True,timeout=15)
                self.assertEqual(result.returncode,0,result.stderr)
                self.assertIn(('capacity\0'+state+'\0').encode(),result.stdout)
                with self.assertRaises(ValueError): M.parse_frame(result.stdout,IDENTITY,900)
        print(json.dumps(dict(archive_sha256=hashlib.sha256(compressed).hexdigest(),
                              probe_sha256=hashlib.sha256(M.sample_script().encode()).hexdigest(),
                              scope='sealed BusyBox and simulated sysfs; no hardware qualification')))

    def test_missing_prerequisites_are_blocked_before_contact(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);argv=['h03','--profile','fixture','--expected-candidate','fixture']
            for name in ('cycle','execution-record','manifest','archive','boot-image','identity-file','known-hosts'):
                argv+=['--'+name,str(root/name)]
            argv+=['--output',str(root/'output')]
            previous=os.umask(0o077)
            try:
                with mock.patch.object(sys,'argv',argv),mock.patch.object(M.subprocess,'run') as run, \
                        mock.patch.object(M.D.CAPTURE.ACCEPTANCE,'source_identity',return_value={'fixture':True}), \
                        contextlib.redirect_stdout(io.StringIO()):
                    self.assertEqual(M.main(),77);run.assert_not_called()
            finally: os.umask(previous)
            result=json.loads((root/'output/result.json').read_text())
            self.assertEqual(result['status'],'BLOCKED');self.assertFalse(result['h03_qualified'])

    def test_contract_deadline_and_sample_count_agree(self):
        contract=json.loads((M.D.REPO/'configs/release-acceptance.json').read_text())
        test=next(row for row in contract['tests'] if row['id']=='H03')
        self.assertEqual(test['deadline_seconds'],M.DEADLINE)
        self.assertEqual((M.WINDOW,M.CADENCE,M.COUNT),(600,10,61))

    def test_failed_transport_retains_reply_without_retry(self):
        clock=Clock()
        reply=subprocess.CompletedProcess([],1,b'partial telemetry',b'read failed')
        with tempfile.TemporaryDirectory() as temp, \
                mock.patch.object(M.D,'host_gate'), mock.patch.object(M.D,'credential'), \
                mock.patch.object(M.D,'ssh_command',return_value=['ssh']), \
                mock.patch.object(M.subprocess,'run',return_value=reply) as run:
            with self.assertRaises(ValueError):
                M.observe(IDENTITY,900,lambda:M.collect(IDENTITY,Path('/key'),Path('/hosts'),'probe'),
                          Path(temp),760,clock=clock,sleep=clock.sleep)
            self.assertEqual((Path(temp)/'sample-00.raw').read_bytes(),reply.stdout)
            self.assertEqual((Path(temp)/'sample-00.stderr').read_bytes(),reply.stderr)
            self.assertEqual(run.call_count,1)

    def test_identity_gate_precedes_credentials_and_transport(self):
        with mock.patch.object(M.D,'host_gate',side_effect=ValueError('wrong topology')), \
                mock.patch.object(M.D,'credential') as credential, \
                mock.patch.object(M.subprocess,'run') as run:
            with self.assertRaises(ValueError):
                M.collect(IDENTITY,Path('/key'),Path('/hosts'),'probe')
            credential.assert_not_called();run.assert_not_called()

    def test_exact_firmware_frame(self):
        row=M.parse_frame(frame(), IDENTITY, 900)
        self.assertEqual(row['role'], 'device/sink')
        self.assertEqual(row['current_ua'], 0)

    def test_missing_error_duplicate_or_oversized_fields_fail(self):
        good=frame()
        for raw in (good[:-1], good+good, good.replace(b'capacity\0present\0', b'capacity\0absent\0'),
                    good.replace(b'capacity\0present\0', b'capacity\0error\0'), b'x'*32769):
            with self.subTest(raw=raw[:40]), self.assertRaises(ValueError):
                M.parse_frame(raw, IDENTITY, 900)

    def test_identity_role_and_numeric_changes_fail(self):
        for update in (dict(boot_after='other'), dict(kernel='other'), dict(wifi='active'),
                       dict(cmdline='rog5.bundle=fixture rog5.bundle=other rog5.recovery_timeout=900'),
                       dict(data_role='[host] device'), dict(power_role='[source] sink'),
                       dict(capacity='True'), dict(current_ua='1.2'), dict(temp_dc='400'),
                       dict(uptime_after='999.00'), dict(uptime_after='nan')):
            with self.subTest(update=update), self.assertRaises(ValueError):
                M.parse_frame(frame(**update), IDENTITY, 900)

    def test_full_series_is_real_bounded_and_never_qualifies_alone(self):
        clock=Clock(); calls=[]
        def fetch():
            calls.append(clock()); clock.now+=0.1
            return frame(uptime_before=str(1000+clock.now), uptime_after=str(1000.05+clock.now))
        with tempfile.TemporaryDirectory() as temp:
            samples=M.observe(IDENTITY, 900, fetch, Path(temp), 760, clock=clock, sleep=clock.sleep)
            outcome=M.REGULATION.evaluate_full(samples)
            self.assertEqual(len(calls), 61)
            self.assertGreaterEqual(outcome['span_seconds'], 600)
            self.assertFalse(outcome['h03_qualified'])
            self.assertEqual(len(list(Path(temp).glob('sample-*.raw'))), 61)

    def test_loss_or_unsafe_data_stops_without_retry(self):
        for failure in ('loss', 'thermal', 'late', 'stale'):
            clock=Clock(); calls=[]
            def fetch():
                calls.append(clock()); clock.now+=0.1
                if len(calls)==2:
                    if failure=='loss': raise OSError('transport disappeared')
                    if failure=='thermal': return frame(temp_dc='400')
                    if failure=='late': clock.now+=3
                    if failure=='stale': return frame()
                return frame(uptime_before=str(1000+clock.now), uptime_after=str(1000.05+clock.now))
            with tempfile.TemporaryDirectory() as temp:
                with self.subTest(failure=failure), self.assertRaises((ValueError, OSError)):
                    M.observe(IDENTITY, 900, fetch, Path(temp), 760, clock=clock, sleep=clock.sleep)
                self.assertEqual(len(calls), 2)

    def test_deadline_prevents_another_sample(self):
        clock=Clock(); calls=[]
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaises(ValueError):
                M.observe(IDENTITY, 900, lambda:calls.append(1), Path(temp), 105,
                          clock=clock, sleep=clock.sleep)
        self.assertFalse(calls)


if __name__=='__main__': unittest.main(verbosity=2)
