#!/usr/bin/env python3
"""Semantic metadata rejection remains active with Python optimization enabled."""
import json
import hashlib
import importlib.util
import io
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tarfile
import tempfile
import time
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]


class PackageArchives(unittest.TestCase):
    """Real detached signatures and package bytes, with disposable fixture keys."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.tmp.cleanup)
        cls.home = Path(cls.tmp.name)
        cls.gpg_home = cls.home / 'gpg'
        cls.gpg_home.mkdir(mode=0o700)
        cls.gpg = ['gpg', '--homedir', str(cls.gpg_home), '--batch', '--no-tty']
        cls.addClassCleanup(subprocess.run, ['gpgconf', '--homedir', str(cls.gpg_home),
                                           '--kill', 'gpg-agent'], check=True, timeout=10)
        subprocess.run(cls.gpg + ['--pinentry-mode', 'loopback', '--passphrase', '',
                                 '--quick-generate-key', 'ROG5 disposable offline fixture',
                                 'ed25519', 'sign', '0'], check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, timeout=20)
        listing = subprocess.check_output(cls.gpg + ['--with-colons', '--list-keys'],
                                          stderr=subprocess.DEVNULL, timeout=10).decode()
        cls.fingerprint = next(line.split(':')[9] for line in listing.splitlines()
                               if line.startswith('fpr:'))
        cls.keyring = cls.home / 'pubkeys.gpg'
        cls.keyring.write_bytes(subprocess.check_output(cls.gpg + ['--export'], timeout=10))
        spec = importlib.util.spec_from_file_location('closure', ROOT / 'scripts/host/check-mobile-package-closure.py')
        cls.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.module)

    def setUp(self):
        self.case = tempfile.TemporaryDirectory(dir=self.home)
        self.addCleanup(self.case.cleanup)
        self.directory = Path(self.case.name)
        self.trusted = self.directory / 'trusted'
        self.trusted.write_text(self.fingerprint + ':4:\n')
        self.revoked = self.directory / 'revoked'
        self.revoked.write_text('')
        self.package = {'name': 'fixture', 'version': '1:2-3', 'architecture': 'aarch64',
                        'archive': 'fixture-1:2-3-aarch64.pkg.tar.xz',
                        'depends': ['glibc', 'provider>=2'], 'provides': ['virtual=2']}
        self.metadata = ('pkgname = fixture\npkgver = 1:2-3\narch = aarch64\n'
                         'depend = glibc\ndepend = provider>=2\nprovides = virtual=2\n').encode()

    def archive(self, metadata=None, duplicate=False, directory=False):
        path = self.directory / self.package['archive']
        data = self.metadata if metadata is None else metadata
        with tarfile.open(path, 'w:xz') as archive:
            if directory:
                info = tarfile.TarInfo('.PKGINFO')
                info.type = tarfile.DIRTYPE
                archive.addfile(info)
            for _ in range(2 if duplicate else 1):
                info = tarfile.TarInfo('.PKGINFO/child' if directory else '.PKGINFO')
                info.size = len(data)
                archive.addfile(info, io.BytesIO(data))
        subprocess.run(self.gpg + ['--yes', '--detach-sign', str(path)], check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, timeout=10)
        self.package.update(size=path.stat().st_size,
                            sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                            signature_sha256=hashlib.sha256(Path(str(path) + '.sig').read_bytes()).hexdigest())
        return path

    def audit(self, packages=None, keyring=None):
        return self.module.audit_archives(packages or [self.package], self.directory,
                                         keyring or self.keyring, self.trusted, self.revoked)

    def test_signed_package_metadata_matches(self):
        self.archive()
        report = self.audit()
        self.assertEqual(report['status'], 'PASS', report)
        self.assertEqual(report['packages'][0]['signer'], self.fingerprint)
        self.assertEqual(report['keyring_freshness'], 'NOT RUN')
        self.assertFalse(report['installation_authorized'])

    def test_corrupt_archive_and_signature_fail(self):
        for field in ('archive', 'signature'):
            with self.subTest(field=field):
                path = self.archive()
                if field == 'signature':
                    path = Path(str(path) + '.sig')
                path.write_bytes(path.read_bytes() + b'corrupted')
                self.assertEqual(self.audit()['status'], 'FAIL')

    def test_signature_hash_alone_is_not_verification(self):
        path = self.archive()
        sig = Path(str(path) + '.sig')
        sig.write_bytes(b'not a signature')
        self.package['signature_sha256'] = hashlib.sha256(sig.read_bytes()).hexdigest()
        self.assertEqual(self.audit()['status'], 'FAIL')

    def test_real_signature_for_different_archive_fails(self):
        path = self.archive()
        signature = Path(str(path) + '.sig').read_bytes()
        self.archive(self.metadata + b'# different signed bytes\n')
        Path(str(path) + '.sig').write_bytes(signature)
        self.package['signature_sha256'] = hashlib.sha256(signature).hexdigest()
        self.assertEqual(self.audit()['status'], 'FAIL')

    def test_untrusted_and_revoked_signers_fail(self):
        self.archive()
        self.trusted.write_text('0' * 40 + ':4:\n')
        self.assertEqual(self.audit()['status'], 'FAIL')
        self.trusted.write_text(self.fingerprint + ':4:\n')
        self.revoked.write_text(self.fingerprint + '\n')
        self.assertEqual(self.audit()['status'], 'FAIL')

    def test_signed_metadata_drift_fails(self):
        for old, new in ((b'fixture', b'other'), (b'1:2-3', b'1:2-4'),
                         (b'aarch64', b'x86_64'), (b'provider>=2', b'provider>=3'),
                         (b'virtual=2', b'virtual=3')):
            with self.subTest(field=old):
                self.archive(self.metadata.replace(old, new))
                self.assertEqual(self.audit()['status'], 'FAIL')

    def test_duplicate_and_oversized_metadata_fail(self):
        self.archive(duplicate=True)
        self.assertEqual(self.audit()['status'], 'FAIL')
        self.archive(self.metadata + b'#' * 70000)
        self.assertEqual(self.audit()['status'], 'FAIL')
        self.archive(self.metadata + b'pkgname = fixture\n')
        self.assertEqual(self.audit()['status'], 'FAIL')
        self.archive(directory=True)
        self.assertEqual(self.audit()['status'], 'FAIL')

    def test_missing_files_and_partial_cache_are_blocked(self):
        self.assertEqual(self.audit()['status'], 'BLOCKED')
        path = self.archive()
        missing = dict(self.package, name='missing', archive='missing.pkg.tar.xz')
        report = self.audit([self.package, missing])
        self.assertEqual(report['status'], 'BLOCKED')
        self.assertEqual(report['counts'], {'PASS': 1, 'FAIL': 0, 'BLOCKED': 1})
        Path(str(path) + '.sig').unlink()
        self.assertEqual(self.audit()['status'], 'BLOCKED')

    def test_missing_keyring_is_blocked(self):
        self.archive()
        self.assertEqual(self.audit(keyring=self.directory / 'absent')['status'], 'BLOCKED')

    def test_missing_tool_is_blocked(self):
        self.archive()
        original = shutil.which
        with mock.patch.object(self.module.shutil, 'which',
                               side_effect=lambda command: None if command == 'gpgv' else original(command)):
            self.assertEqual(self.audit()['status'], 'BLOCKED')

    def test_archive_mutation_during_verification_fails(self):
        path = self.archive()
        original = self.module.bounded_command
        def mutate(argv, **kwargs):
            result = original(argv, **kwargs)
            if argv[:2] == ['bsdtar', '-xOf']:
                with path.open('ab') as stream:
                    stream.write(b'changed after metadata inspection')
            return result
        with mock.patch.object(self.module, 'bounded_command', side_effect=mutate):
            report = self.audit()
        self.assertEqual(report['status'], 'FAIL')
        self.assertIn('changed during verification', report['packages'][0]['reason'])

    def test_symlink_and_escaping_archive_names_fail(self):
        path = self.archive()
        saved = path.with_name('saved')
        path.rename(saved)
        path.symlink_to(saved)
        self.assertEqual(self.audit()['status'], 'FAIL')
        for name in ('../saved', str(saved), './saved'):
            with self.subTest(name=name):
                self.package['archive'] = name
                self.assertEqual(self.audit()['status'], 'FAIL')

    def test_subprocess_deadline_and_output_bound(self):
        for code, limit in (('import time; time.sleep(10)', 0.05),
                            ('import os; os.write(1,b"x"*100000)', 5)):
            with self.subTest(code=code):
                with self.assertRaises(ValueError):
                    self.module.bounded_command([sys.executable, '-c', code],
                                                timeout=limit, limit=1000)

    def test_interruption_reaps_the_owned_command(self):
        for sig in (signal.SIGTERM, signal.SIGINT):
            with self.subTest(signal=sig):
                pidfile = self.directory / f'child-{sig}.pid'
                child = (f'import os,time;from pathlib import Path;'
                         f'Path({str(pidfile)!r}).write_text(str(os.getpid()));time.sleep(60)')
                parent = ('import importlib.util,sys;'
                          's=importlib.util.spec_from_file_location("closure",sys.argv[1]);'
                          'm=importlib.util.module_from_spec(s);s.loader.exec_module(m);'
                          'm.bounded_command([sys.executable,"-c",sys.argv[2]])')
                proc = subprocess.Popen([sys.executable, '-c', parent,
                                         str(ROOT / 'scripts/host/check-mobile-package-closure.py'), child],
                                        stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                child_pid = None
                try:
                    deadline = time.monotonic() + 3
                    while not pidfile.exists() and time.monotonic() < deadline:
                        time.sleep(0.01)
                    self.assertTrue(pidfile.exists(), 'child did not arm')
                    child_pid = int(pidfile.read_text())
                    proc.send_signal(sig)
                    stdout, stderr = proc.communicate(timeout=3)
                    self.assertEqual(proc.returncode, 128 + sig, stderr)
                    self.assertEqual(stdout, b'')
                    self.assertFalse(Path(f'/proc/{child_pid}').exists(), 'owned command was not reaped')
                    child_pid = None
                finally:
                    if proc.poll() is None:
                        proc.kill()
                    proc.communicate(timeout=3)
                    if child_pid is not None:
                        try:
                            os.killpg(child_pid, signal.SIGKILL)
                        except ProcessLookupError:
                            pass



class Checkers(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        subprocess.run(['git', 'init', '-q', str(self.root)], check=True)
        for name in ('manifests/artifact-sets.json', 'manifests/artifacts.tsv',
                     'manifests/current-artifact.json', 'packaging/arch/mobile-package-closure.json',
                     'configs/denial/source-lock-v1.json'):
            path = self.root/name
            path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT/name, path)

    def check(self, checker, expect, graph=None):
        program = ('import importlib.util, pathlib, sys; '
                   's=importlib.util.spec_from_file_location("checker",sys.argv[1]); '
                   'm=importlib.util.module_from_spec(s); s.loader.exec_module(m); '
                   'm.validate(pathlib.Path(sys.argv[2]), graph=pathlib.Path(sys.argv[3])) '
                   'if len(sys.argv)>3 else m.validate(pathlib.Path(sys.argv[2]))')
        result = subprocess.run([sys.executable, '-O', '-c', program,
                                 str(ROOT/'scripts/host'/checker), str(self.root)] +
                                ([str(graph)] if graph is not None else []),
                                capture_output=True, text=True, timeout=10)
        if expect:
            self.assertEqual(result.returncode, 0, result.stderr)
        else:
            self.assertNotEqual(result.returncode, 0, result.stdout)
            self.assertIn('ValueError', result.stderr)

    def alter(self, name, change):
        path = self.root/name
        data = json.loads(path.read_text())
        change(data)
        path.write_text(json.dumps(data))

    def test_valid_metadata_under_optimization(self):
        self.check('check-artifact-inventory.py', True)
        self.check('check-mobile-package-closure.py', True)

    def test_unclassified_registered_artifact_refuses_under_optimization(self):
        def remove(data):
            entry = next(x for x in data['sets'] if x['id'] == 'artifacts/buttons-indicator-v1')
            entry['outputs'] = [x for x in entry['outputs'] if not x['path'].endswith('.dtb')]
        self.alter('manifests/artifact-sets.json', remove)
        self.check('check-artifact-inventory.py', False)

    def test_missing_dependency_edge_refuses_under_optimization(self):
        self.alter('packaging/arch/mobile-package-closure.json',
                   lambda data: data['dependency_edges'].pop())
        self.check('check-mobile-package-closure.py', False)

    def test_explicit_graph_is_selected_and_validated_under_optimization(self):
        original = 'packaging/arch/mobile-package-closure.json'
        selected = 'packaging/arch/selected-snapshot.json'
        shutil.copyfile(self.root / original, self.root / selected)
        self.alter(original, lambda data: data['dependency_edges'].pop())
        self.check('check-mobile-package-closure.py', True, selected)
        self.alter(selected, lambda data: data['dependency_edges'].pop())
        self.check('check-mobile-package-closure.py', False, selected)

    def test_wrong_provider_refuses_under_optimization(self):
        def replace(data):
            edge = next(e for e in data['dependency_edges'] if e['dependency'] == 'mesa')
            edge['provider'] = 'glibc'
        self.alter('packaging/arch/mobile-package-closure.json', replace)
        self.check('check-mobile-package-closure.py', False)


if __name__ == '__main__':
    unittest.main(verbosity=2)
