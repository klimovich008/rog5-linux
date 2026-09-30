#!/usr/bin/env python3
"""Offline tests for scripts/host/rog5-build-rootfs (no download, no chroot).

The full build is rehearsed separately (docs/fresh-install-rehearsal.md);
these cases cover the parts that decide what the phone boots: the first
selector and bundle layout of the boot step, the kept filesystem UUID, the
package lists and the namespace entry script.
"""
from __future__ import annotations

import hashlib
import importlib.util
import shutil
import subprocess
import tempfile
import types
import unittest
from importlib.machinery import SourceFileLoader
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
loader = SourceFileLoader('rog5_build_rootfs', str(REPO / 'scripts/host/rog5-build-rootfs'))
TOOL = importlib.util.module_from_spec(importlib.util.spec_from_loader(loader.name, loader))
loader.exec_module(TOOL)


def userns() -> bool:
    return bool(shutil.which('unshare')) and subprocess.run(
        ['unshare', '--map-auto', '--map-root-user', 'true'], capture_output=True).returncode == 0


def args(**overrides):
    base = dict(work=None, ssh_key=None, steps=None, tarball=None, tarball_sig=None, alarm_key=None,
                skip_custom='', phone_password_hash_file=None, image_bytes=TOOL.DEFAULT_IMAGE_BYTES,
                fs_uuid=None, bundle=None, descriptor=None, fallback_bundle=None)
    base.update(overrides)
    return types.SimpleNamespace(**base)


class Static(unittest.TestCase):
    def test_enter_script_is_valid_shell(self):
        self.assertEqual(subprocess.run(['sh', '-n'], input=TOOL.ENTER, text=True).returncode, 0)

    def test_package_lists(self):
        pkgs = [l.split('#')[0].strip() for l in (REPO / 'configs/rootfs/packages.txt').read_text().splitlines()]
        pkgs = [p for p in pkgs if p]
        self.assertEqual(len(pkgs), len(set(pkgs)))
        for required in ('openssh', 'networkmanager', 'phosh', 'phoc', 'gcc', 'lsof', 'squashfs-tools'):
            self.assertIn(required, pkgs)
        for forbidden in ('linux-aarch64', 'linux-firmware', 'gtk2', 'phosh-debug'):
            self.assertNotIn(forbidden, pkgs)
        rows = [l for l in (REPO / 'configs/rootfs/custom-packages.txt').read_text().splitlines()
                if l.strip() and not l.startswith('#')]
        for row in rows:
            cols = [c for c in row.split('\t') if c]
            self.assertEqual(len(cols), 4, row)
            self.assertTrue((REPO / 'packages' / cols[0] / 'PKGBUILD').is_file(), row)

    def test_default_image_is_the_reference_p24(self):
        self.assertEqual(TOOL.DEFAULT_IMAGE_BYTES, 67108824 * 512)


@unittest.skipUnless(userns(), 'needs unshare --map-auto --map-root-user')
class BootStep(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: subprocess.run(['unshare', '--map-auto', '--map-root-user',
                                                'rm', '-rf', '--', str(self.tmp)]))
        (self.tmp / 'work/root/etc').mkdir(parents=True)
        (self.tmp / 'work/root/etc/os-release').write_text('ID=archarm\n')
        (self.tmp / 'work/source.env').write_text('source_archive_size=1\nsource_archive_sha256=' + 'a' * 64 + '\n')
        self.bundle = self.tmp / 'main-k1-d10-261001a'
        self.bundle.mkdir()
        for name in TOOL.BUNDLE_FILES:
            (self.bundle / name).write_bytes(name.encode() + b'\n')

    def test_boot_step_needs_the_sealed_directory(self):
        with self.assertRaises(subprocess.CalledProcessError):
            TOOL.Builder(args(work=str(self.tmp / 'work'), bundle=str(self.bundle))).step_boot()

    def test_v1_selector_and_modes(self):
        builder = TOOL.Builder(args(work=str(self.tmp / 'work'), bundle=str(self.bundle)))
        builder.step_seal()          # makes /boot/rog5-linux and seals the tree
        builder.step_boot()          # verifies the seal again afterwards
        builder.step_boot()          # replacing the bundles keeps it valid too
        linux = self.tmp / 'work/root/boot/rog5-linux'
        selector = (linux / 'selector').read_text()
        self.assertEqual(selector, 'format=rog5-slotb-selector-v1\nbundle=main-k1-d10-261001a\n'
                         f'manifest_sha256={hashlib.sha256(b"manifest" + bytes([10])).hexdigest()}\n')
        self.assertEqual(oct((linux / 'selector').stat().st_mode & 0o777), '0o600')
        self.assertEqual(oct((linux / 'bundles').stat().st_mode & 0o777), '0o700')
        installed = linux / 'bundles' / self.bundle.name
        self.assertEqual(sorted(p.name for p in installed.iterdir()), sorted(TOOL.BUNDLE_FILES))
        self.assertEqual(oct((installed / 'Image').stat().st_mode & 0o777), '0o400')

    def test_bad_bundles_are_refused(self):
        (self.bundle / 'extra').write_text('x')
        with self.assertRaises(SystemExit):
            TOOL.Builder(args(work=str(self.tmp / 'work'), bundle=str(self.bundle))).step_boot()
        (self.bundle / 'extra').unlink()
        with self.assertRaises(SystemExit):   # a fallback needs the primary's descriptor
            TOOL.Builder(args(work=str(self.tmp / 'work'), bundle=str(self.bundle),
                              fallback_bundle=str(self.bundle))).step_boot()

    def test_no_bundle_is_a_no_op(self):
        TOOL.Builder(args(work=str(self.tmp / 'work'))).step_boot()
        self.assertFalse((self.tmp / 'work/root/boot').exists())

    def test_seal_verifies_right_after_sealing(self):
        builder = TOOL.Builder(args(work=str(self.tmp / 'work')))
        builder.step_seal()
        builder.step_seal()          # resealing is repeatable


if __name__ == '__main__':
    unittest.main()
