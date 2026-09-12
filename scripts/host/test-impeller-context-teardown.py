#!/usr/bin/env python3
"""Compile actual pinned Impeller surface destructor with bounded API adapters."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import time

BASE='d728e61e7d835e02c453c70ae9523a40f6c03215'
FILE='engine/src/flutter/shell/gpu/gpu_surface_gl_impeller.cc'


def destructor(text):
    start=text.index('GPUSurfaceGLImpeller::~GPUSurfaceGLImpeller()')
    if text[start:].startswith('GPUSurfaceGLImpeller::~GPUSurfaceGLImpeller() = default;'):
        return 'GPUSurfaceGLImpeller::~GPUSurfaceGLImpeller() = default;'
    end=text.index('{',start)+1; depth=1
    while depth:
        depth+=(text[end]=='{')-(text[end]=='}');end+=1
    return text[start:end]


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    args=p.parse_args();repo=Path(__file__).resolve().parents[2]
    compiler=os.environ.get('CXX','c++')
    if not shutil.which(compiler):p.error('BLOCKED: C++ compiler missing')
    output=args.output.absolute();output.mkdir(parents=True,exist_ok=False)
    original=subprocess.check_output(['git','-C',str(args.source),'show',BASE+':'+FILE],text=True,timeout=10)
    source=output/'source';file=source/FILE;file.parent.mkdir(parents=True);file.write_text(original)
    patch=repo/'patches/flutter-engine-d728e61e/0001-release-impeller-surface-context.patch'
    for flags in (['--check'],[]):subprocess.run(['git','apply',*flags,str(patch)],cwd=source,check=True,timeout=10)
    fixture=(repo/'tools/denial-engine-tests/impeller-teardown.cc').read_text()
    result={'scope':'actual destructor; context, resources and logger are adapters; real engine build/VM NOT RUN by this test','base':BASE,'patch_sha256':hashlib.sha256(patch.read_bytes()).hexdigest(),'runs':[]}
    for label,text in [('before',original),('after',file.read_text())]:
        unit=output/(label+'.cc');unit.write_text(fixture.replace('// @DESTRUCTOR@',destructor(text)))
        binary=output/label;cmd=[compiler,'-std=c++17','-Wall','-Wextra','-Werror',str(unit),'-o',str(binary)]
        started=time.monotonic();subprocess.run(cmd,check=True,capture_output=True,timeout=30)
        for mode in ('normal','initially-unbound','invalid','bind-failure','clear-failure'):
            r=subprocess.run([str(binary),mode],capture_output=True,text=True,timeout=5)
            (output/(label+'-'+mode+'.log')).write_text(r.stdout+r.stderr)
            expected=0 if label=='after' or mode=='invalid' else 1
            result['runs'].append({'label':label,'mode':mode,'build_command':cmd,'test_command':[str(binary),mode],'exit_status':r.returncode,'expected_observed':r.returncode==expected,'duration_since_build_start_seconds':time.monotonic()-started})
    result['status']='PASS' if all(r['expected_observed'] for r in result['runs']) else 'FAIL'
    (output/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2));return result['status']!='PASS'


if __name__=='__main__':raise SystemExit(main())
