#!/usr/bin/env python3
"""Per-test deadlines/results; the existing shell selector and cleanup stay intact."""
import argparse
import ast
import collections
import hashlib
import json
import os
from pathlib import Path
import shutil
import re
import signal
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

STATUSES = ('PASS', 'FAIL', 'BLOCKED', 'SKIPPED', 'NOT_SELECTED')


def atomic(path, value):
    temporary = path.with_name(path.name + '.' + str(os.getpid()) + '.tmp')
    temporary.write_text(value)
    os.replace(temporary, path)


def entries(repo):
    rows = json.loads((repo / 'configs/repository-tests.json').read_text())['tests']
    required = {'path', 'interpreter', 'tiers', 'mandatory', 'deadline_seconds',
                'prerequisites', 'resource_class', 'exclusivity_group',
                'python_optimized', 'exact_source', 'required_inputs'}
    paths = set()
    for row in rows:
        if not required <= set(row) or set(row) - required - {'optional_subchecks'} or row['path'] in paths:
            raise ValueError('invalid or duplicate manifest entry')
        if row['deadline_seconds'] <= 0 or row['deadline_seconds'] > 3600:
            raise ValueError('invalid deadline')
        if row['resource_class'] != 'isolated' and row['exclusivity_group'] != 'repository':
            raise ValueError('resource-sensitive tests must serialize')
        ids = set()
        for item in row.get('optional_subchecks', []):
            if set(item) != {'id', 'kind', 'message', 'scope', 'reason', 'inputs', 'test_ids'}:
                raise ValueError('invalid optional-subcheck declaration')
            if item['id'] in ids or not item['reason'] or not item['inputs'] or not item['message']:
                raise ValueError('optional subcheck needs unique identity, reason and inputs')
            if item['kind'] not in ('line', 'unittest') or item['scope'] not in ('subcheck', 'whole_test'):
                raise ValueError('invalid optional-subcheck matcher or scope')
            if item['kind'] == 'unittest' and not item['test_ids']:
                raise ValueError('unittest skips require exact test identities')
            if item['scope'] == 'whole_test' and row['mandatory']:
                raise ValueError('whole optional suite cannot be mandatory')
            ids.add(item['id'])
        paths.add(row['path'])
    return rows


def members(group):
    # The direct child remains unreaped until cleanup, reserving its PID/PGID.
    result = []
    for entry in Path('/proc').iterdir():
        if not entry.name.isdigit():
            continue
        try:
            fields = (entry / 'stat').read_text().rsplit(')', 1)[1].split()
            if int(fields[2]) == group and int(entry.name) != group and fields[0] != 'Z':
                result.append(int(entry.name))
        except (OSError, ValueError, IndexError):
            pass
    return result


def execute(command, deadline, stdout, stderr):
    started = time.monotonic()
    child = subprocess.Popen(command, start_new_session=True, stdout=stdout, stderr=stderr)
    status, reason = 'FAIL', 'interrupted'
    old_handlers = {}
    cleaning = False
    def interrupt(signum, frame):
        nonlocal status, reason
        if cleaning:
            # A second interrupt must not escape the TERM/KILL/reap sequence.
            status, reason = 'FAIL', 'signal ' + str(signum) + ' during cleanup'
            return
        raise InterruptedError('signal ' + str(signum))
    try:
        for sig in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP):
            old_handlers[sig] = signal.signal(sig, interrupt)
        while True:
            result = os.waitid(os.P_PID, child.pid, os.WEXITED | os.WNOHANG | os.WNOWAIT)
            if result is not None:
                status = 'PASS' if result.si_code == os.CLD_EXITED and result.si_status == 0 else 'FAIL'
                reason = 'exit ' + str(result.si_status)
                if members(child.pid):
                    status, reason = 'FAIL', 'background descendants'
                break
            if time.monotonic() - started >= deadline:
                reason = 'deadline exceeded'
                break
            time.sleep(.02)
    except InterruptedError as error:
        reason = str(error)
    finally:
        cleaning = True
        # Clean the full test group on success too; no escaped ordinary children.
        try:
            os.killpg(child.pid, signal.SIGTERM)
            time.sleep(.05)
            os.killpg(child.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        child.wait()
        for sig, handler in old_handlers.items():
            signal.signal(sig, handler)
    return status, reason, time.monotonic() - started


def classify_output(row, result, lines):
    """An exact declaration can excuse only its skipped optional subsection."""
    sections, skips = [], []
    reported_skips, ran_tests = 0, 0
    for line in lines:
        text = line.strip()
        if text.startswith(('PASS applicability:', 'PASS compilation:', 'PASS behavioral:',
                            'NOT RUN ', 'BLOCKED ', 'SKIP ', 'SKIP:', 'SKIPPED ')):
            sections.append(text)
        event = None
        if text.startswith(('SKIP ', 'SKIP:', 'SKIPPED ')):
            event = dict(kind='line', message=text, test_id=None)
        match = re.match(r'^(\S+) \(([^)]+)\).*?\.\.\. skipped (.+)$', text)
        if match:
            method, identity, encoded = match.groups()
            try:
                message = ast.literal_eval(encoded)
            except (SyntaxError, ValueError):
                message = None
            identity = identity.removeprefix('__main__.')
            if not identity.endswith('.' + method):
                identity += '.' + method
            event = dict(kind='unittest', message=message if isinstance(message, str) else text,
                         test_id=identity)
            sections.append(text)
        summary = re.match(r'^(?:OK|FAILED) \(.*?skipped=(\d+)(?:[,)].*)?$', text)
        if summary:
            reported_skips += int(summary[1])
        ran = re.match(r'^Ran (\d+) tests? in ', text)
        if ran:
            ran_tests += int(ran[1])
        if event:
            matches = [item for item in row.get('optional_subchecks', [])
                       if item['kind'] == event['kind'] and item['message'] == event['message']
                       and (event['kind'] == 'line' or event['test_id'] in item['test_ids'])]
            declared = matches[0] if len(matches) == 1 else None
            skips.append(dict(event, status='SKIPPED', declared_optional=declared is not None,
                              declaration=declared))
    detailed = sum(item['kind'] == 'unittest' for item in skips)
    if reported_skips > detailed:
        skips.append(dict(kind='unittest-summary', message=f'{reported_skips-detailed} unidentified unittest skips',
                          count=reported_skips-detailed, test_id=None, status='SKIPPED',
                          declared_optional=False, declaration=None))
    result.update(source_sections=sections, subchecks=skips,
                  subcheck_counts={'SKIPPED': sum(item.get('count', 1) for item in skips)}, optional_suite_skip=False)
    # Exit failures/deadlines/cleanup failures always dominate printed skip text.
    if result['status'] != 'PASS':
        return
    if any(line.startswith('BLOCKED ') for line in sections):
        result.update(status='BLOCKED', reason='test reported BLOCKED')
        return
    whole = any(item['declared_optional'] and item['declaration']['scope'] == 'whole_test' for item in skips)
    unknown = any(not item['declared_optional'] for item in skips)
    all_unittest_skipped = ran_tests > 0 and max(reported_skips, detailed) >= ran_tests
    if unknown or whole or all_unittest_skipped:
        result.update(status='SKIPPED', reason='undeclared/mandatory skip' if unknown else 'whole test skipped')
        result['optional_suite_skip'] = not row['mandatory'] and not unknown and whole


def run(repo, directory, path):
    row = next(row for row in entries(repo) if row['path'] == path)
    result = dict(path=path, status='BLOCKED', reason='', duration_seconds=0,
                  source_sections=[], command=[], subchecks=[], subcheck_counts={'SKIPPED': 0},
                  optional_suite_skip=False)
    # Match the compiler selected by the Rust test, including an explicit empty
    # or missing override. Never fall back to a different PATH compiler.
    prerequisites = [row['interpreter'], *[os.environ.get('RUSTC', name)
                     if name == 'rustc' else name for name in row['prerequisites']]]
    result['resolved_prerequisites'] = prerequisites
    missing = [name for name in prerequisites if shutil.which(name) is None]
    missing += [name for name in row['required_inputs'] if not (repo / name).is_file()]
    if row['exact_source'] and not os.environ.get('ROG5_LINUX_SOURCE'):
        missing.append('ROG5_LINUX_SOURCE')
    key = hashlib.sha256(path.encode()).hexdigest()[:20]
    if missing:
        result['reason'] = 'missing prerequisites: ' + ', '.join(missing)
    else:
        command = [row['interpreter']]
        if row['python_optimized']:
            command.append('-O')
        command.append(str(repo / path))
        if any(item['kind'] == 'unittest' for item in row.get('optional_subchecks', [])) and path.endswith('.py'):
            # unittest's default progress dots omit skip reasons/test identities.
            command.append('-v')
        result['command'] = command
        with (directory / (key + '.stdout')).open('wb') as out, (directory / (key + '.stderr')).open('wb') as err:
            result['status'], result['reason'], result['duration_seconds'] = execute(command, row['deadline_seconds'], out, err)
        texts = []
        for suffix, stream in (('.stdout', sys.stdout), ('.stderr', sys.stderr)):
            with (directory / (key + suffix)).open(errors='replace') as source:
                for line in source:
                    stream.write(line)
                    if line.startswith(('PASS applicability:', 'PASS compilation:', 'PASS behavioral:',
                                        'NOT RUN ', 'BLOCKED ', 'SKIP ', 'SKIP:', 'SKIPPED ',
                                        'OK (', 'FAILED (', 'Ran ')) or '... skipped ' in line:
                        texts.append(line)
        classify_output(row, result, texts)
    atomic(directory / (key + '.json'), json.dumps(result, indent=2) + '\n')
    print('RESULT', result['status'], path, result['reason'])
    return 0 if result['status'] == 'PASS' or result['optional_suite_skip'] else 1


def summarize(repo, directory):
    selection = json.loads((directory / 'selection.json').read_text())
    results = {item['path']: item for path in directory.glob('*.json')
               if path.name not in ('selection.json', 'summary.json')
               for item in [json.loads(path.read_text())]}
    rows = []
    for entry in entries(repo):
        path = entry['path']
        rows.append(results.get(path, dict(path=path, status='BLOCKED' if path in selection['selected'] else 'NOT_SELECTED',
                                          reason='not reached' if path in selection['selected'] else 'outside selected tier',
                                          duration_seconds=0, source_sections=[])))
    counts = {status: sum(row['status'] == status for row in rows) for status in STATUSES}
    subchecks = [(row['path'], item) for row in rows for item in row.get('subchecks', [])]
    summary = dict(schema=1, tier=selection['tier'], counts=counts,
                   subcheck_counts={'SKIPPED': sum(item.get('count', 1) for _, item in subchecks)}, tests=rows)
    atomic(directory / 'summary.json', json.dumps(summary, indent=2) + '\n')
    suite = ET.Element('testsuite', name='rog5-offline', tests=str(len(rows) + len(subchecks)),
                       failures=str(counts['FAIL']), errors=str(counts['BLOCKED']),
                       skipped=str(counts['SKIPPED'] + counts['NOT_SELECTED'] + len(subchecks)))
    for row in rows:
        case = ET.SubElement(suite, 'testcase', name=row['path'], time=str(row['duration_seconds']))
        if row['status'] != 'PASS':
            kind = 'failure' if row['status'] == 'FAIL' else 'error' if row['status'] == 'BLOCKED' else 'skipped'
            ET.SubElement(case, kind, message=row['status'] + ': ' + row['reason'])
        ET.SubElement(case, 'system-out').text = '\n'.join(row['source_sections'])
    for index, (path, item) in enumerate(subchecks):
        case = ET.SubElement(suite, 'testcase', name=path + '::optional-subcheck-' + str(index), time='0')
        ET.SubElement(case, 'skipped', message=item['message'])
        ET.SubElement(case, 'system-out').text = json.dumps(item, sort_keys=True)
    atomic(directory / 'summary.xml', ET.tostring(suite, encoding='unicode') + '\n')
    print('SUMMARY', json.dumps(counts), directory / 'summary.json')
    return int(any(row['status'] in ('FAIL', 'BLOCKED') or
                   (row['status'] == 'SKIPPED' and not row.get('optional_suite_skip', False))
                   for row in rows))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['init', 'run', 'summary'])
    parser.add_argument('repo', type=Path)
    parser.add_argument('directory', type=Path)
    parser.add_argument('values', nargs='*')
    args = parser.parse_args()
    if args.action == 'init':
        tier, *selected = args.values
        indexed = {row['path']: row for row in entries(args.repo)}
        for path in selected:
            if path not in indexed or tier not in indexed[path]['tiers']:
                raise ValueError('selected test absent from manifest tier: ' + path)
        expected = {path for path, row in indexed.items() if tier in row['tiers']}
        if set(selected) != expected:
            raise ValueError('shell selection and declarative manifest disagree')
        args.directory.mkdir(parents=True, exist_ok=False)
        atomic(args.directory / 'selection.json', json.dumps(dict(tier=tier, selected=selected)))
    elif args.action == 'run':
        return run(args.repo, args.directory, args.values[0])
    else:
        return summarize(args.repo, args.directory)
    return 0


if __name__ == '__main__':
    sys.exit(main())
