#!/usr/bin/env python3
"""Carry two exact display modules into RAM without loading or enabling them.

Compose over a caller-pinned current-kernel archive with the qualified corrected
buttons payload. The historical signed V9 payload is deliberately not upgraded
or accepted as that corrected payload by this tool.
"""
import argparse
import gzip
import importlib.util
import json
import os
from pathlib import Path
import re
import stat

REPO = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    'display_buttons', REPO/'scripts/device/build-buttons-indicator-trial-initramfs.py')
BUTTONS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BUTTONS)
ARCHIVE = BUTTONS.ARCHIVE
PERSISTENT = BUTTONS.PERSISTENT
require, sha = BUTTONS.require, BUTTONS.sha
RELEASE, PREFIX, CATALOG = BUTTONS.RELEASE, BUTTONS.PREFIX, BUTTONS.CATALOG
PAYLOAD_PREFIX = PREFIX+'display-trial/'
PAYLOAD = {
    'qcom-refgen-regulator.ko': (338408, 'f0ee47b2f1f5b7bd70fe1c486322a04f6509be04c58c10ecb5890d82a2272fc6', 0o644),
    'panel-asus-rog5-ams678.ko': (395528, '5bacaed0279d6e94b08003cc4dfb35f8eb17c33f643190ceef78ef40aa7f0f6c', 0o644),
}
DISPLAY_OPT_IN = ('screen-toggle.sh', 'status-screen.sh', 'power-buttond.py',
                  'qcom-pon.ko', 'units/rog5-status-screen.service',
                  'units/rog5-power-button.service', 'display-diagnostic')


def validate_payload(payload):
    require(set(payload) == set(PAYLOAD), 'display payload inventory mismatch')
    for name, (size, expected, _) in PAYLOAD.items():
        data = payload[name]
        require(type(data) is bytes and len(data) == size and sha(data) == expected,
                'display payload identity mismatch: '+name)


def validate_buttons(members):
    prefix = BUTTONS.PAYLOAD_PREFIX
    expected = {prefix[:-1]} | {prefix+n for n in BUTTONS.PAYLOAD}
    present = {n for n in members if n == prefix[:-1] or n.startswith(prefix)}
    require(present == expected, 'corrected buttons payload inventory mismatch')
    payload = {}
    for path in expected:
        fields, data = members[path]
        if path == prefix[:-1]:
            mode, links, size = stat.S_IFDIR | 0o755, 2, 0
        else:
            name = path[len(prefix):]
            size, _, permissions = BUTTONS.PAYLOAD[name]
            mode, links = stat.S_IFREG | permissions, 1
            payload[name] = data
        require(fields[1:] == [mode, 0, 0, links, ARCHIVE.EPOCH, size,
                0, 0, 0, 0, len(path.encode())+1, 0] and len(data) == size,
                'corrected buttons payload metadata mismatch: '+path)
    BUTTONS.validate_payload(payload)


def compose(base, expected_base, descriptor, payload):
    require(sha(base) == expected_base, 'base hash mismatch')
    validate_payload(payload)
    original = ARCHIVE.entries(gzip.decompress(base))
    for name in (PREFIX+'kernel-release', CATALOG):
        require(name in original and original[name][0][1:5] ==
                [stat.S_IFREG | 0o444, 0, 0, 1], 'base metadata mismatch: '+name)
    require(original[PREFIX+'kernel-release'][1] == (RELEASE+'\n').encode(),
            'current kernel release mismatch')
    require(original[CATALOG][1] == BUTTONS.catalog(original), 'base catalog mismatch')
    validate_buttons(original)
    shutdown = original.get('shutdown')
    require(shutdown is not None and shutdown[0][1:5] == [stat.S_IFREG | 0o755, 0, 0, 1]
            and sha(shutdown[1]) == BUTTONS.SHUTDOWN_SHA256,
            'corrected shutdown identity mismatch')
    runtime = original.get(PREFIX+'runtime')
    require(runtime is not None and runtime[0][1:5] == [stat.S_IFREG | 0o755, 0, 0, 1]
            and runtime[1] == (REPO/'initramfs/native-wifi/runtime').read_bytes(),
            'current runtime identity mismatch')
    require(not any(PREFIX+n in original for n in DISPLAY_OPT_IN),
            'base contains display activation opt-in')
    require(not any(n == PAYLOAD_PREFIX[:-1] or n.startswith(PAYLOAD_PREFIX)
                    for n in original), 'display payload already exists')
    # Identity-only successor: any source radio/probe mismatch is refused by
    # the comparison below rather than silently refreshed as another change.
    intermediate, _ = PERSISTENT.compose_successor(
        base, expected_base, descriptor, ARCHIVE.TRIAL_HELPER.read_bytes())
    members = ARCHIVE.entries(gzip.decompress(intermediate))
    allowed = {PREFIX+'trial-descriptor', CATALOG}
    require(set(members) == set(original), 'unexpected successor inventory')
    for name, entry in original.items():
        require(name in allowed or members[name] == entry,
                'unexpected successor change: '+name)
    for name in sorted(PAYLOAD):
        ARCHIVE.add(members, PAYLOAD_PREFIX+name, payload[name],
                    stat.S_IFREG | PAYLOAD[name][2])
    ARCHIVE.replace(members, CATALOG, BUTTONS.catalog(members))
    added = {PAYLOAD_PREFIX[:-1]} | {PAYLOAD_PREFIX+n for n in PAYLOAD}
    require(set(members)-set(original) == added, 'unexpected final inventory')
    for name, entry in original.items():
        require(name in allowed or members[name] == entry,
                'unexpected final change: '+name)
    ARCHIVE.verify_radio_composition(members)
    packed = gzip.compress(ARCHIVE.encode(members), compresslevel=1, mtime=0)
    require(ARCHIVE.entries(gzip.decompress(packed)) == members, 'archive round-trip mismatch')
    return packed, {'status': 'PASS', 'base_sha256': expected_base, 'sha256': sha(packed),
                    'kernel_release': RELEASE, 'trial': ARCHIVE.parse_trial_descriptor(descriptor),
                    'changed_existing_members': sorted(allowed), 'added_members': sorted(added),
                    'payload_sha256': {n: sha(payload[n]) for n in sorted(payload)},
                    'corrected_buttons_payload': 'preserved unchanged',
                    'activation': 'none added; nested payload and canonical headless installer',
                    'paired_root_autoload_absence': 'NOT VERIFIED; final paired-root check required',
                    'kernel_rebuilt': False, 'arch_root_rebuilt': False,
                    'authority': 'unsigned inert payload composition only'}


def read_regular(path, limit):
    path = Path(os.path.abspath(path))
    require(path.resolve(strict=True) == path, 'linked input path')
    return BUTTONS.read_regular(path, limit)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base', type=Path, required=True)
    parser.add_argument('--expected-base-sha256', required=True)
    parser.add_argument('--trial-descriptor', type=Path, required=True)
    parser.add_argument('--payload-directory', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output = Path(os.path.abspath(args.output))
    require(args.output.parent.resolve(strict=True) == args.output.parent,
            'linked output directory')
    require(re.fullmatch('[0-9a-f]{64}', args.expected_base_sha256), 'invalid base SHA-256')
    result_path = Path(str(args.output)+'.json')
    require(not os.path.lexists(args.output) and not os.path.lexists(result_path), 'output exists')
    require(args.payload_directory.is_dir() and not args.payload_directory.is_symlink(),
            'unsafe payload directory')
    require({p.name for p in args.payload_directory.iterdir()} == set(PAYLOAD),
            'payload directory inventory mismatch')
    payload = {n: read_regular(args.payload_directory/n, spec[0]) for n, spec in PAYLOAD.items()}
    packed, result = compose(read_regular(args.base, 128*1024**2), args.expected_base_sha256,
                             read_regular(args.trial_descriptor, 512), payload)
    with args.output.open('xb') as stream:
        stream.write(packed)
    with result_path.open('x') as stream:
        json.dump(result, stream, indent=2)
        stream.write('\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
