#!/usr/bin/env python3
"""Exercise real cache admission/staging, using a tiny recorded target cache.

Only full-tree authentication is mocked: prepare-qemu-linker-cache's separate
tests exercise that helper. The preparer digest constant is rebound to a fixture
script digest; no private historical script is required in clean CI. No target
generation, VM, phone, or hardware consumer is exercised by this suite.
"""
import importlib.util
import io
import json
from pathlib import Path
import stat
import struct
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock

SPEC = importlib.util.spec_from_file_location('hwdb', Path(__file__).with_name('stage-qemu-hwdb-cache.py'))
HWDB = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(HWDB)


class Admission(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.original = self.root/'runtime'; self.view = self.root/'view'
        self.directory = self.root/'prepared'; self.destination = self.root/'assembly'
        for path in (self.original, self.view, self.directory, self.destination):
            path.mkdir()
        tools = {}
        for name, relative in HWDB.TOOL_PATHS.items():
            path = self.original/relative; path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(name); tools[name] = HWDB.BASE.identity(path)
        for name, filename in (('qemu', 'qemu-aarch64-static'), ('bwrap', 'bwrap')):
            path = self.root/filename; path.write_text(name); tools[name] = HWDB.BASE.identity(path)
        (self.original/'etc/udev/hwdb.d').mkdir(parents=True)
        script = self.root/'prepare.py'; script.write_text('bounded historical preparer fixture')
        patch = mock.patch.object(HWDB, 'PREPARER', HWDB.BASE.digest(script)); patch.start(); self.addCleanup(patch.stop)
        patch = mock.patch.object(HWDB.BASE, 'bound_runtime', return_value=(self.original, self.view, 'metadata'))
        self.bound = patch.start(); self.addCleanup(patch.stop)
        receipts = {}
        for name in ('tree', 'materialization', 'view_receipt'):
            path = self.root/(name+'.json'); path.write_text('{}'); receipts[name] = HWDB.BASE.identity(path)
        self.receipt = Path(receipts['view_receipt']['path'])
        cache = self.directory/'hwdb.bin'
        cache.write_bytes(struct.pack('<8s9Q', b'KSLPHHRH', 261, 105, 80, 24, 16, 32, 80, 24, 1) + bytes(25))
        steps = []
        for command, name, content in zip(HWDB.commands(self.original, self.directory, Path(tools['qemu']['path'])),
                                           ('generate.log', 'query.log'), ('', HWDB.QUERY)):
            path = self.directory/name; path.write_text(content)
            steps.append(dict(command=command, seconds=.1, exit_status=0, log=HWDB.BASE.identity(path)))
        self.record = dict(status='PASS_TARGET_HWDB_PREPARED', authority='none; generic VM cache experiment',
                           physical='NOT RUN', runtime=str(self.original), view=str(self.view),
                           view_metadata_sha256='metadata', script=HWDB.BASE.identity(script), tools=tools,
                           cache=HWDB.BASE.identity(cache), cache_bytes=105, steps=steps, **receipts)
        self.save()

    def save(self):
        (self.directory/'result.json').write_text(json.dumps(self.record))

    def validate(self):
        return HWDB.validate(self.directory, self.view, self.receipt)

    def refuses(self):
        with self.assertRaises((ValueError, FileNotFoundError)):
            self.validate()

    def stage(self):
        return HWDB.stage(self.directory, self.view, self.receipt, self.destination)

    def test_matching_runtime_and_private_stage(self):
        self.assertEqual(self.stage(), self.record)
        self.assertEqual((self.destination/'hwdb-cache').read_bytes(), (self.directory/'hwdb.bin').read_bytes())
        self.assertEqual((self.destination/'hwdb-cache.sha256').read_text(), self.record['cache']['sha256']+'\n')
        for path in self.destination.iterdir():
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
        self.bound.assert_called_once_with(Path(self.record['tree']['path']),
                                          Path(self.record['materialization']['path']), self.receipt)
        self.assertFalse((self.original/'usr/lib/udev/hwdb.bin').exists())

    def test_wrong_tree_bytes(self):
        Path(self.record['tree']['path']).write_text('{"changed":true}'); self.refuses()

    def test_authentication_failure_propagates(self):
        self.bound.side_effect = ValueError('unauthenticated tree'); self.refuses()

    def test_wrong_view_and_metadata(self):
        for key in ('view', 'view_metadata_sha256', 'runtime'):
            with self.subTest(key=key):
                prior = self.record[key]; self.record[key] = '/other'; self.save(); self.refuses()
                self.record[key] = prior

    def test_wrong_tool_bytes_or_path(self):
        for name in self.record['tools']:
            with self.subTest(name=name):
                path = Path(self.record['tools'][name]['path']); old = path.read_bytes()
                path.write_bytes(b'changed'); self.refuses(); path.write_bytes(old)
        self.record['tools']['hwdb'] = self.record['tools']['unit']; self.save(); self.refuses()

    def test_wrong_preparer(self):
        self.record['script']['sha256'] = '0'*64; self.save(); self.refuses()

    def test_failed_or_unbounded_target_steps(self):
        for index in range(2):
            for key, bad in (('exit_status', 42), ('seconds', 51), ('seconds', float('nan')),
                              ('command', ['true'])):
                with self.subTest(index=index, key=key, bad=bad):
                    row = self.record['steps'][index]; old = row[key]; row[key] = bad
                    self.save(); self.refuses(); row[key] = old

    def test_query_semantics_even_with_updated_hash(self):
        path = self.directory/'query.log'; path.write_text('ID_VENDOR_FROM_DATABASE=Wrong\n')
        self.record['steps'][1]['log'] = HWDB.BASE.identity(path); self.save(); self.refuses()

    def test_unexpected_generate_diagnostics(self):
        path = self.directory/'generate.log'; path.write_text('warning\n')
        self.record['steps'][0]['log'] = HWDB.BASE.identity(path); self.save(); self.refuses()

    def test_cache_mutation(self):
        with (self.directory/'hwdb.bin').open('r+b') as stream:
            stream.seek(100); stream.write(b'x')
        self.refuses()

    def test_header_and_record_size(self):
        path = self.directory/'hwdb.bin'; data = path.read_bytes()
        for offset, value in ((0, b'WRONGMAG'), (8, struct.pack('<Q', 260)), (16, struct.pack('<Q', 999)),
                              (56, struct.pack('<Q', 0))):
            with self.subTest(offset=offset):
                path.write_bytes(data[:offset] + value + data[offset+8:])
                self.record['cache'] = HWDB.BASE.identity(path); self.save(); self.refuses()
        path.write_bytes(data); self.record['cache'] = HWDB.BASE.identity(path)
        self.record['cache_bytes'] = 106; self.save(); self.refuses()

    def test_symlink_cache_and_parent(self):
        cache = self.directory/'hwdb.bin'; copy = self.directory/'copy'
        cache.rename(copy); cache.symlink_to(copy); self.refuses()
        cache.unlink(); copy.rename(cache)
        alias = self.root/'alias'; alias.symlink_to(self.directory, target_is_directory=True)
        with self.assertRaises(ValueError): HWDB.validate(alias, self.view, self.receipt)

    def test_oversize_cache(self):
        with (self.directory/'hwdb.bin').open('wb') as stream: stream.truncate(HWDB.LIMIT+1)
        self.refuses()

    def test_existing_databases_and_custom_entries(self):
        for name in ('usr/lib/udev/hwdb.bin', 'etc/udev/hwdb.bin', 'etc/udev/hwdb.d/custom.hwdb'):
            with self.subTest(name=name):
                path = self.original/name; path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text('existing'); self.refuses(); path.unlink()
        (self.original/'etc/udev/hwdb.bin').symlink_to('missing'); self.refuses()

    def test_existing_outputs_refused_without_partial_stage(self):
        for name in ('hwdb-cache', 'hwdb-cache.sha256'):
            with self.subTest(name=name):
                path = self.destination/name; path.write_text('keep')
                with self.assertRaises(FileExistsError): self.stage()
                self.assertEqual(list(self.destination.iterdir()), [path]); self.assertEqual(path.read_text(), 'keep')
                path.unlink()

    def test_staging_cannot_write_retained_runtime(self):
        self.destination = self.original
        with self.assertRaises(ValueError): self.stage()

    def test_output_symlink_refuses_without_following(self):
        path = self.destination/'hwdb-cache.sha256'; path.symlink_to(self.root/'missing')
        with self.assertRaises(FileExistsError): self.stage()
        self.assertTrue(path.is_symlink()); self.assertFalse((self.root/'missing').exists())
        self.assertFalse((self.destination/'hwdb-cache').exists())

    def test_interruption_cleans_partial_output(self):
        with mock.patch.object(HWDB.os, 'open', side_effect=InterruptedError('fixture interruption')):
            with self.assertRaises(InterruptedError): self.stage()
        self.assertEqual(list(self.destination.iterdir()), [])

    def test_mutation_after_validation_cleans_partial_stage(self):
        # Exercise the real validator, then model a writer changing the source
        # at the copy boundary; stage must not publish a hash for stale bytes.
        validate = HWDB.validate
        def mutate(*args):
            result = validate(*args)
            with (self.directory/'hwdb.bin').open('ab') as output: output.write(b'changed')
            return result
        with mock.patch.object(HWDB, 'validate', side_effect=mutate):
            with self.assertRaises(ValueError): self.stage()
        self.assertEqual(list(self.destination.iterdir()), [])


class RunnerWiring(unittest.TestCase):
    def setUp(self):
        spec = importlib.util.spec_from_file_location('hwdb_runner', Path(__file__).with_name('test-qemu-logind.py'))
        self.runner = importlib.util.module_from_spec(spec); spec.loader.exec_module(self.runner)
        temporary = tempfile.TemporaryDirectory(); self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)

    def test_original_runtime_output_rejected_before_creation(self):
        original, view = self.root/'original', self.root/'view'
        original.mkdir(); view.mkdir()
        receipt = self.root/'receipt.json'
        receipt.write_text(json.dumps({'runtime':str(original),'root':str(view),
            'status':'PASS_VIEW_PREPARED','security_model':'mapped-file','readonly_required':True}))
        output = original/'must-not-create'
        args = ['fixture']
        for name, value in {'runtime-view':view,'runtime-receipt':receipt,'output':output,
                            'kernel':'missing','qemu-image':'invalid','toolchain-image':'invalid',
                            'libc':'missing','libloading':'missing'}.items():
            args += ['--'+name, str(value)]
        with mock.patch.object(self.runner.sys,'argv',args), \
             mock.patch.object(self.runner.os,'geteuid',return_value=1000), \
             mock.patch.object(self.runner,'install_handlers'), \
             mock.patch.object(self.runner.shutil,'disk_usage',return_value=SimpleNamespace(free=10**12)), \
             mock.patch.object(self.runner.sys,'stdout',io.StringIO()), \
             mock.patch.object(self.runner.sys,'stderr',io.StringIO()):
            try:
                self.assertNotEqual(self.runner.main(),0)
            except SystemExit as exc:
                self.assertEqual(exc.code,2)
        self.assertFalse(output.exists(), 'runner changed the retained original runtime')

    def test_stage_records_actual_outputs(self):
        destination = self.root/'assembly'
        record = {'status':'fixture admitted'}
        def stage(directory, runtime, receipt, output):
            self.assertEqual((directory,runtime,receipt),('cache','runtime','receipt'))
            (output/'hwdb-cache').write_bytes(b'actual fixture bytes')
            (output/'hwdb-cache.sha256').write_text('fixture digest\n')
            return record
        module = SimpleNamespace(stage=mock.Mock(side_effect=stage))
        result = {'outputs':{}}
        with mock.patch.object(self.runner,'hwdb_cache_module',return_value=module):
            self.runner.stage_hwdb_cache('cache','runtime','receipt',destination,result)
        self.assertEqual(result['hwdb_cache'],record)
        module.stage.assert_called_once()
        for name in ('hwdb-cache','hwdb-cache.sha256'):
            self.assertEqual(result['outputs']['payload/'+name],self.runner.identity(destination/'payload'/name))

    def test_stage_failure_propagates_without_acceptance(self):
        result = {'outputs':{}}
        module = SimpleNamespace(stage=mock.Mock(side_effect=ValueError('fixture refusal')))
        with mock.patch.object(self.runner,'hwdb_cache_module',return_value=module):
            with self.assertRaisesRegex(ValueError,'fixture refusal'):
                self.runner.stage_hwdb_cache('cache','runtime','receipt',self.root/'stage',result)
        self.assertEqual(result,{'outputs':{}})

    def test_large_cache_does_not_enter_bounded_initramfs(self):
        # The first integrated attempt hit SIGXFSZ at 8 MiB. Exercise actual
        # staging and the same bounded cpio executor with a 14 MB cache.
        def stage(directory, runtime, receipt, output):
            with (output/'hwdb-cache').open('wb') as stream:
                stream.truncate(13996390)
            (output/'hwdb-cache.sha256').write_text('fixture\n')
            return {'status':'fixture'}
        with mock.patch.object(self.runner,'hwdb_cache_module',return_value=SimpleNamespace(stage=stage)):
            self.runner.stage_hwdb_cache('cache','runtime','receipt',self.root,{'outputs':{}})
        initramfs = self.root/'initramfs'; (initramfs/'stage').mkdir(parents=True)
        (initramfs/'stage/guest.sh').write_text('#!/bin/sh\nexit 0\n')
        members = sorted(str(path.relative_to(initramfs)) for path in initramfs.rglob('*'))
        archive = self.root/'initramfs.cpio'
        with archive.open('xb') as output:
            self.runner.execute(['cpio','--null','-o','--quiet','--format=newc','--owner=0:0'],
                self.root/'cpio.log',10,[],cwd=initramfs,
                data=('\0'.join(members)+'\0').encode(),stdout=output)
        self.assertLess(archive.stat().st_size,self.runner.LOG_LIMIT)
        self.assertEqual((self.root/'payload/hwdb-cache').stat().st_size,13996390)
        self.assertNotIn(b'hwdb-cache',archive.read_bytes())


if __name__ == '__main__':
    unittest.main()
