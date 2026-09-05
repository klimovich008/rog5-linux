#!/usr/bin/env python3
"""Exercise sealed headless runtime against an already mounted RO loop image.

No phone, admission, mount setup, repair, signing or service activation. The
caller owns the private mount namespace and cleanup. PASS is archive/root
composition evidence, not final boot-wrapper or physical qualification.
"""
import argparse
import gzip
import io
import importlib.util
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import tempfile
import time

REPO = Path(__file__).resolve().parents[2]


def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, REPO/filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


SEALED = load('rescue_sealed', 'scripts/host/run-sealed-busybox.py')
ACCEPTANCE = load('rescue_acceptance', 'scripts/host/release-acceptance.py')
FUNCTIONS = ('verify_exact_regular', 'prepare_volatile_root_account',
             'prepare_volatile_ssh_policy', 'verify_systemd_update_marker',
             'prepare_volatile_systemd_state', 'prepare_runtime')
MARKERS = ('PREPARE', 'SYSTEMD_EXEC', 'VOLATILE_HOST_KEY', 'SSH_POLICY', 'UNIT_VERIFY')


def archive_parameters(members):
    source = members['init'][1].decode()
    keys = ('KERNEL_RELEASE', 'UFS_STORAGE_MODE', 'PROBE_BOOT_ID', 'NATIVE_ROOT_MODE',
            'SSH_DIAGNOSTIC_MODE', 'PERSISTENT_OVERLAY_MODE')
    values = {}
    for key in keys:
        matches = re.findall('(?m)^expected_'+key.lower()+r'=([^\n]+)$', source)
        if len(matches) != 1:
            raise ValueError('missing/duplicate archive parameter: '+key)
        values[key] = matches[0]
    if not re.fullmatch(r'7\.1\.4-g[0-9a-f]{12}', values['KERNEL_RELEASE']):
        raise ValueError('unsupported rescue kernel release')
    expected = dict(UFS_STORAGE_MODE='read-only', PROBE_BOOT_ID='staged-seal',
                    NATIVE_ROOT_MODE='1', SSH_DIAGNOSTIC_MODE='0', PERSISTENT_OVERLAY_MODE='0')
    if any(values[k] != v for k, v in expected.items()):
        raise ValueError('requires headless native-root volatile-overlay composition')
    for name, template, parameters in (
        ('init', 'initramfs/persistent-root-init', values),
        ('usr/local/sbin/rog5-p2-attest', 'initramfs/persistent-root-attest',
         {k: values[k] for k in ('UFS_STORAGE_MODE', 'PROBE_BOOT_ID', 'NATIVE_ROOT_MODE', 'PERSISTENT_OVERLAY_MODE')}),
    ):
        if members[name][1] != SEALED.ARCHIVE.render_boot_template(REPO/template, parameters):
            raise ValueError('unpaired archive/source member: '+name)
    power = members['sbin/rog5-load-persistent-power-usb'][1]
    if power != (REPO/'scripts/device/load-persistent-root-power-usb.sh').read_bytes():
        raise ValueError('stale power safety helper')
    observer = members.get('usr/local/sbin/rog5-startup-observer')
    if observer is not None and observer[1] != (REPO/'initramfs/persistent-startup-observer').read_bytes():
        raise ValueError('stale startup observer')
    for name, (fields, data) in members.items():
        if name.startswith('rog5-native-wifi/'):
            raise ValueError('headless rescue must not activate optional radio/display payload')
        if stat.S_ISREG(fields[1]) and (b'@EXPECTED_' in data or b'@OUTER_SECONDS@' in data):
            raise ValueError('unresolved archive parameter: '+name)
    return values


def driver(source):
    blocks = []
    for name in FUNCTIONS:
        marker = name+'() {\n'
        if source.count(marker) != 1:
            raise ValueError('missing/duplicate sealed function: '+name)
        start = source.index(marker)
        blocks.append(source[start:source.index('\n}\n', start)+3])
    return '''#!/bin/sh
set -eu
export PATH=/bin:/sbin:/usr/bin:/usr/sbin
expected_persistent_overlay_mode=0
expected_ssh_diagnostic_mode=0
native_wifi_boot=0
# Unit-generation fixture, not deployed timing. No service is activated here;
# exact manifest/wrapper timeout binding remains a separate release check.
recovery_timeout=1
reboot_helper=/usr/libexec/rog5-reboot-bootloader
# Explicit hardware lookup fixture; no actual block node is passed to helpers.
find_exact_userdata() { printf '/dev/rog5-offline-fixture\n'; }
'''+''.join(blocks)+'''
prepare_runtime
echo COMPOSITION_PREPARE_PASS
chroot /newroot /usr/bin/systemd-analyze --version
echo COMPOSITION_SYSTEMD_EXEC_PASS
mkdir -p /newroot/run/sshd
chroot /newroot /usr/bin/ssh-keygen -q -t ed25519 -N '' -f /etc/ssh/ssh_host_ed25519_key
echo COMPOSITION_VOLATILE_HOST_KEY_PASS
chroot /newroot /usr/bin/sshd -T >/run/ssh-effective
for option in passwordauthentication kbdinteractiveauthentication usepam hostbasedauthentication gssapiauthentication; do
    [ "$(awk -v k="$option" '$1 == k { n++; v=$2 } END { if(n!=1) exit 1; print v }' /run/ssh-effective)" = no ]
done
[ "$(awk '$1 == "pubkeyauthentication" { print $2 }' /run/ssh-effective)" = yes ]
case $(awk '$1 == "permitrootlogin" { print $2 }' /run/ssh-effective) in
    prohibit-password|without-password) ;; *) exit 1 ;; esac
echo COMPOSITION_SSH_POLICY_PASS
set -- /run/systemd/system/rog5-p2-ready.service /run/systemd/system/rog5-early-sshd.service /run/systemd/system/rog5-persistent-state.service /run/systemd/system/rog5-persistent-ssh-identity.service
if [ -e /run/systemd/system/rog5-startup-observer.service ]; then
    set -- "$@" /run/systemd/system/rog5-startup-observer.service
fi
chroot /newroot /usr/bin/systemd-analyze verify --man=no --generators=no "$@"
echo COMPOSITION_UNIT_VERIFY_PASS
'''


def verify_mount(root, image):
    result = subprocess.check_output(['findmnt', '-J', '-o', 'TARGET,SOURCE,FSTYPE,OPTIONS',
                                      '--target', str(root)], text=True)
    entries = json.loads(result)['filesystems']
    if len(entries) != 1:
        raise ValueError('ambiguous root mount')
    entry = entries[0]
    options = set(entry['options'].split(','))
    if (entry['target'] != str(root) or entry['fstype'] != 'ext4'
            or not re.fullmatch(r'/dev/loop[0-9]+', entry['source'])
            or not {'ro', 'nodev', 'nosuid'} <= options or 'rw' in options
            or not options.intersection({'noload', 'norecovery'})):
        raise ValueError('root must be an exact dedicated read-only no-recovery ext4 loop mount')
    backing = subprocess.check_output(['losetup', '-n', '-O', 'BACK-FILE', entry['source']], text=True).strip()
    readonly = subprocess.check_output(['blockdev', '--getro', entry['source']], text=True).strip()
    if Path(backing).resolve() != image.resolve() or readonly != '1':
        raise ValueError('root loop does not match exact read-only receipt image')
    return entry


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inputs', type=Path, required=True)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if os.geteuid() != 0:
        print('BLOCKED: requires the reviewed private read-only loop-mount environment')
        return 77
    source = ACCEPTANCE.source_identity()
    inputs = ACCEPTANCE.verify_release(args.inputs, required_roles={'kernel', 'dtb', 'initramfs', 'rootfs'})
    if inputs['source_revision'] != source['revision']:
        raise ValueError('input receipt/source revision mismatch')
    root = args.root.resolve(strict=True)
    mount = verify_mount(root, Path(inputs['artifact_paths']['rootfs']))
    with Path(inputs['artifact_paths']['initramfs']).open('rb') as stream:
        blob = stream.read(256 * 1024 * 1024 + 1)
    if len(blob) > 256 * 1024 * 1024:
        raise ValueError('compressed archive exceeds 256 MiB')
    with gzip.GzipFile(fileobj=io.BytesIO(blob)) as stream:
        payload = stream.read(512 * 1024 * 1024 + 1)
    if len(payload) > 512 * 1024 * 1024:
        raise ValueError('expanded archive exceeds 512 MiB')
    members = SEALED.ARCHIVE.entries(payload)
    values = archive_parameters(members)
    if ('Linux version '+values['KERNEL_RELEASE']+' ').encode() not in Path(inputs['artifact_paths']['kernel']).read_bytes():
        raise ValueError('kernel banner/archive release mismatch')
    args.output.mkdir(mode=0o700)  # New, private, never replace prior evidence.
    started = time.monotonic()
    with tempfile.TemporaryDirectory(prefix='fixture-', dir=args.output) as temp, \
            tempfile.TemporaryDirectory(prefix='rog5-composition-', dir='/dev/shm') as volatile:
        target = Path(temp)/'archive'; target.mkdir()
        SEALED.extract(members, target)
        for name in ('mnt/root-ro', 'mnt/state/upper', 'newroot', 'run', 'tmp', 'dev', 'proc'):
            (target/name).mkdir(parents=True, exist_ok=True)
        (target/'rog5-qemu').touch()
        (target/'composition-test.sh').write_text(driver(members['init'][1].decode()))
        upper, work, runtime = (Path(volatile)/name for name in ('upper', 'work', 'run'))
        for path in (upper, work, runtime):
            path.mkdir(mode=0o755)
        command = ['bwrap', '--unshare-ipc', '--unshare-pid', '--unshare-net', '--unshare-uts',
                   '--unshare-cgroup', '--die-with-parent', '--new-session', '--cap-drop', 'ALL',
                   '--cap-add', 'CAP_SYS_CHROOT', '--ro-bind', str(target), '/',
                   '--ro-bind', str(root), '/mnt/root-ro', '--overlay-src', str(root),
                   '--overlay', str(upper), str(work), '/newroot', '--bind', str(upper), '/mnt/state/upper',
                   '--bind', str(runtime), '/run', '--bind', str(runtime), '/newroot/run',
                   '--tmpfs', '/tmp', '--dev', '/dev', '--proc', '/proc',
                   '--dev', '/newroot/dev', '--proc', '/newroot/proc',
                   '--ro-bind', '/usr/bin/qemu-aarch64-static', '/rog5-qemu', '--clearenv',
                   '--setenv', 'PATH', '/bin:/sbin:/usr/bin:/usr/sbin',
                   '--setenv', 'QEMU_UNAME', values['KERNEL_RELEASE'],
                   '/rog5-qemu', '/bin/busybox', 'sh', '/composition-test.sh']
        try:
            result = subprocess.run(command, capture_output=True, timeout=60)
            log, code = result.stdout+result.stderr, result.returncode
        except subprocess.TimeoutExpired as exc:
            log, code = (exc.stdout or b'')+(exc.stderr or b''), 124
        (args.output/'runtime.log').write_bytes(log)
        passed = code == 0 and all(('COMPOSITION_'+m+'_PASS').encode() in log for m in MARKERS)
        passed = passed and source == ACCEPTANCE.source_identity()
        passed = passed and inputs == ACCEPTANCE.verify_release(
            args.inputs, required_roles={'kernel', 'dtb', 'initramfs', 'rootfs'})
        passed = passed and mount == verify_mount(root, Path(inputs['artifact_paths']['rootfs']))
        record = dict(status='PASS' if passed else 'FAIL', source=source, inputs=inputs,
                      scope='archive/root runtime preparation and executable/unit compatibility only',
                      limitations=['hardware lookup fixture', 'no physical boot or storage recovery proof',
                                   'no final wrapper/admission or module-load proof',
                                   'unit lifetime is a fixture, not deployed timeout verification'],
                      mount=mount, exit_code=code, duration_seconds=round(time.monotonic()-started, 3),
                      checker_sha256=ACCEPTANCE.sha_file(Path(__file__)),
                      qemu_sha256=ACCEPTANCE.sha_file(Path('/usr/bin/qemu-aarch64-static')))
        (args.output/'result.json').write_text(json.dumps(record, indent=2)+'\n')
        print(json.dumps(record, indent=2))
        return 0 if passed else 1


if __name__ == '__main__':
    raise SystemExit(main())
