#!/usr/bin/env python3
"""Standby bisect kit: compose-standby-bisect-dtb.sh against a synthetic r9-shaped
tree (and the real production DTB r9 when it is present), the ramdisk gate on
the composed noadsp tree, and rog5-standby-bisect-measure's verdict with mocked
counters and a mocked suspend."""
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[2]
COMPOSE = REPO / 'scripts/device/compose-standby-bisect-dtb.sh'
MEASURE = REPO / 'scripts/device/rog5-standby-bisect-measure'
GATE = REPO / 'scripts/device/load-persistent-root-power-usb.sh'
R9 = Path(os.environ.get('ROG5_BISECT_R9_DTB', Path.home() /
          '.local/state/rog5-production-boot-20260923/platform-cpucap-dp4-btmtc-memx-dtb-r9/board.dtb'))
R9_SHA = '4a919c152c678d27b9e0f7fe0d337f63384069227acf4167ad7f176a66168d39'

# The nodes and phandle chains of production DTB r9 the kit relies on.
FIXTURE = '''/dts-v1/;
/ {
	#address-cells = <2>; #size-cells = <2>;
	memory { device_type = "memory"; reg = <0 0x80000000 0 0x37100000>; };
	reserved-memory {
		#address-cells = <2>; #size-cells = <2>; ranges;
		cdsp_mem: memory@89700000 { reg = <0 0x89700000 0 0x1e00000>; no-map; };
		memory@34a000000 { reg = <3 0x4a000000 0 0x4000000>; no-map; };
	};
	soc@0 {
		#address-cells = <2>; #size-cells = <2>; ranges;
		remoteproc@5c00000 { compatible = "qcom,sm8350-slpi-pas";
			firmware-name = "qcom/sm8350/slpi.mdt"; status = "okay"; };
		remoteproc@3000000 { compatible = "qcom,sm8350-adsp-pas"; status = "okay";
			glink-edge { apr { service@4 {
				q6afecc: clock-controller { #clock-cells = <2>; };
			}; }; };
		};
		remoteproc@a300000 { compatible = "qcom,sm8350-cdsp-pas";
			memory-region = <&cdsp_mem>; status = "disabled";
			glink-edge { fastrpc { compatible = "qcom,fastrpc"; }; };
		};
		display-subsystem@ae00000 {
			displayport-controller@ae90000 { status = "okay"; };
		};
		codec@3370000 { compatible = "qcom,sm8250-lpass-va-macro";
			clocks = <&q6afecc 57 1 &q6afecc 102 1 &q6afecc 103 1>; };
		pinctrl@33c0000 { compatible = "qcom,sm8350-lpass-lpi-pinctrl";
			clocks = <&q6afecc 102 1 &q6afecc 103 1>; };
		other_clk: clock-controller@100000 { #clock-cells = <1>; };
		geniqup@ac0000 { i2c@a94000 { status = "okay";
			typec@4e { compatible = "richtek,rt1715"; vbus-supply = <&btm_vbus>; };
		}; };
	};
	pmic-glink { compatible = "qcom,sm8350-pmic-glink";
		asus,btm-otg-boost = <&btm_boost>; connector@0 { reg = <0>; }; };
	btm_vbus: regulator-rog5-btm-vbus { compatible = "regulator-fixed";
		vin-supply = <&btm_boost>;
		btm_boost: btm-otg-boost { regulator-name = "btm_otg_boost"; };
	};
	sound { compatible = "qcom,sm8250-sndcard"; };
	/*EXTRA*/
};
'''


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def fdtget(dtb, node, prop, typ=None):
    cmd = ['fdtget'] + (['-t', typ] if typ else []) + [str(dtb), node, prop]
    p = subprocess.run(cmd, capture_output=True, text=True)
    return p.stdout.strip() if p.returncode == 0 else None


def function(text, name):
    begin = text.index(name + '() {')
    return text[begin:text.index('\n}', begin) + 2]


@unittest.skipUnless(shutil.which('dtc') and shutil.which('fdtget') and shutil.which('fdtput'),
                     'needs dtc, fdtget and fdtput')
class ComposeTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        self.base = self.fixture()

    def fixture(self, source=FIXTURE, name='base.dtb'):
        dts = self.tmp / (name + '.dts')
        dts.write_text(source)
        out = self.tmp / name
        subprocess.run(['dtc', '-q', '-I', 'dts', '-O', 'dtb', '-o', str(out), str(dts)], check=True)
        return out

    def compose(self, variants, base=None, out=None, expected=None):
        base = base or self.base
        out = out or self.tmp / ('out-%s.dtb' % variants.replace(',', '_'))
        env = dict(os.environ, EXPECTED_BISECT_BASE_SHA256=expected or sha(base))
        p = subprocess.run(['sh', str(COMPOSE), str(base), str(out), variants],
                           capture_output=True, text=True, env=env, timeout=30)
        return p, out

    def test_every_variant_keeps_memx_and_the_markers(self):
        for variants in ('baseline', 'noslpi', 'noadsp', 'cdsp', 'noslpi,noadsp', 'noadsp,noslpi,cdsp'):
            with self.subTest(variants):
                p, out = self.compose(variants)
                self.assertEqual(p.returncode, 0, p.stderr)
                self.assertIn(sha(out), p.stdout)
                self.assertEqual(fdtget(out, '/', 'rog5,standby-bisect'), variants)
                self.assertEqual(fdtget(out, '/', 'rog5,standby-bisect-base'), 'production-dtb-r9')
                self.assertEqual(fdtget(out, '/reserved-memory/memory@34a000000', 'reg', 'x'), '3 4a000000 0 4000000')
                self.assertIsNotNone(fdtget(out, '/reserved-memory/memory@34a000000', 'no-map'))

    def test_baseline_changes_nothing_else(self):
        p, out = self.compose('baseline')
        self.assertEqual(p.returncode, 0, p.stderr)
        subprocess.run(['fdtput', '-d', str(out), '/', 'rog5,standby-bisect'], check=True)
        subprocess.run(['fdtput', '-d', str(out), '/', 'rog5,standby-bisect-base'], check=True)
        dts = lambda d: subprocess.run(['dtc', '-q', '-I', 'dtb', '-O', 'dts', str(d)],
                                       capture_output=True, text=True, check=True).stdout
        self.assertEqual(dts(out), dts(self.base))

    def test_noslpi_only_disables_the_slpi(self):
        p, out = self.compose('noslpi')
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(fdtget(out, '/soc@0/remoteproc@5c00000', 'status'), 'disabled')
        self.assertEqual(fdtget(out, '/soc@0/remoteproc@3000000', 'status'), 'okay')
        self.assertIsNotNone(fdtget(out, '/sound', 'compatible'))
        self.assertIsNone(fdtget(out, '/soc@0/geniqup@ac0000/i2c@a94000/typec@4e', 'status'))

    def test_noadsp_takes_every_adsp_dependent_node_along(self):
        p, out = self.compose('noadsp')
        self.assertEqual(p.returncode, 0, p.stderr)
        adsp = '/soc@0/remoteproc@3000000'
        self.assertEqual(fdtget(out, adsp, 'status'), 'disabled')
        self.assertEqual(fdtget(out, adsp, 'rog5,standby-bisect'), 'noadsp')
        for node in ('/pmic-glink', '/soc@0/display-subsystem@ae00000/displayport-controller@ae90000',
                     '/soc@0/codec@3370000', '/soc@0/pinctrl@33c0000', '/regulator-rog5-btm-vbus',
                     '/soc@0/geniqup@ac0000/i2c@a94000/typec@4e'):
            with self.subTest(node):
                self.assertEqual(fdtget(out, node, 'status'), 'disabled')
        self.assertIsNone(fdtget(out, '/sound', 'compatible'))
        # The bottom port's I2C/xHCI side and the SLPI stay as in production.
        self.assertEqual(fdtget(out, '/soc@0/geniqup@ac0000/i2c@a94000', 'status'), 'okay')
        self.assertEqual(fdtget(out, '/soc@0/remoteproc@5c00000', 'status'), 'okay')

    def test_the_ramdisk_gate_accepts_exactly_the_composed_noadsp_tree(self):
        text = GATE.read_text()
        body = function(text, 'adsp_bisect_off')
        for variants, want in (('noadsp', 'SKIP'), ('noslpi', 'CHECK'), ('baseline', 'CHECK')):
            with self.subTest(variants):
                p, out = self.compose(variants)
                self.assertEqual(p.returncode, 0, p.stderr)
                tree = self.tmp / ('tree-' + variants)
                for node, prop in (('/soc@0/remoteproc@3000000', 'status'),
                                   ('/soc@0/remoteproc@3000000', 'rog5,standby-bisect'),
                                   ('/pmic-glink', 'status')):
                    value = fdtget(out, node, prop)
                    if value is None:
                        continue
                    path = tree / node.lstrip('/') / prop
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_bytes(value.encode() + b'\0')
                script = 'production=1\n' + body.replace('/proc/device-tree', str(tree)) + \
                    '\nadsp_bisect_off && echo SKIP || echo CHECK\n'
                r = subprocess.run(['sh'], input=script, text=True, capture_output=True, timeout=5)
                self.assertEqual(r.stdout.strip(), want, r.stderr)

    def test_cdsp_boots_without_a_fastrpc_client(self):
        p, out = self.compose('cdsp')
        self.assertEqual(p.returncode, 0, p.stderr)
        node = '/soc@0/remoteproc@a300000'
        self.assertEqual(fdtget(out, node, 'status'), 'okay')
        self.assertEqual(fdtget(out, node, 'firmware-name'), 'qcom/sm8350/cdsp.mdt')
        self.assertEqual(fdtget(out, node + '/glink-edge/fastrpc', 'status'), 'disabled')

    def test_bad_arguments_are_refused(self):
        for variants, message in (('baseline,noslpi', 'baseline cannot be combined'),
                                  ('noslpi,noslpi', 'repeated variant'),
                                  ('noslpi,foo', 'unknown variant foo'),
                                  (',', 'missing variant')):
            with self.subTest(variants):
                p, out = self.compose(variants, out=self.tmp / 'bad.dtb')
                self.assertNotEqual(p.returncode, 0)
                self.assertIn(message, p.stderr)
                self.assertFalse(out.exists())
        p, _ = self.compose('noslpi', expected='0' * 64)
        self.assertIn('not the reviewed production DTB', p.stderr)
        (self.tmp / 'exists.dtb').write_bytes(b'')
        p, _ = self.compose('noslpi', out=self.tmp / 'exists.dtb')
        self.assertIn('output exists', p.stderr)

    def test_a_base_that_is_not_r9_shaped_is_refused(self):
        cases = (
            ('no memx', FIXTURE.replace('memory@34a000000 { reg = <3 0x4a000000 0 0x4000000>; no-map; };', ''),
             'memx reservation missing'),
            ('stage-A switch', FIXTURE.replace('/*EXTRA*/', 'rog5-btm-vbus-output { compatible = "regulator-output"; };'),
             'stage-A 5 V switch present'),
            ('VA macro on another clock', FIXTURE.replace('clocks = <&q6afecc 57 1 &q6afecc 102 1 &q6afecc 103 1>;',
                                                         'clocks = <&other_clk 57 &q6afecc 102 1 &q6afecc 103 1>;'),
             'not all from the ADSP q6afe clock controller'),
            ('TCPC on another supply', FIXTURE.replace('vbus-supply = <&btm_vbus>;', 'vbus-supply = <&btm_boost>;'),
             'bottom-port 5 V chain'),
            ('SLPI already off', FIXTURE.replace('firmware-name = "qcom/sm8350/slpi.mdt"; status = "okay";',
                                                 'firmware-name = "qcom/sm8350/slpi.mdt"; status = "disabled";'),
             'remoteproc@5c00000 status is not okay'),
            ('pmic-glink off', FIXTURE.replace('asus,btm-otg-boost = <&btm_boost>;',
                                               'asus,btm-otg-boost = <&btm_boost>; status = "disabled";'),
             '/pmic-glink is not enabled'),
        )
        for label, source, message in cases:
            with self.subTest(label):
                base = self.fixture(source, name=label.replace(' ', '-') + '.dtb')
                p, out = self.compose('noadsp', base=base, out=self.tmp / 'refused.dtb')
                self.assertNotEqual(p.returncode, 0)
                self.assertIn(message, p.stderr)
                self.assertFalse(out.exists())


@unittest.skipUnless(R9.is_file() and shutil.which('dtc') and shutil.which('fdtput'),
                     'requires the private production DTB r9')
class ProductionR9Test(unittest.TestCase):
    """The real r9 bytes: every variant composes with the built-in hash, and no
    enabled node of a noadsp tree still points at a disabled or removed node."""

    def test_r9_variants_leave_no_dangling_enabled_consumer(self):
        try:
            import libfdt
        except ImportError:
            self.skipTest('requires python libfdt')
        self.assertEqual(sha(R9), R9_SHA)
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp)
        # Production itself points two enabled nodes at disabled ones (i2c13's
        # GPI DMA 1, kept off on purpose; a thermal zone on the disabled PMIC
        # SID 5): only references a variant adds count.
        known = set(dangling(libfdt, R9.read_bytes()))
        self.assertEqual(sorted(dangling_self_test(libfdt, tmp)),
                         [('/consumer', 'clocks', '/clock-b'), ('/lost', 'interrupts-extended', 'missing phandle 0x7777')])
        for variants in ('baseline', 'noslpi', 'noadsp', 'cdsp', 'noslpi,noadsp', 'noadsp,noslpi,cdsp'):
            with self.subTest(variants):
                out = tmp / (variants.replace(',', '_') + '.dtb')
                env = {k: v for k, v in os.environ.items() if k != 'EXPECTED_BISECT_BASE_SHA256'}
                p = subprocess.run(['sh', str(COMPOSE), str(R9), str(out), variants],
                                   capture_output=True, text=True, env=env, timeout=30)
                self.assertEqual(p.returncode, 0, p.stderr)
                self.assertEqual(sorted(set(dangling(libfdt, out.read_bytes())) - known), [])
        # The check sees a consumer left behind: the TCPC re-enabled in noadsp.
        subprocess.run(['fdtput', '-t', 's', str(tmp / 'noadsp.dtb'),
                        '/soc@0/geniqup@ac0000/i2c@a94000/typec@4e', 'status', 'okay'], check=True)
        self.assertIn(('/soc@0/geniqup@ac0000/i2c@a94000/typec@4e', 'vbus-supply', '/regulator-rog5-btm-vbus'),
                      set(dangling(libfdt, (tmp / 'noadsp.dtb').read_bytes())) - known)


# Supplier lists fw_devlink follows, with the provider's cells property (None:
# plain phandle list). OF graph links (remote-endpoint) are left out: fw_devlink
# ignores a graph link to a disabled node.
PHANDLE_LISTS = {
    'clocks': '#clock-cells', 'power-domains': '#power-domain-cells',
    'interconnects': '#interconnect-cells', 'iommus': '#iommu-cells', 'dmas': '#dma-cells',
    'phys': '#phy-cells', 'sound-dai': '#sound-dai-cells', 'mboxes': '#mbox-cells',
    'resets': '#reset-cells', 'qcom,smem-states': '#qcom,smem-state-cells',
    'thermal-sensors': '#thermal-sensor-cells', 'io-channels': '#io-channel-cells',
    'interrupts-extended': '#interrupt-cells', 'memory-region': None, 'nvmem-cells': None,
}


def dangling(libfdt, data):
    """(consumer, property, supplier) for every enabled consumer whose supplier
    is disabled, sits under a disabled node, or does not exist."""
    import struct
    fdt = libfdt.Fdt(data)
    nodes = {}

    def walk(off, path, enabled):
        try:
            status = fdt.getprop(off, 'status').as_str()
        except libfdt.FdtException:
            status = 'okay'
        enabled = enabled and status in ('okay', 'ok')
        nodes[off] = (path, enabled)
        child = fdt.first_subnode(off, [libfdt.FDT_ERR_NOTFOUND])
        while child >= 0:
            walk(child, path.rstrip('/') + '/' + fdt.get_name(child), enabled)
            child = fdt.next_subnode(child, [libfdt.FDT_ERR_NOTFOUND])
    walk(0, '/', True)
    by_phandle = {}
    for off in nodes:
        try:
            by_phandle[struct.unpack('>I', bytes(fdt.getprop(off, 'phandle')))[0]] = off
        except libfdt.FdtException:
            pass

    def cells(off, name):
        try:
            return struct.unpack('>I', bytes(fdt.getprop(off, name)))[0]
        except libfdt.FdtException:
            return None

    bad = []
    for off, (path, enabled) in nodes.items():
        if not enabled or path.startswith('/__'):
            continue
        po = fdt.first_property_offset(off, [libfdt.FDT_ERR_NOTFOUND])
        while po >= 0:
            prop = fdt.get_property_by_offset(po)
            name, value = prop.name, bytes(prop)
            po = fdt.next_property_offset(po, [libfdt.FDT_ERR_NOTFOUND])
            if name in PHANDLE_LISTS:
                cells_name = PHANDLE_LISTS[name]
            elif name.endswith('-supply') or (name.startswith('pinctrl-') and name[8:].isdigit()):
                cells_name = None
            else:
                continue
            words = struct.unpack('>%dI' % (len(value) // 4), value)
            i = 0
            while i < len(words):
                target = by_phandle.get(words[i])
                if target is None:
                    bad.append((path, name, 'missing phandle 0x%x' % words[i]))
                    break
                if not nodes[target][1]:
                    bad.append((path, name, nodes[target][0]))
                n = 0 if cells_name is None else cells(target, cells_name)
                if n is None:
                    bad.append((path, name, nodes[target][0] + ' without ' + cells_name))
                    break
                i += 1 + n
    return bad


def dangling_self_test(libfdt, tmp):
    """The walk must see a disabled second supplier and a dangling phandle."""
    dts = tmp / 'walk.dts'
    dts.write_text("""/dts-v1/;
/ { a: clock-a { #clock-cells = <1>; }; b: clock-b { #clock-cells = <0>; status = "disabled"; };
    consumer { clocks = <&a 7 &b>; }; off { status = "disabled"; clocks = <&b>; };
    lost { interrupts-extended = <0x7777 1>; }; };
""")
    out = tmp / 'walk.dtb'
    subprocess.run(['dtc', '-q', '-I', 'dts', '-O', 'dtb', '-o', str(out), str(dts)], check=True)
    return dangling(libfdt, out.read_bytes())


class MeasureVerdictTest(unittest.TestCase):
    """The verdict: APSS residency comes from frozen timekeeping and the cluster
    genpd s2idle count (qcom_stats "apss" stays empty under mainline)."""

    STATS = {'ddr': 0, 'cxsd': 0, 'aosd': 0, 'adsp': 5}

    def run_measure(self, frozen=58.0, cluster=1, ddr=0, lpm=0, cxsd=0, success=1, rejected=0,
                    uptime_before='99.99', timer_after=True):
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp)
        stats, binp, drm, sysdev, dt = (tmp / d for d in ('stats', 'bin', 'drm', 'sysdev', 'dt'))
        for d in (stats, binp, drm, sysdev, dt):
            d.mkdir()
        (dt / 'rog5,standby-bisect').write_bytes(b'noslpi\0')
        (dt / 'rog5,standby-bisect-base').write_bytes(b'production-dtb-r9\0')
        write_stats = '''
w() { printf 'Count: %s\\nLast Entered At: 0\\nLast Exited At: 0\\nAccumulated Duration: %s\\n' "$2" "$3" >"$S/$1"; }
'''
        (tmp / 'state.sh').write_text(f'''S={stats}
{write_stats}
w ddr 0 0; w cxsd 0 0; w aosd 0 0; w adsp 5 100
: >"$S/apss"
printf 'DDR LPM Stat Name:0xd4\\tcount:0\\tDuration (ticks):0\\nDDR Freq 200Mhz:\\tCP IDX:1\\tcount:3\\tDuration (ticks):10\\n' >"$S/ddr_stats"
echo '{uptime_before} 0' >{tmp}/uptime
echo 'now at 100000000000 nsecs' >{tmp}/timer_list
printf 'State  Time(ms)       Usage      Rejected   Above      Below      S2idle\\nS0     1 1 0 0 0 0\\nS1     1 1 0 0 0 4\\n' >{tmp}/cluster
echo 7 >{tmp}/success
''')
        subprocess.run(['sh', str(tmp / 'state.sh')], check=True)
        (binp / 'id').write_text('#!/bin/sh\necho 0\n')
        (binp / 'rtcwake').write_text('#!/bin/sh\nexit 0\n')
        (binp / 'sleep').write_text('#!/bin/sh\nexit 0\n')
        (binp / 'journalctl').write_text('#!/bin/sh\nexit 0\n')
        # The mocked suspend: counters move, the boot clock runs ahead of the
        # monotonic clock by FROZEN seconds.
        (binp / 'systemctl').write_text(f'''#!/bin/sh
S={stats}
{write_stats}
w ddr {ddr} {ddr * 19200000}; w cxsd {cxsd} {cxsd * 19200000}; w adsp 9 900
printf 'DDR LPM Stat Name:0xd4\\tcount:{lpm}\\tDuration (ticks):{lpm * 1000}\\nDDR Freq 200Mhz:\\tCP IDX:1\\tcount:9\\tDuration (ticks):99\\n' >"$S/ddr_stats"
awk -v f={frozen} 'BEGIN {{ printf "%.2f 0\\n", 102 + f }}' >{tmp}/uptime
{"echo 'now at 102000000000 nsecs'" if timer_after else ': '} >{tmp}/timer_list
printf 'State  Time(ms)       Usage      Rejected   Above      Below      S2idle\\nS0     1 1 0 0 0 0\\nS1     1 {1 + cluster - rejected} {rejected} 0 0 {4 + cluster}\\n' >{tmp}/cluster
echo {7 + success} >{tmp}/success
''')
        for f in binp.iterdir():
            f.chmod(0o755)
        (tmp / 'mem_sleep').write_text('[s2idle] deep\n')
        (tmp / 'dpms').write_text('Off\n')
        (tmp / 'online').write_text('0\n')
        bat = tmp / 'bat'
        bat.mkdir()
        for name, value in (('status', 'Discharging'), ('capacity', '80'), ('charge_counter', '3000000'),
                            ('voltage_now', '4000000'), ('current_now', '-80000'), ('temp', '300')):
            (bat / name).write_text(value + '\n')
        env = dict(os.environ, ROG5_BISECT_TEST_BIN=str(binp), ROG5_BISECT_STATS=str(stats),
                   ROG5_BISECT_BAT=str(bat), ROG5_BISECT_USB=str(tmp / 'online'),
                   ROG5_BISECT_DPMS=str(tmp / 'dpms'), ROG5_BISECT_STAY=str(tmp / 'stay'),
                   ROG5_BISECT_SUCCESS=str(tmp / 'success'), ROG5_BISECT_OUT=str(tmp / 'out'),
                   ROG5_BISECT_MEM_SLEEP=str(tmp / 'mem_sleep'), ROG5_BISECT_UPTIME=str(tmp / 'uptime'),
                   ROG5_BISECT_TIMER_LIST=str(tmp / 'timer_list'), ROG5_BISECT_CLUSTER=str(tmp / 'cluster'),
                   ROG5_BISECT_DRM=str(drm), ROG5_BISECT_SYSDEV=str(sysdev), ROG5_BISECT_DT=str(dt))
        p = subprocess.run(['sh', str(MEASURE), '--secs=60'], capture_output=True, text=True, env=env, timeout=60)
        summary = next((tmp / 'out').glob('*/summary.txt'), None)
        self.assertIsNotNone(summary, p.stdout + p.stderr)
        self.assertFalse((tmp / 'stay').exists())
        return summary.read_text()

    def verdict(self, text):
        return next(line for line in text.splitlines() if line.startswith('VERDICT'))

    def test_a_clean_negative_trial_is_valid(self):
        text = self.run_measure()
        self.assertIn('noslpi on production-dtb-r9', text)
        self.assertIn('timekeeping frozen 58.0 s', text)
        self.assertIn('cluster-sleep-1 s2idle requests +1, PSCI refusals +0', text)
        self.assertTrue(self.verdict(text).startswith('VERDICT negative'), text)

    def test_all_three_counters_make_a_positive(self):
        self.assertTrue(self.verdict(self.run_measure(ddr=3, lpm=3, cxsd=3)).startswith('VERDICT POSITIVE'))
        self.assertTrue(self.verdict(self.run_measure(lpm=3)).startswith('VERDICT PARTIAL'))

    def test_invalid_trials(self):
        self.assertIn('timekeeping frozen only 30.0 s', self.verdict(self.run_measure(frozen=30.0)))
        self.assertIn('never requested its APSS-off state', self.verdict(self.run_measure(cluster=0)))
        text = self.run_measure(cluster=2, rejected=2)
        self.assertIn('WARN PSCI refused cluster-sleep-1 +2 times against +2', text)
        self.assertTrue(self.verdict(text).startswith('VERDICT negative'), text)
        self.assertIn('exactly one successful suspend', self.verdict(self.run_measure(success=2)))
        # No monotonic reading after the suspend: never counted as frozen time.
        self.assertIn('timekeeping frozen only NA s', self.verdict(self.run_measure(timer_after=False)))

    def test_a_slightly_negative_awake_offset_is_fine(self):
        # uptime rounds down and is read first: awake offsets like -0.01.
        text = self.run_measure(uptime_before='99.99')
        self.assertIn('timekeeping frozen 58.0 s', text)
        self.assertTrue(self.verdict(text).startswith('VERDICT negative'), text)


if __name__ == '__main__':
    unittest.main()
