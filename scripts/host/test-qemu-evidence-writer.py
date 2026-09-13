#!/usr/bin/env python3
"""Compile and exercise the production VM evidence writer with real Linux pipes.

The concurrent FIFO and strace checks prove framing on the tested host binary;
ARM64 compilation/execution and the actual virtio channel remain separate gates.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import select
import shlex
import shutil
import subprocess
import tempfile
import threading
import time
import unittest

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / 'tools/qemu-virtio-drm/evidence-writer.rs'
TERMINAL = b'independently clocked Flutter KMS session complete'
OUTPUT = None


class EvidenceWriter(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.binary = OUTPUT / 'evidence-writer'

    def run_writer(self, *args, data=b''):
        return subprocess.run([str(self.binary), *args], input=data,
                              capture_output=True, timeout=5)

    def forward(self, data):
        read, write = os.pipe()
        try:
            run = subprocess.run(['bash', '-c', 'exec "$1" forward 3>&"$2"',
                                  '_', str(self.binary), str(write)], pass_fds=(write,),
                                 input=data, capture_output=True, timeout=5)
        finally:
            os.close(write)
        with os.fdopen(read, 'rb') as stream:
            evidence = stream.read(8192)
        return run, evidence

    def test_client_prefix_frames_partial_input_as_complete_records(self):
        result = self.run_writer('prefix', 'FOOT_WAYLAND', data=b'first\nsecond\n')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, b'FOOT_WAYLAND first\nFOOT_WAYLAND second\n')

    def test_maximum_record_is_4096_bytes(self):
        data = b'x' * (4096 - len(b'EDITOR_WAYLAND ') - 1) + b'\n'
        run = self.run_writer('prefix', 'EDITOR_WAYLAND', data=data)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(len(run.stdout), 4096)

    def test_oversized_line_rejects_without_unbounded_allocation_and_drains(self):
        run = self.run_writer('prefix', 'FOOT_WAYLAND', data=b'x' * (4 * 1024 * 1024))
        self.assertNotEqual(run.returncode, 0)
        self.assertEqual(run.stdout, b'FAIL launcher client evidence rejected\n')
        self.assertIn(b'line limit', run.stderr)

    def test_aggregate_cap_rejects_whole_record_and_drains(self):
        run = self.run_writer('prefix', 'FOOT_WAYLAND', data=(b'x' * 1000 + b'\n') * 2000)
        self.assertNotEqual(run.returncode, 0)
        self.assertLessEqual(len(run.stdout), 1024 * 1024 + 64)
        self.assertTrue(run.stdout.endswith(b'FAIL launcher client evidence rejected\n'))
        self.assertIn(b'log limit', run.stderr)
        self.assertTrue(all(line.startswith((b'FOOT_WAYLAND ', b'FAIL launcher '))
                            for line in run.stdout.splitlines()))

    def test_unterminated_client_line_is_not_manufactured(self):
        run = self.run_writer('prefix', 'FOOT_WAYLAND', data=b'good\nincomplete')
        self.assertNotEqual(run.returncode, 0)
        self.assertEqual(run.stdout, b'FOOT_WAYLAND good\nFAIL launcher client evidence rejected\n')

    def test_record_rejects_newlines_nul_empty_and_overflow(self):
        for text in ('', 'forged\nowner', 'forged\rline', 'x' * 4096):
            with self.subTest(text=text[:20]):
                run = self.run_writer('record', text)
                self.assertNotEqual(run.returncode, 0)
                self.assertEqual(run.stdout, b'')
        # NUL cannot be passed through argv; Rust also rejects it defensively.
        run = self.run_writer('record', 'OBSERVE launcher app=foot owner=3 start=9')
        self.assertEqual(run.returncode, 0)
        self.assertEqual(run.stdout, b'OBSERVE launcher app=foot owner=3 start=9\n')

    def test_unknown_mode_prefix_and_extra_arguments_fail(self):
        for args in [('other',), ('prefix', 'NATIVE'), ('record', 'a', 'b'), ('forward', 'extra')]:
            self.assertNotEqual(self.run_writer(*args).returncode, 0)

    def test_regular_file_cannot_masquerade_as_atomic_fifo(self):
        with tempfile.TemporaryFile() as stream:
            run = subprocess.run([str(self.binary), 'record', 'hello'],
                                 stdout=stream, stderr=subprocess.PIPE, timeout=5)
        self.assertNotEqual(run.returncode, 0)
        self.assertIn(b'must be a FIFO', run.stderr)

    def test_forward_requires_inherited_evidence_descriptor(self):
        run = self.run_writer('forward', data=TERMINAL+b'\n')
        self.assertNotEqual(run.returncode, 0)
        self.assertEqual(run.stdout, b'')

    def test_forward_preserves_bytes_and_emits_only_terminal(self):
        data = b'partial\x00native\r\nnoise\nINFO ' + TERMINAL + b' raster_frames=3\ntrailing partial'
        run, evidence = self.forward(data)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, data)
        self.assertEqual(evidence, TERMINAL + b'\n')

    def test_forward_missing_duplicate_and_unterminated_terminal_fail(self):
        for data in [b'ordinary\n', TERMINAL, TERMINAL+b'\n'+TERMINAL+b'\n',
                     TERMINAL+b' and '+TERMINAL+b'\n']:
            with self.subTest(data=data):
                run, evidence = self.forward(data)
                self.assertNotEqual(run.returncode, 0)
                self.assertLessEqual(evidence.count(TERMINAL), 1)
                self.assertTrue(evidence.endswith(b'FAIL launcher native evidence rejected\n'))

    def test_forward_line_and_total_bounds_drain(self):
        for data in [b'x' * 20000, (b'x' * 16000 + b'\n') * 530]:
            run, evidence = self.forward(data)
            self.assertNotEqual(run.returncode, 0)
            self.assertLessEqual(len(run.stdout), 8 * 1024 * 1024)
            self.assertEqual(evidence, b'FAIL launcher native evidence rejected\n')

    def test_terminal_evidence_write_precedes_terminal_stdout(self):
        trace = OUTPUT / 'forward.strace'
        read, write = os.pipe()
        try:
            run = subprocess.run(['bash', '-c', 'exec strace -e trace=write -s 256 -o "$1" "$2" forward 3>&"$3"',
                                  '_', str(trace), str(self.binary), str(write)],
                                 pass_fds=(write,), input=TERMINAL+b' count=4\n',
                                 capture_output=True, timeout=5)
        finally:
            os.close(write)
            os.close(read)
        self.assertEqual(run.returncode, 0, run.stderr)
        lines = [line for line in trace.read_text().splitlines() if line.startswith('write(')]
        self.assertEqual(len(lines), 2, lines)
        self.assertIn('complete\\n"', lines[0])
        self.assertIn('complete count=4\\n"', lines[1])

    def test_pipefail_preserves_native_failure_even_after_terminal(self):
        read, write = os.pipe()
        try:
            run = subprocess.run(['bash', '-c',
                                  'set -o pipefail; (printf "%s\\n" "$1"; exit 42) | "$2" forward 3>&"$3"',
                                  '_', TERMINAL.decode(), str(self.binary), str(write)],
                                 pass_fds=(write,), capture_output=True, timeout=5)
        finally:
            os.close(write)
            os.close(read)
        self.assertEqual(run.returncode, 42, run.stderr)

    def test_prefix_uses_exactly_one_syscall_per_record(self):
        trace = OUTPUT / 'prefix.strace'
        run = subprocess.run(['strace', '-e', 'trace=write', '-s', '8192', '-o', str(trace),
                              str(self.binary), 'prefix', 'FOOT_WAYLAND'],
                             input=b'first\nsecond\n', capture_output=True, timeout=5)
        self.assertEqual(run.returncode, 0, run.stderr)
        writes = [line for line in trace.read_text().splitlines() if line.startswith('write(')]
        self.assertEqual(len(writes), 2, writes)
        for index, name in enumerate(('first', 'second')):
            length = len('FOOT_WAYLAND '+name+'\n')
            self.assertRegex(writes[index], rf'^write\(\d+, "FOOT_WAYLAND {name}\\n", {length}\)\s+= {length}$')

    def test_concurrent_fifo_writers_preserve_maximum_records(self):
        with tempfile.TemporaryDirectory(dir=OUTPUT) as directory:
            fifo = Path(directory) / 'aggregate'
            os.mkfifo(fifo, 0o600)
            handle = os.open(fifo, os.O_RDWR)
            collected = bytearray()
            stopped = threading.Event()
            def collect():
                while True:
                    ready, _, _ = select.select([handle], [], [], .02)
                    if ready:
                        collected.extend(os.read(handle, 65536))
                    elif stopped.is_set():
                        return
            reader = threading.Thread(target=collect, daemon=True)
            reader.start()
            processes = []
            expected = []
            try:
                for index in range(4):
                    name = ('EDITOR_WAYLAND', 'FOOT_WAYLAND')[index % 2]
                    payloads = []
                    for number in range(150):
                        start = f'{index}:{number}:'.encode()
                        content = start + b'x' * (4096 - len(name) - 2 - len(start)) + b'\n'
                        payloads.append(content)
                        expected.append(name.encode()+b' '+content)
                    input_file = Path(directory) / str(index)
                    input_file.write_bytes(b''.join(payloads))
                    with input_file.open('rb') as stream:
                        processes.append(subprocess.Popen([str(self.binary), 'prefix', name],
                                                          stdin=stream, stdout=handle, stderr=subprocess.PIPE))
                for process in processes:
                    _, stderr = process.communicate(timeout=5)
                    self.assertEqual(process.returncode, 0, stderr)
            finally:
                for process in processes:
                    if process.poll() is None:
                        process.kill()
                        process.wait(timeout=2)
                stopped.set()
                reader.join(timeout=2)
                os.close(handle)
            self.assertFalse(reader.is_alive())
            actual = collected.splitlines(keepends=True)
            self.assertEqual(len(actual), 600)
            self.assertEqual(sorted(actual), sorted(expected))


def main():
    global OUTPUT
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    compiler = shutil.which(os.environ.get('RUSTC', 'rustc'))
    if not compiler or not shutil.which('strace'):
        parser.error('BLOCKED: rustc and strace are required')
    OUTPUT = args.output.absolute()
    OUTPUT.mkdir(parents=True, exist_ok=False)
    environment = dict(os.environ, TMPDIR=str(OUTPUT))
    result = {'source_sha256': hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
              'scope': __doc__, 'status': 'FAIL', 'runs': [], 'vm': 'NOT RUN', 'phone': 'NOT RUN'}
    for name, flags in [('evidence-writer', []), ('unit', ['--test'])]:
        command = [compiler, '--edition=2024', '-Dwarnings', *flags, str(SOURCE), '-o', str(OUTPUT/name)]
        started = time.monotonic()
        build = subprocess.run(command, capture_output=True, text=True, timeout=45, env=environment)
        (OUTPUT/(name+'-build.log')).write_text(build.stdout+build.stderr)
        result['runs'].append({'command': command, 'duration_seconds': time.monotonic()-started,
                               'exit_status': build.returncode})
        if build.returncode:
            (OUTPUT/'result.json').write_text(json.dumps(result, indent=2)+'\n')
            print(build.stderr)
            return 1
    started = time.monotonic()
    unit = subprocess.run([str(OUTPUT/'unit'), '--test-threads=1'], capture_output=True, text=True, timeout=10)
    (OUTPUT/'unit.log').write_text(unit.stdout+unit.stderr)
    result['unit'] = {'exit_status': unit.returncode, 'duration_seconds': time.monotonic()-started}
    started = time.monotonic()
    with (OUTPUT/'host-tests.log').open('w') as stream:
        tests = unittest.TextTestRunner(stream=stream, verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(EvidenceWriter))
    result['host'] = {'duration_seconds': time.monotonic()-started, 'run': tests.testsRun,
                      'failures': len(tests.failures), 'errors': len(tests.errors), 'skipped': len(tests.skipped)}
    result['binary_sha256'] = hashlib.sha256((OUTPUT/'evidence-writer').read_bytes()).hexdigest()
    result['status'] = 'PASS' if unit.returncode == 0 and tests.wasSuccessful() else 'FAIL'
    (OUTPUT/'result.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result, indent=2))
    return 0 if result['status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
