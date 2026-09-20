#!/usr/bin/env python3
"""Inert ARM64 ELF fixtures exercise actual metadata, closure and publication."""
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import tarfile
import tempfile
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location('display_module_builder', HERE/'build-production-display-modules.py')
B = importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(B)


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def dump(path, value): path.write_text(json.dumps(value, sort_keys=True)+'\n')


class Modules(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.compiled = tempfile.TemporaryDirectory(prefix='rog5-module-elfs-')
        cls.addClassCleanup(cls.compiled.cleanup)
        cls.elfs = Path(cls.compiled.name)
        cls.dependencies = {'helper': '', 'unrelated': '', 'qcom_refgen_regulator': '',
                            'gpucc_sm8350': '', 'panel_asus_rog5_ams678': 'helper',
                            'msm': 'helper,panel_asus_rog5_ams678'}
        cls.vermagic = B.RELEASE+' SMP preempt mod_unload aarch64'
        for name, deps in cls.dependencies.items():
            source = cls.elfs/(name+'.c')
            source.write_text('const char info[] __attribute__((section(".modinfo"),used)) = '+
                              json.dumps('name='+name+'\0vermagic='+cls.vermagic+'\0depends='+deps+'\0').replace('\\u0000', '\\0')+';\n')
            subprocess.run(['clang', '--target=aarch64-linux-gnu', '-c', str(source), '-o', str(cls.elfs/(name+'.ko'))],
                           check=True, timeout=10)

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='rog5-module-package-')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.repo = self.root/'repo'; self.repo.mkdir()
        (self.repo/'scripts/host').mkdir(parents=True)
        shutil.copyfile(B.ROOT/'scripts/host/check-production-build-diagnostics.py', self.repo/'scripts/host/check-production-build-diagnostics.py')
        p = patch.object(B, 'ROOT', self.repo); p.start(); self.addCleanup(p.stop)
        self.cohort = self.root/'cohort'; self.cohort.mkdir()
        self.modroot = self.cohort/B.PREFIX; (self.modroot/'kernel').mkdir(parents=True)
        self.meta = self.cohort/'module-provenance.json'
        self.proof = self.repo/'proof.json'; self.pointer = self.repo/'pointer.json'
        self.output = self.root/'output.tar'
        self.entries = []
        for name, deps in self.dependencies.items():
            path = B.PREFIX+'kernel/'+name+'.ko'
            shutil.copyfile(self.elfs/(name+'.ko'), self.cohort/path)
            self.entries.append(dict(path=path, sha256=sha(self.cohort/path), name=name,
                                     vermagic=self.vermagic, depends=deps, firmware=[]))
        (self.modroot/'modules.dep').write_text(''.join('kernel/'+row['name']+'.ko: '+
            ' '.join('kernel/'+dep+'.ko' for dep in row['depends'].split(',') if dep)+'\n' for row in self.entries))
        (self.modroot/'modules.builtin').write_text('kernel/builtin.ko\n')
        (self.modroot/'modules.softdep').write_text('# fixture no softdeps\n')
        self.board = dict(status='PASS: offline incremental software qualification', candidate=None,
                          release=B.RELEASE, source_commit='1'*40, source_tree='2'*40, linux_base='3'*40,
                          production_series_sha256='4'*64, config_sha256='5'*64,
                          module_artifact_root=str(self.cohort), panel_module=dict(
                              sha256=next(row['sha256'] for row in self.entries if row['name']=='panel_asus_rog5_ams678'),
                              vermagic=self.vermagic))
        self.refresh()

    def refresh(self):
        dump(self.meta, self.entries)
        self.board['module_metadata'] = dict(path=str(self.meta), sha256=sha(self.meta), size=self.meta.stat().st_size)
        proof = {k: self.board[k] for k in ('release', 'source_commit', 'source_tree', 'production_series_sha256', 'config_sha256')}
        proof['linux_commit'] = self.board['linux_base']
        proof['cohort'] = dict(status='PASS', module_metadata_sha256=sha(self.meta), indexes={
            name: sha(self.modroot/name) for name in ('modules.dep','modules.builtin','modules.softdep')})
        dump(self.proof, proof)
        self.board['evidence'] = dict(path='proof.json', sha256=sha(self.proof), size=self.proof.stat().st_size)
        dump(self.pointer, dict(current_board_qualification=self.board))

    def build(self): return B.assemble(self.pointer, self.output)

    def refuses(self, message=None):
        with self.assertRaises((ValueError, OSError)) as error: self.build()
        if message: self.assertIn(message, str(error.exception))
        self.assertFalse(self.output.exists())
        self.assertFalse(list(self.root.glob('.output.tar.*')))

    def test_actual_elf_closed_subset_and_deterministic_archive(self):
        result = self.build()
        other = self.root/'twin.tar'; B.assemble(self.pointer, other)
        self.assertEqual(sha(self.output), sha(other))
        names = [row['name'] for row in result['modules']]
        self.assertEqual(len(names), 5)
        self.assertNotIn('unrelated', names)
        self.assertLess(names.index('helper'), names.index('panel_asus_rog5_ams678'))
        self.assertLess(names.index('panel_asus_rog5_ams678'), names.index('msm'))
        with tarfile.open(self.output) as archive:
            self.assertEqual(len(archive.getmembers()), 6)
            for entry in archive.getmembers():
                self.assertTrue(entry.isfile()); self.assertEqual(entry.mode, 0o644)
                self.assertEqual(entry.uid, 0); self.assertEqual(entry.mtime, 0)
            manifest = json.load(archive.extractfile('manifest.json'))
            self.assertEqual(manifest['authority'], 'none')
            self.assertEqual(manifest['physical'], 'NOT RUN')
            self.assertIn('NOT PACKAGED', manifest['firmware_status'])

    def test_historical_two_modules_do_not_close_current_dependencies(self):
        self.entries = [r for r in self.entries if r['name'] in ('qcom_refgen_regulator','panel_asus_rog5_ams678')]
        self.refresh(); self.refuses('closure invalid')

    def test_missing_dependency_refuses(self):
        self.entries = [r for r in self.entries if r['name'] != 'helper']
        self.refresh(); self.refuses('closure invalid')

    def test_duplicate_normalized_names_refuse(self):
        row = copy.deepcopy(self.entries[-1]); row['name'] = 'qcom-refgen-regulator'
        self.entries.append(row); self.refresh(); self.refuses('closure invalid')

    def test_cycle_refuses(self):
        p = self.modroot/'modules.dep'; p.write_text(p.read_text().replace('kernel/helper.ko: ', 'kernel/helper.ko: kernel/msm.ko '))
        self.refresh(); self.refuses('closure invalid')

    def test_unsafe_module_path_refuses(self):
        self.entries[0]['path'] = B.PREFIX+'kernel/../helper.ko'
        self.refresh(); self.refuses()

    def test_unrelated_depmod_edge_cannot_expand_the_symbol_closure(self):
        path = self.modroot/'modules.dep'
        path.write_text(path.read_text().replace('kernel/msm.ko: ', 'kernel/msm.ko: kernel/unrelated.ko '))
        self.refresh(); self.refuses('outside declared transitive closure')

    def test_legitimate_depmod_transitive_edge_is_accepted(self):
        # msm declares only panel, panel declares helper; depmod lists both.
        row = next(r for r in self.entries if r['name'] == 'msm')
        row['depends'] = 'panel_asus_rog5_ams678'
        source = self.root/'msm.c'
        source.write_text('const char info[] __attribute__((section(".modinfo"),used)) = '+
                          json.dumps('name=msm\0vermagic='+self.vermagic+'\0depends='+row['depends']+'\0').replace('\\u0000', '\\0')+';\n')
        output = self.cohort/row['path']
        subprocess.run(['clang','--target=aarch64-linux-gnu','-c',str(source),'-o',str(output)],check=True,timeout=10)
        row['sha256'] = sha(output); self.refresh()
        self.assertEqual(len(self.build()['modules']), 5)

    def test_other_falsy_firmware_types_refuse(self):
        for value in (None, False, 0, {}):
            with self.subTest(value=value):
                self.output.unlink(missing_ok=True)
                self.entries[0]['firmware'] = value; self.refresh()
                self.refuses('firmware metadata schema')

    def test_selected_softdep_refuses(self):
        (self.modroot/'modules.softdep').write_text('softdep msm pre: unrelated\n')
        self.refresh(); self.refuses('softdep requires')

    def test_unrelated_softdep_does_not_expand_selection(self):
        (self.modroot/'modules.softdep').write_text('softdep unrelated pre: helper\n')
        self.refresh(); self.assertEqual(len(self.build()['modules']), 5)

    def test_actual_elf_metadata_disagreement_refuses(self):
        self.entries[0]['vermagic'] += ' wrong'
        self.refresh(); self.refuses('ELF metadata mismatch')

    def test_panel_pin_disagreement_refuses(self):
        self.board['panel_module']['sha256'] = 'f'*64
        self.refresh(); self.refuses('panel mismatch')

    def test_changed_module_bytes_refuse_before_publication(self):
        row = self.entries[0]; path=self.cohort/row['path']
        path.write_bytes(path.read_bytes()+b'changed')
        self.refuses('digest mismatch')

    def test_non_arm64_elf_refuses(self):
        row=self.entries[0]; path=self.cohort/row['path']; raw=bytearray(path.read_bytes()); raw[18:20]=b'\x3e\x00'; path.write_bytes(raw)
        row['sha256']=sha(path); self.refresh(); self.refuses('ARM64 relocatable')

    def test_symlink_in_module_parent_refuses(self):
        kernel=self.modroot/'kernel'; kernel.rename(self.modroot/'elsewhere'); kernel.symlink_to('elsewhere')
        self.refuses('symlink')

    def test_changed_index_refuses(self):
        path=self.modroot/'modules.dep'; path.write_text(path.read_text()+'\n')
        self.refuses('digest mismatch')

    def test_changed_provenance_refuses(self):
        self.meta.write_text(self.meta.read_text()+' ')
        self.refuses('digest mismatch')

    def test_board_proof_binding_mismatch_refuses(self):
        self.board['source_commit']='9'*40; dump(self.pointer, dict(current_board_qualification=self.board))
        self.refuses('binding mismatch')

    def test_late_tool_failure_does_not_publish(self):
        actual=B.inspect_module; calls=0
        def inspect(path):
            nonlocal calls
            calls+=1
            if calls==2: raise ValueError('injected late metadata tool failure')
            return actual(path)
        with patch.object(B, 'inspect_module', side_effect=inspect): self.refuses('late metadata')

    def test_module_changed_during_metadata_inspection_refuses(self):
        actual=B.inspect_module
        def inspect(path):
            result=actual(path); path.write_bytes(path.read_bytes()+b'race'); return result
        with patch.object(B, 'inspect_module', side_effect=inspect): self.refuses('digest mismatch')

    def test_existing_output_is_preserved(self):
        self.output.write_bytes(b'keep')
        with self.assertRaisesRegex(ValueError, 'already exists'): self.build()
        self.assertEqual(self.output.read_bytes(), b'keep')

    def test_publication_race_does_not_replace_other_file(self):
        link=os.link
        def raced(source,target,**kwargs):
            self.output.write_bytes(b'other writer'); return link(source,target,**kwargs)
        with patch.object(B.os, 'link', side_effect=raced):
            with self.assertRaises(FileExistsError): self.build()
        self.assertEqual(self.output.read_bytes(), b'other writer')
        self.assertFalse(list(self.root.glob('.output.tar.*')))

    def test_legacy_empty_firmware_scalar_normalizes_explicitly(self):
        self.entries[0]['firmware']=''; self.refresh()
        result = self.build()
        self.assertEqual(len(result['modules']),5)
        self.assertTrue(all(type(row['firmware']) is list for row in result['modules']))

    def test_nonempty_firmware_scalar_refuses(self):
        self.entries[0]['firmware']='invented.fw'; self.refresh(); self.refuses('firmware metadata schema')


if __name__ == '__main__': unittest.main(verbosity=2)
