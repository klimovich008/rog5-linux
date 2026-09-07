#!/usr/bin/env python3
"""Sanitized offline S02/S03 fixtures, not physical qualification."""
import copy
import importlib.util
import json
import subprocess
import sys
import tempfile
from pathlib import Path
import unittest

s=importlib.util.spec_from_file_location('runtime_evidence',Path(__file__).with_name('check-server-runtime-evidence.py'))
M=importlib.util.module_from_spec(s);s.loader.exec_module(M)
def fixture(kind):
    identity=dict(serial='fixture',bundle='fixture',release='fixture',
                  boot_id='11111111-1111-4111-8111-111111111111')
    hashes={k:'a'*64 for k in ('kernel','dtb','initramfs','rootfs','boot_bundle')}
    base=dict(identity=identity,interface='wlp1s0',carrier='1',default_route=True,addresses=['192.168.1.2'],
        power=dict(health='Good',temp='300',voltage_now='8550000'),
        units={n:dict(ActiveState='active',InvocationID='b'*32) for n in M.F.NAMES})
    usb=dict(name='usb',host_interface=M.B.ROOT.D.CAPTURE.INTERFACE,target_interface='usb0',source='10.77.0.1',address='10.77.0.2')
    wifi=dict(name='wifi',host_interface='wlan0',target_interface='wlp1s0',source='192.168.1.3',address='192.168.1.2')
    record=dict(status='PASS',release_qualified=False,**{kind.lower()+'_qualified':True},
        source=dict(clean=True,revision='a'*40,worktree_digest='b'*64),identity=identity,artifact_hashes=hashes,
        before=base,cases=[],commands=[],seconds=30,deadline_seconds=720 if kind=='S02' else 300)
    logs={}
    def command(value,link=None,code=0,error=b''):
        n=len(record['commands'])+1
        fields=dict(sequence=n,returncode=code)
        if kind=='S02':fields['sha256']='c'*64
        else:fields.update(script_sha256='c'*64,link=link)
        record['commands'].append(fields)
        logs[f'{n:02d}.stdout']=json.dumps(value).encode() if value is not None else b''
        logs[f'{n:02d}.stderr']=error
    command(base)
    if kind=='S02':
        record.update(links=[usb,wifi],per_direction_seconds=180)
        for n,(item,direction) in enumerate((l,d) for l in (usb,wifi) for d in ('upload','download')):
            record['cases'].append(dict(link=item,direction=direction,status='PASS',nonce=f'{n+1:064x}',
                script_sha256='c'*64,bytes=M.T.LIMIT,returncode=0,duration_seconds=1,s02_qualified=False,sha256='9'*64))
            command(base);command(base)
    else:
        record['per_restart_seconds']=40;prior=base
        for n,action in enumerate(M.ACTIONS):
            command(prior);after=copy.deepcopy(prior)
            after['units'][action]['InvocationID']=f'{n+1:032x}'
            if action=='rog5-wifi-wpa':after['units']['rog5-wifi-dhcp']['InvocationID']='e'*32
            if action=='rog5-early-sshd':
                command(None,code=255,error=(M.R/'tests/fixtures/headless-userspace/ssh-post-restart-refused.txt').read_bytes())
            command(after);command({'boot':identity['boot_id']},wifi)
            record['cases'].append(dict(action=action,status='PASS',started_seconds=1+n*5,seconds=2,after=after))
            prior=after
    return record,logs,identity,hashes

class Tests(unittest.TestCase):
    def check(self,kind,record,logs,identity,hashes):
        M.validate(kind,record,logs,identity,hashes,expected_digest=lambda nonce,size:'9'*64)
    def reject(self,kind,change):
        data=fixture(kind);change(*data)
        with self.assertRaises((ValueError,KeyError,TypeError)):self.check(kind,*data)
    def test_both_complete_fixtures(self):
        for kind in ('S02','S03'):
            with self.subTest(kind=kind):self.check(kind,*fixture(kind))
    def test_missing_case_and_raw_snapshot(self):
        for kind in ('S02','S03'):
            self.reject(kind,lambda r,l,*unused:r['cases'].pop())
            self.reject(kind,lambda r,l,*unused:l.pop('01.stdout'))
    def test_wrong_release_or_boot(self):
        for kind in ('S02','S03'):
            self.reject(kind,lambda r,l,i,h:r.update(artifact_hashes={}))
            self.reject(kind,lambda r,l,i,h:r.update(identity={}))
    def test_transfer_wrong_hash_size_nonce_and_order(self):
        for field,value in [('sha256','0'*64),('bytes',1),('nonce','bad'),('direction','other'),('returncode',True)]:
            with self.subTest(field=field):self.reject('S02',lambda r,*unused:r['cases'][0].update({field:value}))
    def test_transfer_wrong_interface_or_source(self):
        for key in ('host_interface','source','target_interface'):
            self.reject('S02',lambda r,*unused:r['links'][0].update({key:'wrong'}))
    def test_deadline_types_and_scope_unchanged(self):
        for kind in ('S02','S03'):
            for value in (True,float('nan'),float('inf'),721):
                self.reject(kind,lambda r,*unused:r.update(seconds=value))
            self.reject(kind,lambda r,*unused:r.update(deadline_seconds=9999))
    def test_nonrequested_radio_restart_rejected(self):
        self.reject('S03',lambda r,*unused:r['cases'][0]['after']['units']['rog5-wifi-radio'].update(InvocationID='f'*32))
    def test_missing_restart_or_overlapping_actions(self):
        self.reject('S03',lambda r,*unused:r['cases'][0].update(after=r['before']))
        self.reject('S03',lambda r,*unused:r['cases'][1].update(started_seconds=1))
    def test_refusal_must_be_readonly_observer_with_no_output(self):
        def bad_hash(r,l,*unused):
            c=next(c for c in r['commands'] if c['returncode']);c['script_sha256']='f'*64
        self.reject('S03',bad_hash)
        def bad_error(r,l,*unused):
            c=next(c for c in r['commands'] if c['returncode']);l[f"{c['sequence']:02d}.stderr"]=b'Host key verification failed'
        self.reject('S03',bad_error)
    def test_missing_final_wifi_and_unsafe_power(self):
        self.reject('S03',lambda r,*unused:r['commands'][-1].update(link=None))
        for kind in ('S02','S03'):
            self.reject(kind,lambda r,*unused:r['before']['power'].update(temp='400'))
            self.reject(kind,lambda r,*unused:r['before']['power'].update(temp=False))
    def test_unimplemented_commands_cannot_be_qualified(self):
        for kind in ('S02','S03'):self.reject(kind,lambda r,*unused:r.update(commands=[]))
    def test_cli_malformed_pinned_metadata_fails_in_normal_and_optimized_python(self):
        for optimized in ([],['-O']):
            for raw,pin in ((b'{}','0'*64),(b'{"kind":"S02","kind":"S03"}',None)):
                with tempfile.TemporaryDirectory() as tmp:
                    root=Path(tmp);inputs=root/'inputs';inputs.write_bytes(raw)
                    p=subprocess.run([sys.executable,*optimized,str(Path(M.__file__)),
                        '--kind','S02','--inputs',str(inputs),'--inputs-sha256',pin or M.B.sha(raw),
                        '--candidate','fixture','--artifact-hashes','kernel='+'a'*64,
                        '--output',str(root/'result')],capture_output=True,text=True,timeout=5)
                    self.assertEqual(p.returncode,1,p.stderr)
                    report=json.loads((root/'result/result.json').read_text())
                    self.assertEqual(report['status'],'FAIL');self.assertFalse(report['s02_qualified'])
if __name__=='__main__':unittest.main()
