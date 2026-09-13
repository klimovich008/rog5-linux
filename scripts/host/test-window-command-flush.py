#!/usr/bin/env python3
"""Execute production command dispatch against bounded real Unix socket adapters.

Reuses dispatch fixture and actual source extraction; does not implement Wayland
wire protocol. Backend WouldBlock suppression/retention is an explicit adapter.
API error injection tests propagation, not detection of per-client flush errors.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import runpy
import shutil
import subprocess
import time

PREFIX = 'compositor/src/bin/deniald/'
FILES = [PREFIX + name for name in ('flutter_event_loop.rs', 'flutter_settings_sync.rs',
                                  'flutter_runtime/service_bridge.rs', 'wire.rs')]
PATCH = 'patches/denial-85b2303e/0012-flush-flutter-window-command-output.patch'


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source', type=Path, required=True, help='Exact retained source with patches 0001..0011')
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    rustc = shutil.which(os.environ.get('RUSTC', 'rustc'))
    if not rustc:
        p.error('BLOCKED: Rust compiler missing')
    repo = Path(__file__).resolve().parents[2]
    function = runpy.run_path(str(repo/'scripts/host/test-window-command-dispatch.py'))['function']
    output = a.output.absolute(); output.mkdir(parents=True, exist_ok=False)
    stage = output/'source'
    for name in FILES:
        q = stage/name; q.parent.mkdir(parents=True, exist_ok=True); q.write_bytes((a.source/name).read_bytes())
    before = {name: (stage/name).read_text() for name in FILES}
    for flags in (['--check'], []):
        subprocess.run(['git','apply',*flags,str(repo/PATCH)], cwd=stage, check=True, timeout=15)
    variants = [('before', before), ('after', {name:(stage/name).read_text() for name in FILES})]
    fixture = (repo/'tools/denial-modifier-tests/window-dispatch-fixture.rs').read_text()
    fixture = fixture.replace('Close { window_id: u64 } }', 'Close { window_id: u64 }, Configure { window_id: u64 } }')
    fixture = fixture.replace('Self::Close { window_id } =>', 'Self::Close { window_id } | Self::Configure { window_id } =>')
    fixture = fixture.replace('native_app_plugins: Option<Plugins>, applied:', 'wayland: Option<Frontend>, native_app_plugins: Option<Plugins>, applied:')
    fixture = fixture.replace('        events.applied.extend(commands);', '        if let Some(frontend) = events.wayland.as_mut() { frontend.display_handle.queue(&commands); }\n        events.applied.extend(commands);')
    fixture = fixture.replace('        runtime.drain_window_commands().for_each(drop);', '        // @LOCKED_DRAIN@')
    fixture += '\n' + (repo/'tools/denial-modifier-tests/window-flush-fixture.rs').read_text()
    result = {'scope': __doc__, 'patch_sha256': hashlib.sha256((repo/PATCH).read_bytes()).hexdigest(),
              'runs': [], 'vm':'NOT RUN', 'phone':'NOT RUN'}
    for label, files in variants:
        loop = files[PREFIX+'flutter_event_loop.rs']
        start = loop.index('        let runtime = flutter\n', loop.index('refreshed Flutter bundle without restarting'))
        end = loop.index('        synchronize_flutter_scene(runtime, &mut events)?;', start)
        names = ['drain_window_commands', 'drain_window_command_batch']
        wire = '\n'.join(function(files[PREFIX+'wire.rs'], name) for name in names)
        runtime = '\n'.join(function(files[PREFIX+'flutter_runtime/service_bridge.rs'], name) for name in names)
        management = files[PREFIX+'flutter_settings_sync.rs']
        names = ['dispatch_flutter_window_commands', 'apply_flutter_window_commands']
        if label == 'after': names.append('flush_flutter_wayland_clients')
        dispatch = '\n'.join(function(management, name) for name in names)
        late_start = management.index('        let commands = runtime.drain_window_commands()')
        late_end = management.index('\n    }\n    if events.pending_window_events', late_start)
        locked_start = management.index('        runtime.drain_window_commands().for_each(drop);', management.index('pub(super) fn synchronize_flutter_window_management'))
        locked_end = management.index('\n    } else {', locked_start)
        unit = fixture.replace('// @SEGMENT@', loop[start:end]).replace('// @WIRE_METHODS@', wire).replace('// @RUNTIME_METHODS@', runtime).replace('// @DISPATCH@', dispatch).replace('// @LATE_DISPATCH@', management[late_start:late_end]).replace('// @LOCKED_DRAIN@', management[locked_start:locked_end])
        source = output/(label+'.rs'); source.write_text(unit); binary=output/label
        command = [rustc,'--edition=2024','--test',str(source),'-o',str(binary)]
        if label == 'before': command += ['--cfg','before']
        started=time.monotonic(); build=subprocess.run(command,capture_output=True,text=True,timeout=45,env=dict(os.environ,TMPDIR=str(output)))
        (output/(label+'-build.log')).write_text(build.stdout+build.stderr)
        build_seconds=time.monotonic()-started
        if build.returncode: print(build.stderr); build.check_returncode()
        test=[str(binary),'--test-threads=1']; started=time.monotonic()
        run=subprocess.run(test,capture_output=True,text=True,timeout=15)
        (output/(label+'.log')).write_text(run.stdout+run.stderr)
        expected='9 passed; 8 failed' if label=='before' else '18 passed; 0 failed'
        result['runs'].append({'variant':label,'build_command':command,'build_seconds':build_seconds,'command':test,
            'duration_seconds':time.monotonic()-started,'exit_status':run.returncode,
            'expected_observed':expected in run.stdout and run.returncode==(101 if label=='before' else 0),
            'unit_sha256':hashlib.sha256(unit.encode()).hexdigest(),
            'source_hashes':{name:hashlib.sha256(value.encode()).hexdigest() for name,value in files.items()}})
    result['status']='PASS' if all(x['expected_observed'] for x in result['runs']) else 'FAIL'
    (output/'result.json').write_text(json.dumps(result,indent=2)+'\n'); print(json.dumps(result,indent=2))
    return 0 if result['status']=='PASS' else 1

if __name__=='__main__':raise SystemExit(main())
