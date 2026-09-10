#!/usr/bin/env python3
"""Verify the display-only delta from the exact current server V9 DTB."""
import argparse
from hashlib import sha256
import importlib.util
import json
import os
from pathlib import Path
import stat
import struct
import sys

SPEC = importlib.util.spec_from_file_location(
    'display60_historical', Path(__file__).with_name('verify-display-60hz-dtb-delta.py'))
HISTORICAL = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(HISTORICAL)
BASE_SHA256 = 'eca5c2c343fc4cd5511490be0c17501d69f4027941e268ff3f95da4672c214f4'
BASE_SIZE = 107878
LIMIT = 2 * 1024 * 1024


def require(condition, message):
    if not condition:
        raise ValueError(message)


def ordinary_path(path):
    path = Path(os.path.abspath(path))
    require(path.resolve(strict=True) == path, 'linked input path')
    return path


def read_regular(path, limit=LIMIT):
    path = ordinary_path(path)
    fd = os.open(path, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, 'rb') as stream:
        before = os.fstat(stream.fileno())
        require(stat.S_ISREG(before.st_mode) and before.st_nlink == 1
                and 0 < before.st_size <= limit, 'unsafe input metadata')
        data = stream.read(limit + 1)
        after = os.fstat(stream.fileno())
        fields = ('st_dev', 'st_ino', 'st_size', 'st_mtime_ns', 'st_ctime_ns')
        require(len(data) == before.st_size and all(getattr(before, k) == getattr(after, k)
                for k in fields), 'input changed while reading')
    return data


def boot_metadata(data):
    """Extract boot authority after the historical parser validates all blocks."""
    header = struct.unpack_from('>10I', data)
    origin = header[4]
    end = origin
    while end <= len(data) - 16:
        address, size = struct.unpack_from('>QQ', data, end)
        end += 16
        if address == 0 and size == 0:
            return header[7], origin, data[origin:end]
        require(size > 0 and address + size <= 1 << 64, 'invalid reservation range')
    raise ValueError('unterminated reservation map')


def verify(base_data, candidate_data):
    require(len(base_data) == BASE_SIZE and sha256(base_data).hexdigest() == BASE_SHA256,
            'current V9 base identity mismatch')
    parser = HISTORICAL.load_parser()
    base = parser.parse_dtb(base_data, 'current V9 base')
    candidate = parser.parse_dtb(candidate_data, 'display V9 candidate')
    # Node equality alone ignores boot_cpuid_phys and the FDT reservation map.
    # parse_dtb above checks offsets, termination, bounds and block overlap.
    require(boot_metadata(base_data) == boot_metadata(candidate_data),
            'boot CPU or reservation map/origin changed')
    added, changed = HISTORICAL.compare(base, candidate, parser)
    return {'status': 'PASS', 'base_sha256': BASE_SHA256,
            'candidate_sha256': sha256(candidate_data).hexdigest(),
            'added_nodes': added, 'changed_existing_properties': changed,
            'boot_cpu_and_reservations_preserved': True,
            'scope': 'unsigned display-only DT delta; no activation or hardware qualification'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('base', type=Path)
    parser.add_argument('candidate', type=Path)
    args = parser.parse_args()
    print(json.dumps(verify(read_regular(args.base), read_regular(args.candidate)), indent=2))


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError) as error:
        print('FAIL ' + str(error), file=sys.stderr)
        raise SystemExit(1)
