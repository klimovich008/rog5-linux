#!/usr/bin/env python3
"""Test actual pinned ContextBinding decisions and audit bounds; no real EGL."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import time


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    repo = Path(__file__).resolve().parents[2]
    spec = importlib.util.spec_from_file_location('selection', repo/'scripts/host/test-denial-modifier-selection.py')
    selection = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(selection)
    rustc = os.environ.get('RUSTC', 'rustc')
    if not shutil.which(rustc):
        parser.error('BLOCKED: Rust compiler missing')
    output = args.output.absolute()
    output.mkdir(parents=True, exist_ok=False)
    source = output/'source'
    root = 'compositor/src/bin/deniald/flutter_runtime/renderer/'
    for name in ('gl.rs', 'handler.rs', 'handler/open_gl.rs'):
        file = source/root/name
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_bytes(subprocess.check_output(['git','-C',str(args.source),'show',selection.BASE+':'+root+name], timeout=10))
    original = (source/root/'gl.rs').read_text()
    patch = repo/'patches/denial-85b2303e/0004-trace-egl-context-ownership.patch'
    for flags in (['--check'], []):
        subprocess.run(['git','apply',*flags,str(patch)],cwd=source,check=True,timeout=10)
    fixture = (repo/'tools/denial-modifier-tests/context-fixture.rs').read_text()
    result = {'scope':'actual ownership methods with EGL/tracing adapters; not VM/phone proof',
              'base':selection.BASE,'patch_sha256':hashlib.sha256(patch.read_bytes()).hexdigest(),'runs':[]}
    for label, text in [('before',original),('after',(source/root/'gl.rs').read_text())]:
        names = ['make_current','clear_current'] + (['trace_binding'] if label=='after' else [])
        methods = '\n'.join(selection.extract(text,name) for name in names)
        file=output/(label+'.rs');file.write_text(fixture.replace('// @METHODS@',methods))
        binary=output/label
        cmd=[rustc,'--edition=2024','--test',str(file),'-o',str(binary)]
        if label=='after':cmd+=['--cfg','egl_trace']
        start=time.monotonic()
        build=subprocess.run(cmd,env=dict(os.environ,TMPDIR=str(output)),capture_output=True,text=True,timeout=30)
        (output/(label+'-build.log')).write_text(build.stdout+build.stderr)
        build.check_returncode()
        commands=[[str(binary),'--skip','trace_bounds']]
        if label=='after':commands.append([str(binary),'--exact','trace_bounds'])
        for command in commands:
            run=subprocess.run(command,capture_output=True,text=True,timeout=10)
            name=label+('-trace' if '--exact' in command else '')
            (output/(name+'.log')).write_text(run.stdout+run.stderr)
            expected='1 passed; 0 failed' if '--exact' in command else '4 passed; 0 failed'
            result['runs'].append({'label':name,'build_command':cmd,'command':command,'exit_status':run.returncode,'expected_observed':run.returncode==0 and expected in run.stdout,'duration_since_build_start_seconds':time.monotonic()-start})
    result['status']='PASS' if all(r['expected_observed'] for r in result['runs']) else 'FAIL'
    (output/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
    return 0 if result['status']=='PASS' else 1


if __name__=='__main__':
    raise SystemExit(main())
