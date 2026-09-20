#!/usr/bin/env python3
"""Production assembly/receipts with real loader and endpoint; hardware fixtures."""
import copy
import importlib.util
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[2]


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m


C=load('display_component',ROOT/'scripts/device/display-component.py')
L=load('loader_fixture',ROOT/'scripts/device/test-load-production-display.py')
EF=load('endpoint_fixture',ROOT/'scripts/device/test-display-endpoint.py')


def pipeline(case, mode='normal', execute=True):
    h=L.Production('test_complete_actual_sequence_zero_and_closure');h.setUp();case.addCleanup(h.doCleanups)
    ep=EF.EndpointFixture('test_success_metadata_zero_and_identity');ep.setUp();case.addCleanup(ep.doCleanups)
    component=C.Component(ep.identity_check)
    # The assembled source bytes are verified unchanged. Its environment and
    # hardware syscalls are explicit fixtures, not target admission.
    g=component.endpoint.identity.__func__.__globals__
    g.update(SYS=ep.sys,PROC=ep.proc,DESCRIPTOR=ep.descriptor)
    m=component.modules
    for key in ('PAYLOAD','HELPER','MODULES','open_directory','exact_file','subprocess'):
        setattr(m,key,getattr(h.m,key))
    m.INSERT_SECONDS=2;m.DISCOVERY_SECONDS=.15
    h.f.mode=mode
    h.f.sys=ep.sys;h.e=component.endpoint;h.f.e.NAME=EF.E.NAME;h.boot=EF.BOOT
    for path in (ep.sys/'module').iterdir():shutil.rmtree(path)
    (ep.sys/'class/backlight'/EF.E.NAME).unlink();(ep.sys/'class/graphics/fb0').unlink()
    component.loader.firmware_factory=lambda:h.firmware
    component.loader.checkpoint=h.checkpoint
    h.loader=component.loader;h.m=m
    def command(helper,directory,filename):
        name=h.names[filename]
        script='import pathlib,time\n'
        script+=f'pathlib.Path({str(ep.sys/"module"/name)!r}).mkdir()\n'
        if name=='panel_asus_rog5_ams678':
            script+=f'assert pathlib.Path({str(h.f.root/"msm-checked")!r}).exists()\n'
            script+=f'pathlib.Path({str(ep.sys/"class/backlight"/EF.E.NAME)!r}).symlink_to({str(ep.backlight)!r})\n'
            script+=f'pathlib.Path({str(ep.sys/"class/graphics/fb0")!r}).symlink_to({str(ep.fb)!r})\n'
        return [sys.executable,'-I','-B','-c',script]
    m.command=command
    actual=m.insert
    def insert(*args):
        row=actual(*args)
        if row['filename']=='panel-asus-rog5-ams678.ko' and row['status']=='PASS_INSERTION':
            h.f.rpc('prepare-fail' if mode=='prepare-fail' else 'prepare')
        return row
    m.insert=insert
    real_write=os.write
    def write(fd,data):
        st=os.fstat(fd);target=(ep.backlight/'brightness').stat()
        if (st.st_dev,st.st_ino)==(target.st_dev,target.st_ino):
            # Model the exact sysfs boundary with the real compiled driver/core:
            # property can update before callback failure, which must propagate.
            value=h.f.rpc('zero-fail' if mode=='write-fail' else 'zero')
            h.f.zeros.append(value)
            if value['ret']:
                raise OSError(-value['ret'],'actual panel/core refused brightness')
        return real_write(fd,data)
    patched=patch.object(os,'write',side_effect=write);patched.start();case.addCleanup(patched.stop)
    if not execute:return component,h,ep,None
    result=h.run_load()
    component.validate_result(result,EF.BOOT,ep.identity_record['owner'])
    return component,h,ep,result


class Assembly(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        L.Production.setUpClass();cls.addClassCleanup(L.Production.doClassCleanups)

    def test_actual_loader_endpoint_and_driver_complete(self):
        component,h,ep,result=pipeline(self)
        self.assertEqual(result['status'],'PASS_MODULES_AND_BLANK')
        self.assertEqual(len(result['insertions']),14)
        self.assertEqual(len(h.f.zeros),1);self.assertEqual(h.f.zeros[0]['ret'],0)
        self.assertEqual(component.entry_intent(EF.BOOT,ep.identity_record['owner'])['modules'],h.entered[0]['modules'])
        self.assertEqual(component.identity(EF.BOOT),result['blank']['after']['identity'])
        self.assertFalse(result['physical_scanout_verified'])

    def test_real_failed_prepare_never_validates(self):
        with self.assertRaisesRegex(ValueError,'actual panel/core refused'):
            pipeline(self,'prepare-fail')

    def test_real_dsi_error_never_validates(self):
        with self.assertRaisesRegex(ValueError,'actual panel/core refused'):
            pipeline(self,'write-fail')

    def test_actual_assembly_under_durable_ack_and_independent_process_cleanup(self):
        component,h,ep,_=pipeline(self,execute=False)
        supervisor=load('supervisor_integration_fixture',ROOT/'scripts/device/test-production-display-supervisor.py')
        supervisor.Supervisor.setUpClass();self.addCleanup(supervisor.Supervisor.doClassCleanups)
        self.base=supervisor.Supervisor.base
        self.b=supervisor.load(supervisor.Supervisor.source,'assembled_supervisor')
        self.component=lambda directory,scenario:component
        value=dict(phase='gpu-iommu-display',boot_id=EF.BOOT,owner=ep.identity_record['owner'],monitor_receipt_sha256='2'*64)
        with patch.object(supervisor,'BOOT',EF.BOOT),patch.object(supervisor,'VALUE',value):
            run=supervisor.Run(self,lifetime=8,lease=5)
            intent=run.arm()
            record=self.b.decode((run.directory/'global-entered.json').read_bytes())
            self.assertEqual(record['intent_sha256'],intent)
            self.assertFalse((ep.sys/'module/panel_asus_rog5_ams678').exists())
            run.send('enter-ack',intent)
            result=run.terminal()
            self.assertEqual(result['status'],'PASS_PRODUCTION_DISPLAY_AND_CLEANUP',result)
            self.assertTrue(result['remote_reaped'])
            self.assertEqual(len(result['component']['insertions']),14)
            self.assertNotEqual(result['action_process']['pid'],result['cleanup_process']['pid'])
            self.assertEqual(result['blank']['write_bytes'],2)
            self.assertFalse(result['physical_scanout_verified'])
            self.assertLess(len(self.b.encoded(result)),self.b.LINE)

    def test_owner_change_refuses_passing_result(self):
        component,h,ep,result=pipeline(self)
        ep.identity_record['owner']='b'*32
        with self.assertRaisesRegex(ValueError,'identity changed'):
            component.validate_result(result,EF.BOOT,'b'*32)

    def test_missing_and_corrupted_receipts_refuse(self):
        component,h,ep,result=pipeline(self)
        mutations=[lambda v:v.update(entered=False),lambda v:v.update(panel_attempted=False),
                   lambda v:v.update(cleanup_errors=[{'reason':'failed cleanup'}]),
                   lambda v:v.update(seconds=float('nan')),lambda v:v.update(seconds=86),
                   lambda v:v.update(checkpoints=[]),lambda v:v.update(preconsumer_checks=[]),
                   lambda v:v.update(drm_opens=1),lambda v:v.update(driver_reprobes=True),
                   lambda v:v.update(physical_scanout_verified=True),lambda v:v.update(blank=None),
                   lambda v:v.update(insertions=v['insertions'][:-1]),
                   lambda v:v['insertions'].reverse(),lambda v:v['insertions'][0].update(returncode=True),
                   lambda v:v['insertions'][0].update(reaped=False),lambda v:v['insertions'][0].update(error='failure'),
                   lambda v:v['insertions'][0].update(seconds=6),lambda v:v['insertions'][0].update(pid=0),
                   lambda v:v['endpoint'].update(identity={}),lambda v:v['endpoint'].update(device_opened=True),
                   lambda v:v['endpoint'].update(virtual_size=[1080,2400]),
                   lambda v:v['blank'].update(write_bytes=1),lambda v:v['blank'].update(brightness_readback=False),
                   lambda v:v['blank']['after'].update(identity={}),lambda v:v.update(cleanup_blank=v['blank'])]
        for index,mutate in enumerate(mutations):
            with self.subTest(index=index):
                bad=copy.deepcopy(result);mutate(bad)
                with self.assertRaises(ValueError):component.validate_result(bad,EF.BOOT,ep.identity_record['owner'])


class SourceBinding(unittest.TestCase):
    def test_dependencies_are_exact_and_source_load_has_no_device_io(self):
        component=C.Component(lambda boot:None)
        self.assertEqual(tuple(Path(r[1]).name for r in component.modules.MODULES),C.ORDER)
        self.assertEqual(component.modules.TOTAL_SECONDS,85)

    def test_changed_source_refuses_before_execution(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'display-firmware.py';p.write_text('raise AssertionError("must not execute")\n')
            with patch.object(C,'HERE',Path(d)):
                with self.assertRaisesRegex(ValueError,'digest'):C.dependency(p.name)

    def test_symlink_dependency_refuses(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'display-firmware.py';p.symlink_to(ROOT/'scripts/device/display-firmware.py')
            with patch.object(C,'HERE',Path(d)):
                with self.assertRaises(OSError):C.dependency(p.name)

    def test_unknown_dependency_refuses(self):
        with self.assertRaisesRegex(ValueError,'pin'):C.dependency('not-allowed.py')


if __name__=='__main__':unittest.main(verbosity=2)
