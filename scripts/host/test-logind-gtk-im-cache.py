#!/usr/bin/env python3
"""Run GTK RAM-cache preparation with real files/processes and a query CLI seam."""
import os
import hashlib
from pathlib import Path
import signal
import subprocess
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[2]
HELPER = ROOT / 'tools/qemu-virtio-drm/logind-gtk-im-cache.sh'
CACHE = ('# GTK+ Input Method Modules file\n'
         '"/usr/lib/gtk-3.0/3.0.0/immodules/im-wayland.so" \n'
         '"wayland" "Wayland" "gtk30" "/usr/share/locale" "" \n')


class GtkInputCache(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='rog5-gtk-cache-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.bin = self.root / 'bin'; self.bin.mkdir()
        self.cache = self.root / 'cache'; self.cache.mkdir()
        self.fixture = self.root / 'query-output'; self.fixture.write_text(CACHE)
        self.query('cat "$FIXTURE"\n')
        self.env = {'PATH': str(self.bin) + ':/usr/bin:/bin', 'HOME': str(self.root),
                    'LC_ALL': 'C', 'FIXTURE': str(self.fixture),
                    'MARKER': str(self.root / 'started')}
        self.cmd = ['bash', '-c', 'source "$1"; prepare_gtk_im_cache "$2"',
                    'cache-test', str(HELPER), str(self.cache)]

    def query(self, text):
        p = self.bin / 'gtk-query-immodules-3.0'
        p.write_text('#!/bin/bash\nset -eu\n[[ $# == 0 && $LC_ALL == C ]]\n'+text)
        p.chmod(0o700)

    def run_helper(self):
        return subprocess.run(self.cmd, env=self.env, capture_output=True, text=True, timeout=15)

    def refuse(self):
        r = self.run_helper()
        self.assertNotEqual(r.returncode, 0)
        self.assertNotIn('PASS GTK input-method cache', r.stdout)
        self.assertFalse((self.cache / 'immodules.cache').exists())
        self.assertEqual(list(self.cache.iterdir()), [])
        return r

    def test_complete_registration_publishes_atomically(self):
        r = self.run_helper(); self.assertEqual(r.returncode, 0, r.stderr)
        p = self.cache / 'immodules.cache'
        self.assertEqual(p.read_text(), CACHE)
        self.assertEqual(p.stat().st_mode & 0o777, 0o644)
        self.assertEqual(list(self.cache.iterdir()), [p])

    def test_query_error_preserved_and_partial_cache_removed(self):
        self.query('cat "$FIXTURE"; echo original-error >&2; exit 42\n')
        r = self.refuse(); self.assertEqual(r.returncode, 42); self.assertIn('original-error', r.stderr)

    def test_timeout_status_preserved(self):
        self.query('exit 124\n'); self.assertEqual(self.refuse().returncode, 124)

    def test_zero_exit_with_discovery_errors_refused(self):
        self.query('cat "$FIXTURE"; echo module-load-failed >&2\n'); self.refuse()

    def test_empty_output_refused(self):
        self.query(':\n'); self.refuse()

    def test_wrong_module_stanza_refused(self):
        self.fixture.write_text(CACHE.replace('im-wayland.so', 'im-other.so')); self.refuse()

    def test_missing_context_refused(self):
        self.fixture.write_text(CACHE.replace('"wayland"', '"other"')); self.refuse()

    def test_duplicate_registration_refused(self):
        self.fixture.write_text(CACHE + CACHE); self.refuse()

    def test_oversized_output_is_bounded_and_refused(self):
        self.query('head -c 262144 /dev/zero\n'); self.refuse()

    def test_existing_cache_never_replaced(self):
        p = self.cache / 'immodules.cache'; p.write_text('retained')
        r = self.run_helper(); self.assertNotEqual(r.returncode, 0); self.assertEqual(p.read_text(), 'retained')

    def test_dangling_destination_never_followed(self):
        p = self.cache / 'immodules.cache'; p.symlink_to(self.root / 'absent')
        r = self.run_helper(); self.assertNotEqual(r.returncode, 0); self.assertTrue(p.is_symlink())
        self.assertFalse((self.root / 'absent').exists())

    def test_two_preparers_cannot_replace_each_other(self):
        processes = [subprocess.Popen(self.cmd, env=self.env, stdout=subprocess.PIPE,
                     stderr=subprocess.PIPE, start_new_session=True) for _ in range(2)]
        try:
            for p in processes: p.communicate(timeout=15)
            self.assertEqual(sum(p.returncode == 0 for p in processes), 1)
            self.assertEqual((self.cache / 'immodules.cache').read_text(), CACHE)
            self.assertEqual(len(list(self.cache.iterdir())), 1)
        finally:
            for p in processes:
                if p.poll() is None: os.killpg(p.pid, signal.SIGKILL); p.wait()

    def test_raced_destination_directory_cannot_receive_nested_cache(self):
        destination = self.cache / 'immodules.cache'
        self.env['DESTINATION'] = str(destination)
        self.query('mkdir "$DESTINATION"; cat "$FIXTURE"\n')
        r = self.run_helper()
        self.assertTrue(destination.is_dir())
        self.assertEqual(list(destination.iterdir()), [], r.stdout+r.stderr)
        self.assertNotEqual(r.returncode, 0, r.stdout+r.stderr)
        self.assertNotIn('PASS GTK input-method cache', r.stdout)
        self.assertEqual(list(self.cache.iterdir()), [destination])

    def test_raced_destination_symlink_cannot_write_external_directory(self):
        destination = self.cache / 'immodules.cache'
        outside = self.root / 'retained'; outside.mkdir()
        marker = outside / 'marker'; marker.write_text('retained')
        self.env.update(DESTINATION=str(destination), OUTSIDE=str(outside))
        self.query('ln -s "$OUTSIDE" "$DESTINATION"; cat "$FIXTURE"\n')
        r = self.run_helper()
        self.assertTrue(destination.is_symlink())
        self.assertEqual(list(outside.iterdir()), [marker], r.stdout+r.stderr)
        self.assertEqual(marker.read_text(), 'retained')
        self.assertNotEqual(r.returncode, 0, r.stdout+r.stderr)
        self.assertNotIn('PASS GTK input-method cache', r.stdout)
        self.assertEqual(list(self.cache.iterdir()), [destination])

    def test_interruption_removes_unpublished_cache(self):
        self.query('cat "$FIXTURE"; touch "$MARKER"; sleep 10\n')
        p = subprocess.Popen(self.cmd, env=self.env, stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE, start_new_session=True)
        try:
            limit = time.monotonic() + 3
            while not (self.root / 'started').exists() and time.monotonic() < limit:
                time.sleep(.01)
            self.assertTrue((self.root / 'started').exists())
            os.killpg(p.pid, signal.SIGTERM); p.communicate(timeout=3)
            self.assertNotEqual(p.returncode, 0)
            self.assertEqual(list(self.cache.iterdir()), [])
        finally:
            if p.poll() is None: os.killpg(p.pid, signal.SIGKILL); p.wait()


class GtkModuleOverride(unittest.TestCase):
    """Real guard/hash/rollback code; mount syscalls are filesystem adapters."""
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='rog5-gtk-override-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.session = self.root/'session'; self.system = self.root/'system'
        self.bin = self.root/'bin'; self.bin.mkdir()
        rel = 'lib/gtk-3.0/3.0.0/immodules/im-wayland.so'
        self.source = self.session/'usr'/rel; self.target = self.system/rel
        self.contract = self.session/'usr/share/rog5-denial/gtk-im-override.sha256'
        for p in (self.source, self.target, self.contract): p.parent.mkdir(parents=True, exist_ok=True)
        self.source.write_bytes(b'patched module'); self.target.write_bytes(b'original module')
        self.old = hashlib.sha256(self.target.read_bytes()).hexdigest()
        self.new = hashlib.sha256(self.source.read_bytes()).hexdigest()
        self.contract.write_text(self.old+' '+self.new+'\n')
        self.env = dict(PATH=str(self.bin)+':/usr/bin:/bin', HOME=str(self.root), LC_ALL='C',
                        STATE=str(self.root/'mounted'), SAVED=str(self.root/'saved'),
                        MODE='success', CALLS=str(self.root/'calls'))
        self.command('mountpoint', '[[ $MODE != mountpoint-error ]] || exit 2\n[[ -f $STATE ]] && exit 0 || exit 32\n')
        self.command('findmnt', '[[ $MODE != writable ]] && echo ro,relatime || echo rw,relatime\n')
        self.command('umount', 'echo umount >> "$CALLS"; rm "$2"; mv "$SAVED" "$2"; rm "$STATE"\n')
        self.command('mount', r"""
echo mount >> "$CALLS"
if [[ $1 == --bind ]]; then
    [[ $MODE != bind-fail ]] || exit 41
    mv "$3" "$SAVED"; cp "$2" "$3"; touch "$STATE"
    [[ $MODE != corrupt ]] || printf corrupt > "$3"
else
    [[ $MODE != remount-fail ]] || exit 42
    if [[ $MODE == interrupt ]]; then kill -TERM "$PPID"; exit 0; fi
fi
""")
        self.cmd = ['bash', '-c', 'source "$1"; stage_gtk_im_override "$2" "$3"',
                    'override-test', str(HELPER), str(self.session), str(self.system)]

    def command(self, name, body):
        p = self.bin/name; p.write_text('#!/bin/bash\nset -eu\n'+body); p.chmod(0o700)

    def run_helper(self):
        return subprocess.run(self.cmd, env=self.env, capture_output=True, text=True, timeout=5)

    def refuse(self):
        r = self.run_helper(); self.assertNotEqual(r.returncode, 0, r.stdout+r.stderr)
        self.assertNotIn('PASS VM-only', r.stdout)
        self.assertEqual(self.target.read_bytes(), b'original module')
        self.assertFalse((self.root/'mounted').exists())
        return r

    def test_optional_absent_is_noop(self):
        self.source.unlink(); self.contract.unlink()
        r = self.run_helper(); self.assertEqual(r.returncode, 0, r.stderr)
        self.assertFalse((self.root/'calls').exists()); self.assertEqual(self.target.read_bytes(), b'original module')

    def test_success_checks_both_hashes_and_readonly_mount(self):
        r = self.run_helper(); self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn('original='+self.old+' replacement='+self.new+' read-only', r.stdout)
        self.assertEqual(self.target.read_bytes(), b'patched module')
        self.assertEqual((self.root/'calls').read_text().splitlines(), ['mount','mount'])

    def test_missing_contract_refused(self):
        self.contract.unlink(); self.refuse()

    def test_missing_module_refused(self):
        self.source.unlink(); self.refuse()

    def test_bad_original_hash_refused(self):
        self.contract.write_text('0'*64+' '+self.new+'\n'); self.refuse()

    def test_bad_replacement_hash_refused(self):
        self.source.write_bytes(b'changed'); self.refuse()

    def test_extra_contract_fields_refused(self):
        self.contract.write_text(self.old+' '+self.new+' extra\n'); self.refuse()

    def test_source_symlink_refused(self):
        saved = self.root/'source'; self.source.rename(saved); self.source.symlink_to(saved); self.refuse()

    def test_hardlinked_readonly_baseline_is_preserved(self):
        alias = self.root/'baseline-link'; os.link(self.target, alias)
        r = self.run_helper(); self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(alias.read_bytes(), b'original module')
        self.assertEqual(self.target.read_bytes(), b'patched module')

    def test_source_hardlink_refused(self):
        os.link(self.source, self.root/'source-link'); self.refuse()

    def test_bind_failure_preserves_code_and_original(self):
        self.env['MODE']='bind-fail'; self.assertEqual(self.refuse().returncode, 41)

    def test_remount_failure_rolls_back(self):
        self.env['MODE']='remount-fail'; self.assertEqual(self.refuse().returncode, 42)
        self.assertIn('umount', (self.root/'calls').read_text())

    def test_writable_mount_refused_and_rolled_back(self):
        self.env['MODE']='writable'; self.refuse()

    def test_post_bind_identity_mismatch_rolled_back(self):
        self.env['MODE']='corrupt'; self.refuse()

    def test_interruption_rolls_back(self):
        self.env['MODE']='interrupt'; self.assertEqual(self.refuse().returncode, 143)

    def test_mountpoint_probe_error_refused_before_mount(self):
        self.env['MODE']='mountpoint-error'; self.refuse()
        self.assertFalse((self.root/'calls').exists())

    def test_existing_mount_is_not_unmounted(self):
        (self.root/'mounted').touch(); r = self.run_helper()
        self.assertNotEqual(r.returncode, 0); self.assertTrue((self.root/'mounted').exists())
        self.assertFalse((self.root/'calls').exists())


if __name__ == '__main__':
    unittest.main()
