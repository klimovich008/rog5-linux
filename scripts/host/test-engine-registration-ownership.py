#!/usr/bin/env python3
"""Test the actual engine-startup ownership tail before/after callback registration.

The real startup tail and Drop/shutdown methods are extracted verbatim; the
engine calls, configuration data and publication boundary use tracked adapters.
No Flutter library is loaded and no real engine thread or device is started.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import resource
import subprocess

HOST = 'compositor/flutter-engine/src/host.rs'
LIB = 'compositor/flutter-engine/src/lib.rs'
PATCH = 'patches/denial-85b2303e/0007-own-startup-callback-graph-before-registration.patch'


def module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-before', type=Path, required=True)
    parser.add_argument('--source-after', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    repo = Path(__file__).resolve().parents[2]
    selection = module(repo / 'scripts/host/test-denial-modifier-selection.py', 'selection')

    def extract(source, name):
        match = re.search(r'\bfn ' + re.escape(name) + r'(?=[<(])', source)
        if match is None:
            raise ValueError('exact function absent: ' + name)
        return selection.extract(source[match.start():], name)
    report = module(repo / 'scripts/host/repository-test-report.py', 'report')
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    output = args.output.absolute(); output.mkdir(parents=True, exist_ok=False)
    patch = repo / PATCH
    before_host = (args.source_before / HOST).read_text()
    after_host = (args.source_after / HOST).read_text()
    before_lib = (args.source_before / LIB).read_text()
    after_lib = (args.source_after / LIB).read_text()
    if before_lib != after_lib:
        raise RuntimeError('unrelated library drift between before and after')
    stage = output / 'patch-check'
    target = stage / HOST; target.parent.mkdir(parents=True); target.write_text(before_host)
    subprocess.run(['git', '-C', str(stage), 'apply', '--check', str(patch)], check=True, timeout=10)
    subprocess.run(['git', '-C', str(stage), 'apply', str(patch)], check=True, timeout=10)
    if target.read_text() != after_host:
        raise RuntimeError('after source is not exactly the applied registration patch')
    fixture = (repo / 'tools/denial-modifier-tests/registration-ownership.rs').read_text()
    cases = re.findall(r'#\[test\]\s*fn (\w+)\(', fixture)
    result = {'scope': 'actual startup ownership tail and shutdown/Drop methods; tracked engine/config adapters',
              'repository_commit': subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD'], text=True, timeout=10).strip(),
              'patch_sha256': sha(patch.read_bytes()), 'fixture_sha256': sha(fixture.encode()),
              'engine_runtime': 'NOT RUN', 'vm': 'NOT RUN', 'phone': 'NOT RUN', 'runs': {}}
    for label, host in [('before', before_host), ('after', after_host)]:
        startup = extract(host, 'start_with_library_and_priority_setter')
        tail = startup[startup.index('        let engine = unsafe { library.run'):]
        sections = {
            '// @STARTUP_TAIL@': tail,
            '// @ENGINE_ACCESSOR@': extract(host, 'engine'),
            '// @HOST_SHUTDOWN@': extract(host, 'shutdown_state'),
            '// @HOST_DROP@': extract(host[host.index('impl Drop for EngineHost'):], 'drop'),
            '// @RELEASE_OR_LEAK@': extract(host, 'release_or_leak'),
            '// @ENGINE_SHUTDOWN@': extract(before_lib, 'shutdown_in_place'),
            '// @ENGINE_DROP@': extract(before_lib[before_lib.index('impl Drop for RunningEngine'):], 'drop'),
        }
        unit = fixture
        for marker, section in sections.items():
            if unit.count(marker) != 1:
                raise RuntimeError('fixture marker absent or duplicated')
            unit = unit.replace(marker, section)
        source = output / (label + '.rs'); source.write_text(unit)
        binary = output / label
        command = ['env', 'TMPDIR='+str(output), os.environ.get('RUSTC','rustc'), '--edition=2024', '--test', str(source), '-o', str(binary)]
        with (output / (label+'-build.log')).open('w') as log:
            status, reason, seconds = report.execute(command,30,log,log)
        run = {'host_sha256':sha(host.encode()), 'lib_sha256':sha(before_lib.encode()),
               'section_sha256':{name:sha(text.encode()) for name,text in sections.items()},
               'unit_sha256':sha(unit.encode()), 'build':{'command':command,'status':status,'reason':reason,'duration_seconds':seconds}, 'cases':[]}
        if status == 'PASS':
            for name in cases:
                command = [str(binary), '--exact', name, '--nocapture']
                log_path = output / (label+'-'+name+'.log')
                with log_path.open('w') as log:
                    status, reason, seconds = report.execute(command,10,log,log)
                expected = 101 if label == 'before' and name in (
                    'first_registration_failure_with_failed_shutdown_retains_graph',
                    'second_registration_failure_with_failed_shutdown_retains_graph') else 0
                executed = 'running 1 test' in log_path.read_text()
                run['cases'].append({'name':name,'command':command,'status':status if executed else 'FAIL',
                                     'reason':reason,'duration_seconds':seconds,'expected_exit':expected,
                                     'expected_observed':executed and reason=='exit '+str(expected)})
        run['counts'] = {s:sum(case['status']==s for case in run['cases']) for s in ('PASS','FAIL','BLOCKED','SKIPPED')}
        run['status'] = 'PASS' if run['build']['status']=='PASS' and len(run['cases'])==len(cases) and all(case['status']=='PASS' for case in run['cases']) else 'FAIL'
        run['expected_observed'] = run['build']['status']=='PASS' and len(run['cases'])==len(cases) and all(case['expected_observed'] for case in run['cases'])
        result['runs'][label] = run
    result['status'] = 'PASS' if all(run['expected_observed'] for run in result['runs'].values()) else 'FAIL'
    (output/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
    return 0 if result['status']=='PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
