#!/usr/bin/env python3
"""Exercise the exact vote decision without hardware or a kernel load."""
from pathlib import Path
import copy
import importlib.util
import json
import hashlib
import os
import re
import subprocess
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[2]
SOURCE = REPO / 'tools/s12_ufs_vote/rog5-s12-ufs-vote.c'

def function(text, name):
    start = text.index('static int ' + name + '(')
    body = text.index('{', start)
    depth = 1
    end = body + 1
    while depth:
        depth += (text[end] == '{') - (text[end] == '}')
        end += 1
    return text[start:end]

class S12VoteTest(unittest.TestCase):
    def test_builders_reject_kernel_without_builtin_rpmh_read_before_output(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);source=root/'source';source.mkdir()
            subprocess.run(['git','init','-q',str(source)],check=True)
            env=dict(os.environ,GIT_AUTHOR_NAME='Fixture',GIT_AUTHOR_EMAIL='fixture@rog5.invalid',
                     GIT_COMMITTER_NAME='Fixture',GIT_COMMITTER_EMAIL='fixture@rog5.invalid')
            subprocess.run(['git','-C',str(source),'commit','--allow-empty','-qm','fixture'],
                           env=env,check=True)
            commit=subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True).strip()
            kit=root/'kit';kit.mkdir();(kit/'.config').write_bytes(b'fixture\n')
            digest=hashlib.sha256((kit/'.config').read_bytes()).hexdigest()
            (kit/'build-meta.txt').write_text(f'patched_commit={commit}\n{digest} /.config\n')
            tool=kit/'tools/bpf/resolve_btfids/resolve_btfids'
            tool.parent.mkdir(parents=True);tool.write_text('#!/bin/sh\nexit 1\n');tool.chmod(0o755)
            good='0x00000000\trpmh_read\tvmlinux\tEXPORT_SYMBOL_GPL\t\n'
            variants=('',good.replace('rpmh_read','rpmh_write'),good.replace('vmlinux','module'),
                      good.replace('EXPORT_SYMBOL_GPL','EXPORT_SYMBOL'),good+good)
            for name in ('build-s12-ufs-vote.sh','build-native-wifi-activation.sh'):
                builder=REPO/'scripts/device'/name
                # Execute the real pre-build prefix; no compiler, output or device.
                prefix=builder.read_text().split('before=$(sha256sum',1)[0]
                for symbols in (*variants,good):
                    with self.subTest(builder=name,symbols=symbols):
                        (kit/'Module.symvers').write_text(symbols)
                        output=root/'output'
                        result=subprocess.run(['sh','-c',prefix+'\nprintf READY\n',str(builder),
                            str(source),str(kit),str(output)],capture_output=True,text=True,timeout=5)
                        if symbols==good:
                            self.assertEqual(result.returncode,0,result.stderr)
                            self.assertEqual(result.stdout,'READY')
                        else:
                            self.assertNotEqual(result.returncode,0)
                            self.assertIn('exact built-in rpmh_read',result.stderr)
                        self.assertFalse(output.exists())

    def test_oem_request_requires_hold_and_fresh_read_and_never_rounds(self):
        body=function(SOURCE.read_text(),'request_oem_voltage')
        code=r'''
#include <assert.h>
#include <stdbool.h>
#include <errno.h>
#include <string.h>
#define RPMH_ACTIVE_ONLY_STATE 0
#define S12_REVOTE_UV 1224000
#define S12_OEM_MV 1350
#define pr_info(...) ((void)0)
static void *s12;
static bool holding;
static int before_error,write_error,after_error,reads,writes,cached_uv=1224000,suppress_cache;
static int read_and_check(const char *phase,unsigned mv,unsigned mode) {
 assert(mode==6);reads++;
 if(!strcmp(phase,"before-oem")){assert(mv==1224);return before_error;}
 assert(!strcmp(phase,"after-oem") && mv==1350);return after_error;
}
static int regulator_set_voltage(void *r,int minimum,int maximum){
 assert(r==s12 && minimum==1350000 && maximum==1350000);
 writes++;if(!write_error && !suppress_cache)cached_uv=minimum;return write_error;
}
static int regulator_get_voltage(void *r){assert(r==s12);return cached_uv;}
'''+body+r'''
int main(void){
 assert(request_oem_voltage()==-EPERM && !reads && !writes);
 holding=true;before_error=-110;assert(request_oem_voltage()==-110 && !writes);
 reads=0;before_error=0;write_error=-110;
 assert(request_oem_voltage()==-110 && writes==1 && reads==1 && holding);
 reads=writes=0;write_error=0;after_error=-ERANGE;
 assert(request_oem_voltage()==-ERANGE && writes==1 && reads==2 && holding);
 reads=writes=0;after_error=0;
 assert(request_oem_voltage()==0 && writes==1 && reads==2 && holding);
 reads=writes=0;suppress_cache=1;cached_uv=1224000;
 assert(request_oem_voltage()==-EIO && writes==1 && reads==2 && holding);
 return 0;
}
'''
        with tempfile.TemporaryDirectory() as temporary:
            c=Path(temporary)/'test.c';binary=Path(temporary)/'test';c.write_text(code)
            subprocess.run(['cc','-Wall','-Wextra','-Werror',str(c),'-o',str(binary)],check=True)
            subprocess.run([str(binary)],check=True,timeout=3)

    def test_sanitized_live_revote_sequences(self):
        spec=importlib.util.spec_from_file_location('live_s12_trace',REPO/'scripts/host/verify-s12-vote-trace.py')
        mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
        for name in ('s12-revote-pass.json','s12-oem-pass.json'):
            fixture=json.loads((REPO/'tests/fixtures/native-wifi'/name).read_text())
            self.assertFalse(fixture['radio_activated'])
            for action,lines in fixture['phases'].items():
                self.assertEqual(mod.verify('\n'.join(lines)+'\n',action)['result'],'PASS')

    def test_read_responses_cannot_prove_write_completion(self):
        spec=importlib.util.spec_from_file_location('s12_trace',REPO/'scripts/host/verify-s12-vote-trace.py')
        trace=importlib.util.module_from_spec(spec);spec.loader.exec_module(trace)
        def pair(kind,address,value):
            sent=0 if kind=='read' else value
            msg=0x108 if kind=='read' else 0x10108
            return (f'x: rpmh_send_msg: apps_rsc: tcs(m): 0 [active] cmd(n): 0 msgid: {msg:#x} addr: {address:#x} data: {sent:#x} complete: 0\n'
              f'x: rpmh_tx_done: apps_rsc: ack: tcs-m: 0 addr: {address:#x} data: {value:#x}\n')
        initial=''.join(pair('read',a,v) for a,v in ((0x40100,0x4c8),(0x40104,1),(0x40108,6)))
        # The old ACK-only regex incorrectly matched a read response as an enable write.
        self.assertRegex(initial,r'rpmh_tx_done:.*addr: 0x40104 data: 0x1')
        with self.assertRaises(ValueError):trace.verify(initial,'held-enable')
        held=initial+pair('write',0x40100,0x4c8)+pair('write',0x40104,1)+initial
        trace.verify(held,'held-enable')
        high=initial.replace('addr: 0x40100 data: 0x4c8','addr: 0x40100 data: 0x546')
        oem=held+pair('write',0x40100,1350)+high
        trace.verify(oem,'held-oem')
        with self.assertRaises(ValueError):trace.verify(oem.replace('0x546','0x548'),'held-oem')
        with self.assertRaises(ValueError):trace.verify(held+high,'held-oem')
        retention=initial.replace('addr: 0x40108 data: 0x6','addr: 0x40108 data: 0x3')
        trace.verify(retention,'query')
        trace.verify(retention+'x: rpmh_send_msg: apps_rsc: tcs(m): 3 [wake] cmd(n): 0 msgid: 0x10008 addr: 0x40108 data: 0x3 complete: 0\n','query')
        trace.verify(retention+pair('write',0x40108,6)+initial,'mode')
        with self.assertRaises(ValueError):trace.verify(initial,'mode')
        with self.assertRaises(ValueError):trace.verify(held.replace('data: 0x4c8 complete:', 'data: 0x548 complete:'),'held-enable')
        with self.assertRaises(ValueError):trace.verify(held.replace('rpmh_tx_done: apps_rsc: ack: tcs-m: 0 addr: 0x40100 data: 0x4c8','lost_ack'),'held-enable')

    def test_diagnostic_dtb_changes_only_the_s12_consumer(self):
        spec=importlib.util.spec_from_file_location('s12_dtb',REPO/'scripts/device/build-s12-revote-dtb.py')
        mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
        base={'/':{'model':b'ASUS ROG Phone 5\0'},
              mod.PMIC:{'compatible':b'qcom,pm8350-rpmh-regulators\0','qcom,pmic-id':b'b\0','vdd-s11-supply':mod.cell(1)},
              '/vph':{'compatible':b'regulator-fixed\0','regulator-always-on':b'','phandle':mod.cell(1)},
              mod.PCIE:{'status':b'disabled\0'},mod.PHY:{'status':b'disabled\0'},
              '/ufs':{'status':b'okay\0'},'/usb':{'status':b'okay\0'}}
        candidate=mod.compose(base);mod.verify(base,candidate)
        self.assertEqual(set(candidate)-set(base),{mod.S12,mod.CONSUMER})
        self.assertEqual(candidate[mod.S12]['regulator-min-microvolt'],mod.cell(1224000))
        self.assertEqual(candidate[mod.S12]['regulator-max-microvolt'],mod.cell(1360000))
        self.assertNotIn('regulator-always-on',candidate[mod.S12])
        for path,key,value in ((mod.PCIE,'status',b'okay\0'),('/ufs','status',b'disabled\0'),
            (mod.S12,'regulator-min-microvolt',mod.cell(1350000)),(mod.S12,'regulator-boot-on',b'')):
            bad=copy.deepcopy(candidate);bad[path][key]=value
            with self.assertRaises(ValueError):mod.verify(base,bad)
        for path,key,value in (('/vph','gpio',mod.cell(2)),(mod.PCIE,'status',b'okay\0')):
            bad=copy.deepcopy(base);bad[path][key]=value
            with self.assertRaises(ValueError):mod.compose(bad)

    def test_revote_bounds_and_fresh_raw_fields_are_exact(self):
        text=SOURCE.read_text()
        code=r'''
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
typedef uint32_t u32;
#define BIT(n) (1U << (n))
#define S12_REVOTE_UV 1224000
#define S12_MAX_UV 1360000
#define S12_OEM_MV 1350
'''+function(text,'voltage_bounds_allowed')+'\n'+function(text,'raw_state_matches')+r'''
int main(void) {
 assert(voltage_bounds_allowed(1224000,1360000));
 assert(!voltage_bounds_allowed(1350000,1352000));
 assert(!voltage_bounds_allowed(1224000,1400000));
 assert(raw_state_matches(0x4c8,0x80000001,3,1224,3));
 assert(raw_state_matches(0x800004c8,1,0x80000006,1224,6));
 assert(raw_state_matches(0x80000546,1,6,1350,6));
 assert(!raw_state_matches(0x548,1,3,1224,3));
 assert(!raw_state_matches(0x548,1,6,1350,6));
 assert(!raw_state_matches(0x548,1,6,1352,6));
 assert(!raw_state_matches(0x4c8,0,3,1224,3));
 assert(!raw_state_matches(0x4c8,1,3,1224,6));
 assert(!raw_state_matches(0x400004c8,1,3,1224,3));
 return 0;
}
'''
        with tempfile.TemporaryDirectory() as tmp:
            c=Path(tmp)/'test.c';binary=Path(tmp)/'test';c.write_text(code)
            subprocess.run(['cc','-std=c11','-Wall','-Wextra','-Werror',str(c),'-o',str(binary)],check=True)
            subprocess.run([str(binary)],check=True,timeout=3)

    def test_mainline_auto_pair_rejected_before_regulator_acquisition(self):
        text = SOURCE.read_text()
        body = function(text, 'modes_allowed')
        stub = '''#include <assert.h>
#define RPMH_REGULATOR_MODE_RET 0
#define RPMH_REGULATOR_MODE_AUTO 2
'''
        main = '''int main(void) {
 for (unsigned int first=0; first<5; first++)
  for (unsigned int second=0; second<5; second++)
   assert(modes_allowed(first,second) == (first==0 && second==2));
 return 0;
}
'''
        with tempfile.TemporaryDirectory() as tmp:
            c = Path(tmp) / 'test.c'; binary = Path(tmp) / 'test'
            c.write_text(stub + body + '\n' + main)
            subprocess.run(['cc', '-std=c11', '-Wall', '-Wextra', '-Werror',
                            str(c), '-o', str(binary)], check=True)
            subprocess.run([str(binary)], check=True, timeout=3)
        self.assertLess(text.index('!modes_allowed(modes[0], modes[1])'),
                        text.index('s12 = of_regulator_get_optional('))

    def test_mode_and_held_enable_are_distinct_and_fail_closed(self):
        body = function(SOURCE.read_text(), 'apply_active_vote')
        stub = r'''
#include <assert.h>
#include <stdbool.h>
#include <errno.h>
#include <string.h>
#define REGULATOR_MODE_NORMAL 2
#define REGULATOR_MODE_STANDBY 8
#define S12_REVOTE_UV 1224000
#define THIS_MODULE ((void *)1)
#define pr_info(...) ((void)0)
#define pr_err(...) ((void)0)
static void *s12;
enum vote_action { QUERY, MODE, HELD_ENABLE, HELD_OEM };
static enum vote_action selected_action;
static bool holding;
static int mode, mode_error, enable_error, mode_calls, enable_calls, pins, suppress;
static int cached_voltage=S12_REVOTE_UV, before_error, after_error, reads;
static int regulator_get_voltage(void *r) { (void)r; return cached_voltage; }
static int read_and_check(const char *phase, unsigned int mv, unsigned int expected) {
 assert(mv==1224);
 reads++;
 if (!strcmp(phase,"before")) {
  assert(expected==((selected_action==HELD_ENABLE || selected_action==HELD_OEM) ? 6U : 3U));return before_error;
 }
 assert(!strcmp(phase,"after") && expected==6);return after_error;
}
static unsigned int regulator_get_mode(void *r) { (void)r; return mode; }
static int regulator_set_mode(void *r, unsigned int value) {
 (void)r; assert(value == REGULATOR_MODE_NORMAL); mode_calls++;
 if (!mode_error && !suppress) mode = value;
 return mode_error;
}
static int regulator_enable(void *r) {
 (void)r; assert(mode == REGULATOR_MODE_NORMAL); enable_calls++;
 return enable_error;
}
static void __module_get(void *m) { assert(m == THIS_MODULE); pins++; }
static int oem_calls;
static int request_oem_voltage(void) { assert(holding && pins==1);oem_calls++;return after_error; }
'''
        cases = [
            (0, 8, 0, 0, 0, 0, 0, 0, 0),
            (1, 8, 0, 0, 0, 0, 1, 0, 0),
            (1, 2, 0, 0, 0, -1, 0, 0, 0),
            (1, 8, -110, 0, 0, -110, 1, 0, 0),
            (1, 8, 0, 0, 1, -5, 1, 0, 0),
            (2, 8, 0, 0, 0, -1, 0, 0, 0),
            (2, 2, 0, 0, 0, 0, 0, 1, 1),
            (2, 2, 0, -110, 0, -110, 0, 1, 0),
        ]
        main = 'int main(void) {\n'
        for operation, initial, me, ee, sup, ret, mc, ec, pin in cases:
            main += (f'selected_action={operation}; holding=false; mode={initial}; '
                     f'mode_error={me}; enable_error={ee}; suppress={sup}; '
                     'mode_calls=enable_calls=pins=0; '
                     f'assert(apply_active_vote()=={ret}); '
                     f'assert(mode_calls=={mc} && enable_calls=={ec} && pins=={pin}); '
                     f'assert(holding=={pin});\n')
        main += '''
 selected_action=MODE;mode=8;mode_error=enable_error=suppress=0;
 holding=false;mode_calls=enable_calls=pins=reads=0;before_error=-110;
 assert(apply_active_vote()==-110 && !mode_calls && !enable_calls && reads==1);
 before_error=0;after_error=-5;reads=0;
 assert(apply_active_vote()==-5 && mode_calls==1 && !enable_calls && reads==2);
 selected_action=HELD_ENABLE;mode=2;mode_calls=enable_calls=pins=reads=0;
 assert(apply_active_vote()==-5 && enable_calls==1 && pins==1 && holding && reads==2);
 assert(finish_init_result(-5)==0 && holding && pins==1);
 holding=false;assert(finish_init_result(-5)==-5);
 selected_action=HELD_OEM;mode=2;mode_calls=enable_calls=pins=reads=0;
 assert(apply_active_vote()==-5 && enable_calls==1 && pins==1 && holding && oem_calls==1);
 assert(finish_init_result(-5)==0 && holding);
 cached_voltage=1352000;mode_calls=enable_calls=reads=0;
 assert(apply_active_vote()==-ERANGE && !mode_calls && !enable_calls && !reads);
'''
        main += 'return 0; }\n'
        with tempfile.TemporaryDirectory() as tmp:
            c = Path(tmp) / 'test.c'; binary = Path(tmp) / 'test'
            c.write_text(stub + body + '\n' + function(SOURCE.read_text(),'finish_init_result') + '\n' + main)
            subprocess.run(['cc', '-std=c11', '-O2', '-Wall', '-Wextra', '-Werror',
                            str(c), '-o', str(binary)], check=True)
            subprocess.run([str(binary)], check=True, timeout=3)

    def test_control_surface_and_identity_are_fixed(self):
        text = SOURCE.read_text()
        for forbidden in (r'\bregulator_disable\s*\(', r'\brpmh_write\s*\(',
                          r'\bioremap\s*\(', r'\bwritel\s*\('):
            self.assertNotRegex(text, forbidden)
        self.assertEqual(len(re.findall(r'\bregulator_set_voltage\s*\(',text)),1)
        self.assertIn('regulator_is_supported_voltage(s12, S12_OEM_MV * 1000',text)
        self.assertIn('regulator_set_voltage(s12, S12_OEM_MV * 1000, S12_OEM_MV * 1000)',text)
        self.assertIn('#define S12_OEM_MV 1350',text)
        self.assertIn('module_param(action, charp, 0400)', text)
        self.assertIn('of_machine_is_compatible("asus,rog-phone5")', text)
        self.assertIn('supply != rail', text)
        self.assertIn('cmd_db_read_addr("smpb12") != 0x40100', text)
        self.assertIn('!modes_allowed(modes[0], modes[1])', text)
        self.assertIn('!voltage_bounds_allowed(minimum, maximum)', text)
        self.assertIn('"rog5,s12-revote-diagnostic"', text)
        self.assertIn('of_device_is_available(pcie)', text)
        self.assertIn('regulator-boot-on', text)
        self.assertIn('return finish_init_result(ret)', text)
        self.assertIn('of_regulator_get_optional(&consumer->dev, pmu, "vddpmu")', text)
        self.assertIn('device_trylock(&consumer->dev)', text)
        self.assertIn('if (consumer->dev.driver)', text)
        self.assertIn('regulator-always-on', text)
        cleanup = text.split('static void __exit s12_vote_exit(void)', 1)[1]
        self.assertIn('if (holding)', cleanup)
        self.assertNotIn('regulator_put(', cleanup)
        self.assertNotIn('regulator_set_mode(', cleanup)
        self.assertNotIn('module_put(', cleanup)

if __name__ == '__main__':
    unittest.main()
