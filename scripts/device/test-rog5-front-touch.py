#!/usr/bin/env python3
"""Host-only protocol checks and compiled disabled-DT assertions; no module build."""
import importlib.util
import os
from pathlib import Path
import shutil
import struct
import subprocess
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[2]
SOURCE = REPO / 'tools/rog5-fts3658u'
OVERLAY = REPO / 'dts/qcom/sm8350-rog5-mp2-front-touch-disabled.dtso'
PARSER = REPO / 'scripts/device/verify-recovery-dtb-delta.py'


def command(argv):
    result = subprocess.run(argv, check=True, capture_output=True,
                            text=True, timeout=60)
    if result.stdout:
        print(result.stdout.rstrip())
    return result


def cells(data):
    return list(struct.unpack('>' + str(len(data) // 4) + 'I', data))


class FrontTouchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        compiler = shutil.which(os.environ.get('CC', 'cc'))
        dtc = shutil.which('dtc')
        if compiler is None or dtc is None:
            raise RuntimeError('require a C compiler with UBSan and dtc')
        scratch = Path(os.environ.get('ROG5_TEST_TMPDIR', REPO / 'build'))
        scratch.mkdir(parents=True, exist_ok=True)
        cls.scratch = tempfile.TemporaryDirectory(
            prefix='rog5-front-touch-', dir=scratch)
        cls.addClassCleanup(cls.scratch.cleanup)
        cls.output = Path(cls.scratch.name)
        cls.compiler = compiler
        spec = importlib.util.spec_from_file_location('dtb_parser', PARSER)
        parser = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(parser)
        blob = cls.output / 'disabled.dtbo'
        command([dtc, '-@', '-I', 'dts', '-O', 'dtb', '-o', str(blob),
                 str(OVERLAY)])
        cls.nodes = parser.read_dtb(blob)
        cls.fixups = {
            key: value.rstrip(b'\0').decode().split('\0')
            for key, value in cls.nodes['/__fixups__'].items()
        }

    def target(self, symbol):
        refs = [ref[:-9] for ref in self.fixups[symbol]
                if ref.endswith(':target:0')]
        self.assertEqual(len(refs), 1)
        return refs[0] + '/__overlay__'

    def compile_and_run(self, name, flags):
        output = self.output / name
        command([self.compiler, '-std=c11', '-Wall', '-Wextra', '-Werror',
                 '-pedantic', *flags, str(SOURCE / 'test_protocol.c'),
                 '-o', str(output)])
        result = command([str(output)])
        self.assertIn('PASS ', result.stdout)

    def test_protocol_optimized(self):
        self.compile_and_run('protocol', ['-O2'])

    def test_protocol_ubsan(self):
        self.compile_and_run('protocol-ubsan', [
            '-O1', '-g', '-fsanitize=undefined', '-fno-sanitize-recover=all'])

    def test_exact_external_targets(self):
        self.assertEqual(set(self.fixups), {'apps_rsc', 'tlmm', 'spi4', 'i2c4'})

    def test_no_enabled_nodes(self):
        statuses = [props['status'] for props in self.nodes.values()
                    if 'status' in props]
        self.assertEqual(statuses, [b'disabled\0'] * 5)

    def test_controller_exclusion(self):
        for symbol in ('spi4', 'i2c4'):
            self.assertEqual(self.nodes[self.target(symbol)]['status'],
                             b'disabled\0')

    def test_real_disabled_rails(self):
        base = self.target('apps_rsc') + '/regulators-1'
        for name, voltage in (('ldo3', 3008000), ('ldo8', 1800000)):
            rail = self.nodes[base + '/' + name]
            self.assertEqual(rail['status'], b'disabled\0')
            self.assertEqual(cells(rail['regulator-min-microvolt']), [voltage])
            self.assertEqual(cells(rail['regulator-max-microvolt']), [voltage])
        self.assertEqual(self.nodes[base + '/ldo8']['regulator-always-on'], b'')
        self.assertFalse(any(key.endswith('-supply') for key in self.nodes[base]))

    def test_exact_front(self):
        child = self.nodes[self.target('i2c4') + '/touchscreen@38']
        self.assertEqual(child['compatible'], b'asus,rog5-mp2-fts3658u\0')
        expected = {
            'reg': [56], 'interrupts': [23, 2],
            'reset-gpios': [0xffffffff, 22, 1],
            'io-enable-gpios': [0xffffffff, 131, 0],
            'touchscreen-size-x': [17280], 'touchscreen-size-y': [39168],
        }
        for key, value in expected.items():
            self.assertEqual(cells(child[key]), value)
        base = self.target('apps_rsc') + '/regulators-1'
        self.assertEqual(child['vdd-supply'],
                         self.nodes[base + '/ldo3']['phandle'])
        self.assertEqual(child['vcc_i2c-supply'],
                         self.nodes[base + '/ldo8']['phandle'])

    def test_pinctrl_not_selected_by_other_device(self):
        pin = self.target('tlmm') + '/rog5-front-touch-active-state'
        self.assertEqual(self.nodes[pin]['pins'], b'gpio22\0gpio23\0')
        self.assertEqual(self.nodes[pin]['function'], b'gpio\0')
        self.assertEqual(cells(self.nodes[pin]['drive-strength']), [8])
        consumers = [path for path, props in self.nodes.items()
                     if props.get('pinctrl-0') == self.nodes[pin]['phandle']]
        self.assertEqual(consumers, [self.target('i2c4') + '/touchscreen@38'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
