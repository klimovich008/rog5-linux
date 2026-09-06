#!/usr/bin/env python3
"""Offline checks for retained restart evidence; never starts a service."""
import copy
import importlib.util
import json
import subprocess
import sys
from pathlib import Path
import tempfile
import unittest

P=Path(__file__).with_name('check-wifi-restart-evidence.py')
S=importlib.util.spec_from_file_location('wifi_evidence',P)
M=importlib.util.module_from_spec(S);S.loader.exec_module(M)

class Tests(unittest.TestCase):
    def fixture(self):
        identity=dict(serial='fixture',bundle='fixture',release='kernel',boot_id='11111111-1111-4111-8111-111111111111')
        units={n:dict(ActiveState='active',InvocationID='1'*32,MainPID='1',ExecMainStartTimestampMonotonic='1') for n in M.NAMES}
        def snapshot():
            return dict(identity=identity,units=copy.deepcopy(units),interface='wlan0',addresses=['192.0.2.2'],carrier='1',default_route=True,
                        power=dict(health='Good',temp='300',voltage_now='8500000'))
        before=snapshot();one=snapshot();two=snapshot()
        one['units']['rog5-wifi-wpa']['InvocationID']='2'*32
        one['units']['rog5-wifi-dhcp']['InvocationID']='2'*32
        two['units']['rog5-wifi-wpa']['InvocationID']='2'*32
        two['units']['rog5-wifi-dhcp']['InvocationID']='3'*32
        r=dict(status='PASS',release_qualified=False,source=dict(clean=True,revision='a'*40),identity=identity,
               artifact_sha256='b'*64,before=before,seconds=10,deadline_seconds=120,per_restart_seconds=40,
               units=dict.fromkeys(['rog5-wifi-'+n+'.service' for n in ('radio','wpa','dhcp')],'c'*64),
               cases=[dict(action='rog5-wifi-wpa',status='PASS',started_seconds=1,seconds=3,after=one),
                      dict(action='rog5-wifi-dhcp',status='PASS',started_seconds=4,seconds=3,after=two)],commands=[])
        logs={};seq=0
        for snap in (before,one,two):
            for transport,value in [('usb',snap),('wifi',dict(boot=identity['boot_id'],connection='192.0.2.1 1234 192.0.2.2 22'))]:
                seq+=1;r['commands'].append(dict(sequence=seq,returncode=0,transport=transport,script_sha256='d'*64))
                logs[f'{seq:02d}.stdout']=json.dumps(value).encode();logs[f'{seq:02d}.stderr']=b''
        return r,logs

    def test_complete_replay_preserves_original_source(self):
        r,logs=self.fixture();M.validate(r,logs,r['identity'],'b'*64)

    def test_pass_label_cannot_hide_wrong_or_missing_behavior(self):
        for mutation in ('radio','boot','missing-wifi','wrong-endpoint','deadline','nan','unchanged-dhcp','transport','missing-log','tampered-snapshot','power'):
            r,logs=self.fixture()
            if mutation=='radio':r['cases'][0]['after']['units']['rog5-wifi-radio']['InvocationID']='9'*32
            if mutation=='boot':r['cases'][0]['after']['identity']=dict(r['identity'],boot_id='wrong')
            if mutation=='missing-wifi':r['commands'].pop()
            if mutation=='wrong-endpoint':logs['06.stdout']=json.dumps(dict(boot=r['identity']['boot_id'],connection='192.0.2.1 1234 192.0.2.3 22')).encode()
            if mutation=='deadline':r['cases'][0]['seconds']=41
            if mutation=='nan':r['seconds']=float('nan')
            if mutation=='unchanged-dhcp':r['cases'][1]['after']['units']['rog5-wifi-dhcp']['InvocationID']='2'*32
            if mutation=='transport':r['commands'][0]['returncode']=1
            if mutation=='missing-log':del logs['01.stdout']
            if mutation=='tampered-snapshot':logs['01.stdout']=b'{}'
            if mutation=='power':r['before']['power']['temp']='400'
            with self.subTest(mutation=mutation),self.assertRaises((ValueError,KeyError)):
                M.validate(r,logs,r['identity'],'b'*64)

    def test_pinned_file_rejects_alteration_symlink_and_oversize(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'file';p.write_bytes(b'original');p.chmod(0o600)
            pin=M.digest(p.read_bytes());self.assertEqual(M.pinned(p,pin),b'original')
            p.write_bytes(b'changed')
            with self.assertRaises(ValueError):M.pinned(p,pin)
            link=Path(tmp)/'link';link.symlink_to(p)
            with self.assertRaises((OSError,ValueError)):M.pinned(link,M.digest(p.read_bytes()))
            with self.assertRaises(ValueError):M.pinned(p,M.digest(p.read_bytes()),limit=2)

    def test_duplicate_metadata_rejected(self):
        with self.assertRaises(ValueError):M.decode(b'{"status":"FAIL","status":"PASS"}')

    def test_all_release_artifacts_must_match_not_just_initramfs(self):
        hashes=dict.fromkeys(('kernel','dtb','initramfs','rootfs','boot_bundle'),'a'*64)
        proof=dict(status='PASS',a01_qualified=True,candidate='fixture',artifact_hashes=hashes)
        M.composition_matches(proof,'fixture',hashes)
        for role in hashes:
            with self.subTest(role=role),self.assertRaises(ValueError):
                M.composition_matches(proof,'fixture',dict(hashes,**{role:'b'*64}))
        with self.assertRaises(ValueError):M.composition_matches(proof,'another',hashes)

    def test_cli_wrong_hash_is_rejected_in_normal_and_optimized_python(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);inputs=root/'inputs';inputs.write_bytes(b'{}')
            for mode in ([],['-O']):
                output=root/('optimized' if mode else 'normal')
                p=subprocess.run([sys.executable,*mode,'-B',str(P),'--inputs',str(inputs),
                    '--inputs-sha256','a'*64,'--candidate','fixture','--target-archive','/not-read',
                    '--artifact-hashes','{}','--output',str(output)],capture_output=True,text=True,timeout=5)
                self.assertNotEqual(p.returncode,0)
                r=json.loads((output/'result.json').read_text())
                self.assertEqual(r['status'],'FAIL');self.assertFalse(r['f02_qualified'])

if __name__=='__main__':unittest.main()
