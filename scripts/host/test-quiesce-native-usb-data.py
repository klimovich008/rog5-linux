#!/usr/bin/env python3
"""Use ordinary fixture files only; never access real USB or require root."""
import importlib.util
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

R = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('quiesce', R/'scripts/host/quiesce-native-usb-data.py')
module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)


class QuiesceTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name)/'device'; self.path.mkdir()
        for name, value in dict(module.IDENTITY, devnum='42', authorized='1').items():
            (self.path/name).write_text(value+'\n')
        self.usb = patch.object(module, 'USB', self.path); self.usb.start(); self.addCleanup(self.usb.stop)
        # Fixture owner stands in for root; production still requires uid0.
        original = module.os.stat
        def metadata(path, **kwargs):
            result = original(path, **kwargs)
            if Path(path) == self.path:
                values = list(result); values[4] = 0; return os.stat_result(values)
            return result
        self.metadata = patch.object(module.os, 'stat', side_effect=metadata)
        self.metadata.start(); self.addCleanup(self.metadata.stop)

    def test_one_disable_and_restore_with_a_bounded_deadline(self):
        calls=[]; events=[]; ticks=[0.0]
        original = module.os.write
        def write(fd,data): calls.append(data); return original(fd,data)
        def pause(seconds): ticks[0]+=seconds
        with patch.object(module.os,'write',side_effect=write):
            module.quiesce(42,1,clock=lambda:ticks[0],pause=pause,report=lambda event,**fields:events.append((event,fields)))
        self.assertEqual(calls,[b'0\n',b'1\n'])
        self.assertLessEqual(ticks[0],1.1)
        self.assertEqual((self.path/'authorized').read_text(),'1\n')
        self.assertEqual(events[-1][1]['result'],'restored')

    def test_wrong_number_identity_symlink_and_unauthorized_never_write(self):
        for kind in ('number','identity','symlink','unauthorized'):
            with self.subTest(kind=kind):
                if kind=='identity': (self.path/'product').write_text('other\n')
                if kind=='symlink':
                    (self.path/'authorized').unlink(); (self.path/'authorized').symlink_to('devnum')
                if kind=='unauthorized': (self.path/'authorized').write_text('0\n')
                with patch.object(module.os,'write',side_effect=AssertionError('unexpected write')):
                    with self.assertRaises((RuntimeError,OSError)):
                        module.quiesce(41 if kind=='number' else 42,1)
                if kind=='identity': (self.path/'product').write_text(module.IDENTITY['product']+'\n')
                if kind=='symlink': (self.path/'authorized').unlink()
                (self.path/'authorized').write_text('1\n')

    def test_replacement_never_receives_cleanup_write(self):
        device=module.NativeDevice(42)
        try:
            device.authorize('0')
            self.path.rename(self.path.with_name('old'))
            self.path.mkdir(); (self.path/'authorized').write_text('0\n')
            self.assertEqual(device.restore(),'replacement-untouched')
            self.assertEqual((self.path/'authorized').read_text(),'0\n')
        finally: device.close()

    def test_interrupted_wait_restores_and_has_no_repeat(self):
        def interrupted(_seconds): raise InterruptedError('fixture')
        with self.assertRaises(InterruptedError):
            module.quiesce(42,1,pause=interrupted,report=lambda *args,**kwargs:None)
        self.assertEqual((self.path/'authorized').read_text(),'1\n')

    def test_invalid_durations_fail_before_open(self):
        for duration in (0,301):
            with patch.object(module,'NativeDevice',side_effect=AssertionError('opened device')):
                with self.assertRaises(ValueError): module.quiesce(42,duration)


if __name__ == '__main__': unittest.main()
