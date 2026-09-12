#!/usr/bin/env python3
"""Bounded semantic checks for the dedicated prototype builder; no device access."""
import importlib.util
import contextlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest import mock

SPEC=importlib.util.spec_from_file_location('touch_build',Path(__file__).with_name('build-rog5-touch-module.py'))
M=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(M)

class Builder(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
        self.kit=self.root/'kit';self.q=self.root/'q';self.q.mkdir()
        for p in ('objects/include/config','objects/include/generated','source'):(self.kit/p).mkdir(parents=True,exist_ok=True)
        self.release='7.1.4-fixture';self.vermagic=self.release+' SMP preempt mod_unload aarch64'
        (self.kit/'objects/include/config/kernel.release').write_text(self.release+'\n')
        (self.kit/'objects/include/generated/utsrelease.h').write_text('#define UTS_RELEASE "'+self.release+'"\n')
        (self.kit/'objects/.config').write_text('CONFIG_ARM64=y\nCONFIG_MODULES=y\nCONFIG_I2C=y\nCONFIG_INPUT=y\n')
        (self.kit/'objects/Module.symvers').write_text('fixture exported symbols\n')
        self.modules=[dict(name='provider',vermagic=self.vermagic,depends='')]
        (self.q/'module-provenance.json').write_text(json.dumps(self.modules))
        self.result={'status':'FAIL','physical_validation':'NOT RUN','module_metadata_sha256':M.digest(self.q/'module-provenance.json'),'module_count':1,'release':self.release,'outputs':{p:M.digest(self.kit/p) for p in ('objects/.config','objects/Module.symvers')},'panel_source':{}}
        self.seal()
    def seal(self):
        (self.q/'result.json').write_text(json.dumps(self.result));self.rpin=M.digest(self.q/'result.json')
        (self.q/'final-source-binding.json').write_text(json.dumps({'qualification_sha256':self.rpin}));self.bpin=M.digest(self.q/'final-source-binding.json')
    def verify(self):return M.verify_kit(self.kit,self.q,self.rpin,self.bpin)
    def test_valid_fixture(self):self.assertEqual(self.verify()[0]['release'],self.release)
    def test_tampered_receipt_refuses(self):
        (self.q/'result.json').write_text('{}')
        with self.assertRaisesRegex(ValueError,'result identity'):self.verify()
    def test_config_and_symvers_identity_refuse(self):
        for name in ('objects/.config','objects/Module.symvers'):
            p=self.kit/name;old=p.read_bytes();p.write_bytes(old+b'changed')
            with self.assertRaisesRegex(ValueError,'kit output changed'):self.verify()
            p.write_bytes(old)
    def test_generated_release_refuses(self):
        (self.kit/'objects/include/generated/utsrelease.h').write_text('#define UTS_RELEASE "other"')
        with self.assertRaisesRegex(ValueError,'generated release'):self.verify()
    def test_module_dependency_and_vermagic_refuse(self):
        m=dict(name='rog5_fts3658u',vermagic=self.vermagic,depends='provider,builtin')
        self.assertEqual(M.check_module(m,self.modules,'kernel/builtin.ko\n'),['builtin','provider'])
        m['depends']='missing'
        with self.assertRaisesRegex(ValueError,'missing module dependency'):M.check_module(m,self.modules,'')
        m['depends']='provider';m['vermagic']='wrong'
        with self.assertRaisesRegex(ValueError,'vermagic'):M.check_module(m,self.modules,'')
    def test_sandbox_only_output_writable(self):
        command=M.sandbox(['make'],self.root/'output')
        self.assertIn('--unshare-net',command);self.assertIn('--unshare-pid',command)
        self.assertEqual(command[command.index('--ro-bind')+1:command.index('--ro-bind')+3],['/','/'])
        self.assertEqual(command.count('--bind'),1)
        self.assertEqual(command[command.index('--bind')+1:command.index('--bind')+3],[str(self.root/'output')]*2)
    def test_real_sandbox_refuses_retained_write(self):
        output=self.root/'output';output.mkdir();protected=self.root/'retained';protected.write_text('unchanged')
        code='import pathlib,sys; p=pathlib.Path(sys.argv[1]); p.write_text("modified")'
        result=subprocess.run(M.sandbox([sys.executable,'-c',code,str(protected)],output),
                              capture_output=True,text=True,timeout=5)
        self.assertNotEqual(result.returncode,0)
        self.assertIn('Read-only file system',result.stderr)
        self.assertEqual(protected.read_text(),'unchanged')
        writable=subprocess.run(M.sandbox(['/usr/bin/touch',str(output/'new')],output),
                                capture_output=True,text=True,timeout=5)
        self.assertEqual(writable.returncode,0,writable.stderr)
        self.assertTrue((output/'new').is_file())
    def test_nonzero_propagates(self):
        with self.assertRaisesRegex(ValueError,'command failed: 42'):
            M.run_owned([sys.executable,'-c','raise SystemExit(42)'],self.root/'log',dict(os.environ),time.monotonic()+2,0)
    def test_deadline_kills_background_group(self):
        pidfile=self.root/'child'
        code='import subprocess,time,pathlib; p=subprocess.Popen(["sleep","30"]);pathlib.Path('+repr(str(pidfile))+').write_text(str(p.pid));time.sleep(30)'
        with self.assertRaisesRegex(ValueError,'deadline'):
            M.run_owned([sys.executable,'-c',code],self.root/'log',dict(os.environ),time.monotonic()+.3,0)
        pid=int(pidfile.read_text());stat=Path('/proc')/str(pid)/'stat'
        self.assertTrue(not stat.exists() or stat.read_text().split()[2]=='Z')
    def test_main_failed_make_retains_stage_receipt(self):
        output=self.root/'failed-build';fake=self.root/'failed-make'
        fake.write_text('#!/bin/sh\nexit 42\n');fake.chmod(0o700)
        receipt={'source_kernel_base':'fixture','config_sha256':'fixture','outputs':{},
                 'module_metadata_sha256':'fixture','tools':{name:{'sha256':'fixture'} for name in
                 ('make','clang','ld.lld','llvm-ar','llvm-nm','llvm-objcopy','modinfo')}}
        argv=['builder','--kit',str(self.kit),'--qualification',str(self.q),'--output',str(output)]
        with mock.patch.object(sys,'argv',argv), mock.patch.object(M,'verify_kit',return_value=(receipt,{'repository_commit':'fixture'},self.modules)), mock.patch.object(M,'digest',return_value='fixture'), mock.patch.object(M,'sandbox',return_value=[str(fake)]), mock.patch.object(M.shutil,'which',return_value='/usr/bin/true'), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(M.main(),1)
        report=json.loads((output/'result.json').read_text());stage=report['stages']['build']
        self.assertEqual(stage['command'],[str(fake)])
        self.assertEqual(stage['exit_code'],42)
        self.assertEqual(stage['status'],'FAIL')
        self.assertGreaterEqual(stage['seconds'],0)
        self.assertIn('42',stage['error'])
    def test_interruption_retains_stage_exit_and_error(self):
        stage={'status':'RUNNING'}
        code='import os,signal,time;os.kill(os.getppid(),signal.SIGTERM);time.sleep(30)'
        with self.assertRaisesRegex(RuntimeError,'interrupted:'):
            M.run_owned([sys.executable,'-c',code],self.root/'log',dict(os.environ),
                        time.monotonic()+2,0,stage=stage)
        self.assertEqual(stage['status'],'FAIL')
        self.assertLess(stage['exit_code'],0)
        self.assertIn('interrupted:',stage['error'])
        self.assertGreaterEqual(stage['seconds'],0)
    def test_disk_reserve_refuses_before_spawn(self):
        marker=self.root/'marker'
        with self.assertRaisesRegex(ValueError,'disk reserve'):
            M.run_owned(['touch',str(marker)],self.root/'log',dict(os.environ),time.monotonic()+2,10**30)
        self.assertFalse(marker.exists())

if __name__=='__main__':unittest.main(verbosity=2)
