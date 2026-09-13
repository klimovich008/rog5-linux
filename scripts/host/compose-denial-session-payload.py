#!/usr/bin/env python3
"""Compose a deterministic, unsigned Denial session-files archive; never install.

Consumes the exact non-root VM payload inventory and retained CLI build receipt.
No package hooks, accounts, service activation, device selection or signing.
"""
import argparse
import gzip
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import stat
import subprocess
import tarfile
import time

BASE = '85b2303e2f09ae7b7b993641f90061a200f03d53'
RESERVE = 3 * 1024**3
REPO = Path(__file__).resolve().parents[2]


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def safe_name(name):
    path = PurePosixPath(name)
    if not name or path.is_absolute() or path.as_posix() != name or '..' in path.parts:
        raise ValueError('unsafe archive member: '+name)
    return name


def regular(path):
    if path.is_symlink() or not stat.S_ISREG(path.stat().st_mode):
        raise ValueError('source must be a regular non-symlink file: '+str(path))
    return path


def file_member(source, destination, expected):
    regular(source)
    if expected['mode'] not in ('0o644', '0o755'):
        raise ValueError('unexpected payload permissions')
    return {'name': safe_name(destination), 'path': source,
            'size': expected['bytes'], 'mode': int(expected['mode'], 8),
            'sha256': expected['sha256']}


def bytes_member(destination, data, mode=0o644):
    return {'name': safe_name(destination), 'data': data, 'size': len(data),
            'mode': mode, 'sha256': hashlib.sha256(data).hexdigest()}


def plan(args):
    for source in (args.flutter_bundle, args.denial_source):
        if args.output.resolve().is_relative_to(source.resolve()):
            raise ValueError('output must be outside immutable source trees')
    qualification = json.loads(args.qualification.read_text())
    if qualification['status'] != 'PASS_NONROOT_VM_SESSION':
        raise ValueError('matching successful non-root VM qualification required')
    inventory = qualification['final_session']['payload']
    required = {'deniald','flutter/lib/libapp.so','flutter/lib/libflutter_engine.so',
                'flutter/data/icudtl.dat'}
    if not required <= inventory.keys():
        raise ValueError('required session files are missing from the inventory')
    if 'deniald' not in inventory or any(n != 'deniald' and not n.startswith('flutter/') for n in inventory):
        raise ValueError('unexpected VM payload inventory')
    bundle = args.flutter_bundle
    if bundle.is_symlink() or not bundle.is_dir():
        raise ValueError('bundle must be a non-symlink directory')
    actual = set()
    for path in bundle.rglob('*'):
        if path.is_symlink():
            raise ValueError('symlink in Flutter bundle')
        if path.is_file():
            actual.add('flutter/'+path.relative_to(bundle).as_posix())
        elif not path.is_dir():
            raise ValueError('special object in Flutter bundle')
    if actual != set(inventory)-{'deniald'}:
        raise ValueError('bundle differs from qualified file set')
    members = [file_member(args.deniald, 'usr/bin/deniald', inventory['deniald'])]
    for name in sorted(actual):
        safe_name(name)
        members.append(file_member(bundle/name.removeprefix('flutter/'),
                                   'usr/lib/denial/'+name, inventory[name]))
    cli = json.loads(args.cli_receipt.read_text())
    if cli['status'] != 'ARM64_NATIVE_CLI_PASS' or cli['source_commit'] != BASE:
        raise ValueError('pinned ARM64 control-client receipt required')
    control = [r for r in cli['artifacts'] if r['name'] == 'denialctl']
    if len(control) != 1 or any(r['returncode'] != 0 for r in control[0]['checks']):
        raise ValueError('control-client checks did not pass')
    row = control[0]
    members.append(file_member(args.denialctl, 'usr/bin/denialctl',
                               {'sha256':row['sha256'], 'bytes':row['size'], 'mode':'0o755'}))
    for original, target, mode in (
        ('packaging/arch/denial-session', 'usr/bin/denial-session', 0o755),
        ('packaging/denial-session.target', 'usr/lib/systemd/user/denial-session.target', 0o644),
    ):
        data = subprocess.check_output(['git', '-C', str(args.denial_source), 'show',
                                       f'{BASE}:{original}'], timeout=10)
        members.append(bytes_member(target, data, mode))
    for original, target, mode in (
        ('packaging/arch/mobile/denial-mobile-session', 'usr/bin/denial-mobile-session', 0o755),
        ('packaging/arch/mobile/denial-mobile.desktop', 'usr/share/wayland-sessions/denial-mobile.desktop', 0o644),
        ('configs/mobile/session-policy.json', 'usr/share/doc/rog5-denial/session-policy.json', 0o644),
    ):
        members.append(bytes_member(target, (REPO/original).read_bytes(), mode))
    if len({m['name'] for m in members}) != len(members):
        raise ValueError('duplicate destination')
    metadata = {'schema':1, 'kind':'unsigned session files, not a rootfs or boot candidate',
                'authority':'none', 'physical_status':'NOT RUN', 'denial_upstream_commit':BASE,
                'qualification_sha256':digest(args.qualification),
                'cli_receipt_sha256':digest(args.cli_receipt),
                'files':[{k:v for k,v in m.items() if k not in ('path','data')} for m in members],
                'requires':['authenticated ARM64 package closure and original PAM helper permissions',
                            'non-conflicting mobile UID/GID1000 and authenticated local logind session',
                            'reviewed explicit KMS/render nodes and qualified60Hz output configuration',
                            'default-off remote services and separate installation/admission authority']}
    members.append(bytes_member('usr/share/rog5-denial/payload.json',
                                (json.dumps(metadata, sort_keys=True, indent=2)+'\n').encode()))
    return members, metadata


class Sink:
    def __init__(self, stream=None, reserve_path=None):
        self.stream, self.reserve_path = stream, reserve_path
        self.size = 0
        self.hasher = hashlib.sha256()

    def write(self, data):
        if self.reserve_path and shutil.disk_usage(self.reserve_path).free < RESERVE+len(data):
            raise ValueError('3 GiB disk reserve reached')
        if self.stream:
            self.stream.write(data)
        self.size += len(data)
        self.hasher.update(data)
        return len(data)

    def flush(self):
        if self.stream:
            self.stream.flush()


class CheckedReader:
    def __init__(self, stream):
        self.stream = stream
        self.hasher = hashlib.sha256()

    def read(self, size):
        data = self.stream.read(size)
        self.hasher.update(data)
        return data


def archive(members, sink):
    directories = set()
    for member in members:
        directories.update(p.as_posix() for p in PurePosixPath(member['name']).parents if str(p) != '.')
    entries = {m['name']:m for m in members}
    if len(entries) != len(members):
        raise ValueError('duplicate archive destination')
    with gzip.GzipFile(filename='', mode='wb', fileobj=sink, mtime=0, compresslevel=6) as compressed:
        with tarfile.open(fileobj=compressed, mode='w|', format=tarfile.USTAR_FORMAT) as tar:
            for name in sorted(directories | entries.keys()):
                info = tarfile.TarInfo(name)
                info.uid = info.gid = info.mtime = 0
                if name in directories:
                    if name in entries:
                        raise ValueError('file/directory collision')
                    info.type, info.mode = tarfile.DIRTYPE, 0o755
                    tar.addfile(info)
                    continue
                row = entries[name]
                info.size, info.mode = row['size'], row['mode']
                if 'data' in row:
                    stream = io.BytesIO(row['data'])
                else:
                    regular(row['path'])
                    stream = os.fdopen(os.open(row['path'], os.O_RDONLY | os.O_NOFOLLOW), 'rb')
                with stream:
                    reader = CheckedReader(stream)
                    tar.addfile(info, reader)
                    if reader.hasher.hexdigest() != row['sha256'] or stream.read(1):
                        raise ValueError('input differs from qualified bytes: '+name)
    return {'sha256':sink.hasher.hexdigest(), 'size':sink.size}


def compose(members, output):
    if output.exists() or output.is_symlink():
        raise ValueError('output must be fresh')
    # Measure and verify without writing a second full archive or copying inputs.
    measured = archive(members, Sink())
    if shutil.disk_usage(output.parent).free < RESERVE+measured['size']+1024**2:
        raise ValueError('insufficient space above 3 GiB reserve')
    output.mkdir(mode=0o700)
    partial = output/'.session.tar.gz.partial'
    try:
        with partial.open('xb') as stream:
            written = archive(members, Sink(stream, output))
            stream.flush()
            os.fsync(stream.fileno())
        if written != measured:
            raise ValueError('archive differs between measurement and publication')
        os.link(partial, output/'session.tar.gz')
    finally:
        partial.unlink(missing_ok=True)
    return written


def publish_receipt(output, result):
    partial, final = output/'.provenance.json.partial', output/'provenance.json'
    created = linked = committed = False
    try:
        with partial.open('x') as stream:
            created = True
            json.dump(result, stream, indent=2)
            stream.write('\n'); stream.flush(); os.fsync(stream.fileno())
        os.link(partial, final)
        linked = True
        partial.unlink()
        directory = os.open(output, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
        committed = True
    finally:
        if linked and not committed:
            final.unlink(missing_ok=True)
        if created:
            partial.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('qualification','cli-receipt','denial-source','deniald','denialctl','flutter-bundle','output'):
        parser.add_argument('--'+name, type=Path, required=True)
    args = parser.parse_args()
    started = time.monotonic()
    members, metadata = plan(args)
    result = compose(members, args.output)
    result.update(status='PREPARED_NOT_INSTALLED', authority='none', physical_status='NOT RUN',
                  duration_seconds=time.monotonic()-started, metadata=metadata,
                  composer_sha256=digest(Path(__file__)),
                  source_commit=subprocess.check_output(['git','-C',str(REPO),'rev-parse','HEAD'],text=True).strip(),
                  source_tree=subprocess.check_output(['git','-C',str(REPO),'rev-parse','HEAD^{tree}'],text=True).strip())
    # Consumers require this terminal receipt and matching archive bytes.
    publish_receipt(args.output, result)
    print(json.dumps({k:v for k,v in result.items() if k != 'metadata'}, indent=2))


if __name__ == '__main__':
    main()
