#!/usr/bin/env python3
"""Run the ROG5 bench on the phone and keep its results.

  rog5-bench.py hw                    hardware matrix (bench/hwcheck.py)
  rog5-bench.py gpu [nop|fault|hang|cycle N]
                                      GPU health / recovery probe
  rog5-bench.py power [--seconds N] [--label L]
                                      idle battery draw, USB unplugged, screen off
  rog5-bench.py perf [--skip cpu,memory,gpu] [--label L]
                                      CPU/memory/GPU throughput (bench/perf.py)
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
import importlib.util, io, json, shlex, sys, tarfile, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('trial', ROOT/'scripts/host/production-ram-trial.py')
trial = importlib.util.module_from_spec(spec)
spec.loader.exec_module(trial)
import os
# USB link first; ROG5_BENCH_ADDR (e.g. the phone's Wi-Fi address) when unplugged.
ADDR = os.environ.get('ROG5_BENCH_ADDR') or next(
    (a for a in ('10.77.0.2', '169.254.77.2') if trial.ssh(a, 'true', 5).returncode == 0), '10.77.0.2')
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


RC = 0      # the remote exit status of the last run (kept with its JSON)


def run(kind, command, timeout):
    global RC
    push()
    r = trial.ssh(ADDR, command, timeout)
    RC = r.returncode
    text = r.stdout.decode(errors='replace')
    try:
        data = json.loads(text)
    except ValueError:
        sys.exit(f'{kind}: no JSON (rc {r.returncode})\n{text[-2000:]}\n{r.stderr.decode(errors="replace")[-2000:]}')
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT/f'{time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())}-{kind}.json'
    path.write_text(json.dumps(data, indent=2) + '\n')
    return data, path


def numbers(words, low, high, what):
    """Bounded numeric gesture arguments (they become Python source on the
    phone, so nothing else may get through)."""
    if not low <= len(words) <= high:
        sys.exit(f'gesture {what}: {low}..{high} numbers expected')
    try:
        values = [float(w) for w in words]
    except ValueError:
        sys.exit(f'gesture {what}: arguments must be numbers')
    if not all(0 <= v <= 10000 for v in values):
        sys.exit(f'gesture {what}: numbers out of range')
    return ','.join(repr(v) for v in values)


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
    # one shell word per argument: a label with spaces or shell characters
    # stays one argument on the phone
    rest = shlex.join(sys.argv[2:])
    if kind == 'hw':
        data, path = run('hw', f'python3 {REMOTE}/bench/hwcheck.py', 120)
        for s in ('pass', 'partial', 'missing', 'error'):
            print(f'{s:8} {", ".join(data["_summary"][s])}')
    elif kind == 'gpu':
        data, path = run('gpu', f'python3 {REMOTE}/gpu-recovery-probe.py {rest or "nop"}', 600)
        print(json.dumps({k: v for k, v in data.items() if k != 'kernel'}, indent=2))
        for line in data.get('kernel', [])[-12:]:
            print('  ', line[:200])
    elif kind == 'power':
        data, path = run('power', f'python3 {REMOTE}/bench/power.py {rest}', 900)
        print(json.dumps({k: v for k, v in data.items() if k != 'top_interrupts_per_s'}, indent=2))
        for rate, name in data.get('top_interrupts_per_s', []):
            print(f'  {rate:8.1f}/s  {name}')
    elif kind == 'perf':
        data, path = run('perf', f'python3 {REMOTE}/bench/perf.py {rest}', 1200)
        print(json.dumps({k: v for k, v in data.items() if k != 'glmark2'}, indent=2))
        g = data.get('glmark2') or {}
        print('glmark2 score:', g.get('score'), g.get('error', ''))
        for scene, fps in g.get('scenes_fps', {}).items():
            print(f'  {fps:6d} fps  {scene}')
    elif kind == 'shot':
        push()
        r = trial.ssh(ADDR, f'python3 {REMOTE}/bench/scanout.py png /run/rog5-shot.png --scale 3 >&2 && '
                            'cat /run/rog5-shot.png && rm -f /run/rog5-shot.png', 120)
        if r.returncode:
            sys.exit('shot failed: ' + r.stderr.decode(errors='replace')[-600:])
        OUT.mkdir(parents=True, exist_ok=True)
        path = Path(sys.argv[2]) if len(sys.argv) > 2 else OUT/f'{time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())}-shot.png'
        path.write_bytes(r.stdout)
        print('stored', path)
        return
    elif kind == 'gesture':
        if len(sys.argv) < 4 or sys.argv[3] not in ('swipe', 'tap'):
            sys.exit(__doc__)
        out, *g = sys.argv[2:]
        call = (f'v.swipe({numbers(g[1:], 4, 5, "swipe")})' if g[0] == 'swipe'
                else f'v.tap({numbers(g[1:], 2, 2, "tap")})')
        push()
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
    # a failed probe stays a failure for scripts, even with a stored result
    if RC != 0 or data.get('status') == 'FAIL':
        print(f'FAIL remote exit {RC}, status {data.get("status", "-")}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
