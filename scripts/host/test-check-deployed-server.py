#!/usr/bin/env python3
"""Offline regressions for the exact deployed-userspace check."""
import ast
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import stat
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock

spec=importlib.util.spec_from_file_location('deployed',Path(__file__).with_name('check-deployed-server.py'))
M=importlib.util.module_from_spec(spec);spec.loader.exec_module(M)

class Tests(unittest.TestCase):
    def setUp(self):
        self.expected=M.expected_files()
        self.identity=dict(boot_id='11111111-1111-4111-8111-111111111111',bundle='fixture',release='fixture-kernel')
        self.value=dict(**self.identity,files=copy.deepcopy(self.expected))

    def test_exact_six_deployed_files(self):
        M.validate_snapshot(self.value,self.identity,self.expected)
        self.assertEqual(len(self.expected),6)

    def test_captured_stale_overlay_is_rejected(self):
        fixture=json.loads((M.REPO/'tests/fixtures/headless-userspace/stale-healthd.json').read_text())
        self.value['files'][fixture['role']].update(sha256=fixture['sha256'],size=fixture['size'])
        with self.assertRaisesRegex(ValueError,'deployed userspace mismatch: healthd'):
            M.validate_snapshot(self.value,self.identity,self.expected)

    def test_missing_error_or_extra_file_is_not_success(self):
        for replacement in ({},{'healthd':{'status':'error'}},dict(self.expected,extra={})):
            with self.subTest(replacement=list(replacement)),self.assertRaises(ValueError):
                M.validate_snapshot(dict(self.value,files=replacement),self.identity,self.expected)

    def test_wrong_boot_bundle_or_kernel(self):
        for key in self.identity:
            with self.subTest(key=key),self.assertRaises(ValueError):
                M.validate_snapshot(dict(self.value,**{key:'wrong'}),self.identity,self.expected)

    def test_metadata_and_hash_are_all_required(self):
        for field,bad in [('sha256','0'*64),('size',1),('mode',511),('uid',1000),('gid',1000),('nlink',2),('status','error')]:
            value=copy.deepcopy(self.value);value['files']['healthd'][field]=bad
            with self.subTest(field=field),self.assertRaises(ValueError):
                M.validate_snapshot(value,self.identity,self.expected)

    def test_boolean_or_float_metadata_is_not_an_integer(self):
        for bad in (False,0.0):
            value=copy.deepcopy(self.value);value['files']['healthd']['uid']=bad
            with self.subTest(bad=bad),self.assertRaises(ValueError):
                M.validate_snapshot(value,self.identity,self.expected)

    def test_transport_gate_precedes_credential_use(self):
        with mock.patch.object(M,'host_gate',side_effect=ValueError('wrong USB')),mock.patch.object(M.subprocess,'run') as run:
            with self.assertRaisesRegex(ValueError,'wrong USB'):
                M.collect({},None,None)
            run.assert_not_called()

    def test_actual_probe_rejects_symlink_and_oversized_file(self):
        function=next(node for node in ast.parse(M.PROBE).body if isinstance(node,ast.FunctionDef) and node.name=='read_file')
        namespace=dict(os=os,stat=stat,hashlib=hashlib)
        exec(compile(ast.Module(body=[function],type_ignores=[]),'exact-target-probe','exec'),namespace)
        read=namespace['read_file']
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'payload';path.write_bytes(b'captured-file')
            observed=read(str(path))
            self.assertEqual(observed['sha256'],hashlib.sha256(b'captured-file').hexdigest())
            self.assertEqual(observed['size'],13)
            original_stat=os.stat
            def changed_stat(*args,**kwargs):
                value=original_stat(*args,**kwargs)
                fields={key:getattr(value,key) for key in ('st_ino','st_dev','st_size','st_mode','st_uid','st_gid','st_nlink','st_mtime_ns','st_ctime_ns')}
                fields['st_mtime_ns']+=1
                return SimpleNamespace(**fields)
            with mock.patch.object(os,'stat',side_effect=changed_stat),self.assertRaisesRegex(ValueError,'pathname changed'):
                read(str(path))
            link=Path(tmp)/'link';link.symlink_to(path)
            with self.assertRaises(OSError): read(str(link))
            directory=Path(tmp)/'directory';directory.symlink_to(Path(tmp),target_is_directory=True)
            with self.assertRaises(OSError): read(str(directory/'payload'))
            with path.open('wb') as f: f.truncate(1048577)
            with self.assertRaises(ValueError): read(str(path))

    def test_help_is_discoverable_without_phone_contact(self):
        result=subprocess.run([str(M.REPO/'scripts/host/rog5-dev'),'check-deployed-server','--help'],capture_output=True,text=True,timeout=5)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertIn('--boot-id',result.stdout)

    def test_quick_acceptance_runs_both_interpreters(self):
        contract=json.loads((M.REPO/'configs/release-acceptance.json').read_text())
        row=next(test for test in contract['tests'] if test['id']=='A02')
        self.assertIn(['python3','scripts/host/test-check-deployed-server.py'],row['commands'])
        self.assertIn(['python3','-O','scripts/host/test-check-deployed-server.py'],row['commands'])

if __name__=='__main__': unittest.main()
