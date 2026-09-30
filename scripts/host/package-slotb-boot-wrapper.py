#!/usr/bin/env python3
"""Package the persistent slot-B boot wrapper (boot_b) and its RAM-trial twin.

Offline only: no fastboot, claim, flash or phone access. Every input is
hash-pinned on the command line and the output directory must be new.

This is how the installed boot_b wrapper dcc487f1 (2026-09-06) was built,
now as one script; with the sources of 14c80891 it rebuilds dcc487f1 byte for
byte:
1. build-persistent-slotb-recovery-initramfs.sh with the local p24 loader
   executor (initramfs/persistent-slotb-local-loader), under umask 077 and C
   collation, keeping the trial-state helper release the installed wrapper
   carries (--trial-helper, v2 in dcc487f1).
2. repack-android-boot-v3.sh around the ASUS 5.4 kernel and the ASUS boot
   template: boot_b-96m.avb.img, 100663296 bytes, AVB salt sha256(raw). This
   is the only file a later, separately approved boot_b flash may use.
3. RAM twin boot-ram-128m.img: the same raw boot image with its AVB footer at
   the 128 MiB envelope that production-ram-trial.py boots. Its salt is
   sha256("<raw sha256>:<version>"), so every version name has its own
   one-use claim identity while the kernel and ramdisk bytes stay identical.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import importlib.util

REPO = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('ram_trial', REPO/'scripts/host/package-production-ram-trial.py')
trial = importlib.util.module_from_spec(spec)
spec.loader.exec_module(trial)
need, sha, pinned = trial.need, trial.sha, trial.pinned

TOOLS = trial.TOOLS
FLASH_SIZE = 100663296
RAM_SIZE = trial.IMAGE_SIZE
VERSION = re.compile(r'slotb-wrapper-[a-z0-9][a-z0-9.-]{0,40}')
HELPER = re.compile(r'artifacts/persistent-trial-state-v[1-9][0-9]*/rog5-persistent-trial-state')
SOURCES = ('initramfs/recovery-init', 'initramfs/persistent-slotb-loader-init',
           'initramfs/persistent-slotb-local-loader', 'tools/reboot_bootloader/rog5-reboot-bootloader.c',
           'scripts/device/build-persistent-slotb-recovery-initramfs.sh',
           'scripts/device/repack-android-boot-v3.sh')


def git(*argv):
    result = subprocess.run(['git', '-C', str(REPO), *argv], capture_output=True, text=True)
    return result.stdout.strip() if result.returncode == 0 else 'unavailable'


def unpack(log, image, out):
    info = log.run(['python3', TOOLS/'unpack_bootimg.py', '--boot_img', image, '--out', out],
                   capture=True).decode()
    need('boot image header version: 3' in info.splitlines(), 'boot image header is not v3')
    cmdline = re.search(r'^command line args: (.*)$', info, re.M)
    need(cmdline is not None, 'boot image command line')
    return cmdline[1]


def package(args):
    out = Path(args.output)
    need(out.is_absolute() and not out.exists(), 'output must be a new absolute directory')
    need(VERSION.fullmatch(args.version) is not None, 'version must be slotb-wrapper-<name>')
    need(HELPER.fullmatch(args.trial_helper) is not None, 'trial helper must be a retained release')
    need(shutil.disk_usage(out.parent).free >= 3 << 30, 'keep a 3 GiB free-space reserve')
    inputs = dict(
        recovery_base=pinned(args.recovery_base, args.recovery_base_sha256, 'recovery base'),
        asus_template=pinned(args.asus_template, args.asus_template_sha256, 'ASUS template'),
        asus_kernel=pinned(args.asus_kernel, args.asus_kernel_sha256, 'ASUS kernel'))
    helper = REPO/args.trial_helper
    helper_sha256 = (helper.parent/'SHA256SUMS').read_text().split()[0]
    need(sha(helper) == helper_sha256, 'trial helper does not match its SHA256SUMS')
    dirty = git('status', '--porcelain', '--', *SOURCES)
    os.umask(0o077)
    out.mkdir(mode=0o700)
    log = trial.Log(out)
    recovery_init, env = trial.wrapper_sources(log, out, getattr(args, 'device_profile', None),
                                               sha(inputs['recovery_base']))
    env.update(LC_ALL='C', ROG5_TRIAL_HELPER=args.trial_helper)
    selector_loader = REPO/'initramfs/persistent-slotb-loader-init'
    if getattr(args, 'device_profile', None):
        rendered = out/'selector-loader.rendered'
        log.run([sys.executable, REPO/'scripts/host/rog5-device-profile', 'render', '--profile',
                 Path(args.device_profile).resolve(), selector_loader, rendered])
        selector_loader = rendered

    recovery = out/'recovery.cpio.gz'
    log.run([REPO/'scripts/device/build-persistent-slotb-recovery-initramfs.sh', inputs['recovery_base'],
             recovery_init, REPO/'initramfs/persistent-slotb-local-loader', recovery], env=env)
    root = out/'recovery-root'
    root.mkdir()
    with open(recovery, 'rb') as archive:
        cpio = subprocess.run(['gzip', '-dc'], stdin=archive, capture_output=True, check=True).stdout
    subprocess.run(['cpio', '-idm', '--quiet', '--no-absolute-filenames'], input=cpio, cwd=root, check=True)
    members = {'init': recovery_init,
               'usr/libexec/rog5-selector-v2-loader': selector_loader,
               'usr/libexec/rog5-persistent-slotb-local-loader': REPO/'initramfs/persistent-slotb-local-loader',
               'usr/libexec/rog5-persistent-trial-state': helper}
    for member, source in members.items():
        need(sha(root/member) == sha(source), 'recovery member differs from its source: '+member)
    need((root/'etc/rog5/recovery-mode').read_text() == 'persistent-slotb-loader-v1\n', 'recovery mode')
    need(not (root/'usr/share/rog5/ram-bundles').exists(), 'persistent wrapper must not embed a bundle')

    raw = out/'boot.raw.img'
    flash = out/'boot_b-96m.avb.img'
    log.run([REPO/'scripts/device/repack-android-boot-v3.sh', inputs['asus_template'], inputs['asus_kernel'],
             recovery, TOOLS, TOOLS/'avbtool.py', raw, flash, str(FLASH_SIZE)], env=env)
    need(flash.stat().st_size == FLASH_SIZE, 'flash image size')

    ram = out/'boot-ram-128m.img'
    shutil.copyfile(raw, ram)
    salt = hashlib.sha256(f'{sha(raw)}:{args.version}'.encode()).hexdigest()
    log.run(['python3', TOOLS/'avbtool.py', 'add_hash_footer', '--image', ram, '--partition_name', 'boot',
             '--partition_size', str(RAM_SIZE), '--algorithm', 'NONE', '--salt', salt])
    need(ram.stat().st_size == RAM_SIZE, 'RAM image size')

    template_cmdline = unpack(log, inputs['asus_template'], out/'template')
    for image in (flash, ram):
        staged = out/('avb-verify-'+image.stem)
        staged.mkdir()
        shutil.copyfile(image, staged/'boot.img')
        log.run(['python3', TOOLS/'avbtool.py', 'verify_image', '--image', staged/'boot.img'])
        check = out/('check-'+image.stem)
        need(unpack(log, image, check) == template_cmdline, 'command line differs from the template')
        need(sha(check/'kernel') == sha(inputs['asus_kernel']) and sha(check/'ramdisk') == sha(recovery),
             'wrapper payload bytes')
        with open(image, 'rb') as source:
            need(source.read(raw.stat().st_size) == raw.read_bytes(), 'raw boot image prefix differs')

    result = dict(
        status='PASS_PACKAGED_UNBOOTED', version=args.version,
        source=dict(commit=git('rev-parse', 'HEAD'), wrapper_sources_clean=not dirty,
                    dirty=dirty.splitlines()),
        flash_image=dict(path=str(flash), sha256=sha(flash), size=FLASH_SIZE, partition='boot_b'),
        ram_image=dict(path=str(ram), sha256=sha(ram), size=RAM_SIZE, avb_salt=salt),
        raw_sha256=sha(raw), recovery_sha256=sha(recovery), cmdline=template_cmdline,
        members={member: sha(root/member) for member in members},
        reboot_helper_sha256=sha(root/'usr/libexec/rog5-reboot-bootloader'),
        inputs={name: dict(path=str(path), sha256=sha(path)) for name, path in inputs.items()},
        trial_helper=dict(path=args.trial_helper, sha256=helper_sha256),
        physical='NOT RUN', flash='forbidden without separate user approval')
    shutil.rmtree(root)
    (out/'result.json').write_text(json.dumps(result, indent=2)+'\n')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    for name in ('recovery-base', 'asus-template', 'asus-kernel'):
        parser.add_argument('--'+name, required=True)
        parser.add_argument('--'+name+'-sha256', required=True)
    parser.add_argument('--trial-helper', default='artifacts/persistent-trial-state-v2/rog5-persistent-trial-state')
    parser.add_argument('--version', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--device-profile', help='render recovery-init and the selector loader for this '
                        'device profile (default: the reference phone)')
    print(json.dumps(package(parser.parse_args()), indent=2))


if __name__ == '__main__':
    main()
