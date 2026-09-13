#!/usr/bin/env python3
"""Exercise actual session archive planning/publication; no install or VM."""
import argparse
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import tarfile
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location('compose', Path(__file__).with_name('compose-denial-session-payload.py'))
M = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(M)


class Payload(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.file = self.root/'input'; self.file.write_bytes(b'qualified bytes')
        self.row = M.file_member(self.file, 'usr/bin/deniald',
            {'bytes':15,'sha256':hashlib.sha256(b'qualified bytes').hexdigest(),'mode':'0o755'})

    def test_deterministic_archive_and_install_metadata(self):
        first, second = io.BytesIO(), io.BytesIO()
        a = M.archive([self.row], M.Sink(first))
        self.file.chmod(0o600)
        b = M.archive([self.row], M.Sink(second))
        self.assertEqual(a, b)
        self.assertEqual(first.getvalue(), second.getvalue())
        with tarfile.open(fileobj=io.BytesIO(first.getvalue()), mode='r:gz') as archive:
            self.assertEqual(archive.getnames(), ['usr','usr/bin','usr/bin/deniald'])
            row=archive.getmember('usr/bin/deniald')
            self.assertEqual((row.uid,row.gid,row.mode,row.mtime), (0,0,0o755,0))
            self.assertEqual(archive.extractfile(row).read(), b'qualified bytes')
        self.assertEqual(self.file.stat().st_mode & 0o777, 0o600)

    def test_fresh_output_only(self):
        output=self.root/'output'; output.mkdir(); keep=output/'keep';keep.write_text('keep')
        with self.assertRaisesRegex(ValueError,'fresh'):
            M.compose([self.row], output)
        self.assertEqual(keep.read_text(),'keep')

    def test_mutated_input_fails_before_publication(self):
        self.file.write_bytes(b'changed payload')
        with self.assertRaisesRegex(ValueError,'qualified bytes'):
            M.compose([self.row],self.root/'output')
        self.assertFalse((self.root/'output').exists())

    def test_change_between_measurement_and_write_removes_partial(self):
        original=M.archive
        def mutate(members,sink):
            if sink.stream is not None:
                self.file.write_bytes(b'changed payload')
            return original(members,sink)
        with patch.object(M,'archive',side_effect=mutate), self.assertRaisesRegex(ValueError,'qualified bytes'):
            M.compose([self.row], self.root/'output')
        self.assertEqual(list((self.root/'output').iterdir()), [])

    def test_reserve_refuses_without_creating_output(self):
        with patch.object(M.shutil,'disk_usage',return_value=argparse.Namespace(free=M.RESERVE)), self.assertRaisesRegex(ValueError,'reserve'):
            M.compose([self.row], self.root/'output')
        self.assertFalse((self.root/'output').exists())

    def test_published_archive_matches_measurement(self):
        output=self.root/'output'; result=M.compose([self.row],output)
        data=(output/'session.tar.gz').read_bytes()
        self.assertEqual(result,{'size':len(data),'sha256':hashlib.sha256(data).hexdigest()})
        self.assertFalse((output/'.session.tar.gz.partial').exists())

    def test_unsafe_destinations_and_privileged_modes_refuse(self):
        for name in ('../escape','/absolute','usr/../escape','usr//file'):
            with self.subTest(name=name), self.assertRaises(ValueError): M.safe_name(name)
        with self.assertRaisesRegex(ValueError,'permissions'):
            M.file_member(self.file,'usr/bin/tool',{'bytes':15,'sha256':self.row['sha256'],'mode':'0o6755'})
        with self.assertRaisesRegex(ValueError,'duplicate'):
            M.archive([self.row,self.row],M.Sink())

    def args(self):
        bundle=self.root/'flutter';(bundle/'lib').mkdir(parents=True)
        (bundle/'lib/libapp.so').write_bytes(b'app')
        inventory={'deniald':{'bytes':15,'sha256':self.row['sha256'],'mode':'0o755'},
                   'flutter/lib/libapp.so':{'bytes':3,'sha256':hashlib.sha256(b'app').hexdigest(),'mode':'0o644'}}
        for name in ('lib/libflutter_engine.so','data/icudtl.dat'):
            p=bundle/name;p.parent.mkdir(exist_ok=True);p.write_bytes(b'app')
            inventory['flutter/'+name]={'bytes':3,'sha256':hashlib.sha256(b'app').hexdigest(),'mode':'0o644'}
        q=self.root/'qualification.json';q.write_text(json.dumps({'status':'PASS_NONROOT_VM_SESSION','final_session':{'payload':inventory}}))
        cli=self.root/'cli.json';cli.write_text(json.dumps({'status':'ARM64_NATIVE_CLI_PASS','source_commit':M.BASE,
            'artifacts':[{'name':'denialctl','sha256':self.row['sha256'],'size':15,'checks':[{'returncode':0}]}]}))
        return argparse.Namespace(qualification=q,cli_receipt=cli,deniald=self.file,denialctl=self.file,
            flutter_bundle=bundle,denial_source=self.root/'git',output=self.root/'output')

    def test_plan_uses_qualified_inventory_and_required_entry_files(self):
        args=self.args()
        with patch.object(M.subprocess,'check_output',return_value=b'upstream fixture'):
            members,metadata=M.plan(args)
        names={m['name'] for m in members}
        self.assertIn('usr/bin/denialctl',names)
        self.assertIn('usr/bin/denial-mobile-session',names)
        self.assertIn('usr/lib/systemd/user/denial-session.target',names)
        self.assertNotIn('etc/denial/session.conf',names)
        self.assertNotIn('etc/passwd',names)
        self.assertEqual(metadata['authority'],'none')

    def test_bundle_extra_missing_and_linked_objects_refuse(self):
        args=self.args();extra=args.flutter_bundle/'extra';extra.write_text('extra')
        with self.assertRaisesRegex(ValueError,'qualified file set'):M.plan(args)
        extra.unlink();app=args.flutter_bundle/'lib/libapp.so';app.unlink()
        with self.assertRaisesRegex(ValueError,'qualified file set'):M.plan(args)
        app.symlink_to(self.file)
        with self.assertRaisesRegex(ValueError,'symlink'):M.plan(args)

    def test_output_inside_source_refuses_before_mutation(self):
        args=self.args();args.output=args.flutter_bundle/'new-output'
        with self.assertRaisesRegex(ValueError,'outside immutable'):M.plan(args)
        self.assertFalse(args.output.exists())

    def test_wrong_receipt_status_refuses(self):
        args=self.args();q=json.loads(args.qualification.read_text());q['status']='FAIL';args.qualification.write_text(json.dumps(q))
        with self.assertRaisesRegex(ValueError,'successful'):M.plan(args)

    def test_incomplete_inventory_cannot_produce_a_session_payload(self):
        args=self.args();q=json.loads(args.qualification.read_text())
        del q['final_session']['payload']['flutter/data/icudtl.dat']
        args.qualification.write_text(json.dumps(q));(args.flutter_bundle/'data/icudtl.dat').unlink()
        with patch.object(M.subprocess,'check_output',return_value=b'upstream fixture'), self.assertRaisesRegex(ValueError,'required session files'):
            M.plan(args)

    def test_interrupted_receipt_write_does_not_publish_partial_success(self):
        output=self.root/'output';output.mkdir()
        def fail(_result,stream,**_kwargs):
            stream.write('{"status":');raise KeyboardInterrupt()
        with patch.object(M.json,'dump',side_effect=fail), self.assertRaises(KeyboardInterrupt):
            M.publish_receipt(output,{'status':'PREPARED_NOT_INSTALLED'})
        self.assertEqual(list(output.iterdir()),[])

    def test_receipt_directory_sync_failure_removes_success(self):
        output=self.root/'output';output.mkdir()
        with patch.object(M.os,'fsync',side_effect=[None,OSError('injected directory sync failure')]), self.assertRaises(OSError):
            M.publish_receipt(output,{'status':'PREPARED_NOT_INSTALLED'})
        self.assertEqual(list(output.iterdir()),[])

    def test_receipt_publication_preserves_existing_file(self):
        output=self.root/'output';output.mkdir()
        M.publish_receipt(output,{'original':True})
        with self.assertRaises(FileExistsError):
            M.publish_receipt(output,{'replacement':True})
        self.assertEqual(json.loads((output/'provenance.json').read_text()),{'original':True})
        self.assertEqual(len(list(output.iterdir())),1)


if __name__=='__main__': unittest.main()
