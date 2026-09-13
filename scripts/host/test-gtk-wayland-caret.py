#!/usr/bin/env python3
"""Execute exact GTK cursor publication functions with bounded host adapters."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import resource
import subprocess
import time

BASE_SHA = '7f5bf63f9ad71da36d625d0870692f49bc6351a71757c0f8ac1fcec38c613c37'
BASE_COMMIT = '6a0b360d473f7c546314738c0c8dd9829eb9d3c2'
FUNCTIONS = ('notify_im_change', 'text_input_done', 'notify_surrounding_text',
             'notify_cursor_location', 'commit_state', 'enable',
             'gtk_im_context_wayland_reset', 'gtk_im_context_wayland_set_cursor_location',
             'gtk_im_context_wayland_set_surrounding')
CASES = ('reset-then-low', 'unchanged', 'small-move', 'pending-done', 'reentry',
         'retrieve-focus-out', 'retrieve-disabled', 'disabled-enable', 'no-global', 'no-proxy', 'no-current', 'wrong-current',
         'unfocused', 'no-window', 'disabled')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True, help='Unmodified pinned imwayland.c')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--unpatched', action='store_true', help='Negative control; failing cases remain FAIL')
    args = parser.parse_args()
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    repo = Path(__file__).resolve().parents[2]
    out = args.output.absolute()
    out.mkdir(parents=True, exist_ok=False)
    started = time.monotonic()
    result = dict(status='FAIL', base_commit=BASE_COMMIT, unpatched=args.unpatched,
                  scope='Host C source-function regression; GTK widget signals/window/protocol are adapters, short ASCII only; no real GTK/Wayland/phone execution',
                  sections={}, runs=[])
    try:
        source = args.source.read_bytes()
        if sha(source) != BASE_SHA:
            raise ValueError('source does not match pinned GTK imwayland.c')
        result['source_sha256'] = sha(source)
        target = out / 'modules/input/imwayland.c'
        target.parent.mkdir(parents=True)
        target.write_bytes(source)
        if not args.unpatched:
            patch = repo / 'patches/gtk-3.24.52/0001-publish-changed-wayland-caret.patch'
            result['patch_sha256'] = sha(patch.read_bytes())
            subprocess.run(['git', 'apply', '--check', str(patch)], cwd=out, check=True, timeout=10)
            subprocess.run(['git', 'apply', str(patch)], cwd=out, check=True, timeout=10)
        source = target.read_text()
        result['patched_source_sha256'] = sha(source.encode())
        sections = []
        for name in FUNCTIONS:
            matches = re.findall(r'^static void\n' + re.escape(name) + r' \([^;]*?\)\n\{.*?^\}', source, re.M | re.S)
            if len(matches) != 1:
                raise ValueError('expected exactly one complete function: ' + name)
            section = matches[0] + '\n'
            result['sections'][name] = sha(section.encode())
            sections.append(section)
        fixture = repo / 'tools/gtk-caret/fixture.c'
        result['fixture_sha256'] = sha(fixture.read_bytes())
        (out / 'fixture.c').write_text(fixture.read_text().replace('/* INSERT_PRODUCTION */', '\n'.join(sections)))
        command = [os.environ.get('CC', 'cc'), '-std=c11', '-O2', '-Wall', '-Wextra', '-Werror',
                   '-Wno-misleading-indentation', '-Wno-sign-compare', '-Wno-unused-parameter',
                   str(out / 'fixture.c'), '-o', str(out / 'fixture')]
        run = subprocess.run(command, capture_output=True, text=True, timeout=30)
        result['compile'] = dict(command=command, exit=run.returncode, stdout=run.stdout, stderr=run.stderr)
        if run.returncode:
            raise RuntimeError('fixture compilation failed')
        for case in CASES:
            t = time.monotonic()
            run = subprocess.run([str(out / 'fixture'), case], capture_output=True, text=True, timeout=3)
            result['runs'].append(dict(case=case, status='PASS' if run.returncode == 0 else 'FAIL',
                                      exit=run.returncode, stdout=run.stdout, stderr=run.stderr,
                                      seconds=time.monotonic() - t))
        result['status'] = 'PASS' if all(r['status'] == 'PASS' for r in result['runs']) else 'FAIL'
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
        result['error'] = str(error)
    result['seconds'] = time.monotonic() - started
    result['counts'] = {s: sum(r['status'] == s for r in result['runs']) for s in ('PASS', 'FAIL')}
    (out / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: result[k] for k in ('status', 'counts', 'seconds')}))
    return 0 if result['status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
