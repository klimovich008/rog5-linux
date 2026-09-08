#!/usr/bin/env python3
"""Passive R01 two-boot capture; no state write, reboot or execution authority."""
import argparse
import errno
import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import signal
import socket
import stat
import subprocess
import time

REPO=Path(__file__).resolve().parents[2]
_spec=importlib.util.spec_from_file_location('isolated_base_capture',Path(__file__).with_name('headless-stage-receiver.py'))
BASE=importlib.util.module_from_spec(_spec);_spec.loader.exec_module(BASE)
STAGES,CLAIMS,NETWORK,ACCEPTANCE=BASE.STAGES,BASE.CLAIMS,BASE.NETWORK,BASE.ACCEPTANCE
ADDRESS,PEER,PORT,INTERFACE=BASE.ADDRESS,BASE.PEER,BASE.PORT,BASE.INTERFACE
USB_READ_OPERATIONS,UsbReadDisappeared=BASE.USB_READ_OPERATIONS,BASE.UsbReadDisappeared
usb_mode,host_ready,process_start=BASE.usb_mode,BASE.host_ready,BASE.process_start
stage_dict,lifetime_ready=BASE.stage_dict,BASE.lifetime_ready

class Receiver(BASE.Receiver):
    def __init__(self,release,emit,*,return_identity,source_boot_id=None,**kwargs):
        if (source_boot_id is not None or type(return_identity) is not dict
                or set(return_identity)!={'bundle','release','manifest_sha256'}
                or any(type(value) is not str for value in return_identity.values())
                or not re.fullmatch('[a-z0-9][a-z0-9._-]{0,127}',return_identity.get('bundle',''))
                or not re.fullmatch('[A-Za-z0-9_.+-]{1,96}',return_identity.get('release',''))
                or return_identity['release']==release
                or not re.fullmatch('[0-9a-f]{64}',return_identity.get('manifest_sha256',''))
                or return_identity['manifest_sha256']=='0'*64):
            raise ValueError('invalid explicit isolated-recovery return')
        super().__init__(release,emit,**kwargs)
        self.return_identity=dict(return_identity)
        self.initial_boot=None
        self.return_pending=False
        self.return_seen=False

    def return_read_allowed(self):
        # Raw capture only. Authenticated failure, timer and return proof are
        # mandatory in R01; a disconnect alone never qualifies recovery.
        return bool(not self.return_seen and not self.failed and self.initial_boot
                    and self.last and self.last.stage=='switch-root' and self.last.state=='PASS')

    def transport(self,mode,interface):
        # Classify each transport transition once. A failed phone may remain
        # in fastboot for the full capture; polling must not flood its evidence.
        if (mode,interface)==(self.mode,self.interface):
            return super().transport(mode,interface)
        if mode=='absent':
            if self.return_seen:
                self.failed=True
                self.emit(dict(event='unexpected-post-return-disconnect',boot_id=self.last.boot_id if self.last else None))
            elif self.return_read_allowed() and not self.return_pending:
                self.return_pending=True
                self.emit(dict(event='recovery-disconnected',source_boot_id=self.initial_boot,
                               last_stage=stage_dict(self.last),authenticated=False))
            elif self.target_seen and not self.return_pending:
                self.failed=True
                self.emit(dict(event='premature-target-disconnect',last_stage=stage_dict(self.last)))
        elif mode in {'fastboot','recovery'} and self.target_seen and not self.return_pending:
            self.failed=True
            self.emit(dict(event='missing-recovery-disconnect',mode=mode))
        super().transport(mode,interface)

    def record(self,payload,peer):
        if peer!=self.peer or self.mode!='target':
            return super().record(payload,peer)
        if self.return_pending and not self.return_seen:
            try:
                release=self.return_identity['release']
                if payload.startswith(b'format=rog5-startup-observation-v1\n'):
                    boot=BASE.parse_startup_observation(payload,release)['boot_id']
                else:boot=STAGES.parse_stage_record(payload,expected_release=release).boot_id
                if boot==self.initial_boot:raise ValueError('isolated target boot returned as rescue')
                self.last=None;self.startup=None;self.release=release
                self.return_seen=True;self.return_pending=False
                self.emit(dict(event='recovery-boot-observed',source_boot_id=self.initial_boot,
                               boot_id=boot,return_identity=self.return_identity,authenticated=False))
            except (STAGES.PersistentCycleError,ValueError) as error:
                self.failed=True
                self.emit(dict(event='invalid-stage',reason=str(error),raw_hex=payload.hex()))
                return
        super().record(payload,peer)
        if self.initial_boot is None:
            self.initial_boot=self.last.boot_id if self.last else (self.startup or {}).get('boot_id')



def update_transport(receiver, serial, ensure_route, *, deadline=None):
    """One discovery step; the caller owns the original bounded lifetime."""
    phase = 'usb-discovery'
    try:
        mode, interface = usb_mode(serial)
        if receiver.is_source(mode):
            mode, interface = 'source', None
        phase = 'network-setup'
        if mode == 'target' and not ensure_route():
            mode, interface = 'enumerating', None
        phase = 'listener-bind'
        receiver.transport(mode, interface)
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
        def removal_read(exc):
            return (isinstance(exc, UsbReadDisappeared)
                    and exc.errno in (errno.ENOENT, errno.ENODEV)
                    and exc.operation in USB_READ_OPERATIONS)
        eligible = (phase == 'usb-discovery' and removal_read(error)
                    and (not receiver.target_seen or receiver.return_read_allowed())
                    and receiver.mode != 'mismatch')
        started = time.monotonic()
        limit = min(started + .15, deadline if deadline is not None else started + .15)
        rechecks = 0
        followup_error = None
        for attempt in range(4):
            if attempt:
                remaining = limit - time.monotonic()
                if not eligible or mode != 'enumerating' or remaining <= 0:
                    break
                if followup_error is not None and not removal_read(followup_error):
                    break
                time.sleep(min(.05, remaining))
                if time.monotonic() >= limit:
                    break
                rechecks += 1
            followup_error = None
            try:
                mode, interface = usb_mode(serial)
            except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as followup:
                followup_error = followup
                mode, interface = 'enumerating', None
        # Recovery is expected to disconnect during kexec. Tolerate only a
        # positively identified sysfs-read removal followed by actual absence,
        # before target observation, or during an explicitly configured R01
        # return. The latter has its own event; it is not ordinary-boot evidence.
        # Never clear an earlier failure or infer
        # this classification from the historical untagged ENODEV message.
        # Sysfs descriptors may disappear before their parent is removed.
        # Resolve only this read-only pre-target race, never retry networking,
        # extend the capture deadline, or accept an unresolved read as absence.
        pending = (eligible and mode == 'absent'
                   and (deadline is None or time.monotonic() < deadline))
        receiver.failed |= not pending
        receiver.emit(dict(event=('recovery-discovery-interrupted' if receiver.target_seen else 'usb-discovery-interrupted')
                           if pending else 'transport-check-failed',
                           phase=phase, errno=getattr(error, 'errno', None),
                           observed_mode=mode, target_seen=receiver.target_seen,
                           removal_rechecks=rechecks, removal_seconds=time.monotonic()-started,
                           followup_errno=getattr(followup_error, 'errno', None),
                           operation=getattr(error, 'operation', None), reason=str(error)[:160],
                           last_stage=stage_dict(receiver.last), last_startup=receiver.startup))
        if mode == 'target':
            # Identity alone cannot substitute for the failed network check.
            mode, interface = 'enumerating', None
        receiver.transport(mode, interface)
    return receiver.mode != 'mismatch'

def return_manifest(path, canonical):
    """Explicit R01 mode binds a return manifest already pinned in admission."""
    if (canonical.get('qualification')!='isolated-failure-r01'
            or canonical.get('execution')!='fastboot-boot-ram-bundle'):
        raise ValueError('return capture requires the isolated R01 admission')
    descriptor=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK|os.O_CLOEXEC)
    try:
        before=os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode) or not 0<before.st_size<=4096:
            raise ValueError('return manifest bound/type')
        raw=os.read(descriptor,4097)
        if (len(raw)!=before.st_size or os.read(descriptor,1)
                or any(getattr(os.fstat(descriptor),key)!=getattr(before,key) for key in
                       ('st_dev','st_ino','st_size','st_mode','st_uid','st_gid','st_nlink','st_mtime_ns','st_ctime_ns'))):
            raise ValueError('return manifest changed')
    finally:os.close(descriptor)
    digest=hashlib.sha256(raw).hexdigest()
    if digest!=canonical.get('fallback_manifest_sha256'):
        raise ValueError('return manifest differs from canonical fallback')
    fields={}
    for line in raw.decode('ascii').splitlines():
        key,value=line.split('=',1)
        if key in fields:raise ValueError('duplicate return manifest field')
        fields[key]=value
    if (fields.get('bundle')!=canonical.get('fallback_bundle')
            or not re.fullmatch('[a-z0-9][a-z0-9._-]{0,127}',fields.get('bundle',''))
            or not re.fullmatch('[A-Za-z0-9_.+-]{1,96}',fields.get('target_release',''))):
        raise ValueError('invalid canonical return identity')
    return dict(bundle=fields['bundle'],release=fields['target_release'],manifest_sha256=digest)

def check_capture_mode(receipt, source_boot_id, return_identity=None):
    if (source_boot_id is not None or return_identity is None or
            receipt.get('source_boot_id') != source_boot_id or
            receipt.get('return_identity') != return_identity or
            (source_boot_id is not None and return_identity is not None) or
            (source_boot_id is not None and not STAGES.BOOT_ID.fullmatch(source_boot_id))):
        raise ValueError('capture mode/source boot mismatch')

def check_receiver(output, profile, *, source_boot_id=None, return_identity=None):
    if return_identity is None:raise ValueError('explicit return capture identity required')
    receipt = json.loads((output/'receipt.json').read_text())
    check_capture_mode(receipt, source_boot_id, return_identity)
    canonical = dict(line.split('=',1) for line in CLAIMS.expected_record(profile).decode().splitlines())
    if (receipt['canonical_record'] != canonical or receipt['profile'] != profile
            or receipt['source'] != ACCEPTANCE.source_identity()
            or receipt['receiver_sha256'] != hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
            or receipt.get('framework_sha256') != hashlib.sha256(Path(BASE.__file__).read_bytes()).hexdigest()
            or receipt['host_boot_id'] != Path('/proc/sys/kernel/random/boot_id').read_text().strip()
            or receipt['process_start'] != process_start(receipt['pid'])):
        raise ValueError('stale or changed receiver identity')
    if canonical.get('qualification')!='isolated-failure-r01' or canonical.get('execution')!='fastboot-boot-ram-bundle':
        raise ValueError('not an isolated R01 capture')
    if (return_identity.get('bundle')!=canonical.get('fallback_bundle')
            or return_identity.get('manifest_sha256')!=canonical.get('fallback_manifest_sha256')):
        raise ValueError('return identity differs from canonical fallback')
    timing=json.loads((REPO/'configs/release-acceptance.json').read_text())['defaults']['rescue_capture']
    required=timing['target_rollback_seconds']+timing['recovery_seconds']+timing['cleanup_seconds']
    if receipt.get('timing')!=timing or receipt.get('required_seconds')!=required:
        raise ValueError('receiver timing differs from capture lattice')
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
            or live.get('source_boot_id') != source_boot_id
            or live.get('return_identity') != return_identity
            or not lifetime_ready(receipt['deadline_monotonic'], time.monotonic(), receipt['required_seconds'])):
        raise ValueError('receiver not ready or remaining lifetime insufficient')
    return dict(status='PASS', test='H01-receiver', profile=profile,
                receipt_sha256=hashlib.sha256((output/'receipt.json').read_bytes()).hexdigest(),
                remaining_seconds=live['remaining_seconds'], authority='none')

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile', required=True)
    parser.add_argument('--manifest', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--return-manifest',type=Path,required=True,help='explicit isolated R01 capture; return bytes must match canonical fallback')
    args = parser.parse_args()
    canonical=dict(line.split('=',1) for line in CLAIMS.expected_record(args.profile).decode().splitlines())
    returning=return_manifest(args.return_manifest,canonical)
    if args.check:
        print(json.dumps(check_receiver(args.output, args.profile, return_identity=returning)))
        return 0
    if args.manifest is None or os.geteuid() != 0:
        raise ValueError('receiver needs an exact manifest and scoped host-network privileges')
    record = canonical
    raw = args.manifest.read_bytes()
    if hashlib.sha256(raw).hexdigest() != record['manifest_sha256']:
        raise ValueError('manifest differs from canonical execution record')
    fields = dict(line.split('=', 1) for line in raw.decode('ascii').splitlines())
    release = fields['target_release']
    if not re.fullmatch(r'[A-Za-z0-9_.+-]{1,96}', release) or release==returning['release']:
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
        with NETWORK.prepared(lifetime, emit, lambda: usb_mode(record['serial'])[0]=='target') as network, Receiver(
                release, emit, return_identity=returning) as receiver:
            deadline, ensure_route = network
            host_ready()
            receiver.probe = ('PROBE '+os.urandom(24).hex()+'\n').encode()
            def readiness():
                try:
                    host_ready()
                    mode_ready = receiver.mode == 'fastboot' and not receiver.target_seen
                    valid = not stopping and not receiver.failed and mode_ready
                except (ValueError, OSError, subprocess.SubprocessError):
                    valid = False
                return dict(ready=valid and lifetime_ready(deadline, time.monotonic(), required),
                            remaining_seconds=deadline-time.monotonic(), required_seconds=required,
                            candidate=record['candidate'], pid=os.getpid(), source_boot_id=None,return_identity=returning)
            receiver.probe_response = readiness
            receipt = dict(format='rog5-headless-capture-v1', profile=args.profile, canonical_record=record,
                           source=ACCEPTANCE.source_identity(),
                           receiver_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                           framework_sha256=hashlib.sha256(Path(BASE.__file__).read_bytes()).hexdigest(),
                           pid=os.getpid(), process_start=process_start(os.getpid()), deadline_monotonic=deadline, required_seconds=required,
                           host_boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
                           probe=receiver.probe.decode(), started_monotonic=started, timing=timing)
            receipt['return_identity']=returning
            (args.output/'receipt.json').write_text(json.dumps(receipt, indent=2)+'\n')
            emit(dict(event='listener-started', address=ADDRESS, port=PORT, authority='none'))
            while not stopping and time.monotonic() < deadline:
                if not update_transport(receiver, record['serial'], ensure_route, deadline=deadline):
                    stopping = True
                receiver.poll()
            result = dict(status='FAIL' if receiver.failed or log_full else 'NOT RUN',
                          reason='capture is evidence, not authenticated device qualification',
                          last_stage=stage_dict(receiver.last), last_startup=receiver.startup,
                          duration_seconds=time.monotonic()-started)
            result.update(return_identity=returning,initial_boot=receiver.initial_boot,return_seen=receiver.return_seen)
            (args.output/'result.json').write_text(json.dumps(result, indent=2)+'\n')
            emit(dict(event='capture-ended', **result))
            return 1 if receiver.failed or log_full else 0

if __name__=='__main__':raise SystemExit(main())
