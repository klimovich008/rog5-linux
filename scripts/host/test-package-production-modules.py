#!/usr/bin/env python3
"""Offline checks for package-production-modules.py: deterministic packing,
member identity and refusal of an incomplete kernel build. The real
reproduction against build-r2 is recorded in test-results, not repeated here."""
import contextlib
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import tarfile
import tempfile
import unittest
from unittest import mock

REPO = Path(__file__).resolve().parents[2]
SOURCE = REPO/'scripts/host/package-production-modules.py'
spec = importlib.util.spec_from_file_location('package_production_modules', SOURCE)
P = importlib.util.module_from_spec(spec)
spec.loader.exec_module(P)


class Packager(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def tree(self):
        tree = self.root/'tree'
        for name, data in (('lib/modules/r/kernel/b.ko', b'b'), ('lib/modules/r/kernel/a/a.ko', b'a'),
                           ('lib/modules/r/modules.dep', b'dep\n')):
            (tree/name).parent.mkdir(parents=True, exist_ok=True)
            (tree/name).write_bytes(data)
        (tree/'lib/modules/r/kernel/a/a.ko').chmod(0o600)
        return tree

    def test_pack_is_deterministic_sorted_and_normalized(self):
        tree = self.tree()
        first, second = self.root/'one.tar.gz', self.root/'two.tar.gz'
        entries, total = P.pack(tree, first)
        P.pack(tree, second)
        self.assertEqual(first.read_bytes(), second.read_bytes())
        self.assertEqual(total, 6)
        with tarfile.open(first, 'r:gz') as archive:
            members = archive.getmembers()
        self.assertEqual([m.name for m in members], sorted(entries))
        self.assertTrue(all(m.isfile() and m.mode == 0o644 and m.uid == m.gid == m.mtime == 0 for m in members))
        self.assertEqual(entries['lib/modules/r/kernel/b.ko'], hashlib.sha256(b'b').hexdigest())

    def test_pack_refuses_an_existing_output(self):
        tree = self.tree()
        (self.root/'exists.tar.gz').write_bytes(b'')
        with self.assertRaises(FileExistsError):
            P.pack(tree, self.root/'exists.tar.gz')

    def test_incomplete_kernel_build_is_refused(self):
        build = self.root/'build'
        build.mkdir()
        (build/'result.json').write_text(json.dumps(dict(status='FAIL', stages={'kernel-build': dict(status='FAIL')})))
        argv = ['package', '--build', str(build), '--output', str(self.root/'out')]
        with mock.patch.object(sys, 'argv', argv), contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaisesRegex(ValueError, 'did not pass'):
                P.main()

    def fake_build(self):
        """A completed build whose result.json binds its outputs and provenance."""
        build = self.root/'build'
        release = '7.2.7-rog5-k1'
        files = {'objects/.config': b'CONFIG_X=y\n', 'objects/Module.symvers': b'sym\n',
                 'objects/System.map': b'map\n', 'objects/arch/arm64/boot/Image': b'image'}
        modules = {'drivers/a.ko': b'module-a', 'drivers/b.ko': b'module-b'}
        for name, data in files.items():
            (build/name).parent.mkdir(parents=True, exist_ok=True)
            (build/name).write_bytes(data)
        installed = build/'modules/lib/modules'/release
        for name, data in modules.items():
            (installed/'kernel'/name).parent.mkdir(parents=True, exist_ok=True)
            (installed/'kernel'/name).write_bytes(data)
        provenance = [dict(path=f'modules/lib/modules/{release}/kernel/{name}', sha256=hashlib.sha256(data).hexdigest(),
                           name=Path(name).stem, vermagic=release+' SMP preempt mod_unload aarch64', depends='', firmware=[])
                      for name, data in modules.items()]
        (build/'module-provenance.json').write_text(json.dumps(provenance))
        outputs = {name: P.sha(build/name) for name in P.BUILD_OUTPUTS}
        built = dict(status='PASS', release=release, config_sha256=outputs['objects/.config'], outputs=outputs)
        return build, built, release, installed

    def test_verified_build_copies_modules_matching_their_provenance(self):
        build, built, release, installed = self.fake_build()
        provenance = P.verify_build(build, built, release)
        dst = self.root/'out/kernel/drivers/a.ko'
        P.copy_board_module(installed, 'drivers/a.ko', dst, provenance, release)
        self.assertEqual(dst.read_bytes(), b'module-a')

    def test_altered_module_is_refused(self):
        build, built, release, installed = self.fake_build()
        provenance = P.verify_build(build, built, release)
        (installed/'kernel/drivers/b.ko').write_bytes(b'module-b rebuilt with the same release')
        with self.assertRaisesRegex(ValueError, 'differs from its provenance hash: drivers/b.ko'):
            P.copy_board_module(installed, 'drivers/b.ko', self.root/'out/b.ko', provenance, release)
        self.assertFalse((self.root/'out/b.ko').exists())
        (installed/'kernel/drivers/c.ko').write_bytes(b'unrecorded')
        with self.assertRaisesRegex(ValueError, 'no provenance record: drivers/c.ko'):
            P.copy_board_module(installed, 'drivers/c.ko', self.root/'out/c.ko', provenance, release)

    def test_altered_config_symvers_map_or_image_is_refused(self):
        for name in ('objects/.config', 'objects/Module.symvers', 'objects/System.map', 'objects/arch/arm64/boot/Image'):
            with self.subTest(name=name):
                build, built, release, _ = self.fake_build()
                (build/name).write_bytes(b'changed after the build')
                with self.assertRaisesRegex(ValueError, 'differs from result.json: '+name.replace('.', r'\.')):
                    P.verify_build(build, built, release)
                import shutil
                shutil.rmtree(build)

    def test_provenance_must_be_bound_to_result_json(self):
        build, built, release, _ = self.fake_build()
        entries = json.loads((build/'module-provenance.json').read_text())
        entries[0]['sha256'] = hashlib.sha256(b'forged').hexdigest()
        (build/'module-provenance.json').write_text(json.dumps(entries))
        with self.assertRaisesRegex(ValueError, 'differs from result.json: module-provenance.json'):
            P.verify_build(build, built, release)
        # A result.json without recorded outputs (an unverifiable build) is refused too.
        del built['outputs']
        with self.assertRaisesRegex(ValueError, 'records no output hashes'):
            P.verify_build(build, built, release)

    def test_a_deleted_module_cannot_pass_as_built_in(self):
        build, built, release, installed = self.fake_build()
        (installed/'kernel/drivers/a.ko').unlink()
        (installed/'modules.builtin').write_text('kernel/drivers/a.ko\n')
        (build/'objects/include/config').mkdir(parents=True)
        (build/'objects/include/config/kernel.release').write_text(release+'\n')
        built['stages'] = {'kernel-build': dict(status='PASS'), 'modules-install': dict(status='PASS')}
        (build/'result.json').write_text(json.dumps(built))
        selection = self.root/'selection.json'
        selection.write_text(json.dumps(dict(board_modules=['drivers/a.ko', 'drivers/b.ko'], external_modules=[],
                                             required_builtin=[])))
        argv = ['package', '--build', str(build), '--selection', str(selection), '--output', str(self.root/'out')]
        with mock.patch.object(sys, 'argv', argv), contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaisesRegex(ValueError, 'modules.builtin names modules the provenance records'):
                P.main()

    def test_provenance_entries_must_name_this_release(self):
        build, built, release, _ = self.fake_build()
        entries = json.loads((build/'module-provenance.json').read_text())
        entries[1]['path'] = entries[1]['path'].replace(release, 'other')
        (build/'module-provenance.json').write_text(json.dumps(entries))
        built['outputs']['module-provenance.json'] = P.sha(build/'module-provenance.json')
        with self.assertRaisesRegex(ValueError, 'outside'):
            P.verify_build(build, built, release)

    def test_selection_is_the_booted_module_set(self):
        selection = json.loads(P.SELECTION.read_text())
        self.assertEqual(len(selection["board_modules"]), 149)  # k116 package (video modules added)
        self.assertEqual(len(selection['board_modules']), len(set(selection['board_modules'])))
        self.assertEqual([m['name'] for m in selection['external_modules']],
                         ['rog5-aura', 'rog5-aw8697', 'rog5-bt-activate', 'rog5-gmu-bind', 'rog5-input-boost', 'rog5-pmic-pon-readonly', 'rog5-s12-ufs-vote', 'rog5-vcnl36866', 'rog5-wifi-activate', 'rog5_fts3658u'])
        for item in selection['external_modules']:
            self.assertTrue((REPO/item['source']/'Makefile').is_file(), item)


if __name__ == '__main__':
    unittest.main(verbosity=2)
