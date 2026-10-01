#!/usr/bin/env python3
"""Offline tests of compose-memslim-dtb.sh.

A synthetic d10-shaped tree covers the composition logic and every refusal.
With the private production DTB d10 present (or ROG5_MEMSLIM_D10_DTB) the
real bytes are composed too, and with a C compiler, OpenSSL and zlib the
loader's own DTB check (verify_fdt of tools/recovery_control/rog5-bundle-verify.c)
must accept every output.
"""
import hashlib
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
TOOL = HERE / 'compose-memslim-dtb.sh'
D10 = Path(os.environ.get('ROG5_MEMSLIM_D10_DTB', Path.home() / '.local/state/rog5-production-boot-20260923/'
                          'platform-dp4-btmtc-memx-l11off-dtb-d10/board.dtb'))
D10_SHA = 'dda8b280da1ee6a4d4c85c663008551757f9766b278dc93dfeba0b875114788e'
MiB = 1 << 20

RESERVED = [  # name, address, size, no-map, phandle label
    ('memory@34a000000', 0x34a000000, 0x4000000, True, None),
    ('memory@edc00000', 0xedc00000, 0x12000000, False, None),
    ('memory@d8000000', 0xd8000000, 0x800000, True, None),
    ('memory@cbc00000', 0xcbc00000, 0x4400000, False, None),
    ('memory@80000000', 0x80000000, 0x600000, True, 'hyp'),
    ('memory@80c00000', 0x80c00000, 0x4600000, True, 'tz'),
    ('memory@85200000', 0x85200000, 0x500000, True, 'cam'),
    ('memory@85700000', 0x85700000, 0x500000, True, 'video'),
    ('memory@85c00000', 0x85c00000, 0x500000, True, 'cvp'),
    ('memory@86100000', 0x86100000, 0x2100000, True, 'adsp'),
    ('memory@88200000', 0x88200000, 0x1500000, True, 'slpi'),
    ('memory@89700000', 0x89700000, 0x1e00000, True, 'cdsp'),
    ('memory@8b500000', 0x8b500000, 0x10000, True, 'ipa'),
    ('memory@8b510000', 0x8b510000, 0xa000, True, 'gsi'),
    ('memory@8b51a000', 0x8b51a000, 0x2000, True, 'gpu'),
    ('memory@8b600000', 0x8b600000, 0x100000, True, 'spss'),
    ('memory@8b800000', 0x8b800000, 0x10000000, True, 'mpss'),
    ('memory@9b800000', 0x9b800000, 0x400000, False, 'ramoops'),
    ('memory@d0000000', 0xd0000000, 0x800000, True, 'hypres'),
    ('memory@d0800000', 0xd0800000, 0x76f7000, True, 'tvm'),
    ('memory@d7ef7000', 0xd7ef7000, 0x9000, True, 'qrtr'),
    ('memory@d7f00000', 0xd7f00000, 0x80000, True, 'chan0'),
    ('memory@d7f80000', 0xd7f80000, 0x80000, True, 'chan1'),
    ('memory@d8800000', 0xd8800000, 0xa800000, True, 'removed'),
    ('memory@e5000000', 0xe5000000, 0x2300000, True, 'splash'),
    ('memory@e7400000', 0xe7400000, 0x100000, True, 'dfps'),
]


def fixture_dts(modem_status='disabled', tvm_user=None):
    nodes = []
    for name, addr, size, nomap, label in RESERVED:
        body = f'reg = <0x{addr >> 32:x} 0x{addr & 0xffffffff:x} 0x0 0x{size:x}>;'
        if nomap:
            body += ' no-map;'
        if name == 'memory@9b800000':
            body += ' compatible = "ramoops"; status = "okay";'
        nodes.append(f'\t\t{label + ": " if label else ""}{name} {{ {body} }};')
    reserved = '\n'.join(nodes)
    user = ''
    if tvm_user:
        user = f'\t\tvm@1 {{ compatible = "test,vm"; memory-region = <&tvm>; status = "{tvm_user}"; }};\n'
    return f'''/dts-v1/;
/ {{
	#address-cells = <2>; #size-cells = <2>;
	model = "ASUS ROG Phone 5"; compatible = "asus,rog-phone5", "qcom,sm8350";
	memory@80000000 {{ device_type = "memory"; reg = <0x0 0x80000000 0x0 0x37100000>; }};
	reserved-memory {{
		#address-cells = <2>; #size-cells = <2>; ranges;
{reserved}
	}};
	soc@0 {{
		#address-cells = <2>; #size-cells = <2>; ranges;
		remoteproc@4080000 {{ compatible = "qcom,sm8350-mpss-pas"; memory-region = <&mpss>; status = "{modem_status}"; }};
		remoteproc@3000000 {{ compatible = "qcom,sm8350-adsp-pas"; memory-region = <&adsp>; status = "okay"; }};
		remoteproc@5c00000 {{ compatible = "qcom,sm8350-slpi-pas"; memory-region = <&slpi>; }};
{user}	}};
}};
'''


def fdtget(dtb, node, prop, kind='s'):
    r = subprocess.run(['fdtget', '-t', kind, str(dtb), node, prop], capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else None


class ComposeMemslimTest(unittest.TestCase):
    def setUp(self):
        self.t = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.t)

    def build(self, **kw):
        src = self.t / 'base.dts'
        src.write_text(fixture_dts(**kw))
        dtb = self.t / f'base-{len(list(self.t.iterdir()))}.dtb'
        subprocess.run(['dtc', '-q', '-@', '-I', 'dts', '-O', 'dtb', '-o', str(dtb), str(src)], check=True)
        return dtb

    def compose(self, base, parts, rc=0, sha=None, out=None):
        out = out or self.t / f'out-{parts.replace(",", "_")}-{len(list(self.t.iterdir()))}.dtb'
        env = dict(os.environ, EXPECTED_MEMSLIM_BASE_SHA256=sha or hashlib.sha256(base.read_bytes()).hexdigest())
        r = subprocess.run(['sh', str(TOOL), str(base), str(out), parts], env=env, capture_output=True, text=True,
                           timeout=60)
        self.assertEqual(r.returncode, rc, r.stdout + r.stderr)
        if rc == 0:
            self.assertEqual(r.stdout.strip(), hashlib.sha256(out.read_bytes()).hexdigest())
        return out, r

    def reserved_bytes(self, dtb):
        """Bytes Linux reserves: active children only (status okay or absent)."""
        names = subprocess.run(['fdtget', '-l', str(dtb), '/reserved-memory'], capture_output=True,
                               text=True, check=True).stdout.split()
        total = 0
        for n in names:
            node = f'/reserved-memory/{n}'
            if (fdtget(dtb, node, 'status') or 'okay') != 'okay':
                continue
            reg = [int(x, 16) for x in fdtget(dtb, node, 'reg', 'x').split()]
            total += (reg[2] << 32) | reg[3]
        return total

    def test_each_part_frees_its_ranges(self):
        base = self.build()
        before = self.reserved_bytes(base)
        expect = {'stockcma': 196 * MiB, 'pil': 266 * MiB, 'ionpool': 128 * MiB}
        for part, freed in expect.items():
            out, _ = self.compose(base, part)
            self.assertEqual(before - self.reserved_bytes(out), freed, part)
            self.assertEqual(fdtget(out, '/', 'rog5,memslim'), part)
            self.assertEqual(fdtget(out, '/', 'rog5,memslim-base'), 'production-dtb-d10')
        out, _ = self.compose(base, 'ionpool,stockcma,pil')
        self.assertEqual(before - self.reserved_bytes(out), 590 * MiB)

    def test_node_level_changes(self):
        out, _ = self.compose(self.build(), 'stockcma,pil,ionpool')
        rm = '/reserved-memory'
        self.assertIsNone(fdtget(out, f'{rm}/memory@cbc00000', 'reg', 'x'))
        self.assertIsNone(fdtget(out, f'{rm}/memory@edc00000', 'reg', 'x'))
        self.assertEqual(fdtget(out, f'{rm}/memory@ef800000', 'reg', 'x'), '0 ef800000 0 4000000')
        self.assertEqual(fdtget(out, f'{rm}/memory@f9c00000', 'reg', 'x'), '0 f9c00000 0 6000000')
        for n in ('memory@d0000000', 'memory@d0800000', 'memory@d7ef7000', 'memory@d7f00000', 'memory@d7f80000',
                  'memory@8b800000', 'memory@85200000', 'memory@85c00000'):
            self.assertEqual(fdtget(out, f'{rm}/{n}', 'status'), 'disabled', n)
            self.assertIsNotNone(fdtget(out, f'{rm}/{n}', 'phandle', 'x'), n)   # references stay valid
        for n in ('memory@34a000000', 'memory@d8000000', 'memory@d8800000', 'memory@80c00000', 'memory@85700000',
                  'memory@86100000', 'memory@88200000', 'memory@89700000', 'memory@8b51a000', 'memory@8b600000',
                  'memory@e5000000'):
            self.assertIn(fdtget(out, f'{rm}/{n}', 'status') or 'okay', ('okay',), n)
        for n in ('memory@ef800000', 'memory@f9c00000'):   # mapped like the span they replace
            self.assertNotEqual(subprocess.run(['fdtget', str(out), f'{rm}/{n}', 'no-map'],
                                               capture_output=True).returncode, 0, n)

    def test_refusals(self):
        base = self.build()
        self.compose(base, 'pil', rc=1, sha='0' * 64)
        _, r = self.compose(base, 'bogus', rc=1)
        self.assertIn('unknown part', r.stderr)
        _, r = self.compose(base, 'pil,pil', rc=1)
        self.assertIn('repeated part', r.stderr)
        out = self.t / 'exists.dtb'
        out.write_bytes(b'x')
        _, r = self.compose(base, 'pil', rc=1, out=out)
        self.assertIn('output exists', r.stderr)
        _, r = self.compose(self.build(modem_status='okay'), 'pil', rc=1)
        self.assertIn('not the disabled MPSS', r.stderr)
        # an enabled user of the trusted-VM region blocks stockcma; a disabled one does not
        _, r = self.compose(self.build(tvm_user='okay'), 'stockcma', rc=1)
        self.assertIn('is used by /soc@0/vm@1', r.stderr)
        _, r = self.compose(self.build(tvm_user='disabled'), 'stockcma', rc=1)
        self.assertIn('is used by /soc@0/vm@1', r.stderr)   # only listed users are allowed
        # a changed span is refused instead of being reshaped
        dts = fixture_dts().replace('0xedc00000 0x0 0x12000000', '0xedc00000 0x0 0x11000000')
        src = self.t / 'odd.dts'
        src.write_text(dts)
        odd = self.t / 'odd.dtb'
        subprocess.run(['dtc', '-q', '-@', '-I', 'dts', '-O', 'dtb', '-o', str(odd), str(src)], check=True)
        _, r = self.compose(odd, 'ionpool', rc=1)
        self.assertIn('memory@edc00000 reg is not', r.stderr)
        # memx must survive
        dts = fixture_dts().replace('0x4a000000 0x0 0x4000000>; no-map;', '0x4a000000 0x0 0x4000000>;')
        src.write_text(dts)
        subprocess.run(['dtc', '-q', '-@', '-I', 'dts', '-O', 'dtb', '-o', str(odd), str(src)], check=True)
        self.compose(odd, 'stockcma', rc=1)


@unittest.skipUnless(D10.is_file() and hashlib.sha256(D10.read_bytes()).hexdigest() == D10_SHA,
                     'requires the private production DTB d10')
class ProductionD10Test(unittest.TestCase):
    def test_d10_parts_compose_and_pass_the_loader_check(self):
        t = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, t)
        verifier = None
        if shutil.which('cc'):
            src = t / 'vfdt.c'
            src.write_text('#define main rog5_verifier_main\n#include "rog5-bundle-verify.c"\n#undef main\n'
                           'int main(int c, char **v) { static unsigned char b[1 << 21]; FILE *f = fopen(v[1], "rb");'
                           ' size_t n = fread(b, 1, sizeof b, f); verify_fdt(b, n); puts("ok"); return 0; }\n')
            r = subprocess.run(['cc', '-w', '-I', str(REPO / 'tools/recovery_control'), '-o', str(t / 'vfdt'),
                                str(src), '-lcrypto', '-lz'], capture_output=True, text=True)
            verifier = t / 'vfdt' if r.returncode == 0 else None
        if verifier is None:
            self.skipTest('requires cc with OpenSSL and zlib headers for the loader check')
        self.assertEqual(subprocess.run([str(verifier), str(D10)], capture_output=True, text=True).stdout.strip(), 'ok')
        for parts in ('stockcma', 'pil', 'ionpool', 'stockcma,pil,ionpool'):
            out = t / f'{parts}.dtb'
            subprocess.run(['sh', str(TOOL), str(D10), str(out), parts], check=True, capture_output=True)
            r = subprocess.run([str(verifier), str(out)], capture_output=True, text=True)
            self.assertEqual(r.stdout.strip(), 'ok', parts + r.stderr)


if __name__ == '__main__':
    unittest.main()
