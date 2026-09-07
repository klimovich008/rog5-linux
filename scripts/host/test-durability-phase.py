#!/usr/bin/env python3
"""Host phase-order fixtures only; no credentials, phone, or storage writes."""
import copy,importlib.util,unittest
from pathlib import Path
spec=importlib.util.spec_from_file_location('s04_phase',Path(__file__).with_name('run-durability-phase.py'))
M=importlib.util.module_from_spec(spec);spec.loader.exec_module(M)
OLD='26f9f5e7-a3e1-463f-b9e5-7e6ba3bdaaf7'
NEW='36f9f5e7-a3e1-463f-b9e5-7e6ba3bdaaf7'

class Tests(unittest.TestCase):
    def setUp(self):
        self.plan=dict(nonce='a'*64)
        self.origin=dict(serial='fixture',bundle='fixture',release='fixture',boot_id=OLD)
        self.scope=dict(status='PASS',mutation='none',identity=self.origin,
            scope=dict(path='/persist',dev=1793,inode=2,mode=0o755,uid=0,gid=0,test_directory_exists=False))
        self.hashes={p:'a'*64 for p in M.SOURCES};self.pin='b'*64
        self.record=dict(file=dict(nonce='a'*64,name='s04-'+'a'*32,sha256='c'*64,
            file=dict(size=64*1024**2,mode=0o400)),namespace_inode=123)
    def request(self,phase='prepare',boot=OLD,previous=None):
        return M.phase_request(self.plan,self.origin,self.scope,phase,boot,previous,self.hashes,self.pin)
    def previous(self,phase='prepare'):
        return dict(status='PASS',phase=phase,inputs_sha256=self.pin,script_hashes=self.hashes,
            target=dict(status='PASS',phase=phase,origin_boot_id=OLD,nonce='a'*64,size=64*1024**2,
                identity=self.origin if phase=='prepare' else dict(self.origin,boot_id=NEW),prepared=self.record))
    def test_exact_single_phase_transitions(self):
        self.assertEqual(self.request()['size'],64*1024**2)
        self.request('probe')
        self.assertEqual(self.request('verify',NEW,self.previous())['prepared'],self.record)
        self.request('cleanup',NEW,self.previous('verify'))
    def test_explicit_pinned_existing_namespace_is_not_an_absence_claim(self):
        self.scope['scope'].update(test_directory_exists=True,namespace_inode=123)
        self.assertEqual(self.request()['scope']['namespace_inode'],123)
        self.assertIs(self.request()['scope']['test_directory_exists'],True)
        for bad in (None,True,0,-1,'123'):
            self.scope['scope']['namespace_inode']=bad
            with self.subTest(bad=bad),self.assertRaises(ValueError):self.request()
    def test_previous_phase_required_and_bound(self):
        with self.assertRaises(ValueError):self.request('verify',NEW)
        for key,value in [('status','FAIL'),('phase','probe'),('inputs_sha256','0'*64),('script_hashes',{})]:
            p=self.previous();p[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):self.request('verify',NEW,p)
        with self.assertRaises(ValueError):self.request('cleanup',NEW,self.previous())
    def test_wrong_boot_refused_without_restarting(self):
        with self.assertRaises(ValueError):self.request('prepare',NEW)
        with self.assertRaises(ValueError):self.request('verify',OLD,self.previous())
        with self.assertRaises(ValueError):self.request('cleanup',OLD,self.previous('verify'))
        p=self.previous();p['target']['identity']=dict(self.origin,bundle='other')
        with self.assertRaises(ValueError):self.request('verify',NEW,p)
    def test_scope_must_be_exact_readonly_inventory(self):
        for key,value in [('status','NOT RUN'),('mutation','format'),('identity',{})]:
            saved=copy.deepcopy(self.scope);self.scope[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):self.request()
            self.scope=saved
        for key,value in [('path','/dev/sda23'),('mode',0o777),('test_directory_exists',True),('dev',True)]:
            saved=copy.deepcopy(self.scope);self.scope['scope'][key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):self.request()
            self.scope=saved
    def test_prepare_does_not_accept_previous_operation(self):
        with self.assertRaises(ValueError):self.request(previous=self.previous())
    def test_changed_existing_namespace_result_refused(self):
        self.scope['scope'].update(test_directory_exists=True,namespace_inode=123)
        request=self.request()
        value=dict(request,status='PASS',seconds=1,prepared=copy.deepcopy(self.record),ops_sha256='a'*64)
        M.validate_result(value,request,'a'*64)
        value['prepared']['namespace_inode']=124
        with self.assertRaises(ValueError):M.validate_result(value,request,'a'*64)
    def test_result_identity_hash_deadline_and_record_checked(self):
        request=self.request();value=dict(request,status='PASS',seconds=1,prepared=self.record,ops_sha256='a'*64)
        M.validate_result(value,request,'a'*64)
        for key,bad in [('status','FAIL'),('seconds',61),('seconds',float('nan')),('ops_sha256','b'*64),('identity',{})]:
            v=copy.deepcopy(value);v[key]=bad
            with self.subTest(key=key),self.assertRaises(ValueError):M.validate_result(v,request,'a'*64)
        request=self.request('verify',NEW,self.previous())
        value=dict(request,status='PASS',seconds=1,ops_sha256='a'*64)
        M.validate_result(value,request,'a'*64)
        value['prepared']={}
        with self.assertRaises(ValueError):M.validate_result(value,request,'a'*64)
if __name__=='__main__':unittest.main()
