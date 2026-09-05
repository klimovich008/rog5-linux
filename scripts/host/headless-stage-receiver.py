#!/usr/bin/env python3
"""Passive prestarted headless stage receiver. Never issues or executes a boot."""
import argparse
import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import select
import signal
import socket
import stat
import subprocess
import sys
import time

REPO = Path(__file__).resolve().parents[2]


def load(name, relative):
    spec = importlib.util.spec_from_file_location(name, REPO/relative)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


STAGES = load('headless_stage_parser', 'scripts/host/run-persistent-root-storage-live-cycle.py')
CLAIMS = load('headless_capture_claims', 'scripts/host/consume-exact-boot-claim.py')
NETWORK = load('headless_capture_network', 'scripts/host/rescue-capture-network.py')
ACCEPTANCE = load('headless_capture_acceptance', 'scripts/host/release-acceptance.py')
ADDRESS, PEER, PORT = NETWORK.ADDRESS, '169.254.77.2', 8079
INTERFACE, PROFILE = NETWORK.INTERFACE, NETWORK.PROFILE
USB = Path('/sys/bus/usb/devices/1-1.2')
ANCHOR = '/sys/devices/pci0000:00/0000:00:08.1/0000:04:00.3/usb1/1-1/1-1.2'


def lifetime_ready(deadline, now, required):
    return required > 0 and deadline - now >= required


def stage_dict(stage):
    if stage is None:
        return None
    return {k: getattr(stage, k) for k in ('boot_id', 'sequence', 'stage', 'state', 'detail')}


def update_transport(receiver, serial, ensure_route):
    """One discovery step; the caller owns the original bounded lifetime."""
    try:
        mode, interface = usb_mode(serial)
        if mode == 'target' and not ensure_route():
            mode, interface = 'enumerating', None
        receiver.transport(mode, interface)
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
        # USB can vanish between sysfs discovery and the bounded NM/ip call.
        # Keep the original capture deadline and last evidence, not admission:
        # any failed check permanently invalidates this capture's readiness.
        receiver.failed = True
        receiver.emit(dict(event='transport-check-failed', reason=str(error)[:160],
                           last_stage=stage_dict(receiver.last),
                           last_startup=receiver.startup))
        try:
            mode, interface = usb_mode(serial)
        except (OSError, ValueError, RuntimeError, subprocess.SubprocessError):
            mode, interface = 'enumerating', None
        if mode == 'target':
            # Identity alone cannot substitute for the failed network check.
            mode, interface = 'enumerating', None
        receiver.transport(mode, interface)
    return receiver.mode != 'mismatch'


def parse_startup_observation(payload, release):
    fields = ('format','target_release','boot_id','sequence','unit','observation',
              'active','sub','result','exit','journal','failure_hex')
    if len(payload) > 512 or not payload.endswith(b'\n') or b'\r' in payload or b'\0' in payload:
        raise ValueError('startup observation framing/bound')
    try:
        lines = payload.decode('ascii').splitlines()
    except UnicodeDecodeError as error:
        raise ValueError('startup observation encoding') from error
    if len(lines) != len(fields) or any(not line.startswith(key+'=') for line,key in zip(lines,fields)):
        raise ValueError('startup observation fields')
    record = {key:line.split('=',1)[1] for key,line in zip(fields,lines)}
    if (record['format'] != 'rog5-startup-observation-v1' or record['target_release'] != release
            or not STAGES.BOOT_ID.fullmatch(record['boot_id'])
            or not re.fullmatch(r'[1-9][0-9]{0,2}',record['sequence'])
            or record['unit'] not in {'p2','state','identity','sshd'}
            or record['observation'] not in {'present','absent','error'}
            or record['journal'] not in {'present','absent','error'}
            or any(not re.fullmatch(r'[a-z][a-z-]{0,31}',record[k]) for k in ('active','sub','result'))
            or not re.fullmatch(r'unknown|[0-9]{1,3}',record['exit'])
            or not re.fullmatch(r'none|(?:[0-9a-f]{2}){1,80}',record['failure_hex'])):
        raise ValueError('startup observation content')
    record['sequence'] = int(record['sequence'])
    return record


class Receiver:
    def __init__(self, release, emit, *, host=ADDRESS, port=PORT, peer=PEER, client_seconds=2):
        self.release, self.emit, self.peer = release, emit, peer
        self.client_seconds = client_seconds
        self.listener = socket.socket()
        self.listener.bind((host, port))  # No FREEBIND: the address must exist first.
        self.listener.listen(8)
        self.listener.setblocking(False)
        self.clients = {}
        self.last = None
        self.startup = None
        self.failed = False
        self.mode, self.interface = 'absent', None
        self.probe = None
        self.probe_response = lambda: {}

    def __enter__(self):
        return self

    def __exit__(self, *_):
        for client in list(self.clients):
            client.close()
        self.listener.close()

    def transport(self, mode, interface):
        if (mode, interface) == (self.mode, self.interface):
            return
        # Close accepted sockets from the previous USB identity before rebinding.
        for client in list(self.clients):
            client.close()
        self.clients.clear()
        if self.interface or interface:
            self.listener.setsockopt(socket.SOL_SOCKET, socket.SO_BINDTODEVICE,
                                     (interface or '').encode()+b'\0')
        self.mode, self.interface = mode, interface
        if mode == 'mismatch':
            self.failed = True
        self.emit(dict(event='transport', mode=mode, interface=interface,
                       last_stage=stage_dict(self.last), last_startup=self.startup))

    def record(self, payload, peer):
        if peer != self.peer or self.mode != 'target':
            self.emit(dict(event='rejected-peer-or-transport', peer=peer, mode=self.mode))
            return
        try:
            if payload.startswith(b'format=rog5-startup-observation-v1\n'):
                current = parse_startup_observation(payload, self.release)
                boot = self.last.boot_id if self.last else (self.startup or {}).get('boot_id')
                if boot and current['boot_id'] != boot:
                    raise ValueError('startup observation changed boot')
                if self.startup and current['sequence'] <= self.startup['sequence']:
                    raise ValueError('startup observation sequence regressed/repeated')
                self.startup = current
                self.emit(dict(event='startup-observation', observation=current, authenticated=False))
                return
            current = STAGES.parse_stage_record(payload, expected_release=self.release)
            if self.startup and current.boot_id != self.startup['boot_id']:
                raise ValueError('stage changed observed startup boot')
            if self.last:
                STAGES.require_stage_successor(self.last, current)
            self.last = current
            self.failed |= current.state == 'FAIL'
            self.emit(dict(event='stage', stage=stage_dict(current), authenticated=False))
        except (STAGES.PersistentCycleError, ValueError) as error:
            self.failed = True
            self.emit(dict(event='invalid-stage', reason=str(error), raw_hex=payload.hex()))

    def poll(self, seconds=.1):
        readable, _, _ = select.select([self.listener, *self.clients], [], [], seconds)
        now = time.monotonic()
        if self.listener in readable:
            client, peer = self.listener.accept()
            client.setblocking(False)
            bound = client.getsockopt(socket.SOL_SOCKET, socket.SO_BINDTODEVICE, 64).rstrip(b'\0')
            if self.interface and bound != self.interface.encode():
                client.close()
                self.emit(dict(event='rejected-unbound-client'))
            elif len(self.clients) == 4:
                client.close()
                self.failed = True
                self.emit(dict(event='client-capacity-exceeded'))
            else:
                self.clients[client] = [peer[0], bytearray(), now+self.client_seconds]
            readable.remove(self.listener)
        for client, (peer, payload, deadline) in list(self.clients.items()):
            done = now >= deadline
            if client in readable:
                try:
                    block = client.recv(514-len(payload))
                except (ConnectionError, OSError):
                    block = b''
                payload.extend(block)
                done |= not block or len(payload) > 512
            if done:
                if self.probe and peer == '127.0.0.1' and bytes(payload) == self.probe:
                    reply = json.dumps(self.probe_response()).encode()+b'\n'
                    try:
                        client.settimeout(.25); client.sendall(reply)
                    except OSError:
                        pass
                else:
                    self.record(bytes(payload), peer)
                client.close()
                del self.clients[client]


def run(*args):
    return subprocess.check_output(args, text=True, stderr=subprocess.PIPE, timeout=3).strip()


def host_ready():
    addresses = json.loads(run('ip', '-j', 'address', 'show', 'lo'))
    if not any(a.get('local') == ADDRESS and a.get('prefixlen') == 32
               for interface in addresses for a in interface.get('addr_info', [])):
        raise ValueError('preboot loopback diagnostic address absent')
    fields = run('nmcli', '-g', 'connection.interface-name,connection.autoconnect,ipv4.method,ipv4.addresses,connection.zone',
                 'connection', 'show', PROFILE).splitlines()
    if len(fields) != 5 or fields[:3] != [INTERFACE, 'yes', 'shared'] or fields[4] != 'nm-shared':
        raise ValueError('prepared exact USB profile differs')
    addresses = set(fields[3].replace(' ', '').split(','))
    if addresses != {'10.77.0.1/30'}:
        raise ValueError('prepared USB addresses differ')
    if NETWORK.command(['firewall-cmd','--zone=nm-shared','--query-rich-rule='+NETWORK.RULE], acceptable=(0,1))[0] != 0:
        raise ValueError('prepared diagnostic firewall rule absent')


def process_start(pid):
    return Path(f'/proc/{pid}/stat').read_text().rpartition(') ')[2].split()[19]


def check_receiver(output, profile):
    receipt = json.loads((output/'receipt.json').read_text())
    canonical = dict(line.split('=',1) for line in CLAIMS.expected_record(profile).decode().splitlines())
    if (receipt['canonical_record'] != canonical or receipt['profile'] != profile
            or receipt['source'] != ACCEPTANCE.source_identity()
            or receipt['receiver_sha256'] != hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
            or receipt['host_boot_id'] != Path('/proc/sys/kernel/random/boot_id').read_text().strip()
            or receipt['process_start'] != process_start(receipt['pid'])):
        raise ValueError('stale or changed receiver identity')
    host_ready()
    with socket.socket() as client:
        client.settimeout(3)
        client.bind(('127.0.0.1',0))
        client.connect((ADDRESS,PORT))
        client.sendall(receipt['probe'].encode()); client.shutdown(socket.SHUT_WR)
        response = bytearray()
        while len(response) < 1025:
            block = client.recv(1025-len(response))
            if not block: break
            response.extend(block)
    if len(response)>1024:
        raise ValueError('oversize receiver response')
    live = json.loads(response)
    if (live.get('ready') is not True or live.get('candidate') != canonical['candidate']
            or live.get('pid') != receipt['pid']
            or live.get('required_seconds') != receipt['required_seconds']
            or not lifetime_ready(receipt['deadline_monotonic'], time.monotonic(), receipt['required_seconds'])):
        raise ValueError('receiver not ready or remaining lifetime insufficient')
    return dict(status='PASS', test='H01-receiver', profile=profile,
                receipt_sha256=hashlib.sha256((output/'receipt.json').read_bytes()).hexdigest(),
                remaining_seconds=live['remaining_seconds'], authority='none')


def usb_mode(serial):
    if not USB.exists():
        return 'absent', None
    if str(USB.resolve(strict=True)) != ANCHOR:
        return 'mismatch', None
    def field(name):
        return (USB/name).read_text().strip()
    identity = field('idVendor'), field('idProduct'), field('product')
    if identity[:2] == ('0b05', '4daf'):
        return ('fastboot' if field('serial') == serial else 'mismatch'), None
    if identity[:2] != ('1d6b', '0104'):
        return 'mismatch', None
    if identity[2] == 'ROG5 recovery':
        return 'recovery', None
    if identity[2] != 'ROG5 persistent root':
        return 'mismatch', None
    net = Path('/sys/class/net')/INTERFACE
    if not net.exists():
        return 'enumerating', None
    if net.joinpath('device').resolve(strict=True).parent != USB.resolve(strict=True):
        return 'mismatch', None
    if net.joinpath('device/driver').resolve(strict=True).name != 'cdc_ncm':
        return 'mismatch', None
    return 'target', INTERFACE


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile', required=True)
    parser.add_argument('--manifest', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    if args.check:
        print(json.dumps(check_receiver(args.output, args.profile)))
        return 0
    if args.manifest is None or os.geteuid() != 0:
        raise ValueError('receiver needs an exact manifest and scoped host-network privileges')
    record = dict(line.split('=', 1) for line in CLAIMS.expected_record(args.profile).decode().splitlines())
    if record.get('execution') not in {'fastboot-boot-fallback-only', 'fastboot-boot-ram-bundle',
                                       'fastboot-boot-selector-trial'}:
        raise ValueError('not a supported headless rescue record')
    raw = args.manifest.read_bytes()
    if hashlib.sha256(raw).hexdigest() != record['manifest_sha256']:
        raise ValueError('manifest differs from canonical execution record')
    fields = dict(line.split('=', 1) for line in raw.decode('ascii').splitlines())
    release = fields['target_release']
    if not re.fullmatch(r'[A-Za-z0-9_.+-]{1,96}', release):
        raise ValueError('invalid target release')
    timing = json.loads((REPO/'configs/release-acceptance.json').read_text())['defaults']['rescue_capture']
    rollback = int(fields['rollback_timeout'])
    if rollback != timing['target_rollback_seconds']:
        raise ValueError('review capture lattice for different target rollback')
    required = timing['recovery_seconds']+rollback+timing['cleanup_seconds']
    lifetime = required+timing['preflight_seconds']
    if usb_mode(record['serial']) != ('fastboot', None):
        raise ValueError('receiver must start at exact fastboot before this attempt')
    if not args.output.is_absolute():
        raise ValueError('use an absolute output path')
    args.output = args.output.resolve()
    if args.output.is_relative_to(REPO):
        raise ValueError('use a fresh private output outside Git')
    args.output.mkdir(mode=0o700)
    started = time.monotonic(); deadline = started+lifetime
    stopping = False
    def stop(*_):
        nonlocal stopping
        stopping = True
    for sig in (signal.SIGTERM, signal.SIGINT):
        signal.signal(sig, stop)
    descriptor = os.open('/run/lock/rog5-headless-stage-receiver.lock',
                         os.O_CREAT|os.O_RDONLY|os.O_CLOEXEC|os.O_NOFOLLOW, 0o600)
    metadata = os.fstat(descriptor)
    if not stat.S_ISREG(metadata.st_mode) or metadata.st_uid != 0 or metadata.st_nlink != 1:
        os.close(descriptor)
        raise ValueError('unsafe capture coordinator lock')
    fcntl.flock(descriptor, fcntl.LOCK_EX|fcntl.LOCK_NB)
    log_full = False
    with os.fdopen(descriptor,'rb') as coordinator_lock, (args.output/'events.jsonl').open('x') as log:
        def emit(event):
            nonlocal stopping, log_full
            event.update(unix=time.time(), monotonic=time.monotonic())
            if log.tell() > 8 * 1024 * 1024:
                stopping = True
                if not log_full:
                    log.write(json.dumps(dict(event='log-bound-exceeded'))+'\n'); log.flush()
                log_full = True
                return
            log.write(json.dumps(event, sort_keys=True)+'\n'); log.flush()
        with NETWORK.prepared(lifetime, emit, lambda: usb_mode(record['serial'])[0]=='target') as network, Receiver(release, emit) as receiver:
            deadline, ensure_route = network
            host_ready()
            receiver.probe = ('PROBE '+os.urandom(24).hex()+'\n').encode()
            def readiness():
                try:
                    host_ready()
                    valid = not stopping and not receiver.failed and receiver.mode == 'fastboot'
                except (ValueError, OSError, subprocess.SubprocessError):
                    valid = False
                return dict(ready=valid and lifetime_ready(deadline, time.monotonic(), required),
                            remaining_seconds=deadline-time.monotonic(), required_seconds=required,
                            candidate=record['candidate'], pid=os.getpid())
            receiver.probe_response = readiness
            receipt = dict(format='rog5-headless-capture-v1', profile=args.profile, canonical_record=record,
                           source=ACCEPTANCE.source_identity(),
                           receiver_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                           pid=os.getpid(), process_start=process_start(os.getpid()), deadline_monotonic=deadline, required_seconds=required,
                           host_boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
                           probe=receiver.probe.decode(), started_monotonic=started, timing=timing)
            (args.output/'receipt.json').write_text(json.dumps(receipt, indent=2)+'\n')
            emit(dict(event='listener-started', address=ADDRESS, port=PORT, authority='none'))
            while not stopping and time.monotonic() < deadline:
                if not update_transport(receiver, record['serial'], ensure_route):
                    stopping = True
                receiver.poll()
            result = dict(status='FAIL' if receiver.failed or log_full else 'NOT RUN',
                          reason='capture is evidence, not authenticated device qualification',
                          last_stage=stage_dict(receiver.last), last_startup=receiver.startup,
                          duration_seconds=time.monotonic()-started)
            (args.output/'result.json').write_text(json.dumps(result, indent=2)+'\n')
            emit(dict(event='capture-ended', **result))
            return 1 if receiver.failed or log_full else 0


if __name__ == '__main__':
    raise SystemExit(main())
