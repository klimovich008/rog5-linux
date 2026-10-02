#!/usr/bin/env python3
"""Exercise quoting, gesture validation and failure propagation without SSH."""
import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import shlex
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock

REPO = Path(__file__).resolve().parents[2]
# Prevent the existing CLI's eager address discovery during import. SSH is
# replaced before exercising any function below.
with mock.patch.dict(os.environ, {'ROG5_BENCH_ADDR': 'offline.invalid'}):
    spec = importlib.util.spec_from_file_location('bench_test', REPO / 'scripts/host/rog5-bench.py')
    BENCH = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(BENCH)


class Bench(unittest.TestCase):
    def run_main(self, argv, rc, status):
        with tempfile.TemporaryDirectory(prefix='rog5-bench-test.') as d:
            with mock.patch.object(BENCH, 'ROOT', Path(d)), mock.patch.object(BENCH, 'OUT', Path(d) / 'results'), \
                    mock.patch.object(BENCH, 'push'), mock.patch.object(sys, 'argv', ['bench', *argv]), \
                    mock.patch.object(BENCH.trial, 'ssh', return_value=SimpleNamespace(
                        returncode=rc, stdout=json.dumps({'status': status}).encode(), stderr=b'')) as ssh, \
                    contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                result = BENCH.main()
                command = ssh.call_args.args[1]
                files = list((Path(d) / 'results').glob('*.json'))
                self.assertEqual(len(files), 1)
                self.assertEqual(json.loads(files[0].read_text())['status'], status)
                return result, command

    def test_labels_preserve_shell_argument_boundaries(self):
        label = 'USB unplugged; $(id) `touch bad`'
        rc, command = self.run_main(['power', '--label', label], 0, 'PASS')
        self.assertEqual(rc, 0)
        self.assertEqual(shlex.split(command)[-2:], ['--label', label])

    def test_remote_failure_is_never_successful_json(self):
        for rc, status, expected in [(1, 'PASS', 1), (0, 'FAIL', 1), (0, 'PASS', 0)]:
            self.assertEqual(self.run_main(['gpu'], rc, status)[0], expected)

    def test_gestures_reject_code_nonfinite_and_out_of_range_values(self):
        for values in [['1; __import__("os").system("id")', '2'], ['nan', '2'],
                       ['inf', '2'], ['-1', '2'], ['10001', '2'], ['1']]:
            with self.subTest(values=values), self.assertRaises(SystemExit):
                BENCH.numbers(values, 2, 2, 'tap')
        self.assertEqual(BENCH.numbers(['1', '2.5'], 2, 2, 'tap'), '1.0,2.5')


if __name__ == '__main__':
    unittest.main()
