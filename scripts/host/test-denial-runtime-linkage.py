#!/usr/bin/env python3
"""Real host dynamic-loader regressions for the confined linkage probe."""
import os
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


class Linkage(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.temp.cleanup)
        cls.root = Path(cls.temp.name)
        cls.probe = cls.root / 'probe'
        subprocess.run([os.environ.get('RUSTC', 'rustc'), '--edition=2024', '-Dwarnings',
                        os.environ.get('PROBE_SOURCE', str(ROOT / 'tools/denial-runtime-linkage/probe.rs')), '-o', str(cls.probe)],
                       check=True, capture_output=True, timeout=60)
        cls.build('helper', 'int helper(void){return 1;}')
        cls.build('good', '#include <stdlib.h>\nint entry(void){abort();}\n')
        cls.build('dependent', 'extern int helper(void); int entry(void){return helper();}',
                  ['-L'+str(cls.root), '-lhelper', '-Wl,-rpath,$ORIGIN'])
        cls.build('unresolved', 'extern int absent(void);int entry(void){return absent();}')
        cls.build('cleanup', '#include <unistd.h>\nint entry(void){return 1;}\n'
                  '__attribute__((destructor)) void done(void){write(1,"FIXTURE_CLOSED\\n",15);}')

    @classmethod
    def build(cls, name, source, flags=()):
        path = cls.root / (name + '.c')
        path.write_text(source)
        subprocess.run([os.environ.get('CC', 'cc'), '-shared', '-fPIC', str(path),
                        '-o', str(cls.root / ('lib'+name+'.so')), *flags],
                       check=True, capture_output=True, timeout=30)

    def run_probe(self, name='good', symbol='entry'):
        return subprocess.run([str(self.probe), str(self.root / ('lib'+name+'.so')), symbol],
                              capture_output=True, text=True, timeout=10,
                              env={k:v for k,v in os.environ.items() if not k.startswith('LD_')})

    def test_symbol_is_resolved_but_never_called(self):
        r = self.run_probe()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn('RESULT PASS_LINKAGE_ONLY', r.stdout)

    def test_missing_library_refuses(self):
        r = self.run_probe('absent')
        self.assertNotEqual(r.returncode, 0)
        self.assertNotIn('RESULT PASS', r.stdout)

    def test_missing_symbol_refuses(self):
        r = self.run_probe(symbol='absent')
        self.assertNotEqual(r.returncode, 0)
        self.assertIn('undefined symbol', r.stderr)

    def test_lazy_unresolved_relocation_is_refused_now(self):
        r = self.run_probe('unresolved')
        self.assertNotEqual(r.returncode, 0)
        self.assertIn('undefined symbol', r.stderr)

    def test_dependency_is_in_actual_loader_inventory(self):
        r = self.run_probe('dependent')
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn('OBJECT '+str(self.root / 'libhelper.so'), r.stdout)

    def test_missing_needed_dependency_refuses(self):
        helper = self.root / 'libhelper.so'
        saved = self.root / 'libhelper.saved'
        helper.rename(saved)
        try:
            r = self.run_probe('dependent')
            self.assertNotEqual(r.returncode, 0)
            self.assertIn('libhelper.so', r.stderr)
        finally:
            saved.rename(helper)

    def test_library_cleanup_precedes_success(self):
        r = self.run_probe('cleanup')
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertLess(r.stdout.index('FIXTURE_CLOSED'), r.stdout.index('RESULT PASS_LINKAGE_ONLY'))

    def test_error_path_closes_library_before_failure_receipt(self):
        r = subprocess.run([str(self.probe), str(self.root/'libcleanup.so'), 'absent'],
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=10)
        self.assertNotEqual(r.returncode, 0)
        self.assertLess(r.stdout.index('FIXTURE_CLOSED'), r.stdout.index('FAIL_LINKAGE:'))

    def test_invalid_arguments_refuse_without_success(self):
        for args in [[], ['relative.so','entry'], ['/missing','bad\nsymbol'],
                     ['/missing']+['entry']*17]:
            with self.subTest(args=args):
                r = subprocess.run([str(self.probe), *args], capture_output=True, text=True, timeout=10)
                self.assertNotEqual(r.returncode, 0)
                self.assertIn('usage:', r.stderr)


class ReceiptAndRoot(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location('linkage_checker', ROOT/'scripts/host/check-denial-runtime-linkage.py')
        cls.module = importlib.util.module_from_spec(spec); spec.loader.exec_module(cls.module)

    def test_complete_receipt_is_required(self):
        good = 'LIBRARY /a\nSYMBOL entry\nOBJECT /usr/lib/liba.so\nRESULT PASS_LINKAGE_ONLY\n'
        self.assertEqual(self.module.parse_receipt(good, '/a', ['entry']), ['/usr/lib/liba.so'])
        for value in ['RESULT PASS_LINKAGE_ONLY\n',good+'EXTRA\n',good.replace('SYMBOL entry','SYMBOL other'),
                      good.replace('OBJECT /usr/lib/liba.so','OBJECT /usr/lib/liba.so\nOBJECT /usr/lib/liba.so')]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.module.parse_receipt(value, '/a', ['entry'])

    def test_absolute_symlink_is_resolved_inside_runtime(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); (root/'usr').mkdir();(root/'usr/lib').mkdir()
            (root/'usr/lib/object').write_bytes(b'exact');(root/'alias').symlink_to('/usr/lib/object')
            rows = [{'path':n,'type':'directory'} for n in ['usr','usr/lib']]
            rows += [{'path':'alias','type':'symlink','target':'/usr/lib/object'},
                     {'path':'usr/lib/object','type':'file','size':5,'sha256':hashlib.sha256(b'exact').hexdigest()}]
            runtime = self.module.Runtime(root,rows)
            self.assertEqual(runtime.resolve('/alias'), root/'usr/lib/object')
            (root/'usr/lib/object').write_bytes(b'wrong')
            with self.assertRaisesRegex(ValueError,'bytes changed'):
                runtime.resolve('/alias')

    def test_changed_link_and_traversal_refuse(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory);(root/'alias').symlink_to('../../outside')
            runtime = self.module.Runtime(root,[{'path':'alias','type':'symlink','target':'../../outside'}])
            with self.assertRaisesRegex(ValueError,'escapes root'):
                runtime.resolve('/alias')
            (root/'alias').unlink();(root/'alias').symlink_to('/different')
            with self.assertRaisesRegex(ValueError,'link changed'):
                runtime.resolve('/alias')

    def test_duplicate_manifest_paths_refuse(self):
        with self.assertRaisesRegex(ValueError,'duplicate runtime'):
            self.module.Runtime(Path('/not-accessed'),[{'path':'a'},{'path':'a'}])


if __name__ == '__main__':
    unittest.main()
