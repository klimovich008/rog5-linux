#!/usr/bin/env python3
"""Check recorded native-mobile dependency metadata; does not install packages."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import selectors
import shutil
import signal
import stat
import subprocess
import tempfile
import time
from contextlib import ExitStack

def need(condition, message):
    if not condition:
        raise ValueError(message)


def bounded_command(argv, *, timeout=20, limit=131072, pass_fds=()):
    """Bound elapsed time and combined output; reap the isolated process group."""
    started = time.monotonic()
    output = bytearray()
    with selectors.DefaultSelector() as selector:
        proc = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, start_new_session=True,
                                pass_fds=pass_fds, env=dict(os.environ, LC_ALL='C'))
        try:
            selector.register(proc.stdout, selectors.EVENT_READ)
            while True:
                remaining = timeout - (time.monotonic() - started)
                need(remaining > 0, f'command deadline exceeded: {argv[0]}')
                for key, _ in selector.select(min(remaining, 0.05)):
                    data = os.read(key.fileobj.fileno(), 8192)
                    if not data:
                        selector.unregister(key.fileobj)
                    output.extend(data)
                    need(len(output) <= limit, f'command output limit exceeded: {argv[0]}')
                # Keep the leader waitable until group cleanup, preventing PID reuse.
                exited = os.waitid(os.P_PID, proc.pid, os.WEXITED | os.WNOHANG | os.WNOWAIT)
                if exited is not None and not selector.get_map():
                    break
        finally:
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            proc.wait()
            proc.stdout.close()
    need(proc.returncode == 0, f'command failed ({proc.returncode}): {argv[0]}')
    return output.decode('utf-8', errors='strict')


def regular_file(path):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        need(stat.S_ISREG(os.fstat(fd).st_mode), f'not a regular file: {path.name}')
        return os.fdopen(fd, 'rb')
    except BaseException:
        os.close(fd)
        raise


def file_identity(stream):
    st = os.fstat(stream.fileno())
    return st.st_dev, st.st_ino, st.st_size, st.st_mtime_ns, st.st_ctime_ns


def stream_hash(stream):
    stream.seek(0)
    digest = hashlib.sha256()
    for chunk in iter(lambda: stream.read(1024 * 1024), b''):
        digest.update(chunk)
    stream.seek(0)
    return digest.hexdigest()


def fingerprints(data, trusted=False):
    result = set()
    for line in data.decode('ascii').splitlines():
        if not line or line.startswith('#'):
            continue
        pattern = r'([A-F0-9]{40}|[A-F0-9]{64}):[456]:' if trusted else r'([A-F0-9]{40}|[A-F0-9]{64})'
        match = re.fullmatch(pattern, line)
        need(match is not None, 'malformed trusted/revoked fingerprint record')
        result.add(match[1])
    need(not trusted or bool(result), 'no explicitly trusted signer')
    return result


def verify_package(package, directory, keyring, trusted, revoked):
    name = package['archive']
    need(isinstance(name, str) and name not in ('', '.', '..')
         and Path(name).name == name and '/' not in name, 'archive must be one basename')
    with ExitStack() as stack:
        archive = stack.enter_context(regular_file(directory / name))
        signature = stack.enter_context(regular_file(directory / (name + '.sig')))
        identities = [file_identity(f) for f in (archive, signature)]
        need(identities[0][2] == package['size'], 'archive size mismatch')
        need(identities[1][2] <= 65536, 'signature too large')
        sha, sigsha = stream_hash(archive), stream_hash(signature)
        need(sha == package['sha256'], 'archive SHA256 mismatch')
        need(sigsha == package['signature_sha256'], 'signature SHA256 mismatch')
        af, sf = archive.fileno(), signature.fileno()
        output = bounded_command(['gpgv', '--homedir', str(keyring.parent), '--status-fd', '1',
                                  '--keyring', str(keyring), f'/proc/self/fd/{sf}',
                                  f'/proc/self/fd/{af}'], pass_fds=(af, sf))
        statuses = [line[len('[GNUPG:] '):].split() for line in output.splitlines()
                    if line.startswith('[GNUPG:] ')]
        valid = [tokens for tokens in statuses if tokens[0] == 'VALIDSIG']
        need(len(valid) == 1 and len(valid[0]) in (10, 11), 'expected one valid signature')
        need(not any(tokens[0] in {'REVKEYSIG', 'EXPKEYSIG', 'EXPSIG', 'KEYEXPIRED',
                                  'SIGEXPIRED', 'BADSIG', 'ERRSIG'} for tokens in statuses),
             'expired, revoked or invalid signature')
        signer = valid[0][1]
        primary = valid[0][10] if len(valid[0]) == 11 else signer
        need(not {signer, primary} & revoked, 'signer is revoked')
        need(primary in trusted, 'primary signer is not explicitly trusted')
        archive.seek(0)
        listing = bounded_command(['bsdtar', '-tvf', f'/proc/self/fd/{af}', '.PKGINFO'],
                                  pass_fds=(af,), limit=4096).splitlines()
        need(len(listing) == 1 and listing[0].startswith('-'),
             'expected one regular .PKGINFO member')
        archive.seek(0)
        metadata = bounded_command(['bsdtar', '-xOf', f'/proc/self/fd/{af}', '.PKGINFO'],
                                   pass_fds=(af,), limit=65536)
        fields = {}
        for line in metadata.splitlines():
            if not line or line.startswith('#'):
                continue
            key, separator, value = line.partition(' = ')
            need(bool(separator) and bool(value), 'malformed .PKGINFO')
            fields.setdefault(key, []).append(value)
        for field, expected in (('pkgname', package['name']), ('pkgver', package['version']),
                                ('arch', package['architecture'])):
            need(fields.get(field) == [expected], f'.PKGINFO {field} mismatch or duplicate')
        for field, expected in (('depend', package['depends']), ('provides', package['provides'])):
            need(sorted(fields.get(field, [])) == sorted(expected), f'.PKGINFO {field} mismatch')
        need(identities == [file_identity(f) for f in (archive, signature)],
             'package input changed during verification')
        return {'sha256': sha, 'signature_sha256': sigsha,
                'signer': signer, 'primary_signer': primary, 'metadata': 'PASS'}


def audit_archives(packages, directory, keyring, trusted_file, revoked_file):
    """Audit an immutable graph against local bytes; never infer runtime closure."""
    report = {'format': 'rog5-mobile-archive-audit-v1', 'packages': [],
              'counts': {'PASS': 0, 'FAIL': 0, 'BLOCKED': 0},
              'keyring_freshness': 'NOT RUN', 'installation_authorized': False,
              'scope': 'archive identity, retained-key signature and .PKGINFO; not runtime qualification'}
    started = time.monotonic()
    with tempfile.TemporaryDirectory(prefix='rog5-package-keys-') as temporary:
        snapshot = Path(temporary)
        try:
            for command in ('gpgv', 'bsdtar'):
                if shutil.which(command) is None:
                    raise FileNotFoundError(f'missing command: {command}')
            report['tools'] = {}
            for command in ('gpgv', 'bsdtar'):
                path = Path(shutil.which(command)).resolve()
                with regular_file(path) as stream:
                    digest = stream_hash(stream)
                report['tools'][command] = {'path': str(path), 'sha256': digest,
                                             'version': bounded_command([str(path), '--version']).splitlines()[0]}
            sources = {}
            for label, path in (('keyring', keyring), ('trusted', trusted_file), ('revoked', revoked_file)):
                with regular_file(path) as stream:
                    identity = file_identity(stream)
                    data = stream.read(2 * 1024 * 1024 + 1)
                    need(len(data) <= 2 * 1024 * 1024, 'key input too large')
                    need(identity == file_identity(stream), 'key input changed')
                (snapshot / label).write_bytes(data)
                sources[label] = hashlib.sha256(data).hexdigest()
            report['trust_inputs_sha256'] = sources
            trusted = fingerprints((snapshot / 'trusted').read_bytes(), trusted=True)
            revoked = fingerprints((snapshot / 'revoked').read_bytes())
            prerequisite = None
        except (OSError, ValueError) as error:
            prerequisite = ('BLOCKED' if isinstance(error, FileNotFoundError) else 'FAIL', str(error))
        for package in packages:
            row = {'name': package['name'], 'version': package['version'], 'archive': package['archive']}
            if prerequisite:
                row.update(status=prerequisite[0], reason=prerequisite[1])
            else:
                try:
                    row.update(verify_package(package, directory, snapshot / 'keyring', trusted, revoked),
                               status='PASS')
                except (OSError, ValueError, KeyError) as error:
                    row.update(status='BLOCKED' if isinstance(error, FileNotFoundError) else 'FAIL',
                               reason=str(error))
            report['packages'].append(row)
            report['counts'][row['status']] += 1
    need(bool(packages), 'empty package graph')
    report['status'] = 'FAIL' if report['counts']['FAIL'] else 'BLOCKED' if report['counts']['BLOCKED'] else 'PASS'
    report['duration_seconds'] = time.monotonic() - started
    return report

def validate(root, database_dir=None):
    lock = json.loads((root / 'packaging/arch/mobile-package-closure.json').read_text())
    need(hashlib.sha256((root / lock['source_lock']['path']).read_bytes()).hexdigest() == lock['source_lock']['sha256'], 'invalid recorded metadata')
    packages = {p['name']: p for p in lock['packages']}
    need(len(packages) == len(lock['packages']) == lock['counts']['packages'], 'invalid recorded metadata')
    need(set(lock['roots']) <= packages.keys(), 'invalid recorded metadata')
    need({'mesa', 'vulkan-freedreno', 'wayland', 'libinput', 'seatd', 'fontconfig', 'foot', 'mousepad'} <= packages.keys(), 'invalid recorded metadata')
    need(not {'plasma-desktop', 'kwin', 'krdp'} & packages.keys(), 'invalid recorded metadata')
    requests = {('root', p) for p in lock['roots']}
    requests |= {(p['name'], d) for p in packages.values() for d in p['depends']}
    edges = {(e['from'], e['dependency']): e['provider'] for e in lock['dependency_edges']}
    need(requests == edges.keys(), 'missing or surplus dependency edge')
    for package in packages.values():
        need(package['architecture'] in ('aarch64', 'any'), 'invalid recorded metadata')
        need(re.fullmatch('[0-9a-f]{64}', package['sha256']), 'invalid recorded metadata')
        need(package['archive'].endswith(('.pkg.tar.xz', '.pkg.tar.zst')), 'invalid recorded metadata')
        need(package['signature_verified'] is False, 'invalid recorded metadata')
    for (_, dependency), provider in edges.items():
        p = packages[provider]
        name, *rest = re.split('([<>=]+)', dependency, maxsplit=1)
        provided = {re.split('[<>=]', v, maxsplit=1)[0]: v for v in p['provides']}
        need(name == provider or name in provided, dependency)
        if rest:
            operator, wanted = rest
            actual = p['version'] if name == provider else provided[name].split('=', 1)[1]
            comparison = int(subprocess.check_output(['vercmp', actual, wanted], text=True))
            need({'=': comparison == 0, '>=': comparison >= 0, '<=': comparison <= 0, '>': comparison > 0, '<': comparison < 0}[operator], dependency)
    if database_dir:
        for database in lock['repository_snapshots']:
            digest = hashlib.sha256()
            path = database_dir / (database['repository'] + '.db')
            need(path.stat().st_size == database['size'], 'invalid recorded metadata')
            with path.open('rb') as stream:
                for chunk in iter(lambda: stream.read(1024 * 1024), b''):
                    digest.update(chunk)
            need(digest.hexdigest() == database['sha256'], 'invalid recorded metadata')
    need(lock['status'] == 'BLOCKED' and lock['blockers'], 'invalid recorded metadata')
    need(lock['denial_runtime_artifacts']['flutter_engine_archive'] is None, 'invalid recorded metadata')
    need(not any(lock['authority'].values()), 'invalid recorded metadata')
    print(f'PASS metadata graph: {len(packages)} packages, {len(edges)} dependency edges')
    print('PASS retained database hashes' if database_dir else 'NOT RUN retained database hashes')
    print('BLOCKED runtime closure: archive/signature verification, valid repository snapshot and engine/AOT remain missing')

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database-dir', type=Path)
    parser.add_argument('--archive-dir', type=Path)
    parser.add_argument('--keyring', type=Path)
    parser.add_argument('--trusted', type=Path)
    parser.add_argument('--revoked', type=Path)
    parser.add_argument('--report', type=Path, help='new JSON file; existing evidence is never overwritten')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    inputs = (args.archive_dir, args.keyring, args.trusted, args.revoked, args.report)
    if any(inputs) and not all(inputs):
        parser.error('archive audit requires --archive-dir, --keyring, --trusted, --revoked and --report')
    validate(root, args.database_dir)
    if args.archive_dir:
        lock_path = root / 'packaging/arch/mobile-package-closure.json'
        lock_bytes = lock_path.read_bytes()
        lock = json.loads(lock_bytes)
        # Reserve the output first, so an existing receipt cannot trigger a rerun.
        with args.report.open('x') as output:
            report = audit_archives(lock['packages'], args.archive_dir, args.keyring, args.trusted, args.revoked)
            report['graph_sha256'] = hashlib.sha256(lock_bytes).hexdigest()
            report['runtime_closure'] = 'BLOCKED: retained repository authentication and matching engine/AOT are unqualified'
            json.dump(report, output, indent=2)
            output.write('\n')
        print(f"{report['status']} archive audit: {report['counts']}; runtime closure remains BLOCKED")
        raise SystemExit(1 if report['status'] == 'FAIL' else 2 if report['status'] == 'BLOCKED' else 0)
if __name__ == '__main__':
    main()
