#!/usr/bin/env python3
"""Compile exact transition logic and reject unsafe staged DT compositions."""
import copy
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[2]

def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(filename))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

def run_c(text):
    with tempfile.TemporaryDirectory() as tmp:
        source, binary = Path(tmp)/'test.c', Path(tmp)/'test'
        source.write_text(text)
        subprocess.run(['cc', '-std=gnu11', '-Wall', '-Wextra', '-Werror', str(source), '-o', str(binary)], check=True)
        subprocess.run([str(binary)], check=True, timeout=3)

class ActivationTest(unittest.TestCase):
    def test_fixed_staged_composition(self):
        fixture = load('delta_test', 'test-native-wifi-dtb.py').WifiDeltaTest()
        fixture.setUp()
        staged = load('staged', 'stage-native-wifi-dtb.py')
        base, radio = fixture.base, fixture.candidate
        radio[staged.wifi.S12]['phandle'] = staged.cell(500)
        radio[staged.PMU]['vddpmu-supply'] = staged.cell(500)
        candidate = staged.compose(base, radio)
        staged.verify(base, radio, candidate)
        for path, key, value in ((staged.wifi.PCIE, 'status', b'okay\0'),
                (staged.PMU, 'status', b'okay\0'), (staged.wifi.PHY, 'status', b'okay\0'),
                (staged.wifi.S12, 'regulator-min-microvolt', staged.cell(1350000)),
                ('/soc@0/ufshc@1d84000', 'status', b'disabled\0')):
            bad = copy.deepcopy(candidate); bad[path][key] = value
            with self.assertRaises(ValueError): staged.verify(base, radio, bad)
        radio[staged.PMU]['vddpmu-supply'] = staged.cell(501)
        with self.assertRaises(ValueError): staged.compose(base, radio)

    def test_one_module_syscall_even_for_retry_shaped_errors(self):
        fixture = json.loads((REPO/'tests/fixtures/native-wifi/module-insert-no-retry.json').read_text())
        self.assertEqual(sum('identity-check' in s for s in fixture['busybox_records']), 2)
        self.assertEqual(sum('identity-check' in s for s in fixture['module_once_records']), 1)
        self.assertFalse(fixture['power_operation_reached'])
        source = (REPO/'tools/module_once/module-once.c').read_text()
        body = source[source.index('static int insert_once'):source.index('\nint main')]
        run_c(r'''
#include <assert.h>
#include <errno.h>
#include <string.h>
#define SYS_finit_module 273
static int calls, wanted_error;
static long fake_syscall(int number, int fd, const char *parameters, int flags) {
 assert(number==273 && fd==9 && !strcmp(parameters,"action=held-oem") && flags==0);
 calls++;errno=wanted_error;return wanted_error ? -1 : 0;
}
#define syscall fake_syscall
''' + body + r'''
int main(void) {
 int errors[]={0,ENODEV,EINVAL,ENOSYS,EINTR,ETIMEDOUT};
 for(unsigned i=0;i<sizeof(errors)/sizeof(errors[0]);i++) {
  calls=0;wanted_error=errors[i];
  assert(insert_once(9,"action=held-oem")== (wanted_error ? -1 : 0));
  assert(calls==1);
 }
 return 0;
}
''')
        self.assertNotIn('SYS_init_module', source)

    def test_hold_qualification_checks_fresh_raw_state(self):
        source = (REPO/'tools/s12_ufs_vote/rog5-s12-ufs-vote.c').read_text()
        begin = source.index('int rog5_s12_validate_hold(void)\n{')
        body = source[begin:source.index('\nEXPORT_SYMBOL_GPL', begin)]
        run_c(r'''
#include <assert.h>
#include <errno.h>
#include <stdbool.h>
#include <string.h>
#define S12_OEM_MV 1350
#define REGULATOR_MODE_NORMAL 2
static bool holding,oem_qualified;
static void *s12,*pmic_device;
static int uv=1350000,mode=2,enabled=1,reads,raw_error;
static int regulator_get_voltage(void *r){(void)r;return uv;}
static int regulator_get_mode(void *r){(void)r;return mode;}
static int regulator_is_enabled(void *r){(void)r;return enabled;}
static int read_and_check(const char *phase,unsigned voltage,unsigned wanted_mode){
 assert(!strcmp(phase,"before-radio") && voltage==1350 && wanted_mode==6);
 reads++;return raw_error;
}
''' + body + r'''
int main(void){
 assert(rog5_s12_validate_hold()==-EPERM && reads==0);
 holding=true;s12=pmic_device=(void *)1;
 assert(rog5_s12_validate_hold()==-EPERM && reads==0);
 oem_qualified=true;uv=1224000;
 assert(rog5_s12_validate_hold()==-EIO && reads==0);
 uv=1350000;mode=8;assert(rog5_s12_validate_hold()==-EIO && reads==0);
 mode=2;enabled=0;assert(rog5_s12_validate_hold()==-EIO && reads==0);
 enabled=1;raw_error=-110;assert(rog5_s12_validate_hold()==-110 && reads==1);
 raw_error=0;assert(rog5_s12_validate_hold()==0 && reads==2);
 return 0;
}
''')

    def test_actual_activator_refuses_before_apply_and_pins_ambiguous_apply(self):
        source = (REPO/'tools/wifi_activate/rog5-wifi-activate.c').read_text()
        source = re.sub(r'^#include .*\n', '', source, flags=re.M)
        run_c(r'''
#include <assert.h>
#include <errno.h>
#include <stdbool.h>
#include <string.h>
#define __init
#define ARRAY_SIZE(a) (sizeof(a)/sizeof((a)[0]))
#define module_param(...)
#define MODULE_PARM_DESC(...)
#define MODULE_LICENSE(...)
#define MODULE_DESCRIPTION(...)
#define module_init(...)
#define THIS_MODULE ((void *)9)
#define pr_info(...) ((void)0)
struct device_node {int id;};
struct platform_device {int unused;};
struct of_changeset {int unused;};
static struct device_node all_nodes[4]={{0},{1},{2},{3}};
static struct platform_device device;
static int board=1,wrong_compatible,enabled,existing,wrong_supply,hold_error;
static int staged,stage_error,applies,pins,apply_error,qualified;
static bool of_machine_is_compatible(const char *s){assert(!strcmp(s,"asus,rog-phone5"));return board;}
static struct device_node *of_find_node_by_path(const char *s){
 if(!strcmp(s,"/wcn6855-pmu"))return &all_nodes[0];
 if(!strcmp(s,"/soc@0/phy@1c06000"))return &all_nodes[1];
 if(!strcmp(s,"/soc@0/pcie@1c00000"))return &all_nodes[2];
 assert(!strcmp(s,"/soc@0/rsc@18200000/regulators-0/smps12"));return &all_nodes[3];
}
static bool of_device_is_compatible(struct device_node *n,const char *s){(void)n;(void)s;return !wrong_compatible;}
static int of_property_read_string(struct device_node *n,const char *s,const char **out){
 (void)n;assert(!strcmp(s,"status"));*out=enabled ? "okay" : "disabled";return 0;
}
static struct platform_device *of_find_device_by_node(struct device_node *n){(void)n;return existing ? &device : 0;}
static void platform_device_put(struct platform_device *p){assert(p==&device);}
static struct device_node *of_parse_phandle(struct device_node *n,const char *s,int i){
 assert(n==&all_nodes[0] && !strcmp(s,"vddpmu-supply") && i==0);return &all_nodes[wrong_supply ? 0 : 3];
}
static void of_node_put(struct device_node *n){(void)n;}
int rog5_s12_validate_hold(void){qualified++;return hold_error;}
static void of_changeset_init(struct of_changeset *s){(void)s;}
static void of_changeset_destroy(struct of_changeset *s){(void)s;}
static int of_changeset_update_prop_string(struct of_changeset *s,struct device_node *n,const char *p,const char *v){
 (void)s;assert(qualified && n==&all_nodes[staged] && !strcmp(p,"status") && !strcmp(v,"okay"));
 staged++;return stage_error;
}
static void __module_get(void *m){assert(m==THIS_MODULE);pins++;}
static int of_changeset_apply(struct of_changeset *s){(void)s;assert(pins==1 && staged==3);applies++;return apply_error;}
''' + source + r'''
int main(void){
 board=0;assert(wifi_activate_init()==-ENODEV && applies==0);board=1;
 wrong_compatible=1;assert(wifi_activate_init()==-ENODEV && applies==0);wrong_compatible=0;
 enabled=1;assert(wifi_activate_init()==-ENODEV && applies==0);enabled=0;
 existing=1;assert(wifi_activate_init()==-EBUSY && applies==0);existing=0;
 wrong_supply=1;assert(wifi_activate_init()==-ENODEV && applies==0);wrong_supply=0;
 hold_error=-110;assert(wifi_activate_init()==-110 && applies==0 && staged==0);hold_error=0;
 stage_error=-12;assert(wifi_activate_init()==-12 && applies==0 && pins==0);stage_error=staged=0;
 apply_error=-5;assert(wifi_activate_init()==0 && result==-5 && applies==1 && pins==1);
 staged=pins=applies=0;apply_error=0;
 assert(wifi_activate_init()==0 && result==0 && applies==1 && pins==1);
 return 0;
}
''')
        self.assertNotIn('of_changeset_revert(', source)
        self.assertNotIn('module_exit(', source)

    def test_release_is_explicit_not_a_previous_kernel_literal(self):
        for name in ('probe-native-wifi.sh', 'trace-native-wifi-pcie.sh'):
            source = (REPO/'scripts/device'/name).read_text()
            self.assertNotRegex(source, r'7\.1\.4-g[0-9a-f]+')
            self.assertIn('"$(uname -r)" = "$expected_release"', source)
            self.assertIn('kernel release from the verified execution plan required', source)

if __name__ == '__main__':
    unittest.main()
