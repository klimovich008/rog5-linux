#!/usr/bin/env python3
"""Offline tests for scripts/host/rog5-device-profile and the profile blocks.

The reference profile must render every profiled boot source unchanged (so
the reference phone's bundles and wrapper stay byte-identical), and another
phone's profile must change only the block values, keep the scripts valid,
and be refused when it is inconsistent.
"""
from __future__ import annotations

import importlib.util
import re
import subprocess
import tempfile
import unittest
from importlib.machinery import SourceFileLoader
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


def load(name: str, path: Path):
    loader = SourceFileLoader(name, str(path))
    module = importlib.util.module_from_spec(importlib.util.spec_from_loader(name, loader))
    loader.exec_module(module)
    return module


TOOL = load('rog5_device_profile', REPO / 'scripts/host/rog5-device-profile')
GIB = 1 << 30

# A 512 GB phone (5 Pro / Ultimate class): 476.9 GiB LUN, stock userdata
# from the same start to the last usable block, p24 cut from its end.
BIG_DISK = 1000204288
BIG_STOCK_SIZE = BIG_DISK - 18821440 - 40


def stock_inventory(disk=494927872, size=476106392) -> str:
    return '\n'.join([
        'format=rog5-inventory-v1', 'model=ASUS ROG Phone 5', 'memtotal_kib=11000000',
        'memory_reg=00000000800000000000000037100000', 'ufs_nodes=116',
        f'disk=sda sectors={disk} lbs=4096',
        f'part=sda23 number=23 name=userdata start=18821440 sectors={size} '
        'partuuid=8d82ef11-4d42-60e9-24e8-4d6ebf20491b',
        'blkid=TYPE=ext4 LABEL=rog5-linux UUID=11111111-2222-4333-8444-555555555555 ',
    ]) + '\n'


def big_profile() -> dict:
    ref = TOOL.parse(TOOL.REFERENCE.read_text())
    plan = TOOL.plan(TOOL.parse_inventory(stock_inventory(BIG_DISK, BIG_STOCK_SIZE)))
    p = dict(ref)
    p.update({
        'ROG5_PROFILE_NAME': 'test-512g',
        'ROG5_UFS_NODE_COUNT': '118',
        'ROG5_UFS_DISK_SECTORS': str(BIG_DISK),
        'ROG5_USERDATA_SECTORS': str(plan['userdata_sectors']),
        'ROG5_USERDATA_PARTUUID': '0e0e0e0e-1111-4222-8333-444444444444',
        'ROG5_USERDATA_FS_UUID': '11111111-2222-4333-8444-555555555555',
        'ROG5_ROOT_START': str(plan['root_start']),
        'ROG5_ROOT_SECTORS': str(plan['root_sectors']),
        'ROG5_ROOT_FS_UUID': '22222222-3333-4444-8555-666666666666',
        'ROG5_OVERLAY_FS_UUID': '33333333-4444-4555-8666-777777777777',
        'ROG5_OVERLAY_CREATE_BYTES': str(plan['overlay_default_bytes']),
        'ROG5_STATE_FS_UUID': '44444444-5555-4666-8777-888888888888',
        'ROG5_ROOT_SEAL_BYTES': '431',
        'ROG5_ROOT_SEAL_SHA256': 'a' * 64,
        'ROG5_ROOT_AUTHORIZED_KEYS_BYTES': '81',
        'ROG5_ROOT_AUTHORIZED_KEYS_SHA256': 'b' * 64,
    })
    return p


class ReferenceProfile(unittest.TestCase):
    def test_reference_is_valid_and_matches_the_sources(self):
        p = TOOL.load(TOOL.REFERENCE)
        self.assertEqual(p['ROG5_OVERLAY_MANIFEST_SHA256'],
                         'e894abd56cccdfce9ce3292438df022aa9672a8655cac6493b94cfd19d6bad5f')
        self.assertEqual(p['ROG5_STATE_MANIFEST_SHA256'],
                         '2c93224d74394876d1617f193f7ec7c3c1cac4575c95da1dfb233557d0819ea6')
        self.assertEqual(p['ROG5_UFS_DISK_BYTES'], '253403070464')
        self.assertEqual(p['ROG5_ROOT_BYTES'], '34359717888')
        # The reference overlay (182 GiB since 2026-09-29) stays within the boot limit.
        self.assertGreaterEqual(int(p['ROG5_OVERLAY_MAX_BYTES']), 182 * GIB)
        self.assertLess(int(p['ROG5_OVERLAY_MAX_BYTES']), 192 * GIB)

    def test_reference_renders_every_source_unchanged(self):
        p = TOOL.load(TOOL.REFERENCE)
        for rel in TOOL.PROFILED_SOURCES:
            text = (REPO / rel).read_text()
            self.assertEqual(TOOL.render(p, text, rel), text, rel)

    def test_no_reference_literal_outside_the_blocks(self):
        # Every per-phone value lives in the block; the rest of the source
        # refers to it by name.
        ref = TOOL.parse(TOOL.REFERENCE.read_text())
        values = [ref[k] for k in ('ROG5_UFS_DISK_SECTORS', 'ROG5_USERDATA_START', 'ROG5_USERDATA_SECTORS',
                                   'ROG5_ROOT_START', 'ROG5_ROOT_SECTORS', 'ROG5_USERDATA_FS_UUID',
                                   'ROG5_USERDATA_PARTUUID', 'ROG5_ROOT_FS_UUID', 'ROG5_OVERLAY_FS_UUID',
                                   'ROG5_STATE_FS_UUID', 'ROG5_ROOT_SEAL_SHA256', 'ROG5_ROOT_TREE_SHA256',
                                   'ROG5_ROOT_AUTHORIZED_KEYS_SHA256', 'ROG5_ROOT_SYSTEMD_SHA256')]
        for rel in TOOL.PROFILED_SOURCES:
            text = (REPO / rel).read_text()
            outside = text[:text.index(TOOL.BEGIN)] + text[text.index(TOOL.END):]
            for value in values:
                self.assertNotIn(value, outside, f'{rel}: {value} outside the profile block')


class OtherPhone(unittest.TestCase):
    def test_render_changes_only_block_values_and_keeps_scripts_valid(self):
        p = TOOL.validate(big_profile())
        with tempfile.TemporaryDirectory() as tmp:
            for rel in TOOL.PROFILED_SOURCES:
                source = (REPO / rel).read_text()
                rendered = TOOL.render(p, source, rel)
                self.assertNotEqual(rendered, source, rel)
                a, b = source.split('\n'), rendered.split('\n')
                self.assertEqual(len(a), len(b))
                changed = [i for i, (x, y) in enumerate(zip(a, b)) if x != y]
                begin = a.index(next(l for l in a if l.startswith(TOOL.BEGIN)))
                end = a.index(TOOL.END)
                self.assertTrue(all(begin < i < end for i in changed), rel)
                path = Path(tmp) / Path(rel).name
                path.write_text(rendered)
                self.assertEqual(subprocess.run(['sh', '-n', str(path)]).returncode, 0, rel)
                for key in TOOL.block_keys(source):
                    self.assertIn(f'\n{key.lower()}={p[key]}\n', rendered, (rel, key))

    def test_overlay_limit_scales_with_userdata(self):
        p = TOOL.validate(big_profile())
        userdata = int(p['ROG5_USERDATA_BYTES'])
        limit = int(p['ROG5_OVERLAY_MAX_BYTES'])
        self.assertEqual(limit % (1 << 20), 0)
        self.assertEqual(limit, (userdata - 4 * GIB - max(2 * GIB, userdata // 32)) // (1 << 20) * (1 << 20))
        self.assertGreater(limit, 400 * GIB)
        _, default = TOOL.overlay_limits(userdata)
        self.assertLess(default, limit)
        self.assertGreaterEqual(userdata - 4 * GIB - default, max(6 * GIB, userdata // 20))

    def test_inconsistent_profiles_are_refused(self):
        base = big_profile()
        cases = {
            'missing key': lambda p: p.pop('ROG5_STATE_FS_UUID'),
            'misaligned p24': lambda p: p.update(ROG5_ROOT_START=str(int(p['ROG5_ROOT_START']) + 1)),
            'p24 overlaps userdata': lambda p: p.update(ROG5_USERDATA_SECTORS=str(int(p['ROG5_USERDATA_SECTORS']) + 8)),
            'p24 past the disk': lambda p: p.update(ROG5_UFS_DISK_SECTORS=str(int(p['ROG5_ROOT_START']) + 8)),
            'overlay too big': lambda p: p.update(ROG5_OVERLAY_CREATE_BYTES=str(int(p['ROG5_USERDATA_SECTORS']) * 512)),
            'overlay not MiB': lambda p: p.update(ROG5_OVERLAY_CREATE_BYTES=str(17 * GIB + 4096)),
            'shared uuid': lambda p: p.update(ROG5_STATE_FS_UUID=p['ROG5_OVERLAY_FS_UUID']),
        }
        for name, mutate in cases.items():
            with self.subTest(name):
                p = dict(base)
                mutate(p)
                with self.assertRaises(TOOL.ProfileError):
                    TOOL.validate(p)
        for text in ('ROG5_NOPE=1\n', 'ROG5_ROOT_FS_UUID=NOT-A-UUID\n',
                     'ROG5_UFS_NODE_COUNT=117\nROG5_UFS_NODE_COUNT=117\n', 'ROG5_UFS_NODE_COUNT=$(reboot)\n'):
            with self.subTest(text=text), self.assertRaises(TOOL.ProfileError):
                TOOL.parse(text)

    def test_derived_values_in_a_file_are_ignored(self):
        text = TOOL.REFERENCE.read_text() + 'ROG5_OVERLAY_MAX_BYTES=999999999999999\n'
        self.assertEqual(TOOL.validate(TOOL.parse(text))['ROG5_OVERLAY_MAX_BYTES'],
                         TOOL.load(TOOL.REFERENCE)['ROG5_OVERLAY_MAX_BYTES'])

    def test_block_with_an_unknown_name_is_refused(self):
        p = TOOL.load(TOOL.REFERENCE)
        text = f'{TOOL.BEGIN}\nrog5_made_up=1\n{TOOL.END}\n'
        with self.assertRaises(TOOL.ProfileError):
            TOOL.render(p, text)
        with self.assertRaises(TOOL.ProfileError):
            TOOL.render(p, 'no block here\n')


class Planning(unittest.TestCase):
    def test_plan_reproduces_the_reference_layout(self):
        plan = TOOL.plan(TOOL.parse_inventory(stock_inventory()))
        ref = TOOL.parse(TOOL.REFERENCE.read_text())
        self.assertEqual(plan['userdata_start'], int(ref['ROG5_USERDATA_START']))
        self.assertEqual(plan['userdata_sectors'], int(ref['ROG5_USERDATA_SECTORS']))
        self.assertEqual(plan['root_start'], int(ref['ROG5_ROOT_START']))
        self.assertEqual(plan['root_sectors'], int(ref['ROG5_ROOT_SECTORS']))
        self.assertEqual(plan['userdata_ext4_blocks_after_shrink'], 51124696)

    def test_plan_for_a_128_gb_phone_leaves_a_usable_userdata(self):
        disk = 238551040          # ~113.75 GiB LUN
        plan = TOOL.plan(TOOL.parse_inventory(stock_inventory(disk, disk - 18821440 - 40)))
        self.assertGreater(plan['userdata_bytes'], 70 * GIB)
        self.assertGreater(plan['overlay_default_bytes'], 16 * GIB)
        self.assertEqual(plan['root_start'] % 8, 0)

    def test_plan_refuses_bad_root_sizes(self):
        # audit 2026-10-02: 4097 became 4096, -4096 grew userdata past the disk
        inv = TOOL.parse_inventory(stock_inventory())
        for bad in (0, -4096, 4097, 8 * GIB - 4096, 8 * GIB + 512):
            with self.assertRaises(TOOL.ProfileError, msg=str(bad)):
                TOOL.plan(inv, bad)
        self.assertEqual(TOOL.plan(inv, 8 * GIB)['root_bytes'] % 4096, 0)

    def test_plan_refuses_a_userdata_past_the_disk_or_into_the_backup_gpt(self):
        disk = 238551040
        for size in (disk, disk - 18821440, disk - 18821440 - 8, disk - 18821440 - 36):
            with self.assertRaises(TOOL.ProfileError, msg=str(size)):
                TOOL.plan(TOOL.parse_inventory(stock_inventory(disk, size)))
        self.assertGreater(TOOL.plan(TOOL.parse_inventory(stock_inventory(disk, disk - 18821440 - 40)))
                           ['userdata_bytes'], 0)

    def test_plan_refuses_a_partitioned_phone_and_foreign_layouts(self):
        inv = stock_inventory() + ('part=sda24 number=24 name=arch_root_a start=427819008 '
                                   'sectors=67108824 partuuid=00000000-0000-4000-8000-000000000000\n')
        with self.assertRaises(TOOL.ProfileError):
            TOOL.plan(TOOL.parse_inventory(inv))
        with self.assertRaises(TOOL.ProfileError):
            TOOL.parse_inventory(stock_inventory().replace('number=23', 'number=31'))
        with self.assertRaises(TOOL.ProfileError):
            TOOL.parse_inventory('format=something-else\n')

    def test_make_builds_a_valid_profile_from_inventory_and_root_identity(self):
        ref = TOOL.parse(TOOL.REFERENCE.read_text())
        identity = ''.join(f'{k}={ref[k]}\n' for k in TOOL.ROOT_IDENTITY_KEYS)
        identity += 'ROG5_ROOT_FS_UUID=22222222-3333-4444-8555-666666666666\n'
        identity += 'ROG5_ROOT_IMAGE_BYTES=34359717888\n'
        inv = stock_inventory().replace('sectors=476106392', 'sectors=408997568').replace('ufs_nodes=116', 'ufs_nodes=117')
        inv += ('part=sda24 number=24 name=arch_root_a start=427819008 sectors=67108824 '
                'partuuid=00000000-0000-4000-8000-000000000000\n'
                'blkid=TYPE=ext4 LABEL=ROG5_ARCH_A UUID=22222222-3333-4444-8555-666666666666 \n')
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / 'inv').write_text(inv)
            (Path(tmp) / 'id').write_text(identity)
            out = Path(tmp) / 'profile.env'
            args = type('A', (), dict(inventory=str(Path(tmp) / 'inv'), root_identity=str(Path(tmp) / 'id'),
                                      base=None, name='test', output=str(out)))
            self.assertEqual(TOOL.cmd_make(args), 0)
            p = TOOL.load(out)
            self.assertEqual(p['ROG5_UFS_NODE_COUNT'], '117')
            self.assertEqual(p['ROG5_ROOT_FS_UUID'], '22222222-3333-4444-8555-666666666666')
            # a profile made from inventory + identity feeds the installer too
            installer = load('installer', REPO / 'scripts/host/install-default-kernel.py')
            self.assertEqual(installer.storage_identity(out)['p24_size'], '34359717888')
            self.assertEqual(installer.storage_identity(None), installer.storage_identity(TOOL.REFERENCE))
            # Before the flash p24 is empty: accepted; a foreign filesystem is not.
            empty = inv.replace('blkid=TYPE=ext4 LABEL=ROG5_ARCH_A UUID=22222222-3333-4444-8555-666666666666 \n', '')
            (Path(tmp) / 'inv').write_text(empty)
            out.unlink()
            self.assertEqual(TOOL.cmd_make(args), 0)
            foreign = inv.replace('LABEL=ROG5_ARCH_A UUID=22222222-3333-4444-8555-666666666666',
                                  'LABEL=other UUID=99999999-3333-4444-8555-666666666666')
            (Path(tmp) / 'inv').write_text(foreign)
            out.unlink()
            with self.assertRaises(TOOL.ProfileError):
                TOOL.cmd_make(args)

    def test_collect_script_is_valid_read_only_shell(self):
        script = TOOL.COLLECT_SCRIPT
        self.assertEqual(subprocess.run(['sh', '-n'], input=script, text=True).returncode, 0)
        for forbidden in ('dd ', 'mkfs', 'sgdisk', 'blockdev --setrw', '>/dev/sd', 'rm '):
            self.assertNotIn(forbidden, script)


if __name__ == '__main__':
    unittest.main()
