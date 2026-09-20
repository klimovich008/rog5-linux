#!/usr/bin/env python3
"""Assemble exact display payload ingredients in a new host directory.

No boot image, target transfer, firmware search-path change, helper execution,
admission or claim. Host ownership is not target-root qualification. The source
loader remains responsible for live identity, metadata and one-use checks.
"""
import argparse
import ast
from contextlib import ExitStack
import hashlib
import importlib.util
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import stat
import tempfile

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location('display_module_intake', HERE/'stage-production-display-modules.py')
S = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(S)
need = S.need
# Retained upstream release20260622 documentation, alongside the exact firmware.
FIRMWARE_SOURCE = 'b2722d241309a1872446c1d00c2e812bad055f89'
DOCUMENTATION = (
    ('LICENSES/LICENSE.qcom', 13962, 'be904cd28cb292b80cdb6cf412ab0d9159d431671e987ad433c1f62e0988a9bc'),
    ('LICENSES/NOTICE.qcom', 23966, 'fa43e1b9a13b341a07adca9dbe73d0f9072d7966fdfe811c01f0dd2872d7309a'),
    ('WHENCE', 449378, '855b6592910c87ba6a73c2543436830775dd0f622d4b82c0cfa6f9406bec3f64'),
)


def source_contracts():
    """Read literal contracts from actual consumers, never execute target code."""
    constants = {}; sources = {}
    for filename, wanted in (
        ('load-production-display.py', {'RELEASE', 'HELPER', 'MODULES'}),
        ('display-firmware.py', {'FIRMWARE'}),
    ):
        with (HERE/filename).open('rb') as stream:
            data = stream.read(256*1024+1)
        need(len(data) <= 256*1024, 'consumer source bound')
        found = {}
        for node in ast.parse(data).body:
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id in wanted:
                        need(target.id not in found, 'duplicate consumer contract')
                        found[target.id] = ast.literal_eval(node.value)
        need(set(found) == wanted, 'missing literal consumer contract')
        constants.update(found); sources[filename] = hashlib.sha256(data).hexdigest()
    return constants, sources


def member(name, size, digest, mode):
    path = PurePosixPath(name)
    need(type(name) is str and not path.is_absolute() and '..' not in path.parts
         and path.as_posix() == name and name not in ('', '.') , 'unsafe ingredient path')
    need(type(size) is int and 0 < size <= 32*1024*1024
         and type(digest) is str and S.HEX.fullmatch(digest), 'ingredient identity bound')
    need(mode in (0o644, 0o755), 'ingredient mode')
    return dict(path=name, bytes=size, sha256=digest, mode=mode)


def plan(expected, constants):
    S.members(expected)
    need(constants['RELEASE'] == S.RELEASE, 'loader release differs')
    actual = [(r['name'], r['path'], r['bytes'], r['sha256']) for r in expected['manifest']['modules']]
    required = list(constants['MODULES'])
    # Archive order is dependency order; the one-use loader has its own reviewed
    # activation order. Require identical identities, not identical ordering.
    need(len(actual) == len(required) and set(actual) == set(required), 'archive differs from loader cohort')
    helper = member(*constants['HELPER'])
    need(helper['path'] == 'module-once', 'unexpected helper path')
    firmware = [member('firmware/'+name, size, digest, 0o644)
                for name, size, digest in constants['FIRMWARE']]
    need(len(firmware) == 3 and len({r['path'] for r in firmware}) == 3,
         'firmware cohort differs')
    return helper, firmware


def open_input(stack, path, row):
    need(path.is_absolute() and path.resolve(strict=True) == path, 'ingredient path contains symlink')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC)
    try:
        stream = os.fdopen(fd, 'rb')
    except BaseException:
        os.close(fd)
        raise
    stack.enter_context(stream)
    before = os.fstat(stream.fileno())
    need(stat.S_ISREG(before.st_mode) and before.st_nlink == 1 and before.st_size == row['bytes'],
         'ingredient type/size/links: '+row['path'])
    need(S.consume(stream, row['bytes']) == row['sha256'] and not stream.read(1),
         'ingredient digest: '+row['path'])
    check_input(path, stream, before)
    stream.seek(0)
    return path, stream, before


def check_input(path, stream, before):
    need(S.stamp(before) == S.stamp(os.fstat(stream.fileno())) == S.stamp(path.lstat()),
         'ingredient changed')


def copy_input(target, row, stream):
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open('xb') as output:
        os.fchmod(output.fileno(), row['mode'])
        need(S.consume(stream, row['bytes'], output) == row['sha256'] and not stream.read(1),
             'ingredient changed while copying')
        output.flush(); os.fsync(output.fileno())


def assemble(archive, expected, helper_path, firmware_root, output):
    constants, sources = source_contracts()
    helper, firmware = plan(expected, constants)
    documentation = [member('firmware/'+name, size, digest, 0o644)
                     for name, size, digest in DOCUMENTATION]
    need(output.is_absolute() and not os.path.lexists(output), 'new absolute output required')
    need(output.parent.resolve(strict=True) == output.parent, 'unsafe output parent')
    stage = None
    with ExitStack() as stack:
        inputs = [(helper, open_input(stack, helper_path, helper))]
        for row in firmware + documentation:
            path = firmware_root/row['path'].removeprefix('firmware/')
            inputs.append((row, open_input(stack, path, row)))
        try:
            stage = Path(tempfile.mkdtemp(prefix='.'+output.name+'.', dir=output.parent))
            S.materialize(archive, expected, stage/'display-modules')
            for row, (path, stream, before) in inputs:
                copy_input(stage/row['path'], row, stream)
                check_input(path, stream, before)
            inventory = [member('display-modules/'+name, size, digest, 0o644)
                         for name, size, digest in S.members(expected)] + [helper] + firmware + documentation
            manifest = dict(format='rog5-production-display-payload-v1', authority='none',
                            physical='NOT RUN', activation='NOT RUN', target_ownership='NOT RUN',
                            firmware_root_transition='NOT RUN', consumer_sources=sources,
                            firmware_source_commit=FIRMWARE_SOURCE,
                            module_archive_sha256=expected['sha256'],
                            module_qualification_sha256=expected['qualification_sha256'],
                            files=sorted(inventory, key=lambda row: row['path']))
            raw = S.canonical_manifest(manifest)
            with (stage/'payload-manifest.json').open('xb') as stream:
                os.fchmod(stream.fileno(), 0o644)
                stream.write(raw); stream.flush(); os.fsync(stream.fileno())
            # Host umask must not create a group-writable future payload path.
            directories = sorted((p for p in stage.rglob('*') if p.is_dir()),
                                 key=lambda p: len(p.parts), reverse=True) + [stage]
            for directory in directories:
                os.chmod(directory, 0o700 if directory == stage else 0o755)
                fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
                try: os.fsync(fd)
                finally: os.close(fd)
            for _, (path, stream, before) in inputs:
                check_input(path, stream, before)
            need(source_contracts() == (constants, sources), 'consumer sources changed')
            S.publish(stage, output); stage = None
        finally:
            if stage is not None and stage.exists(): shutil.rmtree(stage)
    return dict(status='PASS_INERT_DISPLAY_PAYLOAD', authority='none', physical='NOT RUN',
                activation='NOT RUN', firmware_root_transition='NOT RUN',
                modules=len(constants['MODULES']), firmware_files=len(firmware),
                manifest_sha256=hashlib.sha256(raw).hexdigest(), manifest=manifest)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive', type=Path)
    parser.add_argument('--qualification', type=Path, required=True)
    parser.add_argument('--qualification-sha256', required=True)
    parser.add_argument('--helper', type=Path, required=True)
    parser.add_argument('--firmware-root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    expected = S.contract(args.qualification, args.qualification_sha256)
    print(json.dumps(assemble(args.archive.absolute(), expected, args.helper.absolute(),
                              args.firmware_root.absolute(), args.output.absolute()), sort_keys=True))


if __name__ == '__main__': main()
