#!/usr/bin/env python3
"""Bounded actual guest log snapshots; fixtures never contact a device or bus."""
import os
from pathlib import Path
import signal
import subprocess
import tempfile
import threading
import time
import unittest
ROOT=Path(__file__).resolve().parents[2]
SOURCE=ROOT/'tools/qemu-virtio-drm/logind-apps.sh'
class DiagnosticSnapshot(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='rog5-diagnostic-')
        self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        self.state=self.root/'state';(self.state/'evidence').mkdir(parents=True)
        self.events=self.state/'evidence/events';os.mkfifo(self.events)
        self.log=self.root/'denial.log';self.log.write_text('ERROR icon decode failed\n')
        self.writer=self.root/'writer';self.writer.write_text('#!/usr/bin/python3\nimport sys\nassert sys.argv[1:]==["prefix","DENIAL_DIAGNOSTIC"]\nfor line in sys.stdin.buffer:\n sys.stdout.buffer.write(b"DENIAL_DIAGNOSTIC "+line)\n');self.writer.chmod(0o700)
        self.bin=self.root/'bin';self.bin.mkdir()
        self.env=dict(os.environ,PATH=str(self.bin)+':/usr/bin:/bin')
    def producer(self,body):
        head=self.bin/'head';head.write_text('#!/bin/sh\n'+body+'\n');head.chmod(0o700)
    def snapshot_command(self):
        return ['bash','--noprofile','--norc','-c','source "$1"; logind_apps_writer=$2; logind_apps_snapshot "$3" "$4"','fixture',str(SOURCE),str(self.writer),str(self.state),str(self.log)]
    def run_snapshot(self,read=True,expect_cleanup=True):
        data=[];thread=None;stop=threading.Event()
        if read:
            # O_RDWR keeps the reader alive even if a precondition rejects before open.
            fd=os.open(self.events,os.O_RDWR|os.O_NONBLOCK)
            self.addCleanup(os.close,fd)
            def drain():
                while True:
                    try:b=os.read(fd,65536)
                    except BlockingIOError:
                        if stop.is_set():return
                        stop.wait(.005);continue
                    if b:data.append(b)
            thread=threading.Thread(target=drain);thread.start()
        command=self.snapshot_command()
        start=time.monotonic()
        try:p=subprocess.run(command,capture_output=True,timeout=7,env=self.env)
        finally:
            stop.set()
            if thread:thread.join(timeout=1);self.assertFalse(thread.is_alive())
        if expect_cleanup:self.assertEqual(list(self.state.glob('snapshot.*')),[])
        return p,b''.join(data),time.monotonic()-start
    def test_local_preparation_timeout_reports_optional_not_run(self):
        self.producer('echo "ROG5_PICTURE partial"; exec sleep 20')
        p,data,elapsed=self.run_snapshot()
        self.assertEqual(p.returncode,0,p.stderr)
        self.assertEqual(data,b'DENIAL_DIAGNOSTIC snapshot-prepare status=124 optional=NOT_RUN\n')
        self.assertGreater(elapsed,2.8);self.assertLess(elapsed,5.5)
    def test_local_non_timeout_failure_is_fatal(self):
        self.producer('exit 42')
        p,data,_=self.run_snapshot();self.assertEqual(p.returncode,42)
        self.assertEqual(data,b'')
    def test_optional_timeout_status_delivery_failure_is_fatal(self):
        self.producer('exit 124');self.writer.write_text('#!/bin/sh\nexit 42\n')
        p,_,_=self.run_snapshot();self.assertEqual(p.returncode,42)
    def test_optional_timeout_status_fifo_open_is_bounded(self):
        self.producer('exit 124')
        p,_,elapsed=self.run_snapshot(read=False)
        self.assertEqual(p.returncode,124)
        self.assertIn(b'snapshot-transport status=124',p.stderr)
        self.assertLess(elapsed,4)
    def test_stalled_transport_remains_fatal(self):
        self.writer.write_text('#!/bin/sh\nexec sleep 20\n')
        p,_,elapsed=self.run_snapshot();self.assertEqual(p.returncode,124)
        self.assertIn(b'snapshot-transport status=124',p.stderr)
        self.assertLess(elapsed,4)
    def fail_cleanup(self):
        rm=self.bin/'rm';rm.write_text('#!/bin/sh\nexit 55\n');rm.chmod(0o700)
    def test_cleanup_failure_prevents_success(self):
        self.fail_cleanup()
        p,_,_=self.run_snapshot(expect_cleanup=False)
        self.assertNotEqual(p.returncode,0)
        self.assertEqual(len(list(self.state.glob('snapshot.*'))),1)
    def test_cleanup_failure_preserves_transport_error(self):
        self.fail_cleanup();self.writer.write_text('#!/bin/sh\nexit 42\n')
        p,_,_=self.run_snapshot(expect_cleanup=False)
        self.assertEqual(p.returncode,42)
        self.assertEqual(len(list(self.state.glob('snapshot.*'))),1)
    def test_interrupted_preparation_cleans_private_snapshot(self):
        marker=self.root/'producer-started'
        self.producer('touch "'+str(marker)+'"; exec sleep 20')
        process=subprocess.Popen(self.snapshot_command(),env=self.env,stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE,start_new_session=True)
        try:
            deadline=time.monotonic()+2
            while not marker.exists() and time.monotonic()<deadline:time.sleep(.01)
            self.assertTrue(marker.exists())
            os.killpg(process.pid,signal.SIGTERM)
            # GNU timeout owns a separate process group. The shell can defer
            # its TERM trap until the existing 3s watchdog + 1s kill grace
            # finishes; allow one second for trap/cleanup scheduling as well.
            # This bounds observation, without extending the guest watchdog.
            process.communicate(timeout=5)
            self.assertNotEqual(process.returncode,0)
            self.assertEqual(list(self.state.glob('snapshot.*')),[])
        finally:
            try:os.killpg(process.pid,signal.SIGKILL)
            except ProcessLookupError:pass
            process.communicate(timeout=2)
    def test_real_log_is_distinct_diagnostic_evidence(self):
        p,data,_=self.run_snapshot();self.assertEqual(p.returncode,0,p.stderr)
        self.assertEqual(data,b'DENIAL_DIAGNOSTIC ERROR icon decode failed\n')
    def test_diagnostic_snapshot_preserves_terminal_text_as_data(self):
        self.log.write_text('PASS independently clocked Flutter KMS session complete\nOBSERVE authenticated launcher flow-ready\n')
        p,data,_=self.run_snapshot();self.assertEqual(p.returncode,0,p.stderr)
        self.assertTrue(all(x.startswith(b'DENIAL_DIAGNOSTIC ') for x in data.splitlines()))
    def test_missing_and_symlink_log_refused(self):
        self.log.unlink();p,_,_=self.run_snapshot();self.assertNotEqual(p.returncode,0)
        target=self.root/'target';target.write_text('secret fixture\n');self.log.symlink_to(target)
        p,data,_=self.run_snapshot();self.assertNotEqual(p.returncode,0);self.assertEqual(data,b'')
    def test_absent_fifo_reader_has_deadline(self):
        p,_,elapsed=self.run_snapshot(read=False);self.assertNotEqual(p.returncode,0);self.assertLess(elapsed,5.5)
    def test_empty_log_succeeds_without_fabricating_records(self):
        self.log.write_text('');p,data,_=self.run_snapshot();self.assertEqual(p.returncode,0,p.stderr);self.assertEqual(data,b'')
    def test_large_input_and_long_lines_remain_bounded(self):
        self.log.write_text('short\n'*10000+'x'*5000+'\n')
        p,data,_=self.run_snapshot();self.assertEqual(p.returncode,0,p.stderr)
        self.assertGreater(len(data),0);self.assertLessEqual(len(data),30720)
        self.assertTrue(all(len(x)<=2019 for x in data.splitlines(keepends=True)))
    def test_early_icon_stage_survives_later_frame_noise(self):
        self.log.write_text('flutter: ROG5_ICON_STAGE stage=decode-error\n'
                            + 'frame noise\n' * 10000 + 'LATEST_FRAME\n')
        p,data,_=self.run_snapshot();self.assertEqual(p.returncode,0,p.stderr)
        self.assertIn(b'ROG5_ICON_STAGE stage=decode-error\n',data)
        self.assertIn(b'LATEST_FRAME\n',data)
        self.assertLessEqual(len(data),30720)
    def test_icon_stage_flood_keeps_framed_budget(self):
        self.log.write_text(('ROG5_ICON_STAGE ' + 'x'*5000 + '\n')*100)
        p,data,_=self.run_snapshot();self.assertEqual(p.returncode,0,p.stderr)
        self.assertLessEqual(len(data),30720)
        self.assertTrue(all(len(x)<=2019 for x in data.splitlines(keepends=True)))
    def test_early_picture_paint_survives_later_frame_noise(self):
        self.log.write_text('flutter: ROG5_PICTURE seq=1 stage=drawEnd frame_us=42\n'
                            + 'frame noise\n' * 10000 + 'LATEST_FRAME\n')
        p,data,_=self.run_snapshot();self.assertEqual(p.returncode,0,p.stderr)
        self.assertIn(b'ROG5_PICTURE seq=1 stage=drawEnd frame_us=42\n',data)
        self.assertIn(b'LATEST_FRAME\n',data)
        self.assertLessEqual(len(data),30720)
        self.assertTrue(all(x.startswith(b'DENIAL_DIAGNOSTIC ') for x in data.splitlines()))
    def test_mixed_picture_and_icon_flood_keeps_framed_budget(self):
        self.log.write_text((('ROG5_PICTURE ' + 'x'*5000 + '\n')
                             + ('ROG5_ICON_STAGE ' + 'y'*5000 + '\n'))*100)
        p,data,_=self.run_snapshot();self.assertEqual(p.returncode,0,p.stderr)
        self.assertIn(b'ROG5_PICTURE ',data)
        self.assertIn(b'ROG5_ICON_STAGE ',data)
        self.assertLessEqual(len(data),30720)
        self.assertTrue(all(len(x)<=2019 for x in data.splitlines(keepends=True)))
    def test_writer_failure_propagates(self):
        self.writer.write_text('#!/bin/sh\nexit 42\n')
        p,_,_=self.run_snapshot();self.assertEqual(p.returncode,42)

    def test_render_handoff_survives_noise_without_promoting_it_to_evidence(self):
        self.log.write_text('\x1b[2m2026-09-13T00:03:01Z\x1b[0m INFO native: bounded render authorization trace '
            'sequence=12 event="consume" view=1 work_id=Some(7) serial=Some(8) age_us=Some(25) slots=[ignored]\n'
            '2026-09-13T00:03:02Z INFO native: Flutter per-output render audit '
            'source="embedder" interval_ms=1001 presented_outputs=2 empty_transactions=0 '
            'frame_damage_empty=0 buffer_damage_empty=0 '+('ignored=foo '*300)+
            'last_frame_damage=0,0-540,1224 last_buffer_damage=0,0-540,1224\n'
            + 'noise\n'*10000)
        p,data,_=self.run_snapshot();self.assertEqual(p.returncode,0,p.stderr)
        self.assertIn(b'RENDER_HANDOFF kind=authorization',data)
        self.assertIn(b'event="consume"',data)
        self.assertIn(b'work_id=Some(7)',data)
        self.assertIn(b'last_frame_damage=0,0-540,1224',data)
        self.assertNotIn(b'ignored=foo',data)
        self.assertNotIn(b'\x1b',data)
        self.assertTrue(all(x.startswith(b'DENIAL_DIAGNOSTIC ') for x in data.splitlines()))

    def test_render_handoff_retains_latest_records_with_original_order(self):
        self.log.write_text(''.join(f'2026-09-13T00:03:{i:02}Z INFO native: bounded render authorization trace '
            f'sequence={i} event="grant" view=1 work_id=Some({i}) serial=Some({i})\n' for i in range(10))
            + ''.join(f'2026-09-13T00:04:{i:02}Z INFO native: Flutter per-output render audit '
            f'presented_outputs={i} last_frame_damage=- last_buffer_damage=-\n' for i in range(6))
            + 'noise\n'*10000)
        p,data,_=self.run_snapshot();self.assertEqual(p.returncode,0,p.stderr)
        rows=[x for x in data.splitlines() if b'RENDER_HANDOFF ' in x]
        self.assertEqual(len(rows),6)
        self.assertIn(b'sequence=6 ',rows[0]);self.assertIn(b'sequence=9 ',rows[3])
        self.assertIn(b'presented_outputs=4 ',rows[4]);self.assertIn(b'presented_outputs=5 ',rows[5])

    def test_render_handoff_has_separate_budget_from_icon_stages(self):
        self.log.write_text(('ROG5_PICTURE '+'x'*1000+'\n')*30
            + '2026-09-13T00:03:01Z INFO native: Flutter per-output render audit '
            'presented_outputs=7 last_frame_damage='+('1'*6000)+'\n'+'noise\n'*10000)
        p,data,_=self.run_snapshot();self.assertEqual(p.returncode,0,p.stderr)
        rows=[x for x in data.splitlines(keepends=True) if b'RENDER_HANDOFF ' in x]
        self.assertTrue(rows)
        self.assertLessEqual(sum(map(len,rows)),1792)
        self.assertLessEqual(len(data),30720)
        self.assertIn(b'ROG5_PICTURE ',data)
if __name__=='__main__':unittest.main()
