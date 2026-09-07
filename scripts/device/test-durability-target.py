#!/usr/bin/env python3
"""S04 adapter fixtures: never contact a device or write a block device."""
import copy
import importlib.util
import os
import stat
import tempfile
import unittest
from pathlib import Path
from unittest import mock

spec = importlib.util.spec_from_file_location('durability_target', Path(__file__).with_name('durability-target.py'))
M = importlib.util.module_from_spec(spec)
spec.loader.exec_module(M)

def request(phase='probe'):
    return dict(phase=phase, nonce='a'*64, size=M.SIZE,
                origin_boot_id='origin', identity=dict(boot_id='origin', release='kernel', bundle='bundle'),
                scope=dict(path='/persist', dev=1793, inode=2))

def snapshot():
    blocks={f'fixture{i}':'1' for i in range(115)}
    blocks.update(sda='0', sda23='0')
    return dict(boot='origin', kernel='kernel', bundles=['bundle'], blocks=blocks,
                backing='/.rog5/userdata-rw/rog5/state/server-state-v1.ext4',
                mountinfo='\n'.join([
                    '1 0 7:1 / /persist rw,nodev,noexec,nosuid,noatime - ext4 /dev/loop1 rw',
                    '2 0 8:24 / /.rog5/root-ro ro - ext4 /dev/sda24 ro,norecovery',
                    '3 0 8:23 / /.rog5/userdata-rw rw - ext4 /dev/sda23 rw']),
                power=dict(health='Good', temp='300', voltage_now='8569000'),
                online='1', thermal=dict(thermal_zone0='31000'))

class Tests(unittest.TestCase):
    def test_expected_scope(self):
        M.request_valid(request()); M.validate(snapshot(),request())

    def test_fixed_request_scope_and_boot_phase(self):
        for key,value in [('phase','format'),('size',True),('size',M.SIZE+1),('nonce','../x')]:
            r=request(); r[key]=value
            with self.subTest(key=key), self.assertRaises(ValueError): M.request_valid(r)
        r=request();r['scope']['path']='/dev/sda23'
        with self.assertRaises(ValueError): M.request_valid(r)
        for phase in ('verify','cleanup'):
            r=request(phase)
            with self.assertRaises(ValueError): M.request_valid(r)
            r['identity']['boot_id']='different';M.request_valid(r)

    def test_wrong_identity_and_missing_or_changed_geometry(self):
        for key,value in [('boot','stale'),('kernel','other'),('bundles',['bundle','bundle']),
                          ('backing','/unrelated'),('blocks',{})]:
            v=snapshot();v[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):M.validate(v,request())
        for node,value in [('sda23','2'),('sda23','1'),('fixture1','0')]:
            v=snapshot();v['blocks'][node]=value
            with self.subTest(node=node,value=value),self.assertRaises(ValueError):M.validate(v,request())

    def test_wrong_mount_or_journal_replay(self):
        for old,new in [('/dev/loop1','/dev/sda23'),('7:1','7:2'),('ro,norecovery','ro'),
                        ('/persist rw,','/persist ro,'),(' ext4 ',' vfat ')]:
            v=snapshot();v['mountinfo']=v['mountinfo'].replace(old,new)
            with self.subTest(old=old),self.assertRaises(ValueError):M.validate(v,request())
        v=snapshot();v['mountinfo']+='\n'+v['mountinfo'].splitlines()[0]
        with self.assertRaises(ValueError):M.validate(v,request())

    def test_unsafe_or_missing_measurements(self):
        for key,value in [('health','Unknown'),('temp','400'),('voltage_now','8300000')]:
            v=snapshot();v['power'][key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):M.validate(v,request())
        for key,value in [('online','0'),('thermal',{}),('thermal',{'t':'60000'})]:
            v=snapshot();v[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):M.validate(v,request())

    def test_no_open_or_mutation_if_initial_guard_fails(self):
        v=snapshot();v['online']='0'
        with mock.patch.object(M,'observe',return_value=v),mock.patch.object(M,'opened_parent') as opened, \
             mock.patch.object(M.signal,'signal'),mock.patch.object(M.signal,'setitimer') as timer:
            with self.assertRaises(ValueError):M.main(request(),'')
            opened.assert_not_called()
            self.assertEqual(timer.call_args.args,(M.signal.ITIMER_REAL,0))

    def test_invalid_request_has_no_side_effects(self):
        r=request();r['phase']='erase'
        with mock.patch.object(M,'observe') as observed,mock.patch.object(M.os,'mkdir') as mkdir:
            with self.assertRaises(ValueError):M.main(r,'')
            observed.assert_not_called();mkdir.assert_not_called()

    def test_complete_adapter_on_disposable_filesystem_with_identity_fixture(self):
        # Substitute physical observations and the root-owned /persist parent
        # only. All file creation, fsync, verification and cleanup are real.
        raw=Path(__file__).with_name('durability-file-ops.py').read_text()
        original=M.open_namespace
        fstat=os.fstat
        def namespace(parent,expected=None):
            # Host fixture may run as an ordinary user; model target root UID
            # only while the adapter opens its fixed namespace.
            def root_owner(fd):
                from types import SimpleNamespace
                s=fstat(fd)
                return SimpleNamespace(st_uid=0,st_gid=0,st_mode=s.st_mode,st_dev=s.st_dev,st_ino=s.st_ino)
            with mock.patch.object(M.os,'fstat',side_effect=root_owner):return original(parent,expected)
        with tempfile.TemporaryDirectory() as tmp:
            parent=os.open(tmp,os.O_RDONLY|os.O_DIRECTORY)
            state=snapshot()
            try:
                with mock.patch.object(M,'opened_parent',side_effect=lambda scope:os.dup(parent)), \
                     mock.patch.object(M,'open_namespace',side_effect=namespace), \
                     mock.patch.object(M,'observe',side_effect=lambda:copy.deepcopy(state)):
                    r=request();self.assertEqual(M.main(r,raw)['prepared'],{})
                    r['phase']='prepare';prepared=M.main(r,raw)
                    self.assertEqual(prepared['prepared']['file']['file']['size'],M.SIZE)
                    with self.assertRaises(FileExistsError):M.main(r,raw)
                    r.update(phase='verify',prepared=prepared['prepared'])
                    r['identity']['boot_id']='different';state['boot']='different'
                    self.assertEqual(M.main(r,raw)['prepared'],prepared['prepared'])
                    r['phase']='cleanup';self.assertEqual(M.main(r,raw)['status'],'PASS')
                    self.assertEqual(os.listdir(parent),[])
            finally:os.close(parent)

if __name__=='__main__':unittest.main()
