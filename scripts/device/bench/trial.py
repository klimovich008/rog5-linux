#!/usr/bin/env python3
"""Post-install trial of a ROG5 kernel, run on the phone as root.

Does what a person would check after installing a new kernel, without
touching the locked Phosh session: boot and service health, the hardware
matrix (hwcheck.py), CPU/GPU identity and live GPU monitoring under a
headless vkmark load, a CPU stress run with result verification, what the
panel is showing (DSI plane grab), network, and kernel warnings / crashes
since boot. With --suspend it also does one RTC-woken suspend/resume cycle
and re-checks Wi-Fi and the GPU afterwards.

Usage: trial.py [--suspend] [--grab-dir DIR]   (JSON on stdout)
"""
import glob, json, os, re, subprocess, sys, threading, time

HERE = os.path.dirname(os.path.abspath(__file__))
CARD = '/sys/class/drm/card0/device'


def sh(cmd, timeout=120):
    try:
        return subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout).stdout.strip()
    except subprocess.TimeoutExpired:
        return 'TIMEOUT'


def rd(path, default=''):
    try:
        with open(path) as f:
            return f.read().strip()
    except OSError:
        return default


def result(status, **evidence):
    return {'status': status, 'evidence': evidence}


def boot():
    state = sh('systemctl is-system-running')
    failed = sh("systemctl --failed --plain --no-legend | awk '{print $1}'").split()
    return result('pass' if state == 'running' and not failed else 'partial', release=os.uname().release,
                  version=os.uname().version, system_state=state, failed_units=failed,
                  uptime_s=int(float(rd('/proc/uptime').split()[0])))


def hardware():
    out = json.loads(sh(f'{sys.executable} {HERE}/hwcheck.py', 300) or '{}')
    summary = out.get('_summary', {})
    return result('pass' if not summary.get('error') else 'partial', **summary)


def cpu_identity():
    names = re.findall(r'^model name\s*:\s*(.+)$', rd('/proc/cpuinfo'), re.M)
    counts = {}
    for n in names:
        counts[n] = counts.get(n, 0) + 1
    lscpu = re.findall(r'Model name:\s*(.+)', sh('lscpu'))
    maxf = {os.path.basename(p): int(rd(p + '/cpuinfo_max_freq', '0')) // 1000
            for p in sorted(glob.glob('/sys/devices/system/cpu/cpufreq/policy*'))}
    return result('pass' if len(names) == os.cpu_count() else 'missing',
                  model_names=counts, lscpu=lscpu, max_mhz=maxf)


def gpu_hwmon():
    for h in glob.glob(CARD + '/hwmon/hwmon*'):
        if rd(h + '/name') == 'msm_gpu':
            return h
    return None


def gpu_monitor():
    """Sample the exported load/clock/temperature while vkmark runs headless."""
    busy_path, hw = CARD + '/gpu_busy_percent', gpu_hwmon()
    if not os.path.exists(busy_path) or not hw:
        return result('missing', gpu_busy_percent=os.path.exists(busy_path), hwmon=hw)
    idle = {'busy': rd(busy_path), 'freq_hz': rd(hw + '/freq1_input'), 'temp_mC': rd(hw + '/temp1_input')}
    samples, stop = [], threading.Event()

    def sample():
        while not stop.is_set():
            samples.append((int(rd(busy_path, '0')), int(rd(hw + '/freq1_input', '0')),
                            int(rd(hw + '/temp1_input', '0') or 0)))
            time.sleep(0.25)

    t = threading.Thread(target=sample)
    t.start()
    bench = sh('sudo -u phone vkmark --winsys headless -b vertex:duration=4 -b texture:duration=4 '
               '-b shading:shading=phong:duration=4 -b cube:duration=4 2>&1', 120)
    stop.set()
    t.join()
    score = re.search(r'vkmark Score:\s*(\d+)', bench)
    peak = (max(s[0] for s in samples), max(s[1] for s in samples), max(s[2] for s in samples)) if samples else (0, 0, 0)
    ok = peak[0] >= 50 and peak[1] > 0 and peak[2] > 0 and score
    return result('pass' if ok else 'partial', idle=idle, peak_busy_percent=peak[0],
                  peak_freq_mhz=peak[1] // 1_000_000, peak_temp_c=peak[2] / 1000,
                  after={'busy': rd(busy_path)}, vkmark_score=int(score.group(1)) if score else None,
                  gpu_name=rd(CARD + '/of_node/compatible').split('\0')[0])


def cpu_stress():
    out = sh('stress-ng --cpu 8 --cpu-method matrixprod --verify -t 15 --metrics-brief 2>&1', 60)
    bogo = re.search(r'cpu\s+(\d+)\s+[\d.]+\s+[\d.]+\s+[\d.]+\s+([\d.]+)', out)
    ok = 'successful run completed' in out and 'fail' not in out.lower().replace('failed: 0', '')
    temps = sh("cat /sys/class/thermal/thermal_zone*/temp | sort -n | tail -1")
    return result('pass' if ok else 'fail', bogo_ops_per_s=float(bogo.group(2)) if bogo else None,
                  hottest_after_mC=temps, tail=out.splitlines()[-2:])


def session():
    units = {u: sh(f'systemctl is-active {u}') for u in
             ('rog5-phosh', 'rog5-gnome', 'rog5-desktop-mode', 'rog5-touchpad', 'rog5-sleep-policy', 'tailscaled')}
    procs = {p: bool(sh(f'pgrep -x {p}')) for p in ('phoc', 'phosh')}
    locked = sh("loginctl show-session $(loginctl list-sessions --no-legend | awk '$3==\"phone\"{print $1; exit}')"
                " -p LockedHint --value")
    dp = {os.path.basename(c): rd(c + '/status') for c in glob.glob('/sys/class/drm/card*-DP-*')}
    ok = units['rog5-phosh'] == 'active' and all(procs.values()) and units['rog5-desktop-mode'] == 'active'
    return result('pass' if ok else 'fail', units=units, processes=procs, locked_hint=locked, dp=dp)


def panel(grab_dir):
    """Grab whatever the DSI panel scans out; a blank panel has no framebuffer."""
    bl = {os.path.basename(b): rd(b + '/brightness') for b in glob.glob('/sys/class/backlight/*')}
    grabs = []
    if grab_dir:
        os.makedirs(grab_dir, exist_ok=True)
        for pid in range(1, 400):
            path = f'{grab_dir}/plane-{pid}.ppm'
            r = subprocess.run(['/usr/local/libexec/rog5-kms-grab', str(pid), path, '/dev/dri/card1'],
                               capture_output=True, text=True)
            if r.returncode == 0:
                grabs.append({'plane': pid, 'file': path, 'info': r.stdout.strip()})
            elif os.path.exists(path):
                os.unlink(path)
    return result('pass' if grabs else 'partial', backlight=bl, grabs=grabs,
                  note='' if grabs else 'no plane is scanning out (panel off/blanked)')


def network():
    wifi = sh("ip -4 -o addr show wlan0 | awk '{print $4}'")
    gw = sh("ip route show default | awk '{print $3; exit}'")
    ping = sh(f'ping -c3 -W2 {gw} | tail -1') if gw else ''
    ts = sh("tailscale status --json 2>/dev/null | python3 -c 'import json,sys;print(json.load(sys.stdin)[\"BackendState\"])'")
    return result('pass' if wifi and 'min/avg' in ping else 'fail', wifi=bool(wifi), gateway_rtt=ping,
                  tailscale=ts)


def kernel_health():
    log = sh('journalctl -k -b --no-pager -o cat', 60)
    pats = {'warn_bug_oops': r'WARNING: CPU|\bBUG:|Internal error:|\bOops:|Call trace:',
            'gpu_fault': r'hangcheck|gpu fault|gmu.*(timed? ?out|fault|fail)|recover(ing)? gpu',
            # The display engine (SIDs 0x820/0xc20) faults ~10 times at the
            # bootloader-splash handover on every boot; count the rest.
            'smmu_fault': r'Unhandled context fault(?!.*cbfrsynra=0x(820|c20),)',
            'dpu_underrun': r'underrun', 'usb_errors': r'usb .*error|device descriptor read',
            'ufs': r'ufshcd.*(err|fail)'}
    lines = log.splitlines()
    # Known since 7.2.7 bring-up: the DSI PHY PLL clock warns once at boot
    # when of_clk_add_hw_provider reparents it (orphan disable/unprepare).
    known = sum(1 for i, l in enumerate(lines) if l.strip() == 'Call trace:' and
                any('clk_core_reparent_orphans' in x for x in lines[i + 1:i + 8]))
    hits = {k: len(re.findall(v, log, re.I)) for k, v in pats.items()}
    hits['warn_bug_oops'] -= known
    samples = {k: [l for l in log.splitlines() if re.search(v, l, re.I)][:3] for k, v in pats.items() if hits[k]}
    dumps = sh('coredumpctl list --since "$(uptime -s)" --no-legend 2>/dev/null').splitlines()
    ok = not hits['warn_bug_oops'] and not hits['gpu_fault'] and not hits['smmu_fault'] and not dumps
    return result('pass' if ok else 'partial', counts=hits, known_clk_reparent_traces=known,
                  samples=samples, coredumps=dumps,
                  err_lines=int(sh('journalctl -k -b -p err --no-pager -o cat | wc -l') or 0))


def usb_devices():
    return sorted(d for d in os.listdir('/sys/bus/usb/devices') if re.fullmatch(r'\d+-[\d.]+', d))


def suspend_cycle():
    policy = sh('systemctl is-active rog5-sleep-policy')
    if policy == 'active':
        sh('systemctl stop rog5-sleep-policy')
    before = rd('/sys/power/suspend_stats/success', '0')
    usb_before = usb_devices()
    t0 = time.time()
    # Like rog5-sleep-policy: systemctl suspend, so system-sleep hooks run
    # (rtcwake -m mem writes /sys/power/state directly and skips them).
    out = sh('rtcwake -m no -s 20 2>&1 && systemctl suspend --check-inhibitors=no 2>&1', 60)
    for _ in range(120):
        if rd('/sys/power/suspend_stats/success', '0') != before:
            break
        time.sleep(0.5)
    slept = time.time() - t0
    time.sleep(5)
    after = rd('/sys/power/suspend_stats/success', '0')
    usb_after = usb_devices()
    for _ in range(8):  # Wi-Fi reassociated 11 s after resume on r183
        net = network()
        if net['status'] == 'pass':
            break
        time.sleep(5)
    gpu = sh('sudo -u phone vkmark --winsys headless -b vertex:duration=3 2>&1 | grep -o "Score: [0-9]*"', 60)
    if policy == 'active':
        sh('systemctl start rog5-sleep-policy')
    ok = int(after) > int(before) and net['status'] == 'pass' and gpu and usb_after == usb_before
    return result('pass' if ok else 'fail', rtcwake=out.splitlines()[-1:], wall_s=round(slept, 1),
                  suspend_success=f'{before}->{after}', wifi_after=net['evidence'], gpu_after=gpu,
                  usb_before=usb_before, usb_after=usb_after,
                  last_failed=rd('/sys/power/suspend_stats/last_failed_dev'))


def main():
    grab_dir = sys.argv[sys.argv.index('--grab-dir') + 1] if '--grab-dir' in sys.argv else None
    checks = [('boot', boot), ('session', session), ('panel', lambda: panel(grab_dir)), ('network', network),
              ('cpu_identity', cpu_identity), ('gpu_monitor', gpu_monitor), ('cpu_stress', cpu_stress),
              ('hardware', hardware)]
    if '--suspend' in sys.argv:
        checks.append(('suspend_cycle', suspend_cycle))
    checks.append(('kernel_health', kernel_health))
    out = {}
    for name, fn in checks:
        try:
            out[name] = fn()
        except Exception as e:  # a broken check must not hide the others
            out[name] = result('error', error=repr(e))
    out['_summary'] = {s: [k for k, v in out.items() if v['status'] == s]
                       for s in ('pass', 'partial', 'missing', 'fail', 'error')}
    print(json.dumps(out, indent=2))


if __name__ == '__main__':
    main()
