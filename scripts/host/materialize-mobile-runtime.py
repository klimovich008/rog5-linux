#!/usr/bin/env python3
"""Assemble authenticated package payloads for isolated host tests, never install them."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import stat
import tarfile
import time

REPO = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location('closure', Path(__file__).with_name('check-mobile-package-closure.py'))
CLOSURE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CLOSURE)
RESERVE = 3 * 1024**3
METADATA = {'.PKGINFO', '.BUILDINFO', '.MTREE', '.INSTALL', '.CHANGELOG'}


def digest(path):
    with CLOSURE.regular_file(path) as stream:
        return CLOSURE.stream_hash(stream)


def inventory(packages, cache):
    """Bounded streaming preflight; do not extract or execute package metadata."""
    rows = []
    owners = {}
    for package in packages:
        path = cache / package['archive']
        if digest(path) != package['sha256']:
            raise ValueError('archive changed before inventory')
        size, entries = 0, 0
        with tarfile.open(path, 'r|*') as archive:
            for member in archive:
                name = PurePosixPath(member.name)
                if name.is_absolute() or '..' in name.parts:
                    raise ValueError('unsafe archive member name')
                if len(name.parts) == 1 and name.name in METADATA:
                    archive.members.clear()
                    continue
                if not (member.isfile() or member.isdir() or member.issym() or member.islnk()):
                    raise ValueError('special archive member refused')
                if not member.isdir():
                    if str(name) in owners:
                        raise ValueError(f'conflicting package payload: {name}')
                    owners[str(name)] = package['name']
                if member.isfile():
                    size += member.size
                entries += 1
                archive.members.clear()
        rows.append({'name': package['name'], 'bytes': size, 'entries': entries})
    return rows


def extract_archive(path, root):
    # Only native tool libraries, the input archive and the new output tree are
    # visible. No host /etc, home, devices, network or target package code runs.
    command = ['bwrap', '--unshare-all', '--die-with-parent', '--cap-drop', 'ALL',
               '--ro-bind', '/usr', '/usr', '--ro-bind', '/lib', '/lib']
    if Path('/lib64').exists():
        command += ['--ro-bind', '/lib64', '/lib64']
    command += ['--ro-bind', str(path), '/archive', '--bind', str(root), '/out',
                '--chdir', '/out', '--clearenv', '--setenv', 'LC_ALL', 'C',
                '--', '/usr/bin/bsdtar', '-xkf', '/archive', '-C', '/out',
                '--no-same-owner', '--no-same-permissions', '--no-acls',
                '--no-xattrs', '--no-fflags']
    for name in sorted(METADATA):
        command += ['--exclude', name]
    CLOSURE.bounded_command(command, timeout=60)
    return command


def materialize(packages, cache, root, inventory_rows):
    required = sum(row['bytes'] + 8192 * row['entries'] for row in inventory_rows)
    if shutil.disk_usage(root.parent).free < RESERVE + required:
        raise ValueError('insufficient disk for payloads plus 3 GiB reserve')
    root.mkdir()  # Caller-owned new directory only; no replacement or merging.
    commands = []
    old_umask = os.umask(0o077)
    try:
        for package, row in zip(packages, inventory_rows, strict=True):
            if shutil.disk_usage(root).free < RESERVE + row['bytes'] + row['entries'] * 8192:
                raise ValueError('disk reserve reached')
            path = cache / package['archive']
            if digest(path) != package['sha256']:
                raise ValueError('archive changed before extraction')
            commands.append(extract_archive(path, root))
            if digest(path) != package['sha256']:
                raise ValueError('archive changed during extraction')
    finally:
        os.umask(old_umask)
    return commands


def tree_manifest(root):
    rows = []
    for directory, subdirs, files in os.walk(root, followlinks=False):
        for name in sorted(subdirs + files):
            path = Path(directory) / name
            info = path.lstat()
            row = {'path': str(path.relative_to(root)), 'mode': stat.S_IMODE(info.st_mode)}
            if stat.S_ISLNK(info.st_mode):
                row.update(type='symlink', target=os.readlink(path))
            elif stat.S_ISREG(info.st_mode):
                row.update(type='file', size=info.st_size, sha256=digest(path))
            elif stat.S_ISDIR(info.st_mode):
                row.update(type='directory')
            else:
                raise ValueError('unexpected special output')
            rows.append(row)
    return sorted(rows, key=lambda row: row['path'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('graph', 'cache', 'keyring', 'trusted', 'revoked', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    output = args.output.absolute()
    output.mkdir()  # Failure here must never change an existing output's receipt.
    record = {'status': 'IN_PROGRESS', 'scope': 'host-test package payload tree; not an installable image',
              'installation_scripts_executed': False, 'physical_status': 'NOT RUN', 'authority': 'none'}
    started = time.monotonic()
    try:
        graph_path = (REPO / args.graph).resolve()
        CLOSURE.validate(REPO, graph=graph_path)
        graph = json.loads(graph_path.read_text())
        record['graph_sha256'] = digest(graph_path)
        record['archive_audit'] = CLOSURE.audit_archives(graph['packages'], args.cache.resolve(),
                                                       args.keyring.absolute(), args.trusted.absolute(),
                                                       args.revoked.absolute())
        if record['archive_audit']['status'] != 'PASS':
            raise ValueError('package authentication failed; no payload tree created')
        rows = inventory(graph['packages'], args.cache.resolve())
        record['inventory'] = rows
        record['commands'] = materialize(graph['packages'], args.cache.resolve(), output / 'root', rows)
        tree = output / 'tree.json'
        tree.write_text(json.dumps(tree_manifest(output / 'root'), indent=2) + '\n')
        record['tree_manifest_sha256'] = digest(tree)
        record['status'] = 'PASS'
    except BaseException as error:
        record.update(status='FAIL', error=f'{type(error).__name__}: {error}')
        raise
    finally:
        record['duration_seconds'] = time.monotonic() - started
        (output / 'result.json').write_text(json.dumps(record, indent=2) + '\n')
    print('PASS host-test payload tree; ABI, generated caches and runtime/session qualification NOT RUN')


if __name__ == '__main__':
    main()
