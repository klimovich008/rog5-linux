#!/usr/bin/env python3
"""Exercise actual work-reservation broker, handler and FFI methods offline.

--source is an unpacked Denial tree with the paired local patches applied.
The reservation patch must reverse-apply cleanly. Full source/section hashes
record exactly what ran; this does not assert an immutable artifact identity.
No engine scheduling, GL/GBM, VM or phone operation is executed.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import resource
import shutil
import subprocess

PREFIX = 'compositor/src/bin/deniald/flutter_runtime/'
INPUTS = {
    'broker': PREFIX + 'output_pipeline.rs',
    'handler': PREFIX + 'renderer/handler/open_gl.rs',
    'cancel': PREFIX + 'renderer/handler.rs',
    'ffi': 'compositor/flutter-engine/src/host.rs',
}
PATCH = 'patches/denial-85b2303e/0006-bind-render-work-reservations.patch'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    repo = Path(__file__).resolve().parents[2]
    selection = module(repo / 'scripts/host/test-denial-modifier-selection.py', 'selection')
    report = module(repo / 'scripts/host/repository-test-report.py', 'report')
    output = args.output.absolute()
    output.mkdir(parents=True, exist_ok=False)
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    result = {
        'scope': 'actual extracted production methods with data, audit and callback-lifetime adapters',
        'repository_commit': subprocess.check_output(
            ['git', '-C', str(repo), 'rev-parse', 'HEAD'], text=True, timeout=10).strip(),
        'upstream_denial_commit': selection.BASE,
        'source_path': str(args.source.absolute()), 'vm': 'NOT RUN', 'phone': 'NOT RUN',
        'engine_scheduling': 'NOT RUN', 'gl_allocation': 'NOT RUN', 'runs': [],
    }
    try:
        patch = repo / PATCH
        result['patch_sha256'] = sha(patch.read_bytes())
        command = ['git', 'apply', '--reverse', '--check', str(patch)]
        with (output / 'identity.log').open('w') as log:
            # git -C avoids changing the runner's own working directory.
            command[1:1] = ['-C', str(args.source.absolute())]
            status, reason, seconds = report.execute(command, 10, log, log)
        result['patch_identity'] = {'command': command, 'status': status,
                                    'reason': reason, 'duration_seconds': seconds}
        if status != 'PASS':
            raise RuntimeError('reservation patch does not reverse-apply to supplied source')
        source = {key: (args.source / path).read_text() for key, path in INPUTS.items()}
        result['source_sha256'] = {INPUTS[key]: sha(text.encode()) for key, text in source.items()}
        sections = {}

        def extract(key, name, ffi=False):
            text_source = source[key]
            if ffi:
                text_source = text_source[text_source.index('unsafe extern "C" fn ' + name):]
            text = selection.extract(text_source, name)
            if ffi:
                # Preserve the production unsafe extern ABI prefix rather than
                # testing an ordinary Rust substitute for an FFI trampoline.
                start = text_source.index('fn ' + name)
                prefix = text_source[text_source.rfind('\n', 0, start) + 1:start]
                text = prefix + text
            sections[key + ':' + name] = text
            return text

        declarations = []
        for kind, name in [('enum', 'BufferState'), ('enum', 'RenderTargetBlocked'),
                           ('struct', 'AuthorizedOutputRequest')]:
            start = source['broker'].index('pub(super) ' + kind + ' ' + name)
            end = source['broker'].index('\n}', start) + 2
            raw = source['broker'][start:end]
            sections['broker:declaration:' + name] = raw
            declarations.append('#[derive(Clone,Copy,Debug,PartialEq,Eq)]\n' + raw.replace('pub(super) ', '')
                                if kind == 'enum' else '#[derive(Clone,Copy,Debug)]\n' + raw.replace('pub(super) ', ''))
        fixture = (repo / 'tools/denial-modifier-tests/render-work-broker.rs').read_text()
        replacements = {
            '// @DECLARATIONS@': '\n'.join(declarations),
            '// @BROKER_METHODS@': '\n'.join(extract('broker', name) for name in (
                'target_available', 'next_work_id', 'authorize', 'cancel_work',
                'end_admission', 'admit', 'expire_authorizations', 'acquire')),
            '// @TRACE_HELPERS@': '\n'.join(extract('broker', name) for name in (
                'next_authorization_trace_sequence', 'trace_render_authorization')),
            '// @HANDLER_METHODS@': '\n'.join(extract('handler', name) for name in (
                'begin_render_work', 'end_render_work', 'render_work_done', 'create_backing_store')),
            '// @CANCEL_METHOD@': extract('cancel', 'cancel_output_work'),
            '// @FFI_METHODS@': '\n'.join(extract('ffi', name, ffi=name in (
                'begin_render_work', 'end_render_work', 'render_work_done')) for name in (
                    'dispatch', 'catch_ffi_unwind', 'begin_render_work', 'end_render_work', 'render_work_done')),
        }
        unit = fixture
        for marker, text in replacements.items():
            if unit.count(marker) != 1:
                raise RuntimeError('fixture marker absent or repeated: ' + marker)
            unit = unit.replace(marker, text)
        result['section_sha256'] = {name: sha(text.encode()) for name, text in sections.items()}
        result['fixture_sha256'] = sha(fixture.encode())
        result['unit_sha256'] = sha(unit.encode())
        path = output / 'render-work-broker.rs'
        path.write_text(unit)
        binary = output / 'render-work-broker'
        rustc = os.environ.get('RUSTC', 'rustc')
        if not shutil.which(rustc):
            raise FileNotFoundError('selected Rust compiler unavailable')
        command = ['env', 'TMPDIR=' + str(output), rustc, '--edition=2024', '--test', str(path), '-o', str(binary)]
        with (output / 'build.log').open('w') as log:
            status, reason, seconds = report.execute(command, 30, log, log)
        result['build'] = {'command': command, 'status': status, 'reason': reason, 'duration_seconds': seconds}
        if status != 'PASS':
            raise RuntimeError('Rust fixture build failed')
        cases = re.findall(r'#\[test\]\s*fn (\w+)\(', fixture)
        if not cases or len(cases) != len(set(cases)):
            raise RuntimeError('test inventory empty or duplicated')
        for name in cases:
            command = [str(binary), '--exact', name, '--nocapture']
            log_path = output / (name + '.log')
            with log_path.open('w') as log:
                status, reason, seconds = report.execute(command, 10, log, log)
            if 'running 1 test' not in log_path.read_text():
                status, reason = 'FAIL', 'expected exact test was not executed: ' + reason
            result['runs'].append({'name': name, 'command': command, 'status': status,
                                   'reason': reason, 'duration_seconds': seconds})
        result['status'] = 'PASS' if all(run['status'] == 'PASS' for run in result['runs']) else 'FAIL'
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
        result['status'] = 'BLOCKED' if isinstance(error, FileNotFoundError) else 'FAIL'
        result['error'] = str(error)
    result['counts'] = {status: sum(run['status'] == status for run in result['runs'])
                        for status in ('PASS', 'FAIL', 'BLOCKED', 'SKIPPED')}
    (output / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))
    return 0 if result['status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
