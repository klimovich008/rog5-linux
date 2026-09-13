#!/usr/bin/env python3
"""Exercise real guest FIFO/launcher cleanup with a prebuilt host Rust writer."""
import argparse
import os
from pathlib import Path
import shlex
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
WRITER = None

class Evidence(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='rog5-evidence-')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.prefix = ('source '+shlex.quote(str(ROOT/'tools/qemu-virtio-drm/launcher-apps.sh'))+'; '
                       'source '+shlex.quote(str(ROOT/'tools/qemu-virtio-drm/launcher-evidence.sh'))+'; '
                       'launcher_guest_guard() { :; }; ')

    def run_channel(self, actions):
        sink = self.root/'sink'; os.mkfifo(sink, 0o600)
        output = self.root/'events'
        with output.open('wb') as dst:
            reader = subprocess.Popen(['cat', str(sink)], stdout=dst)
            try:
                command = (self.prefix+'launcher_evidence_prepare '+shlex.quote(str(self.root/'channel'))+' '+
                           shlex.quote(str(sink))+' '+shlex.quote(str(WRITER))+'; '+actions+
                           '; launcher_evidence_finish')
                run = subprocess.run(['bash', '-euc', command], capture_output=True, timeout=10)
                reader.wait(timeout=3)
            finally:
                if reader.poll() is None: reader.kill(); reader.wait()
        self.assertLessEqual(output.stat().st_size, 3*1024*1024)
        return run, output.read_bytes()

    def test_concurrent_complete_records_and_unrelated_partial_console(self):
        writer=shlex.quote(str(WRITER)); fifo=shlex.quote(str(self.root/'channel/events'))
        actions=("printf 'flutter[partial'; "
                 f"(for i in {{1..100}}; do printf 'event-%s\\n' \"$i\"; done | {writer} prefix EDITOR_WAYLAND >{fifo}) & a=$!; "
                 f"(for i in {{1..100}}; do printf 'event-%s\\n' \"$i\"; done | {writer} prefix FOOT_WAYLAND >{fifo}) & b=$!; "
                 'wait "$a"; wait "$b"; printf \'rest]\\n\'')
        run, data=self.run_channel(actions)
        self.assertEqual(run.returncode,0,run.stderr)
        self.assertEqual(run.stdout,b'flutter[partialrest]\n')
        self.assertEqual(sorted(data.splitlines()),sorted(
            f'{app} event-{i}'.encode() for app in ('EDITOR_WAYLAND','FOOT_WAYLAND') for i in range(1,101)))

    def test_native_terminal_is_in_channel_before_later_exit_record(self):
        writer=shlex.quote(str(WRITER)); fifo=shlex.quote(str(self.root/'channel/events'))
        marker='independently clocked Flutter KMS session complete'
        actions=(f"printf 'native prefix\\n{marker} raster_frames=5\\n' | {writer} forward 3>{fifo}; "
                 f"{writer} record 'OBSERVE launcher app=foot exit=0' >{fifo}")
        run,data=self.run_channel(actions)
        self.assertEqual(run.returncode,0,run.stderr)
        self.assertEqual(data.splitlines(),[marker.encode(),b'OBSERVE launcher app=foot exit=0'])
        self.assertIn(b'raster_frames=5',run.stdout)

    def test_missing_writer_does_not_create_state(self):
        state=self.root/'absent'
        p=subprocess.run(['bash','-c',self.prefix+f'launcher_evidence_prepare {state} /dev/null /missing'],capture_output=True,timeout=3)
        self.assertNotEqual(p.returncode,0); self.assertFalse(state.exists())

    def test_failed_sink_makes_drain_fail_without_hanging(self):
        state=self.root/'channel'; writer=shlex.quote(str(WRITER))
        command=self.prefix+f'launcher_evidence_prepare {state} /dev/full {writer}; {writer} record hello >{state}/events; launcher_evidence_finish'
        run=subprocess.run(['bash','-euc',command],capture_output=True,timeout=3)
        self.assertNotEqual(run.returncode,0)
        self.assertIn(b'FAIL launcher evidence drain',run.stderr)

    def test_real_supervisor_preserves_failure_with_atomic_writer(self):
        state=self.root/'apps'; (state/'data/applications').mkdir(parents=True)
        bindir=self.root/'bin';bindir.mkdir()
        app=bindir/'foot';app.write_text('#!/usr/bin/env bash\necho hello\nexit 42\n');app.chmod(0o700)
        writer=shlex.quote(str(WRITER)); fifo=shlex.quote(str(self.root/'channel/events'))
        actions=f'export WAYLAND_DISPLAY=wayland-fixture; status=0; launcher_app_run foot {state} {bindir} {fifo} {writer} || status=$?; [[ $status == 42 ]]'
        run,data=self.run_channel(actions)
        self.assertEqual(run.returncode,0,run.stderr)
        self.assertIn(b'FOOT_WAYLAND hello\n',data)
        self.assertIn(b'OBSERVE launcher app=foot exit=42\n',data)
        self.assertEqual((state/'foot/exit-status').read_text(),'42\n')
        self.assertTrue((state/'foot/finished').exists())

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--writer',required=True,type=Path)
    args,rest=parser.parse_known_args();WRITER=args.writer.resolve(strict=True)
    unittest.main(argv=[__file__,*rest])
