#!/usr/bin/env python3
"""Install a signed production bundle as the phone's slot-B default kernel.

The bundle becomes the selector's try-once primary with the signed V11 bundle
as fallback. Its ramdisk must carry the matching trial descriptor
(PRODUCTION_TRIAL_DESCRIPTOR), so each healthy boot commits itself and the
next boot takes it again; a boot that does not commit falls back to V11.

Without --stage this is read-only on p23/p24: it verifies both bundles with
the trust key (V11 fetched from the phone), generates the selector, backs up
the current selector and record, then runs the target script's --inspect and
--preflight with the payload in /run (RAM) and removes that copy. --stage
then performs the one write window (scripts/device/install-default-kernel-on-target.sh)
once: the evidence directory holds INSTALL-ENTERED.json and never allows a
retry. No reboot is done; the next ordinary boot starts the new trial.
"""
import argparse
import gzip
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import time

REPO = Path(__file__).resolve().parents[2]
TARGET_SCRIPT = REPO/'scripts/device/install-default-kernel-on-target.sh'
VERIFIER_SOURCE = REPO/'tools/recovery_control/rog5-bundle-verify.c'
FILES = ('Image', 'board.dtb', 'initramfs.cpio.gz', 'manifest', 'manifest.sig')
FALLBACK = 'persistent-native-root-v11'
TRUST_RAW_SHA256 = 'cc1bca69dadbb0ae6f221a3ac5866d0edfebabd9bf96a9e0ef2747e8283f6054'
P24_UUID = '8b03827a-cc2d-4408-8558-e9b61195f96b'
P24_SIZE = '34359717888'
P23_UUID = '0892bacf-3e02-41b0-84a4-5f05c2df7ce5'
ROOT_MOUNT = '/.rog5/root-ro'
USERDATA_MOUNT = '/.rog5/userdata-rw'
STAGED = 'PASS default kernel {bundle} installed; V11 fallback preserved; p24 relocked; no boot performed\n'
SHA = re.compile(r'[0-9a-f]{64}')
NAME = re.compile(r'[a-z0-9][a-z0-9._-]{0,63}')
VALUE = re.compile(r'[A-Za-z0-9._/:-]{1,200}')


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


SELECTOR = load('rog5_selector', REPO/'scripts/host/build-persistent-wifi-selector.py')


def need(ok, why):
    if not ok:
        raise ValueError(why)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def regular(path):
    info = os.lstat(path)
    need(Path(path).is_file() and not Path(path).is_symlink() and info.st_nlink == 1,
         f'{path} must be a regular file with one link')
    return Path(path).read_bytes()


def descriptor_fields(data):
    rows = data.decode('ascii').split('\n')
    need(len(rows) == 5 and rows[4] == '' and rows[0] == 'format=rog5-persistent-wifi-health-v1'
         and rows[3] == 'mode=try-once', 'trial descriptor format')
    need(rows[1].startswith('trial_id=') and SHA.fullmatch(rows[1][9:]), 'trial id')
    need(rows[2].startswith('primary_bundle=') and NAME.fullmatch(rows[2][15:]) and '..' not in rows[2],
         'primary bundle name')
    return rows[1][9:], rows[2][15:]


def newc_member(archive, wanted):
    """Bytes of one regular member of a gzip newc cpio archive, or None."""
    data = gzip.decompress(archive)
    offset = 0
    while offset + 110 <= len(data):
        need(data[offset:offset+6] in (b'070701', b'070702'), 'initramfs is not newc cpio')
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


def verify_bundle(verifier, trust, root, bundle, manifest_sha256):
    plan = subprocess.run([str(verifier), '--bundle-root', str(root), '--trust-key', str(trust),
                           bundle, manifest_sha256], capture_output=True, timeout=120)
    need(plan.returncode == 0, f'{bundle}: signature or payload verification failed: '
         + plan.stderr.decode(errors='replace')[-300:])
    text = plan.stdout.decode()
    need(f'bundle={bundle}\n' in text, f'{bundle}: verified plan identity')
    return text


def archive_name(bundle, old_sha256):
    return f'wifi-trial-state.archived-before-{bundle}-{old_sha256}'


def render(values):
    """The target script with its exact values prepended."""
    lines = []
    for name, value in sorted(values.items()):
        need(re.fullmatch(r'[a-z0-9_]+', name) and VALUE.fullmatch(str(value)), 'unsafe value '+name)
        lines.append(f"{name}='{value}'")
    body = TARGET_SCRIPT.read_text()
    shebang, rest = body.split('\n', 1)
    return (shebang+'\n'+'\n'.join(lines)+'\n'+rest).encode()


class Phone:
    def __init__(self, address):
        self.trial = load('rog5_trial', REPO/'scripts/host/production-ram-trial.py')
        self.address = address

    def run(self, command, timeout=60, data=None, check=True):
        result = self.trial.ssh(self.address, command, timeout, data)
        if check:
            need(result.returncode == 0, f'remote command failed ({result.returncode}): {command[:80]}: '
                 + result.stderr.decode(errors='replace')[-300:])
        return result

    def read(self, path, limit=None):
        return self.run(f"cat -- '{path}'", timeout=120).stdout

    def script(self, text, mode, timeout=60):
        return self.run(f'sh -s -- {mode}', timeout=timeout, data=text, check=False)


def write_new(path, data):
    with open(path, 'xb') as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--bundle-dir', type=Path, required=True, help='packaged bundles/<name> directory')
    parser.add_argument('--descriptor', type=Path, required=True, help='trial descriptor built into the ramdisk')
    parser.add_argument('--trust-key', type=Path, required=True, help='raw Ed25519 trust key (32 bytes)')
    parser.add_argument('--evidence', type=Path, required=True, help='new directory for backups and logs')
    parser.add_argument('--address', default='169.254.77.2')
    parser.add_argument('--stage', action='store_true', help='perform the persistent install')
    args = parser.parse_args()

    need(not args.evidence.exists(), 'evidence directory exists: inspect it, never retry')
    trial_id, bundle = descriptor_fields(regular(args.descriptor))
    need(args.bundle_dir.name == bundle, 'bundle directory does not match the descriptor')
    need(bundle != FALLBACK, 'refusing to replace the fallback bundle')
    need(sorted(p.name for p in args.bundle_dir.iterdir()) == sorted(FILES), 'bundle inventory')
    payload = {name: regular(args.bundle_dir/name) for name in FILES}
    need(sha(regular(args.trust_key)) == TRUST_RAW_SHA256, 'trust key is not the slot-B loader key')
    carried = newc_member(payload['initramfs.cpio.gz'], 'rog5-production-trial/trial-descriptor')
    need(carried == regular(args.descriptor),
         'the bundle ramdisk does not carry this trial descriptor, so it could never commit')
    if args.stage:
        dirty = subprocess.run(['git', '-C', str(REPO), 'status', '--porcelain'], capture_output=True, text=True)
        need(dirty.returncode == 0 and not dirty.stdout, 'the repository must be clean to stage')

    phone = Phone(args.address)
    os.umask(0o077)
    args.evidence.mkdir(mode=0o700, parents=False)
    log = (args.evidence/'install.log').open('a')

    def note(text):
        line = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())+' '+text
        print(line, flush=True)
        log.write(line+'\n')
        log.flush()

    identity = phone.run('cat /proc/sys/kernel/random/boot_id; uname -r').stdout.decode().split()
    need(len(identity) == 2, 'running identity')
    boot_id = identity[0]
    note(f'running {identity[1]} boot {boot_id}')
    linux = ROOT_MOUNT+'/boot/rog5-linux'
    record_path = USERDATA_MOUNT+'/rog5/boot/wifi-trial-state'
    selector_old = phone.read(linux+'/selector')
    record_probe = phone.run(f"test -e '{record_path}' && echo present || echo absent").stdout.decode().strip()
    record_old = phone.read(record_path) if record_probe == 'present' else None
    write_new(args.evidence/'selector.before', selector_old)
    if record_old is not None:
        write_new(args.evidence/'wifi-trial-state.before', record_old)
    need(f'trial_id={trial_id}\n'.encode() not in selector_old + (record_old or b''),
         'this trial id is already in use: build a fresh descriptor')

    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        verifier = tmp/'rog5-bundle-verify'
        subprocess.run(['cc', '-O2', '-DROG5_BUNDLE_TESTING=1', '-o', str(verifier), str(VERIFIER_SOURCE),
                        '-lcrypto', '-lz'], check=True, capture_output=True)
        roots = tmp/'bundles'
        (roots/bundle).mkdir(parents=True)
        for name, data in payload.items():
            (roots/bundle/name).write_bytes(data)
        fallback = {}
        (roots/FALLBACK).mkdir()
        for name in FILES:
            fallback[name] = phone.read(f'{linux}/bundles/{FALLBACK}/{name}')
            (roots/FALLBACK/name).write_bytes(fallback[name])
        need(sha(fallback['manifest']) == SELECTOR.FALLBACK_MANIFEST_SHA256, 'V11 manifest changed')
        verify_bundle(verifier, args.trust_key, roots, FALLBACK, sha(fallback['manifest']))
        plan = verify_bundle(verifier, args.trust_key, roots, bundle, sha(payload['manifest']))
        (args.evidence/'verified-plan.txt').write_text(plan)
    note(f'verified {bundle} and {FALLBACK} with trust key {TRUST_RAW_SHA256[:8]}')

    selector, generated = SELECTOR.generate(regular(args.descriptor), payload['manifest'], fallback['manifest'])
    write_new(args.evidence/'selector', selector)
    values = dict(
        boot_id=boot_id, bundle=bundle, trial_id=trial_id,
        payload_image=sha(payload['Image']), payload_dtb=sha(payload['board.dtb']),
        payload_initramfs=sha(payload['initramfs.cpio.gz']), payload_manifest=sha(payload['manifest']),
        payload_signature=sha(payload['manifest.sig']),
        selector_old_sha256=sha(selector_old), selector_old_size=len(selector_old),
        selector_new_sha256=sha(selector),
        record_old_sha256=sha(record_old) if record_old is not None else 'absent',
        record_archive=archive_name(bundle, sha(record_old) if record_old is not None else 'none'),
        fallback_image=sha(fallback['Image']), fallback_dtb=sha(fallback['board.dtb']),
        fallback_initramfs=sha(fallback['initramfs.cpio.gz']), fallback_manifest=sha(fallback['manifest']),
        fallback_signature=sha(fallback['manifest.sig']),
        p24_uuid=P24_UUID, p23_uuid=P23_UUID, p24_size=P24_SIZE,
        root_mount=ROOT_MOUNT, userdata_mount=USERDATA_MOUNT,
        source_root='/run/rog5-default-kernel-'+trial_id[:16],
        sys_block='/sys/class/block', sys_power='/sys/class/power_supply')
    script = render(values)
    write_new(args.evidence/'install-on-target.sh', script)
    (args.evidence/'values.json').write_text(json.dumps(dict(values, generated=generated), indent=2)+'\n')

    result = phone.script(script, '--inspect')
    write_new(args.evidence/'inspect.log', result.stdout+result.stderr)
    need(result.returncode == 0 and result.stdout.startswith(b'PASS default kernel inspection'),
         'inspection failed: '+(result.stdout+result.stderr).decode(errors='replace')[-300:])
    note(result.stdout.decode().strip())

    source = values['source_root']
    phone.run(f"test \"$(findmnt -n -o FSTYPE /run)\" = tmpfs && mkdir -m 700 '{source}'")
    for name, data in list(payload.items())+[('selector', selector)]:
        pushed = phone.run(f"cat > '{source}/{name}' && sha256sum '{source}/{name}'", timeout=180, data=data)
        need(pushed.stdout.decode().split()[0] == sha(data), 'transfer changed '+name)
    result = phone.script(script, '--preflight')
    write_new(args.evidence/'preflight.log', result.stdout+result.stderr)
    need(result.returncode == 0 and result.stdout == b'PASS default kernel payload preflight\n',
         'payload preflight failed: '+(result.stdout+result.stderr).decode(errors='replace')[-300:])
    note('payload preflight PASS')
    if not args.stage:
        phone.run(f"rm -r -- '{source}'")
        note('read-only run complete; nothing was installed')
        return 0

    head = subprocess.run(['git', '-C', str(REPO), 'rev-parse', 'HEAD'], capture_output=True, text=True).stdout.strip()
    write_new(args.evidence/'INSTALL-ENTERED.json', json.dumps(dict(
        bundle=bundle, trial_id=trial_id, boot_id=boot_id, source_revision=head,
        script_sha256=sha(script), selector_sha256=sha(selector),
        previous_selector_sha256=sha(selector_old), previous_record_sha256=values['record_old_sha256'],
        time=time.time()), indent=2).encode()+b'\n')
    report = dict(status='FAIL', bundle=bundle)
    started = time.monotonic()
    try:
        result = phone.script(script, '--stage', timeout=240)
        write_new(args.evidence/'stage.log', result.stdout+result.stderr)
        report['returncode'] = result.returncode
        need(result.returncode == 0 and result.stdout.endswith(STAGED.format(bundle=bundle).encode()),
             'stage failed; inspect the phone, never retry: '+(result.stdout+result.stderr).decode(errors='replace')[-300:])
        after = phone.read(linux+'/selector')
        need(after == selector, 'active selector differs after staging')
        report['status'] = 'PASS'
    except Exception as error:
        report['reason'] = str(error)
    finally:
        report['seconds'] = round(time.monotonic()-started, 1)
        write_new(args.evidence/'INSTALL-RESULT.json', json.dumps(report, indent=2).encode()+b'\n')
    phone.run(f"rm -r -- '{source}'", check=False)
    note(json.dumps(report))
    need(report['status'] == 'PASS', 'install not proven')
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        print('FAIL '+str(error), file=sys.stderr)
        sys.exit(1)
