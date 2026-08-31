#!/usr/bin/env python3
"""Add only a fixed-voltage diagnostic S12 consumer; leave radio disabled."""
import copy
import hashlib
import importlib.util
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tempfile

PMIC='/soc@0/rsc@18200000/regulators-0'
S12=PMIC+'/smps12'
PCIE='/soc@0/pcie@1c00000'
PHY='/soc@0/phy@1c06000'
CONSUMER='/rog5-s12-revote'
cell=lambda value:struct.pack('>I',value)

def compose(base):
    if (base.get('/',{}).get('model')!=b'ASUS ROG Phone 5\0'
        or S12 in base or CONSUMER in base or '/wcn6855-pmu' in base
        or base.get(PCIE,{}).get('status')!=b'disabled\0'
        or base.get(PHY,{}).get('status')!=b'disabled\0'):
        raise ValueError('not the radio-disabled native baseline')
    pmic=base.get(PMIC,{})
    if (pmic.get('compatible')!=b'qcom,pm8350-rpmh-regulators\0'
        or pmic.get('qcom,pmic-id')!=b'b\0' or 'vdd-s12-supply' in pmic):
        raise ValueError('unexpected S12 provider or existing wiring')
    parent=pmic.get('vdd-s11-supply')
    sources=[props for props in base.values() if props.get('phandle')==parent and parent is not None]
    if (len(sources)!=1 or len(parent)!=4
        or sources[0].get('compatible')!=b'regulator-fixed\0'
        or 'regulator-always-on' not in sources[0]
        or any(key in sources[0] for key in ('gpio','gpios'))):
        raise ValueError('S12 parent is not the unchanged fixed VPH source')
    phandles=[struct.unpack('>I',p['phandle'])[0] for p in base.values() if 'phandle' in p]
    handle=max(phandles)+1
    if handle>=0xffffffff:raise ValueError('no unused phandle')
    candidate=copy.deepcopy(base)
    candidate[PMIC]['vdd-s12-supply']=parent
    candidate[S12]={'phandle':cell(handle),'regulator-name':b'vreg_s12b_revote\0',
        'regulator-min-microvolt':cell(1224000),'regulator-max-microvolt':cell(1224000),
        'regulator-initial-mode':cell(0),'regulator-allowed-modes':cell(0)+cell(2)}
    # No real driver matches this compatible; only the manually loaded probe
    # acquires the supply. This cannot auto-probe the WCN/PCIe power sequence.
    candidate[CONSUMER]={'compatible':b'rog5,s12-revote-diagnostic\0','vddpmu-supply':cell(handle)}
    return candidate

def verify(base,candidate):
    if candidate!=compose(base):raise ValueError('diagnostic DT escaped its exact two-node delta')

def main():
    if len(sys.argv)!=3:raise SystemExit('usage: build-s12-revote-dtb.py BASE NEW_OUTPUT')
    base,output=map(Path,sys.argv[1:])
    if not base.is_file() or base.is_symlink() or output.exists() or output.is_symlink():
        raise ValueError('unsafe or existing DTB path')
    spec=importlib.util.spec_from_file_location('delta',Path(__file__).with_name('verify-recovery-dtb-delta.py'))
    parser=importlib.util.module_from_spec(spec);spec.loader.exec_module(parser)
    source=parser.read_dtb(base);expected=compose(source)
    with tempfile.TemporaryDirectory(prefix='.s12-dtb-',dir=output.parent) as temporary:
        staged=Path(temporary)/'board.dtb';shutil.copyfile(base,staged)
        for node in (S12,CONSUMER):
            subprocess.run(['fdtput','-c',str(staged),node],check=True)
        for node in (PMIC,S12,CONSUMER):
            for name,value in expected[node].items():
                if value==source.get(node,{}).get(name):continue
                if name in ('compatible','regulator-name'):
                    args=['-t','s',str(staged),node,name,value.rstrip(b'\0').decode()]
                else:
                    args=['-t','x',str(staged),node,name,*[f'{v:x}' for v in struct.unpack('>'+str(len(value)//4)+'I',value)]]
                subprocess.run(['fdtput',*args],check=True)
        verify(source,parser.read_dtb(staged))
        # Exclusive creation prevents replacing an earlier qualified artifact.
        with output.open('xb') as target:target.write(staged.read_bytes())
    print('PASS S12 diagnostic DT: radio/PHY disabled, unrelated properties unchanged')
    print(hashlib.sha256(output.read_bytes()).hexdigest())

if __name__=='__main__':main()
