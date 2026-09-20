#!/usr/bin/env python3
"""Real inert ARM64 archive intake; no kernel module or device operation."""
import copy
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import tarfile
import unittest
from unittest.mock import patch

HERE=Path(__file__).resolve().parent

def load(name, filename):
    spec=importlib.util.spec_from_file_location(name,HERE/filename)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

S=load('module_archive_stage','stage-production-display-modules.py')
F=load('module_archive_fixture','test-production-display-modules.py')


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()


class Intake(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        F.Modules.setUpClass(); cls.addClassCleanup(F.Modules.doClassCleanups)

    def setUp(self):
        self.fixture=F.Modules(); self.fixture.setUp();self.addCleanup(self.fixture.doCleanups)
        self.manifest=self.fixture.build();self.archive=self.fixture.output
        self.root=self.fixture.root;self.output=self.root/'staged'
        self.expected=dict(sha256=sha(self.archive),bytes=self.archive.stat().st_size,
                           manifest=self.manifest,qualification_sha256='a'*64)

    def stage(self): return S.materialize(self.archive,self.expected,self.output)

    def rejected(self, message=None):
        before=set(os.listdir('/proc/self/fd'))
        with self.assertRaises((ValueError,OSError)) as error:self.stage()
        if message:self.assertIn(message,str(error.exception))
        self.assertFalse(self.output.exists())
        self.assertFalse(list(self.root.glob('.staged.*')))
        self.assertEqual(set(os.listdir('/proc/self/fd')),before)

    def repin(self):
        # Deliberately allow the malicious container's outer hash. These tests
        # exercise member/format enforcement in addition to outer pin checking.
        self.expected['sha256']=sha(self.archive);self.expected['bytes']=self.archive.stat().st_size

    def mutate(self, fn):
        with tarfile.open(self.archive) as archive:
            rows=[(copy.copy(info),archive.extractfile(info).read()) for info in archive.getmembers()]
        fn(rows)
        with tarfile.open(self.archive,'w',format=tarfile.USTAR_FORMAT) as archive:
            for info,data in rows:archive.addfile(info,io.BytesIO(data) if info.isfile() else None)
        self.repin()

    def test_exact_archive_materializes_without_authority(self):
        before=set(os.listdir('/proc/self/fd'));result=self.stage()
        self.assertEqual(result['modules'],5)
        self.assertEqual(result['authority'],'none');self.assertEqual(result['physical'],'NOT RUN')
        self.assertEqual({str(p.relative_to(self.output)) for p in self.output.rglob('*') if p.is_file()},
                         {'manifest.json'}|{r['path'] for r in self.manifest['modules']})
        for row in self.manifest['modules']:
            path=self.output/row['path'];self.assertEqual(sha(path),row['sha256']);self.assertEqual(path.stat().st_mode&0o777,0o644)
        self.assertEqual(set(os.listdir('/proc/self/fd')),before)

    def test_restrictive_umask_does_not_change_qualified_member_mode(self):
        prior=os.umask(0o077)
        try:self.stage()
        finally:os.umask(prior)
        self.assertTrue(all((self.output/r['path']).stat().st_mode&0o777==0o644 for r in self.manifest['modules']))

    def test_wrong_outer_hash_refuses(self):
        self.expected['sha256']='f'*64;self.rejected('digest mismatch')

    def test_growing_archive_hash_read_is_bounded(self):
        class GrowingStream:
            def __init__(self,data): self.inner=io.BytesIO(data);self.read_bytes=0
            def readable(self): return True
            def read(self,size):
                data=self.inner.read(size);self.read_bytes+=len(data);return data
            def readinto(self,buffer):
                amount=self.inner.readinto(buffer);self.read_bytes+=amount;return amount
            def seek(self,*args): return self.inner.seek(*args)
            def tell(self): return self.inner.tell()
        # Represents growth after the initial file size observation.
        stream=GrowingStream(self.archive.read_bytes()+bytes(128*1024))
        with self.assertRaises(ValueError): S.verify(stream,self.expected)
        self.assertLessEqual(stream.read_bytes,self.expected['bytes']+1)

    def test_truncated_archive_refuses(self):
        self.archive.write_bytes(self.archive.read_bytes()[:-512]);self.repin();self.rejected()

    def test_duplicate_member_refuses(self):
        self.mutate(lambda rows:rows.insert(1,copy.deepcopy(rows[0])));self.rejected('header')

    def test_unlisted_member_refuses(self):
        def extra(rows):
            info=tarfile.TarInfo('unexpected');info.size=1;info.mode=0o644;rows.append((info,b'x'))
        self.mutate(extra);self.rejected()

    def test_missing_member_refuses(self):
        self.mutate(lambda rows:rows.pop(0));self.rejected('header')

    def test_reordered_members_refuse(self):
        def swap(rows):rows[0],rows[1]=rows[1],rows[0]
        self.mutate(swap);self.rejected('header')

    def test_symlink_member_refuses(self):
        def link(rows):rows[0][0].type=tarfile.SYMTYPE;rows[0][0].linkname='/tmp/outside';rows[0][0].size=0
        self.mutate(link);self.rejected('header')

    def test_hardlink_member_refuses(self):
        def link(rows):rows[0][0].type=tarfile.LNKTYPE;rows[0][0].linkname='manifest.json';rows[0][0].size=0
        self.mutate(link);self.rejected('header')

    def test_special_member_refuses(self):
        def special(rows):rows[0][0].type=tarfile.CHRTYPE;rows[0][0].size=0
        self.mutate(special);self.rejected('header')

    def test_archive_traversal_path_refuses(self):
        self.mutate(lambda rows:setattr(rows[0][0],'name','../outside'));self.rejected('header')
        self.assertFalse((self.root/'outside').exists())

    def test_contract_traversal_path_refuses_before_staging(self):
        self.manifest['modules'][0]['path']=S.PREFIX+'../../outside.ko';self.rejected('path')

    def test_mode_change_refuses(self):
        self.mutate(lambda rows:setattr(rows[0][0],'mode',0o777));self.rejected('header')

    def test_owner_change_refuses(self):
        self.mutate(lambda rows:setattr(rows[0][0],'uid',1000));self.rejected('header')

    def test_payload_digest_change_refuses_even_with_resealed_container(self):
        def corrupt(rows):
            info,data=rows[0];rows[0]=(info,bytes([data[0]^1])+data[1:])
        self.mutate(corrupt);self.rejected('member digest mismatch')

    def test_nonzero_data_padding_refuses(self):
        raw=bytearray(self.archive.read_bytes());size=self.manifest['modules'][0]['bytes']
        self.assertNotEqual(size%512,0);raw[512+size]=1;self.archive.write_bytes(raw);self.repin();self.rejected('padding')

    def test_concatenated_archive_refuses(self):
        raw=self.archive.read_bytes();self.archive.write_bytes(raw+raw);self.repin();self.rejected('length')

    def test_nonzero_end_record_refuses(self):
        raw=bytearray(self.archive.read_bytes());raw[-1]=1;self.archive.write_bytes(raw);self.repin();self.rejected('end')

    def test_input_symlink_refuses(self):
        actual=self.archive;self.archive=self.root/'archive-link';self.archive.symlink_to(actual);self.rejected()

    def test_replaced_archive_after_verification_refuses(self):
        verify=S.verify
        def replace(stream,expected):
            result=verify(stream,expected);self.archive.rename(self.root/'old-archive');self.archive.write_bytes((self.root/'old-archive').read_bytes());return result
        with patch.object(S,'verify',side_effect=replace):self.rejected('changed')

    def test_changed_archive_during_staging_removes_partial_files(self):
        make=S.tempfile.mkdtemp
        def change(*args,**kwargs):
            directory=make(*args,**kwargs)
            with self.archive.open('r+b') as stream:stream.seek(512);stream.write(b'bad')
            return directory
        with patch.object(S.tempfile,'mkdtemp',side_effect=change):self.rejected('changed during staging')

    def test_interruption_removes_partial_files(self):
        consume=S.consume
        def interrupt(stream,size,output=None):
            if output is not None:output.write(b'partial');raise KeyboardInterrupt('fixture interruption')
            return consume(stream,size)
        with patch.object(S,'consume',side_effect=interrupt):
            with self.assertRaises(KeyboardInterrupt):self.stage()
        self.assertFalse(self.output.exists());self.assertFalse(list(self.root.glob('.staged.*')))

    def test_existing_output_preserved(self):
        self.output.mkdir();(self.output/'keep').write_text('original')
        with self.assertRaisesRegex(ValueError,'already exists'):self.stage()
        self.assertEqual((self.output/'keep').read_text(),'original')

    def test_publication_race_preserves_other_directory(self):
        publish=S.publish
        def race(stage,output):output.mkdir();(output/'keep').write_text('other');publish(stage,output)
        with patch.object(S,'publish',side_effect=race):
            with self.assertRaises(OSError):self.stage()
        self.assertEqual((self.output/'keep').read_text(),'other');self.assertFalse(list(self.root.glob('.staged.*')))

    def test_parent_sync_failure_reports_failure_without_deleting_published_files(self):
        def sync_failure(stage,output):
            rename=S.ctypes.CDLL(None,use_errno=True).renameat2
            rename.argtypes=[S.ctypes.c_int,S.ctypes.c_char_p,S.ctypes.c_int,S.ctypes.c_char_p,S.ctypes.c_uint]
            rename.restype=S.ctypes.c_int
            self.assertEqual(rename(-100,os.fsencode(stage),-100,os.fsencode(output),1),0)
            raise OSError('fixture parent fsync failure after publication')
        with patch.object(S,'publish',side_effect=sync_failure):
            with self.assertRaisesRegex(OSError,'parent fsync failure'):self.stage()
        self.assertEqual(sha(self.output/self.manifest['modules'][0]['path']),self.manifest['modules'][0]['sha256'])
        self.assertFalse(list(self.root.glob('.staged.*')))

    def qualification(self):
        row=dict(sha256=self.expected['sha256'],bytes=self.expected['bytes'],exit_status=0,
                 embedded_manifest_sha256=hashlib.sha256(S.canonical_manifest(self.manifest)).hexdigest())
        record=dict(status='PASS_OFFLINE_INERT_MODULE_PACKAGING',authority='none',physical='NOT RUN',
                    build=dict(status='PASS_INERT_ARCHIVE_TWINS',runs=[row,copy.deepcopy(row)]),embedded_manifest=self.manifest)
        path=self.root/'qualification.json';path.write_text(json.dumps(record));return path,record

    def test_pinned_qualification_contract(self):
        path,_=self.qualification();expected=S.contract(path,sha(path))
        self.assertEqual(expected['manifest'],self.manifest)
        S.materialize(self.archive,expected,self.output)

    def test_wrong_qualification_hash_refuses(self):
        path,_=self.qualification()
        with self.assertRaisesRegex(ValueError,'digest mismatch'):S.contract(path,'0'*64)

    def test_inconsistent_twins_refuse(self):
        path,record=self.qualification();record['build']['runs'][1]['sha256']='0'*64;path.write_text(json.dumps(record))
        with self.assertRaisesRegex(ValueError,'twins differ'):S.contract(path,sha(path))

    def test_duplicate_qualification_key_refuses(self):
        path,_=self.qualification();text=path.read_text();path.write_text(text[:-1]+',"authority":"none"}')
        with self.assertRaisesRegex(ValueError,'duplicate JSON'):S.contract(path,sha(path))


if __name__=='__main__':unittest.main(verbosity=2)
