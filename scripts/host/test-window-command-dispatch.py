#!/usr/bin/env python3
"""Execute the pinned event-loop dispatch segment with deterministic time adapters.

Actual queue methods and corrected native/plugin routing are extracted; engine,
clock, background services and Wayland endpoints are fixtures. No VM/phone proof.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import time

BASE = '85b2303e2f09ae7b7b993641f90061a200f03d53'
PREFIX = 'compositor/src/bin/deniald/'
FILES = [PREFIX + name for name in ('flutter_event_loop.rs', 'flutter_settings_sync.rs',
                                  'flutter_runtime/service_bridge.rs', 'wire.rs')]
FILES.append('compositor/src/bin/deniald.rs')
PATCH = 'patches/denial-85b2303e/0009-service-window-commands-before-background-yield.patch'


def function(source, name):
    match = re.search(r'(?m)^\s*(?:pub(?:\([^\n)]*\))? )?fn ' + re.escape(name) + r'\(', source)
    if not match:
        raise ValueError('missing production function: ' + name)
    start = source.index('{', match.start())
    end, depth = start + 1, 1
    while depth:
        depth += (source[end] == '{') - (source[end] == '}')
        end += 1
    return source[match.start():end].replace('pub(super)', 'pub(crate)')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True, help='Git repository containing pinned Denial commit')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--before-only', action='store_true', help='Reproduce the unfixed failure; returns FAIL')
    args = parser.parse_args()
    rustc = shutil.which(os.environ.get('RUSTC', 'rustc'))
    if not rustc:
        parser.error('BLOCKED: Rust compiler missing')
    repo = Path(__file__).resolve().parents[2]
    output = args.output.absolute()
    output.mkdir(parents=True, exist_ok=False)
    stage = output / 'source'
    for name in FILES:
        p = stage / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(subprocess.check_output(['git', '-C', str(args.source), 'show', BASE + ':' + name], timeout=15))
    before = {name: (stage/name).read_text() for name in FILES}
    variants = [('before', before)]
    patch = repo / PATCH
    if not args.before_only:
        for flags in (['--check'], []):
            subprocess.run(['git', 'apply', *flags, str(patch)], cwd=stage, check=True, timeout=15)
        variants.append(('after', {name: (stage/name).read_text() for name in FILES}))
    fixture = (repo/'tools/denial-modifier-tests/window-dispatch-fixture.rs').read_text()
    result = {'scope': __doc__, 'source_commit': BASE, 'phone': 'NOT RUN', 'vm': 'NOT RUN',
              'patch_sha256': None if args.before_only else hashlib.sha256(patch.read_bytes()).hexdigest(), 'runs': []}
    for label, files in variants:
        loop = files[PREFIX+'flutter_event_loop.rs']
        start = loop.index('        let runtime = flutter\n', loop.index('refreshed Flutter bundle without restarting'))
        end = loop.index('        synchronize_flutter_scene(runtime, &mut events)?;', start)
        segment = loop[start:end]
        names = ['drain_window_commands'] + (['drain_window_command_batch'] if label == 'after' else [])
        wire = '\n'.join(function(files[PREFIX+'wire.rs'], name) for name in names)
        runtime = '\n'.join(function(files[PREFIX+'flutter_runtime/service_bridge.rs'], name) for name in names)
        management = files[PREFIX+'flutter_settings_sync.rs']
        dispatch = '\n'.join(function(management, name) for name in ('dispatch_flutter_window_commands', 'apply_flutter_window_commands')) if label == 'after' else ''
        late_start = management.index('        let commands = runtime.drain_window_commands()')
        late_end = management.index('\n    }\n    if events.pending_window_events', late_start)
        late = management[late_start:late_end]
        unit = fixture.replace('// @SEGMENT@', segment).replace('// @WIRE_METHODS@', wire).replace('// @RUNTIME_METHODS@', runtime).replace('// @DISPATCH@', dispatch).replace('// @LATE_DISPATCH@', late)
        path = output/(label+'.rs'); path.write_text(unit)
        binary = output/label
        build = [rustc, '--edition=2024', '--test', str(path), '-o', str(binary)]
        if label == 'before':
            build += ['--cfg', 'before']
        start_time = time.monotonic()
        p = subprocess.run(build, env=dict(os.environ, TMPDIR=str(output)), capture_output=True, text=True, timeout=45)
        (output/(label+'-build.log')).write_text(p.stdout+p.stderr)
        build_seconds = time.monotonic()-start_time
        if p.returncode:
            print(p.stderr)
            p.check_returncode()
        command = [str(binary), '--test-threads=1']
        start_time = time.monotonic()
        run = subprocess.run(command, capture_output=True, text=True, timeout=10)
        (output/(label+'.log')).write_text(run.stdout+run.stderr)
        expected = '2 passed; 6 failed' if label == 'before' else '9 passed; 0 failed'
        result['runs'].append({'variant': label, 'build_command': build, 'build_seconds': build_seconds,
                               'command': command, 'duration_seconds': time.monotonic()-start_time,
                               'exit_status': run.returncode, 'expected_observed': expected in run.stdout and run.returncode == (101 if label == 'before' else 0),
                               'unit_sha256': hashlib.sha256(unit.encode()).hexdigest(),
                               'source_hashes': {name: hashlib.sha256(text.encode()).hexdigest() for name, text in files.items()}})
    result['counterexamples_observed'] = result['runs'][0]['expected_observed']
    result['status'] = 'PASS' if not args.before_only and all(r['expected_observed'] for r in result['runs']) else 'FAIL'
    (output/'result.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result, indent=2))
    return 0 if result['status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
