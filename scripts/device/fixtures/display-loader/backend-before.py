"""Fixed, root-owned RAM GPU initialization worker carried over authenticated SSH.

No boot, staging, arbitrary command, unload, retry or physical PASS API. The
host must bind this transport to its qualified owner, health and monitor. All
hardware calls run in a supervised process; zero cleanup has separate ownership
and a separate bounded process after the action process exits or is killed.
"""
import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import selectors
import signal
import socket
import stat
import time

PINS = {'module-io.py': 'c028b4ddd27ed43af9e7eda48c4dd21e5a685a1bda0ee61209eaa12df8f87620', 'load-display.py': '5c298ba05fe7a6f338471cd178a10b49cd9c03914f4a696ad442e7e0dbc1838d', 'endpoint.py': '1c8c173d59a69cc514365844d179813b16d5ae6e7696ecfc9e12ccb999e654ca', 'initialize.py': '373eb2bc855619e19901dd152344407ed3b119c6441e2d57b9716a7423181a38', 'provider-proof.py': 'f73a9c55474fc38645e8b3f83809debc2b5fe1238dd69e291bf3c345e5b294d9', 'provider-backend.py': '38dfdeff0180c9311f721bf76bb15d5b6edbd659dd5ea5466355be64c178faa1', 'provider.py': '3cc937fa611f0a85f75d234f75c8d3123e609735305a601f1077ce7a6a6f8924', 'reprobe.py': 'c2486e2c35ffc180b70d975523431169e338eff3774f14240b2b0353240562a5'}
QUERY_SHA = '9f7bf87f99987cb96030489e1dd995e1eaba13c532731bb24c6229d94387fbb6'
LINE = 32768
LEASE = 3.0
LIFETIME = 60.0
REAP = 2.0
CLEANUP = 4.0
ENTRY = Path('/run/initramfs/rog5-gpu-iommu-display-entered.json')
INITIALIZER_ENTRY = Path('/run/initramfs/rog5-gpu-iommu-initialize-entered.json')
LOCK = Path('/run/initramfs/rog5-gpu-iommu-display.lock')


def need(ok, reason):
    if not ok:
        raise ValueError(reason)


def encoded(value):
    raw = json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()+b'\n'
    need(len(raw) <= LINE, 'record output bound')
    return raw


def decode(raw):
    def pairs(items):
        value = {}
        for key, item in items:
            need(key not in value, 'duplicate JSON key')
            value[key] = item
        return value
    def constant(_):
        raise ValueError('nonfinite JSON')
    need(len(raw) <= LINE, 'record input bound')
    value = json.loads(raw, object_pairs_hook=pairs, parse_constant=constant)
    need(type(value) is dict, 'record object')
    return value


def save(path, value):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600)
    try:
        raw = encoded(value)
        need(os.write(fd, raw) == len(raw), 'short evidence write')
        os.fsync(fd)
    finally:
        os.close(fd)
    directory = os.open(path.parent, os.O_DIRECTORY | os.O_RDONLY | os.O_CLOEXEC)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)


def regular(path, limit=65536, mode=0o600):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC)
    try:
        st = os.fstat(fd)
        need(stat.S_ISREG(st.st_mode) and st.st_uid == st.st_gid == 0
             and stat.S_IMODE(st.st_mode) == mode and st.st_nlink == 1
             and 0 < st.st_size <= limit, 'staged file metadata')
        raw = b''
        while len(raw) <= limit:
            part = os.read(fd, min(65536, limit+1-len(raw)))
            if not part:
                break
            raw += part
        def stamp(info):
            return (info.st_dev,info.st_ino,info.st_mode,info.st_uid,info.st_gid,
                    info.st_nlink,info.st_size,info.st_mtime_ns,info.st_ctime_ns)
        need(len(raw) == st.st_size and stamp(st) == stamp(os.fstat(fd)) == stamp(path.lstat()),
             'staged file changed')
        return raw
    finally:
        os.close(fd)


def context(directory, manifest_sha):
    need(os.geteuid() == 0 and re.fullmatch('[0-9a-f]{64}', manifest_sha), 'root and manifest pin required')
    parent = Path('/run/initramfs')
    run_st = Path('/run').lstat()
    parent_st = parent.lstat()
    need(stat.S_ISDIR(run_st.st_mode) and run_st.st_uid == run_st.st_gid == 0
         and stat.S_IMODE(run_st.st_mode) in (0o755, 0o1777), 'RAM root owner/mode')
    need(parent.resolve() == parent and stat.S_ISDIR(parent_st.st_mode)
         and parent_st.st_uid == parent_st.st_gid == 0
         and stat.S_IMODE(parent_st.st_mode) == 0o755
         and parent_st.st_dev == run_st.st_dev, 'RAM parent owner/mode/device')
    device = str(os.major(run_st.st_dev)) + ':' + str(os.minor(run_st.st_dev))
    mounts = [line.split(' - ', 1)[1].split()[0]
              for line in Path('/proc/self/mountinfo').read_text().splitlines()
              if line.split()[4] == '/run' and line.split()[2] == device]
    need(mounts == ['tmpfs'], 'RAM root filesystem')
    need(directory.parent == parent and directory.resolve() == directory
         and re.fullmatch('rog5-gpu-iommu-display-[0-9a-f]{32}', directory.name), 'fixed RAM namespace')
    st = directory.lstat()
    need(stat.S_ISDIR(st.st_mode) and st.st_uid == st.st_gid == 0
         and stat.S_IMODE(st.st_mode) == 0o700, 'RAM namespace owner/mode')
    raw = regular(directory/'manifest.json', LINE)
    need(hashlib.sha256(raw).hexdigest() == manifest_sha, 'manifest changed')
    value = decode(raw)
    need(set(value) == {'format','phase','boot_id','owner','monitor_receipt_sha256','files'}
         and value['format'] == 'rog5-gpu-iommu-display-backend-v1' and value['phase'] == 'gpu-iommu-display'
         and type(value['owner']) is str and re.fullmatch('[0-9a-f]{32}', value['owner'])
         and directory.name == 'rog5-gpu-iommu-display-'+value['owner']
         and type(value['boot_id']) is str
         and re.fullmatch(r'[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}', value['boot_id'])
         and type(value['monitor_receipt_sha256']) is str
         and re.fullmatch('[0-9a-f]{64}', value['monitor_receipt_sha256']), 'manifest identity')
    files = value['files']
    need(type(files) is dict and set(files) == {*PINS, 'backend.py'}, 'fixed staged source inventory')
    for name, pin in files.items():
        need(type(pin) is str and re.fullmatch('[0-9a-f]{64}', pin)
             and (name == 'backend.py' or pin == PINS[name])
             and hashlib.sha256(regular(directory/name)).hexdigest() == pin, 'staged source changed')
    need(hashlib.sha256(regular(directory/'rog5-gpu-query',542016,0o755)).hexdigest() == QUERY_SHA, 'staged query changed')
    need(not os.path.lexists(ENTRY) and not os.path.lexists(INITIALIZER_ENTRY)
         and not os.path.lexists(directory/'run-entered.json'), 'GPU attempt already entered')
    return value


class Records:
    def __init__(self, fd):
        self.fd, self.buffer = fd, b''
        self.bytes = 0
        os.set_blocking(fd, False)

    def read(self):
        raw = os.read(self.fd, 4096)
        need(raw, 'transport EOF')
        self.bytes += len(raw)
        need(self.bytes <= 262144, 'transport total input bound')
        self.buffer += raw
        rows = []
        while b'\n' in self.buffer:
            line, self.buffer = self.buffer.split(b'\n', 1)
            need(len(rows) < 32, 'transport burst bound')
            rows.append(decode(line))
        need(len(self.buffer) <= LINE, 'unterminated record bound')
        return rows


def send(fd, value, seconds=.25):
    raw = encoded(value)
    deadline = time.monotonic()+seconds
    os.set_blocking(fd, False)
    with selectors.DefaultSelector() as selector:
        selector.register(fd, selectors.EVENT_WRITE)
        while raw:
            left = deadline-time.monotonic()
            need(left > 0 and selector.select(left), 'transport output deadline')
            try:
                count = os.write(fd, raw)
            except BlockingIOError:
                continue
            need(count > 0, 'transport short output')
            raw = raw[count:]


def load_component(directory):
    spec = importlib.util.spec_from_file_location('bounded_module_component', directory/'initialize.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def worker(channel, directory, value, cleanup):
    reader = Records(channel.fileno())
    with selectors.DefaultSelector() as selector:
        selector.register(channel, selectors.EVENT_READ)

        def rpc(kind, payload=None):
            send(channel.fileno(), dict(kind=kind, payload=payload))
            deadline = time.monotonic()+(LEASE if kind == 'enter' else 1.0)
            while time.monotonic() < deadline:
                if selector.select(max(0, deadline-time.monotonic())):
                    rows = reader.read()
                    if rows:
                        need(len(rows) == 1 and set(rows[0]) == {'ok'}, 'worker reply')
                        return rows[0]['ok'] is True
            return False

        module = load_component(directory)
        boot = value['boot_id']
        def ownership():
            return module.identity(boot)['boot_id'] == boot
        if cleanup:
            result = module.DL.E.blank(boot, ownership)
        else:
            ownership()
            need(rpc('authorize'), 'GPU host/logging lease absent')
            need(rpc('enter', intent(value)), 'GPU entry was not acknowledged')
            def record(event, **fields):
                need(rpc('progress', dict(event=event, **fields)), 'GPU progress not recorded')
            result = module.run(boot, value['owner'], lambda: rpc('authorize'), ownership, record)
        send(channel.fileno(), dict(kind='result', payload=result))


def intent(value):
    return dict(identity=dict(boot_id=value['boot_id'], release='7.1.4-g136f75ae869a',
                              bundle='gpu-136f7-a9b1bc89566205b6'),
                sources=PINS, query_sha256=QUERY_SHA, maximum_module_insertions=2,
                maximum_query_opens=1, maximum_query_ioctls=4, submit_calls=0,
                cleanup_brightness=0, retry_allowed=False)


def proof_reader():
    path=Path(__file__).resolve().parent/'provider-proof.py'
    need(path.resolve()==path and path.stat().st_size<16384 and hashlib.sha256(path.read_bytes()).hexdigest()==PINS['provider-proof.py'],'provider proof source changed')
    spec=importlib.util.spec_from_file_location('backend_provider_proof',path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

def validate_component(value, boot, owner):
    need(type(value) is dict and value.get('status') == 'PASS_GPU_INITIALIZATION_ONLY'
         and all(value.get(k) is True for k in ('entered','module_attempted','query_attempted'))
         and value.get('retry_allowed') is False and value.get('hardware_acceleration_verified') is False,
         'GPU component failed')
    need(type(value.get('gpucc_insertions')) is int and value['gpucc_insertions']==0
         and type(value.get('driver_probes')) is int and value['driver_probes']==0
         and type(value.get('maximum_module_insertions')) is int and value['maximum_module_insertions']==2,
         'display/query hardware scope differs')
    proof_reader().validate_observation(value.get('provider'),boot,owner)
    display=value.get('display',{})
    need(display.get('status') == 'PASS_MODULES_AND_BLANK' and display.get('entered') is True
         and display.get('panel_attempted') is True and display.get('cleanup_errors') == [],
         'GPU display prerequisite failed')
    rows=display.get('insertions',[])
    need(type(rows) is list and len(rows) == 2 and all(
        r.get('filename') == name and r.get('status') == 'PASS_INSERTION' and r.get('reaped') is True
        and type(r.get('returncode')) is int and r['returncode'] == 0
        for r,name in zip(rows,('qcom-refgen-regulator.ko','panel-asus-rog5-ams678.ko'))),
        'GPU display insertion proof absent')
    query=value.get('query',{})
    need(query.get('error') is None and query.get('reaped') is True
         and type(query.get('returncode')) is int and query['returncode'] == 0
         and query.get('stderr') == '' and type(query.get('stdout')) is str, 'GPU query closure absent')
    expected=dict(status='PASS',stage='complete',errno=None,open_attempts=1,opened=True,
        ioctl_attempts=4,close_attempted=True,closed=True,close_errno=None,
        values_gpu_chip_gmem=[660,0x06060001,1572864],submit_calls=0,admission_authority=False)
    rows=[decode(line.encode()) for line in query['stdout'].splitlines()]
    need(encoded({'rows':rows}) == encoded({'rows':[dict(event='OPERATIONAL_OPEN_ENTERING',
        admission_authority=False),expected]}) and encoded(value.get('parameters')) == encoded(expected),
        'GPU query proof mismatch')
    return value


def spawn(directory, value, cleanup, close_fds):
    parent, child = socket.socketpair()
    pid = os.fork()
    if pid == 0:
        parent.close()
        try:
            os.setsid()
            for fd in set(close_fds):
                if fd != child.fileno():
                    os.close(fd)
            # No worker/debug output can corrupt the authenticated protocol.
            null = os.open('/dev/null', os.O_RDWR)
            for fd in (0, 1, 2):
                if fd != child.fileno():
                    os.dup2(null, fd)
            os.close(null)
            worker(child, directory, value, cleanup)
        except BaseException as exc:
            try:
                send(child.fileno(), dict(kind='error', payload=dict(
                    type=type(exc).__name__, reason=str(exc)[:1000],
                    component=getattr(exc, 'evidence', None))))
            except BaseException:
                pass
            os._exit(1)
        os._exit(0)
    child.close()
    return pid, parent


def stop(pid, force):
    deadline = time.monotonic()+REAP
    # PID is our unreaped child, so cannot have been reused. Kill the helper's
    # process group too; a kernel task stuck in uninterruptible sleep may remain.
    if force:
        for call in (lambda: os.killpg(pid, signal.SIGKILL), lambda: os.kill(pid, signal.SIGKILL)):
            try:
                call()
            except ProcessLookupError:
                pass
    status = None
    while time.monotonic() < deadline:
        if status is None:
            got, child_status = os.waitpid(pid, os.WNOHANG)
            if got:
                status = child_status
        if status is not None:
            try:
                os.killpg(pid, 0)
            except ProcessLookupError:
                return dict(pid=pid, reaped=True, exitcode=os.waitstatus_to_exitcode(status),
                            group_absent=True, killed=force)
        time.sleep(.01)
    return dict(pid=pid, reaped=status is not None,
                exitcode=os.waitstatus_to_exitcode(status) if status is not None else None,
                group_absent=False, killed=force)


class Supervisor:
    def __init__(self, directory, value, input_fd=0, output_fd=1):
        self.directory, self.value = directory, value
        self.input, self.output = input_fd, output_fd
        self.identity = {key:value[key] for key in ('phase','boot_id','owner','monitor_receipt_sha256')}
        self.start = time.monotonic()
        self.deadline = self.start+LIFETIME
        self.lease = self.start+LEASE
        self.sequence = 0
        self.entered = self.acknowledged = self.started = self.owns_run = False
        self.intent_sha = None
        self.out_count = 0
        self.lock = None

    def emit(self, kind, payload=None):
        self.out_count += 1
        need(self.out_count <= 32, 'supervisor event count')
        send(self.output, dict(self.identity, event=kind, payload=payload))

    def alive(self):
        return time.monotonic() < min(self.lease, self.deadline)

    def command(self, row, channel):
        need(set(row) == {*self.identity,'sequence','command','intent_sha256'}
             and all(row[k] == v for k,v in self.identity.items())
             and type(row['sequence']) is int and row['sequence'] == self.sequence+1
             and self.alive(), 'host command identity/sequence/deadline')
        command = row['command']
        need(command in ('start','lease','enter-ack','stop'), 'fixed host command')
        if command != 'enter-ack':
            need(row['intent_sha256'] is None, 'unexpected intent acknowledgement')
        if command == 'stop':
            raise ValueError('host stop')
        if command == 'start':
            need(not self.started and channel is None, 'start already consumed')
            self.started = True
        elif command == 'enter-ack':
            need(self.entered and not self.acknowledged and channel is not None
                 and row['intent_sha256'] == self.intent_sha, 'entry acknowledgement differs')
            self.acknowledged = True
            send(channel.fileno(), {'ok':True})
        self.sequence = row['sequence']
        self.lease = min(time.monotonic()+LEASE, self.deadline)

    def run(self):
        pid = channel = result = error = blank = cleanup_proc = None
        process = dict(reaped=False)
        cleanup_errors = []
        reader = Records(self.input)
        try:
            self.lock = os.open(LOCK, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC, 0o600)
            st = os.fstat(self.lock)
            need(stat.S_ISREG(st.st_mode) and st.st_uid == st.st_gid == 0
                 and stat.S_IMODE(st.st_mode) == 0o600 and st.st_nlink == 1, 'global module lock metadata')
            fcntl.flock(self.lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            need(not os.path.lexists(ENTRY) and not os.path.lexists(INITIALIZER_ENTRY), 'global GPU attempt already entered')
            save(self.directory/'run-entered.json', dict(self.identity, started_monotonic=self.start))
            self.owns_run = True
            self.emit('transport-ready', dict(lease_seconds=LEASE, maximum_seconds=LIFETIME))
            with selectors.DefaultSelector() as selector:
                selector.register(self.input, selectors.EVENT_READ, 'host')
                child_reader = None
                while result is None:
                    need(self.alive(), 'host lease or worker lifetime expired')
                    for key, _ in selector.select(.05):
                        if key.data == 'host':
                            for row in reader.read():
                                self.command(row, channel)
                            if self.started and pid is None:
                                pid, channel = spawn(self.directory, self.value, False,
                                                     (self.input,self.output,self.lock,selector.fileno()))
                                child_reader = Records(channel.fileno())
                                selector.register(channel, selectors.EVENT_READ, 'worker')
                        else:
                            for row in child_reader.read():
                                need(set(row) == {'kind','payload'}, 'worker event shape')
                                if row['kind'] == 'authorize':
                                    need(row['payload'] is None, 'authorization payload')
                                    send(channel.fileno(), {'ok':self.alive()})
                                elif row['kind'] == 'enter':
                                    need(not self.entered and type(row['payload']) is dict, 'repeated module entry')
                                    self.intent_sha = hashlib.sha256(encoded(row['payload'])).hexdigest()
                                    save(ENTRY, dict(self.identity, intent_sha256=self.intent_sha,
                                                     entered_monotonic=time.monotonic(), intent=row['payload']))
                                    self.entered = True
                                    self.emit('enter-request', dict(intent_sha256=self.intent_sha, intent=row['payload']))
                                elif row['kind'] == 'progress':
                                    need(self.acknowledged and type(row['payload']) is dict
                                         and row['payload'].get('event') in ('provider-verified',
                                         'display-entering','display-result','render-discovered','query-entering',
                                         'query-result','terminal'), 'GPU progress before entry or unknown event')
                                    save(self.directory/('progress-%02d.json' % self.out_count), row['payload'])
                                    self.emit('component-progress', row['payload'])
                                    send(channel.fileno(), {'ok':self.alive()})
                                elif row['kind'] == 'result':
                                    need(self.acknowledged and result is None, 'result before entry acknowledgement')
                                    result = row['payload']
                                elif row['kind'] == 'error':
                                    raise ValueError('worker failed: '+str(row['payload'])[:2000])
                                else:
                                    raise ValueError('unexpected worker event')
            process = stop(pid, False)
            if process['reaped']:
                pid = None
            need(process['reaped'] and process['group_absent'] and process['exitcode'] == 0,
                 'module worker did not close successfully')
            validate_component(result, self.value['boot_id'], self.value['owner'])
        except Exception as exc:
            error = dict(type=type(exc).__name__, reason=str(exc)[:2500])
        finally:
            if pid is not None:
                process = stop(pid, True)
            if channel is not None:
                channel.close()
            if self.entered:
                # Independent of host/lease health. Exact boot identity is checked
                # again by the cleanup worker and every endpoint operation.
                try:
                    blank, cleanup_proc = self.cleanup()
                except Exception as exc:
                    cleanup_proc = getattr(exc, 'process', None)
                    cleanup_errors.append(dict(stage='independent-zero', reason=str(exc)[:1000]))
            if not (process['reaped'] and process.get('group_absent')) and self.started:
                cleanup_errors.append(dict(stage='action-reap', reason='worker remains unreaped'))
            final = dict(self.identity, format='rog5-gpu-iommu-display-backend-result-v1',
                         status='PASS_GPU_INITIALIZATION_AND_CLEANUP' if error is None and not cleanup_errors else 'FAIL',
                         entered=self.entered, acknowledged=self.acknowledged, component=result,
                         action_process=process, cleanup_process=cleanup_proc,
                         remote_reaped=bool(process['reaped'] and process.get('group_absent')
                                            and cleanup_proc and cleanup_proc['reaped'] and cleanup_proc['group_absent']),
                         blank=blank, error=error, cleanup_errors=cleanup_errors,
                         seconds=time.monotonic()-self.start, ended_target_monotonic=time.monotonic(),
                         retry_allowed=False, hardware_acceleration_verified=False, physical_scanout_verified=False, physical_darkness_verified=False)
            try:
                if self.owns_run:
                    save(self.directory/'result.json', final)
                self.emit('terminal', final)
            finally:
                if self.lock is not None:
                    os.close(self.lock)
        return final

    def cleanup(self):
        pid, channel = spawn(self.directory, self.value, True, (self.input,self.output,self.lock))
        reader = Records(channel.fileno())
        result = None
        process = None
        error = None
        try:
            deadline = time.monotonic()+CLEANUP
            with selectors.DefaultSelector() as selector:
                selector.register(channel, selectors.EVENT_READ)
                while result is None:
                    need(time.monotonic() < deadline, 'zero cleanup deadline')
                    if selector.select(max(0, deadline-time.monotonic())):
                        for row in reader.read():
                            need(set(row) == {'kind','payload'} and row['kind'] == 'result'
                                 and result is None, 'zero cleanup worker failure')
                            result = row['payload']
            process = stop(pid, False)
            if process['reaped']:
                pid = None
            need(process['reaped'] and process['group_absent'] and process['exitcode'] == 0, 'zero worker closure')
            who = dict(boot_id=self.value['boot_id'], release='7.1.4-g136f75ae869a', bundle='gpu-136f7-a9b1bc89566205b6')
            need(type(result) is dict and result.get('status') == 'PASS_ZERO_BRIGHTNESS_COMMAND'
                 and type(result.get('brightness_readback')) is int and result['brightness_readback'] == 0
                 and result.get('after', {}).get('identity') == who
                 and type(result['after'].get('brightness')) is int and result['after']['brightness'] == 0,
                 'independent zero readback differs')
        except Exception as exc:
            error = exc
        finally:
            if pid is not None:
                process = stop(pid, True)
            channel.close()
        if error is not None:
            error.process = process
            raise error
        return result, process


def main():
    import sys
    need(len(sys.argv) == 3 and sys.argv[1] == '--manifest-sha256', 'fixed manifest command required')
    directory = Path(__file__).resolve().parent
    value = context(directory, sys.argv[2])
    # SSH hangup must not bypass the independent cleanup path. The loop detects
    # EOF or missing lease within three seconds even if this signal is ignored.
    signal.signal(signal.SIGHUP, signal.SIG_IGN)
    def stopped(_number, _frame):
        raise ValueError('supervisor termination requested')
    signal.signal(signal.SIGTERM, stopped)
    signal.signal(signal.SIGINT, stopped)
    result = Supervisor(directory, value).run()
    return 0 if result['status'] == 'PASS_GPU_INITIALIZATION_AND_CLEANUP' else 1


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except Exception as exc:
        os.write(2, (type(exc).__name__+': '+str(exc)[:1000]+'\n').encode())
        raise SystemExit(1)
