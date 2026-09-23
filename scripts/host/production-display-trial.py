#!/usr/bin/env python3
"""Bounded OLED + Adreno 660 bring-up on a running production target.

Runs one SSH command per step against a production-display boot and records
every step's output plus a filtered kernel-log tail into a new evidence
directory. The order follows the reviewed findings: REFGEN, then GPUCC, then
a reprobe of the GPU SMMU, whose deferred probe timed out before GPUCC existed.
arm-smmu suppresses its bind attribute, so the reprobe goes through
drivers_probe (trial d1: bind gave EPERM, drivers_probe bound it and the GPU
followed). Then msm with separate_gpu_kms=1, the panel, a short visible
brightness check and a single render-node open, which runs the first GMU/zap
start. The panel is always set back to brightness 0 at the end. No retries,
reprobes of other devices, or writes outside sysfs/modprobe.
"""
import argparse
import importlib.util
import json
from pathlib import Path
import sys
import time

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('production_ram_trial', HERE/'production-ram-trial.py')
TRIAL = importlib.util.module_from_spec(spec)
spec.loader.exec_module(TRIAL)

M = 'modprobe -d /run/rog5-modules'
LOG = "dmesg | grep -iE 'msm|dsi|dpu|mdss|panel|ams678|drm|adreno|a6xx|gmu|zap|smmu|iommu|gpucc|refgen|backlight|fb0|firmware' | tail -n 60"
STEPS = [
    ('baseline', "uname -r; test -f /run/rog5-modules/lib/modules/$(uname -r)/modules.dep && echo tree-ok; "
                 "ls /run/rog5-charge-firmware/qcom /run/rog5-charge-firmware/qcom/sm8350; "
                 "cat /sys/module/firmware_class/parameters/path; ls /sys/class/drm; "
                 "ls -l /sys/bus/platform/devices/3da0000.iommu/driver 2>&1; cut -d' ' -f1 /proc/modules | tr '\\n' ' '", True),
    ('refgen', f"{M} qcom_refgen_regulator && echo LOADED", True),
    ('gpucc', f"{M} gpucc_sm8350 && echo LOADED; sleep 1; ls -l /sys/bus/platform/devices/3d90000.clock-controller/driver", True),
    ('smmu-probe', "d=/sys/bus/platform/devices/3da0000.iommu; if [ ! -e $d/driver ]; then "
                   "echo 3da0000.iommu > /sys/bus/platform/drivers_probe; sleep 2; fi; "
                   "[ -e $d/driver ] && echo PROBED; ls -l /sys/bus/platform/devices/3d00000.gpu/iommu_group "
                   "/sys/bus/platform/devices/3d6a000.gmu/iommu_group 2>&1", False),
    ('msm', f"{M} msm separate_gpu_kms=1 && echo LOADED; sleep 3; ls /sys/class/drm; "
            "cat /sys/module/msm/parameters/separate_gpu_kms", True),
    ('panel', f"{M} panel_asus_rog5_ams678 && echo LOADED; sleep 6; ls /sys/class/drm /sys/class/backlight /sys/class/graphics 2>&1; "
              "for c in /sys/class/drm/card*-*; do echo \"$c $(cat $c/status 2>/dev/null) $(cat $c/enabled 2>/dev/null)\"; "
              "head -3 $c/modes 2>/dev/null; done", True),
    ('brightness', "b=$(ls -d /sys/class/backlight/* | head -1); echo $b; cat $b/max_brightness $b/brightness; "
                   "m=$(cat $b/max_brightness); echo $((m/4)) > $b/brightness; cat $b/brightness; sleep 20; "
                   "echo 0 > $b/brightness; cat $b/brightness", False),
    ('gpu-open', "for i in 1 2 3 4 5; do ls /dev/dri/renderD* >/dev/null 2>&1 && break; sleep 1; done; ls -l /dev/dri; r=$(ls /dev/dri/renderD* 2>/dev/null | head -1); echo render=$r; "
                 "[ -n \"$r\" ] && { exec 3<$r; sleep 4; exec 3<&-; echo OPENED; }", False),
]


def run(address, evidence, name, command, timeout=90):
    started = time.monotonic()
    result = TRIAL.ssh(address, command+'; echo ---LOG---; '+LOG, timeout)
    record = dict(step=name, t=TRIAL.now(), seconds=round(time.monotonic()-started, 2),
                  returncode=result.returncode, stdout=result.stdout.decode(errors='replace'),
                  stderr=result.stderr.decode(errors='replace')[-2000:])
    (evidence/f'{len(list(evidence.glob("*.json"))):02d}-{name}.json').write_text(json.dumps(record, indent=2)+'\n')
    head = record['stdout'].split('---LOG---')[0].strip().replace('\n', ' | ')[:300]
    print(f"{record['t']} {name} rc={result.returncode} {record['seconds']}s: {head}", flush=True)
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--evidence', required=True)
    parser.add_argument('--address', default='169.254.77.2')
    args = parser.parse_args()
    evidence = Path(args.evidence)
    TRIAL.need(evidence.is_absolute() and not evidence.exists(), 'evidence must be a new absolute directory')
    TRIAL.need(TRIAL.usb_state() == 'target', 'no running target on the approved port')
    evidence.mkdir(mode=0o700, parents=True)
    release = TRIAL.ssh(args.address, 'uname -r', 20).stdout.decode().strip()
    TRIAL.need(release == '7.1.4-rog5-production', 'target is not the production kernel: '+release)
    summary = dict(release=release, steps=[])
    try:
        for name, command, critical in STEPS:
            record = run(args.address, evidence, name, command)
            marker = dict(refgen='LOADED', gpucc='LOADED', msm='LOADED', panel='LOADED', **{'smmu-probe': 'PROBED', 'gpu-open': 'OPENED'}).get(name)
            ok = record['returncode'] == 0 and (marker is None or marker in record['stdout'].split('---LOG---')[0])
            summary['steps'].append(dict(step=name, ok=ok, returncode=record['returncode']))
            if not ok and critical:
                print(f'{TRIAL.now()} stopping after failed critical step {name}', flush=True)
                break
    finally:
        cleanup = TRIAL.ssh(args.address, 'for b in /sys/class/backlight/*; do [ -w $b/brightness ] && echo 0 > $b/brightness; done; '
                            'dmesg', 60)
        (evidence/'dmesg-final.txt').write_bytes(cleanup.stdout)
        summary['final_usb'] = TRIAL.usb_state()
        (evidence/'summary.json').write_text(json.dumps(summary, indent=2)+'\n')
        print(json.dumps(summary), flush=True)


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError) as error:
        print('FAIL '+str(error), file=sys.stderr)
        raise SystemExit(1)
