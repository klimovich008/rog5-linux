"""Denial ARM64 engine: GN graphs and compile stages (engine-recipe-r1/RECIPE.md).

Stages run in the pinned engine builder with networking off, under the same
disk watchdog as run.py:
  gn       both graphs: ARM64 release embedder (x64-hosted ARM64 gen_snapshot)
           and x64 host tools; records args.gn and the resolved outputs
  target   ARM64 flutter_engine, platform dill and the cross gen_snapshot
  host     x64 dart_sdk, frontend_server, const_finder, font_subset and the
           host GTK library/headers that asset assembly needs
Deviation from the recipe: -j4 in a 4-CPU/8 GiB container instead of -j1
(wall time); outputs and args are otherwise as specified.
"""
from pathlib import Path
import hashlib, json, shutil, signal, subprocess, sys, time, os

D = Path(__file__).resolve().parent
stage = sys.argv[1]
assert stage in ('gn', 'target', 'host')
for name in ('sync', 'hooks'):
    assert json.loads((D/(name+'-result.json')).read_text())['status'] == 'PASS'
if stage != 'gn':
    assert json.loads((D/'gn-result.json').read_text())['status'] == 'PASS'
free = shutil.disk_usage(D).free
assert free >= 40 * 1024**3
builder = json.loads((D/'builder-identity.json').read_text())['image']
SRC = '/build/checkout/engine/src'
TARGET = '/build/engine/out/denial_linux_release_arm64'
HOST = '/build/engine/out/denial_host_release'
scripts = {
    'gn': f'''set -eu
cd {SRC}
./flutter/tools/gn --linux --linux-cpu=arm64 --runtime-mode=release --embedder-for-target \\
  --enable-fontconfig --no-lto --out-dir=/build/engine --target-dir=denial_linux_release_arm64
./flutter/tools/gn --runtime-mode=release --enable-fontconfig --no-lto \\
  --out-dir=/build/engine --target-dir=denial_host_release
for out in {TARGET} {HOST}; do
  cat "$out/args.gn"
  ./flutter/third_party/gn/gn desc "$out" //flutter/shell/platform/embedder:flutter_engine outputs 2>/dev/null || true
done
./flutter/third_party/gn/gn desc {TARGET} '//flutter/third_party/dart/runtime/bin:gen_snapshot(//build/toolchain/linux:clang_x64)' outputs
''',
    'target': f'''set -eu
cd {SRC}
ninja -C {TARGET} -j4 flutter/shell/platform/embedder:flutter_engine flutter/lib/snapshot:kernel_platform_files \\
  clang_x64/gen_snapshot
''',
    'host': f'''set -eu
cd {SRC}
ninja -C {HOST} -j4 flutter/build/dart:dart_sdk flutter/flutter_frontend_server:frontend_server \\
  flutter/tools/const_finder flutter/tools/font_subset \\
  flutter/shell/platform/linux:flutter_linux_gtk flutter/shell/platform/linux:publish_headers_linux
''',
}
(D/(stage+'.sh')).write_text(scripts[stage])
env = {'HOME': '/build/home', 'TMPDIR': '/build/tmp', 'DEPOT_TOOLS_UPDATE': '0', 'VPYTHON_VIRTUALENV_ROOT': '/build/vpython',
       'CIPD_CACHE_DIR': '/build/cipd-cache', 'GIT_TERMINAL_PROMPT': '0',
       'PATH': f'{SRC}/flutter/third_party/ninja:{SRC}/flutter/third_party/depot_tools:/usr/bin:/bin'}
cmd = ['podman', 'run', '--rm', '--read-only', '--read-only-tmpfs=false', '--memory=8g', '--memory-swap=8g', '--cpus=4',
       '--pids-limit=1024', '--network=none', '--cidfile', str(D/(stage+'.cid')), '-v', str(D)+':/build:rw',
       '-v', str(D/'tmp')+':/tmp:rw']
for k, v in env.items():
    cmd += ['-e', k+'='+v]
cmd += ['--workdir', SRC, builder, 'sh', '/build/'+stage+'.sh']
deadline = {'gn': 1800, 'target': 6*3600, 'host': 4*3600}[stage]
growth = {'gn': 5, 'target': 40, 'host': 30}[stage] * 1024**3
started = time.monotonic()
stop = None
with (D/(stage+'-started.json')).open('x') as f:
    json.dump({'command': cmd, 'script_sha256': hashlib.sha256((D/(stage+'.sh')).read_bytes()).hexdigest(),
               'free_before': free, 'unix': time.time(), 'deadline_seconds': deadline, 'growth_limit': growth}, f, indent=2)
with (D/(stage+'.log')).open('x') as log:
    p = subprocess.Popen(cmd, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
    try:
        while p.poll() is None:
            remaining = shutil.disk_usage(D).free
            if remaining < 10 * 1024**3 or free - remaining > growth:
                stop = 'disk budget exceeded'
            if time.monotonic() - started > deadline:
                stop = 'stage deadline exceeded'
            if stop:
                break
            time.sleep(5)
    finally:
        if stop or p.poll() is None:
            cid = (D/(stage+'.cid')).read_text().strip() if (D/(stage+'.cid')).exists() else ''
            if cid:
                subprocess.run(['podman', 'stop', '--time', '10', cid], stdout=log, stderr=subprocess.STDOUT, timeout=60)
            if p.poll() is None:
                os.killpg(p.pid, signal.SIGTERM)
            p.wait(timeout=60)
result = {'status': 'PASS' if p.returncode == 0 and not stop else 'FAIL', 'returncode': p.returncode, 'stop_reason': stop,
          'seconds': round(time.monotonic() - started, 1), 'free_before': free, 'free_after': shutil.disk_usage(D).free}
with (D/(stage+'-result.json')).open('x') as f:
    json.dump(result, f, indent=2)
print(json.dumps(result))
sys.exit(0 if result['status'] == 'PASS' else 1)
