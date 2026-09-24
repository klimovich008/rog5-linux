#!/usr/bin/env python3
"""Denial smoothness bench: scripted gestures, measured at the display.

Runs on the phone as root while rog5-denial.service is up. For every scenario
it injects gestures through a virtual touchscreen (vtouch.py) and records, in
one tracefs timeline (CLOCK_MONOTONIC):
  dpu_crtc_complete_flip        a frame reached the panel (the frame clock)
  dpu_enc_kickoff               a frame was committed to the encoder
  dpu_enc_frame_done_timeout / dpu_enc_phys_cmd_pdone_timeout / dpu_enc_underrun_cb
                                display glitches (tearing, stalls, underruns)
  msm_gpu_submit_retired        per-job GPU time
  msm_gpu_suspend / msm_gpu_resume  GPU power cycling (GMU slumber)
Per scenario it reports input-to-first-frame latency, animation duration,
frame count, p50/p95/p99/max frame interval, dropped frames against the
panel refresh, GPU busy share and glitch counts. The summary JSON goes to
stdout (and --out). GPU faults logged during the run fail the bench.
"""
import argparse, json, os, re, statistics, subprocess, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from vtouch import VirtualTouch

T = '/sys/kernel/tracing'
EVENTS = ['dpu/dpu_crtc_complete_flip', 'dpu/dpu_enc_kickoff', 'dpu/dpu_enc_frame_done_timeout',
          'dpu/dpu_enc_phys_cmd_pdone_timeout', 'dpu/dpu_enc_underrun_cb', 'drm_msm_gpu/msm_gpu_submit',
          'drm_msm_gpu/msm_gpu_submit_retired', 'drm_msm_gpu/msm_gpu_suspend', 'drm_msm_gpu/msm_gpu_resume',
          'drm_msm_gpu/msm_gpu_freq_change']
GLITCH = ('dpu_enc_frame_done_timeout', 'dpu_enc_phys_cmd_pdone_timeout', 'dpu_enc_underrun_cb')
W, H = 1080, 2448
S = 2.5  # Denial output scale


def wr(path, value):
    with open(os.path.join(T, path), 'w') as f:
        f.write(value)


def mark(text):
    wr('trace_marker', 'bench: ' + text)


# Each scenario: list of (gesture, args, settle seconds). Coordinates are panel pixels,
# checked against screenshots (rog5-bench.py gesture ...): the open shade ends
# near y=1180 with its drag handle at y~1155.
QS_HANDLE_Y = 1155
SCENARIOS = {
    'idle': [('wait', (), 2.0)],
    'quick_settings': [('swipe', (540, 0.5 * 48 * S, 540, 0.5 * 48 * S + 488 * S, 0.30), 1.5),
                       ('swipe', (540, QS_HANDLE_Y, 540, 100, 0.30), 1.5)],
    'quick_settings_slow_drag': [('swipe', (540, 0.5 * 48 * S, 540, 0.5 * 48 * S + 488 * S, 1.0, False), 1.5),
                                 ('swipe', (540, QS_HANDLE_Y, 540, 100, 1.0, False), 1.5)],
    # the bottom swipe on the home screen opens the on-screen keyboard; drag it down to close
    'keyboard': [('swipe', (540, H - 20, 540, H - 900, 0.25), 1.5),
                 ('swipe', (540, 1745, 540, H - 8, 0.30), 1.5)],
    # the home screen has two pages
    'home_pages': [('swipe', (950, 1900, 130, 1900, 0.25), 1.5),
                   ('swipe', (130, 1900, 950, 1900, 0.25), 1.5)],
}


def cpu_ticks(pid):
    try:
        f = open(f'/proc/{pid}/stat').read().rsplit(')', 1)[1].split()
        return int(f[11]) + int(f[12])
    except (OSError, IndexError):
        return 0


def run_scenario(vt, name, steps, pid):
    windows = []
    for gesture, args, settle in steps:
        c0 = cpu_ticks(pid)
        mark(f'{name} {gesture} start')
        t0 = time.monotonic()
        if gesture == 'swipe':
            vt.swipe(*args)
        t_in_end = time.monotonic()
        time.sleep(settle)
        t1 = time.monotonic()
        windows.append((t0, t_in_end, t1, (cpu_ticks(pid) - c0) / os.sysconf('SC_CLK_TCK') / (t1 - t0)))
        mark(f'{name} {gesture} end')
    return windows


LINE = re.compile(r'\s+(\d+\.\d+):\s+(\w+):\s?(.*)$')


def parse_trace(text):
    events = []
    for line in text.splitlines():
        if line.startswith('#'):
            continue
        m = LINE.search(line)
        if m:
            events.append((float(m.group(1)), m.group(2), m.group(3)))
    return events


def pct(values, p):
    if not values:
        return None
    s = sorted(values)
    return round(s[min(len(s) - 1, int(round(p / 100 * (len(s) - 1))))], 2)


def analyse(events, windows, refresh_ms):
    flips = [t for t, e, _ in events if e == 'dpu_crtc_complete_flip']
    res = {'gestures': []}
    all_intervals = []
    for t0, t_in_end, t1, cpu in windows:
        f = [t for t in flips if t0 <= t < t1]
        g = {'frames': len(f), 'compositor_cpu_share': round(cpu, 2)}
        if f:
            g['input_to_first_frame_ms'] = round((f[0] - t0) * 1000, 1)
            # animation ends at the last frame before a >250 ms quiet gap
            end = f[0]
            for a, b in zip(f, f[1:]):
                if b - a > 0.25:
                    break
                end = b
            active = [t for t in f if t <= end]
            iv = [(b - a) * 1000 for a, b in zip(active, active[1:])]
            all_intervals += iv
            g['animation_ms'] = round((end - t0) * 1000, 1)
            g['fps'] = round(len(active) / max(end - f[0], 1e-3), 1) if len(active) > 1 else None
            g['interval_p50_ms'] = pct(iv, 50)
            g['interval_p95_ms'] = pct(iv, 95)
            g['interval_max_ms'] = round(max(iv), 2) if iv else None
            g['dropped_frames'] = sum(max(0, round(i / refresh_ms) - 1) for i in iv)
        gpu = [e for e in events if e[1] == 'msm_gpu_submit_retired' and t0 <= e[0] < t1]
        busy = 0.0
        for _, _, body in gpu:
            m = re.search(r'elapsed=(\d+)', body)
            if m:
                busy += int(m.group(1)) / 1e6
        sub = {m.group(1): t for t, e, b in events if e == 'msm_gpu_submit' and t0 <= t < t1
               for m in [re.search(r'id=(\d+)', b)] if m}
        lat = [(t - sub[m.group(1)]) * 1000 for t, _, b in gpu for m in [re.search(r'id=(\d+)', b)]
               if m and m.group(1) in sub]
        el = [int(m.group(1)) / 1e6 for _, _, b in gpu for m in [re.search(r'elapsed=(\d+)', b)] if m]
        g['gpu_job_ms_p50'] = pct(el, 50)
        g['gpu_job_ms_max'] = round(max(el), 2) if el else None
        g['gpu_submit_to_done_ms_p50'] = pct(lat, 50)
        g['gpu_jobs'] = len(gpu)
        g['gpu_busy_ms'] = round(busy, 1)
        freqs = [int(m.group(1)) for _, e, b in events if e == 'msm_gpu_freq_change' and t0 <= _ < t1
                 for m in [re.search(r'new_freq=(\d+)', b)] if m]
        g['gpu_freq_max'] = max(freqs) if freqs else None
        g['gpu_suspend_resume'] = sum(1 for e in events if e[1] in ('msm_gpu_suspend', 'msm_gpu_resume') and t0 <= e[0] < t1)
        g['glitches'] = sum(1 for e in events if e[1] in GLITCH and t0 <= e[0] < t1)
        res['gestures'].append(g)
    res['interval_p50_ms'] = pct(all_intervals, 50)
    res['interval_p95_ms'] = pct(all_intervals, 95)
    res['interval_p99_ms'] = pct(all_intervals, 99)
    res['dropped_frames'] = sum(g.get('dropped_frames', 0) for g in res['gestures'])
    res['glitches'] = sum(g['glitches'] for g in res['gestures'])
    return res


def kernel_gpu_errors(since):
    out = subprocess.run(['journalctl', '-k', '--no-pager', '-o', 'cat', '--since', since],
                         capture_output=True, text=True).stdout
    return [l for l in out.splitlines() if re.search(r'gpu fault|hangcheck|GMU|gmu.*ERROR|underrun', l)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--scenarios', default=','.join(SCENARIOS))
    ap.add_argument('--repeat', type=int, default=3)
    ap.add_argument('--refresh-hz', type=float, default=60.0)
    ap.add_argument('--out')
    a = ap.parse_args()
    if subprocess.run(['systemctl', 'is-active', '-q', 'rog5-denial.service']).returncode:
        sys.exit('rog5-denial.service is not active')
    since = time.strftime('%Y-%m-%d %H:%M:%S')
    wr('tracing_on', '0')
    wr('trace_clock', 'mono')
    wr('buffer_size_kb', '16384')
    wr('set_event', '')
    for e in EVENTS:
        try:
            wr(f'events/{e}/enable', '1')
        except OSError:
            pass
    wr('trace', '')
    pid = subprocess.run(['pgrep', '-x', 'deniald'], capture_output=True, text=True).stdout.split()[0]
    vt = VirtualTouch()
    report = {'refresh_hz': a.refresh_hz, 'scenarios': {}}
    try:
        wr('tracing_on', '1')
        for name in a.scenarios.split(','):
            runs = []
            for i in range(a.repeat):
                runs.append(run_scenario(vt, name, SCENARIOS[name], pid))
            report['scenarios'][name] = runs
    finally:
        wr('tracing_on', '0')
        vt.close()
    raw = open(os.path.join(T, 'trace')).read()
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'last-trace.txt'), 'w') as f:
        f.write(raw)
    events = parse_trace(raw)
    wr('set_event', '')
    report['trace_events'] = len(events)
    for name, runs in list(report['scenarios'].items()):
        windows = [w for run in runs for w in run]
        report['scenarios'][name] = analyse(events, windows, 1000 / a.refresh_hz)
    report['kernel_gpu_errors'] = kernel_gpu_errors(since)
    report['status'] = 'FAIL' if report['kernel_gpu_errors'] else 'PASS'
    text = json.dumps(report, indent=2)
    if a.out:
        with open(a.out, 'w') as f:
            f.write(text)
    print(text)
    return 0 if report['status'] == 'PASS' else 1


if __name__ == '__main__':
    sys.exit(main())
