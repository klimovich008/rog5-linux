#!/usr/bin/env python3
"""Small ROG5 acceptance dispatcher. No admission, device retry or evidence merge."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import time

REPO = Path(__file__).resolve().parents[2]
CONTRACT = REPO/'configs/release-acceptance.json'
STATUSES = ['PASS', 'FAIL', 'BLOCKED', 'NOT RUN']
ARTIFACT_ROLES = {'kernel', 'dtb', 'initramfs', 'rootfs', 'boot_bundle'}


def sha_file(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def load_contract():
    contract = json.loads(CONTRACT.read_text())
    validate_contract(contract)
    return contract


def validate_contract(contract):
    if contract.get('format') != 'rog5-release-acceptance-v1' or contract.get('statuses') != STATUSES:
        raise ValueError('unsupported contract/status vocabulary')
    seen = set()
    for test in contract['tests']:
        if not re.fullmatch(r'[A-Z][0-9]{2}', test['id']) or test['id'] in seen:
            raise ValueError('invalid/duplicate test ID')
        seen.add(test['id'])
        for field in ('outcome', 'environment', 'prerequisites', 'pass_condition',
                      'fail_condition', 'mutations', 'cleanup', 'required_evidence'):
            if not test.get(field):
                raise ValueError(f'{test["id"]}: missing {field}')
        if type(test['mandatory']) is not bool or type(test['deadline_seconds']) is not int or test['deadline_seconds'] <= 0:
            raise ValueError('invalid mandatory/deadline')
        if test['tier'] not in {'quick', 'offline', 'device-smoke', 'release'}:
            raise ValueError('unknown test tier')
        if not test['commands'] and not test['blocker']:
            raise ValueError('unimplemented check needs an explicit blocker')
        for command in test['commands']:
            if not command or any(not isinstance(x, str) or not x for x in command):
                raise ValueError('commands must be nonempty argv arrays')
    if not seen:
        raise ValueError('empty contract')


def select(contract, tier):
    return [t for t in contract['tests'] if t['tier'] in contract['tiers'][tier]]


def all_pass(rows):
    required = [r for r in rows if r['mandatory']]
    return bool(required) and all(r['status'] == 'PASS' for r in required)


def source_identity(repo=REPO):
    def git(*args):
        return subprocess.check_output(['git', '-C', str(repo), *args])
    revision = git('rev-parse', 'HEAD').decode().strip()
    status = git('status', '--porcelain=v1', '--untracked-files=all')
    digest = hashlib.sha256(revision.encode() + status + git('diff', '--binary', '--no-ext-diff', 'HEAD'))
    for name in sorted(git('ls-files', '--others', '--exclude-standard', '-z').split(b'\0')):
        if name:
            path = repo/os.fsdecode(name)
            digest.update(name + b'\0')
            if path.is_symlink():
                digest.update(os.fsencode(os.readlink(path)))
            elif path.is_file():
                digest.update(sha_file(path).encode())
    return {'revision': revision, 'worktree_digest': digest.hexdigest(), 'clean': not status}


def verify_release(path, *, required_roles=None):
    record = json.loads(path.read_text())
    if record.get('format') != 'rog5-release-inputs-v1' or not re.fullmatch(r'[0-9a-f]{40}', record.get('source_revision', '')):
        raise ValueError('release input format/revision')
    if not re.fullmatch(r'[a-z0-9][a-z0-9._-]{0,127}', record.get('candidate_id', '')):
        raise ValueError('release candidate identity')
    required_roles = ARTIFACT_ROLES if required_roles is None else required_roles
    if not required_roles or not required_roles <= set(record.get('artifacts', {})) <= ARTIFACT_ROLES:
        raise ValueError('release must bind kernel, DTB, archive, retained root image and boot bundle')
    identities = {}
    for role, artifact in record['artifacts'].items():
        target = Path(artifact['path'])
        if not target.is_absolute() or target.is_symlink() or not target.is_file():
            raise ValueError(f'{role}: not an exact regular artifact')
        if type(artifact.get('size')) is not int or target.stat().st_size != artifact['size']:
            raise ValueError(f'{role}: size mismatch')
        if not re.fullmatch(r'[0-9a-f]{64}', artifact.get('sha256', '')) or sha_file(target) != artifact['sha256']:
            raise ValueError(f'{role}: hash mismatch')
        identities[role] = {key: artifact[key] for key in ('size', 'sha256')}
    return {'candidate_id': record['candidate_id'], 'source_revision': record['source_revision'],
            'artifact_paths': {role: artifact['path'] for role, artifact in record['artifacts'].items()},
            'artifacts': identities, 'receipt_sha256': sha_file(path)}


def utc():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def run_one(test, output, release=None, capture=None):
    row = {'id': test['id'], 'mandatory': test['mandatory'], 'outcome': test['outcome'],
           'status': 'BLOCKED', 'duration_seconds': 0, 'started_at': utc(),
           'next_action': test['blocker'], 'commands': test['commands'], 'test_versions': {}}
    if not test['commands']:
        return row
    commands = test['commands']
    if any('{' in token or '}' in token for command in commands for token in command):
        if release is None:
            row['next_action'] = 'supply verified exact artifact receipt; source tests are not archive proof'
            return row
        bindings = {'{kernel}': release['artifact_paths']['kernel'],
                    '{initramfs}': release['artifact_paths']['initramfs'],
                    '{test_output}': str(output/test['id'])}
        if any(token.startswith('{capture_') for command in commands for token in command):
            if capture is None:
                row['next_action'] = 'supply the currently running exact receiver with --capture'
                return row
            try:
                receipt = json.loads((capture/'receipt.json').read_text())
                if (receipt['canonical_record']['candidate'] != release['candidate_id']
                        or receipt['canonical_record']['boot_image_sha256'] != release['artifacts']['boot_bundle']['sha256']):
                    raise ValueError('capture/release candidate or boot image mismatch')
                row['capture_receipt_sha256'] = sha_file(capture/'receipt.json')
                bindings.update({'{capture_profile}':receipt['profile'], '{capture_output}':str(capture)})
            except (OSError, KeyError, TypeError, ValueError) as error:
                row.update(status='FAIL', next_action='invalid capture binding: '+str(error))
                return row
        commands = [[bindings.get(token, token) for token in command] for command in commands]
        if any('{' in token or '}' in token for command in commands for token in command):
            row['next_action'] = 'unknown unresolved runner argument'
            return row
        row['commands'] = commands
    for prerequisite in test['prerequisites']:
        if prerequisite in {'python3', 'bash', 'sh', 'gcc', 'git', 'cpio', 'podman', 'bwrap'} and not shutil.which(prerequisite):
            row['next_action'] = f'missing prerequisite: {prerequisite}'
            return row
        if prerequisite.startswith('artifacts/') and not (REPO/prerequisite).is_file():
            row['next_action'] = f'missing prerequisite: {prerequisite}'
            return row
    started = time.monotonic()
    log_path = output/(test['id'] + '.log')
    row['log'] = log_path.name
    row['status'] = 'PASS'
    # Whole test shares one deadline; child groups cannot outlive a timed-out test.
    with log_path.open('wb') as log:
        for command in commands:
            for token in command:
                path = REPO/token
                if path.is_file():
                    row['test_versions'][token] = sha_file(path)
            remaining = test['deadline_seconds'] - (time.monotonic() - started)
            if remaining <= 0:
                row.update(status='FAIL', next_action='test deadline exhausted')
                break
            try:
                process = subprocess.Popen(command, cwd=REPO, stdout=log, stderr=subprocess.STDOUT,
                                           start_new_session=True, env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1'))
            except FileNotFoundError:
                row.update(status='BLOCKED', next_action=f'missing executable: {command[0]}')
                break
            try:
                code = process.wait(timeout=remaining)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait()
                row.update(status='FAIL', next_action='test deadline exceeded; owned process group stopped')
                break
            row['exit_code'] = code
            if code == 77:
                row.update(status='BLOCKED', next_action='runner prerequisite unavailable; see private log')
                break
            if code:
                row.update(status='FAIL', next_action=f'fix failing test; exit {code}; see private log')
                break
    row.update(duration_seconds=round(time.monotonic() - started, 3),
               ended_at=utc(), log_sha256=sha_file(log_path))
    if row['status'] == 'PASS' and re.search(r'skipped=[1-9][0-9]*|^SKIP\b', log_path.read_text(errors='replace'), re.M):
        row.update(status='BLOCKED', next_action='required suite skipped behavior; supply prerequisites and rerun')
    return row


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('tier', choices=['quick', 'offline', 'device-smoke', 'release'])
    parser.add_argument('--list', action='store_true', help='show contract without executing')
    parser.add_argument('--output', type=Path, help='new private evidence directory outside repository')
    parser.add_argument('--release', type=Path, help='exact artifact receipt; no implied admission')
    parser.add_argument('--capture', type=Path, help='currently running private receiver directory; H01 only')
    args = parser.parse_args()
    contract = load_contract()
    selected = select(contract, args.tier)
    if args.list:
        for test in selected:
            command = ' ; '.join(' '.join(c) for c in test['commands']) or 'BLOCKED: ' + test['blocker']
            print(f'{test["id"]}\t{test["deadline_seconds"]}s\t{test["outcome"]}\t{command}')
        return 0
    if args.output is None:
        parser.error('execution requires --output pointing to a new private directory')
    output = args.output.resolve()
    if output.is_relative_to(REPO) or output.exists():
        parser.error('output must be new and outside repository (private logs)')
    output.mkdir(mode=0o700, parents=False)
    before = source_identity()
    started = time.monotonic()
    report = {'format': 'rog5-release-results-v1', 'started_at': utc(), 'tier': args.tier,
              'source': before, 'contract_sha256': sha_file(CONTRACT),
              'runner_sha256': sha_file(Path(__file__)), 'release': None,
              'evidence_reused': False, 'qualified': False, 'tests': []}
    error = ''
    if args.release:
        try:
            report['release'] = verify_release(args.release)
            if report['release']['source_revision'] != before['revision']:
                raise ValueError('artifact source revision does not match tested HEAD')
        except (ValueError, KeyError, OSError, TypeError) as exc:
            error = str(exc)
    selected_ids = {t['id'] for t in selected}
    for test in contract['tests']:
        if test['id'] not in selected_ids or error:
            row = {'id': test['id'], 'mandatory': test['mandatory'], 'outcome': test['outcome'],
                   'status': 'NOT RUN', 'duration_seconds': 0,
                   'next_action': error or f'run {test["tier"]} prerequisite/check'}
        else:
            row = run_one(test, output, report['release'], args.capture)
            print(f'{row["id"]}: {row["status"]} ({row["duration_seconds"]:.3f}s)', flush=True)
        report['tests'].append(row)
    after = source_identity()
    if before != after:
        error = 'source changed during run; results are not a frozen checkpoint'
    if args.release and report['release']:
        try:
            if verify_release(args.release) != report['release']:
                error = 'release receipt changed during run; no coherent release evidence'
        except (ValueError, KeyError, OSError, TypeError) as exc:
            error = 'artifact revalidation failed: ' + str(exc)
    report.update(ended_at=utc(), duration_seconds=round(time.monotonic()-started, 3),
                  source_after=after, invalid_reason=error)
    selected_rows = [r for r in report['tests'] if r['id'] in selected_ids]
    report['result'] = ('FAIL' if error or any(r['status'] == 'FAIL' for r in selected_rows)
                        else 'PASS' if all_pass(selected_rows) else 'BLOCKED')
    report['qualified'] = bool(not error and before['clean'] and report['release'] and all_pass(report['tests']))
    (output/'results.json').write_text(json.dumps(report, indent=2) + '\n')
    matrix = ['# Current run — not an aggregate of historical releases', '',
              f'Tier: {args.tier}; result: {report["result"]}; release qualified: {report["qualified"]}.', '',
              '| Required test | Result | Evidence | Next action |', '|---|---|---|---|']
    for row in report['tests']:
        matrix.append(f'| {row["id"]}: {row["outcome"]} | {row["status"]} | {row.get("log", "none")} | {row["next_action"]} |')
    (output/'matrix.md').write_text('\n'.join(matrix) + '\n')
    print(f'{report["result"]}; release qualified={report["qualified"]}; evidence: {output}')
    return {'PASS': 0, 'FAIL': 1, 'BLOCKED': 2}[report['result']]


if __name__ == '__main__':
    raise SystemExit(main())
