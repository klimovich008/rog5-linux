#!/usr/bin/env python3
"""Compile the actual pinned Denial broker before/after diagnostic separation."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import time


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    repo = Path(__file__).resolve().parents[2]
    spec = importlib.util.spec_from_file_location('selection', repo / 'scripts/host/test-denial-modifier-selection.py')
    selection = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(selection)
    rustc = os.environ.get('RUSTC', 'rustc')
    if not shutil.which(rustc):
        parser.error('BLOCKED: Rust compiler missing')
    path = 'compositor/src/bin/deniald/flutter_runtime/output_pipeline.rs'
    audit = 'compositor/src/bin/deniald/flutter_runtime/render_audit.rs'
    output = args.output.absolute()
    output.mkdir(parents=True, exist_ok=False)
    source = output / 'source'
    originals = {}
    for name in (path, audit, 'compositor/src/bin/deniald/flutter_runtime/output_runtime.rs'):
        originals[name] = subprocess.check_output(['git', '-C', str(args.source), 'show', selection.BASE + ':' + name], text=True, timeout=10)
        target = source / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(originals[name])
    patch = repo / 'patches/denial-85b2303e/0002-distinguish-render-target-refusals.patch'
    subprocess.run(['git', 'apply', '--check', str(patch)], cwd=source, check=True, timeout=10)
    subprocess.run(['git', 'apply', str(patch)], cwd=source, check=True, timeout=10)
    trace_patch = repo / 'patches/denial-85b2303e/0003-trace-render-authorization-history.patch'
    subprocess.run(['git', 'apply', '--check', str(trace_patch)], cwd=source, check=True, timeout=10)
    subprocess.run(['git', 'apply', str(trace_patch)], cwd=source, check=True, timeout=10)
    result = {'scope': 'actual broker functions with data adapters; no VM or phone proof', 'physical': 'NOT RUN', 'source_commit': selection.BASE, 'patch_sha256': hashlib.sha256(patch.read_bytes()).hexdigest(), 'trace_patch_sha256': hashlib.sha256(trace_patch.read_bytes()).hexdigest(), 'runs': {}}
    fixture = (repo / 'tools/denial-modifier-tests/broker-fixture.rs').read_text()
    for label, text in [('before', originals[path]), ('after', (source / path).read_text())]:
        enums = []
        for name in ('BufferState', 'RenderTargetBlocked'):
            start = text.index('pub(super) enum ' + name)
            end = text.index('\n}', start) + 2
            enums.append('#[derive(Clone,Copy,Debug,PartialEq,Eq)]\n' + text[start:end].replace('pub(super) ', ''))
        methods = '\n'.join(selection.extract(text, name) for name in ('acquire', 'expire_authorizations', 'target_available', 'authorize', 'cancel_authorizations'))
        audit_text = originals[audit] if label == 'before' else (source / audit).read_text()
        unit = fixture.replace('// @ENUMS@', '\n'.join(enums)).replace('// @METHODS@', methods).replace('// @AUDIT_METHOD@', selection.extract(audit_text, 'record_target_blocked'))
        helpers = '' if label == 'before' else '\n'.join(selection.extract(text, name) for name in ('next_authorization_trace_sequence', 'trace_render_authorization'))
        unit = unit.replace('// @TRACE_HELPERS@', helpers)
        rust = output / (label + '.rs')
        rust.write_text(unit)
        binary = output / label
        cmd = [rustc, '--edition=2024', '--test', str(rust), '-o', str(binary)]
        if label == 'after':
            cmd += ['--cfg', 'authorization_trace']
        start = time.monotonic()
        subprocess.run(cmd, env=dict(os.environ, TMPDIR=str(output)), check=True, capture_output=True, timeout=30)
        run = subprocess.run([str(binary)], capture_output=True, text=True, timeout=10)
        (output / (label + '.log')).write_text(run.stdout + run.stderr)
        expected = '4 passed; 4 failed' if label == 'before' else '9 passed; 0 failed'
        result['runs'][label] = {'command': cmd, 'test_command': [str(binary)], 'exit_status': run.returncode, 'duration_seconds': time.monotonic()-start, 'expected_result_observed': expected in run.stdout and run.returncode == (101 if label == 'before' else 0), 'source_sha256': hashlib.sha256(unit.encode()).hexdigest()}
    result['status'] = 'PASS' if all(r['expected_result_observed'] for r in result['runs'].values()) else 'FAIL'
    (output / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))
    return 0 if result['status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
