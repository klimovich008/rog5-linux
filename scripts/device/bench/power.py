#!/usr/bin/env python3
"""Idle power: battery draw with USB unplugged and the screen off.

Refuses to measure on USB power (the charger would mask the draw). Waits up to
--blank-wait seconds for the display to blank (Denial's idle DPMS), then
samples qcom-battmgr-bat current_now/voltage_now every second for --seconds.
Reports mean/median current and power, CPU busy share and the interrupt
sources with the most wakeups over the window. JSON on stdout.
"""
import argparse, json, os, statistics, time

BAT = '/sys/class/power_supply/qcom-battmgr-bat'
USB = '/sys/class/power_supply/qcom-battmgr-usb/online'


def rd(path):
    with open(path) as f:
        return f.read().strip()


def display_on():
    try:
        state = rd('/sys/kernel/debug/dri/1/state')
    except OSError:
        return None
    return '\tactive=1' in state.split('crtc[', 1)[-1].split('\n\n', 1)[0]


def cpu_times():
    f = rd('/proc/stat').splitlines()[0].split()[1:]
    v = list(map(int, f))
    idle = v[3] + v[4]
    return sum(v), idle


def interrupts():
    out = {}
    for line in rd('/proc/interrupts').splitlines()[1:]:
        parts = line.split()
        if not parts:
            continue
        counts = [int(p) for p in parts[1:9] if p.isdigit()]
        out[(parts[0].rstrip(':') + ' ' + ' '.join(parts[9:]))[:60]] = sum(counts)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--seconds', type=int, default=120)
    ap.add_argument('--blank-wait', type=int, default=120)
    ap.add_argument('--label', default='')
    a = ap.parse_args()
    report = {'label': a.label, 'time': time.strftime('%Y-%m-%dT%H:%M:%S')}
    if rd(USB) == '1':
        report.update(status='REFUSED', reason='USB power is connected')
        print(json.dumps(report, indent=2))
        return 2
    waited = 0
    while display_on() and waited < a.blank_wait:
        time.sleep(2)
        waited += 2
    report['display_off'] = display_on() is False
    report['blank_wait_s'] = waited
    t0, i0 = cpu_times()
    irq0 = interrupts()
    ma, mw = [], []
    for _ in range(a.seconds):
        ua = int(rd(f'{BAT}/current_now'))
        uv = int(rd(f'{BAT}/voltage_now'))
        ma.append(ua / 1000)
        mw.append(ua / 1000 * uv / 1e6)
        time.sleep(1)
    t1, i1 = cpu_times()
    irq1 = interrupts()
    busy = 1 - (i1 - i0) / max(1, t1 - t0)
    wakeups = sorted(((irq1[k] - irq0.get(k, 0)) / a.seconds, k) for k in irq1)[-6:]
    report.update(
        status='PASS' if report['display_off'] else 'PASS_SCREEN_ON',
        seconds=a.seconds,
        current_ma_mean=round(statistics.mean(ma), 1),
        current_ma_median=round(statistics.median(ma), 1),
        current_ma_p10_p90=[round(sorted(ma)[len(ma) // 10], 1), round(sorted(ma)[len(ma) * 9 // 10], 1)],
        power_mw_mean=round(statistics.mean(mw), 1),
        voltage_v=round(int(rd(f'{BAT}/voltage_now')) / 1e6, 3),
        capacity=int(rd(f'{BAT}/capacity')),
        cpu_busy_pct=round(100 * busy, 2),
        top_interrupts_per_s=[[round(r, 1), k] for r, k in reversed(wakeups)],
    )
    print(json.dumps(report, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
