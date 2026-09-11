#!/usr/bin/env python3
"""Exact 05941 RAM boot primitive; import-only with an exact registered profile.

The controller must qualify staging, recovery, capacity and one-use execution.
This module never registers or consumes a claim and never flashes a partition.
"""
import importlib.util
import os
from pathlib import Path
import subprocess

from rog5_composition_profile import load_profile, PROFILE_ID

HERE = Path(__file__).resolve().parent


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# Reuse only size-bound snapshot/capacity primitives. Never change their globals,
# invoke R01 canonical()/boot(), or reuse that experiment's consumed claim.
RAM = load('kernel_hardware_ram_primitives', HERE/'verified-isolated-recovery-boot.py')
BASE = RAM.BASE
CLAIMS = RAM.CLAIMS
SERIAL = 'M5AIKN00F0353YH'
IMAGE_SIZE = 134217728
COMPOSITION_SOURCE = 'f316fe5805448fb0b248515f73c3a7cf036eca03'
PROFILE_SHA256 = 'd253f346de4ba9b0e73203accc5fa86b45820331b55c828e19f9be778ab09c5f'
A01_SHA256 = 'b65597078acd49bf47fadebbf5aff548c64892cc5538aa2aa050472eabd5ddab'


def need(value, message):
    if not value:
        raise ValueError(message)


def expected_fields():
    """Describe the exact claim; registration does not consume its one attempt."""
    profile = load_profile()
    need(profile['profile_sha256'] == PROFILE_SHA256
         and profile['artifacts']['boot_bundle']['size'] == IMAGE_SIZE
         and RAM.IMAGE_SIZE == IMAGE_SIZE and RAM.SERIAL == SERIAL,
         'kernel hardware profile or RAM primitive changed')
    return dict(
        format='rog5-temporary-boot-consumption-v1',
        recovery_profile=PROFILE_ID, candidate=PROFILE_ID,
        target_bundle=profile['bundle'], manifest_sha256=profile['manifest_sha256'],
        boot_image_sha256=profile['artifacts']['boot_bundle']['sha256'],
        recovery_initramfs_sha256=profile['artifacts']['recovery']['sha256'],
        ram_boot_image_size=str(IMAGE_SIZE), trial_id=profile['trial_id'],
        fallback_bundle='persistent-native-root-v11',
        fallback_manifest_sha256='a684bad14f84251ba342a87bde07da1f7b9aea412275ad124f7000716e94bbe2',
        verification_source_commit=COMPOSITION_SOURCE,
        composition_profile_sha256=PROFILE_SHA256, a01_result_sha256=A01_SHA256,
        serial=SERIAL, product='lahaina', usb_path='1-1.2', expected_slot='b',
        recovery_storage='read-only',
        target_storage='accepted-v10-root-overlay-and-v11-service-state',
        qualification='kernel-hardware-headless-trial', flash='forbidden',
        execution='fastboot-boot-ram-bundle', attempt_limit='1', state='BOOT_CLAIMED')


def canonical(expected_sha256, serial):
    expected = expected_fields()
    need(serial == SERIAL and expected_sha256 == expected['boot_image_sha256'],
         'wrong kernel hardware image or device')
    # An offline composition profile is insufficient. This lookup currently
    # requires both exact registration and durable one-use consumption.
    raw = CLAIMS.expected_record(PROFILE_ID)
    need(type(raw) is bytes and len(raw) <= 8192 and raw.endswith(b'\n'),
         'invalid kernel hardware claim encoding')
    rows = [line.split('=', 1) for line in raw.decode('ascii').splitlines()]
    need(all(len(row) == 2 for row in rows)
         and len({row[0] for row in rows}) == len(rows), 'ambiguous kernel hardware claim')
    record = dict(rows)
    need(record == expected, 'not the exact kernel hardware claim')
    CLAIMS.verify_entered(PROFILE_ID)
    return record


def download_capacity(serial):
    expected_fields()
    need(serial == SERIAL, 'wrong kernel hardware serial')
    return RAM.download_capacity(serial)


def replay_capacity(value):
    expected_fields()
    return RAM.replay_capacity(value)


def sealed_snapshot(image, expected_sha256):
    expected = expected_fields()
    need(expected_sha256 == expected['boot_image_sha256'], 'wrong kernel hardware image')
    return RAM.sealed_snapshot(image, expected_sha256)


def boot(image, expected_sha256, serial):
    need(os.environ.get('ALLOW_TEMPORARY_BOOT') == '1'
         and os.environ.get('ALLOW_HEADLESS_LIVE_GATE') == '1',
         'explicit kernel hardware execution environment required')
    canonical(expected_sha256, serial)
    BASE.validate_fastboot()
    snapshot = sealed_snapshot(image, expected_sha256)
    try:
        subprocess.run([str(BASE.FASTBOOT), '-s', serial, 'boot', f'/proc/self/fd/{snapshot}'],
                       check=True, stdin=subprocess.DEVNULL, pass_fds=(snapshot,))
    finally:
        os.close(snapshot)


if __name__ == '__main__':
    raise SystemExit('Import-only kernel hardware helper; a separately admitted one-use controller is required')
