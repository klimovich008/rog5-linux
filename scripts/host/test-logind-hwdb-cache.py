#!/usr/bin/env python3
"""Exercise the actual guest cache transaction; systemd/ARM64 remain separate."""
import hashlib
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / 'tools/qemu-virtio-drm/logind-linker-cache.sh'
QUERY = 'ID_VENDOR_FROM_DATABASE=Logitech, Inc.\nID_MODEL_FROM_DATABASE=WingMan Extreme Joystick\n'


class HardwareDatabase(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='rog5-hwdb-guest-')
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.run, self.etc, self.bin = [self.root/p for p in ('run', 'etc', 'bin')]
        for path in (self.run, self.etc/'udev', self.bin):
            path.mkdir(parents=True)
        self.output = self.etc/'udev/hwdb.bin'
        self.marker = self.run/'hwdb-cache.verified'
        self.dropin = self.etc/'systemd/system/systemd-hwdb-update.service.d'
        self.guard = self.dropin/'50-rog5-cache.conf'
        self.data = b'fixture: host admission checks the actual binary format\0'*3
        helper = self.bin/'systemd-hwdb'
        helper.write_text('''#!/usr/bin/python3
import os, pathlib, sys
root = pathlib.Path(os.environ['HWDB_FIXTURE'])
if sys.argv[1:] != ['query', 'usb:v046Dp0200d0000']: sys.exit(91)
if (root/'etc/udev/hwdb.bin').read_bytes() != (pathlib.Path(os.environ['HWDB_INPUT'])/'hwdb-cache').read_bytes(): sys.exit(92)
if (root/'run/hwdb-cache.verified').exists(): sys.exit(93)
if (root/'etc/systemd/system/systemd-hwdb-update.service.d').exists(): sys.exit(94)
(root/'queried').write_text('published cache consumed before suppression')
mode = os.environ.get('HWDB_MODE', '')
if mode == 'fail': sys.exit(42)
if mode == 'timeout': sys.exit(124)
if mode == 'overflow':
    os.write(1, b'x'*65536)
    sys.exit(0)
if mode == 'stderr': print('unexpected diagnostic', file=sys.stderr)
sys.stdout.write('wrong answer\\n' if mode == 'wrong' else ''' + repr(QUERY) + ''')
''')
        helper.chmod(0o755)

    def inputs(self):
        (self.run/'hwdb-cache').write_bytes(self.data)
        (self.run/'hwdb-cache.sha256').write_text(hashlib.sha256(self.data).hexdigest()+'\n')

    def call(self, mode='', inject='', input_directory=None):
        input_directory = input_directory or self.run
        env = dict(os.environ, PATH=str(self.bin)+':'+os.environ['PATH'],
                   HWDB_FIXTURE=str(self.root), HWDB_MODE=mode, HWDB_INPUT=str(input_directory))
        return subprocess.run(['bash', '--noprofile', '--norc', '-c',
            'source "$1" || exit $?\n'+inject+
            '\nif prepare_hwdb_cache "$2" "$3" "$4"; then exit 0; else exit $?; fi',
            'fixture', str(SCRIPT), str(self.run), str(self.etc), str(input_directory)],
            env=env, capture_output=True, text=True, timeout=8)

    def clean_failure(self, result):
        self.assertNotEqual(result.returncode, 0, result.stdout+result.stderr)
        for path in (self.output, self.marker, self.dropin):
            self.assertFalse(path.exists(), str(path))
        for base in (self.run, self.etc):
            self.assertEqual(list(base.glob('.rog5-hwdb-cache.*')), [])

    def test_absent_optional_cache(self):
        self.assertEqual(self.call().returncode, 0)
        self.assertFalse((self.root/'queried').exists())

    def test_consumer_precedes_guard_and_marker(self):
        self.inputs()
        result = self.call()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((self.root/'queried').exists())
        self.assertEqual(self.output.read_bytes(), self.data)
        self.assertEqual(self.output.stat().st_nlink, 1)
        self.assertEqual(self.output.stat().st_mode & 0o777, 0o644)
        self.assertEqual(self.marker.read_bytes(), (self.run/'hwdb-cache.sha256').read_bytes())
        self.assertEqual(self.guard.read_text(), f'[Unit]\nConditionPathExists=!{self.run}/hwdb-cache.verified\n')
        self.assertFalse((self.etc/'.updated').exists())

    def test_failed_consumers_roll_back(self):
        self.inputs()
        for mode in ('fail', 'timeout', 'overflow', 'wrong', 'stderr'):
            with self.subTest(mode=mode):
                self.clean_failure(self.call(mode))

    def test_missing_consumer(self):
        self.inputs()
        (self.bin/'systemd-hwdb').write_text('#!/bin/sh\nexit 127\n')
        self.clean_failure(self.call())

    def test_missing_each_input(self):
        for member in ('hwdb-cache', 'hwdb-cache.sha256'):
            with self.subTest(member=member):
                self.inputs()
                (self.run/member).unlink()
                self.clean_failure(self.call())

    def test_hash_mismatch_prevents_query(self):
        self.inputs()
        (self.run/'hwdb-cache.sha256').write_text('0'*64+'\n')
        self.clean_failure(self.call())
        self.assertFalse((self.root/'queried').exists())

    def test_size_bounds(self):
        for size in (79, 67108865):
            self.inputs()
            with (self.run/'hwdb-cache').open('r+b') as stream:
                stream.truncate(size)
            self.clean_failure(self.call())

    def test_udev_symlink_refused(self):
        self.inputs()
        (self.etc/'udev').rmdir()
        (self.root/'other').mkdir()
        (self.etc/'udev').symlink_to(self.root/'other')
        self.clean_failure(self.call())

    def test_existing_cache_preserved(self):
        self.inputs()
        self.output.write_bytes(b'keep')
        self.assertNotEqual(self.call().returncode, 0)
        self.assertEqual(self.output.read_bytes(), b'keep')
        self.assertFalse(self.marker.exists())

    def test_payload_input_remains_separate_from_ram_marker(self):
        self.inputs()
        payload = self.run/'payload'; payload.mkdir()
        for name in ('hwdb-cache', 'hwdb-cache.sha256'):
            (self.run/name).rename(payload/name)
            (payload/name).chmod(0o444)
        result = self.call(input_directory=payload)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((payload/'hwdb-cache').read_bytes(), self.data)
        self.assertEqual((payload/'hwdb-cache').stat().st_mode & 0o777, 0o444)
        self.assertTrue(self.marker.exists())
        self.assertFalse((payload/'hwdb-cache.verified').exists())

    def test_failure_at_publication(self):
        self.inputs()
        for point in ('cache', 'guard', 'marker'):
            with self.subTest(point=point):
                self.clean_failure(self.call(inject='''ln() {
                    [[ ${@: -1} != "${'''+point+'''}" ]] || return 42
                    command ln "$@"
                }'''))

    def test_interruption_after_cache_publication(self):
        self.inputs()
        self.clean_failure(self.call(inject='''ln() {
            command ln "$@" || return $?
            [[ ${@: -1} != "$cache" ]] || kill -TERM "$BASHPID"
        }'''))

    def test_linker_and_hwdb_coexist(self):
        self.inputs()
        (self.run/'linker-cache').write_bytes(self.data)
        (self.run/'linker-cache.sha256').write_text(hashlib.sha256(self.data).hexdigest()+'\n')
        result = self.call(inject='prepare_linker_cache "$2" "$3" || exit $?')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((self.run/'linker-cache.verified').exists())
        self.assertTrue(self.marker.exists())
        self.assertTrue((self.etc/'systemd/system/ldconfig.service.d/50-rog5-cache.conf').exists())

    def test_boot_cache_dispatch_stops_after_linker_failure(self):
        self.inputs()
        result = self.call(inject='''prepare_linker_cache() { return 42; }
            prepare_hwdb_cache() { echo unexpected; return 0; }
            prepare_boot_caches "$2" "$3"
            exit $?''')
        self.assertEqual(result.returncode, 42)
        self.assertNotIn('unexpected', result.stdout)

    def test_actual_boot_dispatch_failure_stops_setup(self):
        self.inputs()
        boot = (ROOT/'tools/qemu-virtio-drm/logind-boot.sh').read_text()
        fragment = boot.split('source /run/logind-linker-cache.sh\n', 1)[1].split('\ndate -u ', 1)[0]
        # Execute the actual call site against private fixture roots. Substitute
        # only the physical poweroff effect; no host or guest power operation.
        fragment = fragment.replace('prepare_boot_caches /run /etc /run/payload;', 'prepare_boot_caches "$2" "$3" "$2";')
        fragment = fragment.replace('/usr/bin/poweroff -ff', "printf 'fixture poweroff\\n'")
        result = self.call(mode='fail', inject=fragment+'\necho unexpected continuation; exit 0')
        self.assertEqual(result.returncode, 1)
        self.assertIn('FAIL optional VM cache preparation', result.stdout)
        self.assertIn('fixture poweroff', result.stdout)
        self.assertNotIn('unexpected continuation', result.stdout)
        self.assertFalse(self.marker.exists())


if __name__ == '__main__':
    unittest.main()
