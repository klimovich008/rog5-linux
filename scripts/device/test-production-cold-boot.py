#!/usr/bin/env python3
"""Clean-checkout cold-boot caller regressions; all external effects are inert."""
import ast
import hashlib
import json
import os
from pathlib import Path
import runpy
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / 'scripts/device/fixtures/display-cold-boot'


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def main():
    if os.getuid() != 1000 or os.geteuid() != 1000:
        raise ValueError('ordinary UID1000 required; no root execution')
    pins = json.loads((FIXTURES / 'source-pins.json').read_text())
    for name, expected in pins['fixtures'].items():
        if digest((FIXTURES / name).read_bytes()) != expected:
            raise ValueError('retained fixture changed: ' + name)
    patch = ROOT / 'patches/display-controller/0011-production-cold-boot.patch'
    if digest(patch.read_bytes()) != pins['patch_sha256']:
        raise ValueError('cold-boot patch identity changed')
    # Existing cohort composition is authoritative; do not copy its patch order.
    cohort = runpy.run_path(str(ROOT / 'scripts/device/test-production-display-cohort.py'))
    scratch = ROOT / 'build'
    scratch.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='cold-boot-integration-', dir=scratch) as temporary:
        work = Path(temporary)
        sources, callers = work / 'sources', work / 'callers'
        sources.mkdir()
        callers.mkdir()
        cohort['assemble'](sources)
        for name in pins['callers']:
            stem = name.removesuffix('.py.txt')
            shutil.copyfile(ROOT / 'scripts/device/fixtures/display-loader' /
                            (stem + '-before.py.txt'), callers / name)
        api_patch = ROOT / 'patches/display-controller/0010-private-display-api.patch'
        for options in (['--check'], []):
            subprocess.run(['git', 'apply', *options, str(api_patch)], cwd=callers,
                           check=True, capture_output=True, timeout=10)
        sections = []
        for prefix, directory, expected in (
                ('production-cohort', sources, pins['cohort']),
                ('current-callers', callers, pins['callers'])):
            for name, sha in expected.items():
                raw = (directory / name).read_bytes()
                if digest(raw) != sha:
                    raise ValueError('composed source changed: ' + name)
                sections.append((prefix + '/' + name, raw))
        for name in pins['fixtures']:
            if name.endswith('.py.txt'):
                sections.append(('downstream/' + name, (FIXTURES / name).read_bytes()))
        packet = work / 'source-packet.txt'
        packet.write_bytes(b''.join(
            ('===== FILE ' + name + ' SHA256 ' + digest(raw) + ' =====\n').encode()
            + raw + b'\n===== END FILE =====\n' for name, raw in sections))
        common = ['--packet', str(packet), '--patch', str(patch), '--sources', str(sources)]
        total = 0
        for filename, classname, count, options in (
                ('integration.py', 'Integration', 28, []),
                ('owned-publication.py', 'Owned', 28,
                 ['--base-test', str(FIXTURES / 'integration.py')]),
                ('finalization.py', 'Finalization', 14,
                 ['--owned-test', str(FIXTURES / 'owned-publication.py'),
                  '--base-test', str(FIXTURES / 'integration.py')])):
            path = FIXTURES / filename
            tree = ast.parse(path.read_bytes())
            cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == classname)
            names = sorted(n.name for n in cls.body
                           if isinstance(n, ast.FunctionDef) and n.name.startswith('test_'))
            if len(names) != count:
                raise ValueError('reviewed test inventory changed: ' + filename)
            # Bound retained dynamic modules between batches. Children remain in
            # the repository runner's process group for its cancellation cleanup.
            for offset in range(0, len(names), 4):
                selected = names[offset:offset + 4]
                cases = ([classname + '.' + name for name in selected] if not options
                         else [arg for name in selected for arg in ('--case', name)])
                command = [sys.executable, '-B', '-O', str(path), *options, *common, *cases]
                result = subprocess.run(command, env=dict(os.environ, TMPDIR=str(work)),
                                        timeout=90, text=True, capture_output=True)
                print(result.stdout, end='')
                print(result.stderr, end='', file=sys.stderr)
                if result.returncode:
                    raise RuntimeError('cold-boot batch failed: ' + ', '.join(selected))
                total += len(selected)
                print(f'PASS behavioral: {classname} {offset // 4 + 1}: {len(selected)} cases', flush=True)
        print(f'PASS behavioral: {total} actual cold-boot/controller/launcher regressions')
        print('PASS applicability: exact composed cohort/callers and strict 0011 application')
        print('NOT RUN private runtime authority, real credentials/claims, VM or phone operation')


if __name__ == '__main__':
    main()
