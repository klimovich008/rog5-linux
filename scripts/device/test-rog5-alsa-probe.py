#!/usr/bin/env python3
"""Tests for tools/alsa_probe/rog5-alsa-probe.c: get/set accept only BOOLEAN,
INTEGER and ENUMERATED controls of at most 128 values, and set refuses values
outside the control's range.

The probe is freestanding AArch64 code; ROG5_ALSA_PROBE_HOST_TEST builds it
for the host with fake syscalls (a one-control card whose type and count the
test picks), under AddressSanitizer when the compiler has it. GPT-6.1-Sol
audit 2026-10-02: "set" filled long integer[count] for any type, so a BYTES
control of 512 values wrote 4096 bytes into a 1024-byte union.
"""
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[2]
PROBE = REPO/'tools/alsa_probe/rog5-alsa-probe.c'

HARNESS = r'''
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#define ROG5_ALSA_PROBE_HOST_TEST 1
#include "rog5-alsa-probe.c"

static int fake_type, fake_count, fake_info_rc, fake_fail_call, info_calls, writes, reads;
static long written[4];

long sys4(long n, long a, long b, long c, long d)
{
	(void)a; (void)c; (void)d;
	if (n != NR_OPENAT)
		return -38;
	return strcmp((const char *)b, "/dev/kmsg") ? 3 : -2;
}

long sys6(long n, long a, long b, long c, long d, long e, long f)
{
	(void)n; (void)a; (void)b; (void)c; (void)d; (void)e; (void)f;
	return -38;
}

long sys3(long n, long a, long b, long c)
{
	(void)a;
	if (n == NR_WRITE)
		return (long)fwrite((const void *)b, 1, (size_t)c, stderr);
	if (n == NR_NANOSLEEP)
		return 0;
	if (n != NR_IOCTL)
		return -38;
	if ((unsigned long)b == CTL_LIST) {
		struct elem_list *l = (struct elem_list *)c;

		l->count = 1;
		l->used = l->offset ? 0 : 1;
		if (l->used) {
			memset(l->pids, 0, sizeof(*l->pids));
			l->pids[0].numid = 7;
			strcpy((char *)l->pids[0].name, "Test Control");
		}
		return 0;
	}
	if ((unsigned long)b == CTL_INFO) {
		struct elem_info *i = (struct elem_info *)c;

		if (fake_info_rc)
			return fake_info_rc;
		if (++info_calls == fake_fail_call)
			return -5;
		i->type = fake_type;
		i->count = (unsigned int)fake_count;
		if (fake_type == TYPE_INTEGER) {
			i->value.integer.min = 0;
			i->value.integer.max = 457;
		} else if (fake_type == TYPE_ENUMERATED) {
			static const char *const names[] = { "Zero", "ASP_RX1", "DSP_TX1" };
			unsigned int item = i->value.enumerated.item;

			i->value.enumerated.items = 3;
			strcpy(i->value.enumerated.name, names[item < 3 ? item : 0]);
		}
		return 0;
	}
	if ((unsigned long)b == CTL_READ) {
		reads++;
		return 0;
	}
	if ((unsigned long)b == CTL_WRITE) {
		const struct elem_value *v = (const struct elem_value *)c;

		writes++;
		for (int k = 0; k < 4; k++)
			written[k] = fake_type == TYPE_ENUMERATED ? (long)v->value.enumerated[k] : v->value.integer[k];
		return 0;
	}
	return -25;
}

/* harness TYPE COUNT INFO_RC FAIL_CALL probe-arguments...: every CTL_INFO
 * returns INFO_RC when it is not 0, CTL_INFO call number FAIL_CALL (from 1)
 * returns -EIO */
int main(int argc, char **argv)
{
	int rc;

	fake_type = atoi(argv[1]);
	fake_count = atoi(argv[2]);
	fake_info_rc = atoi(argv[3]);
	fake_fail_call = atoi(argv[4]);
	argv[4] = "rog5-alsa-probe";
	rc = run(argc - 4, argv + 4);
	printf("rc=%d writes=%d reads=%d values=%ld,%ld,%ld,%ld\n", rc, writes, reads,
	       written[0], written[1], written[2], written[3]);
	return 0;
}
'''

BOOLEAN, INTEGER, ENUMERATED, BYTES, IEC958, INTEGER64 = 1, 2, 3, 4, 5, 6


def compiler():
    for cc in ('cc', 'gcc', 'clang'):
        if shutil.which(cc):
            return cc
    return None


@unittest.skipUnless(compiler(), 'no C compiler (cc, gcc or clang) on this host')
class Probe(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dir = Path(tempfile.mkdtemp(prefix='rog5-alsa-probe-'))
        shutil.copy(PROBE, cls.dir/'rog5-alsa-probe.c')
        (cls.dir/'harness.c').write_text(HARNESS)
        cls.binary = cls.dir/'harness'
        base = [compiler(), '-std=gnu11', '-O1', '-g', '-Wall', '-Wno-unused-function',
                '-o', str(cls.binary), str(cls.dir/'harness.c')]
        sanitized = base[:2] + ['-fsanitize=address,undefined', '-fno-sanitize-recover=all'] + base[2:]
        cls.sanitized = subprocess.run(sanitized, capture_output=True, text=True).returncode == 0
        if not cls.sanitized:
            build = subprocess.run(base, capture_output=True, text=True)
            if build.returncode:
                raise AssertionError(build.stderr)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.dir)

    def probe(self, kind, count, *args, info_rc=0, fail_call=0):
        result = subprocess.run([str(self.binary), str(kind), str(count), str(info_rc), str(fail_call), *args],
                                capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)  # a sanitizer report exits non-zero
        fields = dict(item.split('=', 1) for item in result.stdout.split())
        return int(fields['rc']), int(fields['writes']), int(fields['reads']), \
            [int(v) for v in fields['values'].split(',')], result.stderr

    def test_bytes_and_other_layouts_are_refused(self):
        for kind, count in ((BYTES, 512), (BYTES, 4), (IEC958, 1), (INTEGER64, 64)):
            rc, writes, reads, values, err = self.probe(kind, count, 'set', '0', 'Test Control', '1')
            self.assertEqual((rc, writes), (4, 0), (kind, count))
            self.assertIn(f'unsupported control Test Control type={kind} count={count}', err)
            rc, writes, reads, values, err = self.probe(kind, count, 'get', '0', 'Test Control')
            self.assertEqual((rc, reads), (4, 0), (kind, count))

    def test_too_many_or_no_values_are_refused(self):
        for kind in (BOOLEAN, INTEGER, ENUMERATED):
            for count in (0, 129, 512):
                rc, writes, reads, values, err = self.probe(kind, count, 'set', '0', 'Test Control', '1')
                self.assertEqual((rc, writes), (4, 0), (kind, count))

    def test_failed_info_is_refused(self):
        rc, writes, reads, values, err = self.probe(INTEGER, 1, 'set', '0', 'Test Control', '1', info_rc=-5)
        self.assertEqual((rc, writes), (4, 0))
        self.assertIn('no info for Test Control', err)

    def test_integer_range(self):
        self.assertEqual(self.probe(INTEGER, 2, 'set', '0', 'Test Control', '361')[:4], (0, 1, 0, [361, 361, 0, 0]))
        for value in ('458', '-1', 'x'):
            self.assertEqual(self.probe(INTEGER, 1, 'set', '0', 'Test Control', value)[:2], (4, 0), value)
        self.assertEqual(self.probe(INTEGER, 128, 'set', '0', 'Test Control', '457')[:2], (0, 1))

    def test_boolean_and_enumerated(self):
        self.assertEqual(self.probe(BOOLEAN, 1, 'set', '0', 'Test Control', '1')[:4], (0, 1, 0, [1, 0, 0, 0]))
        self.assertEqual(self.probe(BOOLEAN, 1, 'set', '0', 'Test Control', '2')[:2], (4, 0))
        self.assertEqual(self.probe(ENUMERATED, 2, 'set', '0', 'Test Control', 'DSP_TX1')[:4],
                         (0, 1, 0, [2, 2, 0, 0]))
        self.assertEqual(self.probe(ENUMERATED, 1, 'set', '0', 'Test Control', '1')[:4], (0, 1, 0, [1, 0, 0, 0]))
        self.assertEqual(self.probe(ENUMERATED, 1, 'set', '0', 'Test Control', '3')[:2], (4, 0))

    def test_failed_enumeration_query_is_an_error(self):
        # CTL_INFO calls of "set ... DSP_TX1" on 3 items: 1 type check, then
        # 2 per item (default, item k), then the type check again
        for call in range(1, 9):
            rc, writes, reads, values, err = self.probe(ENUMERATED, 1, 'set', '0', 'Test Control', 'DSP_TX1',
                                                        fail_call=call)
            self.assertNotEqual(rc, 0, call)
            self.assertEqual(writes, 0, call)
        self.assertEqual(self.probe(ENUMERATED, 1, 'set', '0', 'Test Control', 'DSP_TX1', fail_call=9)[:4],
                         (0, 1, 0, [2, 0, 0, 0]))
        for call in (2, 3):
            rc, writes, reads, values, err = self.probe(ENUMERATED, 1, 'get', '0', 'Test Control', fail_call=call)
            self.assertEqual(rc, 3, call)

    def test_out_of_range_decimal_is_refused(self):
        for value in ('18446744073709552025', '9223372036854775808', '-9223372036854775809',
                      '99999999999999999999999', '--1', '1-', ''):
            self.assertEqual(self.probe(INTEGER, 1, 'set', '0', 'Test Control', value)[:2], (4, 0), value)
        for value in ('9223372036854775807', '-9223372036854775808'):
            # parsed exactly, then outside the control's 0..457
            rc, writes, reads, values, err = self.probe(INTEGER, 1, 'set', '0', 'Test Control', value)
            self.assertEqual((rc, writes), (4, 0), value)
            self.assertIn('value out of range', err)

    def test_get_prints_values(self):
        rc, writes, reads, values, err = self.probe(INTEGER, 2, 'get', '0', 'Test Control')
        self.assertEqual((rc, reads), (0, 1))
        self.assertIn('Test Control = 0 0', err)


@unittest.skipUnless(shutil.which('clang'), 'no clang for the AArch64 build check')
class Target(unittest.TestCase):
    def test_freestanding_aarch64_build(self):
        with tempfile.TemporaryDirectory(prefix='rog5-alsa-probe-') as tmp:
            result = subprocess.run(['clang', '--target=aarch64-linux-gnu', '-ffreestanding', '-nostdlib',
                                     '-fno-stack-protector', '-O2', '-Wall', '-Werror', '-c', str(PROBE),
                                     '-o', f'{tmp}/probe.o'], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == '__main__':
    unittest.main()
