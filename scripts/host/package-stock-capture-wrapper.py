#!/usr/bin/env python3
"""Package the stock ASUS 5.4 capture executor into a 128 MiB RAM-boot wrapper.

Offline only: no fastboot, claim, flash or phone access. The wrapper is the
proven recovery ramdisk with initramfs/stock-capture-5.4 as the slot-B loader
executor (no signed bundle, no kexec), rebuilt into the exact ASUS boot
template like package-production-ram-trial.py. --capture-id is written into
the executor, so every capture boot has its own wrapper hash.
"""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

REPO = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('ram_trial', REPO/'scripts/host/package-production-ram-trial.py')
trial = importlib.util.module_from_spec(spec)
spec.loader.exec_module(trial)
need, sha, pinned = trial.need, trial.sha, trial.pinned


def package(args):
    out = Path(args.output)
    need(out.is_absolute() and not out.exists(), 'output must be a new absolute directory')
    need(re.fullmatch(r'[a-z0-9][a-z0-9-]{0,47}', args.capture_id) is not None, 'invalid capture id')
    need(shutil.disk_usage(out.parent).free >= 3 << 30, 'keep a 3 GiB free-space reserve')
    inputs = dict(
        recovery_base=pinned(args.recovery_base, args.recovery_base_sha256, 'recovery base'),
        asus_template=pinned(args.asus_template, args.asus_template_sha256, 'ASUS template'),
        asus_kernel=pinned(args.asus_kernel, args.asus_kernel_sha256, 'ASUS kernel'))
    os.umask(0o077)
    out.mkdir(mode=0o700)
    log = trial.Log(out)
    source = (REPO/'initramfs/stock-capture-5.4').read_text()
    need(source.count('@CAPTURE_ID@') == 1, 'capture id placeholder')
    executor = out/'stock-capture-5.4'
    executor.write_text(source.replace('@CAPTURE_ID@', args.capture_id))
    executor.chmod(0o755)
    recovery = out/'recovery.cpio.gz'
    log.run([REPO/'scripts/device/build-persistent-slotb-recovery-initramfs.sh', inputs['recovery_base'],
             REPO/'initramfs/recovery-init', executor, recovery])
    wrapper = trial.build_wrapper(log, out, inputs, recovery)
    result = dict(status='PASS_PACKAGED_UNBOOTED', capture_id=args.capture_id,
                  wrapper=dict(path=str(wrapper), sha256=sha(wrapper), size=trial.IMAGE_SIZE),
                  executor_sha256=sha(executor), recovery_sha256=sha(recovery),
                  inputs={name: dict(path=str(path), sha256=sha(path)) for name, path in inputs.items()},
                  physical='NOT RUN', flash='forbidden')
    (out/'result.json').write_text(json.dumps(result, indent=2)+'\n')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    for name in ('recovery-base', 'asus-template', 'asus-kernel'):
        parser.add_argument('--'+name, required=True)
        parser.add_argument('--'+name+'-sha256', required=True)
    parser.add_argument('--capture-id', required=True)
    parser.add_argument('--output', required=True)
    print(json.dumps(package(parser.parse_args()), indent=2))


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        print('FAIL '+str(error), file=sys.stderr)
        raise SystemExit(1)
