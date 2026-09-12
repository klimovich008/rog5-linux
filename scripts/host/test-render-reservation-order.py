#!/usr/bin/env python3
"""Reproduce unresolved stale-work properties in the actual Denial broker.

Exit 1 and status FAIL are intentional while the desired properties fail.
counterexamples_observed reports reproduction separately; it is not a fix PASS.
No engine, VM, device or framebuffer operation is executed.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import resource
import shutil
import subprocess


def no_core():
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    repo = Path(__file__).resolve().parents[2]
    spec = importlib.util.spec_from_file_location(
        'selection', repo / 'scripts/host/test-denial-modifier-selection.py')
    selection = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(selection)
    report_spec = importlib.util.spec_from_file_location(
        'report', repo / 'scripts/host/repository-test-report.py')
    report = importlib.util.module_from_spec(report_spec)
    report_spec.loader.exec_module(report)
    no_core()
    rustc = os.environ.get('RUSTC', 'rustc')
    if not shutil.which(rustc):
        parser.error('BLOCKED: selected Rust compiler unavailable')
    output = args.output.absolute()
    output.mkdir(parents=True, exist_ok=False)
    stage = output / 'source'
    prefix = 'compositor/src/bin/deniald/flutter_runtime/'
    for name in ('output_pipeline.rs', 'output_runtime.rs', 'render_audit.rs'):
        path = prefix + name
        target = stage / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(subprocess.check_output(
            ['git', '-C', str(args.source), 'show', selection.BASE + ':' + path], timeout=10))
    patches = {}
    for name in ('0002-distinguish-render-target-refusals.patch',
                 '0003-trace-render-authorization-history.patch'):
        patch = repo / 'patches/denial-85b2303e' / name
        patches[name] = hashlib.sha256(patch.read_bytes()).hexdigest()
        for flags in (['--check'], []):
            subprocess.run(['git', 'apply', *flags, str(patch)], cwd=stage,
                           check=True, timeout=10)
    source = (stage / prefix / 'output_pipeline.rs').read_text()
    sections = {name: selection.extract(source, name) for name in (
        'acquire', 'expire_authorizations', 'target_available',
        'authorize', 'cancel_authorizations')}
    enums = []
    for name in ('BufferState', 'RenderTargetBlocked'):
        start = source.index('pub(super) enum ' + name)
        end = source.index('\n}', start) + 2
        enums.append('#[derive(Clone,Copy,Debug,PartialEq,Eq)]\n' +
                     source[start:end].replace('pub(super) ', ''))
    audit = (stage / prefix / 'render_audit.rs').read_text()
    fixture = (repo / 'tools/denial-modifier-tests/broker-fixture.rs').read_text()
    tests = (repo / 'tools/denial-modifier-tests/reservation-order.rs').read_text()
    unit = fixture.replace('// @ENUMS@', '\n'.join(enums)).replace(
        '// @METHODS@', '\n'.join(sections.values())).replace(
        '// @AUDIT_METHOD@', selection.extract(audit, 'record_target_blocked')).replace(
        '// @TRACE_HELPERS@', '\n'.join(selection.extract(source, name) for name in (
            'next_authorization_trace_sequence', 'trace_render_authorization'))) + tests
    path = output / 'reservation-order.rs'
    path.write_text(unit)
    binary = output / 'reservation-order'
    command = ['env', 'TMPDIR=' + str(output), rustc, '--edition=2024',
               '--test', str(path), '-o', str(binary)]
    with (output / 'build.log').open('w') as log:
        build_status, build_reason, build_seconds = report.execute(command, 30, log, log)
    result = {'source_commit': selection.BASE, 'repository_commit': subprocess.check_output(
        ['git', '-C', str(repo), 'rev-parse', 'HEAD'], text=True, timeout=10).strip(),
        'patches': patches, 'section_sha256': {name: hashlib.sha256(text.encode()).hexdigest()
                                             for name, text in sections.items()},
        'unit_sha256': hashlib.sha256(unit.encode()).hexdigest(),
        'build': {'command': command, 'status': build_status, 'reason': build_reason,
                  'duration_seconds': build_seconds},
        'scope': 'actual broker methods; deterministic call ordering with data adapters',
        'vm': 'NOT RUN', 'phone': 'NOT RUN', 'runs': []}
    if build_status != 'PASS':
        result['status'] = 'FAIL'
        result['counterexamples_observed'] = False
    else:
        cases = {
            'delayed_acquire_must_not_consume_a_replacement_reservation': 101,
            'delayed_cancel_must_not_remove_a_replacement_reservation': 101,
            'expired_acquire_without_replacement_is_refused': 0,
            'current_acquire_consumes_exactly_once': 0,
        }
        for name, expected in cases.items():
            cmd = [str(binary), '--exact', 'reservation_order::' + name, '--nocapture']
            log_path = output / (name + '.log')
            with log_path.open('w') as log:
                status, reason, seconds = report.execute(cmd, 10, log, log)
            ran = 'running 1 test' in log_path.read_text()
            result['runs'].append({'name': name, 'command': cmd, 'reason': reason,
                                  'status': status if ran else 'FAIL',
                                  'expected_exit_status': expected,
                                  'observed_expected': ran and reason == 'exit ' + str(expected),
                                  'duration_seconds': seconds})
        result['counterexamples_observed'] = all(r['observed_expected'] for r in result['runs'])
        result['status'] = 'PASS' if all(r['status'] == 'PASS' for r in result['runs']) else 'FAIL'
    (output / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))
    return 0 if result['status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
