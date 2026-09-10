#!/usr/bin/env python3
"""Compose an unsigned display-only DTB from the pinned server V9 baseline."""
import argparse
from hashlib import sha256
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

SPEC = importlib.util.spec_from_file_location(
    'display_v9', Path(__file__).with_name('verify-display-v9-dtb-delta.py'))
V = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(V)
OVERLAY_SHA256 = '6180bc9f0b451afd8a9edd7ec78fdae8c5b6628cce49a397212fd1517d4fcb7b'


def build(base, overlay, output):
    output = Path(os.path.abspath(output))
    V.ordinary_path(output.parent)
    V.require(not os.path.lexists(output), 'output already exists')
    base_data, overlay_data = V.read_regular(base), V.read_regular(overlay, 128 * 1024)
    V.require(len(base_data) == V.BASE_SIZE and sha256(base_data).hexdigest() == V.BASE_SHA256,
              'current V9 base identity mismatch')
    V.require(sha256(overlay_data).hexdigest() == OVERLAY_SHA256, 'display overlay identity mismatch')
    # Compile snapshots of already checked inputs; never pass mutable originals
    # or the eventual output path to external tools.
    with tempfile.TemporaryDirectory(prefix='rog5-display-v9-') as temporary:
        root = Path(temporary)
        (root/'base.dtb').write_bytes(base_data)
        (root/'overlay.dts').write_bytes(overlay_data)
        for argv in (
            ['dtc', '-q', '-@', '-I', 'dts', '-O', 'dtb', '-o', str(root/'overlay.dtbo'), str(root/'overlay.dts')],
            ['fdtoverlay', '-i', str(root/'base.dtb'), '-o', str(root/'candidate.dtb'), str(root/'overlay.dtbo')],
        ):
            subprocess.run(argv, check=True, capture_output=True, timeout=10)
        candidate = V.read_regular(root/'candidate.dtb')
        report = V.verify(base_data, candidate)
    # Exclusive creation also closes an output-name race after the first check.
    V.ordinary_path(output.parent)
    fd = os.open(output, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC, 0o644)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(candidate)
        stream.flush()
        os.fsync(stream.fileno())
    report['overlay_sha256'] = OVERLAY_SHA256
    report['output'] = str(output)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('base', type=Path)
    parser.add_argument('overlay', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    print(json.dumps(build(args.base, args.overlay, args.output), indent=2))


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        print('FAIL ' + str(error), file=sys.stderr)
        raise SystemExit(1)
