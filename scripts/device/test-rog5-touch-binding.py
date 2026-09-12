#!/usr/bin/env python3
"""Validate the disabled prototype binding against actual-overlay DTB fixtures."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import shlex
import subprocess
import tempfile
import time

ROOT=Path(__file__).resolve().parents[2]
BINDING=ROOT/'tools/rog5-fts3658u/asus,rog5-mp2-fts3658u.yaml'
OVERLAY=ROOT/'dts/qcom/sm8350-rog5-mp2-front-touch-disabled.dtso'

def need(value,message):
    if not value:raise ValueError(message)

def run_suite(out):
    started=time.monotonic();result={'status':'FAIL','scope':'offline schema fixtures, no enabling or hardware qualification','physical_validation':'NOT RUN','stages':{},'cases':{}}
    def run(name,argv):
        before=time.monotonic();p=subprocess.run([str(x) for x in argv],text=True,capture_output=True,timeout=30)
        log=p.stdout+p.stderr;(out/(name+'.log')).write_text(log)
        result['stages'][name]={'command':[str(x) for x in argv],'exit_code':p.returncode,'seconds':round(time.monotonic()-before,3)}
        need(p.returncode==0,name+' failed: '+log)
        return log
    try:
        for tool in ('dt-doc-validate','dt-mk-schema','dt-validate','dtc'):
            need(shutil.which(tool),'required schema tool missing: '+tool)
        entrypoint=Path(shutil.which('dt-validate')).read_text().splitlines()[0]
        need(entrypoint.startswith('#!'),'schema entrypoint lacks interpreter')
        schema_python=shlex.split(entrypoint[2:])
        strict_code = '''import dtschema,sys
from pathlib import Path
validator=dtschema.DTValidator([sys.argv[1]])
tree=validator.decode_dtb(Path(sys.argv[2]).read_bytes())[0]
node=tree['i2c']['touchscreen@38'];node['$nodename']=['touchscreen@38']
for error in validator.iter_errors(node,filter=['asus,rog5-mp2-fts3658u']):
    print(dtschema.format_error(sys.argv[2],error,nodename='touchscreen@38',compatible=node['compatible'][0]))
'''
        target=out/'input/touchscreen'/BINDING.name;target.parent.mkdir(parents=True);shutil.copyfile(BINDING,target)
        need(not run('meta-schema',['dt-doc-validate',target]).strip(),'meta-schema diagnostics')
        need(not run('schema-cache',['dt-mk-schema','-j','-o',out/'schema.json',target]).strip(),'schema-cache diagnostics')
        original=OVERLAY.read_text();match=re.search(r'\ttouchscreen@38 \{.*?\n\t\};',original,re.S)
        need(match,'actual disabled touch node missing')
        node=match.group(0)
        # Controller/supply stubs supply real phandle types only; the target
        # touchscreen node is copied verbatim from the shipped disabled overlay.
        def dts(body):
            return '''/dts-v1/;
/ {
    #address-cells = <1>; #size-cells = <1>;
    tlmm: gpio-controller { gpio-controller; #gpio-cells = <2>;
        interrupt-controller; #interrupt-cells = <2>; #address-cells = <0>; };
    rog5_touch_l3c: regulator-vdd {};
    rog5_touch_l8c: regulator-io {};
    rog5_front_touch_active: pin-state {};
    i2c { #address-cells = <1>; #size-cells = <0>;
'''+body+'\n    };\n};\n'
        variants={'valid-disabled':(node,None)}
        def variant(name,old,new,expected):
            need(node.count(old)==1,'ambiguous fixture replacement '+name)
            variants[name]=(node.replace(old,new),expected)
        variant('wrong-address','reg = <0x38>','reg = <0x39>','reg:')
        variant('wrong-irq-polarity','interrupts = <23 2>','interrupts = <23 1>','interrupts:')
        variant('wrong-irq-pin','interrupts = <23 2>','interrupts = <24 2>','interrupts:')
        variant('wrong-reset-polarity','reset-gpios = <&tlmm 22 1>','reset-gpios = <&tlmm 22 0>','reset-gpios:')
        variant('wrong-reset-pin','reset-gpios = <&tlmm 22 1>','reset-gpios = <&tlmm 21 1>','reset-gpios:')
        variant('wrong-io-polarity','io-enable-gpios = <&tlmm 131 0>','io-enable-gpios = <&tlmm 131 1>','io-enable-gpios:')
        variant('wrong-io-pin','io-enable-gpios = <&tlmm 131 0>','io-enable-gpios = <&tlmm 130 0>','io-enable-gpios:')
        variant('pixel-x','touchscreen-size-x = <17280>','touchscreen-size-x = <1080>','touchscreen-size-x:')
        variant('pixel-y','touchscreen-size-y = <39168>','touchscreen-size-y = <2448>','touchscreen-size-y:')
        variant('missing-vdd','vdd-supply = <&rog5_touch_l3c>;','',"'vdd-supply' is a required property")
        variant('missing-io','vcc_i2c-supply = <&rog5_touch_l8c>;','',"'vcc_i2c-supply' is a required property")
        variant('enabled','status = "disabled"','status = "okay"','status:')
        variant('unimplemented-transform','status = "disabled";','status = "disabled"; touchscreen-inverted-x;','touchscreen-inverted-x')
        variant('unqualified-wakeup','status = "disabled";','status = "disabled"; wakeup-source;','wakeup-source')
        for name,(body,expected) in variants.items():
            source=out/(name+'.dts');source.write_text(dts(body));dtb=out/(name+'.dtb')
            run(name+'-dtc',['dtc','-I','dts','-O','dtb','-o',dtb,source])
            log=run(name+'-schema',['dt-validate','-s',out/'schema.json','-l','asus,rog5-mp2-fts3658u',dtb])
            # CLI suppresses required-property errors on disabled nodes. The
            # library reports them without changing the fixture's status.
            strict=run(name+'-strict-schema',schema_python+['-c',strict_code,str(out/'schema.json'),str(dtb)])
            need(expected in strict if expected else not strict.strip(),name+': unexpected strict validation result '+strict)
            if name=='valid-disabled':need(not log.strip(),'valid CLI diagnostics')
            result['cases'][name]={'status':'PASS','expected_rejection':expected is not None,'dtb_sha256':hashlib.sha256(dtb.read_bytes()).hexdigest()}
        run('before-cache',['dt-mk-schema','-j','-o',out/'before-schema.json'])
        before=run('before-schema',['dt-validate','-m','-s',out/'before-schema.json',out/'valid-disabled.dtb'])
        need("failed to match any schema with compatible: ['asus,rog5-mp2-fts3658u']" in before,'missing-schema counterexample not reproduced')
        result['disabled_cli_limit']='dt-validate suppresses required errors on disabled nodes; direct DTValidator checks above retain them'
        result['before']='FAIL: actual disabled compatible has no matching schema without new binding'
        result['status']='PASS'
        result['inputs']={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (BINDING,OVERLAY,ROOT/'tools/rog5-fts3658u/rog5_fts3658u.c',ROOT/'tools/rog5-fts3658u/rog5_fts_protocol.h')}
    finally:
        result['seconds']=round(time.monotonic()-started,3);(out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    print('PASS disabled touch binding: '+str(len(result['cases']))+' semantic DTB cases; physical NOT RUN')

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path);args=parser.parse_args()
    if args.output:
        need(not args.output.exists(),'output must be new');args.output.mkdir(parents=True);run_suite(args.output.resolve())
    else:
        (ROOT/'build').mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='touch-binding-',dir=ROOT/'build') as temporary:run_suite(Path(temporary))

if __name__=='__main__':main()
