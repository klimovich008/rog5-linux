#!/usr/bin/env python3
"""Run the ROG5 bench on the phone and keep its results.

  rog5-bench.py hw                    hardware matrix (bench/hwcheck.py)
  rog5-bench.py gpu [nop|fault|hang|cycle N]
                                      GPU health / recovery probe
  rog5-bench.py shot [OUT.png]       screenshot of what the panel shows
  rog5-bench.py gesture OUT.png swipe X0 Y0 X1 Y1 [SECONDS] | tap X Y
                                      one gesture (panel pixels), then a screenshot
  rog5-bench.py smooth [--repeat N] [--scenarios a,b]
                                      Denial gesture bench (bench/run.py)
Each run pushes scripts/device/bench and the GPU probe to /root/rog5-bench,
runs there as root over the USB link, stores the JSON under
test-results/bench/<utc>-<kind>.json and, for smooth runs, prints the change
against the previous stored run.
"""
import importlib.util, io, json, sys, tarfile, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('trial', ROOT/'scripts/host/production-ram-trial.py')
trial = importlib.util.module_from_spec(spec)
spec.loader.exec_module(trial)
ADDR = '10.77.0.2'
OUT = ROOT/'test-results/bench'
REMOTE = '/root/rog5-bench'


def push():
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode='w') as tar:
        for p in sorted([*(ROOT/'scripts/device/bench').glob('*.py'), *(ROOT/'scripts/device/bench').glob('*.c')]):
            tar.add(p, arcname='bench/'+p.name)
        tar.add(ROOT/'scripts/device/gpu-recovery-probe.py', arcname='gpu-recovery-probe.py')
    r = trial.ssh(ADDR, f'rm -rf {REMOTE} && mkdir -p {REMOTE} && tar -xf - -C {REMOTE}', 30, data=buf.getvalue())
    if r.returncode:
        sys.exit('push failed: ' + r.stderr.decode()[-300:])


def run(kind, command, timeout):
    push()
    r = trial.ssh(ADDR, command, timeout)
    text = r.stdout.decode(errors='replace')
    try:
        data = json.loads(text)
    except ValueError:
        sys.exit(f'{kind}: no JSON (rc {r.returncode})\n{text[-2000:]}\n{r.stderr.decode(errors="replace")[-2000:]}')
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT/f'{time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())}-{kind}.json'
    path.write_text(json.dumps(data, indent=2) + '\n')
    return data, path


def smooth_table(data, previous=None):
    cols = ('interval_p50_ms', 'interval_p95_ms', 'interval_p99_ms', 'dropped_frames', 'glitches')
    print(f'{"scenario":26}' + ''.join(f'{c:>18}' for c in cols) + f'{"latency p50":>14}')
    for name, s in data['scenarios'].items():
        lat = sorted(g['input_to_first_frame_ms'] for g in s['gestures'] if 'input_to_first_frame_ms' in g)
        row = f'{name:26}'
        for c in cols:
            v = s.get(c)
            old = (previous or {}).get('scenarios', {}).get(name, {}).get(c)
            delta = f' ({v - old:+.1f})' if isinstance(v, (int, float)) and isinstance(old, (int, float)) else ''
            row += f'{str(v) + delta:>18}'
        row += f'{(lat[len(lat)//2] if lat else "-")!s:>14}'
        print(row)


def main():
    kind = sys.argv[1] if len(sys.argv) > 1 else 'hw'
    rest = ' '.join(sys.argv[2:])
    if kind == 'hw':
        data, path = run('hw', f'python3 {REMOTE}/bench/hwcheck.py', 120)
        for s in ('pass', 'partial', 'missing', 'error'):
            print(f'{s:8} {", ".join(data["_summary"][s])}')
    elif kind == 'gpu':
        data, path = run('gpu', f'python3 {REMOTE}/gpu-recovery-probe.py {rest or "nop"}', 600)
        print(json.dumps({k: v for k, v in data.items() if k != 'kernel'}, indent=2))
        for line in data.get('kernel', [])[-12:]:
            print('  ', line[:200])
    elif kind == 'shot':
        push()
        r = trial.ssh(ADDR, f'python3 {REMOTE}/bench/scanout.py png /run/rog5-shot.png --scale 3 >&2 && '
                            'cat /run/rog5-shot.png && rm -f /run/rog5-shot.png', 120)
        if r.returncode:
            sys.exit('shot failed: ' + r.stderr.decode(errors='replace')[-600:])
        OUT.mkdir(parents=True, exist_ok=True)
        path = Path(rest) if rest else OUT/f'{time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())}-shot.png'
        path.write_bytes(r.stdout)
        print('stored', path)
        return
    elif kind == 'gesture':
        out, *g = sys.argv[2:]
        push()
        call = (f'v.swipe({",".join(g[1:])})' if g[0] == 'swipe' else f'v.tap({",".join(g[1:])})')
        r = trial.ssh(ADDR, f'cd {REMOTE}/bench && python3 -c "from vtouch import VirtualTouch, wake_display; import time; '
                            f'wake_display(0.5); v = VirtualTouch(); {call}; time.sleep(1.5); v.close()" && '
                            'python3 scanout.py png /run/rog5-shot.png --scale 3 --no-wake >&2 && '
                            'cat /run/rog5-shot.png && rm -f /run/rog5-shot.png', 120)
        if r.returncode:
            sys.exit('gesture failed: ' + r.stderr.decode(errors='replace')[-600:])
        Path(out).write_bytes(r.stdout)
        print('stored', out)
        return
    elif kind == 'smooth':
        previous = sorted(OUT.glob('*-smooth.json')) if OUT.exists() else []
        data, path = run('smooth', f'python3 {REMOTE}/bench/run.py {rest}', 900)
        smooth_table(data, json.loads(previous[-1].read_text()) if previous else None)
        if data.get('kernel_gpu_errors'):
            print('GPU errors:', *data['kernel_gpu_errors'][:8], sep='\n  ')
    else:
        sys.exit(__doc__)
    print('stored', path.relative_to(ROOT), 'status', data.get('status', '-'))


if __name__ == '__main__':
    main()
