#!/usr/bin/env python3
"""Compose a RAM-test archive from the qualified base/radio record; no admission.

Preserve every existing archive member except the three named boot helpers.
No firmware, kernel, modules or credential is downloaded or built here.
"""
import argparse
import gzip
import hashlib
import io
import json
import os
import re
from pathlib import Path, PurePosixPath
import stat
import tarfile
import time

REPO = Path(__file__).resolve().parents[2]
EPOCH = 1681862400
TRIAL_HELPER_SHA256 = 'ff6ede42d089a6a651db320a007947091029aca504500227e0c51bed6792f3ca'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def entries(data):
    offset = 0
    result = {}
    while True:
        header = data[offset:offset+110]
        assert len(header) == 110 and header[:6] == b'070701', 'newc header'
        fields = [int(header[6+i*8:14+i*8], 16) for i in range(13)]
        size, name_size = fields[6], fields[11]
        name = data[offset+110:offset+110+name_size]
        assert name_size > 0 and name.endswith(b'\0') and b'\0' not in name[:-1]
        name = name[:-1].decode('utf-8')
        assert name not in result and not name.startswith('/') and '..' not in name.split('/')
        body = (offset+110+name_size+3) & ~3
        offset = (body+size+3) & ~3
        assert offset <= len(data) and fields[12] == 0
        if name == 'TRAILER!!!':
            assert not any(data[offset:])
            return result
        result[name] = (fields, data[body:body+size])


def encode(members):
    output = bytearray()
    ordered = sorted(members.items()) + [('TRAILER!!!', ([0]*13, b''))]
    for name, (old, payload) in ordered:
        fields = old.copy()
        encoded = name.encode() + b'\0'
        fields[6], fields[11] = len(payload), len(encoded)
        output.extend(b'070701' + b''.join(f'{v:08x}'.encode() for v in fields) + encoded)
        output.extend(b'\0' * (-len(output) % 4))
        output.extend(payload)
        output.extend(b'\0' * (-len(output) % 4))
    output.extend(b'\0' * (-len(output) % 512))
    return bytes(output)


def add(members, name, data, mode):
    assert name not in members and not name.startswith('/') and '..' not in name.split('/')
    for parent in reversed(PurePosixPath(name).parents):
        if str(parent) == '.':
            continue
        if str(parent) not in members:
            add(members, str(parent), b'', stat.S_IFDIR | 0o755)
        assert stat.S_ISDIR(members[str(parent)][0][1]), 'non-directory parent'
    inode = max((f[0] for f, _ in members.values()), default=0) + 1
    fields = [inode, mode, 0, 0, 2 if stat.S_ISDIR(mode) else 1, EPOCH,
              len(data), 0, 0, 0, 0, len(name.encode())+1, 0]
    members[name] = fields, data


def replace(members, name, data):
    fields, old = members[name]
    assert stat.S_ISREG(fields[1]) and fields[4] == 1
    fields = fields.copy()
    fields[6] = len(data)
    members[name] = fields, data


def parse_trial_descriptor(data):
    text = data.decode('ascii')
    assert '\r' not in text and text.endswith('\n')
    lines = text.splitlines()
    assert len(lines) == 4 and lines[0] == 'format=rog5-persistent-wifi-health-v1'
    names = ('trial_id', 'primary_bundle', 'mode')
    values = {}
    for line, name in zip(lines[1:], names, strict=True):
        prefix = name + '='
        assert line.startswith(prefix)
        values[name] = line[len(prefix):]
    assert re.fullmatch(r'[0-9a-f]{64}', values['trial_id'])
    assert re.fullmatch(r'[a-z0-9][a-z0-9._-]{0,63}', values['primary_bundle'])
    assert '..' not in values['primary_bundle']
    assert values['mode'] == 'try-once'
    return values


def compose(base, package, record):
    assert sha(base) == record['files']['initramfs.cpio.gz'], 'base identity'
    assert sha(package) == record['probe_package_sha256'], 'radio package identity'
    release = record['kernel_release']
    assert release.startswith('7.1.4-g') and all(c.isalnum() or c in '.-' for c in release)
    original = entries(gzip.decompress(base))
    members = {k: (f.copy(), data) for k, (f, data) in original.items()}
    init = original['init'][1]
    for line in (f'expected_kernel_release={release}\n', 'expected_native_root_mode=1\n',
                 'expected_ufs_storage_mode=read-only\n', 'expected_ssh_diagnostic_mode=0\n'):
        assert init.count(line.encode()) == 1, 'not the qualified read-only native base'
    new_init = (REPO/'initramfs/persistent-root-init').read_text()
    for key, value in {'KERNEL_RELEASE': release, 'NATIVE_ROOT_MODE': '1',
                       'UFS_STORAGE_MODE': 'read-only', 'SSH_DIAGNOSTIC_MODE': '0',
                       'PROBE_BOOT_ID': 'staged-seal',
                       'PERSISTENT_OVERLAY_MODE': '0'}.items():
        token = '@EXPECTED_' + key + '@'
        assert new_init.count(token) == 1
        new_init = new_init.replace(token, value)
    assert '@EXPECTED_' not in new_init
    changed = {'init': new_init.encode(),
               'sbin/rog5-load-persistent-power-usb': (REPO/'scripts/device/load-persistent-root-power-usb.sh').read_bytes(),
               'usr/local/sbin/rog5-persistent-tailscale': (REPO/'initramfs/persistent-tailscale-runtime').read_bytes()}
    for name, data in changed.items():
        replace(members, name, data)

    prefix = 'rog5-native-wifi/'
    with tarfile.open(fileobj=io.BytesIO(package), mode='r:gz') as archive:
        seen = set()
        for member in archive:
            name = member.name.removeprefix('./')
            assert name and not name.startswith('/') and '..' not in name.split('/')
            assert name not in seen, 'duplicate radio package member'
            seen.add(name)
            if member.isdir():
                continue
            assert member.isfile() and not member.islnk() and not member.issym()
            assert name in record['probe_files'] or name == 'probe-files.sha256'
            data = archive.extractfile(member).read()
            if name != 'probe-files.sha256':
                assert sha(data) == record['probe_files'][name], 'radio member identity'
                add(members, prefix+name, data, stat.S_IFREG | (0o755 if member.mode & 0o111 else 0o644))
        assert set(record['probe_files']) <= seen, 'incomplete qualified radio package'
    # Only public userspace changes; retain every qualified firmware/module byte.
    replace(members, prefix+'probe-native-wifi.sh', (REPO/'scripts/device/probe-native-wifi.sh').read_bytes())
    timing = dict(re.findall(r'^([a-z_]+)=([0-9]+)$', (REPO/'initramfs/native-wifi/timing').read_text(), re.M))
    assert int(timing['outer_seconds']) > int(timing['radio_seconds']) + int(timing['cleanup_seconds'])
    assert f"--on-active={timing['radio_seconds']}s" in (REPO/'scripts/device/probe-native-wifi.sh').read_text()
    for path in sorted((REPO/'initramfs/native-wifi').rglob('*')):
        if path.is_file():
            assert not path.is_symlink()
            data = path.read_bytes().replace(b'@OUTER_SECONDS@', timing['outer_seconds'].encode())
            add(members, prefix+str(path.relative_to(REPO/'initramfs/native-wifi')),
                data, stat.S_IFREG | (0o755 if os.access(path, os.X_OK) else 0o644))
    add(members, prefix+'automatic', b'rog5-native-wifi-boot-v1\n', stat.S_IFREG | 0o444)
    add(members, prefix+'kernel-release', release.encode()+b'\n', stat.S_IFREG | 0o444)
    checks = ''.join(f'{sha(data)}  {name[len(prefix):]}\n' for name, (fields, data)
                     in sorted(members.items()) if name.startswith(prefix) and stat.S_ISREG(fields[1]))
    add(members, prefix+'boot-files.sha256', checks.encode(), stat.S_IFREG | 0o444)
    for name, value in original.items():
        if name not in changed:
            assert members[name] == value, 'unrelated base member changed'
    packed = gzip.compress(encode(members), compresslevel=1, mtime=0)
    assert entries(gzip.decompress(packed)) == members, 'newc round trip'
    return packed, {'kernel_release': release, 'changed_existing_members': sorted(changed),
                    'added_members': len(members)-len(original), 'base_sha256': sha(base),
                    'radio_package_sha256': sha(package), 'sha256': sha(packed),
                    'authority': 'none; RAM-test composition only', 'kernel_rebuilt': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base', type=Path, required=True)
    parser.add_argument('--radio-package', type=Path, required=True)
    parser.add_argument('--record', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    output_record = Path(str(args.output)+'.json')
    assert not args.output.exists() and not output_record.exists(), 'output already exists'
    start = time.monotonic()
    packed, result = compose(args.base.read_bytes(), args.radio_package.read_bytes(),
                             json.loads(args.record.read_text()))
    with args.output.open('xb') as stream:
        stream.write(packed)
    result['seconds'] = time.monotonic()-start
    with output_record.open('x') as stream:
        json.dump(result, stream, indent=2)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
