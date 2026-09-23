#!/usr/bin/env python3
"""Run rebase-kernel-series.py on a toy kernel repository: one clean patch,
one conflicting patch resolved through continue, then export and the
reproduction check. Tag signatures are skipped with --no-verify; the real
v7.1.4 -> v7.2.7 replay is recorded in test-results."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[2]
TOOL = REPO/'scripts/host/rebase-kernel-series.py'


def git(*args, cwd):
    subprocess.run(['git', *args], cwd=cwd, check=True, capture_output=True)


def run(*args):
    return subprocess.run([sys.executable, str(TOOL), *args], capture_output=True, text=True)


class Rebase(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = self.root = Path(self.temp.name)
        kernel = root/'kernel'
        kernel.mkdir()
        git('init', '-q', cwd=kernel)
        (kernel/'a.c').write_text('int a;\n')
        (kernel/'b.c').write_text('int b;\nint keep;\n')
        git('add', '-A', cwd=kernel)
        git('-c', 'user.name=t', '-c', 'user.email=t@t', 'commit', '-qm', 'v1', cwd=kernel)
        base = kernel.parent/'base'
        subprocess.run(['cp', '-a', str(kernel), str(base)], check=True)
        (base/'a.c').write_text('int a;\nint a2;\n')
        (base/'b.c').write_text('int b;\nint b2;\n')
        diff_a = subprocess.run(['git', 'diff', '--', 'a.c'], cwd=base, capture_output=True, text=True).stdout
        diff_b = subprocess.run(['git', 'diff', '--', 'b.c'], cwd=base, capture_output=True, text=True).stdout
        series = self.series = root/'patches'
        series.mkdir()
        (series/'0001-a.patch').write_text('From: t\nSubject: a\n\nbody a\n---\n'+diff_a)
        (series/'0002-b.patch').write_text(diff_b)
        (series/'series.production').write_text('# test\n0001-a.patch\n0002-b.patch\n')
        (kernel/'b.c').write_text('int b;\nint changed;\n')
        git('-c', 'user.name=t', '-c', 'user.email=t@t', 'commit', '-qam', 'v2', cwd=kernel)
        git('tag', 'v2', cwd=kernel)
        self.kernel = kernel
        self.policy = root/'policy.json'
        self.policy.write_text(json.dumps(dict(base_commit='old', base_archive_sha256='old', patch_dir='old', keep='yes')))

    def test_conflict_continue_export(self):
        work = self.root/'work'
        first = run('start', '--linux-git', str(self.kernel), '--tag', 'v2', '--from', str(self.series), '--work', str(work), '--no-verify')
        self.assertEqual(first.returncode, 2, first.stderr)
        self.assertEqual(json.loads(first.stdout)['patch'], '0002-b.patch')
        early = run('export', '--work', str(work), '--output', str(self.root/'x'), '--policy-from', str(self.policy))
        self.assertEqual(early.returncode, 1)
        self.assertIn('not fully applied', early.stderr)
        refused = run('continue', '--work', str(work))
        self.assertEqual(refused.returncode, 1)
        self.assertIn('.rej', refused.stderr)
        (work/'tree/b.c').write_text('int b;\nint changed;\nint b2;\n')
        for leftover in (work/'tree').rglob('*.rej'):
            leftover.unlink()
        done = run('continue', '--work', str(work))
        self.assertEqual(done.returncode, 0, done.stderr)
        out, policy = self.root/'patches-v2', self.root/'policy-v2.json'
        exported = run('export', '--work', str(work), '--output', str(out), '--policy-from', str(self.policy), '--policy-output', str(policy))
        self.assertEqual(exported.returncode, 0, exported.stderr)
        self.assertTrue((out/'0001-a.patch').read_text().startswith('From: t\nSubject: a\n'))
        self.assertIn('+int b2;', (out/'0002-b.patch').read_text())
        new = json.loads(policy.read_text())
        self.assertEqual((new['keep'], new['patch_dir']), ('yes', str(out)))
        self.assertEqual(len(new['base_commit']), 40)
        self.assertEqual(json.loads((work/'state.json').read_text())['resolved'], ['0002-b.patch'])

    def test_unsigned_tag_is_refused_without_no_verify(self):
        result = run('start', '--linux-git', str(self.kernel), '--tag', 'v2', '--from', str(self.series), '--work', str(self.root/'w2'))
        self.assertEqual(result.returncode, 1)
        self.assertIn('signature', result.stderr)


if __name__ == '__main__':
    unittest.main(verbosity=2)
