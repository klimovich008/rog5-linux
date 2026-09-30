#!/usr/bin/env python3
"""Package one signed production bundle into a 128 MiB RAM-boot wrapper.

Offline only: no fastboot, claim, flash or phone access. Every input is
hash-pinned on the command line. The output directory must be new.

Steps: sign the bundle with the existing packager; embed it in the proven
recovery ramdisk (existing-recovery-ram loader path); rebuild the exact ASUS
boot template around the ASUS 5.4 wrapper kernel; add the unsigned AVB
footer at the reviewed 128 MiB envelope; then re-verify the signed bundle
with the wrapper's own trust key and the host build of rog5-bundle-verify.
"""
import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

REPO = Path(__file__).resolve().parents[2]
TOOLS = REPO/'artifacts/android-boot-tools-v1'
IMAGE_SIZE = 134217728
# The reference phone's loader key. The key a bundle must be signed with is
# the one the recovery base embeds (etc/rog5/recovery-bundle-ed25519.pub),
# so another phone's wrapper and key work without editing this file.
TRUST_RAW_SHA256 = 'cc1bca69dadbb0ae6f221a3ac5866d0edfebabd9bf96a9e0ef2747e8283f6054'
TRUST_MEMBER = 'etc/rog5/recovery-bundle-ed25519.pub'
# The reference phone's recovery base; another base is pinned by its caller.
REFERENCE_RECOVERY_BASE_SHA256 = 'd2f46588b46b615eae907ef98e2108fbcc06efc330ffa40136f6e89bdc39ddbc'


def wrapper_sources(log, out, device_profile, recovery_base_sha256):
    """The recovery init and the builder environment for this phone.

    With a device profile the wrapper's recovery init and selector loader are
    rendered with it (scripts/host/rog5-device-profile); a recovery base other
    than the reference one is pinned by the hash its caller gave.
    """
    init = REPO/'initramfs/recovery-init'
    env = dict(os.environ)
    env.pop('ROG5_DEVICE_PROFILE', None)
    env.pop('ROG5_RECOVERY_BASE_SHA256', None)
    if device_profile:
        profile = Path(device_profile).resolve()
        rendered = out/'recovery-init.rendered'
        log.run([sys.executable, REPO/'scripts/host/rog5-device-profile', 'render', '--profile', profile,
                 init, rendered])
        init = rendered
        env['ROG5_DEVICE_PROFILE'] = str(profile)
    if recovery_base_sha256 != REFERENCE_RECOVERY_BASE_SHA256:
        env['ROG5_RECOVERY_BASE_SHA256'] = recovery_base_sha256
    return init, env
SHA = re.compile(r'[0-9a-f]{64}')
NAME = re.compile(r'[a-z0-9][a-z0-9._-]{0,63}')


def need(ok, why):
    if not ok:
        raise ValueError(why)


def newc_member(archive, wanted):
    """Bytes of one regular member of a gzip newc cpio archive, or None."""
    data = gzip.decompress(archive)
    offset = 0
    while offset + 110 <= len(data):
        need(data[offset:offset+6] in (b'070701', b'070702'), 'recovery base is not newc cpio')
        fields = [int(data[offset+6+8*i:offset+14+8*i], 16) for i in range(13)]
        mode, size, name_size = fields[1], fields[6], fields[11]
        name_end = offset + 110 + name_size
        name = data[offset+110:name_end-1].decode('utf-8', 'replace')
        start = (name_end + 3) & ~3
        if name == 'TRAILER!!!':
            return None
        if name.lstrip('./') == wanted:
            need(mode & 0o170000 == 0o100000, wanted+' is not a regular file')
            return data[start:start+size]
        offset = (start + size + 3) & ~3
    return None


def wrapper_trust_sha256(recovery_base):
    """SHA-256 of the raw Ed25519 key the wrapper's loader verifies with."""
    key = newc_member(Path(recovery_base).read_bytes(), TRUST_MEMBER)
    need(key is not None and len(key) == 32, f'recovery base carries no 32-byte {TRUST_MEMBER}')
    return hashlib.sha256(key).hexdigest()


def sha(path):
    digest = hashlib.sha256()
    with open(path, 'rb') as source:
        for chunk in iter(lambda: source.read(1 << 20), b''):
            digest.update(chunk)
    return digest.hexdigest()


def pinned(path, expected, label):
    path = Path(path)
    need(path.is_absolute() and path.is_file() and not path.is_symlink(), label+' must be an absolute regular file')
    need(SHA.fullmatch(expected or '') is not None, label+' needs a SHA-256 pin')
    need(sha(path) == expected, label+' does not match its pin')
    return path


class Log:
    def __init__(self, out):
        self.path = out/'commands.log'

    def run(self, argv, capture=False, **kwargs):
        argv = [str(item) for item in argv]
        with self.path.open('a') as log:
            log.write('$ '+' '.join(argv)+'\n')
        result = subprocess.run(argv, stdin=subprocess.DEVNULL, capture_output=True, timeout=600, **kwargs)
        with self.path.open('ab') as log:
            log.write(result.stdout[-20000:]+result.stderr[-20000:]+b'\n')
        need(result.returncode == 0, 'command failed: '+' '.join(argv[:3])+': '
             + result.stderr.decode(errors='replace')[-600:])
        return result.stdout if capture else None


def build_wrapper(log, out, inputs, recovery):
    """Rebuild the ASUS boot template around the 5.4 kernel and RECOVERY."""
    raw_args = log.run(['python3', TOOLS/'unpack_bootimg.py', '--boot_img', inputs['asus_template'],
                        '--out', out/'template', '--format=mkbootimg', '--null'], capture=True)
    need(raw_args.endswith(b'\0'), 'mkbootimg argument framing')
    boot_args = raw_args[:-1].decode().split('\0')
    for flag, value in (('--kernel', inputs['asus_kernel']), ('--ramdisk', recovery)):
        need(boot_args.count(flag) == 1 and boot_args.index(flag)+1 < len(boot_args), 'template '+flag)
        boot_args[boot_args.index(flag)+1] = str(value)
    need('--output' not in boot_args, 'unexpected template output option')
    raw = out/'boot.raw.img'
    log.run(['python3', TOOLS/'mkbootimg.py', *boot_args, '--output', raw])
    maximum = int(log.run(['python3', TOOLS/'avbtool.py', 'add_hash_footer', '--partition_size',
                           str(IMAGE_SIZE), '--calc_max_image_size'], capture=True).decode().strip())
    need(raw.stat().st_size <= maximum, 'wrapper does not fit the 128 MiB envelope')
    wrapper = out/'boot-ram-128m.img'
    shutil.copyfile(raw, wrapper)
    log.run(['python3', TOOLS/'avbtool.py', 'add_hash_footer', '--image', wrapper, '--partition_name', 'boot',
             '--partition_size', str(IMAGE_SIZE), '--algorithm', 'NONE', '--salt', sha(raw)])
    need(wrapper.stat().st_size == IMAGE_SIZE, 'AVB envelope size')
    # avbtool resolves the partition by name next to the image it verifies.
    staged = out/'avb-verify'
    staged.mkdir(mode=0o700)
    shutil.copyfile(wrapper, staged/'boot.img')
    log.run(['python3', TOOLS/'avbtool.py', 'verify_image', '--image', staged/'boot.img'])
    need(sha(staged/'boot.img') == sha(wrapper), 'AVB staging copy changed')
    check = out/'check'
    log.run(['python3', TOOLS/'unpack_bootimg.py', '--boot_img', raw, '--out', check])
    need(sha(check/'kernel') == sha(inputs['asus_kernel']) and sha(check/'ramdisk') == sha(recovery),
         'wrapper payload bytes')
    return wrapper


def package(args):
    out = Path(args.output)
    need(out.is_absolute() and not out.exists(), 'output must be a new absolute directory')
    need(NAME.fullmatch(args.bundle) is not None, 'invalid bundle name')
    need(shutil.disk_usage(out.parent).free >= 3 << 30, 'keep a 3 GiB free-space reserve')
    inputs = dict(
        image=pinned(args.image, args.image_sha256, 'Image'),
        dtb=pinned(args.dtb, args.dtb_sha256, 'DTB'),
        initramfs=pinned(args.initramfs, args.initramfs_sha256, 'initramfs'),
        recovery_base=pinned(args.recovery_base, args.recovery_base_sha256, 'recovery base'),
        asus_template=pinned(args.asus_template, args.asus_template_sha256, 'ASUS template'),
        asus_kernel=pinned(args.asus_kernel, args.asus_kernel_sha256, 'ASUS kernel'))
    key = Path(args.private_key)
    need(key.is_absolute() and key.is_file() and not key.is_symlink(), 'private key path')
    public = subprocess.run(['openssl', 'pkey', '-in', str(key), '-pubout', '-outform', 'DER'],
                            capture_output=True, check=True).stdout
    trust_sha256 = wrapper_trust_sha256(inputs['recovery_base'])
    need(hashlib.sha256(public[-32:]).hexdigest() == trust_sha256,
         'signing key is not the wrapper trust key')
    os.umask(0o077)
    out.mkdir(mode=0o700)
    log = Log(out)
    recipe = dict(bundle=args.bundle, profile='persistent-root-ro-v1', image=str(inputs['image']),
                  dtb=str(inputs['dtb']), initramfs=str(inputs['initramfs']),
                  target_id=args.bundle, target_release=args.release,
                  rollback_timeout=str(args.rollback_timeout), target_timeout=str(args.target_timeout),
                  a660_command_manifest_sha256='0'*64, root_generation='none',
                  root_tree_sha256='0'*64, root_seal_sha256='0'*64, root_tree_entries='0',
                  root_subtree='none')
    (out/'recipe.json').write_text(json.dumps(recipe, indent=2, sort_keys=True)+'\n')
    bundles = out/'bundles'
    bundles.mkdir(mode=0o700)
    signed = log.run(['python3', '-B', REPO/'scripts/host/prepare-recovery-runtime-bundle.py',
                      '--config', out/'recipe.json', '--private-key', key, '--bundle-root', bundles],
                     capture=True).decode()
    rows = dict(line.split('=', 1) for line in signed.splitlines() if '=' in line)
    need(rows.get('trust_key_sha256') == trust_sha256, 'packager trust key mismatch')
    bundle = bundles/args.bundle
    manifest_sha256 = sha(bundle/'manifest')

    recovery = out/'recovery.cpio.gz'
    recovery_init, env = wrapper_sources(log, out, getattr(args, 'device_profile', None), sha(inputs['recovery_base']))
    log.run([REPO/'scripts/device/build-persistent-slotb-recovery-initramfs.sh', inputs['recovery_base'],
             recovery_init, 'embedded-ram', recovery, bundle], env=env)

    wrapper = build_wrapper(log, out, inputs, recovery)

    # Re-verify with the wrapper's own trust key using the host verifier build.
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        verifier = tmp/'rog5-bundle-verify'
        subprocess.run(['cc', '-O2', '-DROG5_BUNDLE_TESTING=1', '-o', str(verifier),
                        str(REPO/'tools/recovery_control/rog5-bundle-verify.c'), '-lcrypto', '-lz'],
                       check=True, capture_output=True)
        trust = tmp/'trust.raw'
        trust.write_bytes(public[-32:])
        trust.chmod(0o644)
        plan = log.run([verifier, '--bundle-root', bundles, '--trust-key', trust, args.bundle,
                        manifest_sha256], capture=True).decode()
    need(f'target_release={args.release}\n' in plan and f'bundle={args.bundle}\n' in plan,
         'verified plan identity')
    (out/'verified-plan.txt').write_text(plan)
    result = dict(status='PASS_PACKAGED_UNBOOTED', bundle=args.bundle, release=args.release,
                  manifest_sha256=manifest_sha256,
                  wrapper=dict(path=str(wrapper), sha256=sha(wrapper), size=IMAGE_SIZE),
                  recovery_sha256=sha(recovery),
                  inputs={name: dict(path=str(path), sha256=sha(path)) for name, path in inputs.items()},
                  cmdline=re.search(r'^cmdline=(.*)$', plan, re.M)[1],
                  physical='NOT RUN', flash='forbidden')
    (out/'result.json').write_text(json.dumps(result, indent=2)+'\n')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    for name in ('image', 'dtb', 'initramfs', 'recovery-base', 'asus-template', 'asus-kernel'):
        parser.add_argument('--'+name, required=True)
        parser.add_argument('--'+name+'-sha256', required=True)
    parser.add_argument('--private-key', required=True)
    parser.add_argument('--device-profile', help='render the wrapper sources for this device profile '
                        '(default: the reference phone)')
    parser.add_argument('--bundle', required=True)
    parser.add_argument('--release', default='7.1.4-rog5-production')
    parser.add_argument('--rollback-timeout', type=int, default=900)
    parser.add_argument('--target-timeout', type=int, default=600)
    parser.add_argument('--output', required=True)
    result = package(parser.parse_args())
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        print('FAIL '+str(error), file=sys.stderr)
        raise SystemExit(1)
