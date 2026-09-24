#!/usr/bin/env python3
"""CPU, memory and GPU throughput (run on the phone as root).

  cpu     openssl SHA-256 on 16 KiB blocks, one thread pinned to an A55 (cpu0),
          an A78 (cpu4) and the X1 (cpu7), then eight processes
  memory  perf bench mem memcpy/memset, 64 MiB, pinned to the X1 and an A55:
          the DDR-sensitive numbers (bwmon and the interconnect votes)
  gpu     glmark2-es2-drm, full screen on the display card (msm_dpu; card0 is
          the GPU-only device), a fixed scene list. Needs the display: Denial
          is stopped for the run and started again afterwards.

Also records the CPU frequency limits, the interconnect aggregate for DDR (EBI)
before and after, and the highest EBI vote seen during each memory run.
JSON on stdout; --skip gpu etc. to leave parts out.
"""
import argparse, json, os, re, subprocess, time

DISPLAY_CARD = '/dev/dri/by-path/platform-ae01000.display-controller-card'

GLMARK_SCENES = ['build:use-vbo=true', 'texture:texture-filter=linear', 'shading:shading=phong',
                 'bump:bump-render=normals', 'effect2d:kernel=0,1,0;1,-4,1;0,1,0;', 'pulsar:quads=5',
                 'desktop:effect=blur:blur-radius=5:passes=1', 'refract', 'terrain']


def sh(command, timeout=300):
    r = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=timeout)
    return r.returncode, r.stdout, r.stderr


def ebi():
    try:
        text = open('/sys/kernel/debug/interconnect/interconnect_summary').read()
    except OSError:
        return None
    m = re.search(r'^ebi@\S+\s+(\d+)\s+(\d+)', text, re.M)
    return {'avg_kBps': int(m.group(1)), 'peak_kBps': int(m.group(2))} if m else None


def sha256(cpus, multi=0):
    cmd = f'taskset -c {cpus} openssl speed -seconds 3 -bytes 16384 -evp sha256'
    if multi:
        cmd = f'openssl speed -seconds 3 -bytes 16384 -multi {multi} -evp sha256'
    code, out, err = sh(cmd, 120)
    # last table row: "sha256   123456.78k"
    rows = [l for l in out.splitlines() if l.lower().startswith(('sha256', 'evp_sha256', 'sha2-256'))]
    m = re.search(r'([\d.]+)k\s*$', rows[-1]) if rows else None
    return round(float(m.group(1)) / 1024, 1) if m else f'rc {code}: {err[-200:]}'


def memory(cpu, op, peaks):
    """GB/s, and the highest EBI peak vote seen while it ran (bwmon at work)."""
    proc = subprocess.Popen(f'taskset -c {cpu} perf bench mem {op} -s 64MB -l 20', shell=True,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    top = 0
    while proc.poll() is None:
        top = max(top, (ebi() or {}).get('peak_kBps', 0))
        time.sleep(0.05)
    out = proc.stdout.read()
    peaks[f'{op}_cpu{cpu}'] = top
    m = re.search(r'([\d.]+) GB/sec', out)
    return float(m.group(1)) if m else f'rc {proc.returncode}: {out[-200:]}'


def gpu():
    result = {}
    was_active = sh('systemctl is-active rog5-denial.service')[1].strip() == 'active'
    if was_active:
        sh('systemctl stop rog5-denial.service', 60)
        time.sleep(1)
    try:
        args = ' '.join(f"-b '{s}'" for s in GLMARK_SCENES)
        card = os.path.realpath(DISPLAY_CARD)
        code, out, err = sh(f'glmark2-es2-drm --winsys-options drm-device={card} {args}', 900)
        scenes = {}
        for line in out.splitlines():
            m = re.match(r'\s*\[(\S+)\] (.*?): FPS: (\d+) FrameTime: ([\d.]+) ms', line)
            if m:
                scenes[f'{m.group(1)} {m.group(2)}'.strip()] = int(m.group(3))
        score = re.search(r'glmark2 Score: (\d+)', out)
        result = {'score': int(score.group(1)) if score else None, 'scenes_fps': scenes,
                  'renderer': (re.search(r'GL_RENDERER:\s*(.*)', out) or [None, None])[1]}
        if not score:
            result['error'] = f'rc {code}: {(out + err)[-400:]}'
    finally:
        if was_active:
            sh('systemctl start rog5-denial.service', 60)
    result['denial_restarted'] = was_active
    return result


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--skip', default='')
    ap.add_argument('--label', default='')
    a = ap.parse_args()
    skip = set(a.skip.split(','))
    report = {'label': a.label, 'time': time.strftime('%Y-%m-%dT%H:%M:%S'),
              'kernel': sh('uname -r')[1].strip(),
              'cpufreq_max_khz': {c: int(open(f'/sys/devices/system/cpu/cpu{c}/cpufreq/scaling_max_freq').read())
                                  for c in (0, 4, 7)},
              'ebi_before': ebi()}
    if 'cpu' not in skip:
        report['sha256_MBps'] = {'a55_cpu0': sha256(0), 'a78_cpu4': sha256(4), 'x1_cpu7': sha256(7),
                                 'all_8': sha256('0-7', multi=8)}
    if 'memory' not in skip:
        peaks = {}
        report['memory_GBps'] = {f'{op}_{name}': memory(cpu, op, peaks)
                                 for op in ('memcpy', 'memset') for name, cpu in (('x1', 7), ('a55', 0))}
        report['ebi_peak_kBps_during_memory'] = peaks
    if 'gpu' not in skip:
        report['glmark2'] = gpu()
    report['ebi_after'] = ebi()
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
