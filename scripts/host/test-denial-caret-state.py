#!/usr/bin/env python3
"""Execute retained Denial's actual generic caret commit/focus state machine.

No Wayland, GPU, VM or phone qualification is provided. --prepare-only emits
an exact-source unit for the coordinator's pinned Rust build environment.
"""
import argparse
import hashlib
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
    parser.add_argument('--prepare-only', action='store_true')
    args = parser.parse_args()
    src = args.source / 'compositor/src/bin/deniald/wayland_frontend/text_input.rs'
    text = src.read_text()
    begin = text.index('#[derive(Clone, Copy, Debug, Default, Eq, PartialEq)]\nstruct CursorRectangle')
    end = text.index('#[derive(Clone, Copy, Debug, Default, Eq, PartialEq)]\npub(super) enum SeatFocusKind')
    state_begin = text.index('/// Focused Wayland caret in owning window content logical coordinates.')
    state_end = text.index('#[derive(Debug)]\npub(super) struct TextInputManager', state_begin)
    fixture = Path(__file__).resolve().parents[2] / 'tools/denial-modifier-tests/caret-state-tests.rs'
    unit = ('#![allow(dead_code)]\nuse std::{mem,time::{Duration,Instant}};\n'
            'const TOUCH_AUTHORIZATION_WINDOW: Duration = Duration::from_millis(250);\n'
            + text[begin:end] + '\n' + text[state_begin:state_end] + fixture.read_text())
    args.output.mkdir(parents=True, exist_ok=False)
    unit_path = args.output / 'caret-tests.rs'
    unit_path.write_text(unit)
    result = {'source_sha256': hashlib.sha256(src.read_bytes()).hexdigest(),
              'fixture_sha256': hashlib.sha256(fixture.read_bytes()).hexdigest(),
              'unit_sha256': hashlib.sha256(unit.encode()).hexdigest(),
              'status': 'NOT_RUN', 'physical': 'NOT_RUN', 'runs': []}
    if not args.prepare_only:
        rustc = shutil.which(os.environ.get('RUSTC', 'rustc'))
        if not rustc:
            result['status'] = 'BLOCKED'
            result['error'] = 'Rust compiler missing'
        else:
            binary = args.output / 'caret-tests'
            for command in ([rustc, '--edition=2024', '--test', str(unit_path), '-o', str(binary)],
                            [str(binary), '--test-threads=1']):
                start = time.monotonic()
                proc = subprocess.run(command, capture_output=True, text=True, timeout=45,
                                      env=dict(os.environ, TMPDIR=str(args.output)))
                log = args.output / f'run-{len(result["runs"])}.log'
                log.write_text(proc.stdout + proc.stderr)
                result['runs'].append({'command': command, 'exit_code': proc.returncode,
                                       'duration_seconds': time.monotonic() - start})
                if proc.returncode:
                    result['status'] = 'FAIL'
                    break
            else:
                result['status'] = 'PASS'
    (args.output / 'result.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result))
    return 0 if args.prepare_only or result['status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
