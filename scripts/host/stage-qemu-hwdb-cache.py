#!/usr/bin/env python3
"""Admit a retained exact-runtime target hwdb cache for an offline VM only."""
import argparse
import importlib.util
import json
import math
import os
from pathlib import Path
import shutil
import stat
import struct

SPEC = importlib.util.spec_from_file_location('linker_cache', Path(__file__).with_name('prepare-qemu-linker-cache.py'))
BASE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BASE)
PREPARER = '3694546421fb37580c90dc00c33cdf0dadb227288b6e6c4e32c85bc6a57e6610'
LIMIT = 64 * 1024**2
TOOL_PATHS = {'hwdb': 'usr/bin/systemd-hwdb',
              'unit': 'usr/lib/systemd/system/systemd-hwdb-update.service',
              'package-hook': 'usr/share/libalpm/scripts/systemd-hook'}
QUERY = 'ID_VENDOR_FROM_DATABASE=Logitech, Inc.\nID_MODEL_FROM_DATABASE=WingMan Extreme Joystick\n'


def real_path(path):
    """Refuse symlink traversal, including a symlink to a missing destination."""
    path = Path(path).absolute()
    if any(p.is_symlink() for p in (path, *path.parents)):
        raise ValueError('symlink in cache admission path: ' + str(path))
    return path


def checked(item, expected=None, maximum=LIMIT, empty=False):
    path = real_path(item['path'])
    if expected is not None and path != Path(expected).absolute():
        raise ValueError('evidence or tool path mismatch')
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or not (0 if empty else 1) <= info.st_size <= maximum:
        raise ValueError('expected bounded regular evidence')
    if BASE.digest(path) != item['sha256'] or BASE.snapshot(info) != BASE.snapshot(path.lstat()):
        raise ValueError('evidence or tool bytes changed')
    return path


def cache_file(path):
    path = BASE.regular(real_path(path), LIMIT)
    with path.open('rb') as stream:
        header = stream.read(80)
    if len(header) != 80:
        raise ValueError('truncated hwdb header')
    magic, version, size, head, node, child, value, root, nodes, strings = struct.unpack('<8s9Q', header)
    # This admission is intentionally specific to the retained systemd 261
    # generator. Header/layout checks do not replace the target consumer proof.
    if (magic != b'KSLPHHRH' or version != 261 or size != path.stat().st_size
            or (head, node, child, value) != (80, 24, 16, 32)
            or nodes < node or strings < 1 or size != head + nodes + strings
            or not head <= root <= head + nodes - node):
        raise ValueError('invalid retained hwdb header/layout')
    return path


def commands(runtime, directory, emulator):
    base = ['bwrap', '--unshare-all', '--die-with-parent', '--new-session',
            '--ro-bind', str(runtime), '/', '--tmpfs', '/opt', '--ro-bind', str(emulator), '/opt/qemu',
            '--proc', '/proc', '--dev', '/dev', '--clearenv', '--setenv', 'PATH', '/usr/bin',
            '--setenv', 'LC_ALL', 'C', '--setenv', 'SYSTEMD_COLORS', '0',
            '--bind', str(directory/'udev'), '/usr/lib/udev', '--tmpfs', '/run', '--tmpfs', '/var',
            '--', '/opt/qemu', '/usr/bin/systemd-hwdb']
    return [base + ['--usr', 'update'], base + ['query', 'usb:v046Dp0200d0000']]


def validate(directory, runtime, view_receipt):
    directory, runtime, view_receipt = map(real_path, (directory, runtime, view_receipt))
    record = BASE.load(real_path(directory/'result.json'))
    if (record.get('status') != 'PASS_TARGET_HWDB_PREPARED'
            or record.get('authority') != 'none; generic VM cache experiment'
            or record.get('physical') != 'NOT RUN' or record.get('view') != str(runtime)
            or record.get('script', {}).get('sha256') != PREPARER):
        raise ValueError('cache does not bind retained preparer and VM runtime')
    checked(record['script'])
    tree = checked(record['tree'])
    materialization = checked(record['materialization'])
    checked(record['view_receipt'], view_receipt)
    original, mapped, metadata = BASE.bound_runtime(tree, materialization, view_receipt)
    if (original != Path(record['runtime']) or mapped != runtime
            or metadata != record.get('view_metadata_sha256')):
        raise ValueError('cache runtime/metadata mismatch')
    for name in ('usr/lib/udev/hwdb.bin', 'etc/udev/hwdb.bin'):
        path = original/name
        if path.exists() or path.is_symlink():
            raise ValueError('runtime already supplies a hardware database')
    custom = real_path(original/'etc/udev/hwdb.d')
    if custom.exists() and (not custom.is_dir() or any(custom.iterdir())):
        raise ValueError('custom hardware database entries require new preparation')
    tools = record['tools']
    if set(tools) != set(TOOL_PATHS) | {'qemu', 'bwrap'}:
        raise ValueError('unexpected tool inventory')
    for name, relative in TOOL_PATHS.items():
        checked(tools[name], original/relative)
    emulator = checked(tools['qemu'])
    checked(tools['bwrap'])
    if emulator.name != 'qemu-aarch64-static' or Path(tools['bwrap']['path']).name != 'bwrap':
        raise ValueError('wrong target generation tools')
    steps = record['steps']
    if len(steps) != 2:
        raise ValueError('missing bounded generation/query evidence')
    for step, command, name in zip(steps, commands(original, directory, emulator), ('generate.log', 'query.log')):
        seconds = step.get('seconds')
        if (step.get('exit_status') != 0 or step.get('command') != command
                or isinstance(seconds, bool) or not isinstance(seconds, (int, float))
                or not math.isfinite(seconds) or not 0 <= seconds <= 50):
            raise ValueError('target generation/query did not succeed within its bound')
        checked(step['log'], directory/name, maximum=1024**2, empty=True)
    if (directory/'generate.log').stat().st_size or (directory/'query.log').read_text() != QUERY:
        raise ValueError('target generation/query diagnostics disagree')
    cache = checked(record['cache'], directory/'hwdb.bin')
    cache_file(cache)
    if type(record.get('cache_bytes')) is not int or record['cache_bytes'] != cache.stat().st_size:
        raise ValueError('cache size differs from generation receipt')
    return record


def stage(directory, runtime, view_receipt, destination):
    directory, destination = real_path(directory), real_path(destination)
    record = validate(directory, runtime, view_receipt)
    if not destination.is_dir() or any(destination.resolve().is_relative_to(Path(record[k]).resolve())
                                       for k in ('runtime', 'view')):
        raise ValueError('staging must be outside retained runtime/view')
    targets = (destination/'hwdb-cache', destination/'hwdb-cache.sha256')
    if any(p.exists() or p.is_symlink() for p in targets):
        raise FileExistsError('fresh hwdb staging outputs required')
    if shutil.disk_usage(destination).free < BASE.RESERVE + record['cache_bytes']:
        raise ValueError('staging requires 3 GiB free disk reserve')
    created = []
    try:
        with targets[0].open('xb') as output:
            created.append(targets[0]); os.chmod(targets[0], 0o600)
            descriptor = os.open(directory/'hwdb.bin', os.O_RDONLY | os.O_NOFOLLOW)
            with os.fdopen(descriptor, 'rb') as source:
                remaining = record['cache_bytes']
                while remaining:
                    chunk = source.read(min(1024**2, remaining))
                    if not chunk:
                        raise ValueError('cache truncated during staging')
                    output.write(chunk); remaining -= len(chunk)
                if source.read(1):
                    raise ValueError('cache grew during staging')
        if BASE.digest(targets[0]) != record['cache']['sha256']:
            raise ValueError('cache changed during staging')
        cache_file(targets[0])
        with targets[1].open('x') as output:
            created.append(targets[1]); os.chmod(targets[1], 0o600)
            output.write(record['cache']['sha256']+'\n')
    except BaseException:
        for path in reversed(created):
            path.unlink()
        raise
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('directory', 'runtime', 'view-receipt', 'destination'):
        parser.add_argument('--'+name, type=Path, required=True)
    args = parser.parse_args()
    record = stage(args.directory, args.runtime, args.view_receipt, args.destination)
    print(json.dumps({'status': 'PASS_HWDB_CACHE_STAGED', 'authority': 'none',
                      'cache_sha256': record['cache']['sha256'], 'physical': 'NOT RUN'}))


if __name__ == '__main__':
    main()
