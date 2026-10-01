#!/usr/bin/env python3
"""Offline tests for scripts/device/rog5-install-userspace and its manifest.

The manifest must name existing repository files, unique targets and known
kinds; an install into an empty root must place every file with its mode,
keep a locally edited conf file, and leave --check clean. The install runs
as root inside a user namespace (unshare --map-auto --map-root-user) and is skipped
where that is unavailable.
"""
from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
TOOL = REPO / 'scripts/device/rog5-install-userspace'
MANIFEST = REPO / 'configs/rootfs/userspace.tsv'


def entries():
    rows = []
    for line in MANIFEST.read_text().splitlines():
        line = line.split('#', 1)[0].rstrip()
        if line.strip():
            rows.append([c for c in re.split(r'\t+', line) if c])
    return rows


def userns_available() -> bool:
    if not shutil.which('unshare'):
        return False
    return subprocess.run(['unshare', '--map-auto', '--map-root-user', 'true'], capture_output=True).returncode == 0


class Manifest(unittest.TestCase):
    def test_rows_are_well_formed_and_sources_exist(self):
        targets = set()
        for row in entries():
            kind = row[0]
            self.assertIn(kind, ('file', 'conf', 'build', 'enable', 'disable', 'user-file'), row)
            if kind in ('enable', 'disable'):
                self.assertEqual(len(row), 3, row)
                self.assertIn(row[1], ('system', 'user'), row)
                continue
            self.assertEqual(len(row), 4, row)
            self.assertTrue((REPO / row[1]).is_file(), row)
            self.assertRegex(row[3], r'^0[0-7]{3}$', row)
            if kind != 'user-file':
                self.assertTrue(row[2].startswith('/'), row)
            self.assertNotIn(row[2], targets, row)
            targets.add(row[2])

    def test_enabled_units_are_installed_or_come_from_packages(self):
        installed = {Path(r[2]).name for r in entries() if r[0] in ('file', 'conf')}
        packaged = {'NetworkManager.service', 'bluetooth.service', 'systemd-resolved.service',
                    'systemd-timesyncd.service'}
        for row in entries():
            if row[0] == 'enable':
                self.assertTrue(row[2] in installed or row[2] in packaged, row)

    def test_disabled_units_are_not_also_enabled(self):
        enabled = {(r[1], r[2]) for r in entries() if r[0] == 'enable'}
        for row in entries():
            if row[0] == 'disable':
                self.assertNotIn((row[1], row[2]), enabled, row)

    def test_executables_are_installed_executable(self):
        for row in entries():
            if row[0] == 'file' and row[2].startswith(('/usr/local/bin/', '/usr/local/sbin/', '/usr/local/libexec/')):
                if not row[2].endswith('.c'):
                    self.assertEqual(row[3], '0755', row)

    def test_script_is_valid_posix_shell(self):
        self.assertEqual(subprocess.run(['sh', '-n', str(TOOL)]).returncode, 0)


@unittest.skipUnless(userns_available(), 'needs unshare --map-auto --map-root-user (subordinate ids)')
class Install(unittest.TestCase):
    def run_tool(self, root: Path, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(['unshare', '--map-auto', '--map-root-user', 'sh', str(TOOL), '--root', str(root),
                               '--no-enable', *args], capture_output=True, text=True)

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        # Files owned by the phone user belong to a subordinate id: remove
        # them from inside the namespace.
        self.addCleanup(lambda: subprocess.run(
            ['unshare', '--map-auto', '--map-root-user', 'rm', '-rf', '--', self.tmp]))

    def test_install_check_and_kept_local_edit(self):
        if True:
            root = Path(self.tmp)
            (root / 'etc').mkdir()
            (root / 'etc/passwd').write_text(
                'root:x:0:0::/root:/bin/bash\nphone:x:1000:1000::/home/phone:/bin/bash\n')
            (root / 'home/phone').mkdir(parents=True)
            result = self.run_tool(root)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn('deferred', result.stdout)   # rog5-kms-reset compiles inside the target
            for row in entries():
                if row[0] in ('file', 'conf'):
                    target = root / row[2].lstrip('/')
                    self.assertTrue(target.is_file(), row)
                    self.assertEqual(target.read_bytes(), (REPO / row[1]).read_bytes(), row)
                    self.assertEqual(oct(target.stat().st_mode & 0o7777), oct(int(row[3], 8)), row)
            env = root / 'home/phone/.config/environment.d/60-rog5-mutter.conf'
            self.assertTrue(env.is_file())
            # A local edit of a conf file survives a reinstall and shows in --check.
            perf = root / 'etc/rog5/perf-mode'
            perf.write_text('perf_on_power=always\n')
            result = self.run_tool(root)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(perf.read_text(), 'perf_on_power=always\n')
            check = subprocess.run(['sh', str(TOOL), '--check', '--root', str(root)], capture_output=True, text=True)
            self.assertIn('local-edit', check.stdout)
            # Only the uncompiled helper is missing.
            missing = [l for l in check.stdout.splitlines() if l.startswith(('missing', 'differs'))]
            self.assertEqual(len(missing), 1, missing)
            self.assertIn('rog5-kms-reset', missing[0])
            # A drifted repository-owned file is reported.
            (root / 'etc/drirc').write_text('changed\n')
            check = subprocess.run(['sh', str(TOOL), '--check', '--root', str(root)], capture_output=True, text=True)
            self.assertEqual(check.returncode, 1)
            self.assertIn('differs    /etc/drirc', check.stdout)

    def test_a_link_in_the_home_is_never_followed(self):
        root = Path(self.tmp)
        (root / 'etc').mkdir()
        (root / 'etc/passwd').write_text('phone:x:1000:1000::/home/phone:/bin/bash\n')
        (root / 'home/phone/.config').mkdir(parents=True)
        outside = root / 'outside'
        outside.mkdir()
        (root / 'home/phone/.config/environment.d').symlink_to(outside)
        result = self.run_tool(root)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('refusing symlink', result.stderr)
        self.assertEqual(list(outside.iterdir()), [])


if __name__ == '__main__':
    unittest.main()
