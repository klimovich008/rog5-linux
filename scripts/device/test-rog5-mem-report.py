#!/usr/bin/env python3
"""Offline tests of rog5-mem-report against a fixture /proc, /sys tree."""
import importlib.machinery
import importlib.util
import json
import os
import platform
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
TOOL = HERE / 'rog5-mem-report'

MEMINFO = """MemTotal:       10866028 kB
MemFree:         7617312 kB
MemAvailable:    8398940 kB
Cached:          1226996 kB
Shmem:            388696 kB
AnonPages:       1523540 kB
AnonHugePages:    903168 kB
Slab:             153184 kB
PageTables:        21684 kB
SwapTotal:       5432828 kB
SwapFree:        5332828 kB
CmaTotal:          32768 kB
"""
DMESG = """[    0.000000] OF: reserved mem: 0x000000008b800000..0x000000009b7fffff (262144 KiB) nomap non-reusable memory@8b800000
[    0.000000] cma: Reserved 32 MiB at 0x00000000ebc00000
[    0.000000] software IO TLB: mapped [mem 0x00000000e7c00000-0x00000000ebc00000] (64MB)
[    0.012893] Memory: 10790452K/12436480K available (16192K kernel code, 4516K rwdata, 9332K rodata, 1344K init, 575K bss, 1606672K reserved, 32768K cma-reserved)
"""


def reg(addr, size):
    return struct.pack('>IIII', addr >> 32, addr & 0xffffffff, size >> 32, size & 0xffffffff)


def build_fixture(t, dp_fifo=True):
    def w(rel, data):
        p = t / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        (p.write_bytes if isinstance(data, bytes) else p.write_text)(data)
    w('proc/meminfo', MEMINFO)
    w('proc/vmstat', 'pswpin 3\npswpout 9\npgmajfault 100\nthp_underused_split_page 2\n')
    w('proc/pressure/memory', 'some avg10=0.00 avg60=0.00 avg300=0.00 total=84124\n'
      'full avg10=0.00 avg60=0.00 avg300=0.00 total=80588\n')
    w('proc/cmdline', 'console=ttyMSM0 rog5.bundle=main-k111-d10-261001b\n')
    w('proc/uptime', '683.2 5000.1\n')
    w('proc/sys/kernel/osrelease', '7.2.7-rog5-k111\n')
    w('proc/sys/vm/swappiness', '100\n')
    w('proc/slabinfo', 'slabinfo - version: 2.1\n# name <active_objs> <num_objs> <objsize> ...\n'
      'ext4_inode_cache 57810 57810 1064 30 8\ndentry 212289 212289 192 21 1\n')
    w('proc/vmallocinfo', '0x1-0x2 110657536 __ioremap_prot+0x88/0x10c phys=0x1 ioremap\n'
      '0x3-0x4 4096 __ioremap_prot+0x88/0x10c phys=0x2 ioremap\n0x5-0x6 8192 copy_process+0x1b8/0xe98 pages=1\n')
    w('proc/modules', 'msm 1359872 3 - Live 0x0\nath11k 413696 1 ath11k_pci, Live 0x0\n')
    w('proc/self/mounts', '')
    w('dmesg.txt', DMESG)
    rm = 'sys/firmware/devicetree/base/reserved-memory'
    w(f'{rm}/memory@8b800000/reg', reg(0x8b800000, 0x10000000))
    w(f'{rm}/memory@8b800000/no-map', b'')
    w(f'{rm}/memory@edc00000/reg', reg(0xedc00000, 0x12000000))
    w(f'{rm}/memory@d0800000/reg', reg(0xd0800000, 0x76f7000))
    w(f'{rm}/memory@d0800000/no-map', b'')
    w(f'{rm}/memory@d0800000/status', b'disabled\0')
    w('sys/kernel/debug/swiotlb/io_tlb_nslabs', '32768\n')
    w('sys/kernel/debug/swiotlb/io_tlb_used', '2\n')
    w('sys/kernel/debug/swiotlb/io_tlb_used_hiwater', '4\n')
    w('sys/block/zram0/comp_algorithm', 'lz4 [zstd]\n')
    w('sys/block/zram0/disksize', '5563219968\n')
    w('sys/block/zram0/mm_stat', '300000000 100000000 110000000 0 120000000 10 0 5 5\n')
    w('sys/fs/cgroup/user.slice/memory.current', '9875931136\n')
    w('sys/kernel/mm/transparent_hugepage/enabled', 'always [madvise] never\n')
    w('sys/kernel/debug/dri/0/name', 'msm dev=3d00000.gpu unique=3d00000.gpu\n')
    w('sys/kernel/debug/dri/0/gem', 'junk\nTotal:      399 objects, 317456384 bytes\n'
      'Active:      22 objects,  25284608 bytes\nResident:   398 objects, 313262080 bytes\n')
    w('sys/kernel/debug/dri/128/name', 'msm dev=3d00000.gpu unique=3d00000.gpu\n')
    w('sys/kernel/debug/dri/128/gem', 'Total:      399 objects, 317456384 bytes\n')
    w('sys/kernel/debug/dri/1/name', 'msm-kms dev=ae01000.display-controller unique=ae01000.display-controller\n')
    w('sys/kernel/debug/dri/1/gem', 'Total:       21 objects, 125341696 bytes\n')
    if dp_fifo:
        # Reading a DP connector's debugfs file has hung the DP controller: a
        # FIFO here blocks forever if the tool ever opens it.
        os.mkfifo(t / 'sys/kernel/debug/dri/1/DP-1')
    w('sys/kernel/debug/dma_buf/bufinfo', 'x\n\nTotal 18 objects, 66961408 bytes\n')
    for pid, comm, pss, huge, unit in ((100, 'gnome-shell', 238168, 16384, 'org.gnome.Shell@user.service'),
                                       (200, 'steamwebhelper', 265140, 36864, 'org.gnome.Shell@user.service'),
                                       (300, 'tailscaled', 70918, 26624, 'tailscaled.service')):
        w(f'proc/{pid}/comm', comm + '\n')
        w(f'proc/{pid}/cgroup', f'0::/user.slice/user-1000.slice/{unit}\n')
        w(f'proc/{pid}/smaps_rollup', f'00400000-ffff [rollup]\nRss: {pss + 1000} kB\nPss: {pss} kB\n'
          f'Pss_Anon: {pss - 500} kB\nPss_File: 400 kB\nPss_Shmem: 100 kB\nSwapPss: 10 kB\nAnonHugePages: {huge} kB\n')
        w(f'proc/{pid}/environ', b'HOME=/home/phone\0GLIBC_TUNABLES=glibc.malloc.hugetlb=0\0')
    w('proc/100/fdinfo/7', 'pos: 0\ndrm-driver:\tmsm\ndrm-client-id:\t13\ndrm-total-memory:\t250664 KiB\n'
      'drm-resident-memory:\t250664 KiB\ndrm-shared-memory:\t65376 KiB\n')
    w('proc/200/fdinfo/9', 'pos: 0\ndrm-driver:\tmsm\ndrm-client-id:\t13\ndrm-total-memory:\t250664 KiB\n')
    w('proc/300/fdinfo/1', 'pos: 0\nflags: 02\n')
    # kpageflags for PFNs 0x8b800..0x8b804: buddy, in use, buddy, nopage, reserved
    flags = [1 << 10, 1 << 5, 1 << 10, 1 << 20, 1 << 32]
    kp = bytearray(0x8b800 * 8) + b''.join(struct.pack('<Q', f) for f in flags)
    w('proc/kpageflags', bytes(kp))


def load_module():
    loader = importlib.machinery.SourceFileLoader('rog5_mem_report', str(TOOL))
    spec = importlib.util.spec_from_loader('rog5_mem_report', loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


class MemReportTest(unittest.TestCase):
    def setUp(self):
        self.t = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.t)
        build_fixture(self.t)
        self.env = dict(os.environ, ROG5_MEMREPORT_ROOT=str(self.t))

    def run_tool(self, *args, rc=0):
        r = subprocess.run([sys.executable, str(TOOL), *args], env=self.env, capture_output=True, text=True,
                           timeout=20)
        self.assertEqual(r.returncode, rc, r.stdout + r.stderr)
        return r

    def snapshot(self, label='a', *extra):
        out = self.t / f'{label}.json'
        self.run_tool('snapshot', '--label', label, '--out', str(out), *extra)
        return json.loads(out.read_text()), out

    def test_snapshot_contents(self):
        s, _ = self.snapshot('base', '--ranges', '0x8b800000-0x8b804fff')
        self.assertEqual(s['bundle'], 'main-k111-d10-261001b')
        self.assertEqual(s['boot_memory']['total_kb'], 12436480)
        self.assertEqual(s['boot_memory']['reserved_kb'], 1606672)
        self.assertEqual(s['boot_memory']['swiotlb_mb'], 64)
        rm = s['reserved_memory']
        self.assertEqual(rm['active_nomap_bytes'], 0x10000000)            # the disabled node does not count
        self.assertEqual(rm['active_map_bytes'], 0x12000000)
        self.assertEqual({n['name']: n['status'] for n in rm['nodes']}['memory@d0800000'], 'disabled')
        self.assertEqual(s['swiotlb'], {'io_tlb_nslabs': 32768, 'io_tlb_used': 2, 'io_tlb_used_hiwater': 4,
                                        'pool_bytes': 64 << 20})
        self.assertEqual(s['zram']['algorithm'], 'zstd')
        self.assertEqual(s['zram']['ratio'], 3.0)
        self.assertEqual(s['slab_top'][0], {'cache': 'ext4_inode_cache', 'bytes': 57810 * 1064})
        self.assertEqual(s['vmalloc_top'][0], {'caller': '__ioremap_prot', 'bytes': 110657536 + 4096})
        self.assertEqual(s['modules_bytes'], 1359872 + 413696)
        gem = s['gpu']['gem']
        self.assertEqual(sorted(gem), ['msm-kms:ae01000.display-controller', 'msm:3d00000.gpu'])  # 128 deduplicated
        self.assertEqual(gem['msm:3d00000.gpu']['total']['bytes'], 317456384)
        self.assertEqual(s['gpu']['dma_buf_bytes'], 66961408)
        self.assertEqual(s['gpu']['clients'], {'gnome-shell': {'total': 250664 * 1024, 'resident': 250664 * 1024,
                                                               'shared': 65376 * 1024}})   # client 13 once
        self.assertEqual(s['processes_total_pss_kb'], 238168 + 265140 + 70918)
        self.assertEqual(s['processes_top'][0]['comm'], 'steamwebhelper')
        self.assertEqual(s['by_unit']['org.gnome.Shell@user.service']['count'], 2)
        self.assertEqual(s['range_use'], [{'range': '0x8b800000-0x8b804fff', 'pages': 5, 'read': 5,
                                           'free_buddy': 2, 'nopage': 1, 'reserved': 1, 'in_use': 1}])
        self.assertEqual(s['session'], {'gnome-shell': 1, 'steamwebhelper': 1})

    def test_compare(self):
        _, a = self.snapshot('before')
        (self.t / 'proc/meminfo').write_text(MEMINFO.replace('903168', '103168').replace('8398940', '9198940'))
        (self.t / 'proc/200/smaps_rollup').write_text('Rss: 100 kB\nPss: 65140 kB\nAnonHugePages: 0 kB\n')
        _, b = self.snapshot('after')
        out = self.run_tool('compare', str(a), str(b)).stdout
        self.assertRegex(out, r'AnonHugePages MiB\s+882\.0\s+100\.8\s+-781\.2')
        self.assertRegex(out, r'MemAvailable MiB\s+8202\.1\s+8983\.[34]\s+\+781\.2')
        self.assertRegex(out, r'steamwebhelper\s+-195\.3')

    def test_bad_ranges_and_pressure_guard(self):
        self.run_tool('snapshot', '--ranges', '0x1000-0x1fff,0x3000-0x2000', rc=1)
        r = self.run_tool('pressure', rc=2)
        self.assertIn('--yes', r.stderr)

    def test_pressure_small_run(self):
        out = self.t / 'p.json'
        self.run_tool('pressure', '--yes', '--target-mib', '8', '--step-mib', '4', '--floor-mib', '0',
                      '--ranges', '0x8b800000-0x9b7fffff', '--exec-sample', '0', '--out', str(out))
        p = json.loads(out.read_text())
        self.assertEqual(p['allocated_mib'], 8)
        self.assertEqual(len(p['steps']), 2)
        self.assertIn('pswpout', p['delta'])
        self.assertIn('0x8b800000-0x9b7fffff', p['range_hits'])
        self.assertEqual(p['range_write_errors'], [])

    def test_perf_light(self):
        out = self.t / 'perf.json'
        self.run_tool('perf', '--runs', '2', '--cmd', 'true', '--fault-mib', '8', '--out', str(out))
        p = json.loads(out.read_text())
        self.assertEqual(p['startup'][0]['cmd'], 'true')
        self.assertEqual([f['madvise_hugepage'] for f in p['fault']], [False, True])
        self.assertEqual(p['glibc_tunables']['gnome-shell'], 'glibc.malloc.hugetlb=0')

    def test_parse_ranges_unit(self):
        mod = load_module()
        self.assertEqual(mod.parse_ranges('0xcbc00000-0xd7ffffff,8b800000-9b7fffff'),
                         [(0xcbc00000, 0xd7ffffff), (0x8b800000, 0x9b7fffff)])
        with self.assertRaises(ValueError):
            mod.parse_ranges('0x1000-0x1ffe')

    def test_exec_pages_child_outcomes(self):
        mod = load_module()
        import mmap
        buf = mmap.mmap(-1, 4 * mod.PAGE)
        buf[0] = 1
        # a PFN that does not match (non-root pagemap reads 0): "moved", never executed
        self.assertEqual(mod.exec_pages([(buf, 0, 0x1234000)]), [{'phys': '0x1234000', 'result': 'moved'}])

        class Broken:          # the child cannot even look the page up: error, not silence
            def __setitem__(self, k, v):
                pass
        res = mod.exec_pages([(Broken(), 0, 0x5000), (buf, 0, 0x6000)])
        self.assertEqual(res[0]['result'], 'not run')
        self.assertEqual(res[-1], {'phys': None, 'result': 'error (exit 4)'})

    def test_supervised_reports_a_killed_probe(self):
        mod = load_module()
        import argparse
        import signal as sig
        res = mod.supervised(lambda a: os.kill(os.getpid(), sig.SIGBUS), argparse.Namespace(label='x'))
        self.assertEqual(res['error'], f'probe process killed by signal {int(sig.SIGBUS)}')
        self.assertEqual(mod.supervised(lambda a: {'ok': 1}, argparse.Namespace(label='x')), {'ok': 1})
        self.assertIn('ZeroDivisionError', mod.supervised(lambda a: 1 / 0, argparse.Namespace())['error'])

    def test_pressure_range_without_hits_is_inconclusive(self):
        out = self.t / 'p.json'
        self.run_tool('pressure', '--yes', '--target-mib', '4', '--step-mib', '4', '--floor-mib', '0',
                      '--ranges', '0x8b800000-0x9b7fffff', '--out', str(out))
        p = json.loads(out.read_text())
        self.assertEqual(p['range_verdict'], {'0x8b800000-0x9b7fffff': 'inconclusive'})
        self.assertIn('zram_exercised', p)

    @unittest.skipUnless(platform.machine() == 'aarch64' and os.geteuid() == 0,
                         'executes an aarch64 RET on a real PFN (root on the phone)')
    def test_exec_pages_native(self):
        mod = load_module()
        import ctypes
        import mmap
        buf = mmap.mmap(-1, mod.PAGE)
        buf[0] = 1
        pfn = mod.pagemap_pfns(ctypes.addressof(ctypes.c_char.from_buffer(buf)), mod.PAGE)[0]
        self.assertEqual(mod.exec_pages([(buf, 0, pfn * mod.PAGE)])[0]['result'], 'ok')

if __name__ == '__main__':
    unittest.main()
