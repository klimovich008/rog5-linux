#!/usr/bin/env python3
"""Make a read-only QEMU mapped-file view; reuse a trusted materialization receipt.

This is a VM fixture, not an installable runtime or a new signature audit.
Regular payload bytes are hardlinked. Never chmod, chown or write those inodes.
QEMU must receive security_model=mapped-file,readonly=on, on a read-only bind.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import stat
import tarfile
import time

RESERVE = 3 * 1024**3
META = '.virtfs_metadata'
ROOT_META = '.virtfs_metadata_root'
PACKAGE_META = {'.PKGINFO', '.BUILDINFO', '.MTREE', '.INSTALL', '.CHANGELOG'}


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def safe_name(value):
    path = PurePosixPath(value)
    if not path.parts or path.is_absolute() or '..' in path.parts or any(
            part in (META, ROOT_META) for part in path.parts):
        raise ValueError('unsafe or reserved payload path')
    return str(path)


def package_modes(packages, cache):
    modes, links = {}, {}
    for package in packages:
        archive_name = safe_name(package['archive'])
        if '/' in archive_name or package.get('status') != 'PASS':
            raise ValueError('invalid retained package audit')
        path = cache / archive_name
        if not path.is_file() or path.is_symlink() or digest(path) != package['sha256']:
            raise ValueError('archive no longer matches retained authentication')
        with tarfile.open(path, 'r|*') as archive:
            for member in archive:
                name = safe_name(member.name)
                if name in PACKAGE_META:
                    archive.members.clear()
                    continue
                if member.isdir():
                    value = (stat.S_IFDIR, (member.mode & 0o755) | 0o700)
                elif member.isfile():
                    value = (stat.S_IFREG, (member.mode & 0o755) | 0o400)
                elif member.issym():
                    value = (stat.S_IFLNK, 0o777)
                elif member.islnk():
                    links[name] = safe_name(member.linkname)
                    value = (stat.S_IFREG, None)
                else:
                    raise ValueError('special package file refused')
                if name in modes and (not member.isdir() or modes[name] != value):
                    raise ValueError('conflicting package path or directory permissions')
                modes[name] = value
                archive.members.clear()
        if digest(path) != package['sha256']:
            raise ValueError('archive changed during mode inventory')
    def resolve(name, seen):
        if name in seen or len(seen) > 64 or name not in modes:
            raise ValueError('invalid package hardlink')
        if name in links:
            target = resolve(links[name], seen | {name})
            if target[0] != stat.S_IFREG:
                raise ValueError('hardlink target is not regular')
            return target
        return modes[name]
    for name in links:
        modes[name] = resolve(name, set())
    return modes


def metadata_digest(root, rows):
    """Bind generated guest modes and symlink descriptions, not just inputs."""
    result = hashlib.sha256()
    result.update((root/ROOT_META).read_bytes())
    for row in sorted(rows, key=lambda r: r['path']):
        name = safe_name(row['path'])
        path = root/name
        entry = {'path': name, 'metadata': (path.parent/META/path.name).read_text()}
        if row['type'] == 'symlink':
            entry['symlink'] = path.read_text()
        result.update(json.dumps(entry, sort_keys=True, separators=(',', ':')).encode()+b'\n')
    return result.hexdigest()


def prepare(runtime, tree_path, receipt_path, cache, output):
    started = time.monotonic()
    if output.resolve().is_relative_to(runtime.resolve(strict=True)):
        raise ValueError('output is inside retained runtime')
    receipt = json.loads(receipt_path.read_text())
    if (receipt.get('status') != 'PASS' or receipt.get('installation_scripts_executed') is not False
            or receipt.get('archive_audit', {}).get('status') != 'PASS'
            or receipt.get('tree_manifest_sha256') != digest(tree_path)):
        raise ValueError('trusted materialization receipt does not bind this tree')
    if output.exists():
        raise ValueError('output already exists')
    rows = json.loads(tree_path.read_text())
    names = [safe_name(row['path']) for row in rows]
    if len(set(names)) != len(names):
        raise ValueError('duplicate tree path')
    # Conservative allocation allowance for independent directories, metadata
    # directory entries and stored symlink descriptions; regular bytes are shared.
    required = sum(8192 if r['type'] == 'directory' else 4096 for r in rows
                   if r['type'] != 'file') + len(rows) * 256 + 1024**2
    if shutil.disk_usage(output.parent).free < RESERVE + required:
        raise ValueError('insufficient disk for view plus 3 GiB reserve')
    modes = package_modes(receipt['archive_audit']['packages'], cache)
    by_name = dict(zip(names, rows, strict=True))
    for name, row in by_name.items():
        if row['type'] not in ('directory', 'file', 'symlink'):
            raise ValueError('unexpected manifest type')
        for parent in PurePosixPath(name).parents:
            if str(parent) != '.' and by_name.get(str(parent), {}).get('type') != 'directory':
                raise ValueError('manifest parent is not a directory')
        if name not in modes:
            if row['type'] != 'directory':
                raise ValueError('payload missing from authenticated archives')
            modes[name] = (stat.S_IFDIR, 0o755)  # implicit extraction parent
        expected_type = {'directory': stat.S_IFDIR, 'file': stat.S_IFREG, 'symlink': stat.S_IFLNK}[row['type']]
        if modes[name][0] != expected_type:
            raise ValueError('archive/manifest type mismatch')
    if not set(modes) <= set(names):
        raise ValueError('authenticated package path missing from tree')
    output.mkdir(mode=0o700)
    root = output/'root'; root.mkdir(mode=0o700)
    shared = output/'metadata'; shared.mkdir(mode=0o700)
    def metadata(path, kind, mode):
        key = str(kind | mode)
        source = shared/key
        if not source.exists():
            source.write_text(f'virtfs.uid=0\nvirtfs.gid=0\nvirtfs.mode={kind | mode}\nvirtfs.rdev=0\n')
            source.chmod(0o600)
        path.parent.mkdir(mode=0o700, exist_ok=True)
        os.link(source, path)
    metadata(root/ROOT_META, stat.S_IFDIR, 0o755)
    counts = {'file': 0, 'directory': 0, 'symlink': 0}
    for name in sorted(names, key=lambda n: (len(PurePosixPath(n).parts), n)):
        if shutil.disk_usage(output).free < RESERVE + 16384:
            raise ValueError('disk reserve reached')
        row = by_name[name]; source = runtime/name; target = root/name
        before = source.lstat()
        if stat.S_IMODE(before.st_mode) != row['mode']:
            raise ValueError('retained source mode changed')
        if row['type'] == 'directory':
            if not stat.S_ISDIR(before.st_mode):
                raise ValueError('source directory changed')
            target.mkdir(mode=0o700)
        elif row['type'] == 'file':
            if not stat.S_ISREG(before.st_mode) or before.st_size != row['size']:
                raise ValueError('retained file type/size changed')
            sha = digest(source)
            after = source.lstat()
            stable = ('st_dev', 'st_ino', 'st_size', 'st_mode', 'st_uid', 'st_gid', 'st_mtime_ns', 'st_ctime_ns')
            if sha != row['sha256'] or any(getattr(before, k) != getattr(after, k) for k in stable):
                raise ValueError('retained file changed')
            os.link(source, target, follow_symlinks=False)
            if target.lstat().st_ino != before.st_ino or source.lstat().st_ino != before.st_ino:
                raise ValueError('retained file replaced while linking')
        else:
            if not stat.S_ISLNK(before.st_mode) or os.readlink(source) != row['target']:
                raise ValueError('retained symlink changed')
            # mapped-file represents guest symlinks as ordinary host files.
            target.write_bytes(row['target'].encode()); target.chmod(0o600)
        metadata(target.parent/META/target.name, *modes[name])
        counts[row['type']] += 1
    result = {'status': 'PASS_VIEW_PREPARED', 'authority': 'none', 'physical_status': 'NOT RUN',
              'scope': 'read-only QEMU mapped-file fixture; guest execution NOT RUN',
              'security_model': 'mapped-file', 'readonly_required': True,
              'permission_policy': 'package-read; guest ownership root:root; no privileged mode bits',
              'authentication': 'reused trusted materialization receipt; archive hashes rechecked, signatures not rerun',
              'source_tree_sha256': digest(tree_path), 'receipt_sha256': digest(receipt_path),
              'guest_metadata_sha256': metadata_digest(root, rows),
              'preparer_sha256': digest(Path(__file__)), 'counts': counts,
              'runtime': str(runtime), 'root': str(root),
              'source_inode_changes': 'hardlinks change nlink/ctime; reads may change atime; no chmod/chown/xattr/content writes',
              'duration_seconds': time.monotonic()-started}
    (output/'result.json').write_text(json.dumps(result, indent=2)+'\n')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('runtime', 'tree', 'receipt', 'cache', 'output'):
        parser.add_argument('--'+name, type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(prepare(args.runtime, args.tree, args.receipt, args.cache, args.output), indent=2))


if __name__ == '__main__':
    main()
