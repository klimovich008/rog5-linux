#!/usr/bin/env python3
"""Prove fixed read scope; optional exact ARM64 binary/QEMU fixture."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

REPO=Path(__file__).resolve().parents[2]
SOURCE=REPO/'tools/pmic_rail_reader/rog5-pmic-rail-readonly.c'

class RailReaderTest(unittest.TestCase):
    def test_scope_and_fail_closed_identity(self):
        harness=r'''
#include <assert.h>
#include <stdio.h>
#include <string.h>
#define READER_TEST
#include "SOURCE_PATH"
static int scenario, register_reads, config_reads, opens;
static unsigned int emitted;
static char output[4096];
static const char *paths[16];
long syscall4(long nr,long a,long b,long c,long d) {
 if(nr==NR_OPENAT) {
  assert(a==-100 && c==READ_FLAGS && !(c&3));
  assert(opens<16); paths[opens]=(const char *)b; return 10+opens++;
 }
 if(nr==NR_CLOSE) return 0;
 if(nr==NR_WRITE) {
  assert(a==1 && c>0 && emitted+(unsigned long)c<sizeof(output));
  if(scenario==8) return -32;
  memcpy(output+emitted,(void *)b,c); emitted+=c; return c;
 }
 assert(nr==NR_PREAD64 && a>=10 && a<10+opens);
 const char *path=paths[a-10],*text=NULL;
 if(!strcmp(path,map)) {
  assert(c==9 && d%9==0); unsigned int reg=d/9,base=reg&~255U,off=reg&255;
  int value=0; register_reads++;
  if(reg==0x104)value=scenario==5 ? 0x52 : 0x51;
  else if(reg==0x105)value=0x30;
  else {
   assert(base>=0x1400 && base<=0x3f00);
   if(off==4)value=base==0x2a00?3:0;
   else if(off==5)value=base==0x2a00?10:0;
   else {
    assert(base==0x2a00);config_reads++;
    switch(off){case 1:value=0;break;case 3:value=4;break;case 0x40:value=0xe8;break;
     case 0x41:value=4;break;case 0x45:value=6;break;case 0x46:value=0x80;break;default:assert(0);}
   }
  }
  char line[10];
  if(scenario==6 && reg==0x104)snprintf(line,sizeof(line),"0105: 51\n");
  else if(scenario==7 && reg==0x1504)snprintf(line,sizeof(line),"%04x: XX\n",reg);
  else snprintf(line,sizeof(line),"%04x: %02x\n",reg,value);
  memcpy((void *)b,line,9);return scenario==9?8:9;
 }
 assert(d==0 && c==256);
 if(strstr(path,"pmic@1/compatible"))text=scenario==2?"qcom,other":"qcom,pm8350";
 else if(strstr(path,"base/compatible"))text=scenario==1?"other,board":"asus,rog-phone5";
 else if(strstr(path,"osrelease"))text=scenario==3?"wrong\n":"7.1.4-g359318de534f\n";
 else if(strstr(path,"/range"))text=scenario==4?"0-ff\n100-ffff\n":"0-ffff\n";
 else if(strstr(path,"/name"))text="pmic-spmi\n";
 else assert(0);
 unsigned int n=strlen(text)+(strstr(path,"compatible")?1:0);
 memcpy((void *)b,text,n);return n;
}
int main(void) {
 for(scenario=0;scenario<10;scenario++) {
  register_reads=config_reads=opens=emitted=0; memset(output,0,sizeof(output));
  int ret=snapshot();
  if(scenario==0 || scenario==7) {
   assert(ret==0 && register_reads==96 && config_reads==6);
   assert(strstr(output,"2a40: e8\n2a41: 04\n2a45: 06\n2a46: 80\n"));
   if(scenario==7)assert(strstr(output,"1504: XX\n"));
  } else { assert(ret!=0); if(scenario<=4)assert(register_reads==0); }
 }
 return 0;
}
'''.replace('SOURCE_PATH',str(SOURCE))
        with tempfile.TemporaryDirectory() as tmp:
            c=Path(tmp)/'test.c';binary=Path(tmp)/'test';c.write_text(harness)
            subprocess.run(['cc','-std=c11','-O2','-Wall','-Wextra','-Werror',str(c),'-o',str(binary)],check=True)
            subprocess.run([str(binary)],check=True,timeout=5)

    @unittest.skipUnless(os.environ.get('ROG5_RAIL_READER_BINARY'),'optional ARM64 artifact')
    def test_exact_arm_binary(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            metadata={
              '/sys/firmware/devicetree/base/compatible':b'asus,rog-phone5\0qcom,sm8350\0',
              '/proc/sys/kernel/osrelease':b'7.1.4-g359318de534f\n',
              '/sys/firmware/devicetree/base/soc@0/spmi@c440000/pmic@1/compatible':b'qcom,pm8350\0qcom,spmi-pmic\0',
              '/sys/kernel/debug/regmap/0-01/name':b'pmic-spmi\n',
              '/sys/kernel/debug/regmap/0-01/range':b'0-ffff\n'}
            for path,data in metadata.items():
                out=root/path.lstrip('/');out.parent.mkdir(parents=True,exist_ok=True);out.write_bytes(data)
            values={0x104:0x51,0x105:0x30}
            for base in range(0x1400,0x4000,0x100):values.update({base+4:0,base+5:0})
            values.update({0x2a04:3,0x2a05:10,0x2a01:0,0x2a03:4,0x2a40:0xe8,0x2a41:4,0x2a45:6,0x2a46:0x80})
            with (root/'sys/kernel/debug/regmap/0-01/registers').open('wb') as f:
                for reg,value in values.items():f.seek(reg*9);f.write(f'{reg:04x}: {value:02x}\n'.encode())
            p=subprocess.run(['qemu-aarch64-static','-L',str(root),os.environ['ROG5_RAIL_READER_BINARY']],capture_output=True,timeout=5)
            self.assertEqual(p.returncode,0,p.stderr)
            self.assertIn(b'2a40: e8\n2a41: 04\n2a45: 06\n2a46: 80\n',p.stdout)
            self.assertEqual(len(p.stdout.splitlines()),96)

if __name__=='__main__':unittest.main()
