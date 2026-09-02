#!/usr/bin/env python3
"""Add rollback-safe persistent trial metadata to a qualified Wi-Fi archive."""

import argparse
import gzip
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import stat
import time


REPO = Path(__file__).resolve().parents[2]
BASE_BUILDER = REPO / 'scripts/device/build-native-wifi-boot-initramfs.py'
SPEC = importlib.util.spec_from_file_location('rog5_wifi_archive', BASE_BUILDER)
ARCHIVE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ARCHIVE)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def compose(base, expected_base, descriptor, helper):
    assert sha(base) == expected_base
    trial = ARCHIVE.parse_trial_descriptor(descriptor)
    assert sha(helper) == ARCHIVE.TRIAL_HELPER_SHA256
    original = ARCHIVE.entries(gzip.decompress(base))
    members = {name: (fields.copy(), data) for name, (fields, data) in original.items()}
    prefix = 'rog5-native-wifi/'
    radio_unit = prefix+'units/rog5-wifi-radio.service'
    for required in (prefix+'automatic', prefix+'runtime', radio_unit,
                     prefix+'boot-files.sha256'):
        assert required in members
    assert members[prefix+'automatic'][1] == b'rog5-native-wifi-boot-v1\n'
    for absent in (prefix+'trial-descriptor', prefix+'trial-state',
                   prefix+'healthy', prefix+'units/rog5-wifi-healthy.service'):
        assert absent not in members

    ARCHIVE.replace(members, prefix+'runtime',
                    (REPO/'initramfs/native-wifi/runtime').read_bytes())
    timing = dict(
        line.split('=', 1)
        for line in (REPO/'initramfs/native-wifi/timing').read_text().splitlines()
        if line and not line.startswith('#')
    )
    radio = (REPO/'initramfs/native-wifi/units/rog5-wifi-radio.service').read_bytes()
    assert radio.count(b'@OUTER_SECONDS@') == 1
    ARCHIVE.replace(
        members,
        radio_unit,
        radio.replace(b'@OUTER_SECONDS@', timing['outer_seconds'].encode()),
    )
    ARCHIVE.add(members, prefix+'trial-descriptor', descriptor, stat.S_IFREG | 0o444)
    ARCHIVE.add(members, prefix+'trial-state', helper,
                stat.S_IFREG | 0o755)
    persistent = REPO/'initramfs/native-wifi-persistent'
    for path in sorted(persistent.rglob('*')):
        if path.is_file():
            assert not path.is_symlink()
            ARCHIVE.add(members, prefix+str(path.relative_to(persistent)),
                        path.read_bytes(),
                        stat.S_IFREG | (0o755 if os.access(path, os.X_OK) else 0o644))
    checks = ''.join(
        f'{sha(data)}  {name[len(prefix):]}\n'
        for name, (fields, data) in sorted(members.items())
        if name.startswith(prefix) and name != prefix+'boot-files.sha256'
        and stat.S_ISREG(fields[1]))
    ARCHIVE.replace(members, prefix+'boot-files.sha256', checks.encode())
    for name, value in original.items():
        if name not in (prefix+'runtime', radio_unit, prefix+'boot-files.sha256'):
            assert members[name] == value
    packed = gzip.compress(ARCHIVE.encode(members), compresslevel=1, mtime=0)
    assert ARCHIVE.entries(gzip.decompress(packed)) == members
    return packed, {
        'base_sha256': expected_base,
        'sha256': sha(packed),
        'trial': trial,
        'trial_helper_sha256': sha(helper),
        'changed_existing_members': [prefix+'boot-files.sha256', prefix+'runtime',
                                     radio_unit],
        'added_members': len(members)-len(original),
        'kernel_rebuilt': False,
        'authority': 'none; persistent trial composition only',
    }


def compose_successor(base, expected_base, descriptor, helper):
    """Replace only consumed trial identity in an already qualified archive."""
    assert sha(base) == expected_base
    trial = ARCHIVE.parse_trial_descriptor(descriptor)
    assert sha(helper) == ARCHIVE.TRIAL_HELPER_SHA256
    original = ARCHIVE.entries(gzip.decompress(base))
    members = {name: (fields.copy(), data) for name, (fields, data) in original.items()}
    prefix = 'rog5-native-wifi/'
    descriptor_name = prefix+'trial-descriptor'
    helper_name = prefix+'trial-state'
    checks_name = prefix+'boot-files.sha256'
    for required in (prefix+'automatic', prefix+'runtime', descriptor_name,
                     helper_name, prefix+'healthy',
                     prefix+'units/rog5-wifi-healthy.service', checks_name):
        assert required in members
    previous = ARCHIVE.parse_trial_descriptor(members[descriptor_name][1])
    assert previous['trial_id'] != trial['trial_id']
    assert previous['primary_bundle'] != trial['primary_bundle']
    assert members[helper_name][1] == helper

    ARCHIVE.replace(members, descriptor_name, descriptor)
    checks = ''.join(
        f'{sha(data)}  {name[len(prefix):]}\n'
        for name, (fields, data) in sorted(members.items())
        if name.startswith(prefix) and name != checks_name
        and stat.S_ISREG(fields[1]))
    ARCHIVE.replace(members, checks_name, checks.encode())
    changed = {descriptor_name, checks_name}
    for name, value in original.items():
        if name not in changed:
            assert members[name] == value
    packed = gzip.compress(ARCHIVE.encode(members), compresslevel=1, mtime=0)
    assert ARCHIVE.entries(gzip.decompress(packed)) == members
    return packed, {
        'base_sha256': expected_base,
        'sha256': sha(packed),
        'previous_trial': previous,
        'trial': trial,
        'trial_helper_sha256': sha(helper),
        'changed_existing_members': sorted(changed),
        'added_members': 0,
        'kernel_rebuilt': False,
        'authority': 'none; persistent successor composition only',
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base', type=Path, required=True)
    parser.add_argument('--expected-base-sha256', required=True)
    parser.add_argument('--trial-descriptor', type=Path, required=True)
    parser.add_argument('--trial-helper', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--successor', action='store_true')
    args = parser.parse_args()
    assert len(args.expected_base_sha256) == 64
    record = Path(str(args.output)+'.json')
    assert not args.output.exists() and not record.exists()
    started = time.monotonic()
    composer = compose_successor if args.successor else compose
    packed, result = composer(args.base.read_bytes(), args.expected_base_sha256,
                              args.trial_descriptor.read_bytes(),
                              args.trial_helper.read_bytes())
    result['seconds'] = time.monotonic()-started
    with args.output.open('xb') as stream:
        stream.write(packed)
    with record.open('x') as stream:
        json.dump(result, stream, indent=2)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
