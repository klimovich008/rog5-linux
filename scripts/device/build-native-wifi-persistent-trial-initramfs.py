#!/usr/bin/env python3
"""Add rollback-safe persistent trial metadata to a qualified Wi-Fi archive."""

import argparse
import gzip
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import stat
import time


REPO = Path(__file__).resolve().parents[2]
BASE_BUILDER = REPO / 'scripts/device/build-native-wifi-boot-initramfs.py'
SPEC = importlib.util.spec_from_file_location('rog5_wifi_archive', BASE_BUILDER)
ARCHIVE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ARCHIVE)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def require(condition, message):
    # These validate release inputs, not programmer-only assertions: -O must
    # enforce the same contract as normal Python.
    if not condition:
        raise ValueError(message)


def compose(base, expected_base, descriptor, helper):
    require(sha(base) == expected_base, 'base hash mismatch')
    trial = ARCHIVE.parse_trial_descriptor(descriptor)
    require(sha(helper) == ARCHIVE.TRIAL_HELPER_SHA256, 'trial helper hash mismatch')
    original = ARCHIVE.entries(gzip.decompress(base))
    members = {name: (fields.copy(), data) for name, (fields, data) in original.items()}
    prefix = 'rog5-native-wifi/'
    radio_unit = prefix+'units/rog5-wifi-radio.service'
    rollback_unit = prefix+'units/rog5-wifi-boot-rollback.service'
    for required in (prefix+'automatic', prefix+'runtime', radio_unit, rollback_unit,
                     prefix+'boot-files.sha256'):
        require(required in members, 'missing member: '+required)
    require(members[prefix+'automatic'][1] == b'rog5-native-wifi-boot-v1\n',
            'incompatible automatic marker')
    for absent in (prefix+'trial-descriptor', prefix+'trial-state',
                   prefix+'healthy', prefix+'units/rog5-wifi-healthy.service'):
        require(absent not in members, 'initial trial member already exists: '+absent)

    ARCHIVE.replace(members, prefix+'runtime',
                    (REPO/'initramfs/native-wifi/runtime').read_bytes())
    # The rollback action and its service are one composition change. Keeping
    # the base's unconditional service would bypass current-boot acceptance.
    ARCHIVE.replace(members, rollback_unit,
                    (REPO/'initramfs/native-wifi/units/rog5-wifi-boot-rollback.service').read_bytes())
    timing = dict(
        line.split('=', 1)
        for line in (REPO/'initramfs/native-wifi/timing').read_text().splitlines()
        if line and not line.startswith('#')
    )
    radio = (REPO/'initramfs/native-wifi/units/rog5-wifi-radio.service').read_bytes()
    require(radio.count(b'@OUTER_SECONDS@') == 1, 'radio timeout template mismatch')
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
            require(not path.is_symlink(), 'symlink source: '+str(path))
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
        if name not in (prefix+'runtime', radio_unit, rollback_unit,
                        prefix+'boot-files.sha256'):
            require(members[name] == value, 'unexpected member change: '+name)
    packed = gzip.compress(ARCHIVE.encode(members), compresslevel=1, mtime=0)
    require(ARCHIVE.entries(gzip.decompress(packed)) == members, 'archive round-trip mismatch')
    return packed, {
        'base_sha256': expected_base,
        'sha256': sha(packed),
        'trial': trial,
        'trial_helper_sha256': sha(helper),
        'changed_existing_members': [prefix+'boot-files.sha256', prefix+'runtime',
                                     radio_unit, rollback_unit],
        'added_members': len(members)-len(original),
        'kernel_rebuilt': False,
        'authority': 'none; persistent trial composition only',
    }


def compose_successor(base, expected_base, descriptor, helper):
    """Replace only consumed trial identity in an already qualified archive."""
    require(sha(base) == expected_base, 'base hash mismatch')
    trial = ARCHIVE.parse_trial_descriptor(descriptor)
    require(sha(helper) == ARCHIVE.TRIAL_HELPER_SHA256, 'trial helper hash mismatch')
    original = ARCHIVE.entries(gzip.decompress(base))
    members = {name: (fields.copy(), data) for name, (fields, data) in original.items()}
    prefix = 'rog5-native-wifi/'
    descriptor_name = prefix+'trial-descriptor'
    helper_name = prefix+'trial-state'
    checks_name = prefix+'boot-files.sha256'
    radio_name = prefix+'radio'
    probe_name = prefix+'probe-native-wifi.sh'
    for required in (prefix+'automatic', prefix+'runtime', descriptor_name,
                     helper_name, prefix+'healthy',
                     prefix+'units/rog5-wifi-healthy.service', radio_name, probe_name,
                     checks_name):
        require(required in members, 'missing member: '+required)
    previous = ARCHIVE.parse_trial_descriptor(members[descriptor_name][1])
    require(previous['trial_id'] != trial['trial_id'], 'successor reuses trial identity')
    require(previous['primary_bundle'] != trial['primary_bundle'], 'successor reuses bundle identity')
    require(members[helper_name][1] == helper, 'retained trial helper mismatch')

    ARCHIVE.replace(members, descriptor_name, descriptor)
    ARCHIVE.replace(members, radio_name,
                    (REPO/'initramfs/native-wifi/radio').read_bytes())
    ARCHIVE.replace(members, probe_name,
                    (REPO/'scripts/device/probe-native-wifi.sh').read_bytes())
    checks = ''.join(
        f'{sha(data)}  {name[len(prefix):]}\n'
        for name, (fields, data) in sorted(members.items())
        if name.startswith(prefix) and name != checks_name
        and stat.S_ISREG(fields[1]))
    ARCHIVE.replace(members, checks_name, checks.encode())
    changed = {descriptor_name, radio_name, probe_name, checks_name}
    for name, value in original.items():
        if name not in changed:
            require(members[name] == value, 'unexpected member change: '+name)
    packed = gzip.compress(ARCHIVE.encode(members), compresslevel=1, mtime=0)
    require(ARCHIVE.entries(gzip.decompress(packed)) == members, 'archive round-trip mismatch')
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
    require(re.fullmatch(r'[0-9a-f]{64}', args.expected_base_sha256), 'invalid base SHA-256')
    record = Path(str(args.output)+'.json')
    require(not os.path.lexists(args.output) and not os.path.lexists(record),
            'output already exists')
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
