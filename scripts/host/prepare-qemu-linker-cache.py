#!/usr/bin/env python3
"""Prepare an opt-in exact-runtime ARM64 linker cache; no installation authority."""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import resource
import shutil
import signal
import stat
import subprocess
import time

LIMIT = 1024**2
RESERVE = 3 * 1024**3


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def regular(path, maximum=64*1024**2):
    path = Path(path)
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or not 0 < info.st_size <= maximum:
        raise ValueError('expected bounded nonempty regular file: ' + str(path))
    return path


def load(path):
    return json.loads(regular(path).read_text())


def identity(path):
    return {'path': str(Path(path).absolute()), 'sha256': digest(path)}


def safe_name(value):
    path = PurePosixPath(value)
    if (not path.parts or path.is_absolute() or '..' in path.parts or str(path) != value
            or any(part.startswith('.virtfs_metadata') for part in path.parts)):
        raise ValueError('unsafe runtime member')
    return value


def snapshot(info):
    return tuple(getattr(info, name) for name in
                 ('st_dev', 'st_ino', 'st_mode', 'st_uid', 'st_gid', 'st_size', 'st_mtime_ns', 'st_ctime_ns'))


def mapped_metadata(path, kind):
    text = regular(path, 1024).read_text()
    fields = {}
    for line in text.splitlines():
        key, sep, value = line.partition('=')
        if not sep or key in fields or not value.isascii() or not value.isdecimal():
            raise ValueError('invalid mapped-file metadata')
        fields[key] = int(value)
    if (set(fields) != {'virtfs.uid', 'virtfs.gid', 'virtfs.mode', 'virtfs.rdev'}
            or any(fields[key] != 0 for key in ('virtfs.uid', 'virtfs.gid', 'virtfs.rdev'))
            or stat.S_IFMT(fields['virtfs.mode']) != kind or fields['virtfs.mode'] & 0o7000):
        raise ValueError('mapped runtime metadata changed')
    return fields


def verify_tree(runtime, tree, view):
    """Check actual symlinks and every byte; mapped-file view is never executable input."""
    rows = load(tree)
    by_name = {safe_name(row['path']): row for row in rows}
    if len(by_name) != len(rows):
        raise ValueError('duplicate runtime member')
    for root in (runtime, view):
        if root.is_symlink() or not root.is_dir():
            raise ValueError('runtime root must be a real directory')
        actual = set()
        for directory, dirs, files in os.walk(root, followlinks=False):
            if root == view:
                dirs[:] = [d for d in dirs if d != '.virtfs_metadata']
                files = [f for f in files if f != '.virtfs_metadata_root']
            actual.update(str((Path(directory)/name).relative_to(root)) for name in dirs+files)
        if actual != set(by_name):
            raise ValueError('runtime inventory additions or omissions')
    metadata = hashlib.sha256()
    metadata.update(json.dumps(mapped_metadata(view/'.virtfs_metadata_root', stat.S_IFDIR), sort_keys=True).encode())
    for name, row in sorted(by_name.items()):
        for parent in PurePosixPath(name).parents:
            if str(parent) != '.' and by_name.get(str(parent), {}).get('type') != 'directory':
                raise ValueError('runtime member has non-directory parent')
        source, target = runtime/name, view/name
        before, mapped = source.lstat(), target.lstat()
        kind = row['type']
        expected_kind = {'directory': stat.S_IFDIR, 'file': stat.S_IFREG, 'symlink': stat.S_IFLNK}.get(kind)
        if expected_kind is None or stat.S_IMODE(before.st_mode) != row['mode']:
            raise ValueError('runtime member type or mode changed')
        fields = mapped_metadata(target.parent/'.virtfs_metadata'/target.name, expected_kind)
        metadata.update(json.dumps({'path': name, 'fields': fields}, sort_keys=True).encode())
        if kind == 'directory':
            if not stat.S_ISDIR(before.st_mode) or not stat.S_ISDIR(mapped.st_mode):
                raise ValueError('runtime directory changed')
            continue
        if kind == 'symlink':
            if (not stat.S_ISLNK(before.st_mode) or os.readlink(source) != row['target']
                    or not stat.S_ISREG(mapped.st_mode) or mapped.st_size != len(row['target'].encode())
                    or mapped.st_size > 4096 or target.read_bytes() != row['target'].encode()):
                raise ValueError('runtime symlink changed or encoded view used as source')
        elif kind == 'file':
            if (not stat.S_ISREG(before.st_mode) or not stat.S_ISREG(mapped.st_mode)
                    or before.st_size != row['size'] or mapped.st_size != row['size']
                    or digest(source) != row['sha256']):
                raise ValueError('runtime bytes changed')
            if (before.st_dev, before.st_ino) != (mapped.st_dev, mapped.st_ino) and digest(target) != row['sha256']:
                raise ValueError('mapped runtime bytes changed')
        else:
            raise ValueError('unsupported runtime member')
        if snapshot(before) != snapshot(source.lstat()) or snapshot(mapped) != snapshot(target.lstat()):
            raise ValueError('runtime changed during verification')
    return metadata.hexdigest()


def bound_runtime(tree, materialization, view_receipt):
    receipt, view = load(materialization), load(view_receipt)
    if (receipt.get('status') != 'PASS' or receipt.get('installation_scripts_executed') is not False
            or receipt.get('archive_audit', {}).get('status') != 'PASS'
            or receipt.get('tree_manifest_sha256') != digest(tree)
            or view.get('status') != 'PASS_VIEW_PREPARED'
            or view.get('security_model') != 'mapped-file' or view.get('readonly_required') is not True
            or view.get('source_tree_sha256') != digest(tree)
            or view.get('receipt_sha256') != digest(materialization)):
        raise ValueError('runtime receipts do not bind the same authenticated tree')
    runtime, mapped = Path(view['runtime']), Path(view['root'])
    metadata = verify_tree(runtime, tree, mapped)
    return runtime, mapped, metadata


def cache_file(path):
    path = regular(path, LIMIT)
    with path.open('rb') as stream:
        header = stream.read(48)
    if len(header) != 48 or not header.startswith(b'glibc-ld.so.cache1.1'):
        raise ValueError('invalid target linker cache header')
    return path


def run(command, log, deadline=30):
    def limits():
        resource.setrlimit(resource.RLIMIT_AS, (512*1024**2,)*2)
        resource.setrlimit(resource.RLIMIT_FSIZE, (8*1024**2,)*2)
    start = time.monotonic()
    with log.open('xb') as stream:
        child = subprocess.Popen(command, stdout=stream, stderr=subprocess.STDOUT,
                                 start_new_session=True, preexec_fn=limits)
        try:
            rc = child.wait(timeout=deadline)
        finally:
            try:
                os.killpg(child.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            child.wait(timeout=5)
    row = {'command': command, 'exit_status': rc, 'seconds': time.monotonic()-start,
           'log': identity(log)}
    if rc:
        raise ValueError('target cache command failed; see ' + str(log))
    return row


def prepare(tree, materialization, view_receipt, emulator, output):
    start = time.monotonic()
    runtime, view, metadata = bound_runtime(tree, materialization, view_receipt)
    emulator = regular(emulator)
    output = output.absolute()
    if (output.exists() or output.is_symlink() or output.resolve().is_relative_to(runtime.resolve())
            or output.resolve().is_relative_to(view.resolve()) or shutil.disk_usage(output.parent).free < RESERVE+16*LIMIT):
        raise ValueError('fresh disk output outside retained runtime with 3 GiB reserve required')
    output.mkdir(mode=0o700)
    scratch = output/'scratch'; scratch.mkdir()
    tools = {name: identity(path) for name, path in [('qemu', emulator), ('bwrap', Path(shutil.which('bwrap') or '')),
                                                   ('ldconfig', runtime/'usr/bin/ldconfig'),
                                                   ('loader', runtime/'usr/lib/ld-linux-aarch64.so.1')]}
    # Explicit emulator execution, independent of host binfmt registrations.
    base = ['bwrap', '--unshare-all', '--die-with-parent', '--new-session', '--ro-bind', str(runtime), '/',
            '--tmpfs', '/opt', '--ro-bind', str(emulator), '/opt/qemu', '--proc', '/proc', '--dev', '/dev',
            '--clearenv', '--setenv', 'PATH', '/usr/bin', '--setenv', 'LC_ALL', 'C']
    steps = [run(base+['--bind', str(scratch), '/run', '--tmpfs', '/var', '--dir', '/var/cache/ldconfig',
                      '--', '/opt/qemu', '/usr/bin/ldconfig', '-X', '-C', '/run/ld.so.cache'], output/'generate.log')]
    cache = cache_file(scratch/'ld.so.cache')
    if (output/'generate.log').stat().st_size:
        raise ValueError('unexpected linker-cache generation diagnostics')
    consume = base+['--tmpfs', '/etc', '--ro-bind', str(cache), '/etc/ld.so.cache']
    steps.append(run(consume+['--', '/opt/qemu', '/usr/bin/ldconfig', '-p'], output/'inventory.log'))
    entries = (output/'inventory.log').read_text().splitlines()
    if not entries or ' libs found in cache ' not in entries[0]:
        raise ValueError('target cache inventory unavailable')
    consumers = {}
    for app in ('mousepad', 'foot'):
        log = output/(app+'.log')
        steps.append(run(consume+['--setenv', 'LD_DEBUG', 'libs', '--', '/opt/qemu',
                                  '/usr/lib/ld-linux-aarch64.so.1', '--list', '/usr/bin/'+app], log))
        data = log.read_text()
        if 'search cache=/etc/ld.so.cache' not in data or 'not found' in data:
            raise ValueError('target loader did not consume cache successfully')
        consumers[app] = {'cache_searches': data.count('search cache=/etc/ld.so.cache'), 'log': identity(log)}
    if verify_tree(runtime, tree, view) != metadata:
        raise ValueError('mapped metadata changed during generation')
    for item in tools.values():
        if digest(item['path']) != item['sha256']:
            raise ValueError('tool changed during generation')
    target = output/'ld.so.cache'
    with cache.open('rb') as source, target.open('xb') as dest:
        shutil.copyfileobj(source, dest)
    target.chmod(0o600)
    record = {'schema': 1, 'status': 'PASS_TARGET_CACHE_PREPARED', 'authority': 'none', 'physical_status': 'NOT RUN',
              'runtime': str(runtime), 'view': str(view), 'view_metadata_sha256': metadata, 'tree': identity(tree),
              'materialization': identity(materialization), 'view_receipt': identity(view_receipt),
              'preparer_sha256': digest(Path(__file__)), 'tools': tools, 'cache': identity(target),
              'consumers': consumers, 'steps': steps, 'seconds': time.monotonic()-start,
              'authentication': 'retained authenticated package receipt; every runtime byte/symlink rechecked; signatures not rerun'}
    (output/'result.json').write_text(json.dumps(record, indent=2)+'\n')
    return record


def validate(directory, runtime, view_receipt):
    record = load(directory/'result.json')
    if (record.get('status') != 'PASS_TARGET_CACHE_PREPARED' or record.get('authority') != 'none'
            or record.get('preparer_sha256') != digest(Path(__file__))
            or record.get('view') != str(runtime)
            or record.get('view_receipt', {}).get('sha256') != digest(view_receipt)):
        raise ValueError('cache does not bind this preparer and VM runtime')
    for key in ('tree', 'materialization', 'view_receipt'):
        item = record[key]
        if digest(regular(item['path'])) != item['sha256']:
            raise ValueError('cache input receipt changed')
    original, mapped, metadata = bound_runtime(Path(record['tree']['path']), Path(record['materialization']['path']), view_receipt)
    if (original != Path(record['runtime']) or mapped != runtime
            or metadata != record.get('view_metadata_sha256')):
        raise ValueError('cache runtime path mismatch')
    cache = cache_file(directory/'ld.so.cache')
    if digest(cache) != record['cache']['sha256']:
        raise ValueError('cache bytes changed')
    for app in ('mousepad', 'foot'):
        item = record['consumers'][app]
        log = regular(item['log']['path'], 8*LIMIT)
        if item['cache_searches'] < 1 or digest(log) != item['log']['sha256']:
            raise ValueError('target consumer evidence changed')
    return record


def stage(directory, runtime, view_receipt, destination):
    record = validate(directory, runtime, view_receipt)
    target = destination/'linker-cache'
    with (directory/'ld.so.cache').open('rb') as source, target.open('xb') as output:
        shutil.copyfileobj(source, output)
    if digest(target) != record['cache']['sha256']:
        raise ValueError('cache changed during staging')
    target.chmod(0o644)
    with (destination/'linker-cache.sha256').open('x') as stream:
        stream.write(record['cache']['sha256']+'\n')
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('tree', 'materialization', 'view-receipt', 'emulator', 'output'):
        parser.add_argument('--'+name, type=Path, required=True)
    args = parser.parse_args()
    def interrupted(_number, _frame):
        raise InterruptedError('cache preparation interrupted')
    signal.signal(signal.SIGTERM, interrupted)
    signal.signal(signal.SIGINT, interrupted)
    record = prepare(args.tree, args.materialization, args.view_receipt, args.emulator, args.output)
    print(json.dumps({key: record[key] for key in ('status', 'cache', 'seconds')}))


if __name__ == '__main__':
    main()
