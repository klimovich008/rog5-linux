#!/usr/bin/env python3
"""Exercise the upstream hw1.1 addition without claiming ASUS chip identity."""
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[2]
PATCH = REPO / 'patches/linux/device/ath11k-wcn6851-hw11.patch'
BUILDER = REPO / 'scripts/device/build-native-ath11k-modules.sh'


def selector_block(source):
    probe = source.index('static int ath11k_pci_probe(')
    wcn = source.index('case WCN6855_DEVICE_ID:', probe)
    start = source.index('switch (soc_hw_version_major)', wcn)
    opening = source.index('{', start)
    depth = 1; end = opening + 1
    while depth:
        depth += (source[end] == '{') - (source[end] == '}')
        end += 1
    return source[start:end]


def validate_full_selector(directory):
    """Execute the exact WCN source switch with only MMIO/logging stubbed."""
    source = (directory/'pci.c').read_text()
    header = (directory/'core.h').read_text()
    enum_start = header.index('enum ath11k_hw_rev {')
    enum = header[enum_start:header.index('};', enum_start)+2]
    block = selector_block(source)
    # A sentinel makes the unpatched driver's rejection observable at runtime.
    missing = '' if 'ATH11K_HW_WCN6855_HW11' in enum else '#define ATH11K_HW_WCN6855_HW11 1000\n'
    harness = '''#include <errno.h>
#include <stdio.h>
''' + enum + '\n' + missing + '''
#define dev_err(...) ((void)0)
#define ath11k_dbg(...) ((void)0)
#define ath11k_pcic_read32(ab, addr) fuse
static int choose(unsigned int soc_hw_version_major,
                  unsigned int soc_hw_version_minor, unsigned int fuse) {
 struct { enum ath11k_hw_rev hw_rev; } value, *ab = &value;
 unsigned int sub_version;
 int ret;
''' + block + '''
 return ab->hw_rev;
err_pci_free_region: return ret;
}
static int failures;
static void check(unsigned int major, unsigned int minor, unsigned int fuse, int expected) {
 int got = choose(major, minor, fuse);
 if (got != expected) {
  fprintf(stderr, "selector %u:%x fuse=%x got=%d expected=%d\\n", major, minor, fuse, got, expected);
  failures++;
 }
}
int main(void) {
 for (unsigned int minor=0; minor<256; minor++) {
  check(1, minor, 0, minor==0x10 ? ATH11K_HW_WCN6855_HW11 : -EOPNOTSUPP);
  int expected = -EOPNOTSUPP;
  if (minor==0 || minor==1) expected=ATH11K_HW_WCN6855_HW20;
  if (minor==0x10 || minor==0x11) expected=ATH11K_HW_WCN6855_HW21;
  check(2, minor, 0, expected);
 }
 unsigned int qca2066[] = {0x1019A0E1,0x1019B0E1,0x1019C0E1,0x1019D0E1};
 for (unsigned int i=0; i<4; i++) check(2,0x10,qca2066[i],ATH11K_HW_QCA2066_HW21);
 check(2,0x11,0x001e60e1,ATH11K_HW_QCA6698AQ_HW21);
 check(9,0x10,0,-EOPNOTSUPP);
 return failures ? 1 : 0;
}
'''
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp); (root/'selector.c').write_text(harness)
        subprocess.run(['cc', '-std=c11', '-Wall', '-Wextra', '-Werror',
                        str(root/'selector.c'), '-o', str(root/'selector')], check=True)
        subprocess.run([str(root/'selector')], check=True)
    print('PASS exact-source hw1.1/hw2.x selector, fuse subtypes and unsupported revisions')


def additions():
    files = {}; current = None
    for line in PATCH.read_text().splitlines():
        if line.startswith('diff --git '):
            current = line.split(' b/', 1)[1]
            files[current] = []
        elif current and line.startswith('+') and not line.startswith('+++'):
            files[current].append(line[1:])
        elif current and line.startswith('-') and not line.startswith(('---', '-- ')):
            raise AssertionError('backport changes existing hardware behavior')
    return {path: '\n'.join(lines) for path, lines in files.items()}


class Hw11Test(unittest.TestCase):
    def test_full_selector_skips_the_earlier_qca6390_switch(self):
        source = '''static int ath11k_pci_probe(void) {
case QCA6390_DEVICE_ID:
 switch (soc_hw_version_major) { qca_only(); }
case WCN6855_DEVICE_ID:
 switch (soc_hw_version_major) { switch (minor) { wcn_only(); } }
}'''
        self.assertEqual(selector_block(source),
                         'switch (soc_hw_version_major) { switch (minor) { wcn_only(); } }')

    def test_only_the_five_ath11k_files_are_extended(self):
        files = additions()
        self.assertEqual(set(files), {'drivers/net/wireless/ath/ath11k/' + name
                                    for name in ('core.c', 'core.h', 'mhi.c', 'pci.c', 'pcic.c')})
        subprocess.run(['git', 'apply', '--numstat', str(PATCH)], check=True, stdout=subprocess.PIPE)

    def test_actual_added_case_accepts_only_hw1_minor_0x10(self):
        branch = additions()['drivers/net/wireless/ath/ath11k/pci.c']
        # Test the actual added branch, not a reimplementation of its logic.
        source = '''#include <assert.h>
enum { ATH11K_HW_WCN6855_HW11 = 11 };
static int added_branch(unsigned int major, unsigned int soc_hw_version_minor) {
 struct { int hw_rev; } value = { -1 }, *ab = &value;
 switch (major) {
''' + branch + '''
 default: goto unsupported_wcn6855_soc;
 }
 return ab->hw_rev;
unsupported_wcn6855_soc: return -1;
}
int main(void) {
 for (unsigned int minor = 0; minor < 256; minor++)
  assert(added_branch(1, minor) == (minor == 0x10 ? 11 : -1));
 assert(added_branch(0, 0x10) == -1);
 assert(added_branch(2, 0x10) == -1); /* not handled by the NEW branch */
 return 0;
}
'''
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); (root/'selector.c').write_text(source)
            subprocess.run(['cc', '-std=c11', '-Wall', '-Wextra', '-Werror',
                            str(root/'selector.c'), '-o', str(root/'selector')], check=True)
            subprocess.run([str(root/'selector')], check=True)

    def test_three_vdevs_matching_firmware_path_and_complete_msi_layout(self):
        files = additions()
        core = files['drivers/net/wireless/ath/ath11k/core.c']
        self.assertIn('.dir = "WCN6855/hw1.1"', core)
        self.assertIn('.num_vdevs = 2 + 1,', core)
        self.assertNotIn('.num_vdevs = 4', core)
        vectors = [(int(n), int(start)) for n, start in re.findall(
            r'\.num_vectors = (\d+), \.base_vector = (\d+)',
            files['drivers/net/wireless/ath/ath11k/pcic.c'])]
        self.assertEqual(vectors, [(3, 0), (10, 3), (1, 13), (18, 14)])
        self.assertEqual([i for n, start in vectors for i in range(start, start+n)], list(range(32)))
        self.assertIn('case ATH11K_HW_WCN6855_HW11:', files['drivers/net/wireless/ath/ath11k/mhi.c'])

    def test_missing_finalizer_refuses_before_output_or_compilation(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for name in ('source', 'kit'): (root/name).mkdir()
            (root/'Module.symvers').write_text('')
            result = subprocess.run(['sh', str(BUILDER), str(root/'source'), str(root/'kit'),
                                     str(root/'Module.symvers'), str(root/'out')], capture_output=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn(b'resolve_btfids', result.stderr + result.stdout)
            self.assertFalse((root/'out').exists())

    def test_rebuilt_family_exports_are_not_reused_as_dependencies(self):
        command = next(line for line in BUILDER.read_text().splitlines()
                       if line.startswith("awk '$3 !~"))
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            rows = ''.join('0x00000000 symbol_' + name + '\tdrivers/wifi/' + name + '\tEXPORT_SYMBOL_GPL\n'
                           for name in ('ath', 'ath11k', 'ath11k_pci', 'ath11k_ahb', 'mac80211'))
            (root/'base').write_text(rows)
            subprocess.run(['sh', '-eu', '-c', 'base_symbols=$1; output=$2; ' + command,
                            'test', str(root/'base'), str(root)], check=True)
            self.assertEqual((root/'dependencies.symvers').read_text(), rows.splitlines(keepends=True)[-1])

    def test_actual_make_command_serializes_btf_not_compilation(self):
        lines = BUILDER.read_text().splitlines()
        start = next(i for i, line in enumerate(lines) if line.startswith('make -C '))
        end = start
        while lines[end].endswith('\\'): end += 1
        command = '\n'.join(lines[start:end+1])
        result = subprocess.run(['sh', '-eu', '-c',
            'source_dir=source; kernel_kit=kit; ath=ath; output=out; jobs=4; '
            'make() { printf "%s\\n" "$@"; }; ' + command], check=True, capture_output=True, text=True)
        arguments = result.stdout.splitlines()
        self.assertIn('JOBS=1', arguments)
        self.assertEqual(arguments[arguments.index('-j')+1], '4')


if __name__ == '__main__':
    if len(sys.argv) == 3 and sys.argv[1] == '--selector-source':
        validate_full_selector(Path(sys.argv[2]))
    else:
        unittest.main()
