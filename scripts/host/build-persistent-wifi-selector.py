#!/usr/bin/env python3
"""Generate selector v2 after both signed bundle manifests exist."""

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import stat


REPO = Path(__file__).resolve().parents[2]
PARSER_PATH = REPO/'scripts/device/build-native-wifi-boot-initramfs.py'
SPEC = importlib.util.spec_from_file_location('rog5_wifi_archive', PARSER_PATH)
PARSER = importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(PARSER)
FALLBACK_BUNDLE = 'persistent-native-root-v11'
FALLBACK_MANIFEST_SHA256 = 'a684bad14f84251ba342a87bde07da1f7b9aea412275ad124f7000716e94bbe2'


def read_regular(path):
    metadata = path.lstat()
    assert stat.S_ISREG(metadata.st_mode) and metadata.st_nlink == 1
    data = path.read_bytes()
    assert 1 <= len(data) <= 4096
    return data


def manifest(data):
    text = data.decode('ascii')
    assert '\r' not in text and text.endswith('\n')
    rows = text.splitlines()
    assert rows[0] == 'format=rog5-recovery-bundle-v2'
    fields = {}
    for row in rows:
        assert row.count('=') == 1
        name, value = row.split('=', 1)
        assert name not in fields and name and value
        fields[name] = value
    assert set(fields) == {
        'format', 'bundle', 'profile', 'kernel_size', 'kernel_sha256',
        'dtb_size', 'dtb_sha256', 'initramfs_size', 'initramfs_sha256',
        'target_id', 'target_release', 'rollback_timeout', 'target_timeout',
        'a660_command_manifest_sha256', 'root_generation', 'root_tree_sha256',
        'root_seal_sha256', 'root_tree_entries', 'root_subtree',
    }
    assert fields['profile'] == 'persistent-root-ro-v1'
    assert fields['bundle'] == fields['target_id']
    assert fields['rollback_timeout'] == '900' and fields['target_timeout'] == '600'
    return fields


def generate(descriptor_data, primary_manifest, fallback_manifest,
             expected_fallback_bundle=None,
             expected_fallback_manifest_sha256=None):
    if expected_fallback_bundle is None:
        expected_fallback_bundle = FALLBACK_BUNDLE
    if expected_fallback_manifest_sha256 is None:
        expected_fallback_manifest_sha256 = FALLBACK_MANIFEST_SHA256
    trial = PARSER.parse_trial_descriptor(descriptor_data)
    primary = manifest(primary_manifest)
    fallback = manifest(fallback_manifest)
    assert primary['bundle'] == trial['primary_bundle']
    assert fallback['bundle'] == expected_fallback_bundle
    fallback_hash = hashlib.sha256(fallback_manifest).hexdigest()
    assert fallback_hash == expected_fallback_manifest_sha256
    primary_hash = hashlib.sha256(primary_manifest).hexdigest()
    selector = (
        'format=rog5-slotb-selector-v2\n'
        f"trial_id={trial['trial_id']}\n"
        f"primary_bundle={primary['bundle']}\n"
        f'primary_manifest_sha256={primary_hash}\n'
        f"fallback_bundle={fallback['bundle']}\n"
        f'fallback_manifest_sha256={fallback_hash}\n'
        'mode=try-once\n').encode()
    return selector, {
        'format': 'rog5-persistent-wifi-selector-generation-v1',
        'trial_id': trial['trial_id'],
        'primary_bundle': primary['bundle'],
        'primary_manifest_sha256': primary_hash,
        'fallback_bundle': fallback['bundle'],
        'fallback_manifest_sha256': fallback_hash,
        'selector_sha256': hashlib.sha256(selector).hexdigest(),
        'authority': 'none; selector generation does not stage or select it',
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--trial-descriptor', type=Path, required=True)
    parser.add_argument('--primary-manifest', type=Path, required=True)
    parser.add_argument('--fallback-manifest', type=Path, required=True)
    parser.add_argument('--expected-fallback-bundle', default=FALLBACK_BUNDLE)
    parser.add_argument('--expected-fallback-manifest-sha256',
                        default=FALLBACK_MANIFEST_SHA256)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    record = Path(str(args.output)+'.json')
    assert not args.output.exists() and not record.exists()
    selector, result = generate(read_regular(args.trial_descriptor),
                                read_regular(args.primary_manifest),
                                read_regular(args.fallback_manifest),
                                args.expected_fallback_bundle,
                                args.expected_fallback_manifest_sha256)
    old_umask = os.umask(0o077)
    try:
        with args.output.open('xb') as stream:
            stream.write(selector); stream.flush(); os.fsync(stream.fileno())
        with record.open('x') as stream:
            json.dump(result, stream, indent=2); stream.flush(); os.fsync(stream.fileno())
    finally:
        os.umask(old_umask)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
