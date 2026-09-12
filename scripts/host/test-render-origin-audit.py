#!/usr/bin/env python3
"""Test the real bounded raster-origin logger; engine build/VM are separate."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

BASE = 'd728e61e7d835e02c453c70ae9523a40f6c03215'
FILE = 'engine/src/flutter/shell/common/rasterizer.cc'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    repo = Path(__file__).resolve().parents[2]
    output = args.output.absolute()
    output.mkdir(parents=True, exist_ok=False)
    file = output / 'source' / FILE
    file.parent.mkdir(parents=True)
    original = subprocess.check_output(['git', '-C', str(args.source), 'show', BASE + ':' + FILE], timeout=10)
    file.write_bytes(original)
    patch = repo / 'patches/flutter-engine-d728e61e/0003-trace-raster-call-origin.patch'
    # This diagnostic is additive: existing admission/scheduling code is retained.
    assert not any(line.startswith('-') and not line.startswith('---') for line in patch.read_text().splitlines())
    for flags in (['--check'], []):
        subprocess.run(['git', 'apply', *flags, str(patch)], cwd=output / 'source', check=True, timeout=10)
    text = file.read_text()
    start = text.index('namespace denial_render_audit {')
    end = text.index('}  // namespace denial_render_audit', start) + len('}  // namespace denial_render_audit')
    fixture = (repo / 'tools/denial-engine-tests/render-origin.cc').read_text()
    unit = output / 'fixture.cc'
    unit.write_text(fixture.replace('// @HELPER@', text[start:end]))
    binary = output / 'fixture'
    cmd = [os.environ.get('CXX', 'c++'), '-std=c++17', '-Wall', '-Wextra', '-Werror', '-pthread', str(unit), '-o', str(binary)]
    started = time.monotonic()
    subprocess.run(cmd, check=True, capture_output=True, timeout=30)
    result = {'base': BASE, 'patch_sha256': hashlib.sha256(patch.read_bytes()).hexdigest(),
              'build_command': cmd, 'build_seconds': time.monotonic() - started, 'runs': []}
    for mode in ('disabled', 'nested', 'concurrent-cap'):
        command = [str(binary), mode]
        started = time.monotonic()
        run = subprocess.run(command, capture_output=True, text=True, timeout=10)
        (output / (mode + '.log')).write_text(run.stdout + run.stderr)
        result['runs'].append({'command': command, 'exit_status': run.returncode,
                              'duration_seconds': time.monotonic() - started})
    result['status'] = 'PASS' if all(r['exit_status'] == 0 for r in result['runs']) else 'FAIL'
    (output / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))
    return result['status'] != 'PASS'


if __name__ == '__main__':
    raise SystemExit(main())
