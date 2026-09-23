#!/usr/bin/env python3
"""Build standalone production ramdisks and refuse hostile module packages.

Argument checks run everywhere. The full builds use the private V9 base
archive and the pinned 7.1.4-rog5-production module package; override them
with ROG5_TEST_STANDALONE_BASE / ROG5_TEST_MODULE_TREE. Nothing is signed or
booted; outputs stay in a temporary directory.
"""
import gzip
import hashlib
import io
import os
from pathlib import Path
import subprocess
import tarfile
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[2]
BUILDER = REPO/'scripts/device/build-persistent-root-standalone-initramfs.sh'
RELEASE = '7.1.4-rog5-production'
STATE = Path.home()/'.local/state'
BASE = Path(os.environ.get('ROG5_TEST_STANDALONE_BASE',
                           STATE/'rog5-cpu-startup-20260908.kjE4IqCf/buttons-successor-unsigned-r2/target-a.cpio.gz'))
PACKAGE = Path(os.environ.get('ROG5_TEST_MODULE_TREE',
                              STATE/'rog5-display-trial-preparation-20260921-r1/module-selection-r1/package-r1/module-root-complete.tar.gz'))
SKIP_MESSAGE = 'production ramdisk build needs the private V9 base archive and module package'
READY = BASE.is_file() and PACKAGE.is_file()


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def build(base, output, package, package_sha, release=RELEASE, extra=(), env_extra=None):
    env = dict(os.environ, EXPECTED_RELEASE=release, EXPECTED_STANDALONE_BASE_SHA256=sha(base) if Path(base).is_file() else '0'*64,
               PRODUCTION_MODULE_PACKAGE=str(package), PRODUCTION_MODULE_PACKAGE_SHA256=package_sha, **(env_extra or {}))
    return subprocess.run(['sh', str(BUILDER), str(base), str(output), *extra],
                          capture_output=True, text=True, env=env, timeout=300)


class Arguments(unittest.TestCase):
    def test_production_mode_refuses_unpinned_or_mixed_inputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)/'base.cpio.gz'
            base.write_bytes(gzip.compress(b''))
            package = Path(tmp)/'package.tar.gz'
            package.write_bytes(b'x')
            for label, kwargs, extra in (
                    ('no hash', dict(package_sha=''), ()),
                    ('legacy release', dict(package_sha='a'*64, release='7.1.4-g359318de534f'), ()),
                    ('loose modules too', dict(package_sha='a'*64), (tmp, tmp))):
                with self.subTest(case=label):
                    result = build(base, Path(tmp)/'out.cpio.gz', package, **kwargs, extra=extra)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn('FAIL production module tree needs', result.stderr)
                    self.assertFalse((Path(tmp)/'out.cpio.gz').exists())


    def test_trial_kit_needs_the_production_tree(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)/'base.cpio.gz'
            base.write_bytes(gzip.compress(b''))
            env = dict(os.environ, EXPECTED_RELEASE=RELEASE, EXPECTED_STANDALONE_BASE_SHA256='0'*64,
                       PRODUCTION_TRIAL_DESCRIPTOR=str(base), PRODUCTION_TRIAL_DESCRIPTOR_SHA256='a'*64)
            env.pop('PRODUCTION_MODULE_PACKAGE', None)
            result = subprocess.run(['sh', str(BUILDER), str(base), str(Path(tmp)/'out.cpio.gz')],
                                    capture_output=True, text=True, env=env, timeout=60)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('FAIL a production trial kit needs the production module tree', result.stderr)


DESCRIPTOR = (b'format=rog5-persistent-wifi-health-v1\ntrial_id=' + b'c'*64 +
              b'\nprimary_bundle=production-7.2.7-test\nmode=try-once\n')


@unittest.skipUnless(READY, SKIP_MESSAGE)
class Builds(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.dir = Path(self.temp.name)

    def members(self, archive):
        listing = subprocess.run(f'gzip -dc {archive} | cpio -t --quiet', shell=True,
                                 capture_output=True, text=True, check=True).stdout.splitlines()
        return listing

    def variant(self, name, mutate):
        """Rewrite the real package through mutate(tar_in, tar_out)."""
        out = self.dir/name
        with tarfile.open(PACKAGE) as source, tarfile.open(out, 'w:gz') as target:
            mutate(source, target)
        return out

    def test_trial_kit_is_installed_with_exact_modes(self):
        descriptor = self.dir/'trial-descriptor'
        descriptor.write_bytes(DESCRIPTOR)
        output = self.dir/'trial.cpio.gz'
        result = build(BASE, output, PACKAGE, sha(PACKAGE), env_extra=dict(
            PRODUCTION_TRIAL_DESCRIPTOR=str(descriptor), PRODUCTION_TRIAL_DESCRIPTOR_SHA256=sha(descriptor)))
        self.assertEqual(result.returncode, 0, result.stderr[-2000:])
        listing = subprocess.run(f'gzip -dc {output} | cpio -tv --quiet', shell=True,
                                 capture_output=True, text=True, check=True).stdout.splitlines()
        modes = {line.split()[-1]: line.split()[0] for line in listing if 'rog5-production-trial' in line}
        self.assertEqual(modes, {'rog5-production-trial': 'drwx------',
                                 'rog5-production-trial/commit': '-rwxr-xr-x',
                                 'rog5-production-trial/rog5-production-trial-commit.service': '-rw-r--r--',
                                 'rog5-production-trial/trial-descriptor': '-r--r--r--',
                                 'rog5-production-trial/trial-state': '-rwxr-xr-x'})
        wrong = build(BASE, self.dir/'wrong.cpio.gz', PACKAGE, sha(PACKAGE), env_extra=dict(
            PRODUCTION_TRIAL_DESCRIPTOR=str(descriptor), PRODUCTION_TRIAL_DESCRIPTOR_SHA256='d'*64))
        self.assertNotEqual(wrong.returncode, 0)
        self.assertIn('FAIL production trial kit', wrong.stderr)

    def test_real_build_has_one_release_tree_and_no_loose_release_modules(self):
        output = self.dir/'target.cpio.gz'
        result = build(BASE, output, PACKAGE, sha(PACKAGE))
        self.assertEqual(result.returncode, 0, result.stderr[-2000:])
        members = self.members(output)
        self.assertEqual(members, sorted(members, key=lambda name: name.encode()))
        modules = [m for m in members if m.endswith('.ko')]
        self.assertEqual(len(modules), 64)
        self.assertTrue(all(m.startswith(f'lib/modules/{RELEASE}/') for m in modules))
        for gone in ('rog5-power-usb-modules', 'rog5-ufs-modules', 'rog5-native-wifi', 'rog5-reboot-mode-modules'):
            self.assertFalse([m for m in members if m == gone or m.startswith(gone+'/')], gone)
        self.assertIn('etc/modprobe.d/rog5-production-no-autoload.conf', members)
        init = subprocess.run(f'gzip -dc {output} | cpio -i --quiet --to-stdout init', shell=True,
                              capture_output=True, check=True).stdout.decode()
        self.assertIn(f'expected_kernel_release={RELEASE}\n', init)
        again = self.dir/'again.cpio.gz'
        self.assertEqual(build(BASE, again, PACKAGE, sha(PACKAGE)).returncode, 0)
        self.assertEqual(sha(output), sha(again), 'production build is not reproducible')

    def test_hostile_packages_are_refused(self):
        def copy(source, target, skip=()):
            for member in source.getmembers():
                if member.name in skip:
                    continue
                target.addfile(member, source.extractfile(member) if member.isfile() else None)

        def with_extra(source, target):
            copy(source, target)
            info = tarfile.TarInfo('etc/rog5-extra')
            info.size = 1
            target.addfile(info, io.BytesIO(b'x'))

        def with_symlink(source, target):
            copy(source, target)
            info = tarfile.TarInfo(f'lib/modules/{RELEASE}/kernel/link.ko')
            info.type = tarfile.SYMTYPE
            info.linkname = '/etc/passwd'
            target.addfile(info)

        def without_dep(source, target):
            copy(source, target, skip={f'lib/modules/{RELEASE}/modules.dep'})

        cases = {'member outside the tree': with_extra, 'symlink member': with_symlink,
                 'no modules.dep': without_dep}
        for label, mutate in cases.items():
            with self.subTest(case=label):
                package = self.variant(label.replace(' ', '-')+'.tar.gz', mutate)
                output = self.dir/(label.replace(' ', '-')+'.cpio.gz')
                result = build(BASE, output, package, sha(package))
                self.assertNotEqual(result.returncode, 0)
                self.assertIn('FAIL production module tree', result.stderr)
                self.assertFalse(output.exists())
        with self.subTest(case='package hash mismatch'):
            output = self.dir/'mismatch.cpio.gz'
            result = build(BASE, output, PACKAGE, 'b'*64)
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(output.exists())


if __name__ == '__main__':
    unittest.main(verbosity=2)
