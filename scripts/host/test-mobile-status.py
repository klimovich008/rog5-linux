#!/usr/bin/env python3
import importlib.util
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[2]
def module(name):
    spec=importlib.util.spec_from_file_location(name,ROOT/'scripts/host'/name)
    value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value);return value
M=module('check-mobile-status.py');P=module('load-private-device-profile.py')

class Status(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
        status=json.loads((ROOT/'configs/project-status.json').read_text())
        contract=json.loads((ROOT/status['mobile_contract']).read_text())
        names={'configs/project-status.json',status['mobile_contract'],
               contract['headless_baseline']['path'],status['artifact_pointer'],status['evidence']}
        for row in contract['rows']:
            for kind in ('software','physical'):
                proof=row[kind]
                if proof['status']=='PASS': names.add(proof['evidence']['path'])
        for name in names:
            (ROOT/name).resolve().relative_to(ROOT)
            path=self.root/name;path.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/name,path)
    def test_contract_validates(self): self.assertIn('NOT RUN',M.validate(self.root))
    def test_physical_pass_cannot_use_unbound_software_proof(self):
        path=self.root/'configs/mobile/acceptance.json';data=json.loads(path.read_text());data['rows'][0]['physical']['status']='PASS';path.write_text(json.dumps(data))
        with self.assertRaisesRegex(ValueError,'evidence'):M.validate(self.root)
    def test_physical_pass_requires_physical_scope(self):
        path=self.root/'configs/mobile/acceptance.json';data=json.loads(path.read_text())
        candidate='b'*64;data['candidate_sha256']=candidate;row=data['rows'][0]
        receipt=self.root/'receipt.json'
        observed={'status':'PASS','row':row['id'],'source_tree':'a'*40,'candidate_sha256':candidate}
        for scope in ('software',None,'physical'):
            with self.subTest(scope=scope):
                if scope is None: observed.pop('scope',None)
                else: observed['scope']=scope
                receipt.write_text(json.dumps(observed))
                row['physical'].update(status='PASS',candidate_sha256=candidate,evidence={
                    'path':'receipt.json','sha256':hashlib.sha256(receipt.read_bytes()).hexdigest()})
                path.write_text(json.dumps(data))
                if scope=='physical': self.assertIn('NOT RUN',M.validate(self.root))
                else:
                    with self.assertRaisesRegex(ValueError,'physical receipt'):M.validate(self.root)
    def test_headless_pass_cannot_be_promoted_by_status_edit(self):
        path=self.root/'configs/project-status.json';data=json.loads(path.read_text());data['open_headless_results']['S06']='PASS';path.write_text(json.dumps(data))
        with self.assertRaisesRegex(ValueError,'headless PASS'):M.validate(self.root)
    def test_summary_cannot_promote_unexecuted_physical_rows(self):
        path=self.root/'configs/project-status.json';data=json.loads(path.read_text());data['physical_tests']='PASS';path.write_text(json.dumps(data))
        with self.assertRaisesRegex(ValueError,'physical summary'):M.validate(self.root)
    def test_changed_headless_baseline_refuses(self):
        with (self.root/'configs/release-acceptance.json').open('a') as out:out.write('\n')
        with self.assertRaisesRegex(ValueError,'baseline'):M.validate(self.root)
    def test_profile_rejects_example_and_public_permissions(self):
        path=self.root/'phone.local.json';path.write_bytes((ROOT/'configs/devices/example.json').read_bytes());path.chmod(0o600)
        with self.assertRaisesRegex(ValueError,'serial'):P.load(path)
        data=json.loads(path.read_text());data.update(serial='fixture-phone',usb_path='9-9.9');path.write_text(json.dumps(data))
        self.assertEqual(P.load(path)['serial'],'fixture-phone')
        path.chmod(0o644)
        with self.assertRaisesRegex(ValueError,'metadata'):P.load(path)
    def test_profile_duplicate_and_symlink_refuse(self):
        path=self.root/'phone.local.json';path.write_text('{"schema":1,"schema":1}');path.chmod(0o600)
        with self.assertRaisesRegex(ValueError,'duplicate'):P.load(path)
        link=self.root/'link.local.json';link.symlink_to(path)
        with self.assertRaises(OSError):P.load(link)

if __name__=='__main__':unittest.main(verbosity=2)
