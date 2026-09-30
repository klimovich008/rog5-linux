#!/usr/bin/env python3
"""USB disks stay outside the exact 117-node UFS scope, which stays exact.

Replays the real storage-scope code of the production ramdisk and runtime
(init, power/USB step, state service, attestor, trial commit, rog5-update,
Wi-Fi guard, legacy healthy check) against a fake sysfs: 117 UFS nodes (sda
and 116 partitions) plus a hub's card reader (sdh, empty, cannot be opened)
and a writable flash drive (sdi, sdi1), both under a usbN bus. 118 non-USB
nodes and 116 UFS nodes must still fail, and a mounted disk still stops the
init's storage lock. ROG5_TEST_BUSYBOX/ROG5_TEST_QEMU run the shell code under
the target's ARM64 BusyBox.
"""
import os
from pathlib import Path
import re
import subprocess
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[2]
INIT = REPO/'initramfs/persistent-root-init'
POWER = REPO/'scripts/device/load-persistent-root-power-usb.sh'
STATE = REPO/'initramfs/persistent-service-state'
ATTEST = REPO/'initramfs/persistent-root-attest'
HEALTHY = REPO/'initramfs/native-wifi-persistent/healthy'
COMMIT = REPO/'initramfs/production-trial-commit'
UPDATE = REPO/'initramfs/rog5-update'
WIFI = REPO/'initramfs/production-wifi'
UFS = 'devices/platform/soc/1d84000.ufshc/host0/target0:0:0/0:0:0:0/block'
USB = ('devices/platform/soc/a600000.usb/a600000.usb/xhci-hcd.1.auto/usb1/1-1/1-1.1/'
       '1-1.1:1.0/host1/target1:0:0/1:0:0:0/block')
USB_TEST = "*/usb[0-9]*/*) "


def function(path, name):
    match = re.search(r'^'+name+r'\(\) \{\n.*?^\}\n', path.read_text(), re.M | re.S)
    assert match, name
    return match.group()


def between(path, start, end):
    text = path.read_text()
    first = text.index(start)
    last = text.index(end, first)+len(end)
    return text[first:last]+'\n'


class Scope(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def node(self, parent, name, partitions=0, ro='0', size='0'):
        disk = self.root/'sys'/parent/name
        (disk/'device').mkdir(parents=True)
        (disk/'queue').mkdir()
        (disk/'queue/logical_block_size').write_text('4096\n')
        nodes = [(disk, name, 0)]
        for number in range(1, partitions+1):
            (disk/f'{name}{number}').mkdir()
            (disk/f'{name}{number}/partition').write_text(f'{number}\n')
            nodes.append((disk/f'{name}{number}', f'{name}{number}', number))
        for directory, node, number in nodes:
            (directory/'dev').write_text(f'8:{number}\n')
            (directory/'ro').write_text(ro+'\n')
            (directory/'size').write_text(size+'\n')
            (directory/'start').write_text('0\n')
            (directory/'uevent').write_text(f'DEVNAME={node}\nPARTNAME=p{number}\n')
            (self.root/'sys/class/block'/node).symlink_to(directory)
            (self.root/'dev'/node).write_text('')

    def fixture(self, extra=False, missing=False, ro='1'):
        (self.root/'sys/class/block').mkdir(parents=True)
        (self.root/'dev').mkdir()
        (self.root/'mountinfo').write_text('')
        self.node(UFS, 'sda', 116, ro)
        self.node(USB, 'sdh')
        self.node(USB.replace('1-1.1', '1-1.2'), 'sdi', 1)
        if extra:
            self.node(UFS.replace('0:0:0:0', '0:0:0:7'), 'sdj', 0, ro)
        if missing:
            partition = self.root/'sys'/UFS/'sda/sda116'
            for name in partition.iterdir():
                name.unlink()
            partition.rmdir()
            (self.root/'sys/class/block/sda116').unlink()
            (self.root/'dev/sda116').unlink()

    def sh(self, text, body):
        root = str(self.root)
        for old, new in (('/sys/class/block', root+'/sys/class/block'),
                         ('/sys/dev/block', root+'/sys/dev/block'),
                         ('/proc/self/mountinfo', root+'/mountinfo'),
                         ('/run/', root+'/run-'),
                         ('device=/dev/', 'device='+root+'/dev/'),
                         ('[ -b "$device" ]', '[ -e "$device" ]')):
            text = text.replace(old, new)
        # blockdev models the sysfs ro flag. An empty USB card reader cannot
        # be opened (ENOMEDIUM), so any open of a USB node fails and is logged.
        stub = f'''root={root}
log() {{ :; }}
blockdev() {{
	name=${{2##*/}}
	printf '%s %s\\n' "$1" "$name" >>"$root/blockdev.log"
	case $name in sdh*|sdi*) return 1 ;; esac
	flag=$(readlink -f "$root/sys/class/block/$name")/ro
	case $1 in
		--setro) echo 1 >"$flag" ;;
		--setrw) echo 0 >"$flag" ;;
		--getro) cat "$flag" ;;
		*) return 1 ;;
	esac
}}
runtime_blockdev() {{ blockdev "$@"; }}
bb() {{ "$@"; }}
'''
        shell, env = ['sh'], dict(os.environ)
        if os.environ.get('ROG5_TEST_BUSYBOX'):
            qemu, busybox = os.environ['ROG5_TEST_QEMU'], os.environ['ROG5_TEST_BUSYBOX']
            applets = self.root/'applets'
            applets.mkdir(exist_ok=True)
            for name in ('readlink', 'cat', 'basename', 'wc', 'sed'):
                (applets/name).write_text(f'#!/bin/sh\nexec {qemu} {busybox} {name} "$@"\n')
                (applets/name).chmod(0o755)
            shell, env['PATH'] = [qemu, busybox, 'sh'], f'{applets}:{env["PATH"]}'
        return subprocess.run(shell, input='set -u\n'+stub+text+'\n'+body, text=True,
                              capture_output=True, env=env, timeout=600)

    def touched_usb(self):
        log = self.root/'blockdev.log'
        return log.exists() and re.search(r' sd[hi]', log.read_text()) is not None

    # persistent-root-init ------------------------------------------------
    INIT_FUNCTIONS = ('usb_attached_block', 'has_block_backed_mount', 'physical_topology_count',
                      'lock_physical_storage', 'verify_physical_storage_read_only',
                      'write_ufs_inventory', 'verify_exact_overlay_write_window',
                      'hold_usb_storage_scan', 'release_usb_storage_scan')

    def init(self, body):
        text = ''.join(function(INIT, name) for name in self.INIT_FUNCTIONS)
        text = text.replace('$usb_storage_delay', '$root/delay_use')
        return self.sh('expected_physical_count=117\n'+text, body)

    def test_init_topology_lock_and_inventory_ignore_usb_disks(self):
        self.fixture(ro='0')
        result = self.init(
            'physical_topology_count\n'
            'lock_physical_storage || exit 10\n'
            'verify_physical_storage_read_only || exit 11\n'
            'write_ufs_inventory || exit 12\n'
            f'overlay_userdata_disk={self.root}/dev/sda; overlay_userdata={self.root}/dev/sda23\n'
            'blockdev --setrw "$overlay_userdata_disk"; blockdev --setrw "$overlay_userdata"\n'
            'verify_exact_overlay_write_window || exit 13\n')
        self.assertEqual((result.returncode, result.stdout), (0, '117\n'), result.stderr)
        self.assertEqual((self.root/'run-rog5-physical-block-count').read_text(), '117\n')
        self.assertEqual(len((self.root/'run-rog5-p2-ufs-inventory.tsv').read_text().splitlines()), 118)
        self.assertFalse(self.touched_usb())
        self.assertEqual((self.root/'sys'/USB/'sdh/ro').read_text(), '0\n')

    def test_init_stays_exact_for_non_usb_nodes(self):
        for case in ('extra', 'missing'):
            with self.subTest(case=case):
                self.setUp()
                self.fixture(extra=case == 'extra', missing=case == 'missing', ro='0')
                result = self.init(
                    'physical_topology_count\n'
                    'lock_physical_storage && exit 10\n'
                    'verify_physical_storage_read_only && exit 11\n'
                    'write_ufs_inventory && exit 12\nexit 0\n')
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stdout, '118\n' if case == 'extra' else '116\n')

    def test_init_mounted_disk_still_stops_the_lock(self):
        self.fixture(ro='0')
        (self.root/'sys/dev/block/8:1').mkdir(parents=True)
        (self.root/'mountinfo').write_text('40 25 8:1 / /media/usb rw - vfat /dev/sdi1 rw\n')
        result = self.init('lock_physical_storage && exit 10\nexit 0\n')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse((self.root/'blockdev.log').exists())

    def test_init_delays_the_usb_scan_until_ufs_is_locked(self):
        self.fixture()
        (self.root/'delay_use').write_text('1\n')
        result = self.init('hold_usb_storage_scan; cat "$root/delay_use"\n'
                           'release_usb_storage_scan; cat "$root/delay_use"\n')
        self.assertEqual((result.returncode, result.stdout), (0, '60\n1\n'), result.stderr)
        source = INIT.read_text()
        hold = source.index('\nhold_usb_storage_scan\n')
        self.assertLess(hold, source.index('if [ -x /sbin/rog5-load-persistent-power-usb ]; then'))
        release = source.index('\nrelease_usb_storage_scan\n')
        self.assertLess(source.index('if ! lock_physical_storage; then'), release)
        self.assertLess(release, source.index('publish_or_rollback userdata-resolved ENTER'))
        (self.root/'delay_use').unlink()
        self.assertEqual(self.init('hold_usb_storage_scan && release_usb_storage_scan').returncode, 0)

    def test_init_resolution_and_every_scope_loop_skip_usb(self):
        source = INIT.read_text()
        self.assertIn('$expected_physical_count', function(INIT, 'lock_physical_storage'))
        # The count comes from the device profile block (reference phone: 117).
        self.assertIn('expected_physical_count=$rog5_ufs_node_count\n', source)
        self.assertIn('rog5_ufs_node_count=117\n', source)
        for name in ('physical_topology_count', 'lock_physical_storage',
                     'verify_physical_storage_read_only', 'find_exact_userdata',
                     'find_exact_arch_root', 'write_ufs_inventory',
                     'verify_exact_userdata_write_window'):
            self.assertIn('! usb_attached_block "$sys_disk" || continue', function(INIT, name), name)
        self.assertIn('! usb_attached_block "$sys_block" || continue',
                      function(INIT, 'verify_exact_overlay_write_window'))
        self.assertIn(USB_TEST, function(INIT, 'usb_attached_block'))

    # power/USB step --------------------------------------------------------
    def test_power_usb_only_rejects_non_usb_disks_before_ufs(self):
        loop = between(POWER, 'physical_count=0\n', "'storage appeared before the UFS stage'")
        for case, expected in (('usb-only', 0), ('ufs', 1)):
            with self.subTest(case=case):
                self.setUp()
                (self.root/'sys/class/block').mkdir(parents=True)
                (self.root/'dev').mkdir()
                self.node(USB, 'sdh')
                self.node(USB.replace('1-1.1', '1-1.2'), 'sdi', 1)
                if case == 'ufs':
                    self.node(UFS, 'sda', 2)
                result = self.sh('fail() { exit 1; }\n'+loop, 'exit 0\n')
                self.assertEqual(result.returncode, expected, result.stderr)

    # persistent-service-state ----------------------------------------------
    def test_state_service_scope_ignores_usb_disks(self):
        text = ''.join(function(STATE, name) for name in
                       ('usb_attached_block', 'verify_storage_read_only', 'verify_write_window',
                        'relock_storage'))
        body = (f'userdata_disk={self.root}/dev/sda; userdata={self.root}/dev/sda23\n'
                'relock_storage || exit 10\nverify_storage_read_only || exit 11\n'
                'blockdev --setrw "$userdata_disk"; blockdev --setrw "$userdata"\n'
                'verify_write_window || exit 12\nrelock_storage || exit 13\n')
        self.fixture(ro='0')
        result = self.sh('expected_physical_count=117\n'+text, body)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(self.touched_usb())
        for case in ('extra', 'missing'):
            with self.subTest(case=case):
                self.setUp()
                self.fixture(extra=case == 'extra', missing=case == 'missing', ro='0')
                result = self.sh('expected_physical_count=117\n'+text, body)
                self.assertEqual(result.returncode, 10, result.stderr)

    # persistent-root-attest --------------------------------------------------
    def test_attestor_topology_ignores_usb_disks(self):
        snippet = between(ATTEST, 'physical_count=0\n', "fail 'physical topology count changed'")
        for case, code in (('usb', 0), ('extra', 1), ('missing', 1)):
            with self.subTest(case=case):
                self.setUp()
                prefix = ('fail() { echo "$*"; exit 1; }\nexpected_physical_count=117\n'
                          'expected_persistent_overlay_mode=1\n'
                          f'overlay_disk={self.root}/dev/sda; overlay_userdata={self.root}/dev/sda23\n')
                self.fixture(extra=case == 'extra', missing=case == 'missing')
                for name in ('sda', 'sda/sda23'):
                    (self.root/'sys'/UFS/name/'ro').write_text('0\n')
                result = self.sh(prefix+snippet, 'exit 0\n')
                self.assertEqual(result.returncode, code, result.stdout+result.stderr)
                self.assertFalse(self.touched_usb())

    # runtime health and write-scope gates -------------------------------------
    def runtime_fixture(self, **kwargs):
        self.fixture(**kwargs)
        for name in ('sda', 'sda/sda23'):
            (self.root/'sys'/UFS/name/'ro').write_text('0\n')

    def test_trial_commit_and_update_health_ignore_writable_usb_disks(self):
        for path in (COMMIT, UPDATE):
            loop = between(path, '\tfor node in "$sys"/class/block/sd*; do\n', '\tdone\n')
            for case, code in (('usb', 0), ('extra', 1)):
                with self.subTest(path=path.name, case=case):
                    self.setUp()
                    text = f'sys={self.root}/sys\nscope() {{\n{loop}\treturn 0\n}}\n'
                    self.runtime_fixture(extra=case == 'extra')
                    if case == 'extra':
                        (self.root/'sys'/UFS.replace('0:0:0:0', '0:0:0:7')/'sdj/ro').write_text('0\n')
                    result = self.sh(text, 'scope\n')
                    self.assertEqual(result.returncode, code, result.stderr)

    def test_wifi_guard_write_scope_ignores_usb_disks(self):
        snippet = between(WIFI, '\twritable=\n', 'fail "write scope is$writable" ;; esac\n')
        for case, code in (('usb', 0), ('extra', 1)):
            with self.subTest(case=case):
                self.setUp()
                self.runtime_fixture(extra=case == 'extra')
                if case == 'extra':
                    (self.root/'sys'/UFS.replace('0:0:0:0', '0:0:0:7')/'sdj/ro').write_text('0\n')
                result = self.sh(f'sys={self.root}/sys\nfail() {{ echo "$*"; exit 1; }}\n'+snippet, 'exit 0\n')
                self.assertEqual(result.returncode, code, result.stdout+result.stderr)

    def test_legacy_healthy_scope_ignores_usb_disks(self):
        snippet = between(HEALTHY, '\tcount=0\n\twritable=0\n', '|| ready=0\n')
        for case, expected in (('usb', '1'), ('extra', '0'), ('missing', '0')):
            with self.subTest(case=case):
                self.setUp()
                self.runtime_fixture(extra=case == 'extra', missing=case == 'missing')
                result = self.sh('ready=1\n'+snippet, 'echo "$ready"\n')
                self.assertEqual((result.returncode, result.stdout), (0, expected+'\n'), result.stderr)


if __name__ == '__main__':
    unittest.main(verbosity=2)
