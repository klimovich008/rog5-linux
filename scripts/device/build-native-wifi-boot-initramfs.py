#!/usr/bin/env python3
"""Compose a RAM-test archive from the qualified base/radio record; no admission.

Preserve every existing archive member except the named boot helpers.
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
TRIAL_HELPER = REPO / (REPO/'configs/persistent-trial-helper.path').read_text().strip()
TRIAL_HELPER_SHA256 = (TRIAL_HELPER.parent/'SHA256SUMS').read_text().split(' ', 1)[0]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def entries(data):
    offset = 0
    result = {}
    while True:
        header = data[offset:offset+110]
        if len(header) != 110 or header[:6] != b'070701':
            raise ValueError('newc header')
        fields = [int(header[6+i*8:14+i*8], 16) for i in range(13)]
        size, name_size = fields[6], fields[11]
        name = data[offset+110:offset+110+name_size]
        if not (name_size > 0 and name.endswith(b'\0') and b'\0' not in name[:-1]):
            raise ValueError('newc name encoding')
        name = name[:-1].decode('utf-8')
        if name in result or name.startswith('/') or '..' in name.split('/'):
            raise ValueError('duplicate or unsafe newc name')
        body = (offset+110+name_size+3) & ~3
        offset = (body+size+3) & ~3
        if offset > len(data) or fields[12] != 0:
            raise ValueError('newc bounds or checksum')
        if name == 'TRAILER!!!':
            if any(data[offset:]):
                raise ValueError('newc trailing data')
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
    if name in members or name.startswith('/') or '..' in name.split('/'):
        raise ValueError('duplicate or unsafe newc name')
    for parent in reversed(PurePosixPath(name).parents):
        if str(parent) == '.':
            continue
        if str(parent) not in members:
            add(members, str(parent), b'', stat.S_IFDIR | 0o755)
        if not stat.S_ISDIR(members[str(parent)][0][1]):
            raise ValueError('non-directory parent')
    inode = max((f[0] for f, _ in members.values()), default=0) + 1
    fields = [inode, mode, 0, 0, 2 if stat.S_ISDIR(mode) else 1, EPOCH,
              len(data), 0, 0, 0, 0, len(name.encode())+1, 0]
    members[name] = fields, data


def replace(members, name, data):
    fields, old = members[name]
    if not stat.S_ISREG(fields[1]) or fields[4] != 1:
        raise ValueError('replacement requires a single-link regular file')
    fields = fields.copy()
    fields[6] = len(data)
    members[name] = fields, data


def parse_trial_descriptor(data):
    text = data.decode('ascii')
    if '\r' in text or not text.endswith('\n'):
        raise ValueError('trial descriptor line endings')
    lines = text.splitlines()
    if len(lines) != 4 or lines[0] != 'format=rog5-persistent-wifi-health-v1':
        raise ValueError('trial descriptor format')
    names = ('trial_id', 'primary_bundle', 'mode')
    values = {}
    for line, name in zip(lines[1:], names, strict=True):
        prefix = name + '='
        if not line.startswith(prefix):
            raise ValueError(f'trial descriptor field: {name}')
        values[name] = line[len(prefix):]
    if not re.fullmatch(r'[0-9a-f]{64}', values['trial_id']):
        raise ValueError('trial descriptor trial_id')
    if not re.fullmatch(r'[a-z0-9][a-z0-9._-]{0,63}', values['primary_bundle']):
        raise ValueError('trial descriptor primary_bundle')
    if '..' in values['primary_bundle']:
        raise ValueError('trial descriptor primary_bundle traversal')
    if values['mode'] != 'try-once':
        raise ValueError('trial descriptor mode')
    return values


def render_boot_template(path, values):
    text = path.read_text()
    for key, value in values.items():
        token = '@EXPECTED_' + key + '@'
        if text.count(token) != 1:
            raise ValueError(f'{path.name}: missing or duplicate {token}')
        text = text.replace(token, value)
    if '@EXPECTED_' in text:
        raise ValueError(f'{path.name}: unresolved boot parameter')
    return text.encode()


def verify_radio_composition(members):
    """Refusal producer, service consumers and rollback are one target ABI.

    Identity-only successors may retain a current coherent archive, but cannot
    refresh the radio while silently keeping older consumers. Recompose the
    small target archive when this ABI changes; no kernel build is needed.
    """
    prefix = 'rog5-native-wifi/'
    outer = re.findall(rb'^outer_seconds=([0-9]+)$',
                       (REPO/'initramfs/native-wifi/timing').read_bytes(), re.M)
    if len(outer) != 1 or int(outer[0]) <= 0:
        raise ValueError('invalid radio timeout')
    sources = {name: REPO/'initramfs/native-wifi'/name for name in (
        'radio', 'runtime', 'units/rog5-wifi-radio.service',
        'units/rog5-wifi-wpa.service', 'units/rog5-wifi-dhcp.service',
        'units/rog5-wifi-boot-rollback.service')}
    healthy = 'units/rog5-wifi-healthy.service'
    if prefix+'trial-descriptor' in members:
        sources[healthy] = REPO/'initramfs/native-wifi-persistent'/healthy
    for name, source in sources.items():
        entry = members.get(prefix+name)
        if entry is None or not stat.S_ISREG(entry[0][1]) or entry[0][4] != 1:
            raise ValueError('radio composition member: '+name)
        if entry[1] != source.read_bytes().replace(b'@OUTER_SECONDS@', outer[0]):
            raise ValueError('incompatible radio composition; recompose target archive: '+name)


def compose(base, package, record):
    if sha(base) != record['files']['initramfs.cpio.gz']:
        raise ValueError('base identity')
    if sha(package) != record['probe_package_sha256']:
        raise ValueError('radio package identity')
    release = record['kernel_release']
    if not (release.startswith('7.1.4-g') and all(c.isalnum() or c in '.-' for c in release)):
        raise ValueError('kernel release')
    original = entries(gzip.decompress(base))
    members = {k: (f.copy(), data) for k, (f, data) in original.items()}
    init = original['init'][1]
    for line in (f'expected_kernel_release={release}\n', 'expected_native_root_mode=1\n',
                 'expected_ufs_storage_mode=read-only\n', 'expected_ssh_diagnostic_mode=0\n'):
        if init.count(line.encode()) != 1:
            raise ValueError('not the qualified read-only native base')
    boot_state = {'NATIVE_ROOT_MODE': '1', 'UFS_STORAGE_MODE': 'read-only',
                  'PROBE_BOOT_ID': 'staged-seal', 'PERSISTENT_OVERLAY_MODE': '0'}
    # The watchdog consumer and its P2 acknowledgment producer are one boot
    # interface. Never refresh init while retaining a historical producer.
    changed = {'init': render_boot_template(REPO/'initramfs/persistent-root-init',
                   dict(boot_state, KERNEL_RELEASE=release, SSH_DIAGNOSTIC_MODE='0')),
               'usr/local/sbin/rog5-p2-attest': render_boot_template(
                   REPO/'initramfs/persistent-root-attest', boot_state),
               'sbin/rog5-load-persistent-power-usb': (REPO/'scripts/device/load-persistent-root-power-usb.sh').read_bytes(),
               'usr/local/sbin/rog5-persistent-tailscale': (REPO/'initramfs/persistent-tailscale-runtime').read_bytes()}
    for name, data in changed.items():
        replace(members, name, data)

    prefix = 'rog5-native-wifi/'
    with tarfile.open(fileobj=io.BytesIO(package), mode='r:gz') as archive:
        seen = set()
        for member in archive:
            name = member.name.removeprefix('./')
            if not name or name.startswith('/') or '..' in name.split('/'):
                raise ValueError('unsafe radio package name')
            if name in seen:
                raise ValueError('duplicate radio package member')
            seen.add(name)
            if member.isdir():
                continue
            if not member.isfile() or member.islnk() or member.issym():
                raise ValueError('radio package member must be a regular file')
            if name not in record['probe_files'] and name != 'probe-files.sha256':
                raise ValueError('unqualified radio package member')
            data = archive.extractfile(member).read()
            if name != 'probe-files.sha256':
                if sha(data) != record['probe_files'][name]:
                    raise ValueError('radio member identity')
                add(members, prefix+name, data, stat.S_IFREG | (0o755 if member.mode & 0o111 else 0o644))
        if not set(record['probe_files']) <= seen:
            raise ValueError('incomplete qualified radio package')
    # Only public userspace changes; retain every qualified firmware/module byte.
    replace(members, prefix+'probe-native-wifi.sh', (REPO/'scripts/device/probe-native-wifi.sh').read_bytes())
    timing = dict(re.findall(r'^([a-z_]+)=([0-9]+)$', (REPO/'initramfs/native-wifi/timing').read_text(), re.M))
    if int(timing['outer_seconds']) <= int(timing['radio_seconds']) + int(timing['cleanup_seconds']):
        raise ValueError('outer timeout must cover radio and cleanup')
    if f"--on-active={timing['radio_seconds']}s" not in (REPO/'scripts/device/probe-native-wifi.sh').read_text():
        raise ValueError('radio timeout mismatch')
    for path in sorted((REPO/'initramfs/native-wifi').rglob('*')):
        if path.is_file():
            if path.is_symlink():
                raise ValueError('symlink in native Wi-Fi files')
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
            if members[name] != value:
                raise ValueError('unrelated base member changed')
    verify_radio_composition(members)
    packed = gzip.compress(encode(members), compresslevel=1, mtime=0)
    if entries(gzip.decompress(packed)) != members:
        raise ValueError('newc round trip')
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
    if args.output.exists() or output_record.exists():
        raise ValueError('output already exists')
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
