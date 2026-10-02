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
import re
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

    def test_required_commands_have_packages_and_users(self):
        # Audit 2026-10-02: rog5-firewall.service ran /usr/bin/nft, but
        # nftables (only optional for networkmanager) was not in the list.
        pkgs = {l.split('#')[0].strip() for l in (REPO / 'configs/rootfs/packages.txt').read_text().splitlines()}
        rows = [[c for c in l.split('\t') if c] for l in
                (REPO / 'configs/rootfs/required-commands.tsv').read_text().splitlines()
                if l.strip() and not l.startswith('#')]
        self.assertEqual(len(rows), len(TOOL.required_commands()))
        for path, package, used_by in rows:
            if not package.startswith('dep:'):
                self.assertIn(package, pkgs, f'{path}: package {package} is not in packages.txt')
            text = (REPO / used_by).read_text()
            name = path.rsplit('/', 1)[1]
            self.assertRegex(text, r'(^|[\s/\'"=$({])' + re.escape(name) + r'($|[\s;\'")])',
                             f'{used_by} does not run {name}')
        for needed in ('/usr/bin/nft', '/usr/bin/grim', '/usr/bin/wmenu-run', '/usr/bin/wayvnc'):
            self.assertIn(needed, TOOL.required_commands())
        firewall = (REPO / 'configs/systemd/rog5-firewall.service').read_text()
        self.assertIn('/usr/bin/nft', firewall)
        self.assertIn('nftables', pkgs)


class Signature(unittest.TestCase):
    KEY = TOOL.ALARM_KEY
    SUB = 'B' * 40

    def status(self, *extra, primary=None, good=True):
        lines = ['[GNUPG:] NEWSIG', '[GNUPG:] KEY_CONSIDERED %s 0' % self.KEY, '[GNUPG:] SIG_ID x 2026-10-01 1790000000']
        if good:
            lines.append('[GNUPG:] GOODSIG 77193F152BDBE6A6 Arch Linux ARM Build System <builder@archlinuxarm.org>')
            lines.append('[GNUPG:] VALIDSIG %s 2026-10-01 1790000000 0 4 0 1 10 00 %s' % (self.SUB, primary or self.KEY))
        lines += list(extra)
        lines.append('[GNUPG:] TRUST_UNDEFINED 0 pgp')
        return '\n'.join(lines) + '\n'

    def test_good_signature_by_a_subkey(self):
        self.assertIsNone(TOOL.check_signature_status(0, self.status(), self.KEY))

    def test_revoked_or_expired_keys_and_signatures_are_refused(self):
        # GnuPG prints VALIDSIG next to REVKEYSIG/EXPKEYSIG/EXPSIG
        for word in ('REVKEYSIG', 'EXPKEYSIG', 'EXPSIG', 'BADSIG', 'ERRSIG', 'NO_PUBKEY'):
            why = TOOL.check_signature_status(0, self.status(f'[GNUPG:] {word} 77193F152BDBE6A6 x'), self.KEY)
            self.assertIsNotNone(why, word)
            self.assertIn(word, why)

    def test_exit_status_counts(self):
        self.assertIn('exited', TOOL.check_signature_status(1, self.status(), self.KEY))

    def test_other_key_missing_primary_or_two_signatures(self):
        self.assertIsNotNone(TOOL.check_signature_status(0, self.status(primary='C' * 40), self.KEY))
        bad = self.status().replace(' ' + self.KEY + '\n', '\n')
        self.assertIsNotNone(TOOL.check_signature_status(0, bad, self.KEY))
        self.assertIsNotNone(TOOL.check_signature_status(0, self.status(good=False), self.KEY))
        two = self.status() + self.status()
        self.assertIsNotNone(TOOL.check_signature_status(0, two, self.KEY))

    def test_fetch_uses_the_status_check(self):
        src = (REPO / 'scripts/host/rog5-build-rootfs').read_text()
        fetch = src[src.index('def step_fetch'):src.index('def step_extract')]
        self.assertIn('check_signature_status(status.returncode, status.stdout, ALARM_KEY)', fetch)
        self.assertNotIn('re.search', fetch)    # no bare VALIDSIG match any more


class PasswordHash(unittest.TestCase):
    """The phone PIN hash goes to chpasswd on stdin, never on a command line
    or in the log (synthetic hash only)."""
    HASH = '$6$synthetic$' + 'x' * 86

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        self.key = self.tmp / 'id.pub'
        self.key.write_text('ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAISyntheticKeyBlobForTestsOnly0000000000 me@pc\n')
        self.hash_file = self.tmp / 'phone.hash'
        self.hash_file.write_text(self.HASH + '\n')
        self.hash_file.chmod(0o600)
        (self.tmp / 'work').mkdir()
        self.addCleanup(TOOL.REDACT.clear)

    def builder(self):
        b = TOOL.Builder(args(work=str(self.tmp / 'work'), ssh_key=str(self.key),
                              phone_password_hash_file=str(self.hash_file)))
        b.calls = []
        b.chroot = lambda script, **kw: b.calls.append((script, kw))
        return b

    def test_hash_on_stdin_only(self):
        import contextlib
        import io
        b = self.builder()
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            b.step_accounts()
        scripts = [c[0] for c in b.calls]
        self.assertFalse(any(self.HASH in s for s in scripts), 'hash in a chroot script (argv)')
        self.assertIn(('chpasswd -e', {'input': f'phone:{self.HASH}\n', 'text': True}), b.calls)
        self.assertNotIn(self.HASH, out.getvalue())

    def test_run_refuses_and_log_masks_a_secret(self):
        import contextlib
        import io
        TOOL.REDACT.append(self.HASH)
        with self.assertRaises(SystemExit):
            TOOL.run(['echo', 'x' + self.HASH])
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            TOOL.log('value ' + self.HASH)
        self.assertNotIn(self.HASH, out.getvalue())
        self.assertIn('<redacted>', out.getvalue())

    def test_group_readable_hash_file_is_refused(self):
        self.hash_file.chmod(0o644)
        with self.assertRaises(SystemExit):
            self.builder().step_accounts()


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
