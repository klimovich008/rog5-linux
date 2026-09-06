#!/usr/bin/env python3
"""Compile the exact added selector/scoping logic; no hardware access."""
from pathlib import Path
import re
import subprocess
import tempfile
import unittest

R=Path(__file__).resolve().parents[2]
PATCH=R/'patches/linux-7.1.4/0036-regulator-qcom-rpmh-asus-s12-oem-point.patch'

def additions():
    return '\n'.join(line[1:] for line in PATCH.read_text().splitlines()
                     if line.startswith('+') and not line.startswith('+++'))

class OemPointTest(unittest.TestCase):
    def test_exact_point_scope_and_preserved_order(self):
        added=additions()
        start=added.index('static const struct linear_range')
        end=added.index('\n\tret = rpmh_regulator_asus_s12_point(vreg, node, pmic_id);')
        body=added[start:end]
        stub=r'''
#include <assert.h>
#include <errno.h>
#include <stdbool.h>
#include <string.h>
#define ARRAY_SIZE(a) (sizeof(a)/sizeof((a)[0]))
#define REGULATOR_LINEAR_RANGE(a,b,c,d) {a,b,c,d}
struct linear_range {unsigned min,min_sel,max_sel,step;};
struct device_node {const char *name;bool pm8350;};
struct device {struct device_node *node;};
struct regulator_desc {const struct linear_range *linear_ranges;unsigned n_linear_ranges,n_voltages;};
struct rpmh_vreg {struct device *dev;unsigned addr;struct regulator_desc rdesc;};
static bool asus;
static bool of_machine_is_compatible(const char *s){assert(!strcmp(s,"asus,rog-phone5"));return asus;}
static struct device_node *dev_of_node(struct device *d){return d->node;}
static bool of_device_is_compatible(struct device_node *n,const char *s){assert(!strcmp(s,"qcom,pm8350-rpmh-regulators"));return n->pm8350;}
static bool of_node_name_eq(struct device_node *n,const char *s){return !strcmp(n->name,s);}
'''
        main=r'''
static unsigned voltage(struct regulator_desc *d,unsigned sel){
 for(unsigned i=0;i<d->n_linear_ranges;i++){
  const struct linear_range *r=&d->linear_ranges[i];
  if(sel>=r->min_sel && sel<=r->max_sel)return r->min+(sel-r->min_sel)*r->step;
 }return 0;
}
static int exact(struct regulator_desc *d,unsigned uv){
 for(unsigned i=0;i<d->n_voltages;i++)if(voltage(d,i)==uv)return i;
 return -EINVAL;
}
int main(void){
 const struct linear_range original={320000,0,215,8000};
 struct device_node provider={"regulators-0",true},leaf={"smps12",false};
 struct device dev={&provider};
 struct rpmh_vreg v={&dev,0x40100,{&original,1,216}};
 assert(exact(&v.rdesc,1350000)==-EINVAL);
 assert(rpmh_regulator_asus_s12_point(&v,&leaf,"b")==0 && v.rdesc.n_voltages==216);
 asus=true;
 assert(rpmh_regulator_asus_s12_point(&v,&leaf,"a")==0 && v.rdesc.n_voltages==216);
 leaf.name="smps11";
 assert(rpmh_regulator_asus_s12_point(&v,&leaf,"b")==0 && v.rdesc.n_voltages==216);
 leaf.name="smps12";provider.pm8350=false;
 assert(rpmh_regulator_asus_s12_point(&v,&leaf,"b")==0 && v.rdesc.n_voltages==216);
 provider.pm8350=true;v.addr=0x40104;
 assert(rpmh_regulator_asus_s12_point(&v,&leaf,"b")==-EINVAL);
 v.addr=0x40100;v.rdesc.n_voltages=215;
 assert(rpmh_regulator_asus_s12_point(&v,&leaf,"b")==-EINVAL);
 v.rdesc.n_voltages=216;
 assert(rpmh_regulator_asus_s12_point(&v,&leaf,"b")==0);
 assert(v.rdesc.n_voltages==217 && exact(&v.rdesc,1350000)==129);
 assert(exact(&v.rdesc,1352000)==130 && exact(&v.rdesc,1224000)==113);
 for(unsigned i=0;i<216;i++)assert(exact(&v.rdesc,320000+8000*i)>=0);
 for(unsigned i=1;i<217;i++)assert(voltage(&v.rdesc,i)>voltage(&v.rdesc,i-1));
 assert(voltage(&v.rdesc,0)==320000 && voltage(&v.rdesc,216)==2040000);
 return 0;
}
'''
        with tempfile.TemporaryDirectory() as temporary:
            c=Path(temporary)/'test.c';exe=Path(temporary)/'test'
            c.write_text(stub+body+main)
            subprocess.run(['cc','-Wall','-Wextra','-Werror',str(c),'-o',str(exe)],check=True)
            subprocess.run([str(exe)],check=True,timeout=3)
            # The previously missing integration cannot pass the exact-point assertion.
            wrong=body.replace('vreg->rdesc.linear_ranges = asus_rog5_s12_ranges;',
                               'return 0;\n\tvreg->rdesc.linear_ranges = asus_rog5_s12_ranges;')
            c.write_text(stub+wrong+main)
            subprocess.run(['cc','-Wall','-Wextra','-Werror',str(c),'-o',str(exe)],check=True)
            self.assertNotEqual(subprocess.run([str(exe)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode,0)

    def test_no_state_seeding_or_voltage_write(self):
        text=additions()
        for name in ('rpmh_write','regulator_enable','regulator_set_voltage'):
            self.assertNotRegex(text,r'\b'+name+r'\s*\(')
        self.assertNotIn('vreg->enabled =',text)
        self.assertNotIn('vreg->voltage_selector =',text)
        self.assertIn('ret = rpmh_regulator_asus_s12_point(vreg, node, pmic_id);',text)

if __name__=='__main__':unittest.main()
