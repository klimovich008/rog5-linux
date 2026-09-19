#!/usr/bin/env python3
"""Exercise real guest RAM-cache transaction; no VM/systemd dispatch proof."""
import hashlib
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / 'tools/qemu-virtio-drm/logind-linker-cache.sh'


class LinkerCache(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='rog5-linker-cache-')
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.run = self.root / 'run'
        self.etc = self.root / 'etc'
        self.run.mkdir()
        self.etc.mkdir()
        self.cache = self.run / 'linker-cache'
        self.hash = self.run / 'linker-cache.sha256'
        self.marker = self.run / 'linker-cache.verified'
        self.output = self.etc / 'ld.so.cache'
        self.dropin = self.etc / 'systemd/system/ldconfig.service.d'
        self.guard = self.dropin / '50-rog5-cache.conf'
        self.data = b'fixture cache bytes; format admission belongs to host\0' * 2

    def inputs(self):
        self.cache.write_bytes(self.data)
        self.hash.write_text(hashlib.sha256(self.data).hexdigest() + '\n')

    def call(self, inject=''):
        # Conditional invocation deliberately disables bash errexit: every
        # production operation must propagate its own failure.
        return subprocess.run(['bash', '--noprofile', '--norc', '-c',
            'source "$1" || exit $?\n' + inject +
            '\nif prepare_linker_cache "$2" "$3"; then exit 0; else exit $?; fi',
            'fixture', str(SCRIPT), str(self.run), str(self.etc)],
            capture_output=True, text=True, timeout=5)

    def clean_failure(self, result):
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertFalse(self.marker.exists())
        self.assertFalse(self.output.exists())
        self.assertFalse(self.dropin.exists())
        self.assertEqual(list(self.etc.glob('.rog5-linker-cache.*')), [])
        self.assertEqual(list(self.run.glob('.rog5-linker-cache.*')), [])

    def test_absent_unchanged(self):
        self.assertEqual(self.call().returncode, 0)
        self.assertEqual(list(self.run.iterdir()), [])
        self.assertEqual(list(self.etc.iterdir()), [])

    def test_publication_never_crosses_run_etc_filesystems(self):
        self.inputs()
        result = self.call("""ln() {
            source_path=${@: -2:1}; target_path=${@: -1}
            if [[ $target_path == "$run/"* ]]; then
                [[ $source_path == "$run/"* ]] || return 18
            elif [[ $target_path == "$etc/"* ]]; then
                [[ $source_path == "$etc/"* ]] || return 18
            else return 18; fi
            command ln "$@"
        }""")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(self.marker.is_file())

    def test_success_and_narrow_guard(self):
        self.inputs()
        result = self.call()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.output.read_bytes(), self.data)
        self.assertEqual(self.output.stat().st_mode & 0o777, 0o644)
        self.assertEqual(self.output.stat().st_nlink, 1)
        self.assertEqual(self.guard.read_text(),
            f'[Unit]\nConditionPathExists=!{self.run}/linker-cache.verified\n')
        self.assertEqual(self.marker.read_bytes(), self.hash.read_bytes())
        self.assertFalse((self.etc / '.updated').exists())
        self.assertEqual(list(self.etc.glob('.rog5-linker-cache.*')), [])
        self.assertEqual(list(self.run.glob('.rog5-linker-cache.*')), [])

    def test_missing_each_input(self):
        for name in ('cache', 'hash'):
            with self.subTest(name=name):
                self.inputs()
                getattr(self, name).unlink()
                self.clean_failure(self.call())
                for path in (self.cache, self.hash):
                    path.unlink(missing_ok=True)

    def test_bad_hashes(self):
        for data in ('0' * 64 + '\n', 'x' * 64 + '\n', 'a' * 64,
                     'a' * 64 + '\r\n', 'a' * 63 + '\n\n'):
            with self.subTest(data=data):
                self.inputs()
                self.hash.write_text(data)
                self.clean_failure(self.call())

    def test_truncated_and_oversized(self):
        for size in (0, 47, 1048577):
            with self.subTest(size=size):
                self.inputs()
                self.cache.write_bytes(b'x' * size)
                self.hash.write_text(hashlib.sha256(self.cache.read_bytes()).hexdigest() + '\n')
                self.clean_failure(self.call())

    def test_symlink_and_hardlink_inputs(self):
        for name in ('cache', 'hash'):
            for kind in ('symlink', 'dangling', 'hardlink'):
                with self.subTest(name=name, kind=kind):
                    self.inputs()
                    path = getattr(self, name)
                    other = self.root / 'other'
                    if kind == 'hardlink':
                        os.link(path, other)
                    else:
                        path.rename(other)
                        path.symlink_to(other if kind == 'symlink' else self.root / 'missing')
                    self.clean_failure(self.call())
                    path.unlink()
                    other.unlink()

    def test_existing_output_unchanged(self):
        self.inputs()
        self.output.write_bytes(b'original')
        self.assertNotEqual(self.call().returncode, 0)
        self.assertEqual(self.output.read_bytes(), b'original')
        self.assertFalse(self.marker.exists())

    def test_existing_dropin_or_marker(self):
        self.inputs()
        self.dropin.mkdir(parents=True)
        self.clean_failure_without_removal(self.dropin)
        self.dropin.rmdir()
        self.marker.symlink_to(self.root / 'missing')
        self.clean_failure_without_removal(self.marker)

    def clean_failure_without_removal(self, preserved):
        self.assertNotEqual(self.call().returncode, 0)
        self.assertTrue(preserved.exists() or preserved.is_symlink())
        self.assertFalse(self.output.exists())

    def test_symlink_parent(self):
        self.inputs()
        outside = self.root / 'outside'
        outside.mkdir()
        (self.etc / 'systemd').symlink_to(outside)
        self.clean_failure(self.call())
        self.assertEqual(list(outside.iterdir()), [])

    def test_copy_failure(self):
        self.inputs()
        self.clean_failure(self.call('cp() { command cp "$@"; return 42; }'))

    def test_corrupted_staged_copy(self):
        self.inputs()
        self.clean_failure(self.call('cp() { command cp "$@" || return; printf x >> "${@: -1}"; }'))

    def test_hash_failure_each_stage(self):
        for suffix in ('linker-cache', '/cache', 'ld.so.cache'):
            with self.subTest(suffix=suffix):
                self.inputs()
                self.clean_failure(self.call(
                    'sha256sum() { [[ ${@: -1} != *"' + suffix +
                    '" ]] || return 43; command sha256sum "$@"; }'))

    def test_publication_failure_each_stage(self):
        for suffix in ('ld.so.cache', '50-rog5-cache.conf', 'linker-cache.verified'):
            with self.subTest(suffix=suffix):
                self.inputs()
                self.clean_failure(self.call(
                    'ln() { [[ ${@: -1} != *"' + suffix +
                    '" ]] || return 44; command ln "$@"; }'))

    def test_marker_after_hash_and_guard(self):
        self.inputs()
        result = self.call('''ln() {
            if [[ ${@: -1} == */linker-cache.verified ]]; then
                [[ -f $guard && -f $cache && ! -e $marker ]] || return 45
                [[ $(command sha256sum -- "$cache") == "$expected "* ]] || return 46
            fi
            command ln "$@"
        }''')
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_interrupted_after_copy_or_publication(self):
        for command, suffix in (('cp', '/cache'), ('ln', 'ld.so.cache'),
                                ('ln', '50-rog5-cache.conf'),
                                ('ln', 'linker-cache.verified')):
            with self.subTest(command=command, suffix=suffix):
                self.inputs()
                self.clean_failure(self.call(command + '() { command ' + command +
                    ' "$@" || return; if [[ ${@: -1} == *"' + suffix +
                    '" ]]; then kill -TERM "$BASHPID"; fi; }'))

    def test_chmod_failure_each_stage(self):
        for suffix in ('/cache', '/guard', '/marker'):
            with self.subTest(suffix=suffix):
                self.inputs()
                self.clean_failure(self.call(
                    'chmod() { [[ ${@: -1} != *"' + suffix +
                    '" ]] || return 47; command chmod "$@"; }'))

    def test_mkdir_failure_each_stage(self):
        for suffix in ('/systemd', '/system', '/ldconfig.service.d'):
            with self.subTest(suffix=suffix):
                self.inputs()
                self.clean_failure(self.call(
                    'mkdir() { [[ ${@: -1} != *"' + suffix +
                    '" ]] || return 48; command mkdir "$@"; }'))

    def test_existing_parent_directories_preserved_on_failure(self):
        self.inputs()
        parent = self.etc / 'systemd/system'
        parent.mkdir(parents=True)
        self.clean_failure(self.call('ln() { return 49; }'))
        self.assertTrue(parent.is_dir())

    def test_existing_destination_symlink_preserved(self):
        self.inputs()
        self.output.symlink_to(self.root / 'missing')
        self.assertNotEqual(self.call().returncode, 0)
        self.assertTrue(self.output.is_symlink())
        self.assertFalse(self.marker.exists())

    def test_guard_path_rejects_systemd_specifier(self):
        self.inputs()
        unusual = self.root / 'run%T'
        self.run.rename(unusual)
        self.run = unusual
        self.assertNotEqual(self.call().returncode, 0)
        self.assertEqual(list(self.etc.iterdir()), [])


if __name__ == '__main__':
    unittest.main()
