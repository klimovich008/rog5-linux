#!/usr/bin/env python3
"""Non-cellular hardware matrix for the ROG5 production kernel.

Read-only functional probes, one per component. Each returns
{status: pass|partial|missing, evidence: ...}; nothing here writes to
hardware except one CP_NOP GPU submit. Output is JSON on stdout; exit 0
whatever the matrix says.
"""
import glob, json, os, re, subprocess, sys, time


def sh(cmd):
    return subprocess.run(cmd, shell=True, capture_output=True, text=True).stdout.strip()


def rd(path, default=''):
    try:
        with open(path) as f:
            return f.read().strip()
    except OSError:
        return default


def result(status, **evidence):
    return {'status': status, 'evidence': evidence}


def display():
    st = {c: rd(c + '/status') for c in glob.glob('/sys/class/drm/card*-DSI-*')}
    modes = {c: rd(c + '/modes').splitlines()[:1] for c in st}
    ok = any(v == 'connected' for v in st.values())
    bl = {b: rd(b + '/brightness') + '/' + rd(b + '/max_brightness') for b in glob.glob('/sys/class/backlight/*')}
    return result('pass' if ok and bl else 'partial' if ok else 'missing', connectors=st, modes=modes, backlight=bl)


def gpu():
    probe = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'gpu-recovery-probe.py')
    out = subprocess.run([sys.executable, probe, 'nop'], capture_output=True, text=True)
    renderer = sh("eglinfo -B 2>/dev/null | grep -m1 'OpenGL ES profile renderer'") or sh(
        "glxinfo -B 2>/dev/null | grep -m1 renderer")
    df = glob.glob('/sys/class/devfreq/*gpu*')
    return result('pass' if out.returncode == 0 else 'missing', nop=out.stdout[-200:], renderer=renderer,
                  devfreq={d: rd(d + '/cur_freq') for d in df})


def touch():
    dev = [p for p in glob.glob('/sys/class/input/event*/device/name') if 'fts' in rd(p).lower()]
    return result('pass' if dev else 'missing', devices=[rd(p) for p in dev])


def buttons():
    names = [rd(p) for p in glob.glob('/sys/class/input/event*/device/name')]
    keys = [n for n in names if re.search(r'gpio.keys|pon|pwrkey|resin|volume', n, re.I)]
    power = [n for n in keys if re.search(r'pon|pwrkey', n, re.I)]
    return result('pass' if power and len(keys) >= 2 else 'partial' if keys else 'missing', devices=keys,
                  power_key=bool(power))


def wifi():
    links = [p.split('/')[4] for p in glob.glob('/sys/class/net/*/wireless')]
    link = links[0] if links else ''
    state = rd(f'/sys/class/net/{link}/operstate') if link else ''
    # The kit's wpa_supplicant has no wpa_cli socket; ask the driver instead.
    assoc = sh(f'iw dev {link} link 2>/dev/null | grep -E "Connected to|freq:|signal:|tx bitrate:"') if link else ''
    ip = sh(f'ip -4 -br addr show {link} 2>/dev/null') if link else ''
    ok = state == 'up' and 'Connected to' in assoc and '.' in ip
    return result('pass' if ok else 'partial' if link else 'missing', interface=link, operstate=state,
                  link=assoc, addr=ip)


def bluetooth():
    hci = [os.path.basename(p) for p in glob.glob('/sys/class/bluetooth/hci*')]
    up = sh('cat /sys/class/bluetooth/hci0/../../*/rfkill*/state 2>/dev/null')
    return result('pass' if hci else 'missing', controllers=hci, rfkill=up)


def audio():
    cards = rd('/proc/asound/cards')
    pcm = rd('/proc/asound/pcm')
    real = cards and 'no soundcards' not in cards
    return result('pass' if real and 'playback' in pcm else 'partial' if real else 'missing',
                  cards=cards.splitlines()[:4], pcm=pcm.splitlines()[:6])


def power_supply():
    out = {}
    for p in glob.glob('/sys/class/power_supply/*'):
        out[os.path.basename(p)] = {k: rd(f'{p}/{k}') for k in
                                    ('type', 'status', 'capacity', 'voltage_now', 'current_now', 'online', 'temp')
                                    if os.path.exists(f'{p}/{k}')}
    bat = [v for v in out.values() if v.get('type') == 'Battery']
    ok = bat and bat[0].get('capacity') and bat[0].get('status')
    return result('pass' if ok else 'partial' if out else 'missing', supplies=out)


def usb():
    udc = {os.path.basename(p): rd(p + '/state') for p in glob.glob('/sys/class/udc/*')}
    roles = {os.path.basename(os.path.dirname(p)): rd(p) for p in glob.glob('/sys/class/usb_role/*/role')}
    return result('pass' if any(v == 'configured' for v in udc.values()) else 'partial' if udc else 'missing',
                  udc=udc, roles=roles)


def storage():
    ufs = glob.glob('/sys/bus/platform/drivers/ufshcd-qcom/*.ufshc*')
    return result('pass' if ufs else 'missing', ufs=ufs, root=sh('findmnt -no SOURCE,FSTYPE /'))


def rtc():
    r = rd('/sys/class/rtc/rtc0/name')
    trusted = os.path.exists('/run/rog5-rtc-time.trusted')
    return result('pass' if r and trusted else 'partial' if r else 'missing', rtc=r, time_trusted=trusted,
                  ntp=sh('timedatectl show -p NTPSynchronized --value'))


def vibration():
    ff = [p for p in glob.glob('/sys/class/input/event*/device') if os.path.exists(p + '/capabilities/ff')
          and rd(p + '/capabilities/ff') not in ('', '0')]
    leds = [p for p in glob.glob('/sys/class/leds/*') if re.search('vib', p)]
    return result('pass' if ff or leds else 'missing', ff_devices=[rd(p + '/name') for p in ff], leds=leds)


def sensors():
    # Light/proximity on I2C (IIO); motion sensors behind the SLPI (SSC over QRTR).
    iio = {os.path.basename(p): rd(p + '/name') for p in glob.glob('/sys/bus/iio/devices/iio:device*')}
    ssc_seen = {}
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import ssc
        for t in ('accel', 'gyro', 'mag'):
            samples = ssc.read(t, 25, 1.5)
            last = samples[-1][0] if samples else []
            ssc_seen[t] = dict(samples=len(samples), last=[round(x, 3) for x in last[:3]])
    except (OSError, SystemExit, ImportError) as e:
        ssc_seen['error'] = repr(e)
    accel = ssc_seen.get('accel', {}).get('last', [])
    g = sum(x * x for x in accel) ** 0.5 if len(accel) == 3 else 0
    motion = g > 7 and all(ssc_seen.get(t, {}).get('samples') for t in ('gyro', 'mag'))
    return result('pass' if iio and motion else 'partial' if iio or motion else 'missing',
                  iio=iio, ssc=ssc_seen, accel_g=round(g, 2))


def thermal_cpufreq():
    zones = {rd(z + '/type'): rd(z + '/temp') for z in glob.glob('/sys/class/thermal/thermal_zone*')}
    pol = {os.path.basename(p): (rd(p + '/scaling_governor'), rd(p + '/scaling_cur_freq'), rd(p + '/scaling_max_freq'))
           for p in glob.glob('/sys/devices/system/cpu/cpufreq/policy*')}
    idle = [rd(p) for p in sorted(glob.glob('/sys/devices/system/cpu/cpu0/cpuidle/state*/name'))]
    ok = zones and len(pol) >= 3 and len(idle) >= 2
    return result('pass' if ok else 'partial' if zones or pol else 'missing',
                  zones=len(zones), hottest_mC=max((int(v) for v in zones.values() if v.lstrip('-').isdigit()), default=None),
                  cpufreq=pol, cpuidle_states=idle)


def suspend():
    states = rd('/sys/power/state')
    mem = rd('/sys/power/mem_sleep')
    return result('partial' if 'freeze' in states or 'mem' in states else 'missing', state=states, mem_sleep=mem,
                  note='entering suspend is exercised by the bench, not here')


def leds():
    l = [os.path.basename(p) for p in glob.glob('/sys/class/leds/*') if 'mmc' not in p]
    return result('pass' if l else 'missing', leds=l)


def remoteprocs():
    rp = {rd(p + '/name'): rd(p + '/state') for p in glob.glob('/sys/class/remoteproc/remoteproc*')}
    return result('pass' if rp and all(v == 'running' for v in rp.values()) else 'partial' if rp else 'missing',
                  remoteprocs=rp)


def nfc():
    return result('pass' if glob.glob('/sys/class/nfc/nfc*') else 'missing', devices=glob.glob('/sys/class/nfc/*'))


def cameras():
    v4l = {os.path.basename(p): rd(p + '/name') for p in glob.glob('/sys/class/video4linux/*')}
    return result('pass' if any('cam' in n.lower() for n in v4l.values()) else 'missing', v4l=v4l)


def fingerprint():
    return result('missing', note='under-display fingerprint sensor has no mainline driver probe here')


CHECKS = [('display', display), ('gpu', gpu), ('touch', touch), ('buttons', buttons), ('wifi', wifi),
          ('bluetooth', bluetooth), ('audio', audio), ('battery_charger', power_supply), ('usb', usb),
          ('storage', storage), ('rtc', rtc), ('vibration', vibration), ('sensors', sensors),
          ('thermal_cpufreq', thermal_cpufreq), ('suspend', suspend), ('leds', leds),
          ('dsp_remoteprocs', remoteprocs), ('nfc', nfc), ('cameras', cameras), ('fingerprint', fingerprint)]


def main():
    out = {}
    for name, fn in CHECKS:
        try:
            out[name] = fn()
        except Exception as e:  # a broken probe must not hide the others
            out[name] = result('error', error=repr(e))
    out['_summary'] = {s: sorted(k for k, v in out.items() if v['status'] == s)
                       for s in ('pass', 'partial', 'missing', 'error')}
    print(json.dumps(out, indent=2))


if __name__ == '__main__':
    main()
