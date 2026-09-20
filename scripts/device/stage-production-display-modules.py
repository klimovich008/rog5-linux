#!/usr/bin/env python3
"""Verify and materialize a qualified inert module archive into a new host directory.

No tar extraction API, module/helper execution, service, device I/O or claim.
A pinned offline qualification is input evidence, never activation authority.
"""
import argparse
import ctypes
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import tarfile
import tempfile

RELEASE = '7.1.4-rog5-production'
PREFIX = 'modules/lib/modules/' + RELEASE + '/kernel/'
ROOTS = {'qcom_refgen_regulator', 'gpucc_sm8350', 'panel_asus_rog5_ams678', 'msm'}
HEX = re.compile(r'[0-9a-f]{64}\Z')
MAX_ARCHIVE = 130 * 1024 * 1024


def need(ok, why):
    if not ok: raise ValueError(why)


def unique(pairs):
    result = {}
    for key, value in pairs:
        need(key not in result, 'duplicate JSON key')
        result[key] = value
    return result


def stamp(st):
    return st.st_dev, st.st_ino, st.st_mode, st.st_uid, st.st_gid, st.st_nlink, st.st_size, st.st_mtime_ns, st.st_ctime_ns


def contract(qualification, expected_digest):
    need(type(expected_digest) is str and HEX.fullmatch(expected_digest), 'qualification hash required')
    fd = os.open(qualification, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC)
    with os.fdopen(fd, 'rb') as stream:
        before = os.fstat(stream.fileno())
        need(stat.S_ISREG(before.st_mode) and 0 < before.st_size <= 2*1024*1024, 'qualification type/size')
        data = stream.read(2*1024*1024+1)
        need(hashlib.sha256(data).hexdigest() == expected_digest, 'qualification digest mismatch')
        need(stamp(before) == stamp(os.fstat(stream.fileno())) == stamp(qualification.lstat()), 'qualification changed')
    record = json.loads(data, object_pairs_hook=unique)
    need(record['status'] == 'PASS_OFFLINE_INERT_MODULE_PACKAGING' and record['authority'] == 'none'
         and record['physical'] == 'NOT RUN', 'offline packaging qualification required')
    build = record['build']; runs = build['runs']
    need(build['status'] == 'PASS_INERT_ARCHIVE_TWINS' and len(runs) == 2
         and all(row['exit_status'] == 0 for row in runs), 'successful twin packaging required')
    need(runs[0]['sha256'] == runs[1]['sha256'] and runs[0]['bytes'] == runs[1]['bytes'], 'packaging twins differ')
    manifest = record['embedded_manifest']
    raw = canonical_manifest(manifest)
    need(hashlib.sha256(raw).hexdigest() == runs[0]['embedded_manifest_sha256']
         == runs[1]['embedded_manifest_sha256'], 'embedded manifest binding mismatch')
    return dict(sha256=runs[0]['sha256'], bytes=runs[0]['bytes'], manifest=manifest,
                qualification_sha256=expected_digest)


def canonical_manifest(manifest):
    return (json.dumps(manifest, sort_keys=True, indent=2)+'\n').encode()


def members(expected):
    """Only canonical builder output is supported, not arbitrary tar syntax."""
    need(type(expected['bytes']) is int and 0 < expected['bytes'] <= MAX_ARCHIVE
         and type(expected['sha256']) is str and HEX.fullmatch(expected['sha256']), 'archive identity bound')
    m = expected['manifest']
    need(m['format'] == 'rog5-production-display-modules-v1' and m['release'] == RELEASE
         and m['authority'] == 'none' and m['physical'] == 'NOT RUN', 'inert production manifest required')
    need(set(m['roots']) == ROOTS and len(m['roots']) == len(ROOTS), 'unexpected module roots')
    need(type(m['modules']) is list and 4 <= len(m['modules']) <= 64, 'module count bound')
    result = []; seen_paths = set(); seen_names = set(); total = 0
    for row in m['modules']:
        name = row['path']; p = PurePosixPath(name)
        need(type(name) is str and name.startswith(PREFIX) and name.endswith('.ko')
             and p.as_posix() == name and '..' not in p.parts
             and re.fullmatch(r'[A-Za-z0-9_./-]+', name), 'unsafe module member path')
        normalized = row['name'].replace('-', '_')
        need(normalized == p.stem.replace('-', '_') and normalized not in seen_names
             and name not in seen_paths, 'duplicate/mismatched module identity')
        need(type(row['bytes']) is int and 0 < row['bytes'] <= 64*1024*1024
             and HEX.fullmatch(row['sha256']), 'module size/hash bound')
        need(row['vermagic'] == RELEASE+' SMP preempt mod_unload aarch64', 'module vermagic')
        # The archive's reviewed order is dependencies-first, never a runnable
        # hardware activation sequence. Reject a reordered/foreign contract.
        need(type(row['dependencies']) is list and set(row['dependencies']) <= seen_paths,
             'dependency absent or after consumer')
        total += row['bytes']; need(total <= 128*1024*1024, 'module byte bound')
        seen_paths.add(name); seen_names.add(normalized)
        result.append((name, row['bytes'], row['sha256']))
    need(ROOTS <= seen_names, 'required module root missing')
    raw = canonical_manifest(m); need(len(raw) <= 1024*1024, 'manifest byte bound')
    result.append(('manifest.json', len(raw), hashlib.sha256(raw).hexdigest()))
    return result


def header(name, size):
    entry = tarfile.TarInfo(name); entry.size = size; entry.mode = 0o644
    return entry.tobuf(format=tarfile.USTAR_FORMAT)


def consume(stream, size, output=None):
    digest = hashlib.sha256()
    while size:
        data = stream.read(min(size, 65536))
        need(data, 'truncated archive member')
        digest.update(data); size -= len(data)
        if output is not None: output.write(data)
    return digest.hexdigest()


def verify(stream, expected):
    plan = members(expected)
    stream.seek(0)
    need(consume(stream, expected['bytes']) == expected['sha256'], 'archive digest mismatch')
    need(not stream.read(1), 'archive larger than expected')
    stream.seek(0); offsets = []
    for name, size, digest in plan:
        need(stream.read(512) == header(name, size), 'noncanonical/unexpected archive header: ' + name)
        offset = stream.tell()
        need(consume(stream, size) == digest, 'archive member digest mismatch: ' + name)
        padding = (-size) % 512
        need(stream.read(padding) == bytes(padding), 'nonzero/truncated member padding')
        offsets.append((name, offset, size, digest))
    padded = ((stream.tell() + 1024 + 10239)//10240)*10240
    need(padded == expected['bytes'], 'archive length/trailing record mismatch')
    remaining = padded-stream.tell()
    while remaining:
        amount = min(remaining, 65536)
        need(stream.read(amount) == bytes(amount), 'nonzero/truncated archive end')
        remaining -= amount
    need(not stream.read(1), 'extra data after archive')
    return offsets


def publish(stage, output):
    # Atomic directory publication, never replace another artifact or writer.
    libc = ctypes.CDLL(None, use_errno=True)
    rename = libc.renameat2
    rename.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
    rename.restype = ctypes.c_int
    if rename(-100, os.fsencode(stage), -100, os.fsencode(output), 1):
        raise OSError(ctypes.get_errno(), 'exclusive module-directory publication failed')
    fd = os.open(output.parent, os.O_RDONLY | os.O_DIRECTORY)
    try: os.fsync(fd)
    finally: os.close(fd)


def materialize(archive, expected, output):
    need(not os.path.lexists(output), 'output already exists')
    need(output.parent.resolve(strict=True) == output.parent, 'unsafe output parent')
    fd = os.open(archive, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC)
    stage = None
    try:
        with os.fdopen(fd, 'rb') as stream:
            before = os.fstat(stream.fileno())
            need(stat.S_ISREG(before.st_mode) and before.st_size == expected['bytes']
                 and 0 < before.st_size <= MAX_ARCHIVE, 'archive type/size')
            offsets = verify(stream, expected)
            need(stamp(before) == stamp(os.fstat(stream.fileno())) == stamp(archive.lstat()), 'archive changed during verification')
            # No output or staging directory exists until every member validates.
            stage = Path(tempfile.mkdtemp(prefix='.'+output.name+'.', dir=output.parent))
            for name, offset, size, digest in offsets:
                target = stage/name; target.parent.mkdir(parents=True, exist_ok=True)
                stream.seek(offset)
                member_fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC, 0o644)
                with os.fdopen(member_fd, 'wb') as member:
                    os.fchmod(member.fileno(), 0o644)
                    need(consume(stream, size, member) == digest, 'archive changed during staging')
                    member.flush(); os.fsync(member.fileno())
            need(stamp(before) == stamp(os.fstat(stream.fileno())) == stamp(archive.lstat()), 'archive changed after staging')
            for directory in sorted((p for p in stage.rglob('*') if p.is_dir()), key=lambda p:len(p.parts), reverse=True)+[stage]:
                dfd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY)
                try: os.fsync(dfd)
                finally: os.close(dfd)
            publish(stage, output); stage = None
    finally:
        if stage is not None and stage.exists(): shutil.rmtree(stage)
    return dict(status='PASS_INERT_MODULE_STAGING', archive_sha256=expected['sha256'],
                qualification_sha256=expected['qualification_sha256'], modules=len(offsets)-1,
                authority='none', activation='NOT RUN', firmware='NOT PACKAGED', physical='NOT RUN')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive', type=Path)
    parser.add_argument('--qualification', type=Path, required=True)
    parser.add_argument('--qualification-sha256', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    expected = contract(args.qualification, args.qualification_sha256)
    print(json.dumps(materialize(args.archive, expected, args.output.absolute()), sort_keys=True))


if __name__ == '__main__': main()
