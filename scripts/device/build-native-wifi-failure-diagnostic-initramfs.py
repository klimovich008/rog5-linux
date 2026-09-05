#!/usr/bin/env python3
"""Add the bounded radio-failure ACM reporter to a qualified Wi-Fi archive."""

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
BASE_BUILDER = REPO/'scripts/device/build-native-wifi-boot-initramfs.py'
SPEC = importlib.util.spec_from_file_location('rog5_wifi_archive', BASE_BUILDER)
ARCHIVE = importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(ARCHIVE)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def compose(base, expected_base):
    assert sha(base) == expected_base
    original = ARCHIVE.entries(gzip.decompress(base))
    members = {name: (fields.copy(), data) for name, (fields, data) in original.items()}
    prefix = 'rog5-native-wifi/'
    replacements = {
        prefix+'runtime': REPO/'initramfs/native-wifi/runtime',
        prefix+'radio': REPO/'initramfs/native-wifi/radio',
        prefix+'units/rog5-wifi-radio.service':
            REPO/'initramfs/native-wifi/units/rog5-wifi-radio.service',
    }
    outer = re.findall(rb'^outer_seconds=([0-9]+)$',
                       (REPO/'initramfs/native-wifi/timing').read_bytes(), re.M)
    if len(outer) != 1 or int(outer[0]) <= 0:
        raise ValueError('missing or invalid canonical outer timeout')
    for name, path in replacements.items():
        data = path.read_bytes().replace(b'@OUTER_SECONDS@', outer[0])
        ARCHIVE.replace(members, name, data)
    additions = {
        prefix+'failure': REPO/'initramfs/native-wifi/failure',
        prefix+'units/rog5-wifi-failure.service':
            REPO/'initramfs/native-wifi/units/rog5-wifi-failure.service',
    }
    for name, path in additions.items():
        ARCHIVE.add(members, name, path.read_bytes(),
                    stat.S_IFREG | (0o755 if os.access(path, os.X_OK) else 0o644))
    checks = ''.join(
        f'{sha(data)}  {name[len(prefix):]}\n'
        for name, (fields, data) in sorted(members.items())
        if name.startswith(prefix) and name != prefix+'boot-files.sha256'
        and stat.S_ISREG(fields[1]))
    ARCHIVE.replace(members, prefix+'boot-files.sha256', checks.encode())
    for name, value in original.items():
        if name not in set(replacements) | {prefix+'boot-files.sha256'}:
            assert members[name] == value
    ARCHIVE.verify_radio_composition(members)
    packed = gzip.compress(ARCHIVE.encode(members), compresslevel=1, mtime=0)
    assert ARCHIVE.entries(gzip.decompress(packed)) == members
    return packed, {
        'base_sha256': expected_base,
        'sha256': sha(packed),
        'changed_existing_members': sorted(set(replacements) |
                                           {prefix+'boot-files.sha256'}),
        'added_members': sorted(additions),
        'kernel_rebuilt': False,
        'authority': 'none; failure-diagnostic composition only',
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base', type=Path, required=True)
    parser.add_argument('--expected-base-sha256', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    record = Path(str(args.output)+'.json')
    assert not args.output.exists() and not record.exists()
    started = time.monotonic()
    packed, result = compose(args.base.read_bytes(), args.expected_base_sha256)
    result['seconds'] = time.monotonic()-started
    with args.output.open('xb') as stream: stream.write(packed)
    with record.open('x') as stream: json.dump(result, stream, indent=2)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
