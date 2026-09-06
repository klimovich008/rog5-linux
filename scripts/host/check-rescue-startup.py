#!/usr/bin/env python3
"""Replay one existing supervised startup; optionally qualify its same live boot.

Default mode is offline timeline replay. --qualify-current verifies the exact
archive/boot image and authenticates the original live boot, including watchdog,
radio isolation and power safety. No boot, write, admission or H03 qualification.
"""
import argparse
import gzip
import hashlib
import importlib.util
import json
import math
import io
import os
from pathlib import Path
import re
import shlex
import stat
import subprocess
import sys
import time

spec = importlib.util.spec_from_file_location('startup_deployed', Path(__file__).with_name('check-deployed-server.py'))
D = importlib.util.module_from_spec(spec)
spec.loader.exec_module(D)
LIMIT = 1024 * 1024
PREPARED = ('host-profile-prepared', 'host-address-prepared', 'host-firewall-prepared', 'listener-started')


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_bytes(path, limit=LIMIT):
    """Bounded descriptor-relative no-follow read, including parent components."""
    require(path.is_absolute() and '..' not in path.parts, 'absolute evidence path required')
    directory = os.open('/', os.O_RDONLY | os.O_DIRECTORY)
    try:
        for part in path.parts[1:-1]:
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=directory)
            os.close(directory); directory = child
        fd = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
        with os.fdopen(fd, 'rb') as stream:
            before = os.fstat(stream.fileno())
            require(stat.S_ISREG(before.st_mode) and before.st_nlink == 1
                    and before.st_uid == os.geteuid() and not before.st_mode & 0o022
                    and before.st_size <= limit, 'unsafe or oversized evidence file')
            raw = stream.read(limit + 1)
            after = os.fstat(stream.fileno())
            current = os.stat(path.name, dir_fd=directory, follow_symlinks=False)
            signature = lambda s: (s.st_dev, s.st_ino, s.st_size, s.st_mode, s.st_nlink,
                                    s.st_uid, s.st_gid, s.st_mtime_ns, s.st_ctime_ns)
            require(len(raw) <= limit and signature(before) == signature(after) == signature(current),
                    'evidence changed during read')
            return raw
    finally:
        os.close(directory)


def unique(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, 'duplicate JSON field: '+key)
        result[key] = value
    return result


def decode(raw):
    return json.loads(raw, object_pairs_hook=unique)


def read_json(path):
    return decode(read_bytes(path))


def number(value):
    require(type(value) in (int, float) and math.isfinite(value) and value >= 0,
            'invalid nonnegative timing value')
    return value


def validate(record, identity, execution, receipt, receipt_hash, events, attempts, smoke, readiness, deadline):
    require(receipt['format'] == 'rog5-headless-capture-v1'
            and receipt['profile'] == record['candidate'], 'wrong capture profile')
    for value in (execution, receipt, readiness):
        require(value['canonical_record'] == record, 'canonical candidate/claim mismatch')
    require(execution['preflight'] == 'PASS' and execution['flash'] is False, 'unproven preflight or flash')
    source = receipt['source']
    require(source['clean'] is True and re.fullmatch(r'[0-9a-f]{40}', source['revision'])
            and re.fullmatch(r'[0-9a-f]{64}', source['worktree_digest'])
            and source == readiness['source'] and execution['source_revision'] == source['revision'],
            'incoherent historical source')
    require(receipt['receiver_sha256'] == digest(D.CAPTURE.__file__)
            and readiness['runner_sha256'] == digest(D.__file__), 'changed evidence producer; review before reuse')
    capture = execution['capture']
    require(capture['status'] == 'PASS' and capture['test'] == 'H01-receiver'
            and capture['profile'] == record['candidate'] and capture['receipt_sha256'] == receipt_hash,
            'missing exact preboot capture proof')
    required = number(receipt['required_seconds'])
    remaining = number(capture['remaining_seconds'])
    require(required > 0 and remaining >= required
            and number(receipt['deadline_monotonic']) - number(receipt['started_monotonic']) >= remaining,
            'insufficient original receiver lifetime')
    commit_time = number(execution['unix'])
    prepared = [e for e in events if e['event'] in PREPARED]
    require(tuple(e['event'] for e in prepared) == PREPARED
            and all(number(e['unix']) < commit_time for e in prepared)
            and all(a['monotonic'] <= b['monotonic'] for a,b in zip(prepared, prepared[1:])),
            'incomplete or late preboot receiver preparation')
    require(not any(e['event'] == 'transport-check-failed' for e in events), 'capture transport integrity failed')
    require(type(smoke['execution_return']) is int and smoke['execution_return'] == 0
            and smoke['status'] == 'PASS', 'failed or ambiguous execution')
    require(bool(attempts) and all(type(a['code']) is int for a in attempts)
            and [i for i,a in enumerate(attempts) if a['code'] == 0] == [len(attempts)-1],
            'missing or multiple successful startup attempts')
    elapsed = [number(a['elapsed']) for a in attempts]
    wall = [number(a['unix']) for a in attempts]
    require(all(a < b for a,b in zip(elapsed, elapsed[1:]))
            and all(a < b for a,b in zip(wall, wall[1:])), 'nonmonotonic startup observations')
    require(0 < elapsed[-1] <= number(smoke['elapsed_seconds']) <= deadline, 'original startup deadline exceeded')
    start = wall[-1] - elapsed[-1]
    require(start <= commit_time < wall[-1] and prepared[-1]['unix'] <= start
            and all(abs((w-e)-start) <= 1 for w,e in zip(wall, elapsed)),
            'startup clock or execution ordering mismatch')
    require(readiness['status'] == 'PASS' and readiness['identity'] == identity, 'readiness identity mismatch')
    validation = D.validate_readiness(readiness['actual'], identity, record['execution'])
    require(validation['marker_boot_bound'], 'legacy unbound readiness cannot qualify current startup')
    stages = [e for e in events if e['event'] == 'stage']
    require(stages and all(e['stage']['boot_id'] == identity['boot_id'] for e in stages)
            and any(e['stage']['stage'] == 'switch-root' and e['stage']['state'] == 'PASS'
                    and commit_time < number(e['unix']) <= wall[-1] for e in stages),
            'missing current-boot handover before authenticated SSH')
    return dict(status='PASS', startup_seconds=elapsed[-1], historical_source=source,
                evidence_reused=True, h02_qualified=False, release_qualified=False,
                scope='H02 preboot capture and original authenticated startup timeline only',
                remaining=['exact deployed watchdog/archive agreement', 'intentional Wi-Fi isolation',
                           'safe power evidence', 'complete H02 dispatcher integration'])


CURRENT_KEYS = ('boot_before', 'boot_after', 'kernel', 'cmdline', 'wifi', 'files',
                'health', 'temperature', 'voltage', 'online', 'status', 'current',
                'capacity', 'uptime', 'watchdog')
RUNTIME_FILES = {
    'usr/local/sbin/rog5-persistent-keyring': '/run/rog5-persistent-keyring',
    'usr/local/share/rog5/rog5-package-keyring.service': '/run/systemd/system/rog5-package-keyring.service',
    'usr/local/sbin/rog5-p2-attest': '/run/rog5-p2-attest',
    'usr/local/sbin/rog5-persistent-ssh-identity': '/run/rog5-persistent-ssh-identity',
    'shutdown': '/run/initramfs/shutdown',
    'bin/busybox': '/run/initramfs/bin/busybox',
    'lib/ld-musl-aarch64.so.1': '/run/initramfs/lib/ld-musl-aarch64.so.1',
    'usr/libexec/rog5-reboot-bootloader': '/run/initramfs/usr/libexec/rog5-reboot-bootloader',
}


def sealed_runtime(archive, manifest):
    composition = D.CAPTURE.load('startup_composition', 'scripts/host/check-rescue-root-composition.py')
    blob = read_bytes(archive, 256*LIMIT)
    require(len(blob) == int(manifest['initramfs_size'])
            and hashlib.sha256(blob).hexdigest() == manifest['initramfs_sha256'], 'signed target archive mismatch')
    with gzip.GzipFile(fileobj=io.BytesIO(blob)) as stream:
        expanded = stream.read(512*LIMIT+1)
    require(len(expanded) <= 512*LIMIT, 'expanded archive exceeds bound')
    members = composition.SEALED.ARCHIVE.entries(expanded)
    parameters = composition.archive_parameters(members)  # Exact paired watchdog/producer; no radio payload.
    require(parameters['KERNEL_RELEASE'] == manifest['target_release'], 'archive kernel release mismatch')
    expected = {}
    for name, path in RUNTIME_FILES.items():
        fields, data = members[name]
        require(stat.S_ISREG(fields[1]) and fields[2:5] == [0,0,1], 'invalid sealed runtime metadata')
        expected[path] = dict(size=len(data), mode=format(stat.S_IMODE(fields[1]), 'o'),
                              sha256=hashlib.sha256(data).hexdigest())
    return expected, blob


def current_script(identity, expected):
    script = 'set -eu\nexport LC_ALL=C\nexpected_boot='+shlex.quote(identity['boot_id'])+'\n'
    script += '''before=$(cat /proc/sys/kernel/random/boot_id)
test "$before" = "$expected_boot"
kernel=$(uname -r)
cmdline=$(cat /proc/cmdline)
test -d /run; test ! -L /run
test -d /run/initramfs; test ! -L /run/initramfs
test "$(findmnt -n -o FSTYPE --target /run/initramfs)" = tmpfs
'''
    script += 'test "$kernel" = '+shlex.quote(identity['release'])+'\n'
    for path, entry in expected.items():
        quoted = shlex.quote(path)
        script += f'''test -f {quoted}; test ! -L {quoted}
stamp=$(stat -c '%d:%i:%s:%y:%z:%a:%u:%g:%h:%F' {quoted})
test "$(stat -c '%u:%g:%a:%s:%h' {quoted})" = 0:0:{entry['mode']}:{entry['size']}:1
test "$(sha256sum {quoted} | cut -d ' ' -f 1)" = {entry['sha256']}
test "$stamp" = "$(stat -c '%d:%i:%s:%y:%z:%a:%u:%g:%h:%F' {quoted})"
'''
    script += '''for phy in /sys/class/ieee80211/*; do
 test ! -e "$phy"; test ! -L "$phy"
done
test ! -d /sys/module/ath11k
health=$(cat /sys/class/power_supply/qcom-battmgr-bat/health)
temperature=$(cat /sys/class/power_supply/qcom-battmgr-bat/temp)
voltage=$(cat /sys/class/power_supply/qcom-battmgr-bat/voltage_now)
online=$(cat /sys/class/power_supply/qcom-battmgr-usb/online)
status=$(cat /sys/class/power_supply/qcom-battmgr-bat/status)
current=$(cat /sys/class/power_supply/qcom-battmgr-bat/current_now)
capacity=$(cat /sys/class/power_supply/qcom-battmgr-bat/capacity)
uptime=$(cut -d ' ' -f 1 /proc/uptime)
watchdog=$(dmesg | grep -E 'rog5-persistent-root: (emergency-reset watchdog armed|watchdog acknowledged)' || true)
after=$(cat /proc/sys/kernel/random/boot_id)
test "$after" = "$expected_boot"
printf '%s\\0' "$before" "$after" "$kernel" "$cmdline" inactive PASS "$health" "$temperature" "$voltage" "$online" "$status" "$current" "$capacity" "$uptime" "$watchdog"
'''
    return script


def collect_current(identity, key, known_hosts, script):
    D.host_gate(identity)
    D.credential(key, True); D.credential(known_hosts, False)
    completed = subprocess.run([*D.ssh_command(key, known_hosts), 'sh -s'],
                               input=script.encode(), capture_output=True, timeout=15)
    require(completed.returncode == 0, 'authenticated same-boot runtime check failed')
    D.host_gate(identity)
    require(len(completed.stdout) <= 32768, 'current runtime output exceeds bound')
    fields = completed.stdout.decode('ascii').split('\0')
    require(len(fields) == len(CURRENT_KEYS)+1 and fields[-1] == '', 'invalid current runtime framing')
    return dict(zip(CURRENT_KEYS, fields[:-1]))


def validate_current(observed, identity, rollback):
    require(observed['boot_before'] == observed['boot_after'] == identity['boot_id']
            and observed['kernel'] == identity['release'], 'current boot/release mismatch')
    tokens = observed['cmdline'].split()
    for key, value in [('rog5.bundle', identity['bundle']), ('rog5.recovery_timeout', str(rollback))]:
        require([t for t in tokens if t.startswith(key+'=')] == [key+'='+value], 'ambiguous current cmdline')
    require(observed['wifi'] == 'inactive' and observed['files'] == 'PASS', 'radio isolation or runtime bytes failed')
    require(observed['health'] == 'Good' and observed['online'] == '1', 'unsafe battery health/input')
    require(0 <= int(observed['temperature']) < 400 and 8400000 <= int(observed['voltage']) <= 9000000
            and 0 <= int(observed['capacity']) <= 100, 'unsafe battery temperature/voltage/capacity')
    int(observed['current'])  # Retain polarity; H02 safety is not H03 regulation.
    armed = re.findall(r'^\[\s*([0-9.]+)\] rog5-persistent-root: emergency-reset watchdog armed for ([0-9]+) seconds$', observed['watchdog'], re.M)
    ack = re.findall(r'^\[\s*([0-9.]+)\] rog5-persistent-root: watchdog acknowledged by current-boot P2 and SSH identity readiness$', observed['watchdog'], re.M)
    require(len(observed['watchdog'].splitlines()) == 2 and len(armed) == len(ack) == 1
            and int(armed[0][1]) == rollback, 'missing/duplicate/wrong deployed watchdog')
    delta = number(float(ack[0])) - number(float(armed[0][0]))
    require(rollback <= delta <= rollback+5 and number(float(observed['uptime'])) >= float(ack[0]),
            'watchdog acknowledgement timing differs from sealed timeout')
    return dict(watchdog='acknowledged', watchdog_delay_seconds=delta, h03_qualified=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cycle', type=Path, required=True)
    parser.add_argument('--execution-record', type=Path, required=True)
    parser.add_argument('--profile', required=True)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--qualify-current', action='store_true', help='read-only pinned SSH qualification of the same boot; never boot')
    parser.add_argument('--archive', type=Path)
    parser.add_argument('--boot-image', type=Path)
    parser.add_argument('--identity-file', type=Path)
    parser.add_argument('--known-hosts', type=Path)
    parser.add_argument('--expected-candidate', help='optional release dispatcher candidate binding')
    args = parser.parse_args()
    require(not args.qualify_current or all((args.archive, args.boot_image, args.identity_file, args.known_hosts)),
            'qualification requires exact archive, boot image and SSH credentials')
    require(args.output.is_absolute() and not args.output.resolve().is_relative_to(D.REPO)
            and not args.output.exists(), 'output must be new and private outside Git')
    source = D.CAPTURE.ACCEPTANCE.source_identity()
    started = time.monotonic()
    raw_files = {}

    def read(path, lines=False):
        raw = read_bytes(path); raw_files[path] = raw
        return [decode(line) for line in raw.splitlines()] if lines else decode(raw)

    record = dict(line.split('=', 1) for line in D.CAPTURE.CLAIMS.expected_record(args.profile).decode().splitlines())
    require(args.expected_candidate is None or record['candidate'] == args.expected_candidate, 'release candidate mismatch')
    D.CAPTURE.CLAIMS.verify_entered(args.profile)  # Read only; no new authority.
    boot_image = None
    if args.boot_image:
        boot_image = read_bytes(args.boot_image, 256*LIMIT)
        require(hashlib.sha256(boot_image).hexdigest() == record['boot_image_sha256'], 'canonical boot image mismatch')
    manifest_raw = read_bytes(args.manifest); raw_files[args.manifest] = manifest_raw
    require(hashlib.sha256(manifest_raw).hexdigest() == record['manifest_sha256'], 'canonical manifest mismatch')
    manifest = dict(line.split('=', 1) for line in manifest_raw.decode('ascii').splitlines())
    receipt_path = args.cycle/'capture/receipt.json'
    receipt = read(receipt_path)
    first = read(args.cycle/'first-pinned-ssh.txt')
    ready_path = Path(first['output'])
    require(ready_path.parent == args.cycle and re.fullmatch(r'readiness-[1-9][0-9]*', ready_path.name),
            'readiness path escapes exact cycle')
    ready = read(ready_path/'result.json')
    identity = dict(serial=record['serial'], bundle=record['target_bundle'],
                    release=manifest['target_release'], boot_id=ready['identity']['boot_id'])
    require(first['status'] == 'PASS' and first['seconds'] == ready['seconds'], 'first readiness result mismatch')
    deadline = next(t['deadline_seconds'] for t in D.CAPTURE.ACCEPTANCE.load_contract()['tests'] if t['id'] == 'H02')
    execution = read(args.execution_record)
    result = validate(record, identity, execution, receipt,
                      hashlib.sha256(raw_files[receipt_path]).hexdigest(),
                      read(args.cycle/'capture/events.jsonl', True), read(args.cycle/'ssh-attempts.jsonl', True),
                      read(args.cycle/'smoke-result.json'), ready, deadline)
    if args.qualify_current:
        # These are the pre-execution readings, not a new fastboot invocation.
        for name in ('device', 'last_fastboot'):
            device = execution[name]
            require(device['product'] == record['product'] and device['current-slot'] == record['expected_slot']
                    and device['battery-soc-ok'] == 'yes' and 8400 <= int(device['battery-voltage']) <= 9000,
                    'historical exact slot/product/power gate failed')
        boot_log = read_bytes(args.cycle/'boot.log'); raw_files[args.cycle/'boot.log'] = boot_log
        require(boot_log.count(b'CLAIM_CONSUMED:') == 1 and boot_log.count(b'FASTBOOT_ACCEPTED:') == 1
                and len(re.findall(rb'^Booting\s+OKAY', boot_log, re.M)) == 1
                and b'FAILED' not in boot_log and b'AMBIGUOUS' not in boot_log, 'incomplete or ambiguous boot transcript')
        expected, archive = sealed_runtime(args.archive, manifest)
        current_ready = D.collect_readiness(identity, args.identity_file, args.known_hosts)
        require(D.validate_readiness(current_ready, identity, record['execution'])['marker_boot_bound'],
                'current readiness is not boot bound')
        script = current_script(identity, expected)
        current = collect_current(identity, args.identity_file, args.known_hosts, script)
        current_validation = validate_current(current, identity, int(manifest['rollback_timeout']))
        require(read_bytes(args.archive, 256*LIMIT) == archive and read_bytes(args.boot_image, 256*LIMIT) == boot_image,
                'artifacts changed during same-boot qualification')
        result.update(h02_qualified=True, scope='H02 original startup plus current same-boot rescue qualification',
                      current=current, current_readiness=current_ready, current_validation=current_validation,
                      expected_runtime=expected, probe_sha256=hashlib.sha256(script.encode()).hexdigest(),
                      artifact_hashes=dict(initramfs=manifest['initramfs_sha256'], boot_image=record['boot_image_sha256']),
                      remaining=['H03 sustained charging/regulation', 'remaining mandatory server/recovery rows'])
    require(source == D.CAPTURE.ACCEPTANCE.source_identity(), 'source changed during replay')
    if boot_image is not None:
        require(read_bytes(args.boot_image, 256*LIMIT) == boot_image, 'boot image changed during replay')
    require(all(read_bytes(path) == raw for path,raw in raw_files.items()), 'cycle changed during replay')
    result.update(source=source, identity=identity, canonical_record=record,
                  seconds=time.monotonic()-started, runner_sha256=digest(__file__),
                  evidence={str(p): hashlib.sha256(raw).hexdigest() for p,raw in raw_files.items()})
    args.output.mkdir(mode=0o700)
    (args.output/'result.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(dict(status=result['status'], seconds=result['seconds'], output=str(args.output),
                         h02_qualified=result['h02_qualified'], release_qualified=False)))
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (OSError, KeyError, TypeError, ValueError, subprocess.SubprocessError) as error:
        print('FAIL '+str(error), file=sys.stderr)
        sys.exit(1)
