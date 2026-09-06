#!/usr/bin/env python3
"""Real subprocess/pipe regressions; no SSH, phone, listener or storage payload."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import time
import unittest

SOURCE=Path(__file__).with_name('network-transfer-stream.py')
SPEC=importlib.util.spec_from_file_location('transfer',SOURCE)
M=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(M)
NONCE='a1'*32


class TransferTests(unittest.TestCase):
    def endpoint(self, action, size):
        return [sys.executable,'-I','-B',str(SOURCE),action,'--bytes',str(size),'--nonce',NONCE]

    def test_real_roundtrip_both_directions_and_no_payload_files(self):
        for direction,action in [('upload','receive'),('download','send')]:
            with self.subTest(direction=direction):
                result=M.transfer(self.endpoint(action,1048576),direction,NONCE,1048576,5)
                self.assertEqual(result['bytes'],1048576)
                self.assertEqual(result['sha256'],M.expected_digest(NONCE,1048576))
                self.assertFalse(result['s02_qualified'])
                self.assertEqual(result['returncode'],0)

    def test_nonce_and_offset_change_payload_and_partial_final_block(self):
        blocks=list(M.payload(NONCE,65536+17))
        self.assertEqual([len(b) for b in blocks],[65536,17])
        self.assertNotEqual(blocks[0][:17],blocks[1])
        self.assertNotEqual(M.expected_digest(NONCE,100),M.expected_digest('b2'*32,100))

    def test_truncated_extra_and_wrong_download_are_not_success(self):
        for code in ('pass','import sys;sys.stdout.buffer.write(b"x"*65)',
                     'import sys;sys.stdout.buffer.write(b"x"*64)'):
            with self.subTest(code=code),self.assertRaises(M.TransferError):
                M.transfer([sys.executable,'-I','-B','-c',code],'download',NONCE,64,2)

    def test_upload_receipt_rejects_wrong_hash_count_boolean_and_duplicates(self):
        good=dict(format='rog5-transfer-v1',bytes=64,sha256=M.expected_digest(NONCE,64))
        variants=[dict(good,bytes=63),dict(good,bytes=True),dict(good,sha256='0'*64),dict(good,extra=1)]
        frames=[json.dumps(v).encode() for v in variants]+[
            json.dumps(good).replace('"bytes": 64','"bytes": 64, "bytes": 64').encode()]
        for frame in frames:
            code='import sys;sys.stdin.buffer.read();sys.stdout.buffer.write('+repr(frame)+')'
            with self.subTest(frame=frame),self.assertRaises(M.TransferError):
                M.transfer([sys.executable,'-I','-B','-c',code],'upload',NONCE,64,2)

    def test_nonzero_exit_and_stderr_flood_refused(self):
        for code in ('import sys;sys.exit(3)', 'import sys;sys.stderr.write("x"*100000)'):
            with self.subTest(code=code),self.assertRaises(M.TransferError):
                M.transfer([sys.executable,'-I','-B','-c',code],'download',NONCE,64,2)

    def test_idle_and_blocked_writer_deadlines_stop_owned_processes(self):
        for direction in ('upload','download'):
            start=time.monotonic()
            with self.subTest(direction=direction),self.assertRaisesRegex(M.TransferError,'deadline'):
                M.transfer([sys.executable,'-I','-B','-c','import time;time.sleep(10)'],
                           direction,NONCE,1048576,.15)
            self.assertLess(time.monotonic()-start,1.5)

    def test_input_limits_fail_before_process_creation(self):
        from unittest.mock import patch
        for size,nonce,timeout,direction in [(0,NONCE,1,'upload'),(M.LIMIT+1,NONCE,1,'upload'),
                (True,NONCE,1,'upload'),(64,'bad',1,'upload'),(64,NONCE,float('nan'),'upload'),
                (64,NONCE,181,'upload'),(64,NONCE,1,'other')]:
            with self.subTest(size=size,nonce=nonce,timeout=timeout,direction=direction), \
                 patch.object(M.subprocess,'Popen') as start,self.assertRaises(ValueError):
                M.transfer(['unused'],direction,nonce,size,timeout)
            start.assert_not_called()

    def test_receiver_rejects_short_and_extra_input(self):
        for data in (b'x'*63,b'x'*64,b'x'*65):
            p=subprocess.run(self.endpoint('receive',64),input=data,capture_output=True,timeout=2)
            self.assertNotEqual(p.returncode,0)
            self.assertEqual(p.stdout,b'')

    def test_deadline_includes_exit_after_all_pipes_close(self):
        code='import os,time;os.close(1);os.close(2);time.sleep(10)'
        start=time.monotonic()
        with self.assertRaisesRegex(M.TransferError,'deadline'):
            M.transfer([sys.executable,'-I','-B','-c',code],'download',NONCE,64,.15)
        self.assertLess(time.monotonic()-start,1.5)

    def test_inherited_pipe_does_not_extend_deadline(self):
        code='import os,time;pid=os.fork();time.sleep(10) if pid==0 else None'
        start=time.monotonic()
        with self.assertRaisesRegex(M.TransferError,'deadline'):
            M.transfer([sys.executable,'-I','-B','-c',code],'download',NONCE,64,.15)
        self.assertLess(time.monotonic()-start,1.5)

    def test_oversized_upload_receipt_is_bounded(self):
        code='import sys;sys.stdin.buffer.read();sys.stdout.buffer.write(b"x"*100000)'
        with self.assertRaisesRegex(M.TransferError,'receipt limit'):
            M.transfer([sys.executable,'-I','-B','-c',code],'upload',NONCE,64,2)


if __name__=='__main__':unittest.main()
