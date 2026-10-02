#!/usr/bin/env python3
"""Offline tests of rog5-memory-tune against a fake /sys, /proc/sys and /etc."""
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
TOOL = HERE / 'rog5-memory-tune'
CONF = HERE.parent.parent / 'configs' / 'rog5' / 'memory'
SHELLS = [s for s in ('sh', 'dash', 'busybox') if shutil.which(s)]


class MemoryTuneTest(unittest.TestCase):
    shell = 'sh'

    def setUp(self):
        self.t = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.t)
        thp = self.t / 'sys/kernel/mm/transparent_hugepage'
        (thp / 'khugepaged').mkdir(parents=True)
        (thp / 'khugepaged/max_ptes_none').write_text('511\n')
        (thp / 'shrink_underused').write_text('0\n')
        (thp / 'hugepages-64kB').mkdir()
        (thp / 'hugepages-64kB/enabled').write_text('always inherit madvise [never]\n')
        (self.t / 'proc/sys/vm').mkdir(parents=True)
        (self.t / 'proc/sys/vm/watermark_boost_factor').write_text('15000\n')
        (self.t / 'etc').mkdir()
        (self.t / 'meminfo').write_text('MemTotal: 10866028 kB\nAnonHugePages: 903168 kB\nShmemHugePages: 276480 kB\n')
        (self.t / 'vmstat').write_text('thp_underused_split_page 7\n')
        self.conf = self.t / 'memory'
        shutil.copy(CONF, self.conf)
        self.env = dict(os.environ,
                        ROG5_MEMORY_CONF=str(self.conf), ROG5_MEMORY_SYSFS=str(self.t / 'sys'),
                        ROG5_MEMORY_PROCSYS=str(self.t / 'proc/sys'), ROG5_MEMORY_ETC=str(self.t / 'etc'),
                        ROG5_MEMORY_STATE=str(self.t / 'state/masks'),
                        ROG5_MEMORY_MEMINFO=str(self.t / 'meminfo'), ROG5_MEMORY_VMSTAT=str(self.t / 'vmstat'))

    def run_tool(self, *args, rc=0):
        argv = [self.shell, str(TOOL), *args] if self.shell != 'busybox' else ['busybox', 'sh', str(TOOL), *args]
        r = subprocess.run(argv, env=self.env, capture_output=True, text=True, timeout=30)
        self.assertEqual(r.returncode, rc, r.stdout + r.stderr)
        return r

    def read(self, rel):
        return (self.t / rel).read_text().strip()

    def dropins(self):
        return [self.t / 'etc/systemd/system.conf.d/60-rog5-malloc-thp.conf',
                self.t / 'etc/systemd/user.conf.d/60-rog5-malloc-thp.conf']

    def test_defaults_apply(self):
        r = self.run_tool('apply')
        self.assertEqual(self.read('sys/kernel/mm/transparent_hugepage/khugepaged/max_ptes_none'), '409')
        self.assertEqual(self.read('sys/kernel/mm/transparent_hugepage/shrink_underused'), '1')
        self.assertEqual(self.read('proc/sys/vm/watermark_boost_factor'), '0')
        for f in self.dropins():
            text = f.read_text()
            self.assertIn('[Manager]\nDefaultEnvironment=GLIBC_TUNABLES=glibc.malloc.hugetlb=0\n', text)
            self.assertTrue(text.startswith('# Written by rog5-memory-tune'))
        self.assertIn('next boot', r.stdout)
        self.assertFalse((self.t / 'etc/systemd/user').exists() and any((self.t / 'etc/systemd/user').iterdir()))
        # idempotent: nothing to report the second time
        self.assertNotIn('next boot', self.run_tool('apply').stdout)

    def test_config_values_and_invalid_fallbacks(self):
        self.conf.write_text('malloc_thp = on  # keep glibc default\nthp_max_ptes_none=256\nwatermark_boost_factor=5000\n')
        self.run_tool('apply')
        self.assertEqual(self.read('sys/kernel/mm/transparent_hugepage/khugepaged/max_ptes_none'), '256')
        self.assertEqual(self.read('proc/sys/vm/watermark_boost_factor'), '5000')
        self.assertFalse(any(f.exists() for f in self.dropins()))
        self.conf.write_text('malloc_thp=maybe\nthp_max_ptes_none=512\nwatermark_boost_factor=-1\n')
        r = self.run_tool('apply')
        self.assertEqual(self.read('sys/kernel/mm/transparent_hugepage/khugepaged/max_ptes_none'), '409')
        self.assertEqual(self.read('proc/sys/vm/watermark_boost_factor'), '0')
        self.assertTrue(all(f.exists() for f in self.dropins()))
        for word in ('malloc_thp=maybe', 'thp_max_ptes_none=512', 'watermark_boost_factor=-1'):
            self.assertIn(word, r.stderr)

    def test_masks_created_recorded_and_removed(self):
        user = self.t / 'etc/systemd/user'
        user.mkdir(parents=True)
        os.symlink('/dev/null', user / 'admin.service')            # the admin's own mask
        (user / 'real.service').write_text('[Service]\n')           # a real unit file
        self.conf.write_text('mask_user_units="evolution-alarm-notify.service localsearch-3.service admin.service '
                             'real.service org.gnome.SettingsDaemon.Wwan.service gnome-software.service '
                             'bad/../x.service foo.timer"\n')
        r = self.run_tool('apply')
        self.assertIn('next login', r.stdout)
        self.assertEqual(os.readlink(user / 'evolution-alarm-notify.service'), '/dev/null')
        self.assertEqual(os.readlink(user / 'localsearch-3.service'), '/dev/null')
        self.assertFalse((user / 'org.gnome.SettingsDaemon.Wwan.service').exists())
        self.assertFalse((user / 'gnome-software.service').exists())
        self.assertEqual((user / 'real.service').read_text(), '[Service]\n')
        self.assertEqual(self.read('state/masks').split(), ['evolution-alarm-notify.service', 'localsearch-3.service'])
        for word in ('refusing to mask org.gnome.SettingsDaemon.Wwan', 'refusing to mask gnome-software',
                     'bad unit name bad/../x.service', 'only .service', 'real.service exists'):
            self.assertIn(word, r.stderr)
        # dropping one from the list removes only that mask; the admin's stays
        self.conf.write_text('mask_user_units=localsearch-3.service admin.service\n')
        self.run_tool('apply')
        self.assertFalse(os.path.lexists(user / 'evolution-alarm-notify.service'))
        self.assertTrue(os.path.islink(user / 'localsearch-3.service'))
        self.assertTrue(os.path.islink(user / 'admin.service'))
        self.assertEqual(self.read('state/masks').split(), ['localsearch-3.service'])
        self.run_tool('revert')
        self.assertFalse(os.path.lexists(user / 'localsearch-3.service'))
        self.assertTrue(os.path.islink(user / 'admin.service'))

    def test_mask_failures_are_reported_and_ownership_kept(self):
        user = self.t / 'etc/systemd/user'
        user.mkdir(parents=True)
        self.conf.write_text('mask_user_units=localsearch-3.service\n')
        # creation fails: not recorded, non-zero
        user.chmod(0o555)
        self.addCleanup(user.chmod, 0o755)
        r = self.run_tool('apply', rc=1)
        self.assertIn('could not mask localsearch-3.service', r.stderr)
        self.assertFalse(os.path.lexists(user / 'localsearch-3.service'))
        self.assertEqual(self.read('state/masks').split(), [])
        # created and recorded once possible
        user.chmod(0o755)
        self.run_tool('apply')
        self.assertEqual(self.read('state/masks').split(), ['localsearch-3.service'])
        # removal fails: still recorded (so a later revert retries), non-zero
        user.chmod(0o555)
        r = self.run_tool('revert', rc=1)
        self.assertIn('could not remove the mask', r.stderr)
        self.assertTrue(os.path.islink(user / 'localsearch-3.service'))
        self.assertEqual(self.read('state/masks').split(), ['localsearch-3.service'])
        user.chmod(0o755)
        self.run_tool('revert')
        self.assertFalse(os.path.lexists(user / 'localsearch-3.service'))
        self.assertEqual(self.read('state/masks').split(), [])

    def test_revert_restores_defaults_and_keeps_foreign_dropin(self):
        self.run_tool('apply')
        foreign = self.t / 'etc/systemd/user.conf.d/60-rog5-malloc-thp.conf'
        foreign.write_text('[Manager]\nDefaultEnvironment=FOO=1\n')
        r = self.run_tool('revert', rc=1)
        self.assertEqual(self.read('sys/kernel/mm/transparent_hugepage/khugepaged/max_ptes_none'), '511')
        self.assertEqual(self.read('proc/sys/vm/watermark_boost_factor'), '15000')
        self.assertFalse(self.dropins()[0].exists())
        self.assertEqual(foreign.read_text(), '[Manager]\nDefaultEnvironment=FOO=1\n')
        self.assertIn('not written by rog5-memory-tune', r.stderr)
        # apply never overwrites it either
        r = self.run_tool('apply', rc=1)
        self.assertEqual(foreign.read_text(), '[Manager]\nDefaultEnvironment=FOO=1\n')
        self.assertTrue(self.dropins()[0].exists())

    def test_dropin_write_failure_is_reported(self):
        (self.t / 'etc/systemd').mkdir(parents=True)
        (self.t / 'etc/systemd/user.conf.d').write_text('not a directory\n')
        r = self.run_tool('apply', rc=1)
        self.assertIn('could not write', r.stderr)
        self.assertTrue(self.dropins()[0].exists())

    def test_mthp_64k_choice(self):
        f = self.t / 'sys/kernel/mm/transparent_hugepage/hugepages-64kB/enabled'
        self.run_tool('apply')
        self.assertEqual(f.read_text(), 'always inherit madvise [never]\n')   # default: untouched
        self.conf.write_text('anon_mthp_64k=always\n')
        self.run_tool('apply')
        self.assertEqual(f.read_text().strip(), 'always')   # the fake file keeps what was written
        self.assertIn('anon_mthp_64k: always (live ', self.run_tool('status').stdout)
        self.conf.write_text('anon_mthp_64k=sometimes\n')
        r = self.run_tool('apply')
        self.assertIn('anon_mthp_64k=sometimes', r.stderr)
        self.assertEqual(f.read_text().strip(), 'never')
        self.run_tool('revert')
        self.assertEqual(f.read_text().strip(), 'never')

    def test_missing_knob_is_skipped_not_fatal(self):
        (self.t / 'sys/kernel/mm/transparent_hugepage/shrink_underused').unlink()
        r = self.run_tool('apply')
        self.assertIn('kernel without it', r.stderr)
        self.assertEqual(self.read('sys/kernel/mm/transparent_hugepage/khugepaged/max_ptes_none'), '409')

    def test_status(self):
        self.run_tool('apply')
        out = self.run_tool('status').stdout
        self.assertIn('malloc_thp: off (drop-in: present', out)
        self.assertIn('thp_max_ptes_none: 409 (live 409, shrink_underused 1)', out)
        self.assertIn('watermark_boost_factor: 0 (live 0)', out)
        self.assertIn('AnonHugePages: 882 MiB, ShmemHugePages: 270 MiB', out)
        self.assertIn('thp_underused_split_page: 7', out)
        self.run_tool('bogus', rc=2)

    def test_service_and_manifest(self):
        repo = HERE.parent.parent
        unit = (repo / 'configs/systemd/rog5-memory-tune.service').read_text()
        self.assertIn('ExecStart=/usr/local/sbin/rog5-memory-tune apply', unit)
        self.assertIn('After=systemd-tmpfiles-setup.service systemd-sysctl.service', unit)
        rows = (repo / 'configs/rootfs/userspace.tsv').read_text()
        self.assertIn('scripts/device/rog5-memory-tune\t/usr/local/sbin/rog5-memory-tune\t0755', rows)
        self.assertIn('conf\tconfigs/rog5/memory\t/etc/rog5/memory\t0644', rows)
        self.assertIn('enable\tsystem\trog5-memory-tune.service', rows)


# The same cases under every POSIX shell on the host (dash/busybox when present).
for _shell in SHELLS[1:]:
    globals()[f'MemoryTune_{_shell}'] = type(f'MemoryTune_{_shell}', (MemoryTuneTest,), {'shell': _shell})

if __name__ == '__main__':
    unittest.main()
