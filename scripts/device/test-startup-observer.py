#!/usr/bin/env python3
"""Post-handover observation regressions; no phone or real systemd mutations."""
import importlib.util
from pathlib import Path
import subprocess
import sys
import shlex
import unittest
import gzip
import hashlib
import tempfile

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO/'scripts/host'))
SPEC = importlib.util.spec_from_file_location('receiver', REPO/'scripts/host/headless-stage-receiver.py')
M = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(M)
BOOT = '12345678-1234-4abc-8def-1234567890ab'
RELEASE = '7.1.4-g359318de534f'
SEALED_ARCHIVE = None


class StartupObservationTest(unittest.TestCase):
    def test_state_start_failure_reports_rejected_gate_over_observer(self):
        source = (REPO/'initramfs/persistent-service-state').read_text()
        start = source[source.index('start_state() {'):source.index('\nstop_state() {')]
        dispatch = source[source.index('case $action in\n'):]
        # Keep the production failure exit; redirect its log to test stdout,
        # never the host kernel buffer.
        fail = source[source.index('fail() {'):source.index('\naction=')].replace(
            '>/dev/kmsg 2>/dev/null', '')
        for rejected, phase in (
            ('resolve_exact_devices', 'devices'),
            ('resolve_userdata_owner', 'owner'),
            ('verify_root_storage_mounts', 'root-mounts'),
            ('verify_filesystem_identity', 'userdata-fs'),
        ):
            with self.subTest(rejected=rejected):
                # All four failures precede any write window. Endpoint mocks
                # must never reach mount/blockdev/loop I/O or cleanup setup.
                script = '''set -eu
action=start
runtime_record=/absent-state-record
runtime_next=/absent-state-next
userdata=/dev/fixture23
expected_userdata_uuid=fixture
expected_userdata_label=fixture
bb() { printf 'UNEXPECTED_IO\\n' >&2; exit 98; }
'''
                for name in ('resolve_exact_devices', 'resolve_userdata_owner',
                             'verify_root_storage_mounts', 'verify_filesystem_identity'):
                    script += name + '() { return ' + ('1' if name == rejected else '0') + '; }\n'
                failure = self.execute(script + fail + start + '\n' + dispatch,
                                       expected_code=1).decode().strip()
                self.assertEqual(failure, f'rog5-persistent-state: FAIL start/{phase} contract failed')
                status = 'LoadState=loaded\nActiveState=failed\nSubState=failed\nResult=exit-code\nExecMainStatus=1'
                record = M.parse_startup_observation(self.produce(status, failure), RELEASE)
                self.assertEqual(bytes.fromhex(record['failure_hex']).decode().strip(), failure)
                self.assertLessEqual(len(failure), 80)

    def test_unavailable_journal_uses_bounded_read_only_kernel_buffer(self):
        source=(REPO/'initramfs/persistent-startup-observer').read_text()
        function=source[source.index('query_failure() {'):source.index('\nobserve_unit() {')]
        # Replay the observed journal error; only a fixed helper prefix may
        # leave the kernel-buffer fallback. No real journal/kernel is accessed.
        script='''bb() {
case "$*" in
  'timeout -s KILL 2 /usr/bin/journalctl '*) return 1 ;;
  'timeout -s KILL 2 /run/initramfs/lib/ld-musl-aarch64.so.1 /run/initramfs/bin/busybox dmesg -r -s 65536')
    printf '%s\\n' '<6>[ 2.00] unrelated private material' \\
      '<3>[ 50.123] rog5-persistent-state: FAIL start contract failed' \\
      '<3>[ 51.00] rog5-p2-attest: FAIL other-unit' ;;
  *) command "$@" ;;
esac
}
'''+function+'\nquery_failure rog5-persistent-state\n'
        output=self.execute(script).decode()
        self.assertEqual(output,'source=kernel-buffer\nrog5-persistent-state: FAIL start contract failed\n')
        status='LoadState=loaded\nActiveState=failed\nSubState=failed\nResult=exit-code\nExecMainStatus=1'
        record=M.parse_startup_observation(self.produce(status,output),RELEASE)
        self.assertEqual(record['journal'],'error')
        self.assertEqual(bytes.fromhex(record['failure_hex']),
                         b'rog5-persistent-state: FAIL start contract failed\n')

    def produce(self, status, journal='', code=0, journal_code=0):
        source = (REPO/'initramfs/persistent-startup-observer').read_text()
        functions = source[source.index('observe_unit() {'):source.index('\n# Entrypoint')]
        script = '''bb() { command "$@"; }
query_status() { printf '%s\\n' "$FIXTURE_STATUS"; return "$FIXTURE_CODE"; }
query_failure() { printf '%s\\n' "$FIXTURE_JOURNAL"; return "$FIXTURE_JOURNAL_CODE"; }
'''+functions+f'\nrelease={RELEASE}\nboot={BOOT}\nsequence=1\nobserve_unit state\n'
        script = ('FIXTURE_STATUS='+shlex.quote(status)+'\nFIXTURE_CODE='+str(code)+
                  '\nFIXTURE_JOURNAL='+shlex.quote(journal)+'\nFIXTURE_JOURNAL_CODE='+str(journal_code)+'\n')+script
        return self.execute(script)

    def execute(self, script, expected_code=0):
        if SEALED_ARCHIVE:
            spec=importlib.util.spec_from_file_location('sealed',REPO/'scripts/host/run-sealed-busybox.py')
            sealed=importlib.util.module_from_spec(spec);spec.loader.exec_module(sealed)
            blob=SEALED_ARCHIVE.read_bytes()
            with tempfile.TemporaryDirectory(prefix='rog5-startup-sealed-') as temp:
                root=Path(temp)
                sealed.extract(sealed.ARCHIVE.entries(gzip.decompress(blob)),root)
                (root/'rog5-qemu').touch()
                # Post-handover has /dev/null. Supply private pseudo-devices,
                # never host block devices, for exact redirection semantics.
                result=subprocess.run(['bwrap','--unshare-all','--die-with-parent','--new-session',
                    '--uid','0','--gid','0','--ro-bind',str(root),'/', '--dev','/dev',
                    '--ro-bind','/usr/bin/qemu-aarch64-static','/rog5-qemu','--clearenv',
                    '--setenv','PATH','/bin:/sbin:/usr/bin:/usr/sbin','--setenv','LC_ALL','C',
                    '/rog5-qemu','/bin/busybox','sh','-c',script],capture_output=True,timeout=10)
            print('sealed_archive_sha256='+hashlib.sha256(blob).hexdigest())
        else:
            result = subprocess.run(['sh', '-c', script], capture_output=True, timeout=3)
        self.assertEqual(result.returncode, expected_code, result.stderr)
        return result.stdout

    def test_real_systemctl_fields_and_missing_optional_observation(self):
        for status, observation, active in (
            ('LoadState=loaded\nActiveState=active\nSubState=exited\nResult=success\nExecMainStatus=0', 'present', 'active'),
            ('LoadState=loaded\nActiveState=failed\nSubState=failed\nResult=exit-code\nExecMainStatus=1', 'present', 'failed'),
            ('LoadState=not-found\nActiveState=inactive\nSubState=dead', 'absent', 'unknown'),
            ('unexpected output', 'error', 'unknown')):
            with self.subTest(status=status):
                record = M.parse_startup_observation(self.produce(status), RELEASE)
                self.assertEqual(record['observation'], observation)
                self.assertEqual(record['active'], active)
        self.assertEqual(M.parse_startup_observation(self.produce('', code=1), RELEASE)['observation'], 'error')

    def test_failure_text_is_bounded_and_unrelated_logs_not_exported(self):
        status='LoadState=loaded\nActiveState=failed\nSubState=failed\nResult=exit-code\nExecMainStatus=1'
        payload=self.produce(status, 'unrelated private material\nrog5-persistent-state: FAIL start contract failed\nrog5-p2-attest: FAIL other-unit\n')
        record=M.parse_startup_observation(payload, RELEASE)
        self.assertNotIn(b'private material', bytes.fromhex(record['failure_hex']))
        self.assertIn(b'start contract failed', bytes.fromhex(record['failure_hex']))
        self.assertNotIn(b'other-unit', bytes.fromhex(record['failure_hex']))
        self.assertLessEqual(len(payload),512)
        record=M.parse_startup_observation(self.produce(status,journal_code=1),RELEASE)
        self.assertEqual(record['journal'],'error')
        self.assertEqual(record['failure_hex'],'none')

    def test_unframed_wrong_release_and_oversized_records_rejected(self):
        payload=self.produce('LoadState=not-found')
        for bad in (payload+b'x', payload.replace(RELEASE.encode(),b'wrong'), payload.replace(b'unit=state',b'unit=arbitrary'), b'x'*513):
            with self.subTest(bad=bad[:40]), self.assertRaises(ValueError):
                M.parse_startup_observation(bad, RELEASE)

    def test_receiver_binds_observer_to_stage_boot_without_accepting_ssh(self):
        payload=self.produce('LoadState=not-found')
        events=[]
        with M.Receiver(RELEASE,events.append,host='127.0.0.1',port=0,peer='127.0.0.1') as receiver:
            receiver.transport('target',None)
            receiver.record(payload,'127.0.0.1')
            self.assertEqual(events[-1]['event'],'startup-observation')
            self.assertFalse(events[-1]['authenticated'])
            self.assertIsNone(receiver.last)  # observation is never a stage/SSH PASS
            wrong=payload.replace(BOOT.encode(),b'87654321-4321-4abc-8def-1234567890ab')
            receiver.record(wrong,'127.0.0.1')
            self.assertTrue(receiver.failed)


if __name__ == '__main__':
    if len(sys.argv)>2 and sys.argv[1]=='--sealed-archive':
        SEALED_ARCHIVE=Path(sys.argv[2]).resolve(strict=True)
        del sys.argv[1:3]
    unittest.main(verbosity=2)
