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
import shlex
import stat
import subprocess
import tempfile
import tarfile
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


def verified_plan(raw, bundle, manifest_hash):
    """Consume the sealed verifier's complete v1 record without lossy dict parsing."""
    if not raw or len(raw) > 4096 or not raw.endswith(b'\n') or b'\r' in raw or b'\0' in raw:
        raise ValueError('invalid verified plan framing')
    pairs = [line.split('=', 1) for line in raw.decode('ascii').splitlines()]
    if any(len(pair) != 2 for pair in pairs) or len({p[0] for p in pairs}) != len(pairs):
        raise ValueError('malformed or duplicate verified plan fields')
    plan = dict(pairs)
    keys = {'format','bundle','manifest_sha256','profile','kernel_file','dtb_file',
            'initramfs_file','target_id','target_release','target_timeout','cmdline_sha256','cmdline'}
    fixed = dict(format='rog5-verified-plan-v1', bundle=bundle, manifest_sha256=manifest_hash,
                 kernel_file='Image', dtb_file='board.dtb', initramfs_file='initramfs.cpio.gz')
    if (plan.keys() != keys or any(plan.get(k) != v for k,v in fixed.items())
            or hashlib.sha256(plan['cmdline'].encode('ascii')).hexdigest() != plan['cmdline_sha256']):
        raise ValueError('verified plan identity, schema or command hash mismatch')
    return plan


def sealed_bundle_plan(members, bundle, manifest_hash):
    """Run only the verifier from a previously authenticated recovery archive.

    The caller must bind recovery bytes to its reviewed wrapper. No source
    substitute, private signing key, claim entry, target execution or device.
    """
    if (not re.fullmatch(r'[a-z0-9][a-z0-9._-]{0,127}', bundle)
            or not re.fullmatch(r'[0-9a-f]{64}', manifest_hash)):
        raise ValueError('invalid sealed bundle selection')
    for name in ('bin/busybox', 'lib/ld-musl-aarch64.so.1', 'usr/libexec/rog5-bundle-verify'):
        member = members.get(name)
        if member is None or member[0][1:5] != [stat.S_IFREG | 0o755, 0, 0, 1]:
            raise ValueError('invalid sealed verification runtime: '+name)
    prefix = 'usr/share/rog5/ram-bundles/'+bundle
    manifest = members.get(prefix+'/manifest')
    if manifest is None or hashlib.sha256(manifest[1]).hexdigest() != manifest_hash:
        raise ValueError('embedded manifest identity mismatch')
    with tempfile.TemporaryDirectory(prefix='rog5-sealed-plan-') as tmp:
        root = Path(tmp)
        SEALED.extract(members, root)
        (root/'rog5-qemu').touch()
        script = ('set -eu\nmkdir -m 700 /run/rog5-bundles\ncp -a '
                  +shlex.quote('/'+prefix)+' /run/rog5-bundles/\n'
                  +'exec /rog5-qemu /usr/libexec/rog5-bundle-verify '
                  +shlex.quote(bundle)+' '+manifest_hash+'\n')
        result = subprocess.run([
            'bwrap', '--unshare-all', '--uid', '0', '--gid', '0', '--cap-drop', 'ALL',
            '--die-with-parent', '--new-session', '--ro-bind', str(root), '/',
            '--tmpfs', '/run', '--dev', '/dev', '--ro-bind',
            '/usr/bin/qemu-aarch64-static', '/rog5-qemu', '--clearenv',
            '--setenv', 'PATH', '/sbin:/bin:/usr/sbin:/usr/bin',
            '/rog5-qemu', '/bin/busybox', 'sh', '-c', script],
            capture_output=True, timeout=20)
        if result.returncode:
            raise ValueError('sealed bundle verification refused: '+result.stderr.decode(errors='replace')[:512])
        return verified_plan(result.stdout, bundle, manifest_hash)


def wrapper_composition(boot, kernel, recovery, cmdline):
    """Pair final boot-v3 bytes with reviewed inputs; NOT signature/admission.

    Reuse the pinned Android unpacker used by the existing packaging workflow.
    Callers still verify the boot-image identity, AVB, signed nested bundle and
    target plan. In particular, header consistency alone grants no authority.
    """
    if (len(boot) < 4096 or len(boot) > 256 * 1024 * 1024
            or boot[:8] != b'ANDROID!' or boot[40:44] != b'\x03\0\0\0'
            or int.from_bytes(boot[20:24], 'little') != 1580 or any(boot[24:40])
            or not kernel or not recovery or not cmdline or '\0' in cmdline):
        raise ValueError('invalid boot-v3 composition inputs')
    tool = REPO/'artifacts/android-boot-tools-v1/unpack_bootimg.py'
    expected_tool = '7012fe91c4032446f23f3bd6f86fe1bc274517eb4e7aef923ed8396a5b619aef'
    if tool.is_symlink() or hashlib.sha256(tool.read_bytes()).hexdigest() != expected_tool:
        raise ValueError('boot unpacker identity changed')
    unpacker = load('composition_boot_unpacker', str(tool.relative_to(REPO)))
    with tempfile.TemporaryDirectory(prefix='rog5-wrapper-composition-') as tmp:
        info = unpacker.unpack_boot_image(io.BytesIO(boot), tmp)
        if (info.header_version != 3 or info.cmdline != cmdline
                or info.kernel_size != len(kernel) or info.ramdisk_size != len(recovery)
                or (Path(tmp)/'kernel').read_bytes() != kernel
                or (Path(tmp)/'ramdisk').read_bytes() != recovery):
            raise ValueError('wrapper kernel/recovery/command-line mismatch')
    return dict(scope='boot-v3 payload pairing only', avb_verified=False,
                release_qualified=False, cmdline=cmdline,
                hashes={name: hashlib.sha256(data).hexdigest()
                        for name, data in (('boot', boot), ('kernel', kernel), ('recovery', recovery))})


def archive_parameters(members, *, profile='rescue'):
    if profile not in ('rescue', 'server-runtime'):
        raise ValueError('unknown composition profile')
    # Matching source bytes are insufficient when the sealed file cannot be
    # executed or is writable/owned by another account. Check before rendering
    # or running any fixture; optional observation remains optional.
    required_modes = {
        'init': 0o755,
        'usr/local/sbin/rog5-p2-attest': 0o755,
        'sbin/rog5-load-persistent-power-usb': 0o755,
        'usr/local/sbin/rog5-persistent-state': 0o755,
        'usr/local/sbin/rog5-persistent-ssh-identity': 0o755,
        'usr/local/sbin/rog5-persistent-keyring': 0o755,
        'usr/local/share/rog5/rog5-package-keyring.service': 0o644,
    }
    if 'usr/local/sbin/rog5-startup-observer' in members:
        required_modes['usr/local/sbin/rog5-startup-observer'] = 0o755
    for name, mode in required_modes.items():
        member = members.get(name)
        if member is None or member[0][1:5] != [stat.S_IFREG | mode, 0, 0, 1]:
            raise ValueError('invalid startup member metadata: '+name)
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


def driver(source, *, profile='rescue', recovery_timeout=None):
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
    if recovery_timeout is not None:
        if type(recovery_timeout) is not int or not 300 <= recovery_timeout <= 900:
            raise ValueError('invalid signed runtime timeout')
        script = script.replace('recovery_timeout=1\n', 'recovery_timeout='+str(recovery_timeout)+'\n')
        script += '''
if [ -e /run/systemd/system/rog5-startup-observer.service ]; then
    [ "$(sed -n 's/^RuntimeMaxSec=//p' /run/systemd/system/rog5-startup-observer.service)" = "$recovery_timeout" ]
    grep -Fx "ExecStart=/run/rog5-startup-observer $((recovery_timeout - 30))" /run/systemd/system/rog5-startup-observer.service
fi
echo COMPOSITION_TIMING_UNITS_PASS
'''
    return script


def firmware_composition(members, expected_hash, expected_count):
    prefix='opt/rog5-charge-firmware/'
    rows=[]
    for path in sorted(name for name in members if name.startswith(prefix)):
        name=path[len(prefix):]
        fields,data=members[path]
        if (not re.fullmatch(r'[A-Za-z0-9._-]+',name)
                or fields[1:5] != [stat.S_IFREG|0o644,0,0,1]):
            raise ValueError('invalid firmware member: '+path)
        rows.append(dict(name=name,size=len(data),sha256=hashlib.sha256(data).hexdigest()))
    digest=hashlib.sha256(''.join(row['sha256']+'  '+row['name']+'\n' for row in rows).encode()).hexdigest()
    if len(rows)!=expected_count or digest!=expected_hash:
        raise ValueError('firmware inventory/content differs from accepted build input')
    return dict(tree_sha256=digest,files=rows,scope='sealed firmware composition, not DSP execution')


def radio_firmware_composition(members):
    """Verify the sealed WCN6855 inventory, not physical firmware execution.

    The caller already authenticated the enclosing archive. Reuse its actual
    radio manifest rather than substituting files from the host firmware tree.
    """
    prefix='rog5-native-wifi/'
    required={'firmware/ath11k/WCN6855/hw1.1/'+name for name in
              ('amss.bin','board-2.bin','m3.bin','regdb.bin')}
    required.update(('firmware/regulatory.db','firmware/regulatory.db.p7s'))
    manifest=members.get(prefix+'radio-files.sha256')
    if (manifest is None or manifest[0][1:5] != [stat.S_IFREG|0o644,0,0,1]
            or not manifest[1] or len(manifest[1])>65536
            or not manifest[1].endswith(b'\n')):
        raise ValueError('invalid sealed radio manifest')
    hashes={}
    for line in manifest[1].splitlines():
        match=re.fullmatch(rb'([0-9a-f]{64})  ([A-Za-z0-9_./-]{1,255})',line)
        if not match: raise ValueError('invalid radio manifest record')
        digest,name=(value.decode('ascii') for value in match.groups())
        if any(part in ('','.','..') for part in name.split('/')) or name in hashes:
            raise ValueError('unsafe or duplicate radio manifest path')
        member=members.get(prefix+name)
        if (member is None or not stat.S_ISREG(member[0][1])
                or member[0][2:5] != [0,0,1] or member[0][1]&0o6022
                or hashlib.sha256(member[1]).hexdigest()!=digest):
            raise ValueError('radio manifest content/metadata mismatch: '+name)
        hashes[name]=digest
    firmware=set()
    for path,(fields,data) in members.items():
        if not path.startswith(prefix+'firmware/'): continue
        if stat.S_ISDIR(fields[1]):
            if fields[2:4]!=[0,0] or fields[1]&0o6022:
                raise ValueError('unsafe radio firmware directory')
            continue
        name=path[len(prefix):];firmware.add(name)
        if name not in required or fields[1:5]!=[stat.S_IFREG|0o644,0,0,1]:
            raise ValueError('unexpected radio firmware member: '+path)
    if firmware!=required or {name for name in hashes if name.startswith('firmware/')}!=required:
        raise ValueError('radio firmware inventory mismatch')
    return dict(manifest_sha256=hashlib.sha256(manifest[1]).hexdigest(),
                files=[dict(name=name,sha256=hashes[name],size=len(members[prefix+name][1]))
                       for name in sorted(required)],
                scope='sealed WCN6855/regulatory content; physical firmware response untested')


def radio_module_files(members, release):
    """Read a bounded, hash-closed nested module tree without extractall()."""
    prefix='rog5-native-wifi/'
    values=[]
    for name in ('module-root-complete.tar.gz','module-files.sha256'):
        entry=members.get(prefix+name)
        if (entry is None or entry[0][1:5] != [stat.S_IFREG|0o644,0,0,1]):
            raise ValueError('invalid nested module package metadata')
        values.append(entry[1])
    package,manifest=values
    if not re.fullmatch(r'7\.1\.4-g[0-9a-f]{12}',release) or len(package)>128*1024**2 or len(manifest)>65536:
        raise ValueError('module package bounds/release')
    root='lib/modules/'+release+'/'
    expected={}
    for line in manifest.splitlines():
        match=re.fullmatch(rb'([0-9a-f]{64})  ([A-Za-z0-9_./-]{1,255})',line)
        if not match: raise ValueError('invalid module manifest')
        digest,name=(value.decode() for value in match.groups())
        if (name in expected or not name.startswith(root)
                or any(part in ('','.','..') for part in name.split('/'))):
            raise ValueError('unsafe/duplicate module manifest path')
        expected[name]=digest
    if not expected or not manifest.endswith(b'\n'):
        raise ValueError('empty/truncated module manifest')
    files={};seen=set();total=0
    try:
        with gzip.GzipFile(fileobj=io.BytesIO(package)) as compressed:
            payload=compressed.read(160*1024**2+1)
        if len(payload)>160*1024**2: raise ValueError('expanded tar bound')
        with tarfile.open(fileobj=io.BytesIO(payload),mode='r:') as tar:
            for member in tar:
                name=member.name.removeprefix('./')
                if name in ('','.'):
                    if ('.' in seen or not member.isdir() or member.uid or member.gid or member.mode&0o6022):
                        raise ValueError('unsafe nested archive root')
                    seen.add('.');continue
                if (name in seen or len(seen)>=256 or member.uid or member.gid
                        or member.mode&0o6022 or any(part in ('','.','..') for part in name.split('/'))):
                    raise ValueError('unsafe nested module member')
                seen.add(name)
                if member.isdir():
                    if not (root.startswith(name+'/') or name.startswith(root)):
                        raise ValueError('directory outside exact module tree')
                    continue
                if not member.isfile() or name not in expected or member.size>32*1024**2:
                    raise ValueError('unlisted or nonregular nested module')
                total+=member.size
                if total>128*1024**2: raise ValueError('expanded module package bound')
                data=tar.extractfile(member).read()
                if hashlib.sha256(data).hexdigest()!=expected[name]: raise ValueError('nested module hash mismatch')
                files[name]=data
    except (tarfile.TarError,EOFError) as error:
        raise ValueError('invalid nested module archive') from error
    if files.keys()!=expected.keys() or any(str(parent) in files for name in files for parent in Path(name).parents):
        raise ValueError('nested module inventory/path collision')
    return files


def radio_module_composition(members, core, release):
    """Resolve sealed software radio roots; board activation stays pending."""
    prefix='rog5-native-wifi/'
    roots=members.get(prefix+'load-roots.txt')
    if (roots is None or roots[0][1:5] != [stat.S_IFREG|0o644,0,0,1]
            or roots[1]!=(REPO/'configs/kernel/rog5-native-wifi-module-roots').read_bytes()
            or members[prefix+'probe-native-wifi.sh'][1]!=(REPO/'scripts/device/probe-native-wifi.sh').read_bytes()):
        raise ValueError('unpaired sealed radio load order')
    files=radio_module_files(members,release)
    fixture=dict(members);rows=list(core);loaded={row['name']:row for row in core}
    order=[name for name in roots[1].decode().splitlines() if name not in ('phy-qcom-qmp-pcie','ath11k_pci')]
    order+=['phy-qcom-qmp-pcie','ath11k_pci']
    deadline=time.monotonic()+15
    def read(args):
        remaining=deadline-time.monotonic()
        if remaining<=0: raise ValueError('radio dependency deadline exceeded')
        return subprocess.check_output(args,text=True,timeout=min(5,remaining)).strip()
    with tempfile.TemporaryDirectory(prefix='rog5-radio-closure-') as temp:
        root=Path(temp)
        for name,data in files.items():
            path=root/name;path.parent.mkdir(parents=True,exist_ok=True)
            path.write_bytes(data);path.chmod(0o400)
        for name in order:
            plan=read(['modprobe','-C','/dev/null','--ignore-install','--show-depends','-d',str(root),'-S',release,name])
            if not plan: raise ValueError('empty radio dependency plan: '+name)
            for line in plan.splitlines():
                # All configured roots are modular in this sealed composition.
                fields=line.split()
                if len(fields)!=2 or fields[0]!='insmod': raise ValueError('unexpected dependency action')
                path=Path(fields[1]);relative=str(path.relative_to(root))
                if relative not in files or not relative.endswith('.ko'): raise ValueError('module outside sealed tree')
                data=files[relative]
                info={field:read(['modinfo','-F',field,str(path)]) for field in ('name','depends','vermagic')}
                module=info['name'];digest=hashlib.sha256(data).hexdigest()
                if (not re.fullmatch(r'[A-Za-z0-9_]+',module)
                        or info['vermagic']!=core[0]['vermagic'] or info['vermagic'].split()[0]!=release
                        or data[:6]!=b'\x7fELF\x02\x01' or data[16:20]!=b'\x01\x00\xb7\x00'):
                    raise ValueError('radio module identity/ABI mismatch')
                if module in loaded:
                    if loaded[module]['sha256']!=digest: raise ValueError('conflicting already-loaded module')
                    continue
                if any(dep.replace('-','_') not in loaded for dep in info['depends'].split(',') if dep):
                    raise ValueError('radio dependency absent or late')
                target='a01-radio-modules/'+module+'.ko'
                SEALED.ARCHIVE.add(fixture,target,data,stat.S_IFREG|0o644)
                parameters={'pwrseq_qcom_wcn':['serial_observation_ms=250'],
                            'pci_pwrctrl_pwrseq':['observation_ms=250']}.get(module,[])
                row=dict(path=target,sha256=digest,parameters=parameters,**info)
                rows.append(row);loaded[module]=row
    return fixture,rows,dict(roots=order,software_modules=rows[len(core):],
        package_sha256=hashlib.sha256(members[prefix+'module-root-complete.tar.gz'][1]).hexdigest(),
        scope='software module closure/load only; ASUS board-only helpers remain untested')


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


def board_helper_refusals(members, vermagic):
    """Two exact modules can reach ENODEV without a fake ASUS board/provider.

    Activation requires the real S12 export and remains a separate pending
    check. Wrong-board refusal proves load-time ABI, not physical operation.
    """
    prefix='rog5-native-wifi/'
    loader=members.get(prefix+'module-once')
    if loader is None or loader[0][1:5]!=[stat.S_IFREG|0o755,0,0,1]:
        raise ValueError('unsafe sealed one-call module loader')
    rows=[];deadline=time.monotonic()+10
    with tempfile.TemporaryDirectory(prefix='rog5-board-module-metadata-') as temp:
        for filename,parameters in (('rog5-pmic-pon-readonly.ko',[]),
                                    ('rog5-s12-ufs-vote.ko',['action=held-oem'])):
            path=prefix+filename
            member=members.get(path)
            if (member is None or member[0][1:5]!=[stat.S_IFREG|0o644,0,0,1]
                    or len(member[1])<64 or member[1][:6]!=b'\x7fELF\x02\x01'
                    or member[1][16:20]!=b'\x01\x00\xb7\x00'):
                raise ValueError('unsafe board helper: '+path)
            file=Path(temp)/filename;file.write_bytes(member[1]);file.chmod(0o400)
            info={}
            for field in ('name','depends','vermagic'):
                remaining=deadline-time.monotonic()
                if remaining<=0:raise ValueError('board helper metadata deadline')
                info[field]=subprocess.check_output(['modinfo','-F',field,str(file)],
                    text=True,timeout=min(5,remaining)).strip()
            if (info['name']!=file.stem.replace('-','_') or info['depends']
                    or info['vermagic']!=vermagic):
                raise ValueError('board helper identity/dependency/ABI mismatch')
            rows.append(dict(path=path,parameters=parameters,
                sha256=hashlib.sha256(member[1]).hexdigest(),**info))
    return rows


def board_refusal_driver(rows):
    script=''
    for row in rows:
        command='/rog5-native-wifi/module-once '+shlex.quote('/'+row['path'])
        command+=''.join(' '+shlex.quote(arg) for arg in row['parameters'])
        script+='''set +e
'''+command+''' >/run/composition-refusal.log 2>&1
refusal_status=$?
set -e
[ "$refusal_status" -eq 1 ]
[ "$(wc -l </run/composition-refusal.log)" -eq 1 ]
grep -Eq '^module-once finit_module errno=19 [(].*[)]; no retry$' /run/composition-refusal.log
'''
        script+='[ ! -d '+shlex.quote('/sys/module/'+row['name'])+' ]\n'
        script+='cat /run/composition-refusal.log\n'
        script+='echo COMPOSITION_HELPER_'+row['name']+'_REFUSED_ENODEV\n'
    return script


def activation_refusal_driver():
    """Never simulate a valid hold: inspect the consumer's safe refusal only."""
    script='''[ ! -d /sys/module/rog5_s12_ufs_vote ]
insmod /a01/rog5_a01_s12_shim.ko
[ -s /sys/kernel/btf/rog5_a01_s12_shim ]
[ "$(cat /sys/module/rog5_a01_s12_shim/parameters/validator_calls)" = 0 ]
'''
    consumer=dict(name='rog5_wifi_activate',path='rog5-native-wifi/rog5-wifi-activate.ko',parameters=[])
    script+=board_refusal_driver([consumer]).replace(
        'COMPOSITION_HELPER_rog5_wifi_activate','COMPOSITION_CONSUMER_rog5_wifi_activate')
    return script+'''[ "$(cat /sys/module/rog5_a01_s12_shim/parameters/btf_coming)" = 1 ]
[ "$(cat /sys/module/rog5_a01_s12_shim/parameters/consumer_live)" = 0 ]
[ "$(cat /sys/module/rog5_a01_s12_shim/parameters/validator_calls)" = 0 ]
rmmod rog5_a01_s12_shim
[ ! -d /sys/module/rog5_a01_s12_shim ]
echo COMPOSITION_ACTIVATION_SPLIT_PASS
'''


def vm_runtime_passed(log, code, modules, *, firmware=False, radio=False, refusals=(), activation=False):
    lines = log.replace('\r\n', '\n').splitlines()
    loaded = re.findall(r'^COMPOSITION_MODULE_([A-Za-z0-9_]+)$', '\n'.join(lines), re.M)
    refused = re.findall(r'^COMPOSITION_HELPER_([A-Za-z0-9_]+)_REFUSED_ENODEV$', '\n'.join(lines), re.M)
    markers=MARKERS+ (('FIRMWARE_RUNTIME',) if firmware else ())
    if radio:
        if not firmware: return False
        markers+=('RADIO_FIRMWARE',)
    split=[line for line in lines if line.startswith(('COMPOSITION_CONSUMER_','COMPOSITION_ACTIVATION_'))]
    expected_split=['COMPOSITION_CONSUMER_rog5_wifi_activate_REFUSED_ENODEV',
                    'COMPOSITION_ACTIVATION_SPLIT_PASS'] if activation else []
    return (code == 0 and loaded == [row['name'] for row in modules]
            and refused == [row['name'] for row in refusals]
            and split == expected_split
            and all(lines.count('COMPOSITION_'+name+'_PASS') == 1 for name in markers)
            and lines.count('COMPOSITION_VM_COMPLETE') == 1
            and not re.search(r'COMPOSITION_VM_FAILURE|Unknown symbol|Invalid module|'
                              r'BTF[^\n]*(?:invalid|fail)|Kernel panic|Oops:|WARNING:', log))


def vm_runtime(members, modules, kernel, root_image, output, *, profile,
               recovery_timeout=None, command_line=None, firmware=False, refusals=(), activation_fixture=None):
    """Combine exact module insertion and existing Arch preparation on QEMU virt.

    No phone DTB, network, hardware activation or writable block device. The
    caller authenticates inputs and hashes the retained root before and after.
    This is runtime composition, not physical probe or watchdog qualification.
    """
    started = time.monotonic()
    image = subprocess.check_output(['podman', 'image', 'inspect', '--format', '{{.Id}}',
        'localhost/rog5-qemu-gate:ubuntu-24.04'], text=True, timeout=10).strip()
    if not re.fullmatch(r'(?:sha256:)?[0-9a-f]{64}', image):
        raise ValueError('invalid resolved QEMU container identity')
    fixture = dict(members)
    add = SEALED.ARCHIVE.add
    if any(name=='a01' or name.startswith('a01/') for name in members):
        raise ValueError('test-only fixture namespace present in target archive')
    if activation_fixture is not None:
        if not any(row['name']=='rog5_s12_ufs_vote' for row in refusals):
            raise ValueError('consumer fixture cannot replace separate real provider proof')
        add(fixture,'a01/rog5_a01_s12_shim.ko',activation_fixture,stat.S_IFREG|0o644)
    if profile=='server-runtime' and firmware:
        # Software radio modules need regulatory lookup before the later
        # runtime handover. Use the same sealed bytes in QEMU's default path;
        # no Qualcomm PCI endpoint or firmware execution is simulated.
        for row in radio_firmware_composition(members)['files']:
            add(fixture,'lib/'+row['name'],members['rog5-native-wifi/'+row['name']][1],stat.S_IFREG|0o644)
    for name in ('proc','sys','dev','run','mnt','mnt/root-ro','mnt/state','newroot'):
        if name in fixture:
            if not stat.S_ISDIR(fixture[name][0][1]):
                raise ValueError('non-directory VM mountpoint: '+name)
        else:
            add(fixture,name,b'',stat.S_IFDIR | 0o755)
    script = '''#!/bin/busybox sh
set -eu
export PATH=/bin:/sbin:/usr/bin:/usr/sbin
/bin/busybox --install -s /bin
mount -t devtmpfs devtmpfs /dev
exec </dev/console >/dev/console 2>&1
trap 'echo COMPOSITION_VM_FAILURE; dmesg; poweroff -f' EXIT
mount -t proc proc /proc
mount -t sysfs sysfs /sys
mount -t tmpfs tmpfs /run
'''
    if firmware:
        loader=members['sbin/rog5-load-persistent-power-usb'][1].decode()
        begin=loader.index('[ -d "$firmware_source" ]')
        end=loader.index('\n\n',loader.index("fail firmware-path",begin))
        script += '''firmware_source=/opt/rog5-charge-firmware
firmware_runtime=/run/rog5-charge-firmware
fail() { echo "COMPOSITION_VM_FAILURE $*"; exit 1; }
'''+loader[begin:end]+'''
[ "$(cat /sys/module/firmware_class/parameters/path)" = "$firmware_runtime" ]
echo COMPOSITION_FIRMWARE_RUNTIME_PASS
'''
    for row in modules:
        # Paths and names came from module_closure, never free-form commands.
        script += 'insmod '+shlex.quote('/'+row['path'])+''.join(' '+shlex.quote(arg) for arg in row.get('parameters',[]))+'\n'
        script += '[ "$(cat '+shlex.quote('/sys/module/'+row['name']+'/initstate')+')" = live ]\n'
        script += 'echo COMPOSITION_MODULE_'+row['name']+'\n'
    script += board_refusal_driver(refusals)
    if activation_fixture is not None:script+=activation_refusal_driver()
    script += '''mount -t ext4 -o ro,noload /dev/vda /mnt/root-ro
mount -t tmpfs tmpfs /mnt/state
mkdir /mnt/state/upper /mnt/state/work
mount -t overlay overlay -o lowerdir=/mnt/root-ro,upperdir=/mnt/state/upper,workdir=/mnt/state/work /newroot
mount --bind /run /newroot/run
mount --bind /dev /newroot/dev
mount --bind /proc /newroot/proc
mount --bind /sys /newroot/sys
'''
    if command_line is not None:
        source=members['init'][1].decode()
        begin=source.index('\nrecovery_timeout=600\n')
        end=source.index('\narm_watchdog || force_rollback',begin)
        script += source[begin:end].replace('$(cat /proc/cmdline)',shlex.join(shlex.split(command_line)))
        script += '\n[ "$recovery_timeout" = '+shlex.quote(str(recovery_timeout))+' ]\n'
    script += '/bin/sh /composition-test.sh\n'
    if profile=='server-runtime' and firmware:
        # Exact sealed BusyBox checks the same manifest as the target radio
        # loader. This performs no radio activation, module insertion or write
        # outside the disposable VM's tmpfs runtime.
        script += '''(cd /run/rog5-native-wifi && sha256sum -c radio-files.sha256)
echo COMPOSITION_RADIO_FIRMWARE_PASS
'''
    if command_line is not None:
        begin=source.index('publish_stage() {\n')
        script += source[begin:source.index('\n}\n',begin)+3]+'''
stage_sequence=0
stage_record=/run/a01-stage.record
target_boot_id=$(cat /proc/sys/kernel/random/boot_id)
running_kernel_release=$(uname -r)
log() { :; }
publish_stage runtime PASS composition
echo COMPOSITION_STAGE_BEGIN
cat "$stage_record"
echo COMPOSITION_STAGE_END
'''
    script += 'dmesg\necho COMPOSITION_VM_COMPLETE\ntrap - EXIT\npoweroff -f\n'
    del fixture['init']  # Replace only the disposable VM entry, never sealed input.
    add(fixture,'init',script.encode(),stat.S_IFREG | 0o755)
    add(fixture,'composition-test.sh',driver(members['init'][1].decode(),profile=profile,
                                            recovery_timeout=recovery_timeout).encode(),
        stat.S_IFREG | 0o755)
    archive = output/'composition-vm.cpio.gz'
    archive.write_bytes(gzip.compress(SEALED.ARCHIVE.encode(fixture),mtime=0))
    command = ['podman','run','--rm','--pull=never','--network=none','--cap-drop=ALL',
        '--security-opt=no-new-privileges','--cpus=2','--memory=1g',
        '-v',str(kernel)+':/Image:ro','-v',str(archive)+':/initramfs:ro',
        '-v',str(root_image)+':/arch.ext4:ro',image,
        'timeout','--kill-after=2','60','qemu-system-aarch64','-M','virt','-cpu','cortex-a72',
        '-m','512','-smp','2','-nographic','-monitor','none','-nic','none','-no-reboot',
        '-kernel','/Image','-initrd','/initramfs','-append','console=ttyAMA0 rdinit=/init panic=2',
        '-drive','file=/arch.ext4,format=raw,if=none,id=root,readonly=on',
        '-device','virtio-blk-device,drive=root']
    with (output/'runtime.log').open('xb') as log:
        try:
            code = subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,timeout=70).returncode
        except subprocess.TimeoutExpired:
            code = 124
    log = (output/'runtime.log').read_text(errors='replace')
    passed=vm_runtime_passed(log,code,modules,firmware=firmware,
                             radio=firmware and profile=='server-runtime',refusals=refusals,
                             activation=activation_fixture is not None)
    frame=None
    if command_line is not None:
        passed=passed and log.splitlines().count('COMPOSITION_TIMING_UNITS_PASS')==1
        frames=re.findall(r'(?m)^COMPOSITION_STAGE_BEGIN\r?\n(.*?)^COMPOSITION_STAGE_END\r?$',log,re.S)
        if len(frames)==1:
            frame=frames[0].replace('\r\n','\n')
        else:
            passed=False
    return dict(status='PASS' if passed else 'FAIL',stage_frame=frame,
        container=image,command=command,exit_code=code,modules=modules,board_refusals=list(refusals),
        activation_split='PASS' if passed and activation_fixture is not None else 'NOT RUN',
        fixture_sha256=ACCEPTANCE.sha_file(archive),duration_seconds=time.monotonic()-started,
        limitations=['virtual hardware only','tmpfs upper, no persistent state activation',
                     'unit generation, not watchdog expiry execution',
                     'radio activation and physical firmware responses not tested'])


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
