#!/usr/bin/env python3
"""Attended RAM-only trial of one packaged production wrapper. Never flashes.

  status       host-only USB state of the approved port (no phone command)
  probe        read-only SSH health read of a running target
  to-fastboot  ask a running target for its normal clean reboot (the RAM
               shutdown stage ends in restart2("bootloader")) and wait
  boot         check the exact fastboot identity, consume the one-use claim
               for this wrapper hash, RAM-boot a sealed snapshot
  observe      bounded capture of USB transitions, SSH health and the kernel
               log into a new evidence directory

Only 'boot' changes phone state beyond a normal reboot, and only with
ROG5_ALLOW_RAM_TRIAL=1. A wrapper hash is consumed once: retrying the same
image needs a deliberate new decision (remove its claim marker by hand).
"""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import time

SERIAL = 'ROG5-SERIAL-REDACTED'
PRODUCT = 'lahaina'
IMAGE_SIZE = 134217728
USB = Path(os.environ.get('ROG5_TRIAL_USB', '/sys/bus/usb/devices/1-1.2'))
ANCHOR = os.environ.get('ROG5_TRIAL_ANCHOR', '/sys/devices/pci0000:00/0000:00:08.1/0000:04:00.3/usb1/1-1/1-1.2')
NET = Path(os.environ.get('ROG5_TRIAL_NET', '/sys/class/net'))
INTERFACE = 'enp4s0f3u1u2'
FASTBOOT = Path(os.environ.get('ROG5_TRIAL_FASTBOOT', '/usr/bin/fastboot'))
SSH = os.environ.get('ROG5_TRIAL_SSH', '/usr/bin/ssh')
STATE = Path.home()/'.local/state'
KEY = STATE/'rog5-v13-live-inputs-20260823-r1/deployment-ssh-key'
KNOWN_HOSTS = STATE/'rog5-native-root-release-v6-20260829-r1/v7-stable-known-hosts'
CLAIMS = Path(os.environ.get('ROG5_TRIAL_CLAIMS', STATE/'rog5-production-boot-20260923/claims'))
SHA = re.compile(r'[0-9a-f]{64}')
NMCLI = os.environ.get('ROG5_TRIAL_NMCLI', '/usr/bin/nmcli')
# Existing NetworkManager profiles on the phone's NCM interface: the V9-line
# targets answer on 10.77.0.2, the V11 fallback only on link-local.
PROFILES = {'10.77.0.2': 'rog5-standalone-shared', '169.254.77.2': 'rog5-fallback-usb-ssh'}
RESCUE = {
    'R1': 'Hold Power + Volume Up about 20 s; when it vibrates or the logo shows, '
          'release Power and keep holding Volume Up until fastboot appears.',
    'R2': 'Crashdump screen: hold Volume Down + Power 8-12 s, then immediately do R1. '
          'Do not pick Recovery or Power off.',
}
HANG_SECONDS = 240
# How a running target reaches fastboot. 'reboot' is a normal clean systemd
# reboot, for targets whose RAM shutdown stage already ends in
# restart2("bootloader"). 'helper' runs that same helper directly after sync;
# it writes nothing on the phone. Userdata then gets one normal ext4 journal
# replay at its next mount, which the production init accepts.
FASTBOOT_MODES = {
    'reboot': 'systemctl reboot',
    'helper': 'sync; sync; exec /run/initramfs/usr/libexec/rog5-reboot-bootloader',
}
PROBE = r'''set +e
echo "boot_id=$(cat /proc/sys/kernel/random/boot_id)"
echo "release=$(uname -r)"
echo "uptime=$(cut -d' ' -f1 /proc/uptime)"
echo "cmdline=$(cat /proc/cmdline)"
echo "modules=$(cut -d' ' -f1 /proc/modules | sort | tr '\n' ' ')"
echo "writable_blocks=$(for b in /sys/class/block/sd*; do [ "$(cat "$b/ro")" = 0 ] && printf '%s ' "${b##*/}"; done)"
echo "system_state=$(systemctl is-system-running 2>/dev/null)"
echo "failed_units=$(systemctl --failed --no-legend --plain 2>/dev/null | cut -d' ' -f1 | tr '\n' ' ')"
for supply in /sys/class/power_supply/*; do
	echo "supply=${supply##*/} $(cat "$supply/capacity" "$supply/temp" "$supply/voltage_now" "$supply/online" 2>/dev/null | tr '\n' ' ')"
done
'''


def need(ok, why):
    if not ok:
        raise ValueError(why)


def now():
    return time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())


def read(path):
    return (path).read_text().strip()


def usb_state():
    """Classify the single approved port. Never searches other ports."""
    try:
        if not USB.exists():
            return 'absent'
        if str(USB.resolve(strict=True)) != ANCHOR:
            return 'mismatch'
        ids = read(USB/'idVendor'), read(USB/'idProduct')
        if ids == ('0b05', '4daf'):
            return 'fastboot' if read(USB/'serial') == SERIAL else 'mismatch'
        if ids == ('05c6', '900e'):
            return 'crashdump'
        if ids != ('1d6b', '0104'):
            return 'mismatch'
        product = read(USB/'product')
        if product == 'ROG5 recovery':
            return 'recovery'
        if product != 'ROG5 persistent root':
            return 'mismatch'
        net = NET/INTERFACE
        if not net.exists():
            return 'enumerating'
        if (net/'device').resolve(strict=True).parent != USB.resolve(strict=True):
            return 'mismatch'
        return 'target'
    except OSError:
        return 'transition'


def ssh(address, command, timeout):
    for path in (KEY, KNOWN_HOSTS):
        info = path.lstat()
        need(stat.S_ISREG(info.st_mode) and info.st_uid == os.geteuid() and not info.st_mode & 0o022,
             'unsafe SSH credential file: '+path.name)
    argv = [SSH, '-F', '/dev/null', '-o', 'BatchMode=yes', '-o', 'IdentitiesOnly=yes',
            '-o', 'IdentityAgent=none', '-o', 'StrictHostKeyChecking=yes', '-o', 'UpdateHostKeys=no',
            '-o', 'ConnectTimeout=3', '-o', 'ServerAliveInterval=2', '-o', 'ServerAliveCountMax=3',
            '-o', 'HostKeyAlias=169.254.77.2', '-o', 'UserKnownHostsFile='+str(KNOWN_HOSTS),
            '-i', str(KEY), 'root@'+address, command]
    return subprocess.run(argv, stdin=subprocess.DEVNULL, capture_output=True, timeout=timeout)


def use_address(address):
    """Activate the existing host profile for this target address (no sudo)."""
    need(address in PROFILES, 'unknown target address')
    active = subprocess.run([NMCLI, '-g', 'GENERAL.CONNECTION', 'device', 'show', INTERFACE],
                            stdin=subprocess.DEVNULL, capture_output=True, timeout=10)
    if active.returncode == 0 and active.stdout.decode().strip() == PROFILES[address]:
        return False
    result = subprocess.run([NMCLI, 'connection', 'up', PROFILES[address], 'ifname', INTERFACE],
                            stdin=subprocess.DEVNULL, capture_output=True, timeout=30)
    need(result.returncode == 0, 'cannot activate host profile '+PROFILES[address])
    return True


def probe(timeout=20, address='10.77.0.2'):
    need(usb_state() == 'target', 'phone is not a running target on the approved port')
    use_address(address)
    result = ssh(address, PROBE, timeout)
    need(result.returncode == 0, 'SSH probe failed: '+result.stderr.decode(errors='replace')[-300:])
    fields = {}
    for line in result.stdout.decode(errors='replace').splitlines():
        key, _, value = line.partition('=')
        fields.setdefault(key, []).append(value)
    return {key: value[0] if len(value) == 1 else value for key, value in fields.items()}


def fastboot(*args, timeout=15):
    info = FASTBOOT.lstat()
    need(stat.S_ISREG(info.st_mode) and not info.st_mode & 0o022, 'fastboot executable is unsafe')
    return subprocess.run([str(FASTBOOT), '-s', SERIAL, *args], stdin=subprocess.DEVNULL,
                          capture_output=True, timeout=timeout)


def getvar(name):
    result = fastboot('getvar', name)
    need(result.returncode == 0, 'fastboot getvar failed: '+name)
    values = re.findall(r'^(?:\(bootloader\) )?'+re.escape(name)+r':\s*(\S+)\s*$',
                        (result.stdout+result.stderr).decode(errors='replace'), re.M)
    need(len(values) == 1, 'ambiguous fastboot getvar: '+name)
    return values[0]


def fastboot_identity():
    need(usb_state() == 'fastboot', 'phone is not in fastboot on the approved port')
    identity = {name: getvar(name) for name in ('product', 'current-slot', 'unlocked', 'max-download-size')}
    need(identity['product'] == PRODUCT, 'wrong fastboot product')
    need(identity['current-slot'] in ('b', '_b'), 'current slot is not b')
    need(identity['unlocked'] == 'yes', 'bootloader is not unlocked')
    size = identity['max-download-size']
    need(int(size, 16 if size.startswith('0x') else 10) >= IMAGE_SIZE, 'download capacity below 128 MiB')
    return identity


def sealed(image, expected):
    source = os.open(image, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
    snapshot = -1
    try:
        before = os.fstat(source)
        need(stat.S_ISREG(before.st_mode) and before.st_uid == os.geteuid() and before.st_nlink == 1
             and not before.st_mode & 0o022 and before.st_size == IMAGE_SIZE, 'wrapper metadata is unsafe')
        snapshot = os.memfd_create('rog5-production-ram-trial', os.MFD_ALLOW_SEALING | os.MFD_CLOEXEC)
        digest = hashlib.sha256()
        while block := os.read(source, 1 << 20):
            digest.update(block)
            view = memoryview(block)
            while view:
                view = view[os.write(snapshot, view):]
        need(digest.hexdigest() == expected, 'wrapper hash does not match the pin')
        os.fchmod(snapshot, 0o400)
        seals = fcntl.F_SEAL_SEAL | fcntl.F_SEAL_SHRINK | fcntl.F_SEAL_GROW | fcntl.F_SEAL_WRITE
        fcntl.fcntl(snapshot, fcntl.F_ADD_SEALS, seals)
        need(fcntl.fcntl(snapshot, fcntl.F_GET_SEALS) == seals, 'snapshot not sealed')
        os.lseek(snapshot, 0, os.SEEK_SET)
        return snapshot
    except BaseException:
        if snapshot >= 0:
            os.close(snapshot)
        raise
    finally:
        os.close(source)


def boot(image, expected, evidence):
    need(os.environ.get('ROG5_ALLOW_RAM_TRIAL') == '1', 'set ROG5_ALLOW_RAM_TRIAL=1 for one RAM-only boot')
    need(SHA.fullmatch(expected) is not None, 'wrapper pin framing')
    identity = fastboot_identity()
    snapshot = sealed(image, expected)
    try:
        CLAIMS.mkdir(mode=0o700, parents=True, exist_ok=True)
        claim = CLAIMS/(expected+'.entered')
        with open(claim, 'x') as marker:  # one use per wrapper hash, even on failure
            json.dump(dict(wrapper_sha256=expected, serial=SERIAL, entered=now(), identity=identity), marker)
        record = dict(entered=now(), identity=identity, wrapper_sha256=expected)
        result = subprocess.run([str(FASTBOOT), '-s', SERIAL, 'boot', f'/proc/self/fd/{snapshot}'],
                                stdin=subprocess.DEVNULL, capture_output=True, timeout=180,
                                pass_fds=(snapshot,))
        record.update(returncode=result.returncode, finished=now(),
                      output=(result.stdout+result.stderr).decode(errors='replace')[-2000:])
        (evidence/'boot.json').write_text(json.dumps(record, indent=2)+'\n')
        need(result.returncode == 0, 'fastboot boot failed; claim stays consumed')
        return record
    finally:
        os.close(snapshot)


def observe(evidence, seconds, interval=1.0, hang_seconds=HANG_SECONDS):
    """Record every USB transition; take one SSH health read and stream the
    kernel log while the target is reachable. Read-only on the phone. With no
    target within hang_seconds, or on the crashdump screen, prompt the one
    manual rescue step (docs/development.md) exactly once."""
    started = time.monotonic()
    deadline = started+seconds
    prompted = set()
    transitions = (evidence/'transitions.jsonl').open('a')
    last = None
    logged = False
    stream = None
    try:
        while time.monotonic() < deadline:
            state = usb_state()
            if state != last:
                transitions.write(json.dumps(dict(t=now(), state=state))+'\n')
                transitions.flush()
                print(f'{now()} usb={state}', flush=True)
                last = state
            rescue = None
            if state == 'crashdump':
                rescue = 'R2'
            elif not logged and state != 'target' and time.monotonic()-started > hang_seconds:
                rescue = 'R1'
            if rescue and rescue not in prompted:
                prompted.add(rescue)
                transitions.write(json.dumps(dict(t=now(), rescue_prompt=rescue))+'\n')
                transitions.flush()
                print(f'{now()} RESCUE {rescue}: {RESCUE[rescue]}', flush=True)
            if state == 'target' and not logged:
                try:
                    health = probe()
                    (evidence/'health.json').write_text(json.dumps(health, indent=2)+'\n')
                    print(f'{now()} ssh: release={health.get("release")} state={health.get("system_state")}', flush=True)
                    logged = True
                    log = (evidence/'kmsg.log').open('ab')
                    stream = subprocess.Popen(
                        [SSH, '-F', '/dev/null', '-o', 'BatchMode=yes', '-o', 'IdentitiesOnly=yes',
                         '-o', 'IdentityAgent=none', '-o', 'StrictHostKeyChecking=yes',
                         '-o', 'UpdateHostKeys=no', '-o', 'ConnectTimeout=3',
                         '-o', 'ServerAliveInterval=2', '-o', 'ServerAliveCountMax=3',
                         '-o', 'HostKeyAlias=169.254.77.2', '-o', 'UserKnownHostsFile='+str(KNOWN_HOSTS),
                         '-i', str(KEY), 'root@10.77.0.2', 'dmesg --follow-new 2>/dev/null || dmesg -w'],
                        stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT)
                    full = ssh('10.77.0.2', 'dmesg', 30)
                    (evidence/'dmesg-at-health.txt').write_bytes(full.stdout)
                except (ValueError, OSError, subprocess.SubprocessError) as error:
                    print(f'{now()} ssh not ready: {error}', flush=True)
            if stream is not None and stream.poll() is not None and state != 'target':
                stream = None
            time.sleep(interval)
    finally:
        transitions.close()
        if stream is not None:
            stream.terminate()
            try:
                stream.wait(timeout=5)
            except subprocess.TimeoutExpired:
                stream.kill()
    return dict(final_state=last, ssh_health=logged, rescue_prompts=sorted(prompted))


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('status')
    probing = sub.add_parser('probe')
    probing.add_argument('--address', choices=sorted(PROFILES), default='10.77.0.2')
    fast = sub.add_parser('to-fastboot')
    fast.add_argument('--wait', type=int, default=120)
    fast.add_argument('--address', choices=sorted(PROFILES), default='10.77.0.2')
    fast.add_argument('--mode', choices=sorted(FASTBOOT_MODES), required=True)
    run = sub.add_parser('boot')
    run.add_argument('--wrapper', required=True)
    run.add_argument('--wrapper-sha256', required=True)
    run.add_argument('--evidence', required=True)
    run.add_argument('--observe-seconds', type=int, default=1200)
    watch = sub.add_parser('observe')
    watch.add_argument('--evidence', required=True)
    watch.add_argument('--seconds', type=int, default=600)
    args = parser.parse_args()
    if args.command == 'status':
        print(json.dumps(dict(usb=usb_state(), t=now())))
    elif args.command == 'probe':
        print(json.dumps(probe(address=args.address), indent=2))
    elif args.command == 'to-fastboot':
        need(usb_state() == 'target', 'phone is not a running target on the approved port')
        use_address(args.address)
        result = ssh(args.address, FASTBOOT_MODES[args.mode], 20)
        # 255 is ssh losing the link as the phone restarts.
        need(result.returncode in (0, 255), 'target refused the reboot request')
        print(f'{now()} {args.mode} requested rc={result.returncode}', flush=True)
        deadline = time.monotonic()+args.wait
        while time.monotonic() < deadline:
            state = usb_state()
            if state == 'fastboot':
                print(json.dumps(dict(usb=state, t=now(), identity=fastboot_identity())))
                return
            time.sleep(1)
        raise ValueError('phone did not reach fastboot within the wait; last state '+usb_state())
    else:
        evidence = Path(args.evidence)
        need(evidence.is_absolute() and not evidence.exists(), 'evidence must be a new absolute directory')
        evidence.mkdir(mode=0o700, parents=True)
        if args.command == 'boot':
            record = boot(Path(args.wrapper), args.wrapper_sha256, evidence)
            print(f'{now()} fastboot accepted the RAM boot', flush=True)
            summary = observe(evidence, args.observe_seconds)
            summary.update(boot=record)
        else:
            summary = observe(evidence, args.seconds)
        (evidence/'summary.json').write_text(json.dumps(summary, indent=2)+'\n')
        print(json.dumps(summary))


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        print('FAIL '+str(error), file=sys.stderr)
        raise SystemExit(1)
