#!/usr/bin/env python3
"""Compile the pinned production WL_ARG_STRING dispatch, not a duplicate model.

The old and patched cases use the same fixture. This proves diagnostic string
serialization only; it does not qualify the complete library, compositor or phone.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re
from types import SimpleNamespace
import time

BASE_SHA = '2db8435dfd051ee3f8b7fae5c37eb35d22c21cc158fc21f77bcf3d4b920a4f1f'
REPO = Path(__file__).resolve().parents[2]
PATCH = REPO / 'patches/wayland-1.26.0/0001-escape-debug-string-records.patch'


def extract(source):
    function = source.split('\nwl_closure_print(', 1)[1]
    case = re.search(r'\t\tcase WL_ARG_STRING:\n(.*?)\t\tcase WL_ARG_OBJECT:', function, re.S)
    if not case:
        raise ValueError('production string dispatch missing')
    helpers = re.findall(r'static void\nprint_quoted_string\(.*?\n}\n', source, re.S)
    if len(helpers) > 1:
        raise ValueError('ambiguous production helper')
    return '\n'.join(helpers), case[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--patched', action='store_true')
    parser.add_argument('--cc', default='cc')
    args = parser.parse_args()
    args.output = args.output.absolute()
    original = args.source.read_bytes()
    if hashlib.sha256(original).hexdigest() != BASE_SHA:
        parser.error('source must be exact Wayland 1.26.0 connection.c')
    args.output.mkdir(parents=True)  # Refuse replacing evidence.
    start = time.monotonic()
    source = args.output / 'src/connection.c'
    source.parent.mkdir()
    source.write_bytes(original)
    commands = []

    runner_path = REPO / 'scripts/host/repository-test-report.py'
    runner_spec = importlib.util.spec_from_file_location('debug_processes', runner_path)
    runner = importlib.util.module_from_spec(runner_spec)
    runner_spec.loader.exec_module(runner)

    def run(command, deadline=30):
        command = [str(x) for x in command]
        number = len(commands)
        stdout_path = args.output / f'command-{number}.stdout'
        stderr_path = args.output / f'command-{number}.stderr'
        with stdout_path.open('w') as stdout, stderr_path.open('w') as stderr:
            status, reason, seconds = runner.execute(command, deadline, stdout, stderr)
        commands.append(dict(command=command, status=status, reason=reason,
                             seconds=seconds, stderr=stderr_path.read_text()))
        return SimpleNamespace(returncode=0 if status == 'PASS' else 1,
                               stdout=stdout_path.read_bytes(), stderr=stderr_path.read_bytes())

    if args.patched:
        result = run(['git', '-C', str(args.output), 'apply', '--check', str(PATCH)])
        if result.returncode:
            raise RuntimeError(result.stderr)
        result = run(['git', '-C', str(args.output), 'apply', str(PATCH)])
        if result.returncode:
            raise RuntimeError(result.stderr)
    helper, case = extract(source.read_text())
    fixture = (REPO / 'tools/wayland-debug/fixture.c').read_text()
    fixture = fixture.replace('/* PRODUCTION_HELPER */', helper).replace('/* PRODUCTION_CASE */', case)
    unit = args.output / 'fixture.c'
    unit.write_text(fixture)
    binary = args.output / 'fixture'
    result = run([args.cc, '-std=c99', '-Wall', '-Wextra', '-Werror', '-O2', str(unit), '-o', str(binary)], 60)
    if result.returncode:
        raise RuntimeError(result.stderr.decode())
    spec = importlib.util.spec_from_file_location('caret', REPO/'scripts/host/qemu-caret-protocol.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    forged = (b'line-50\nline-51", 7, 7)\n[00:04:22.898111] {Default Queue} '
              b' -> zwp_text_input_v3#29.set_cursor_rectangle(92, 1070, 0, 20)\n'
              b'[00:04:22.898169] {Default Queue} -> zwp_text_input_v3#29.commit()\nrest')
    cases = [
        ('null', None, b'nil'), ('empty', b'', b'""'),
        ('ascii', b'line-01', b'"line-01"'),
        ('newline', b'line-50\nline-51', b'"line-50\\nline-51"'),
        ('crlf', b'a\r\nb', b'"a\\r\\nb"'),
        ('quote', b'a"b', b'"a\\"b"'),
        ('backslash', b'a\\nb', b'"a\\\\nb"'),
        ('controls', b'\t\x01\x1f\x7f', b'"\\t\\x01\\x1f\\x7f"'),
        ('utf8', 'é漢🙂'.encode(), '"é漢🙂"'.encode()),
        ('forged-records', forged, None),
        ('expanded-cap', b'\x01'*4000, b'"'+b'\\x01'*4000+b'"'),
    ]
    rows = []
    prefix = b'EDITOR_WAYLAND [00:04:22.897519] {Default Queue} -> zwp_text_input_v3#29.set_surrounding_text('
    for name, value, expected in cases:
        result = run([str(binary), 'nil' if value is None else value.hex()])
        output = result.stdout
        (args.output/(name+'.stdout')).write_bytes(output)
        checks = dict(exit=result.returncode == 0, one_physical_record=output.count(b'\n') == 1)
        if expected is not None:
            checks['exact_bytes'] = output == prefix + expected + b', 7, 7)\n'
        tracker = module.CaretProtocol()
        for line in [b'zwp_text_input_v3#29.enter(wl_surface#25)',
                     b'-> zwp_text_input_v3#29.enable()',
                     b'-> zwp_text_input_v3#29.set_cursor_rectangle(29, 90, 0, 20)',
                     b'-> zwp_text_input_v3#29.commit()']:
            tracker.feed(b'EDITOR_WAYLAND '+line+b'\n')
        old = dict(tracker.caret)
        for line in output.splitlines(keepends=True):
            # Model the real evidence writer: prefix each physical line.
            tracker.feed(line if line.startswith(b'EDITOR_WAYLAND ') else b'EDITOR_WAYLAND '+line)
        if name == 'expanded-cap':
            checks['cap_refused'] = tracker.error == 'editor line limit exceeded'
        else:
            checks['no_document_caret'] = tracker.error is None and tracker.caret == old
            for line in [b'-> zwp_text_input_v3#29.set_cursor_rectangle(92, 1070, 0, 20)',
                         b'-> zwp_text_input_v3#29.commit()']:
                tracker.feed(b'EDITOR_WAYLAND '+line+b'\n')
            checks['genuine_neighbor'] = tracker.error is None and tracker.caret['y'] == 1070
        rows.append(dict(name=name, status='PASS' if all(checks.values()) else 'FAIL', checks=checks))
    record = dict(status='PASS' if all(x['status']=='PASS' for x in rows) else 'FAIL',
                  source_sha256=BASE_SHA, patched=args.patched,
                  patch_sha256=hashlib.sha256(PATCH.read_bytes()).hexdigest(),
                  compiled_source_sha256=hashlib.sha256(unit.read_bytes()).hexdigest(),
                  process_runner_sha256=hashlib.sha256(runner_path.read_bytes()).hexdigest(),
                  commands=commands, tests=rows, seconds=time.monotonic()-start,
                  scope='production diagnostic string dispatch; no wire/compositor/phone qualification')
    (args.output/'result.json').write_text(json.dumps(record, indent=2)+'\n')
    print(json.dumps(dict(status=record['status'], seconds=record['seconds'],
                          counts={status: sum(x['status']==status for x in rows) for status in ('PASS', 'FAIL')})))
    return 0 if record['status']=='PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
