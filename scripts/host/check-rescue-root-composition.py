#!/usr/bin/env python3
"""Exercise sealed headless runtime against an already mounted RO loop image.

No phone, admission, mount setup, repair, signing or service activation. The
caller owns the private mount namespace and cleanup. PASS is archive/root
composition evidence, not final boot-wrapper or physical qualification.
"""
import argparse
import gzip
import hashlib
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
             'prepare_volatile_systemd_state', 'prepare_package_keyring', 'prepare_runtime')
MARKERS = ('PREPARE', 'EXITRD', 'SYSTEMD_EXEC', 'VOLATILE_HOST_KEY', 'SSH_POLICY', 'UNIT_VERIFY')


def archive_parameters(members, *, profile='rescue'):
    if profile not in ('rescue', 'server-runtime'):
        raise ValueError('unknown composition profile')
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
                    NATIVE_ROOT_MODE='1', SSH_DIAGNOSTIC_MODE='0',
                    PERSISTENT_OVERLAY_MODE='1' if profile == 'server-runtime' else '0')
    if any(values[k] != v for k, v in expected.items()):
        raise ValueError('requires exact native-root composition for '+profile)
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
    shutdown = members.get('shutdown')
    if (shutdown is None or shutdown[0][1:5] != [stat.S_IFREG | 0o755, 0, 0, 1]
            or shutdown[1] != (REPO/'initramfs/persistent-root-shutdown-standalone').read_bytes()):
        raise ValueError('unpaired shutdown helper')
    # Pair the strengthened watchdog with its actual startup/identity producer;
    # a fresh init plus a legacy producer would pass P2 but inevitably roll back.
    for name, source in (
        ('usr/local/sbin/rog5-persistent-state', 'initramfs/persistent-service-state'),
        ('usr/local/sbin/rog5-persistent-ssh-identity', 'initramfs/persistent-ssh-identity'),
        ('usr/local/sbin/rog5-persistent-keyring', 'initramfs/persistent-package-keyring'),
        ('usr/local/share/rog5/rog5-package-keyring.service', 'configs/systemd/rog5-package-keyring.service'),
    ):
        member = members.get(name)
        if member is None or member[1] != (REPO/source).read_bytes():
            raise ValueError('unpaired startup helper: '+name)
    observer = members.get('usr/local/sbin/rog5-startup-observer')
    if observer is not None and observer[1] != (REPO/'initramfs/persistent-startup-observer').read_bytes():
        raise ValueError('stale startup observer')
    for name, (fields, data) in members.items():
        if profile == 'rescue' and name.startswith('rog5-native-wifi/'):
            raise ValueError('headless rescue must not activate optional radio/display payload')
        if stat.S_ISREG(fields[1]) and (b'@EXPECTED_' in data or b'@OUTER_SECONDS@' in data):
            raise ValueError('unresolved archive parameter: '+name)
    if profile == 'server-runtime':
        marker = members.get('rog5-native-wifi/automatic')
        if (marker is None or marker[0][1:5] != [stat.S_IFREG | 0o444, 0, 0, 1]
                or marker[1] != b'rog5-native-wifi-boot-v1\n'):
            raise ValueError('invalid server radio marker')
        SEALED.ARCHIVE.verify_radio_composition(members)
        outer = re.findall(rb'^outer_seconds=([0-9]+)$',
                           (REPO/'initramfs/native-wifi/timing').read_bytes(), re.M)
        if len(outer) != 1:
            raise ValueError('invalid server timing')
        for directory in ('native-wifi', 'native-wifi-persistent'):
            base = REPO/'initramfs'/directory
            for path in base.rglob('*'):
                if not path.is_file():
                    continue
                name = 'rog5-native-wifi/'+str(path.relative_to(base))
                mode = 0o755 if path.stat().st_mode & 0o111 else 0o644
                member = members.get(name)
                if (path.is_symlink() or member is None
                        or member[0][1:5] != [stat.S_IFREG | mode, 0, 0, 1]
                        or member[1] != path.read_bytes().replace(b'@OUTER_SECONDS@', outer[0])):
                    raise ValueError('unpaired server userspace: '+name)
    return values


def driver(source, *, profile='rescue'):
    if profile not in ('rescue', 'server-runtime'):
        raise ValueError('unknown composition profile')
    blocks = []
    for name in FUNCTIONS:
        marker = name+'() {\n'
        if source.count(marker) != 1:
            raise ValueError('missing/duplicate sealed function: '+name)
        start = source.index(marker)
        blocks.append(source[start:source.index('\n}\n', start)+3])
    script = '''#!/bin/sh
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
# Reproduce the previous observer mistake from the actual Arch filesystem:
# an absolute BusyBox pathname does not relocate its ELF interpreter. Never
# execute shutdown; these commands only parse it with the exact sealed shell.
if [ ! -e /newroot/lib/ld-musl-aarch64.so.1 ]; then
    if chroot /newroot /run/initramfs/bin/busybox sh -n /run/initramfs/shutdown; then
        echo 'FAIL exitrd unexpectedly executable without its interpreter' >&2
        exit 1
    fi
    echo COMPOSITION_EXITRD_OUTSIDE_ROOT_REFUSED
fi
chroot /newroot /usr/bin/chroot /run/initramfs /bin/sh -n /shutdown
echo COMPOSITION_EXITRD_PASS
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
    if profile == 'server-runtime':
        script = script.replace('expected_persistent_overlay_mode=0', 'expected_persistent_overlay_mode=1')
        script = script.replace('native_wifi_boot=0', 'native_wifi_boot=1')
        script = script.replace('\nprepare_runtime\n', '''
# Installation fixture: archive root is read-only here. The real init moves
# this directory; copy exact members into owned tmpfs without activating radio.
cp -a /rog5-native-wifi /run/
# Prior storage-stage input fixture, not storage enumeration or write proof.
# No block node exists at this name inside the isolated environment.
overlay_userdata=/dev/rog5-offline-fixture
printf '%s\\n' "$overlay_userdata" >/run/rog5-persistent-state-userdata-device
chmod 0444 /run/rog5-persistent-state-userdata-device
echo COMPOSITION_PRIOR_STAGE_FIXTURE_READY
prepare_runtime
''')
        script = script.replace('chroot /newroot /usr/bin/systemd-analyze verify', '''
set -- "$@" /run/systemd/system/rog5-wifi-radio.service /run/systemd/system/rog5-wifi-wpa.service /run/systemd/system/rog5-wifi-dhcp.service /run/systemd/system/rog5-wifi-healthy.service /run/systemd/system/rog5-wifi-boot-rollback.timer /run/systemd/system/rog5-wifi-failure.service
chroot /newroot /usr/bin/systemd-analyze verify''')
    return script


def core_module_members(members, profile):
    """Keep the power/UFS closure strict; radio activation is a separate test.

    The server-runtime profile proves service preparation only. It must never
    turn untested nested/probe radio modules into a full module-closure PASS.
    """
    if profile == 'rescue':
        return members, []
    if profile != 'server-runtime':
        raise ValueError('unknown composition profile')
    auxiliary = {'rog5-native-wifi/'+name for name in (
        'rog5-pmic-pon-readonly.ko', 'rog5-s12-ufs-vote.ko', 'rog5-wifi-activate.ko',
        'module-root-complete.tar.gz')}
    if not auxiliary <= members.keys():
        raise ValueError('missing retained radio module payload')
    pending = [dict(path=name, sha256=hashlib.sha256(members[name][1]).hexdigest(),
                    status='NOT RUN', scope='radio module load/closure') for name in sorted(auxiliary)]
    return {name: member for name, member in members.items() if name not in auxiliary}, pending


def module_closure(members, release):
    """Check the sealed power-then-UFS insmod order, not a hardware load proof.

    archive_parameters separately binds the scripts to the reviewed call sites.
    Module dependency metadata lists loadable dependencies, not built-in symbols;
    vermagic agreement cannot by itself prove BTF/symbol or hardware compatibility.
    """
    power = members['sbin/rog5-load-persistent-power-usb'][1].decode()
    init = members['init'][1].decode()
    power_calls = list(re.finditer(r'(?m)^\s*if ! power_usb_failure=\$\(/sbin/rog5-load-persistent-power-usb\)', init))
    ufs_calls = list(re.finditer(r'(?m)^\s*load_deferred_ufs_modules\s*$', init))
    if len(power_calls) != 1 or len(ufs_calls) != 1 or power_calls[0].start() >= ufs_calls[0].start():
        raise ValueError('unsupported power/UFS call-site order')
    order = ['rog5-power-usb-modules/'+name for name in re.findall(
        r'(?m)^load_module ([A-Za-z0-9_-]+\.ko) [A-Za-z0-9_-]+ [A-Za-z0-9_-]+$', power)]
    order += re.findall(r'(?m)^\s*insmod /(rog5-ufs-modules/[A-Za-z0-9_-]+\.ko) \|\| return 1$', init)
    inventory = {name for name in members if name.endswith('.ko')}
    if not order or len(order) != len(set(order)) or set(order) != inventory:
        raise ValueError('sealed module inventory/load-order mismatch')
    rows, loaded, vermagic = [], set(), None
    deadline = time.monotonic() + 10
    with tempfile.TemporaryDirectory(prefix='rog5-module-metadata-') as temp:
        for index, name in enumerate(order):
            fields, data = members[name]
            if (not stat.S_ISREG(fields[1]) or fields[4] != 1 or fields[2:4] != [0,0]
                    or fields[1] & 0o6022 or len(data) < 64
                    or data[:6] != b'\x7fELF\x02\x01' or data[16:20] != b'\x01\x00\xb7\x00'):
                raise ValueError('unsafe or non-AArch64 module: '+name)
            # Only verified regular member bytes, never archive paths/links.
            directory=Path(temp)/str(index); directory.mkdir()
            path=directory/Path(name).name; path.write_bytes(data); path.chmod(0o400)
            metadata = {}
            for field in ('name','depends','vermagic'):
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise ValueError('module metadata deadline exceeded')
                metadata[field] = subprocess.check_output(['modinfo','-F',field,str(path)],
                        text=True,timeout=min(5,remaining)).strip()
            module=metadata['name']
            if not re.fullmatch(r'[A-Za-z0-9_]+',module) or module in loaded:
                raise ValueError('invalid/duplicate module identity: '+name)
            if module != path.stem.replace('-','_'):
                raise ValueError('module filename/name mismatch: '+name)
            words=metadata['vermagic'].split()
            if not words or words[0]!=release:
                raise ValueError('module/kernel release mismatch: '+name)
            if vermagic is not None and metadata['vermagic']!=vermagic:
                raise ValueError('inconsistent module vermagic: '+name)
            vermagic=metadata['vermagic']
            dependencies=metadata['depends'].split(',') if metadata['depends'] else []
            if any(not re.fullmatch(r'[A-Za-z0-9_-]+',dep) or dep.replace('-','_') not in loaded
                   for dep in dependencies):
                raise ValueError('module dependency absent or loaded too late: '+name)
            loaded.add(module)
            rows.append(dict(path=name,sha256=hashlib.sha256(data).hexdigest(),**metadata))
    return rows


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
    parser.add_argument('--profile', choices=('rescue', 'server-runtime'), default='rescue')
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
    values = archive_parameters(members, profile=args.profile)
    core_members, radio_pending = core_module_members(members, args.profile)
    modules = module_closure(core_members, values['KERNEL_RELEASE'])
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
        (target/'composition-test.sh').write_text(driver(members['init'][1].decode(), profile=args.profile))
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
                   # Private fixture trace pinpoints the exact failed predicate;
                   # never publish the raw log (it can contain rootfs metadata).
                   '/rog5-qemu', '/bin/busybox', 'sh', '-x', '/composition-test.sh']
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
        record = dict(status='PASS' if passed else 'FAIL', source=source, inputs=inputs, profile=args.profile,
                      scope='archive/root runtime preparation and executable/unit compatibility only',
                      limitations=['hardware lookup fixture', 'no physical boot or storage recovery proof',
                                   'no final wrapper/admission or module-load proof',
                                   'unit lifetime is a fixture, not deployed timeout verification'],
                      mount=mount, exit_code=code, duration_seconds=round(time.monotonic()-started, 3),
                      module_metadata_in_load_order=modules,
                      radio_module_tests=radio_pending,
                      checker_sha256=ACCEPTANCE.sha_file(Path(__file__)),
                      qemu_sha256=ACCEPTANCE.sha_file(Path('/usr/bin/qemu-aarch64-static')))
        (args.output/'result.json').write_text(json.dumps(record, indent=2)+'\n')
        print(json.dumps(record, indent=2))
        return 0 if passed else 1


if __name__ == '__main__':
    raise SystemExit(main())
