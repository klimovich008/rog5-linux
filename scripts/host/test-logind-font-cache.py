#!/usr/bin/env python3
"""Execute the guest helper with real files and substituted external CLIs."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

HELPER = Path(__file__).resolve().parents[2] / 'tools/qemu-virtio-drm/logind-font-cache.sh'


class FontCacheTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='rog5-font-cache-test-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.bin = self.root / 'bin'; self.bin.mkdir()
        self.home = self.root / 'home'; self.home.mkdir()
        self.cache = self.root / 'cache'
        self.fonts = self.root / 'fonts'; self.fonts.mkdir()
        self.defaults = self.root / 'defaults'; self.defaults.mkdir()
        self.conf = self.root / 'conf.d'; self.conf.mkdir()
        (self.defaults / '10-default.conf').write_text('<fontconfig/>\n')
        self.hook = self.root / 'config-hook'
        # Same install/remove loop as the packaged hook; CLI fixture only.
        self.hook.write_text('''#!/bin/bash
while read -r f; do
 link="${1:?}/${f##*/}"
 if [[ -e $f && ! -e $link ]]; then
  ln -sT "/$f" "$link"
 elif [[ ! -e $f && -L $link ]]; then
  rm -f "$link"
 fi
done
''')
        (self.fonts / 'fixture.ttf').write_bytes(b'fixture font, not parsed by fake CLI')
        self.env = {**os.environ, 'PATH': str(self.bin) + ':' + os.environ['PATH'],
                    'TEST_CACHE': str(self.cache), 'TEST_FONTS': str(self.fonts),
                    'TEST_RECORD': str(self.root / 'calls'), 'TEST_MODE': 'success',
                    'TEST_CONF': str(self.conf)}
        self.command('timeout', '''printf 'timeout %s\\n' "$*" >> "$TEST_RECORD"
[[ $1 == -k && $2 == 1 && ( $3 == 20 || $3 == 10 ) ]] || exit 98
shift 3
exec "$@"
''')
        self.command('setpriv', '''printf 'setpriv %s\\n' "$*" >> "$TEST_RECORD"
[[ $1 == --reuid=1000 && $2 == --regid=1000 && $3 == --clear-groups && $4 == --no-new-privs ]] || exit 98
shift 4
exec "$@"
''')
        self.command('fc-conflist', '''case $TEST_MODE in
 config42) exit 42;; config124) exit 124;; ignoredconfig) echo "- $TEST_CONF/10-default.conf: ignored"; exit 0;;
 missingconfig) exit 0;; esac
for f in "$TEST_CONF"/*.conf; do printf '+ %s: fixture processed\\n' "$f"; done
''')
        self.command('fc-cache', '''[[ $* == '-s -v' ]] || exit 98
case $TEST_MODE in prepare42) exit 42;; prepare124) exit 124;; missing) exit 0;; esac
printf cache > "$TEST_CACHE/abc-le64.cache-12"
ln -s abc-le64.cache-12 "$TEST_CACHE/abc-le64.cache-11"
case $TEST_MODE in empty) : > "$TEST_CACHE/abc-le64.cache-12";;
 symlink) rm "$TEST_CACHE/abc-le64.cache-12"; ln -s "$TEST_FONTS/fixture.ttf" "$TEST_CACHE/abc-le64.cache-12";; esac
echo 'skipping, existing cache is valid: 1 fonts, 0 dirs'
''')
        self.command('fc-match', '''[[ $LANG == C.UTF-8 && $FC_DEBUG == 16 && $XDG_CACHE_HOME == "$HOME/.cache" ]] || exit 98
[[ $1 == -f && $2 == 'FONT_FILE=%{file}\\n' && $3 == sans ]] || exit 98
case $TEST_MODE in consume42) exit 42;; consume124) exit 124;;
 oversized) printf '%1048577s' x; exit 0;;
 mutated) printf changed >> "$TEST_CACHE/abc-le64.cache-12";;
 rewritten) printf cache > "$TEST_CACHE/new"; mv "$TEST_CACHE/new" "$TEST_CACHE/abc-le64.cache-12";;
 fallback) mkdir -p "$HOME/.cache/fontconfig";;
 legacyfallback) mkdir -p "$HOME/.fontconfig";;
 deleted) rm "$TEST_CACHE/abc-le64.cache-11" "$TEST_CACHE/abc-le64.cache-12";;
 aliasmutated) rm "$TEST_CACHE/abc-le64.cache-11";; esac
if [[ $TEST_MODE != missingdebug ]]; then
 echo "cache: abc-le64.cache-12 (dir: $TEST_FONTS)"
 checksum=1789235204
 [[ $TEST_MODE != mismatchedchecksum ]] || checksum=100
 echo "FcCacheTimeValid dir \\\"$TEST_FONTS\\\" cache checksum 1789235204 dir checksum $checksum"
fi
case $TEST_MODE in
 wrongfont) echo 'FONT_FILE=/outside/wrong.ttf';;
 missingfont) echo "FONT_FILE=$TEST_FONTS/missing.ttf";;
 nofont) :;;
 duplicate) printf 'FONT_FILE=%s/fixture.ttf\\nFONT_FILE=%s/fixture.ttf\\n' "$TEST_FONTS" "$TEST_FONTS";;
 escaped) echo "FONT_FILE=$TEST_FONTS/../outside.ttf";;
 *) echo "FONT_FILE=$TEST_FONTS/fixture.ttf";;
esac
''')

    def command(self, name, script):
        path = self.bin / name
        path.write_text('#!/bin/bash\nset -eu\n' + script)
        path.chmod(0o755)

    def run_helper(self, mode='success'):
        return subprocess.run(['bash', '-euc', 'source "$1"; prepare_font_cache "$2" "$3" "$4" "$5" "$6" "$7"',
                               'fixture', str(HELPER), str(self.cache), str(self.home), str(self.fonts),
                               str(self.defaults), str(self.conf), str(self.hook)],
                              env={**self.env, 'TEST_MODE': mode}, capture_output=True, text=True, timeout=4)

    def test_default_config_restored_as_exact_absolute_hook_link(self):
        result = self.run_helper()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((self.conf / '10-default.conf').is_symlink())
        self.assertEqual(os.readlink(self.conf / '10-default.conf'), str(self.defaults / '10-default.conf'))
        self.assertIn(f'+ {self.conf}/10-default.conf:', result.stdout)

    def test_existing_config_and_unrelated_files_preserved(self):
        existing = self.conf / '10-default.conf'; existing.write_text('<fontconfig>override</fontconfig>')
        readme = self.conf / 'README'; readme.write_text('retain')
        before = (existing.read_bytes(), existing.stat().st_ino, existing.stat().st_mtime_ns)
        result = self.run_helper()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((existing.read_bytes(), existing.stat().st_ino, existing.stat().st_mtime_ns), before)
        self.assertEqual(readme.read_text(), 'retain')

    def test_existing_valid_override_symlink_preserved(self):
        override = self.root / 'override.conf'; override.write_text('<fontconfig/>\n')
        target = self.conf / '10-default.conf'; target.symlink_to(override)
        before = (target.lstat().st_ino, os.readlink(target), override.read_bytes())
        result = self.run_helper()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((target.lstat().st_ino, os.readlink(target), override.read_bytes()), before)

    def test_dangling_config_conflict_refused_before_hook(self):
        target = self.conf / '10-default.conf'; target.symlink_to('missing')
        result = self.run_helper()
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(os.readlink(target), 'missing')

    def test_defaults_must_exist_and_resolve(self):
        (self.defaults / '10-default.conf').unlink()
        result = self.run_helper()
        self.assertNotEqual(result.returncode, 0)
        (self.defaults / '10-default.conf').symlink_to('missing')
        result = self.run_helper()
        self.assertNotEqual(result.returncode, 0)

    def test_unprocessed_default_and_config_status_fail(self):
        for mode in ('ignoredconfig', 'missingconfig', 'config42', 'config124'):
            with self.subTest(mode=mode):
                self.cache = self.root / mode; self.env['TEST_CACHE'] = str(self.cache)
                result = self.run_helper(mode)
                expected = 42 if mode == 'config42' else 124 if mode == 'config124' else 1
                self.assertEqual(result.returncode, expected, result.stderr)

    def test_hook_failure_and_wrong_link_refused(self):
        self.hook.write_text('exit 42\n')
        self.assertEqual(self.run_helper().returncode, 42)
        self.hook.write_text('ln -s /wrong "$1/10-default.conf"\n')
        self.assertNotEqual(self.run_helper().returncode, 0)

    def test_hook_first_link_failure_cannot_be_hidden_by_later_success(self):
        (self.defaults / '20-second.conf').write_text('<fontconfig/>\n')
        self.command('ln', '''if [[ $* == *10-default.conf* ]]; then exit 42; fi
exec /usr/bin/ln "$@"
''')
        result = self.run_helper()
        self.assertEqual(result.returncode, 42, result.stderr)
        self.assertFalse((self.conf / '20-second.conf').exists())
        self.assertFalse(self.cache.exists())

    def test_configuration_mutation_is_refused(self):
        target = self.conf / '10-default.conf'; target.write_text('<fontconfig>retain</fontconfig>')
        self.hook.write_text('printf changed > "$1/10-default.conf"\n')
        result = self.run_helper()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('preexisting font configuration changed', result.stderr)

    def test_source_has_no_execution_or_writes(self):
        result = subprocess.run(['bash', '-euc', 'source "$1"', 'fixture', str(HELPER)],
                                env=self.env, capture_output=True, text=True, timeout=2)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(self.cache.exists())
        self.assertFalse((self.root / 'calls').exists())
        self.assertEqual(result.stdout + result.stderr, '')

    def test_success_real_cache_files_alias_and_consumer_environment(self):
        before = (self.fonts / 'fixture.ttf').stat().st_mtime_ns
        result = self.run_helper()
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertIn('PASS', result.stdout)
        self.assertIn('FcCacheTimeValid dir', result.stdout)
        self.assertIn('stage=prepare phase=end status=0 elapsed_seconds=', result.stderr)
        self.assertIn('stage=consume phase=end status=0 elapsed_seconds=', result.stderr)
        calls = (self.root / 'calls').read_text()
        self.assertIn('timeout -k 1 20 fc-cache -s -v', calls)
        self.assertIn('timeout -k 1 10 setpriv', calls)
        self.assertIn('--reuid=1000 --regid=1000 --clear-groups --no-new-privs', calls)
        self.assertLess(calls.index('fc-cache -s -v'), calls.index('fc-conflist'))
        self.assertLess(calls.index('fc-conflist'), calls.index('fc-match -f'))
        self.assertEqual((self.cache / 'abc-le64.cache-12').read_bytes(), b'cache')
        self.assertEqual((self.fonts / 'fixture.ttf').stat().st_mtime_ns, before)

    def test_external_exit_status_and_stage_preserved(self):
        for mode in ('prepare42', 'prepare124', 'consume42', 'consume124'):
            with self.subTest(mode=mode):
                # Each invocation owns a fresh cache; never erase another run.
                self.cache = self.root / mode
                self.env['TEST_CACHE'] = str(self.cache)
                result = self.run_helper(mode)
                status = 124 if mode.endswith('124') else 42
                self.assertEqual(result.returncode, status, result.stderr)
                stage = 'prepare' if mode.startswith('prepare') else 'consume'
                self.assertIn(f'stage={stage} phase=end status={status}', result.stderr)
                self.assertNotIn('PASS', result.stdout)

    def test_invalid_cache_inventory(self):
        for mode in ('missing', 'empty', 'symlink'):
            with self.subTest(mode=mode):
                self.cache = self.root / mode; self.env['TEST_CACHE'] = str(self.cache)
                result = self.run_helper(mode)
                self.assertNotEqual(result.returncode, 0)
                self.assertNotIn('PASS', result.stdout)

    def test_mutation_or_removal_refused(self):
        for mode in ('mutated', 'deleted', 'aliasmutated', 'rewritten'):
            with self.subTest(mode=mode):
                self.cache = self.root / mode; self.env['TEST_CACHE'] = str(self.cache)
                result = self.run_helper(mode)
                self.assertNotEqual(result.returncode, 0)
                self.assertNotIn('PASS', result.stdout)

    def test_consumer_diagnostic_output_bound(self):
        result = self.run_helper('oversized')
        self.assertEqual(result.returncode, 42)
        self.assertIn('stage=consume phase=end status=42', result.stderr)
        self.assertLess(len(result.stdout), 1048576)

    def test_retained_warm_debug_format_with_real_inventory(self):
        # Sanitized records retain exact2.18.3 debug grammar and observed font
        # directory layout. This is parser proof, not replayed font execution.
        self.cache.mkdir()
        records = []
        rows = [('3830d5c3ddfd5cd38a049b759396e72e', '', 1789235204),
                ('4b31aef11cb0687b6d280d34cbe23592', '/Adwaita', 1788569924),
                ('a1c95d6dfc9a7b34f44445cf81166004', '/encodings', 1775776340),
                ('923e285e415b1073c8df160bee08820f', '/noto', 1788260175),
                ('5ca8086aeacc9c68e81a71e7ef846b3b', '/encodings/large', 1775776340)]
        for basename, suffix, checksum in rows:
            name = basename + '-le64.cache-12'
            (self.cache / name).write_bytes(b'fixture cache')
            records += [f'cache: {name} (dir: {self.fonts}{suffix})',
                        f'FcCacheTimeValid dir "{self.fonts}{suffix}" cache checksum {checksum} dir checksum {checksum}']
        result = subprocess.run(['bash', '-euc', 'source "$1"; font_cache_loaded "$2" "$3" "$4"',
                                 'fixture', str(HELPER), str(self.cache), str(self.fonts), '\n'.join(records)],
                                env=self.env, capture_output=True, text=True, timeout=2)
        self.assertEqual(result.returncode, 0, result.stderr)
        # A cache omitted from otherwise valid debug records cannot pass.
        (self.cache / 'unreported-le64.cache-12').write_bytes(b'extra')
        result = subprocess.run(result.args, env=self.env, capture_output=True, text=True, timeout=2)
        self.assertNotEqual(result.returncode, 0)

    def test_new_fallback_refused(self):
        result = self.run_helper('fallback')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('fallback', result.stderr)

    def test_new_legacy_fallback_refused(self):
        result = self.run_helper('legacyfallback')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('fallback', result.stderr)

    def test_preexisting_fallback_refused_before_command(self):
        (self.home / '.cache/fontconfig').mkdir(parents=True)
        result = self.run_helper()
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((self.root / 'calls').exists())

    def test_font_result_must_be_unique_readable_and_contained(self):
        (self.root / 'outside.ttf').write_text('outside')
        for mode in ('wrongfont', 'missingfont', 'nofont', 'duplicate', 'escaped'):
            with self.subTest(mode=mode):
                self.cache = self.root / mode; self.env['TEST_CACHE'] = str(self.cache)
                result = self.run_helper(mode)
                self.assertNotEqual(result.returncode, 0)
                self.assertNotIn('PASS', result.stdout)

    def test_streaming_hash_failure_preserved(self):
        self.command('sha256sum', 'exit 42\n')
        result = self.run_helper()
        self.assertEqual(result.returncode, 42)
        self.assertNotIn('PASS', result.stdout)

    def test_consumer_must_validate_each_cache_checksum(self):
        for mode in ('missingdebug', 'mismatchedchecksum'):
            with self.subTest(mode=mode):
                self.cache = self.root / mode; self.env['TEST_CACHE'] = str(self.cache)
                result = self.run_helper(mode)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn('consumption diagnostics', result.stderr)
                self.assertNotIn('PASS', result.stdout)


if __name__ == '__main__':
    unittest.main()
