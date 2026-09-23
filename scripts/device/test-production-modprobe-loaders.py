#!/usr/bin/env python3
"""Run the power and UFS stage loaders against the production depmod tree.

The target ARM64 BusyBox resolves every plan (modprobe -D) from the real
7.1.4-rog5-production modules.dep inside an unprivileged chroot under
qemu-aarch64. Only the insertion itself and /proc/modules are fixtures; no
module is loaded. Legacy loose-module archives must keep their insmod path.

Inputs (private, untracked): a target archive with bin/busybox and the musl
loader, and the module-root-complete tarball. Override with
ROG5_TEST_TARGET_ARCHIVE and ROG5_TEST_MODULE_TREE; the suite skips when the
inputs, qemu or user namespaces are unavailable.
"""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[2]
POWER = REPO/'scripts/device/load-persistent-root-power-usb.sh'
INIT = REPO/'initramfs/persistent-root-init'
RELEASE = '7.1.4-rog5-production'
STATE = Path.home()/'.local/state/rog5-display-trial-preparation-20260921-r1/module-selection-r1'
ARCHIVE = Path(os.environ.get('ROG5_TEST_TARGET_ARCHIVE', STATE/'archive-rehearsal-r1/disabled-init-module-refresh.cpio.gz'))
TREE = Path(os.environ.get('ROG5_TEST_MODULE_TREE', STATE/'package-r1/module-root-complete.tar.gz'))
QEMU = Path(os.environ.get('ROG5_TEST_QEMU', '/usr/bin/qemu-aarch64-static'))
APPLETS = ('sh', 'grep', 'find', 'wc', 'cat', 'sed', 'head', 'tail', 'tr', 'basename',
           'mkdir', 'rm', 'uname', 'sleep', 'modprobe', 'insmod', 'true', 'false')
POWER_ORDER = ['mdt_loader', 'qcom_q6v5', 'qcom_glink_smem', 'qcom_common', 'qcom_pil_info',
               'qcom_q6v5_pas', 'qrtr', 'qrtr_smd', 'qcom_pdr_msg', 'qcom_pd_mapper',
               'pdr_interface', 'pmic_glink', 'qcom_battmgr', 'typec', 'typec_ucsi', 'ucsi_glink']
UFS_ORDER = ['phy_qcom_qmp_ufs', 'ufshcd_core', 'ufshcd_pltfrm', 'ufs_qcom']

HARNESS = r'''
set -eu
fail() { printf 'FAIL %s\n' "$1"; exit 1; }
log() { :; }
modprobe() {
	if [ "$1" = -D ]; then /bin/busybox modprobe -D "$2"; return; fi
	printf 'MODPROBE %s\n' "$1"
	case " ${FAIL_LOAD:-} " in *" $1 "*) return 1 ;; esac
	case " ${SILENT_LOAD:-} " in *" $1 "*) return 0 ;; esac
	printf '%s 16384 0 - Live 0x0\n' "$1" >>/proc/modules
}
insmod() {
	n=$(basename "$1" .ko | tr - _)
	printf 'INSMOD %s\n' "$n"
	printf '%s 16384 0 - Live 0x0\n' "$n" >>/proc/modules
}
'''


def function(text, name):
    begin = text.index(name+'() {')
    return text[begin:text.index('\n}', begin)+3]


def between(text, start, end):
    begin = text.index(start)
    return text[begin:text.index(end, begin)+len(end)]


SKIP_MESSAGE = 'target busybox modprobe replay needs the private archive, module tree, qemu and user namespaces'
REPLAY_READY = (all(p.is_file() for p in (ARCHIVE, TREE, QEMU))
                and subprocess.run(['unshare', '-r', 'true'], capture_output=True).returncode == 0)


class Source(unittest.TestCase):
    """Runs everywhere: the legacy paths stay intact and the tree mode is gated."""

    def test_power_loader_keeps_legacy_inventory_and_orders_mdt_first_in_tree_mode(self):
        text = POWER.read_text()
        self.assertEqual(text.count('\nload_module '), 15)
        self.assertIn("-name '*.ko' | wc -l)\" -eq 15 ]", text)
        tree = between(text, 'if [ "$module_mode" = legacy ]; then', '\nfi\n')
        self.assertIn('load_module mdt_loader.ko mdt_loader mdt-loader', tree)
        self.assertIn('/proc/sys/kernel/osrelease', text)
        self.assertNotIn('uname', text)

    def test_main_flow_gate_sees_the_production_tree(self):
        # The r2 package failed this: the gate only knew the legacy directory,
        # so the production ramdisk would never have loaded UFS.
        gate = function(INIT.read_text(), 'deferred_ufs_modules_present')
        self.assertIn('/rog5-ufs-modules', gate)
        self.assertIn('/lib/modules/${running_kernel_release:-}/modules.dep', gate)
        init = INIT.read_text()
        self.assertLess(init.index('IFS= read -r running_kernel_release'),
                        init.index('if deferred_ufs_modules_present; then'))

    def test_init_dispatches_production_ufs_only_without_loose_modules(self):
        text = INIT.read_text()
        legacy = function(text, 'load_deferred_ufs_modules')
        self.assertIn('[ ! -e /rog5-ufs-modules ]', legacy)
        self.assertIn('load_production_ufs_modules', legacy)
        self.assertNotIn('modprobe', legacy)
        production = function(text, 'load_production_ufs_modules')
        self.assertFalse([line for line in production.splitlines() if line.strip().startswith('insmod ')])
        self.assertIn('$running_kernel_release', production)
        self.assertNotIn('uname -r', text)


@unittest.skipUnless(REPLAY_READY, SKIP_MESSAGE)
class Loaders(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix='rog5-modprobe-loaders-')
        cls.addClassCleanup(cls.temp.cleanup)
        root = cls.root = Path(cls.temp.name)/'root'
        root.mkdir()
        members = subprocess.run(f'gzip -dc {ARCHIVE} | cpio -id --quiet bin/busybox "lib/ld-musl-aarch64.so.1"',
                                 shell=True, cwd=root, capture_output=True, text=True)
        if members.returncode or not (root/'bin/busybox').is_file():
            raise unittest.SkipTest('SKIP target busybox not extractable: '+members.stderr[-300:])
        for applet in APPLETS:
            (root/'bin'/applet).symlink_to('busybox')
        subprocess.run(['tar', '-xzf', str(TREE), '-C', str(root)], check=True)
        shutil.copy2(QEMU, root/'qemu')
        (root/'proc').mkdir()
        (root/'dev').mkdir()
        (root/'dev/null').write_bytes(b'')
        (root/'proc/sys/kernel').mkdir(parents=True)
        (root/'proc/sys/kernel/osrelease').write_text(RELEASE+'\n')
        cls.dep = root/'lib/modules'/RELEASE/'modules.dep'
        cls.dep_text = cls.dep.read_text()
        cls.power = POWER.read_text()
        cls.init = INIT.read_text()

    def setUp(self):
        self.dep.write_text(self.dep_text)
        (self.root/'proc/modules').write_text('')
        for name in ('rog5-power-usb-modules', 'rog5-ufs-modules'):
            shutil.rmtree(self.root/name, ignore_errors=True)

    def run_case(self, body, env=None, preload=()):
        (self.root/'proc/modules').write_text(''.join(f'{m} 16384 0 - Live 0x0\n' for m in preload))
        (self.root/'case.sh').write_text(HARNESS+body)
        # A private mount namespace provides the ramdisk's /dev/null.
        command = ['unshare', '-rm', 'sh', '-c',
                   'mount --bind /dev/null "$1/dev/null" && exec chroot "$1" /qemu -r "$2" /bin/busybox sh /case.sh',
                   'sh', str(self.root), RELEASE]
        # Children that busybox execs run under binfmt's qemu, which reads the
        # release from QEMU_UNAME rather than the parent's -r option.
        run_env = {'PATH': '/bin', 'QEMU_UNAME': RELEASE, **(env or {})}
        result = subprocess.run(command, capture_output=True, text=True, timeout=60, env=run_env)
        loaded = [line.split()[0] for line in (self.root/'proc/modules').read_text().splitlines()]
        return result, loaded

    def power_case(self, **kwargs):
        text = self.power
        body = ('module_root=/rog5-power-usb-modules\n'
                + between(text, 'module_release=\n', '\nfi\n')
                + function(text, 'load_module')
                + between(text, 'if [ "$module_mode" = legacy ]; then',
                          'load_module ucsi_glink.ko ucsi_glink ucsi-glink\n')
                + "printf 'PASS mode=%s\\n' \"$module_mode\"\n")
        return self.run_case(body, **kwargs)

    def ufs_case(self, **kwargs):
        text = self.init
        body = ('IFS= read -r running_kernel_release </proc/sys/kernel/osrelease\n'
                + function(text, 'load_production_ufs_modules') + function(text, 'load_deferred_ufs_modules')
                + 'mode=legacy; [ -e /rog5-ufs-modules ] || mode=tree\n'
                + 'if load_deferred_ufs_modules; then echo "PASS mode=$mode"; '
                  'else echo "FAIL ufs mode=$mode"; exit 1; fi\n')
        return self.run_case(body, **kwargs)

    def test_power_tree_loads_mdt_loader_first_then_historical_order(self):
        result, loaded = self.power_case()
        self.assertEqual(result.returncode, 0, result.stdout+result.stderr)
        self.assertIn('PASS mode=tree', result.stdout)
        self.assertEqual(loaded, POWER_ORDER)
        self.assertNotIn('INSMOD', result.stdout)

    def test_power_tree_refuses_preloaded_module(self):
        result, loaded = self.power_case(preload=['qcom_q6v5'])
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('FAIL module-qcom-q6v5-already-loaded', result.stdout)
        self.assertEqual(loaded, ['qcom_q6v5', 'mdt_loader'])

    def test_power_tree_refuses_module_absent_from_tree(self):
        self.dep.write_text(''.join(line+'\n' for line in self.dep_text.splitlines()
                                    if '/qcom_battmgr.ko:' not in line))
        result, loaded = self.power_case()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('FAIL module-qcom-battmgr-missing', result.stdout)
        self.assertEqual(loaded, POWER_ORDER[:POWER_ORDER.index('qcom_battmgr')])

    def test_power_tree_insertion_failure_and_unobservable_module(self):
        for key, detail in (('FAIL_LOAD', 'load'), ('SILENT_LOAD', 'unobservable')):
            with self.subTest(case=key):
                result, loaded = self.power_case(env={key: 'qcom_q6v5_pas'})
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(f'FAIL module-qcom-q6v5-pas-{detail}', result.stdout)
                self.assertEqual(loaded, POWER_ORDER[:POWER_ORDER.index('qcom_q6v5_pas')])

    def test_power_legacy_archive_keeps_insmod_without_mdt_loader(self):
        legacy = self.root/'rog5-power-usb-modules'
        legacy.mkdir()
        for name in POWER_ORDER[1:]:
            (legacy/(name.replace('qrtr_smd', 'qrtr-smd')+'.ko')).write_bytes(b'x')
        result, loaded = self.power_case()
        self.assertEqual(result.returncode, 0, result.stdout+result.stderr)
        self.assertIn('PASS mode=legacy', result.stdout)
        self.assertEqual(loaded, POWER_ORDER[1:])
        self.assertNotIn('MODPROBE', result.stdout)

    def test_power_legacy_inventory_must_stay_fifteen(self):
        legacy = self.root/'rog5-power-usb-modules'
        legacy.mkdir()
        for name in POWER_ORDER:  # sixteen files, including mdt_loader
            (legacy/(name+'.ko')).write_bytes(b'x')
        result, loaded = self.power_case()
        self.assertIn('FAIL module-inventory', result.stdout)
        self.assertEqual(loaded, [])

    def test_ufs_tree_loads_four_modules_in_order(self):
        result, loaded = self.ufs_case()
        self.assertEqual(result.returncode, 0, result.stdout+result.stderr)
        self.assertIn('PASS mode=tree', result.stdout)
        self.assertEqual(loaded, UFS_ORDER)

    def test_ufs_tree_refuses_preloaded_or_failed_module(self):
        result, loaded = self.ufs_case(preload=['ufshcd_core'])
        self.assertIn('FAIL ufs mode=tree', result.stdout)
        self.assertEqual(loaded, ['ufshcd_core'])
        result, loaded = self.ufs_case(env={'FAIL_LOAD': 'ufshcd_pltfrm'})
        self.assertIn('FAIL ufs mode=tree', result.stdout)
        self.assertEqual(loaded, UFS_ORDER[:2])

    def test_ufs_gate_under_target_busybox(self):
        body = ('IFS= read -r running_kernel_release </proc/sys/kernel/osrelease\n'
                + function(self.init, 'deferred_ufs_modules_present')
                + 'if deferred_ufs_modules_present; then echo GATE=1; else echo GATE=0; fi\n')
        result, _ = self.run_case(body)
        self.assertIn('GATE=1', result.stdout, result.stdout+result.stderr)
        (self.root/'rog5-ufs-modules').mkdir()
        result, _ = self.run_case(body)
        self.assertIn('GATE=1', result.stdout)
        (self.root/'rog5-ufs-modules').rmdir()
        self.dep.rename(self.dep.with_suffix('.hidden'))
        try:
            result, _ = self.run_case(body)
            self.assertIn('GATE=0', result.stdout)
        finally:
            self.dep.with_suffix('.hidden').rename(self.dep)

    def test_ufs_legacy_archive_keeps_insmod(self):
        legacy = self.root/'rog5-ufs-modules'
        legacy.mkdir()
        for name in ('phy-qcom-qmp-ufs', 'ufshcd-core', 'ufshcd-pltfrm', 'ufs-qcom'):
            (legacy/(name+'.ko')).write_bytes(b'x')
        result, loaded = self.ufs_case()
        self.assertIn('PASS mode=legacy', result.stdout)
        self.assertEqual(loaded, UFS_ORDER)
        self.assertNotIn('MODPROBE', result.stdout)


if __name__ == '__main__':
    unittest.main(verbosity=2)
