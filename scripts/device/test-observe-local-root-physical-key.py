#!/usr/bin/env python3
"""Exact shell FD/PRE/control flow with private host fixtures, no input reads."""
import json,os,shlex,subprocess,tempfile,unittest
from pathlib import Path
HERE=Path(__file__).resolve().parent;SOURCE=(HERE/'observe-local-root-physical-key.sh').read_text()
BOOT='11111111-1111-1111-1111-111111111111';PREVIOUS='22222222-2222-2222-2222-222222222222'
PREFIX,TAIL=SOURCE.split('\ncheck_runtime\ndiscover\nexec 7<',1)
MOCKS=r'''
check_runtime() {
 [ "${TEST_RUNTIME_FAIL:-0}" = 0 ] || fail 'fixture inhibitor absent'
 pid=123 start=456 lock='fixture exact inhibitor'
}
discover() {
 device=/dev/null
 identity=$(command stat -L -c '%d:%i:%t:%T' "$device")
 [ "${TEST_IDENTITY_BAD:-0}" = 0 ] || identity=wrong
 syspath=/fixture/input/event0; sysdev=1:3
}
awk() {
 if [ "$1" = '/^flags:/ {print $2}' ]; then printf '%s\n' "$TEST_FLAGS"; else command awk "$@"; fi
}
stat() {
 if [ "$*" = '-f -c %T /run' ]; then printf 'tmpfs\n'; else command stat "$@"; fi
}
mktemp() { command mktemp -d "$FIXTURE_ROOT/observer.XXXXXX"; }
dd() { printf 'dd_called\n' > "$FIXTURE_ROOT/dd-called"; return 1; }
timeout() { [ "$6" = dd ] || return 2; shift 5; "$@"; }
'''
class ReaderTests(unittest.TestCase):
    def fixture(self,flags='0400000',key='power',mode='--preflight',seconds='90',**extra):
        with tempfile.TemporaryDirectory(prefix="rog5-reader-fd-") as temp:
            root=Path(temp);script=root/'fixture.sh'
            script.write_text('id() { printf "0\\n"; }\n'+PREFIX+'\n'+MOCKS+'\ncheck_runtime\ndiscover\nexec 7<'+TAIL)
            args=[BOOT,PREVIOUS,key,seconds,'b'*64]+([] if mode is None else [mode])
            env=dict(os.environ,ALLOW_ROG5_LOCAL_KEY_OBSERVER='rog5-v9-local-key-observer-v1',FIXTURE_ROOT=temp,TEST_FLAGS=flags,**extra)
            result=subprocess.run(['/usr/bin/bash','--posix',str(script),*args],env=env,capture_output=True,text=True,timeout=3)
            return result,(root/'dd-called').exists(),list(root.glob('observer.*'))
    def test_arm64_largefile_is_not_generic_largefile(self):
        result=subprocess.run(['/usr/bin/bash','--posix','-c','flags=0400000; printf "%s %s\\n" "$((flags & ~02100000))" "$((flags & ~02400000))"'],capture_output=True,text=True,check=True)
        self.assertEqual(result.stdout,'131072 0\n')
    def test_allowed_read_flags(self):
        for flags in ('0','0400000','02000000','02400000'):
            with self.subTest(flags=flags):
                result,read,left=self.fixture(flags);self.assertEqual(result.returncode,0,result.stderr);self.assertFalse(read);self.assertEqual(left,[])
    def test_write_or_extra_flags_refused(self):
        for bit in (1,2,0o4000,0o2000,0o10000000,0o100000,0o200000,0o40000):
            flags='0'+format(0o400000|bit,'o')
            with self.subTest(flags=flags):
                result,read,_=self.fixture(flags);self.assertNotEqual(result.returncode,0);self.assertIn('FD must be read-only',result.stderr);self.assertFalse(read);self.assertNotIn('READY',result.stderr)
    def test_malformed_flags_refused(self):
        for flags in ('','888','-1','0400000 extra'):
            with self.subTest(flags=flags):
                result,read,_=self.fixture(flags);self.assertNotEqual(result.returncode,0);self.assertIn('invalid FD flags',result.stderr);self.assertFalse(read)
    def test_all_three_preflight_without_ready_or_read(self):
        for key in ('power','volume-down','volume-up'):
            with self.subTest(key=key):
                result,read,left=self.fixture(key=key);self.assertEqual(result.returncode,0,result.stderr);self.assertEqual(result.stdout,'');self.assertFalse(read);self.assertEqual(left,[])
                self.assertEqual([line.split('\t')[0] for line in result.stderr.splitlines()],['PRE','PREFLIGHT']);self.assertIn('\t'+key+'\t90',result.stderr);self.assertNotIn('READY',result.stderr)
    def test_missing_inhibitor_refuses_preflight(self):
        result,read,_=self.fixture(TEST_RUNTIME_FAIL='1');self.assertNotEqual(result.returncode,0);self.assertFalse(read);self.assertNotIn('PREFLIGHT',result.stderr)
    def test_mismatched_fd_refuses_preflight(self):
        result,read,_=self.fixture(TEST_IDENTITY_BAD='1');self.assertNotEqual(result.returncode,0);self.assertIn('FD identity mismatch',result.stderr);self.assertFalse(read)
    def test_default_mode_still_ready_before_read(self):
        result,read,left=self.fixture(mode=None);self.assertNotEqual(result.returncode,0);self.assertTrue(read);self.assertIn('READY\t'+BOOT+'\tpower\t90',result.stderr);self.assertNotIn('PREFLIGHT',result.stderr);self.assertEqual(left,[])
    def test_unknown_mode_refused(self):
        result,read,_=self.fixture(mode='--other');self.assertNotEqual(result.returncode,0);self.assertIn('unknown observer mode',result.stderr);self.assertFalse(read)
    def test_original_timeout_bounds_unchanged(self):
        for seconds in ('29','301','bad'):
            result,read,_=self.fixture(seconds=seconds);self.assertNotEqual(result.returncode,0);self.assertFalse(read)
if __name__=='__main__':unittest.main()
