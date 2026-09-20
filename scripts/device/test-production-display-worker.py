#!/usr/bin/env python3
"""Actual worker/identity regressions; private admission and device I/O are fixtures."""
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
FIXTURES = ROOT / 'scripts/device/fixtures/display-worker'


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def prepare_loader(work, sources, after, pins):
    """Reuse existing source composition; retain only the packet the tests consume."""
    loader = work / 'loader'
    callers = loader / 'current-callers'
    callers.mkdir(parents=True)
    admission = callers / 'live-admission.py.txt'
    shutil.copyfile(ROOT / 'scripts/device/fixtures/display-loader/live-admission-before.py.txt',
                    admission)
    for filename, directory, include in (
            ('0010-private-display-api.patch', callers, admission.name),
            ('0011-production-cold-boot.patch', loader, 'current-callers/' + admission.name)):
        for options in (['--check'], []):
            # git apply matches --include after adding its repository prefix.
            # Scratch lives inside ROOT/build, so an unprefixed name skips it.
            selected = str(directory.relative_to(ROOT) / include)
            subprocess.run(['git', 'apply', *options, '--include=' + selected,
                            str(ROOT / 'patches/display-controller' / filename)],
                           cwd=directory, check=True, capture_output=True, timeout=10)
    expected = pins['checked_loader']
    if digest(admission.read_bytes()) != expected['admission_sha256']:
        raise ValueError('checked-loader admission composition differs')
    composed = loader / 'production-cohort'
    shutil.copytree(sources, composed)
    shutil.copyfile(after / 'production-cohort/session.py', composed / 'session.py')
    contents = {name: (after / name).read_bytes() for name in pins['after']}
    contents['current-callers/' + admission.name] = admission.read_bytes()
    packet = loader / 'packet.txt'
    packet.write_bytes(b''.join(
        ('===== FILE ' + name + ' SHA256 ' + digest(raw) + ' =====\n').encode()
        + raw + b'\n===== END FILE =====\n' for name, raw in contents.items()))
    patch = ROOT / 'patches/display-controller/0013-checked-worker-sources.patch'
    if digest(patch.read_bytes()) != expected['patch_sha256']:
        raise ValueError('checked-loader patch changed')
    before_sha = pins['after']['production-cohort/session.py']
    # Leave composed at the reviewed BEFORE bytes: each test applies the patch.
    for options, sha in ((['--check'], None), ([], expected['after_session_sha256']),
                         (['--reverse', '--check'], None), (['--reverse'], before_sha)):
        subprocess.run(['git', 'apply', *options, str(patch)], cwd=loader,
                       check=True, capture_output=True, timeout=10)
        if sha and digest((composed / 'session.py').read_bytes()) != sha:
            raise ValueError('checked-loader application bytes differ')
    return ['--packet', str(packet), '--patch', str(patch), '--sources', str(composed)]


def main():
    if os.getuid() != 1000 or os.geteuid() != 1000:
        raise ValueError('ordinary UID1000 required; no root execution')
    pins = json.loads((FIXTURES / 'source-pins.json').read_text())
    for name, expected in pins['fixtures'].items():
        if digest((FIXTURES / name).read_bytes()) != expected:
            raise ValueError('retained worker fixture changed: ' + name)
    patch = ROOT / 'patches/display-controller/0012-worker-source-lifetime.patch'
    if digest(patch.read_bytes()) != pins['patch_sha256']:
        raise ValueError('worker patch changed')
    cohort_path = ROOT / 'scripts/device/test-production-display-cohort.py'
    if digest(cohort_path.read_bytes()) != pins['cohort_test_sha256']:
        raise ValueError('cohort test changed')
    cohort = runpy.run_path(str(cohort_path))
    scratch = ROOT / 'build'
    scratch.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='display-worker-', dir=scratch) as temporary:
        work = Path(temporary)
        sources, before, after = (work / name for name in ('sources', 'before', 'after'))
        for directory in (sources, before, after):
            directory.mkdir()
        cohort['assemble'](sources)
        contents = {}
        for name, expected in pins['before'].items():
            path = (sources / 'session.py' if name == 'production-cohort/session.py'
                    else ROOT / 'scripts/host/release-acceptance.py' if name == 'release-acceptance.py.txt'
                    else FIXTURES / name)
            raw = path.read_bytes()
            if digest(raw) != expected:
                raise ValueError('worker base changed: ' + name)
            contents[name] = raw
        contents[cohort_path.name] = cohort_path.read_bytes()
        for name, raw in contents.items():
            for directory in (before, after):
                path = directory / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(raw)
        # Exact forward/reverse application verifies the final composed bytes.
        for options, expected in ((['--check'], None), ([], pins['after']),
                                  (['--reverse', '--check'], None),
                                  (['--reverse'], pins['before']), ([], pins['after'])):
            subprocess.run(['git', 'apply', *options, str(patch)], cwd=after,
                           check=True, capture_output=True, timeout=10)
            if expected:
                for name, sha in expected.items():
                    if digest((after / name).read_bytes()) != sha:
                        raise ValueError('worker application bytes differ: ' + name)
        intermediate = work / 'intermediate'
        intermediate.mkdir()
        shutil.copyfile(after / 'ssh-worker.py.txt', intermediate / 'ssh-worker.py.txt')
        finalization_patch = FIXTURES / 'finalization.patch'
        for options in (['--reverse', '--check'], ['--reverse']):
            subprocess.run(['git', 'apply', *options, str(finalization_patch)], cwd=intermediate,
                           check=True, capture_output=True, timeout=10)
        if digest((intermediate / 'ssh-worker.py.txt').read_bytes()) != pins['finalization_before_sha256']:
            raise ValueError('finalization negative-control source differs')
        # Preserve the reviewed test interface without retaining a private packet.
        packet = work / 'source-packet.txt'
        packet.write_bytes(b''.join(
            ('===== FILE ' + name + ' SHA256 ' + digest(raw)
             + ' ORIGINAL_SHA256 fixture =====\n').encode()
            + raw + b'\n===== END FILE =====\n' for name, raw in contents.items()))
        common = ['--packet', str(packet), '--patch', str(patch), '--sources', str(sources),
                  '--acceptance', str(ROOT / 'scripts/host/release-acceptance.py')]
        loader_options = prepare_loader(work, sources, after, pins)
        total = 0
        for filename in ('binding.py', 'lifetime.py', 'finalization.py', 'checked-loader.py'):
            options = (['--before', str(intermediate / 'ssh-worker.py.txt'),
                        '--after', str(after / 'ssh-worker.py.txt')]
                       if filename == 'finalization.py' else common)
            if filename == 'lifetime.py':
                options = ['--binding-test', str(FIXTURES / 'binding.py'), *options]
            if filename == 'checked-loader.py':
                options = loader_options
            names = pins['cases'][filename]
            classname = {'binding.py': 'Binding', 'lifetime.py': 'Focused',
                         'finalization.py': 'Finalization', 'checked-loader.py': 'Loader'}[filename]
            tree = ast.parse((FIXTURES / filename).read_bytes())
            cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == classname)
            actual_names = sorted(n.name for n in cls.body
                                  if isinstance(n, ast.FunctionDef) and n.name.startswith('test_'))
            if names != actual_names:
                raise ValueError('worker case inventory changed: ' + filename)
            for offset in range(0, len(names), 6):
                selected = names[offset:offset + 6]
                command = [sys.executable, '-B', '-O', str(FIXTURES / filename), *options]
                command += [arg for name in selected for arg in ('--case', name)]
                result = subprocess.run(command, env=dict(os.environ, TMPDIR=str(work)),
                                        timeout=90, text=True, capture_output=True)
                print(result.stdout, end='')
                print(result.stderr, end='', file=sys.stderr)
                if result.returncode:
                    raise RuntimeError('worker batch failed: ' + ', '.join(selected))
                total += len(selected)
                print(f'PASS behavioral: {filename}: {len(selected)} cases', flush=True)
        print(f'PASS behavioral: {total} actual worker/source-identity/finalization/loader regressions')
        print('PASS applicability: exact source composition and strict forward/reverse patch application')
        print('NOT RUN private admission, installed runtime, real credentials, VM or phone operation')


if __name__ == '__main__':
    main()
