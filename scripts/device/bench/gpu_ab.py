#!/usr/bin/env python3
"""GPU A/B benchmark for the ROG5, run on the phone as root.

Runs headless vkmark (every default scene) and optionally the Geekbench 6
Vulkan compute benchmark under one GPU devfreq setting, while sampling the
GPU clock, load, temperature and every thermal cooling device that is
throttling. Prints one JSON object; compare runs of different settings.

Usage: gpu_ab.py --label NAME [--governor simple_ondemand|performance]
                 [--min-freq HZ] [--repeat N] [--gb6]
"""
import argparse, glob, json, os, re, subprocess, threading, time

CARD = '/sys/class/drm/card0/device'
DEVFREQ = glob.glob(CARD + '/devfreq/*')[0]
GB6 = '/opt/geekbench/Geekbench-6.7.2-LinuxARMPreview/geekbench6'


def rd(path, default=''):
    try:
        with open(path) as f:
            return f.read().strip()
    except OSError:
        return default


def wr(path, value):
    with open(path, 'w') as f:
        f.write(str(value))


def gpu_temp_mc():
    # Hottest GPU thermal zone (the msm_gpu hwmon exports only the clock).
    temps = [int(rd(z + '/temp', '0') or 0) for z in glob.glob('/sys/class/thermal/thermal_zone*')
             if rd(z + '/type').startswith('gpu')]
    return max(temps, default=0)


class Sampler(threading.Thread):
    def __init__(self):
        super().__init__(daemon=True)
        self.stop, self.samples = threading.Event(), []
        self.cool = [c for c in glob.glob('/sys/class/thermal/cooling_device*')]
        self.skin = next((z for z in glob.glob('/sys/class/thermal/thermal_zone*')
                          if rd(z + '/type') == 'skin-thermal'), None)

    def run(self):
        while not self.stop.is_set():
            throttled = sorted(rd(c + '/type') for c in self.cool if rd(c + '/cur_state', '0') not in ('0', ''))
            self.samples.append({'t': time.time(), 'freq': int(rd(DEVFREQ + '/cur_freq', '0')),
                                 'busy': int(rd(CARD + '/gpu_busy_percent', '0') or 0),
                                 'temp': gpu_temp_mc(),
                                 'screen_on': rd('/sys/class/drm/card1-DSI-1/dpms') == 'On',
                                 'skin': int(rd(self.skin + '/temp', '0') or 0) if self.skin else 0,
                                 'throttled': throttled})
            time.sleep(0.2)

    def summary(self):
        s = self.samples
        if not s:
            return {}
        hist = {}
        for x in s:
            hist[x['freq'] // 1_000_000] = hist.get(x['freq'] // 1_000_000, 0) + 1
        busy = [x for x in s if x['busy'] >= 50]
        thr = {}
        for x in s:
            for t in x['throttled']:
                thr[t] = thr.get(t, 0) + 1
        return {'samples': len(s), 'freq_mhz_hist': dict(sorted(hist.items())),
                'mean_freq_mhz_when_busy': round(sum(x['freq'] for x in busy) / len(busy) / 1e6) if busy else None,
                'mean_busy': round(sum(x['busy'] for x in s) / len(s)), 'max_temp_c': max(x['temp'] for x in s) / 1000,
                'max_skin_c': max(x['skin'] for x in s) / 1000,
                'throttling_cooling_devices': thr,
                # The phone in use during a run skews it (2026-09-29).
                'screen_on_fraction': round(sum(x['screen_on'] for x in s) / len(s), 2)}


def vkmark():
    out = subprocess.run('sudo -u phone vkmark --winsys headless 2>&1', shell=True, capture_output=True,
                         text=True, timeout=600).stdout
    scenes = re.findall(r'\[(\w+)\] (\S*): FPS: (\d+)', out)
    score = re.search(r'vkmark Score:\s*(\d+)', out)
    return {'score': int(score.group(1)) if score else None,
            'scenes': {f'{n} {o}': int(f) for n, o, f in scenes}}


def gb6():
    out = subprocess.run(f'{GB6} --gpu Vulkan 2>&1', shell=True, capture_output=True,
                         text=True, timeout=1200).stdout
    score = re.search(r'Vulkan Score\s+(\d+)', out)
    url = re.search(r'https://browser\.geekbench\.com/\S+', out)
    return {'score': int(score.group(1)) if score else None, 'url': url.group(0) if url else None,
            'tail': out.strip().splitlines()[-3:]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--label', required=True)
    ap.add_argument('--governor')
    ap.add_argument('--min-freq', type=int)
    ap.add_argument('--repeat', type=int, default=2)
    ap.add_argument('--gb6', action='store_true')
    a = ap.parse_args()
    saved = {k: rd(f'{DEVFREQ}/{k}') for k in ('governor', 'min_freq')}
    try:
        if a.governor:
            wr(f'{DEVFREQ}/governor', a.governor)
        if a.min_freq:
            wr(f'{DEVFREQ}/min_freq', a.min_freq)
        time.sleep(2)
        bundle = re.search(r'rog5\.bundle=(\S+)', rd('/proc/cmdline'))
        res = {'label': a.label, 'bundle': bundle.group(1) if bundle else None, 'governor': rd(f'{DEVFREQ}/governor'),
               'min_freq': rd(f'{DEVFREQ}/min_freq'), 'start_temp_c': gpu_temp_mc() / 1000,
               'mesa': subprocess.run("pacman -Q mesa vulkan-freedreno 2>/dev/null | tr '\\n' ' '", shell=True,
                                      capture_output=True, text=True).stdout.strip()}
        runs = []
        for _ in range(a.repeat):
            s = Sampler(); s.start()
            r = vkmark()
            s.stop.set(); s.join()
            r['monitor'] = s.summary()
            runs.append(r)
            time.sleep(20)  # let it cool a little between runs
        res['vkmark'] = runs
        if a.gb6:
            s = Sampler(); s.start()
            r = gb6()
            s.stop.set(); s.join()
            r['monitor'] = s.summary()
            res['gb6_vulkan'] = r
        print(json.dumps(res, indent=1))
    finally:
        wr(f'{DEVFREQ}/governor', saved['governor'])
        if saved['min_freq']:
            wr(f'{DEVFREQ}/min_freq', saved['min_freq'])


if __name__ == '__main__':
    main()
