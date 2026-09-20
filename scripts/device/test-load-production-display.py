#!/usr/bin/env python3
"""Actual successor + real inert children + compiled current panel/core callbacks.

No module, firmware or phone is activated. Target identity/ownership and provider
binding are explicit fixtures; the separate firmware suite exercises that reader.
"""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import shutil
import sys
import time
import types
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


BASE = load('display_order_fixture', ROOT/'scripts/device/test-display-loader-ordering.py')


class Production(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        BASE.Ordering.setUpClass()
        cls.addClassCleanup(BASE.Ordering.doClassCleanups)

    def setUp(self):
        f = self.f = BASE.Ordering('test_preparation_finishes_before_insertion_returns')
        f.setUp(); self.addCleanup(f.doCleanups)
        self.m = m = load('production_loader', ROOT/'scripts/device/load-production-display.py')
        self.original_modules = m.MODULES
        m.PAYLOAD = f.payload
        m.INSERT_SECONDS = 2; m.DISCOVERY_SECONDS = .15
        m.open_directory = f.m.open_directory
        m.exact_file = f.m.exact_file
        m.HELPER = f.m.HELPER
        m.subprocess = f.m.subprocess
        self.boot = 'fixture-boot'
        self.entered = []; self.events = []; self.closed = False
        self.fail_checkpoint = self.fail_after = self.corrupt_before = None
        self.firmware_ok = True
        self.firmware = types.SimpleNamespace(check=self.firmware_check, close=self.firmware_close)
        self.identity_ok = True
        def identity(boot):
            value = f.identity(boot)
            value['release'] = m.RELEASE
            return value
        self.e = types.SimpleNamespace(**vars(f.e)); self.e.identity = identity
        def blank(boot,authorize):
            value=f.blank(boot,authorize)
            return dict(value,write_bytes=2,physical_darkness_verified=False)
        def framebuffer(boot):
            value=f.framebuffer(boot)
            return dict(value,identity=identity(boot),device_opened=False,physical_scanout_verified=False)
        self.e.blank=blank;self.e.framebuffer=framebuffer
        m.MODULES = tuple((name,path,1,'fixture') for name,path,_,_ in m.MODULES)
        for _,path,*_ in m.MODULES:
            p = f.payload/'display-modules'/path; p.parent.mkdir(parents=True, exist_ok=True); p.write_bytes(b'x')
        names = {Path(path).name:name for name,path,*_ in m.MODULES}
        self.names = names
        def command(helper, directory, filename):
            name = names[filename]
            self.events.append(('spawn',name))
            script = 'import pathlib,time\n'
            script += f'pathlib.Path({str(f.sys/"module"/name)!r}).mkdir()\n'
            if name == 'panel_asus_rog5_ams678':
                # A real child refuses early panel insertion: MSM must already
                # be present and its checkpoint acknowledged by the parent.
                script += f'assert pathlib.Path({str(f.root/"msm-checked")!r}).exists(), "MSM checkpoint missing"\n'
                script += f'pathlib.Path({str(f.sys/"class/backlight"/f.e.NAME)!r}).touch()\n'
                if f.mode != 'no-fb': script += f'pathlib.Path({str(f.sys/"class/graphics/fb0")!r}).touch()\n'
                script += f'ack=pathlib.Path({str(f.root/"registration-observed")!r})\n'
                script += 'end=time.monotonic()+5\nwhile not ack.exists():\n if time.monotonic()>end: raise SystemExit(43)\n time.sleep(.005)\n'
                if f.mode == 'panel-fail': script += 'raise SystemExit(42)\n'
                if f.mode == 'timeout': script += 'time.sleep(10)\n'
            return [sys.executable,'-I','-B','-c',script]
        m.command = command
        actual_insert = m.insert
        def insert(*args):
            row = actual_insert(*args); name = names[row['filename']]
            self.events.append(('reaped',name)); f.insertions.append(row)
            if name == 'panel_asus_rog5_ams678' and row['status']=='PASS_INSERTION':
                if f.mode not in ('deferred','no-fb'):
                    f.rpc('prepare-fail' if f.mode=='prepare-fail' else 'prepare')
            if name == self.fail_after: self.firmware_ok = False
            if self.corrupt_before:
                p=f.payload/'display-modules'/next(r[1] for r in m.MODULES if r[0]==self.corrupt_before)
                p.write_bytes(b'changed'); self.corrupt_before=None
            return row
        m.insert = insert
        self.loader = m.Loader(self.e,lambda:self.firmware,self.checkpoint)

    def firmware_check(self):
        self.events.append(('firmware',self.firmware_ok))
        if not self.firmware_ok: raise ValueError('fixture firmware view changed')
        return True

    def firmware_close(self):
        self.closed = True

    def checkpoint(self, phase, boot):
        self.events.append(('checkpoint',phase))
        self.assertFalse((self.f.sys/'module/panel_asus_rog5_ams678').exists())
        if phase=='gpucc': self.assertFalse((self.f.sys/'module/msm').exists())
        if phase=='msm':
            self.assertTrue((self.f.sys/'module/msm').exists())
            (self.f.root/'msm-checked').touch()
        if phase==self.fail_checkpoint: raise ValueError('fixture provider unbound: '+phase)
        return True

    def enter(self,intent):
        self.entered.append(intent)
        return True

    def run_load(self):
        return self.loader.load_once(self.boot,lambda:self.f.health_ok,self.enter,lambda:self.f.cleanup_ok)

    def fail_load(self):
        with self.assertRaises(self.m.LoadError) as error:self.run_load()
        return error.exception.evidence

    def test_complete_actual_sequence_zero_and_closure(self):
        result=self.run_load()
        self.assertEqual(result['status'],'PASS_MODULES_AND_BLANK')
        self.assertEqual(len(result['insertions']),14)
        self.assertEqual(result['checkpoints'],['refgen','gpucc','msm'])
        self.assertEqual(self.events[-1],('firmware',True))
        self.assertEqual([v for k,v in self.events if k=='spawn'][-2:],['msm','panel_asus_rog5_ams678'])
        self.assertTrue(all(r['reaped'] and r['returncode']==0 for r in result['insertions']))
        self.assertEqual(len(self.f.zeros),1);self.assertEqual(self.f.zeros[0]['ret'],0)
        self.assertTrue(self.closed)
        self.assertEqual(self.entered[0]['maximum_insertions'],14)
        self.assertFalse(result['physical_darkness_verified'])
        self.fail_load();self.assertEqual(len(self.entered),1)

    def test_symbol_archive_order_is_not_activation_order(self):
        rows={r[0]:r for r in self.m.MODULES}
        manifest=json.loads((ROOT/'test-results/2026-09-20-production-display-modules-qualification.json').read_text())['embedded_manifest']
        self.m.MODULES=tuple(rows[r['name']] for r in manifest['modules'])
        result=self.fail_load()
        self.assertIn(('checkpoint','msm'),self.events)
        self.assertFalse(result['panel_attempted'])
        self.assertTrue(result['insertions'][-1]['reaped'])
        self.assertFalse(any(r['filename'] in ('msm.ko','panel-asus-rog5-ams678.ko')
                             for r in result['insertions']))

    def test_module_pins_match_qualified_archive(self):
        manifest=json.loads((ROOT/'test-results/2026-09-20-production-display-modules-qualification.json').read_text())['embedded_manifest']
        self.assertEqual(set(self.original_modules),{(r['name'],r['path'],r['bytes'],r['sha256']) for r in manifest['modules']})

    def test_refgen_binding_failure_prevents_gpucc(self):
        self.fail_checkpoint='refgen';result=self.fail_load()
        self.assertEqual(len(result['insertions']),1);self.assertFalse(self.f.zeros)

    def test_smmu_failure_prevents_msm_without_reprobe(self):
        self.fail_checkpoint='gpucc';result=self.fail_load()
        self.assertEqual(len(result['insertions']),2);self.assertEqual(result['driver_reprobes'],0)
        self.assertFalse(result['panel_attempted'])

    def test_adreno_binding_failure_prevents_panel(self):
        self.fail_checkpoint='msm';result=self.fail_load()
        self.assertEqual(len(result['insertions']),13);self.assertFalse(result['panel_attempted'])

    def test_real_firmware_owner_is_checked_and_closed(self):
        module=load('firmware_integration_fixture',ROOT/'scripts/device/test-display-firmware.py')
        fixture=module.Firmware('test_valid_and_idempotent_close')
        fixture.setUp();self.addCleanup(fixture.doCleanups)
        self.loader.firmware_factory=fixture.open
        result=self.run_load()
        self.assertEqual(result['status'],'PASS_MODULES_AND_BLANK')
        self.assertTrue(fixture.inputs.closed)

    def test_real_firmware_path_replacement_stops_before_msm(self):
        module=load('firmware_integration_fixture',ROOT/'scripts/device/test-display-firmware.py')
        fixture=module.Firmware('test_valid_and_idempotent_close')
        fixture.setUp();self.addCleanup(fixture.doCleanups)
        self.loader.firmware_factory=fixture.open
        actual=self.m.insert
        def replace(*args):
            row=actual(*args)
            if row['filename']=='gpucc-sm8350.ko':
                fixture.file().parent.rename(fixture.file().parent.with_name('moved'))
            return row
        self.m.insert=replace
        result=self.fail_load()
        self.assertEqual(len(result['insertions']),2)
        self.assertTrue(fixture.inputs.closed)
        self.assertFalse(self.f.zeros)

    def provider_fixture(self):
        fixture=load('provider_integration_fixture',ROOT/'scripts/device/test-display-providers.py')
        p=fixture.Providers();p.setUp();self.addCleanup(p.doCleanups)
        self.boot=fixture.BOOT
        self.f.sys=p.sys;self.e.SYS=p.sys
        # One shared sysfs tree. Simulate registration only after each inert
        # child succeeds; actual reader observes the same module/endpoint tree.
        for directory in (p.sys/'module').iterdir():shutil.rmtree(directory)
        (p.device('3d00000.gpu')/'driver').unlink()
        actual=self.m.insert
        def register(*args):
            row=actual(*args)
            if row['filename']=='msm.ko' and row['status']=='PASS_INSERTION':
                (p.device('3d00000.gpu')/'driver').symlink_to(p.sys/'bus/platform/drivers/adreno')
                for name,value in [('modeset','Y\n'),('skip_gpu','N\n'),('separate_gpu_kms','N\n')]:
                    p.write(p.sys/'module/msm/parameters'/name,value)
            return row
        self.m.insert=register
        def checkpoint(phase,boot):
            result=fixture.P.checkpoint(phase,boot,self.e.identity)
            self.checkpoint(phase,boot)
            return result
        self.loader.checkpoint=checkpoint
        return p

    def test_real_provider_readers_drive_complete_sequence(self):
        self.provider_fixture()
        self.assertEqual(self.run_load()['status'],'PASS_MODULES_AND_BLANK')

    def test_provider_loss_during_helpers_prevents_msm_insertion(self):
        p=self.provider_fixture()
        actual=self.m.insert
        def lose(*args):
            row=actual(*args)
            if row['filename']=='ubwc_config.ko':
                (p.device('3da0000.iommu')/'driver').unlink()
            return row
        self.m.insert=lose
        result=self.fail_load()
        self.assertFalse(any(r['filename']=='msm.ko' for r in result['insertions']))

    def test_real_missing_gmu_group_stops_before_msm(self):
        p=self.provider_fixture()
        (p.device('3d6a000.gmu')/'iommu_group').unlink()
        result=self.fail_load()
        self.assertEqual(len(result['insertions']),2)
        self.assertIn('IOMMU group absent',result['error']['reason'])
        self.assertFalse(self.f.zeros)

    def test_missing_firmware_owner_prevents_entry(self):
        self.loader.firmware_factory=lambda:None
        self.fail_load();self.assertFalse(self.entered)

    def test_firmware_failure_prevents_entry(self):
        self.firmware_ok=False;result=self.fail_load()
        self.assertFalse(self.entered);self.assertFalse(result['insertions']);self.assertTrue(self.closed)

    def test_firmware_change_after_gpucc_prevents_msm(self):
        self.fail_after='gpucc_sm8350';result=self.fail_load()
        self.assertEqual(len(result['insertions']),2);self.assertFalse(self.f.zeros)

    def test_firmware_change_after_panel_retains_independent_cleanup(self):
        self.fail_after='panel_asus_rog5_ams678';result=self.fail_load()
        self.assertIsNotNone(result['cleanup_blank']);self.assertIsNone(result['blank'])
        self.assertFalse(result['cleanup_errors']);self.assertTrue(self.closed)

    def test_uncertain_entry_does_not_retry(self):
        self.enter=lambda intent:1
        self.fail_load();self.fail_load();self.assertFalse(self.f.children)

    def test_changed_module_prevents_its_insertion(self):
        self.corrupt_before='msm';result=self.fail_load()
        self.assertIn('module file changed',result['error']['reason'])
        self.assertFalse(any(r['filename']=='msm.ko' for r in result['insertions']))

    def test_existing_module_prevents_entry(self):
        (self.f.sys/'module/msm').mkdir();self.fail_load();self.assertFalse(self.entered)

    def test_legacy_endpoint_release_is_refused(self):
        self.e.identity=lambda boot:dict(release='7.1.4-g136f75ae869a')
        result=self.fail_load();self.assertIn('production release',result['error']['reason'])
        self.assertFalse(self.entered)

    def test_failed_preparation_zero_property_is_not_success(self):
        self.f.mode='prepare-fail';result=self.fail_load()
        self.assertIsNone(result['blank']);self.assertTrue(result['cleanup_errors'])
        self.assertTrue(all(v['brightness']==0 and v['ret']!=0 for v in self.f.zeros))

    def test_missing_zero_receipt_cannot_pass(self):
        self.e.blank=lambda boot,authorize:None
        result=self.fail_load()
        self.assertFalse(self.f.zeros)
        self.assertTrue(result['cleanup_errors'])

    def test_missing_framebuffer_receipt_prevents_startup_zero(self):
        self.e.framebuffer=lambda boot:None
        result=self.fail_load()
        self.assertIsNone(result['blank'])

    def test_zero_write_error_remains_failed(self):
        self.f.mode='write-fail';result=self.fail_load()
        self.assertIsNone(result['blank']);self.assertTrue(result['cleanup_errors'])

    def test_panel_timeout_kills_and_reaps(self):
        self.f.mode='timeout';self.m.INSERT_SECONDS=.15
        result=self.fail_load();self.assertTrue(result['insertions'][-1]['reaped'])
        self.assertEqual(result['insertions'][-1]['returncode'],-9)

    def test_interruption_closes_children_firmware_and_descriptors(self):
        self.f.mode='interrupt';before=set(os.listdir('/proc/self/fd'))
        with self.assertRaises(KeyboardInterrupt):self.run_load()
        self.assertTrue(self.closed);self.assertEqual(set(os.listdir('/proc/self/fd')),before)
        self.assertTrue(all(c.poll() is not None for c in self.f.children))
        self.fail_load();self.assertEqual(len(self.entered),1)

    def test_missing_cleanup_owner_prevents_entry(self):
        self.f.cleanup_ok=False;self.fail_load();self.assertFalse(self.entered)

    def test_total_deadline_before_entry(self):
        self.m.TOTAL_SECONDS=-1;result=self.fail_load()
        self.assertIn('total deadline',result['error']['reason']);self.assertFalse(self.entered)

    def test_post_zero_health_loss_stays_failure(self):
        self.f.mode='post-zero-health';result=self.fail_load()
        self.assertIsNotNone(result['blank']);self.assertIsNotNone(result['cleanup_blank'])


class DirectoryLifetime(unittest.TestCase):
    def test_interruption_while_opening_directory_closes_both_fds(self):
        module=load('production_directory_lifetime',ROOT/'scripts/device/load-production-display.py')
        before=set(os.listdir('/proc/self/fd'))
        try:
            with patch.object(module.os,'fstat',side_effect=KeyboardInterrupt('directory open interruption')):
                with self.assertRaises(KeyboardInterrupt): module.open_directory(Path('/proc'))
            leaked=set(os.listdir('/proc/self/fd'))-before
        finally:
            # Preserve the failing-before observation without leaking its FD.
            for fd in set(os.listdir('/proc/self/fd'))-before:
                try:os.close(int(fd))
                except OSError:pass
        self.assertFalse(leaked, 'owned directory descriptor leaked')


if __name__=='__main__':unittest.main(verbosity=2)
