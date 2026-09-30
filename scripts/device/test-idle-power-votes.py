#!/usr/bin/env python3
"""Idle power votes: the l11off overlay (PM8350C LDO11 boot-on, late cleanup
turns it off) against a synthetic PM8350C node and, when the private inputs
are present, compose-production-dtb.sh r9 + l11off; the 0148 patch in the
production series; rog5-idle-power-sample against a fake sysfs."""
import importlib.machinery
import importlib.util
import json
import os
from pathlib import Path
import signal
import subprocess
import tempfile
import time
import unittest

REPO = Path(__file__).resolve().parents[2]
DTSO = REPO / 'dts/qcom/sm8350-asus-rog-phone5-antenna-rail-off.dtso'
COMPOSE = REPO / 'scripts/device/compose-production-dtb.sh'
SAMPLE = REPO / 'scripts/device/rog5-idle-power-sample'
SERIES = REPO / 'patches/linux-7.2.7/series.production'
PATCH = '0148-usb-dwc3-qcom-legacy-ROG5-usb-ddr-vote-follows-the-attached-devices.patch'
STATE = Path.home() / '.local/state'
BASE = Path(os.environ.get('ROG5_V9_BASE_DTB', STATE / 'rog5-production-boot-20260923/v9-board.dtb'))
SOURCE = Path(os.environ.get('ROG5_KERNEL_SOURCE', STATE / 'rog5-kernel-7.2.7-build-r110/source'))
R9_FEATURES = ('touch,bluetooth,cpuidle,gpubw,bwmon,ddrscale,periph,audio,slpi,usbotg,osi,aoss,'
               'qupicc,dp,l3,skin,acd,cpucap,usbbtm,mic,usbbtmtc,memx')
R9_SHA = '4a919c152c678d27b9e0f7fe0d337f63384069227acf4167ad7f176a66168d39'
R10_SHA = 'dda8b280da1ee6a4d4c85c663008551757f9766b278dc93dfeba0b875114788e'
VR = '/soc@0/rsc@18200000/regulators-1'

FIXTURE = '''/dts-v1/;
/ {
	soc@0 { rsc@18200000 { regulators-1 {
		compatible = "qcom,pm8350c-rpmh-regulators"; qcom,pmic-id = "c";
		vreg_bob: bob { regulator-name = "vreg_bob"; };
		ldo1 { regulator-name = "vreg_l1c_1p8"; };
	}; }; };
};
'''


def run(*cmd, **kw):
    return subprocess.run(cmd, check=True, capture_output=True, text=True, **kw)


def fdtget(dtb, node, prop, *opts):
    r = subprocess.run(['fdtget', *opts, str(dtb), node, prop], capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else None


class OverlayTest(unittest.TestCase):
    def test_ldo11_boot_on_without_voltage_mode_or_consumer(self):
        with tempfile.TemporaryDirectory() as t:
            t = Path(t)
            (t / 'base.dts').write_text(FIXTURE)
            run('dtc', '-@', '-q', '-I', 'dts', '-O', 'dtb', '-o', str(t / 'base.dtb'), str(t / 'base.dts'))
            run('dtc', '-@', '-q', '-I', 'dts', '-O', 'dtb', '-o', str(t / 'o.dtbo'), str(DTSO))
            run('fdtoverlay', '-i', str(t / 'base.dtb'), '-o', str(t / 'out.dtb'), str(t / 'o.dtbo'))
            out = t / 'out.dtb'
            ldo = VR + '/ldo11'
            self.assertEqual(fdtget(out, ldo, 'regulator-name'), 'rog5_l11c_antenna')
            # Any min/max sets apply_uV (a voltage request at registration).
            for prop in ('regulator-min-microvolt', 'regulator-max-microvolt', 'regulator-initial-mode'):
                self.assertIsNone(fdtget(out, ldo, prop), prop)
            self.assertIsNotNone(fdtget(out, ldo, 'regulator-boot-on'))
            self.assertIsNone(fdtget(out, ldo, 'regulator-always-on'))
            self.assertIsNone(fdtget(out, ldo, 'phandle'))
            self.assertNotIn('ldo7', run('fdtget', '-l', str(out), VR).stdout.split())


@unittest.skipUnless(BASE.is_file() and (SOURCE / 'scripts/dtc/include-prefixes').is_dir(),
                     'requires the private V9 base DTB and the kernel r110 source')
class ProductionR10Test(unittest.TestCase):
    def test_r9_reproduced_and_r10_adds_only_ldo11(self):
        with tempfile.TemporaryDirectory() as t:
            t = Path(t)
            run('sh', str(COMPOSE), str(BASE), str(SOURCE), str(t / 'r9.dtb'), R9_FEATURES)
            run('sh', str(COMPOSE), str(BASE), str(SOURCE), str(t / 'r10.dtb'), R9_FEATURES + ',l11off')
            sha = lambda p: run('sha256sum', str(p)).stdout.split()[0]
            self.assertEqual(sha(t / 'r9.dtb'), R9_SHA)
            self.assertEqual(sha(t / 'r10.dtb'), R10_SHA)
            d9 = run('dtc', '-q', '-s', '-I', 'dtb', '-O', 'dts', str(t / 'r9.dtb')).stdout.splitlines()
            d10 = run('dtc', '-q', '-s', '-I', 'dtb', '-O', 'dts', str(t / 'r10.dtb')).stdout.splitlines()
            added = [line.strip() for line in d10 if line not in d9]
            self.assertEqual(len(d10) - len(d9), 5)
            self.assertIn('ldo11 {', added)
            self.assertIn('regulator-boot-on;', added)


class SeriesTest(unittest.TestCase):
    def test_0148_follows_0147_and_touches_only_the_legacy_glue(self):
        names = [l for l in SERIES.read_text().split() if not l.startswith('#')]
        self.assertEqual(names[-2:][1], PATCH)
        self.assertTrue(names[-2].startswith('0147-'))
        text = (SERIES.parent / PATCH).read_text()
        self.assertEqual(sorted({l[6:] for l in text.splitlines() if l.startswith('+++ b/')}),
                         ['drivers/usb/dwc3/dwc3-qcom-legacy.c'])
        for needle in ('usb_register_notify', 'ddr_bw_follows_devices', 'USB_MEMORY_AVG_FLOOR_BW 1',
                       'qcom->bw_role_hold = true', 'dwc3_qcom_bw_prune'):
            self.assertIn(needle, text)


def load_sample(root):
    os.environ['ROG5_IPS_ROOT'] = str(root)
    os.environ['ROG5_IPS_NOSLEEP'] = '1'
    loader = importlib.machinery.SourceFileLoader('ips', str(SAMPLE))
    spec = importlib.util.spec_from_loader('ips', loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


def write(root, rel, text):
    p = root / rel.lstrip('/')
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)


DDR = ('DDR LPM Stat Name:0xd4\tcount:0\tDuration (ticks):0\n'
       'DDR Freq 200Mhz:\tCP IDX:0\tcount:{c200}\tDuration (ticks):{t200}\n'
       'DDR Freq 451Mhz:\tCP IDX:2\tcount:5\tDuration (ticks):{t451}\n')
ICC = ('ebi@1580000.interconnect                        4480000     12784000\n'
       '  a8f8800.usb                            0            1            1\n'
       '  a6f8800.usb                            0         2000        12000\n'
       'xm_usb3_0@16e0000.interconnect                   2000        12000\n'
       '  a6f8800.usb                            0         2000        12000\n')


class SampleTest(unittest.TestCase):
    def fake(self, root):
        write(root, '/sys/class/power_supply/qcom-battmgr-usb/online', '1')
        write(root, '/sys/class/power_supply/qcom-battmgr-usb/voltage_now', '5000000')
        write(root, '/sys/class/power_supply/qcom-battmgr-usb/current_now', '300000')
        write(root, '/sys/class/power_supply/qcom-battmgr-wls/online', '0')
        write(root, '/sys/class/power_supply/qcom-battmgr-bat/current_now', '-2000')
        write(root, '/sys/kernel/debug/qcom_stats/ddr_stats', DDR.format(c200=3, t200=100, t451=TICKS * 10))
        write(root, '/sys/kernel/debug/interconnect/interconnect_summary', ICC)
        write(root, '/sys/class/regulator/regulator.9/name', 'rog5_l11c_antenna')
        write(root, '/sys/class/regulator/regulator.9/state', 'disabled')
        write(root, '/sys/class/regulator/regulator.3/name', 'vreg_bob')
        write(root, '/sys/bus/usb/devices/3-1/idVendor', '046d')
        write(root, '/sys/bus/usb/devices/3-1/idProduct', 'c08b')
        write(root, '/sys/bus/usb/devices/3-1/speed', '12')
        write(root, '/sys/bus/usb/devices/usb3/speed', '480')
        write(root, '/sys/module/dwc3_qcom_legacy/parameters/ddr_bw_follows_devices', 'Y')

    def test_window_reads_power_ddr_votes_rails_devices(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            self.fake(root)
            m = load_sample(root)
            before = m.ddr_residency()
            write(root, '/sys/kernel/debug/qcom_stats/ddr_stats',
                  DDR.format(c200=4, t200=100 + TICKS * 30, t451=TICKS * 20))
            rows = m.ddr_delta(before, m.ddr_residency())
            self.assertEqual(rows, [(200, 1, 30.0), (451, 0, 10.0)])
            self.assertAlmostEqual(m.input_power_w(), 1.5)
            self.assertEqual(m.usb_votes(), {'a8f8800.usb': '1/1', 'a6f8800.usb': '2000/12000'})
            self.assertEqual(list(m.rails()), ['rog5_l11c_antenna'])
            self.assertEqual(m.usb_devices(), ['3-1 046d:c08b 12'])
            rec = m.window('x', 4, 2)
            self.assertEqual(rec['n'], 3)
            self.assertTrue(rec['valid'])
            self.assertEqual(rec['param'], 'Y')

    def test_ab_alternates_and_restores_the_parameter(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            self.fake(root)
            param = root / 'sys/module/dwc3_qcom_legacy/parameters/ddr_bw_follows_devices'
            out = root / 'w.json'
            env = dict(os.environ, ROG5_IPS_ROOT=str(root), ROG5_IPS_NOSLEEP='1')
            r = subprocess.run(['python3', str(SAMPLE), '--ab=2', '--seconds=2', '--interval=1',
                                '--settle=0', f'--json={out}'], env=env, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertEqual([w['param'] for w in json.loads(out.read_text())], ['N', 'Y', 'Y', 'N'])
            self.assertEqual(param.read_text(), 'Y')
            self.assertIn('restored ddr_bw_follows_devices=Y', r.stdout)

    def test_unreadable_or_reset_ddr_stats_invalidate_the_window(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            self.fake(root)
            m = load_sample(root)
            before = m.ddr_residency()
            self.assertIsNone(m.ddr_delta(before, None))
            self.assertIsNone(m.ddr_delta(None, before))
            reset = m.ddr_residency()
            reset[451] = (1, 5)
            self.assertIsNone(m.ddr_delta(before, reset))
            (root / 'sys/kernel/debug/qcom_stats/ddr_stats').unlink()
            self.assertIsNone(m.ddr_residency())
            rec = m.window('x', 2, 1)
            self.assertFalse(rec['valid'])
            self.assertIsNone(rec['ddr'])

    def test_window_samples_start_to_end(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            self.fake(root)
            m = load_sample(root)
            self.assertEqual(m.window('x', 4, 2)['n'], 3)
            self.assertEqual(m.window('x', 1, 2)['n'], 2)

    def test_signals_during_ab_restore_the_parameter(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            self.fake(root)
            param = root / 'sys/module/dwc3_qcom_legacy/parameters/ddr_bw_follows_devices'
            env = dict(os.environ, ROG5_IPS_ROOT=str(root))
            env.pop('ROG5_IPS_NOSLEEP', None)
            p = subprocess.Popen(['python3', str(SAMPLE), '--ab=1', '--seconds=30', '--interval=1',
                                  '--settle=0'], env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                 text=True)
            for _ in range(100):
                if param.read_text() == 'N':
                    break
                time.sleep(0.05)
            self.assertEqual(param.read_text(), 'N')
            p.send_signal(signal.SIGTERM)
            p.send_signal(signal.SIGTERM)
            out, err = p.communicate(timeout=30)
            self.assertEqual(param.read_text(), 'Y', out + err)
            self.assertIn('restored ddr_bw_follows_devices=Y', out)

    def test_ab_refuses_without_0148(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            self.fake(root)
            (root / 'sys/module/dwc3_qcom_legacy/parameters/ddr_bw_follows_devices').unlink()
            env = dict(os.environ, ROG5_IPS_ROOT=str(root), ROG5_IPS_NOSLEEP='1')
            r = subprocess.run(['python3', str(SAMPLE), '--ab=1'], env=env, capture_output=True, text=True)
            self.assertNotEqual(r.returncode, 0)
            self.assertIn('without 0148', r.stderr)


TICKS = 19200000

if __name__ == '__main__':
    unittest.main()
