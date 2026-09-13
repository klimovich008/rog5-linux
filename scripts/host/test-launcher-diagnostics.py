#!/usr/bin/env python3
"""Bounded actual guest log snapshots; fixtures never contact a device or bus."""
import os
from pathlib import Path
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
    def run_snapshot(self,read=True):
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
        command=['bash','--noprofile','--norc','-c','source "$1"; logind_apps_writer=$2; logind_apps_snapshot "$3" "$4"','fixture',str(SOURCE),str(self.writer),str(self.state),str(self.log)]
        start=time.monotonic()
        try:p=subprocess.run(command,capture_output=True,timeout=7)
        finally:
            stop.set()
            if thread:thread.join(timeout=1);self.assertFalse(thread.is_alive())
        return p,b''.join(data),time.monotonic()-start
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
