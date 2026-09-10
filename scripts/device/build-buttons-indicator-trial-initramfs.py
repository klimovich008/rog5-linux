#!/usr/bin/env python3
"""Add an inert indicator payload and the paired shutdown fix to a fresh trial.

No modules are loaded and no service is enabled by this composition. The
existing initramfs carries the payload into /run for a separately guarded test.
"""
import argparse
import gzip
import importlib.util
import json
import os
from pathlib import Path
import re
import stat
import time

REPO = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    'persistent_successor', REPO/'scripts/device/build-native-wifi-persistent-trial-initramfs.py')
PERSISTENT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PERSISTENT)
ARCHIVE = PERSISTENT.ARCHIVE
require = PERSISTENT.require
sha = ARCHIVE.sha
RELEASE = '7.1.4-gf17befd4ef17'
PREFIX = 'rog5-native-wifi/'
PAYLOAD_PREFIX = PREFIX+'buttons-indicator/'
CATALOG = PREFIX+'boot-files.sha256'
OLD_SHUTDOWN_SHA256 = '1cd007ea25d9a694c7fff25c7e7a7ee005b28f4767d94bf5682f17fe7e6303cd'
SHUTDOWN_SHA256 = 'fc1ce027c20679a1d18200858e216c106c0fa690224de26e3705c105fda67860'
SHUTDOWN = REPO/'initramfs/persistent-root-shutdown-standalone'
# Exact artifacts from the retained installed-kernel module kit and the
# reproducible static AArch64 indicator. Never substitute the older 7a5 ABI.
PAYLOAD = {
    'led-class-multicolor.ko': (276976, '562c45971e2fa51d2aea8fe8661f4dd654ab0f704b8aba04b4a63cc3d1e3ec4b', 0o644),
    'qcom-pbs.ko': (284304, '63dd1f7091a37e87cfc452fe37619027d4601f4da019893bac68d8bf56ff3d22', 0o644),
    'leds-qcom-lpg.ko': (368424, '681440a4905d930b8b4e8e138020099700390a540ebb2b443941be7f09b914c6', 0o644),
    'rog5-key-indicatord': (67520, '3792745382a390ebeef37a081e532884aae07bbcd73fd9f0da1c94e67bdabbc8', 0o755),
}


def catalog(members):
    return ''.join(
        f'{sha(data)}  {name[len(PREFIX):]}\n'
        for name, (fields, data) in sorted(members.items())
        if name.startswith(PREFIX) and name != CATALOG
        and stat.S_ISREG(fields[1])).encode()


def validate_payload(payload):
    require(set(payload) == set(PAYLOAD), 'payload inventory mismatch')
    for name, (size, expected, _) in PAYLOAD.items():
        data = payload[name]
        require(type(data) is bytes and len(data) == size and sha(data) == expected,
                'payload identity mismatch: '+name)


def compose(base, expected_base, descriptor, payload):
    require(sha(base) == expected_base, 'base hash mismatch')
    validate_payload(payload)
    original = ARCHIVE.entries(gzip.decompress(base))
    for name, mode in ((PREFIX+'kernel-release', 0o444), (CATALOG, 0o444)):
        require(name in original and original[name][0][1:5] ==
                [stat.S_IFREG | mode, 0, 0, 1], 'base member metadata: '+name)
    require(original[PREFIX+'kernel-release'][1] == (RELEASE+'\n').encode(),
            'kernel release mismatch')
    require(original[CATALOG][1] == catalog(original), 'base integrity catalog mismatch')
    shutdown = original.get('shutdown')
    require(shutdown is not None and shutdown[0][1:5] == [stat.S_IFREG | 0o755, 0, 0, 1]
            and sha(shutdown[1]) == OLD_SHUTDOWN_SHA256, 'retained shutdown identity mismatch')
    corrected_shutdown = read_regular(SHUTDOWN, 128*1024)
    require(sha(corrected_shutdown) == SHUTDOWN_SHA256, 'corrected shutdown identity mismatch')
    require(not any(name == PAYLOAD_PREFIX[:-1] or name.startswith(PAYLOAD_PREFIX)
                    for name in original), 'indicator payload already exists')
    # Reuse the current coherent radio/trial checks without broadening the
    # existing successor composer's hardware-preservation contract.
    intermediate, _ = PERSISTENT.compose_successor(
        base, expected_base, descriptor, ARCHIVE.TRIAL_HELPER.read_bytes())
    members = ARCHIVE.entries(gzip.decompress(intermediate))
    allowed = {PREFIX+'trial-descriptor', CATALOG}
    require(set(members) == set(original), 'unexpected successor member inventory')
    for name, entry in original.items():
        require(name in allowed or members[name] == entry,
                'unexpected successor member change: '+name)
    # The current composition verifier pairs this exact tested correction.
    # Carry it explicitly; never waive the mismatch with the installed helper.
    ARCHIVE.replace(members, 'shutdown', corrected_shutdown)
    allowed.add('shutdown')
    for name in sorted(PAYLOAD):
        ARCHIVE.add(members, PAYLOAD_PREFIX+name, payload[name],
                    stat.S_IFREG | PAYLOAD[name][2])
    ARCHIVE.replace(members, CATALOG, catalog(members))
    added = {PAYLOAD_PREFIX[:-1]} | {PAYLOAD_PREFIX+name for name in PAYLOAD}
    require(set(members)-set(original) == added, 'unexpected payload member inventory')
    for name, entry in original.items():
        require(name in allowed or members[name] == entry,
                'unexpected final member change: '+name)
    ARCHIVE.verify_radio_composition(members)
    packed = gzip.compress(ARCHIVE.encode(members), compresslevel=1, mtime=0)
    require(ARCHIVE.entries(gzip.decompress(packed)) == members, 'archive round-trip mismatch')
    return packed, {
        'status': 'PASS', 'base_sha256': expected_base, 'sha256': sha(packed),
        'kernel_release': RELEASE, 'trial': ARCHIVE.parse_trial_descriptor(descriptor),
        'changed_existing_members': sorted(allowed), 'added_members': sorted(added),
        'payload_sha256': {name: sha(payload[name]) for name in sorted(payload)},
        'shutdown_sha256': sha(corrected_shutdown),
        'activation': 'none; deferred to a separately guarded runtime test',
        'kernel_rebuilt': False, 'arch_root_rebuilt': False,
        'authority': 'unsigned offline composition only',
    }


def read_regular(path, limit):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, 'rb') as stream:
        info = os.fstat(stream.fileno())
        require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1
                and info.st_size <= limit, 'unsafe input metadata: '+str(path))
        data = stream.read(limit+1)
        require(len(data) == info.st_size, 'input size changed: '+str(path))
        return data


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base', type=Path, required=True)
    parser.add_argument('--expected-base-sha256', required=True)
    parser.add_argument('--trial-descriptor', type=Path, required=True)
    parser.add_argument('--payload-directory', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    require(re.fullmatch('[0-9a-f]{64}', args.expected_base_sha256), 'invalid base SHA-256')
    result_path = Path(str(args.output)+'.json')
    require(not os.path.lexists(args.output) and not os.path.lexists(result_path), 'output exists')
    require(args.payload_directory.is_dir() and not args.payload_directory.is_symlink(),
            'unsafe payload directory')
    require({p.name for p in args.payload_directory.iterdir()} == set(PAYLOAD),
            'payload directory inventory mismatch')
    started = time.monotonic()
    payload = {name: read_regular(args.payload_directory/name, size)
               for name, (size, _, _) in PAYLOAD.items()}
    packed, result = compose(read_regular(args.base, 128*1024**2), args.expected_base_sha256,
                             read_regular(args.trial_descriptor, 512), payload)
    result['seconds'] = time.monotonic()-started
    with args.output.open('xb') as stream:
        stream.write(packed)
    with result_path.open('x') as stream:
        json.dump(result, stream, indent=2)
        stream.write('\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
