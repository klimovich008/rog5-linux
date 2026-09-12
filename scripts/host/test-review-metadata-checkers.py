#!/usr/bin/env python3
"""Semantic metadata rejection remains active with Python optimization enabled."""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


class Checkers(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        subprocess.run(['git', 'init', '-q', str(self.root)], check=True)
        for name in ('manifests/artifact-sets.json', 'manifests/artifacts.tsv',
                     'manifests/current-artifact.json', 'packaging/arch/mobile-package-closure.json',
                     'configs/denial/source-lock-v1.json'):
            path = self.root/name
            path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT/name, path)

    def check(self, checker, expect):
        program = ('import importlib.util, pathlib, sys; '
                   's=importlib.util.spec_from_file_location("checker",sys.argv[1]); '
                   'm=importlib.util.module_from_spec(s); s.loader.exec_module(m); '
                   'm.validate(pathlib.Path(sys.argv[2]))')
        result = subprocess.run([sys.executable, '-O', '-c', program,
                                 str(ROOT/'scripts/host'/checker), str(self.root)],
                                capture_output=True, text=True, timeout=10)
        if expect:
            self.assertEqual(result.returncode, 0, result.stderr)
        else:
            self.assertNotEqual(result.returncode, 0, result.stdout)
            self.assertIn('ValueError', result.stderr)

    def alter(self, name, change):
        path = self.root/name
        data = json.loads(path.read_text())
        change(data)
        path.write_text(json.dumps(data))

    def test_valid_metadata_under_optimization(self):
        self.check('check-artifact-inventory.py', True)
        self.check('check-mobile-package-closure.py', True)

    def test_unclassified_registered_artifact_refuses_under_optimization(self):
        def remove(data):
            entry = next(x for x in data['sets'] if x['id'] == 'artifacts/buttons-indicator-v1')
            entry['outputs'] = [x for x in entry['outputs'] if not x['path'].endswith('.dtb')]
        self.alter('manifests/artifact-sets.json', remove)
        self.check('check-artifact-inventory.py', False)

    def test_missing_dependency_edge_refuses_under_optimization(self):
        self.alter('packaging/arch/mobile-package-closure.json',
                   lambda data: data['dependency_edges'].pop())
        self.check('check-mobile-package-closure.py', False)

    def test_wrong_provider_refuses_under_optimization(self):
        def replace(data):
            edge = next(e for e in data['dependency_edges'] if e['dependency'] == 'mesa')
            edge['provider'] = 'glibc'
        self.alter('packaging/arch/mobile-package-closure.json', replace)
        self.check('check-mobile-package-closure.py', False)


if __name__ == '__main__':
    unittest.main(verbosity=2)
