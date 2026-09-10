#!/usr/bin/env python3
"""Check the fixed-address observer and its strictly unqueued busy retry."""
from pathlib import Path
import importlib.util
import re
import subprocess
import tempfile
import unittest

REPO=Path(__file__).resolve().parents[2]
SOURCE=REPO/'tools/rpmh_state_reader/rog5-rpmh-state-readonly.c'

class StateReaderTest(unittest.TestCase):
    def test_live_vote_decoder_preserves_nonvalue_bits_and_absence(self):
        spec=importlib.util.spec_from_file_location('rpmh_decode',REPO/'tools/rpmh_state_reader/decode.py')
        decoder=importlib.util.module_from_spec(spec);spec.loader.exec_module(decoder)
        prefix=('READBACK_INSMOD_STATUS=0\nformat=rog5-rpmh-readonly-v1\n'
                'kernel=7.1.4-fixture\nscope=APPS-votes-not-physical-measurements\n')
        sample=prefix+('s12-voltage result=0 raw=0x4c8\ns12-enable result=0 raw=0x80000001\n'
          's12-mode result=0 raw=0x3\nreference-l6-voltage result=0 raw=0x800004b0\n'
          'reference-l6-enable result=0 raw=0x0\nreference-l6-mode result=0 raw=0x80000007\n')
        fields=decoder.decode(sample)['fields']
        self.assertEqual(fields['s12-voltage']['millivolt_vote'],1224)
        self.assertEqual(fields['s12-enable']['enable_vote'],1)
        self.assertEqual(fields['s12-enable']['uninterpreted_bits'],'0x80000000')
        self.assertEqual(fields['s12-mode']['mode'],'retention')
        self.assertEqual(fields['reference-l6-voltage']['millivolt_vote'],1200)
        missing=decoder.decode(prefix+'s12-voltage result=-110 raw=unavailable\n')['fields']
        self.assertEqual(missing['s12-voltage']['status'],'error')
        self.assertNotIn('millivolt_vote',missing['s12-voltage'])
        self.assertEqual(missing['s12-enable']['status'],'absent')
        for invalid in (sample+'s12-mode result=0 raw=0x3\n',sample.replace('0x4c8','0x100000000'),
                        sample.replace('s12-voltage','unknown-voltage')):
            with self.assertRaises(ValueError):decoder.decode(invalid)

    def test_busy_only_retry(self):
        text=SOURCE.read_text()
        start=text.index('static int read_one(');end=text.index('\n}\n',start)+3
        code=r'''
#include <assert.h>
#include <errno.h>
struct device {int unused;};struct tcs_cmd {unsigned int addr,data,wait;};
static int values[5],calls,sleeps;
static int rpmh_read(const struct device *d,struct tcs_cmd *c){assert(calls<5);return values[calls++];}
static void msleep(int n){assert(n==20);sleeps++;}
'''+text[start:end]+r'''
int main(void){
 struct device d={0};struct tcs_cmd c={0};
 int cases[4][5]={{-EAGAIN,-EAGAIN,0,0,0},{-ETIMEDOUT,0,0,0,0},
 {-EINVAL,0,0,0,0},{-EAGAIN,-EAGAIN,-EAGAIN,-EAGAIN,-EAGAIN}};
 int returns[]={0,-ETIMEDOUT,-EINVAL,-EAGAIN};int counts[]={3,1,1,5};int waits[]={2,0,0,4};
 for(int i=0;i<4;i++){for(int j=0;j<5;j++)values[j]=cases[i][j];calls=sleeps=0;
  assert(read_one(&d,&c)==returns[i] && calls==counts[i] && sleeps==waits[i]);}
 return 0;
}
'''
        with tempfile.TemporaryDirectory() as tmp:
            c=Path(tmp)/'test.c';out=Path(tmp)/'test';c.write_text(code)
            subprocess.run(['cc','-Wall','-Wextra','-Werror','-Wno-unused-parameter',str(c),'-o',str(out)],check=True)
            subprocess.run([str(out)],check=True,timeout=3)

    def test_fixed_read_only_surface_and_baseline(self):
        text=SOURCE.read_text()
        for call in ('rpmh_write','rpmh_write_async','regulator_enable','regulator_set_voltage','writel'):
            self.assertNotRegex(text,r'\b'+call+r'\s*\(')
        self.assertIn('.owner = THIS_MODULE',text)
        self.assertIn('!pmic || !rsc || s12 || !pcie || of_device_is_available(pcie)',text)
        self.assertIn('cmd_db_read_addr("smpb12") != 0x40100',text)
        self.assertIn('cmd_db_read_addr("ldob6") != 0x41a00',text)
        self.assertIn('raw=unavailable',text)
        self.assertEqual(len(re.findall(r'\{ "(?:reference-l6|s12)-',text)),6)
        self.assertLess(text.index('{ "s12-voltage"'),text.index('{ "reference-l6-voltage"'))
        self.assertIn('if (ret)\n\t\t\tbreak;',text)

if __name__=='__main__':unittest.main()
