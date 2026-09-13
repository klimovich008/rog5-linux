#!/usr/bin/env python3
"""Compile the production opt-in/bounded native trace helper with an injected sink.

No engine, Wayland, VM or phone behavior is simulated or qualified. Call-site
integration requires the exact compositor build and a separately bounded VM run.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import time

PREFIX = 'compositor/src/bin/'
FILES = [PREFIX + 'deniald.rs'] + [PREFIX + 'deniald/' + p for p in (
    'wire/decode.rs', 'flutter_settings_sync.rs', 'wayland_frontend/window_management.rs')]
PATCH = 'patches/denial-85b2303e/0011-trace-native-focus-delivery.patch'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True, type=Path, help='Retained Denial source with patch 0009 applied')
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    rustc = shutil.which(os.environ.get('RUSTC', 'rustc'))
    if not rustc:
        parser.error('BLOCKED: Rust compiler missing')
    repo = Path(__file__).resolve().parents[2]
    output = args.output.absolute()
    output.mkdir(parents=True, exist_ok=False)
    stage = output / 'source'
    inputs = {}
    for name in FILES:
        data = (args.source / name).read_bytes()
        inputs[name] = hashlib.sha256(data).hexdigest()
        p = stage / name; p.parent.mkdir(parents=True, exist_ok=True); p.write_bytes(data)
    patch = repo / PATCH
    for flags in (['--check'], []):
        subprocess.run(['git', 'apply', *flags, str(patch)], cwd=stage, check=True, timeout=15)
    helper = stage / (PREFIX + 'deniald/focus_trace.rs')
    fixture = repo / 'tools/denial-modifier-tests/native-focus-trace-tests.rs'
    # Exclude only the logging dependency adapter from this standalone std-only
    # test unit. Production keeps log() available to full cargo test builds.
    helper_text = helper.read_text()
    adapter = helper_text.index('pub(super) fn log(')
    policy = helper_text[:adapter]
    unit = 'mod focus_trace {\n' + policy.replace('//!', '//', 1) + '\n' + fixture.read_text() + '\n}\n'
    source = output / 'tests.rs'; source.write_text(unit)
    binary = output / 'tests'
    commands = [[rustc, '--edition=2024', '--test', str(source), '-o', str(binary)],
                [str(binary), '--test-threads=1']]
    runs = []
    for label, command in zip(('build', 'test'), commands):
        started = time.monotonic()
        proc = subprocess.run(command, capture_output=True, text=True,
                              env=dict(os.environ, TMPDIR=str(output)), timeout=45)
        (output / (label + '.log')).write_text(proc.stdout + proc.stderr)
        runs.append({'command': command, 'duration_seconds': time.monotonic() - started,
                     'exit_status': proc.returncode})
        if proc.returncode:
            break
    status = 'PASS' if len(runs) == 2 and all(r['exit_status'] == 0 for r in runs) else 'FAIL'
    result = {'status': status, 'scope': __doc__, 'cases': 6 if status == 'PASS' else None,
              'source_hashes': inputs, 'patch_sha256': hashlib.sha256(patch.read_bytes()).hexdigest(),
              'helper_sha256': hashlib.sha256(helper.read_bytes()).hexdigest(),
              'test_unit_sha256': hashlib.sha256(source.read_bytes()).hexdigest(), 'runs': runs,
              'exact_compositor_build': 'NOT RUN', 'vm': 'NOT RUN', 'phone': 'NOT RUN'}
    (output / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))
    return 0 if status == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
