#!/usr/bin/env python3
"""Run the staged encoder helper against inert sysfs/command adapters."""
import json
import os
import re
from pathlib import Path
import subprocess
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / 'scripts/device/rog5-video-encoder-trial'


class EncoderTrial(unittest.TestCase):
    def run_trial(self, mode='pass', *args):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for d in ('sys/module/qcom_iris/parameters', 'sys/module/printk/parameters',
                      'sys/class/video4linux/video1', 'proc/sys/kernel/random', 'dev', 'bin'):
                (root / d).mkdir(parents=True)
            for name in ('markers', 'marker_delay_ms', 'enc_stop_before'):
                (root / 'sys/module/qcom_iris/parameters' / name).write_text('0')
            (root / 'sys/class/video4linux/video1/name').write_text('qcom-iris-encoder')
            (root / 'proc/sys/kernel/random/boot_id').write_text('fixture-boot')
            (root / 'dev/kmsg').touch()
            # Redirect only paths in a disposable script copy, with no production
            # environment override that could bypass the helper's preconditions.
            source = SCRIPT.read_text()
            source = re.sub(r'/(?:sys|proc|dev|var/tmp)/', lambda m: str(root) + m[0], source)
            (root / 'trial').write_text(source)
            mock = r'''#!/usr/bin/env python3
import os, pathlib, sys
r=pathlib.Path(os.environ['FIXTURE_ROOT']); mode=os.environ['FIXTURE_MODE']
name=pathlib.Path(sys.argv[0]).name
if name=='id': print('0')
elif name=='sync' or name=='sleep': pass
elif name=='fuser': sys.exit(0 if mode=='open' else 1)
elif name=='ffprobe': print('59' if mode=='badframes' else '60')
elif name=='ffmpeg':
    stop=(r/'sys/module/qcom_iris/parameters/enc_stop_before').read_text().strip()
    with (r/'commands').open('a') as f: f.write(stop+'\n')
    pathlib.Path(sys.argv[-1]).write_text('fake encoder output')
    sys.exit(137 if mode=='timeout' else (1 if stop!='0' else 0))
elif name=='dmesg':
    if '-n' in sys.argv: sys.exit(0)
    stop=(r/'sys/module/qcom_iris/parameters/enc_stop_before').read_text().strip()
    # A matching stale stop before the stage must not satisfy this invocation.
    print('mark: encoder stopped before command '+stop)
    if mode!='missing_start':
        print('rog5-enc: stage stop_before='+stop+': encode 1280x720 NV12 -> H.264')
        print('mark: encoder configuration observed')
    if mode=='warning': print('WARNING: test injected kernel warning')
    elif mode=='fatal': print('fatal firmware error (injected)')
    elif mode!='missing' and stop!='0': print('mark: encoder stopped before command '+stop)
'''
            for name in ('id', 'sync', 'sleep', 'fuser', 'ffprobe', 'ffmpeg', 'dmesg'):
                path = root / 'bin' / name
                path.write_text(mock)
                path.chmod(0o755)
            env = dict(os.environ, PATH=str(root / 'bin') + ':' + os.environ['PATH'],
                       FIXTURE_ROOT=str(root), FIXTURE_MODE=mode)
            shell = ['sh']
            if os.environ.get('ROG5_TEST_QEMU') and os.environ.get('ROG5_TEST_BUSYBOX'):
                shell = [os.environ['ROG5_TEST_QEMU'], os.environ['ROG5_TEST_BUSYBOX'], 'sh']
            result = subprocess.run([*shell, str(root / 'trial'), *args], env=env,
                                    capture_output=True, text=True, timeout=30)
            commands = (root / 'commands').read_text().splitlines() if (root / 'commands').exists() else []
            parameter = (root / 'sys/module/qcom_iris/parameters/enc_stop_before').read_text().strip()
            return result, commands, parameter

    def test_all_stages_and_sixty_frames(self):
        result, commands, parameter = self.run_trial()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(commands, ['0x11002', '0x211001', '0x211002', '0x211004', '0x211005', '0'])
        self.assertIn('done: PASS', result.stdout)
        self.assertEqual(parameter, '0')

    def test_stop_at_timeout_missing_current_marker_and_kernel_fault(self):
        for mode in ('timeout', 'missing', 'warning', 'fatal'):
            with self.subTest(mode=mode):
                result, commands, parameter = self.run_trial(mode)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(commands, ['0x11002'])
                self.assertIn('done: FAIL', result.stdout)
                self.assertEqual(parameter, '0')

    def test_full_encode_without_current_stage_evidence_fails(self):
        result, commands, parameter = self.run_trial('missing_start', '--stages', '0')
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(commands, ['0'])
        self.assertIn('no current-stage kernel evidence', result.stdout)

    def test_frame_count_is_required(self):
        result, commands, parameter = self.run_trial('badframes')
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(len(commands), 6)
        self.assertIn('59 frames', result.stdout)

    def test_preconditions_and_reviewed_boundaries(self):
        result, commands, parameter = self.run_trial('open')
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(commands)
        for args in (('--delay', 'bad'), ('--delay', '1001'), ('--stages', ''), ('--stages', '0xdead')):
            with self.subTest(args=args):
                result, commands, parameter = self.run_trial('pass', *args)
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse(commands)


if __name__ == '__main__':
    unittest.main()
