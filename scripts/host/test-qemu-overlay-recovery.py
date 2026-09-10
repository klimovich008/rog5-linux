#!/usr/bin/env python3
"""Disposable ext4/OverlayFS interruption with the supplied kernel and sealed shell.

Runs exact archive predicates and systemd-state preparation, not full phone init,
UFS hardware, actual systemd startup or persistent-update authorization. Only
new test-owned disks are writable in a networkless QEMU container.
"""
import argparse
import gzip
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import time

R = Path(__file__).resolve().parents[2]


def sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024*1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def require(ok, message):
    if not ok:
        raise RuntimeError(message)


class MissingPrerequisite(RuntimeError):
    pass


def function(source, name):
    marker = '\n'+name+'() {\n'
    require(source.count(marker) == 1, 'ambiguous archive function: '+name)
    begin = source.index(marker)+1
    return source[begin:source.index('\n}\n', begin)+3]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--kernel', type=Path, required=True)
    parser.add_argument('--target-archive', type=Path, required=True)
    parser.add_argument('--root-image', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    require(not output.exists() and not output.is_relative_to(R), 'output must be new and outside repository')
    for path in (args.kernel, args.target_archive, args.root_image):
        require(path.is_file() and not path.is_symlink(), 'unsafe input file')
    os.umask(0o077)
    output.mkdir(mode=0o700)
    started = time.monotonic()
    report = dict(status='FAIL', scope=__doc__, cases=[], commands=[])

    def run(argv, *, check=True, timeout=15):
        p = subprocess.run(list(map(str, argv)), capture_output=True, timeout=timeout)
        report['commands'].append(dict(argv=list(map(str, argv)), exit_code=p.returncode,
                                       stderr=p.stderr.decode(errors='replace')[-2000:]))
        require(not check or p.returncode == 0, 'command failed: '+str(argv[0]))
        return p

    try:
        for executable in ('git', 'podman', 'debugfs', 'mkfs.ext4', 'dumpe2fs', 'e2fsck'):
            if shutil.which(executable) is None:
                raise MissingPrerequisite('missing executable: '+executable)
        report['source_revision'] = run(['git', '-C', R, 'rev-parse', 'HEAD']).stdout.decode().strip()
        source_before = run(['git', '-C', R, 'diff', '--binary', 'HEAD']).stdout
        report['source_diff_sha256'] = hashlib.sha256(source_before).hexdigest()
        report['runner_sha256'] = sha(Path(__file__))
        inputs = dict(kernel=args.kernel, initramfs=args.target_archive, root=args.root_image)
        report['input_sha256'] = {name: sha(path) for name, path in inputs.items()}
        spec = importlib.util.spec_from_file_location('overlay_archive', R/'scripts/device/build-native-wifi-boot-initramfs.py')
        archive = importlib.util.module_from_spec(spec); spec.loader.exec_module(archive)
        target = archive.entries(gzip.decompress(args.target_archive.read_bytes()))
        source = target['init'][1].decode()
        funcs = '\n'.join(function(source, name) for name in (
            'verify_exact_regular', 'verify_overlay_workdir_pre_mount',
            'verify_systemd_update_marker', 'prepare_volatile_systemd_state'))
        # Read one public file from the exact retained image; never mount it RW.
        cache = run(['debugfs', '-R', 'cat /etc/ld.so.cache', args.root_image]).stdout
        require(cache.startswith(b'glibc-ld.so.cache') and len(cache) < 1024*1024,
                'retained root cache missing or unsupported')
        report['retained_cache_sha256'] = hashlib.sha256(cache).hexdigest()
        container = run(['podman', 'image', 'inspect', '--format', '{{.Id}}',
                         'localhost/rog5-qemu-gate:ubuntu-24.04'], check=False).stdout.decode().strip()
        if not re.fullmatch(r'(sha256:)?[0-9a-f]{64}', container):
            raise MissingPrerequisite('missing installed QEMU container')
        report['container'] = container
        disk = output/'interrupted.ext4'
        with disk.open('xb') as stream:
            stream.truncate(64*1024*1024)
        run(['mkfs.ext4', '-q', '-F', '-O', '^orphan_file', disk])
        protected = output/'protected.img'
        protected.write_bytes(b'ROG5 disposable read-only block sentinel\n'*1024)
        protected_hash = sha(protected)
        driver = r'''#!/bin/busybox sh
set -eu
/bin/busybox --install -s /bin
export PATH=/bin
trap 'echo OVERLAY_GUEST_FAILED; poweroff -f' EXIT
mount -t proc proc /proc
mount -t sysfs sysfs /sys
mount -t devtmpfs devtmpfs /dev
mkdir -p /lower /state /merged
for runtime_dir in /runtime /runtime2 /runtime3 /runtime4; do
    mkdir -p "$runtime_dir/systemd/system/sysinit.target.wants"
done
mount -t tmpfs -o size=2m tmpfs /lower
mkdir /lower/etc /lower/var /lower/usr
cp /cache /lower/etc/ld.so.cache
chmod 0644 /lower/etc/ld.so.cache
echo immutable >/lower/sentinel
echo remove-this >/lower/remove-me
lower_hash=$(sha256sum /lower/sentinel)
mount -o remount,ro /lower
i=0
while [ ! -b /dev/vda ] || [ ! -b /dev/vdb ]; do
    i=$((i+1)); [ "$i" -le 10 ]; sleep 1
done
[ "$(blockdev --getro /dev/vdb)" = 1 ]
sha256sum /dev/vdb
if [ "@PHASE@" = corrupt ]; then
    if mount -t ext4 -o nodev,nosuid /dev/vda /state; then
        echo CORRUPT_MOUNT_ACCEPTED; exit 1
    fi
    echo CORRUPT_MOUNT_REJECTED
    trap - EXIT; poweroff -f
fi
mount -t ext4 -o nodev,nosuid /dev/vda /state
if [ "@PHASE@" = prepare ]; then
    mkdir -m 0755 /state/upper
    mkdir -m 0700 /state/work
else
    find /state/work -mindepth 1 -maxdepth 2 -exec stat -c 'RETAINED %n %F %a %h %t:%T' '{}' ';'
    if verify_overlay_workdir_pre_mount /state; then
        echo WORK_GUARD_PASS
    else
        echo WORK_GUARD_FAIL
    fi
    # Each mutation is isolated in this disposable guest. The real cached
    # whiteout remains in place; guard failures must not remove any entry.
    for mutation in regular symlink dangling directory hidden name dev mode owner; do
        hostile=/state/work/work/#abcd
        case $mutation in
            regular) echo unrelated >"$hostile" ;;
            symlink) ln -s /state/upper/remove-me "$hostile" ;;
            dangling) ln -s /absent "$hostile" ;;
            directory) mkdir "$hostile" ;;
            hidden) hostile=/state/work/work/.unrelated; : >"$hostile" ;;
            name) hostile=/state/work/work/#00; mknod -m 000 "$hostile" c 0 0 ;;
            dev) mknod -m 000 "$hostile" c 1 3 ;;
            mode) mknod -m 666 "$hostile" c 0 0 ;;
            owner) mknod -m 000 "$hostile" c 0 0; chown 1000:1000 "$hostile" ;;
        esac
        if verify_overlay_workdir_pre_mount /state; then
            echo "HOSTILE_ACCEPTED $mutation"; exit 1
        fi
        [ -e "$hostile" ] || [ -L "$hostile" ]
        if [ "$mutation" = directory ]; then rmdir "$hostile"; else rm "$hostile"; fi
    done
    echo HOSTILE_WORK_ENTRIES_REJECTED
fi
mount -t overlay overlay -o lowerdir=/lower,upperdir=/state/upper,workdir=/state/work /merged
if [ "@PHASE@" = prepare ]; then
    rm /merged/remove-me
    printf '%s\n' \
      '# This file was created by systemd-update-done. The timestamp below is the' \
      '# modification time of /usr/ for which the most recent updates of /etc/ have' \
      '# been applied. See man:systemd-update-done.service(8) for details.' \
      'TIMESTAMP_NSEC=1234' >/merged/etc/.updated
    chmod 0644 /merged/etc/.updated
    find /state/work/work -mindepth 1 -maxdepth 1 -exec stat -c 'INTERRUPTED %n %F %a %h %t:%T' '{}' ';'
    sync -f /merged
    echo INTERRUPTED_UPDATE_DURABLE
    echo b >/proc/sysrq-trigger
    exit 1
fi
[ ! -e /merged/remove-me ]
[ -z "$(find /state/work/work -mindepth 1 -maxdepth 1 -print -quit)" ]
echo KERNEL_WORK_CLEANUP_PASS
[ "$(sha256sum /lower/sentinel)" = "$lower_hash" ]
cmp /lower/sentinel /merged/sentinel
expected_persistent_overlay_mode=1
expected_ssh_diagnostic_mode=0
cp /merged/etc/.updated /saved-marker
prepare_volatile_systemd_state /merged /lower /state/upper /runtime
cmp /saved-marker /merged/etc/.updated
[ ! -s /merged/var/.updated ]
echo INTERRUPTED_ETC_ONLY_PASS
sed 's@updates of /etc/@updates of /var/@;s/1234/5678/' /saved-marker >/merged/var/.updated
chmod 0644 /merged/var/.updated
prepare_volatile_systemd_state /merged /lower /state/upper /runtime2
[ "$(verify_systemd_update_marker /merged /state/upper etc)" = 1234 ]
[ "$(verify_systemd_update_marker /merged /state/upper var)" = 5678 ]
echo INDEPENDENT_UPDATE_MARKERS_PASS
echo malformed >/merged/etc/.updated
if prepare_volatile_systemd_state /merged /lower /state/upper /runtime3; then
    echo MALFORMED_MARKER_ACCEPTED; exit 1
fi
echo MALFORMED_MARKER_REJECTED
cp /saved-marker /merged/etc/.updated
rm /merged/etc/.updated
prepare_volatile_systemd_state /merged /lower /state/upper /runtime4
[ ! -s /merged/etc/.updated ]
[ "$(verify_systemd_update_marker /merged /state/upper var)" = 5678 ]
echo INTERRUPTED_VAR_ONLY_PASS
cp /saved-marker /merged/etc/.updated
[ ! -e /lower/etc/.updated ] && [ ! -e /lower/var/.updated ]
[ "$(sha256sum /lower/sentinel)" = "$lower_hash" ]
sync -f /merged
umount /merged
verify_overlay_workdir_pre_mount /state
echo CLEAN_REMOUNT_GUARD_PASS
umount /state
echo OVERLAY_RECOVERY_COMPLETE
trap - EXIT; poweroff -f
'''
        for phase in ('prepare', 'recover', 'corrupt'):
            if phase == 'recover':
                header = run(['dumpe2fs', '-h', disk]).stdout.decode()
                (output/'interrupted-header.txt').write_text(header)
                require('needs_recovery' in header, 'VM reset did not retain journal-pending filesystem')
                shutil.copyfile(disk, output/'journal-pending.ext4')
            if phase == 'corrupt':
                disk = output/'corrupt.ext4'
                shutil.copyfile(output/'journal-pending.ext4', disk)
                with disk.open('r+b') as stream:
                    stream.seek(1024+56); stream.write(b'\0\0')
            members = {}
            for name in ('bin/busybox', 'lib/ld-musl-aarch64.so.1'):
                fields, data = target[name]
                require(stat.S_ISREG(fields[1]) and fields[4] == 1, 'unsafe sealed runtime')
                archive.add(members, name, data, fields[1])
            for name in ('dev', 'sys', 'proc'):
                archive.add(members, name, b'', stat.S_IFDIR | 0o755)
            archive.add(members, 'cache', cache, stat.S_IFREG | 0o644)
            body = driver.replace('mount -t proc proc /proc', funcs+'\nmount -t proc proc /proc').replace('@PHASE@', phase)
            archive.add(members, 'init', body.encode(), stat.S_IFREG | 0o755)
            initrd = output/(phase+'.cpio.gz')
            initrd.write_bytes(gzip.compress(archive.encode(members), mtime=0))
            command = ['podman', 'run', '--rm', '--network=none', '--cap-drop=ALL', '--security-opt', 'label=disable',
                '-v', str(args.kernel.resolve())+':/Image:ro', '-v', str(initrd)+':/initramfs:ro',
                '-v', str(output)+':/work:rw', container, 'timeout', '45', 'qemu-system-aarch64',
                '-M', 'virt', '-cpu', 'cortex-a72', '-m', '512', '-smp', '2', '-nographic',
                '-monitor', 'none', '-nic', 'none', '-no-reboot', '-kernel', '/Image', '-initrd', '/initramfs',
                '-append', 'console=ttyAMA0 rdinit=/init panic=2',
                '-drive', 'file=/work/'+disk.name+',format=raw,if=virtio',
                '-drive', 'file=/work/protected.img,format=raw,if=virtio,readonly=on']
            begin = time.monotonic()
            result = run(command, check=False, timeout=55)
            log = result.stdout.decode(errors='replace')+result.stderr.decode(errors='replace')
            (output/(phase+'.log')).write_text(log)
            expected = {'prepare': ['INTERRUPTED_UPDATE_DURABLE', 'sysrq: Resetting'],
                'recover': ['recovery complete', 'WORK_GUARD_PASS', 'KERNEL_WORK_CLEANUP_PASS',
                    'HOSTILE_WORK_ENTRIES_REJECTED',
                    'INTERRUPTED_ETC_ONLY_PASS', 'INDEPENDENT_UPDATE_MARKERS_PASS',
                    'MALFORMED_MARKER_REJECTED', 'INTERRUPTED_VAR_ONLY_PASS',
                    'CLEAN_REMOUNT_GUARD_PASS', 'OVERLAY_RECOVERY_COMPLETE'],
                'corrupt': ['CORRUPT_MOUNT_REJECTED']}[phase]
            missing = [marker for marker in expected if marker not in log]
            passed = result.returncode == 0 and not missing and 'OVERLAY_GUEST_FAILED' not in log
            report['cases'].append(dict(phase=phase, status='PASS' if passed else 'FAIL',
                missing=missing, exit_code=result.returncode, seconds=time.monotonic()-begin))
            if phase == 'prepare':
                require(passed, 'preparation did not reach controlled VM reset')
            if phase == 'recover' and passed:
                fsck = run(['e2fsck', '-fn', disk], check=False)
                (output/'recovered-fsck.log').write_bytes(fsck.stdout+fsck.stderr)
                require(fsck.returncode == 0, 'recovered disposable filesystem is not clean')
        require(sha(protected) == protected_hash, 'read-only sentinel disk changed')
        report['protected_disk_sha256'] = protected_hash
        require(all(c['status'] == 'PASS' for c in report['cases']), 'one or more guest cases failed')
        require({name: sha(path) for name, path in inputs.items()} == report['input_sha256'],
                'exact input changed during test')
        require(run(['git', '-C', R, 'rev-parse', 'HEAD']).stdout.decode().strip() == report['source_revision']
                and run(['git', '-C', R, 'diff', '--binary', 'HEAD']).stdout == source_before
                and sha(Path(__file__)) == report['runner_sha256'], 'source changed during test')
        report['status'] = 'PASS'
    except MissingPrerequisite as error:
        report.update(status='BLOCKED', error=str(error))
    except Exception as error:
        report['error'] = str(error)
    finally:
        report['duration_seconds'] = time.monotonic()-started
        (output/'result.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report['cases']))
    print(json.dumps({k: report[k] for k in ('status', 'duration_seconds')} | {'error': report.get('error')}))
    return 0 if report['status'] == 'PASS' else 77 if report['status'] == 'BLOCKED' else 1


if __name__ == '__main__':
    raise SystemExit(main())
