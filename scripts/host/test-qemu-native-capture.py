#!/usr/bin/env python3
"""Exercise the actual bounded capture coordinator and lossless encoding."""
import importlib.util
import json
from pathlib import Path
import struct
import tempfile
import threading
import time
import unittest
import zlib

def module(name, filename):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(filename))
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result

CAP = module('native_capture', 'qemu-native-capture.py')
OBS = module('mobile_observer', 'qemu-mobile-observer.py')
PPM = b'P6\n540 1224\n255\n' + b'\xff\x12\x34' * (540*1224)

class CaptureTests(unittest.TestCase):
    def test_encoding_retains_every_pixel(self):
        png = CAP.ppm_to_png(PPM)
        at, compressed = 8, b''
        while at < len(png):
            size = struct.unpack('>I', png[at:at+4])[0]
            if png[at+4:at+8] == b'IDAT':
                compressed += png[at+8:at+8+size]
            at += 12+size
        raw = zlib.decompress(compressed)
        self.assertEqual(raw, (b'\0'+b'\xff\x12\x34'*540)*1224)

    def test_bad_dimensions_truncation_and_extra_pixels_refused(self):
        for data in (b'', PPM[:-1], PPM+b'0', PPM.replace(b'540 1224', b'541 1224')):
            with self.subTest(size=len(data)), self.assertRaises(ValueError):
                CAP.ppm_to_png(data)

    def exercise(self, directory, status=b'0\n', data=PPM, metadata=b'{"status":"PASS"}'):
        def vnc(sock, name, path):
            path.write_bytes(CAP.ppm_to_png(PPM))
        capture = CAP.NativeCapture(directory/'native', vnc, OBS.png_identity, timeout=.5)
        def worker():
            for _ in range(200):
                if (capture.directory/'initial.request').exists():
                    (capture.directory/'initial.ppm').write_bytes(data)
                    (capture.directory/'initial.json').write_bytes(metadata)
                    (capture.directory/'initial.done').write_bytes(status)
                    return
                time.sleep(.005)
        thread = threading.Thread(target=worker)
        thread.start()
        return capture, thread

    def test_request_capture_and_identity(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            capture, worker = self.exercise(root)
            try:
                capture(None, 'owned-vm', root/'00-editor-empty.png')
                self.assertEqual(len(capture.records), 1)
                record = capture.records[0]
                self.assertEqual(record['vnc']['sha256'], record['native']['sha256'])
                self.assertEqual((capture.directory/'initial.request').read_text(), 'initial\n')
                self.assertEqual(capture.directory.stat().st_mode & 0o777, 0o700)
            finally:
                worker.join(2)
            self.assertFalse(worker.is_alive())

    def test_failed_client_or_invalid_pixels_never_records_success(self):
        for status, data, metadata in ((b'1\n', PPM, b'{}'), (b'0\n', PPM[:-1], b'{}'),
                                       (b'0\n', PPM, b'x'*16385)):
            with self.subTest(status=status, size=len(data)), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                capture, worker = self.exercise(root, status, data, metadata)
                try:
                    with self.assertRaises(ValueError):
                        capture(None, 'owned-vm', root/'00-editor-empty.png')
                    self.assertEqual(capture.records, [])
                finally:
                    worker.join(2)

    def test_deadline_and_existing_output_refusal(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            capture = CAP.NativeCapture(root/'native', lambda *args: None, OBS.png_identity, timeout=.03)
            start = time.monotonic()
            with self.assertRaises(TimeoutError):
                capture(None, 'owned-vm', root/'00-editor-empty.png')
            self.assertLess(time.monotonic()-start, .5)
            with self.assertRaises(FileExistsError):
                capture(None, 'owned-vm', root/'00-editor-empty.png')
            with self.assertRaises(FileExistsError):
                CAP.NativeCapture(root/'native', None, None)

    def test_intermediate_capture_does_not_request_native(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            calls = []
            capture = CAP.NativeCapture(root/'native', lambda *args: calls.append(args), OBS.png_identity)
            capture(None, 'owned-vm', root/'02-editor-test.png')
            self.assertEqual(len(calls), 1)
            self.assertEqual(list(capture.directory.iterdir()), [])

    def test_symlink_directory_and_aggregate_limit(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            capture = CAP.NativeCapture(root/'native', None, None)
            bad = capture.directory/'bad'
            bad.symlink_to(root/'absent')
            with self.assertRaises(ValueError): capture.check_bound()
            bad.unlink(); bad.mkdir()
            with self.assertRaises(ValueError): capture.check_bound()
            bad.rmdir()
            with bad.open('wb') as stream: stream.truncate(8*1024*1024+1)
            with self.assertRaises(ValueError): capture.check_bound()

if __name__ == '__main__':
    unittest.main()
