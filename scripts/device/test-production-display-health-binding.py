#!/usr/bin/env python3
"""Compose and exercise the actual health binding with synthetic authority only."""
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
FIXTURES = ROOT / 'scripts/device/fixtures/display-health'


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def apply(directory, patch, *flags):
    subprocess.run(['git', 'apply', *flags, str(patch)], cwd=directory,
                   check=True, capture_output=True, timeout=10)


def compose(work, pins):
    """Reuse the existing worker and public-cohort builders, without private inputs."""
    worker = runpy.run_path(str(ROOT / 'scripts/device/test-production-display-worker.py'))
    wp = json.loads((worker['FIXTURES'] / 'source-pins.json').read_text())
    cohort = runpy.run_path(str(ROOT / 'scripts/device/test-production-display-cohort.py'))
    sources, after = work / 'sources', work / 'after'
    sources.mkdir(); after.mkdir()
    cohort['assemble'](sources)
    for name, expected in wp['before'].items():
        path = (sources / 'session.py' if name == 'production-cohort/session.py'
                else ROOT / 'scripts/host/release-acceptance.py' if name == 'release-acceptance.py.txt'
                else worker['FIXTURES'] / name)
        raw = path.read_bytes()
        if digest(raw) != expected:
            raise ValueError('worker composition changed: ' + name)
        target = after / name
        target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(raw)
    patch = ROOT / 'patches/display-controller/0012-worker-source-lifetime.patch'
    apply(after, patch, '--check'); apply(after, patch)
    for name, expected in wp['after'].items():
        if digest((after / name).read_bytes()) != expected:
            raise ValueError('worker output changed: ' + name)
    worker['prepare_loader'](work, sources, after, wp)
    loader = work / 'loader'
    apply(loader, ROOT / 'patches/display-controller/0013-checked-worker-sources.patch')
    contents = {'production-cohort/' + p.name: p.read_bytes()
                for p in (loader / 'production-cohort').iterdir() if p.is_file()}
    contents.update({'worker-closure/' + name: (after / name).read_bytes()
                     for name in wp['after'] if '/' not in name})
    contents.update({'health-private/' + p.name: p.read_bytes()
                     for p in FIXTURES.glob('*.txt')})
    contents['current-callers/live-admission.py.txt'] = (loader / 'current-callers/live-admission.py.txt').read_bytes()
    contents['repo/scripts/device/fixtures/display-worker/checked-loader.py'] = (worker['FIXTURES'] / 'checked-loader.py').read_bytes()
    for name, row in pins['transitions'].items():
        if digest(contents[name]) != row['before_sha256']:
            raise ValueError('health base changed: ' + name)
    packet = work / 'packet.txt'
    packet.write_bytes(b''.join(
        ('===== FILE ' + name + ' SHA256 ' + digest(raw) + ' =====\n').encode()
        + raw + b'\n===== END FILE =====\n' for name, raw in sorted(contents.items())))
    return packet


def main():
    if os.getuid() != 1000 or os.geteuid() != 1000:
        raise ValueError('ordinary UID1000 required')
    pins = json.loads((FIXTURES / 'source-pins.json').read_text())
    for name, expected in pins['fixtures'].items():
        if digest((FIXTURES / name).read_bytes()) != expected:
            raise ValueError('health fixture changed: ' + name)
    patch = ROOT / 'patches/display-controller/0014-checked-health-sources.patch'
    if digest(patch.read_bytes()) != pins['patch_sha256']:
        raise ValueError('health patch changed')
    test = FIXTURES / 'binding.py'
    cls = next(n for n in ast.parse(test.read_bytes()).body
               if isinstance(n, ast.ClassDef) and n.name == 'HealthSources')
    actual = sorted(n.name for n in cls.body if isinstance(n, ast.FunctionDef) and n.name.startswith('test_'))
    selected = [name for batch in pins['batches'] for name in batch]
    if actual != sorted(selected) or len(selected) != len(set(selected)):
        raise ValueError('health case inventory differs')
    scratch = ROOT / 'build'; scratch.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='display-health-binding-', dir=scratch) as temporary:
        work = Path(temporary); packet = compose(work, pins)
        for batch in pins['batches']:
            command = [sys.executable, '-B', '-O', str(test), '--packet', str(packet), '--patch', str(patch)]
            command += [arg for name in batch for arg in ('--case', name)]
            result = subprocess.run(command, env=dict(os.environ, TMPDIR=str(work)),
                                    timeout=90, text=True, capture_output=True)
            print(result.stdout, end=''); print(result.stderr, end='', file=sys.stderr)
            if result.returncode:
                raise RuntimeError('health batch failed: ' + ', '.join(batch))
            print(f'PASS behavioral: {len(batch)} health binding cases', flush=True)
    print(f'PASS behavioral: {len(selected)} actual health binding regressions')
    print('NOT RUN private bootstrap authentication, installed runtime, VM or phone operation')


if __name__ == '__main__':
    main()
