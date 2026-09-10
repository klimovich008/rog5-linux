"""Bounded A01 Podman lifecycle; container completion is separate from guest PASS.

Ownership is recorded before create. A killed host cannot claim cleanup; an
outer controller may reconcile the retained name/label/CID without retrying VM.
"""
import json
import math
import os
from pathlib import Path
import re
import signal
import stat
import subprocess
import tempfile
import time
import uuid

LABEL = 'rog5.a01-owner'
LOG_LIMIT = 8 * 1024 * 1024


def need(condition, reason):
    if not condition:
        raise ValueError(reason)


def save(path, value):
    with path.open('x') as stream:
        json.dump(value, stream, indent=2)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())
    descriptor = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def create_command(command, name, owner, cidfile):
    argv = [str(value) for value in command]
    need(argv[:2] == ['podman', 'run'], 'expected A01 podman run command')
    options = []
    index = 2
    while index < len(argv) and argv[index].startswith('-'):
        value = argv[index]
        if value == '-v':
            need(index + 1 < len(argv) and argv[index + 1].endswith(':ro'),
                 'A01 mounts must be read-only')
            options.extend(argv[index:index + 2])
            index += 2
            continue
        need(value in ('--rm', '--pull=never', '--network=none', '--cap-drop=ALL',
                       '--security-opt=no-new-privileges', '--cpus=2',
                       '--memory=1g', '--memory-swap=1g'), 'unexpected A01 option')
        need(value not in options, 'duplicate A01 option')
        if value != '--rm':
            options.append(value)
        index += 1
    required = {'--pull=never', '--network=none', '--cap-drop=ALL',
                '--security-opt=no-new-privileges', '--cpus=2',
                '--memory=1g', '--memory-swap=1g'}
    need(required <= set(options), 'missing A01 resource/isolation guard')
    need(index < len(argv) and re.fullmatch(r'(?:sha256:)?[0-9a-f]{64}', argv[index]),
         'resolved container image required')
    image = argv[index].removeprefix('sha256:')
    need(argv[index + 1:index + 7] == ['timeout', '--kill-after=2', '60',
         'qemu-system-aarch64', '-M', 'virt'], 'bounded A01 guest command required')
    return (['podman', 'create', '--name', name, '--label', LABEL + '=' + owner,
             '--cidfile', str(cidfile), *options, *argv[index:]], image)


def call(argv, timeout):
    # Podman metadata is small; avoid unbounded captured-output allocation.
    with tempfile.TemporaryFile() as stdout, tempfile.TemporaryFile() as stderr:
        result = subprocess.run(argv, stdout=stdout, stderr=stderr,
                                timeout=timeout, check=False)
        stdout.seek(0)
        stderr.seek(0)
        out, err = stdout.read(256 * 1024 + 1), stderr.read(256 * 1024 + 1)
    need(len(out) <= 256 * 1024 and len(err) <= 256 * 1024, 'Podman metadata limit')
    return result.returncode, out.decode(), err.decode(errors='replace')


def owned(info, record, expected_id=None):
    cid = info['Id']
    need(re.fullmatch('[0-9a-f]{64}', cid) and
         (expected_id is None or cid == expected_id) and
         info['Name'].lstrip('/') == record['name'] and
         info['Image'].removeprefix('sha256:') == record['image'] and
         info['Config']['Labels'].get(LABEL) == record['owner'],
         'container ownership mismatch')
    return cid


def inspect(reference, record, timeout, expected_id=None):
    code, out, err = call(['podman', 'inspect', reference], timeout)
    need(code == 0, 'container inspect failed: ' + err[:512])
    rows = json.loads(out)
    need(isinstance(rows, list) and len(rows) == 1, 'container inspect shape')
    owned(rows[0], record, expected_id)
    state = rows[0]['State']
    need(type(state['Running']) is bool and type(state['OOMKilled']) is bool and
         type(state['ExitCode']) is int, 'container state shape')
    return rows[0]


def cleanup(record, result, process):
    evidence = result['cleanup']
    final_end = time.monotonic() + 25
    end = final_end - 10  # Reserve independent client/group closure time.

    def attempt(label, operation):
        try:
            remaining = end - time.monotonic()
            need(remaining > 0, 'cleanup deadline')
            value = operation(min(3, remaining))
            evidence['actions'].append(label)
            return value
        except Exception as error:
            evidence['errors'].append(label + ': ' + type(error).__name__ + ': ' + str(error))
            return None

    # Use the known UUID name even after malformed/truncated create output.
    # A failed create never reaches start. Retry discovery, not guest execution.
    info = None
    for _ in range(3):
        info = attempt('inspect owned container', lambda timeout:
                       inspect(record['name'], record, timeout, result['container_id']))
        if info is not None:
            break
    if info is not None:
        cid = info['Id']
        result['container_id'] = cid
        if info['State']['Running']:
            evidence['forced_stop'] = True

            def stop(timeout):
                code, _, err = call(['podman', 'stop', '--time', '1', cid], timeout)
                need(code == 0, 'stop failed: ' + err[:512])
                return True

            stopped = attempt('stop owned container', stop)
            if stopped is None:
                attempt('kill owned container', lambda timeout:
                        checked_cleanup(['podman', 'kill', cid], timeout))
        terminal = attempt('inspect terminal container', lambda timeout:
                           inspect(cid, record, timeout, cid))
        if terminal is not None and terminal['State']['Running']:
            evidence['forced_stop'] = True
            attempt('kill still-running container', lambda timeout:
                    checked_cleanup(['podman', 'kill', cid], timeout))
            terminal = attempt('inspect killed container', lambda timeout:
                               inspect(cid, record, timeout, cid))
        if terminal is not None:
            result['container_state'] = terminal['State']
            if not terminal['State']['Running']:
                removed = attempt('remove owned container', lambda timeout:
                                  checked_cleanup(['podman', 'rm', cid], timeout))
                if removed:
                    absent = attempt('confirm removal', lambda timeout:
                                     absent_container(cid, timeout))
                    result['container_removed'] = absent is True
    # Client cleanup is independent of every container observation/action.
    end = final_end
    if process is not None:
        try:
            group_live = attempt('inspect attach group', lambda timeout: group_exists(process.pid))
            if group_live is True:
                evidence['forced_stop'] = True
                attempt('terminate attach group', lambda timeout:
                        signal_group(process.pid, signal.SIGTERM))
            leader = attempt('reap attach client', lambda timeout: wait_client(process, min(1, timeout)))
            closed = attempt('confirm attach group absent', lambda timeout:
                             wait_group(process.pid, min(1, timeout)))
            if leader is not True or closed is not True:
                evidence['forced_stop'] = True
                attempt('kill attach group', lambda timeout:
                        signal_group(process.pid, signal.SIGKILL))
                leader = attempt('reap killed attach client', lambda timeout:
                                 wait_client(process, min(2, timeout)))
                closed = attempt('confirm killed attach group absent', lambda timeout:
                                 wait_group(process.pid, min(2, timeout)))
            evidence['leader_reaped'] = leader is True
            evidence['attach_group_closed'] = closed is True
            evidence['client_reaped'] = leader is True and closed is True
        except Exception as error:
            evidence['errors'].append('attach cleanup: ' + str(error))
    else:
        evidence['client_reaped'] = True
        evidence['leader_reaped'] = True
        evidence['attach_group_closed'] = True
    evidence['confirmed'] = result['container_removed'] and evidence['client_reaped']


def checked_cleanup(argv, timeout):
    code, _, err = call(argv, timeout)
    need(code == 0, 'cleanup command failed: ' + err[:512])
    return True


def absent_container(cid, timeout):
    code, _, err = call(['podman', 'container', 'exists', cid], timeout)
    need(code in (0, 1), 'removal lookup failed: ' + err[:512])
    need(code == 1, 'container remains after removal')
    return True


def wait_client(process, timeout):
    process.wait(timeout=timeout)
    return True


def group_exists(pgid):
    try:
        os.killpg(pgid, 0)
    except ProcessLookupError:
        return False
    return True


def signal_group(pgid, number):
    try:
        os.killpg(pgid, number)
    except ProcessLookupError:
        pass
    return True


def wait_group(pgid, timeout):
    end = time.monotonic() + timeout
    while group_exists(pgid):
        need(time.monotonic() < end, 'attach process-group descendants remain')
        time.sleep(min(0.05, max(0, end - time.monotonic())))
    return True


def run(command, log_path, deadline_seconds=70):
    """Return JSON evidence. ``passed`` covers lifecycle, not console semantics."""
    result = dict(exit_code=None, passed=False, container_id=None,
                  container_state=None, container_removed=False,
                  cleanup=dict(errors=[], actions=[], forced_stop=False,
                               client_reaped=False, leader_reaped=False,
                               attach_group_closed=False, confirmed=False))
    process = None
    record = None
    handlers = {}
    started = time.monotonic()
    try:
        need(isinstance(deadline_seconds, (int, float)) and
             math.isfinite(deadline_seconds) and 0 < deadline_seconds <= 70,
             'A01 deadline must be positive and at most 70 seconds')
        log_path = Path(log_path)
        need(log_path.is_absolute() and log_path.parent.resolve() == log_path.parent
             and log_path.parent.is_dir(), 'absolute private output path required')
        need(not log_path.exists() and not log_path.is_symlink(), 'fresh VM log required')
        owner = uuid.uuid4().hex
        cidfile = log_path.with_name(log_path.name + '.cid')
        ownership = log_path.with_name(log_path.name + '.ownership.json')
        need(not cidfile.exists() and not cidfile.is_symlink(), 'fresh CID file required')
        create, image = create_command(command, 'rog5-a01-' + owner, owner, cidfile)
        record = dict(name='rog5-a01-' + owner, owner=owner, label=LABEL,
                      image=image, cidfile=str(cidfile), create_command=create,
                      cleanup_confirmed=False,
                      limitation='Host SIGKILL/OOM leaves cleanup unconfirmed; never retry start.')
        save(ownership, record)
        result.update(ownership_path=str(ownership), command=create, image=image)

        def interrupted(number, _frame):
            raise RuntimeError('VM host signal ' + str(number))

        for number in (signal.SIGTERM, signal.SIGINT):
            handlers[number] = signal.signal(number, interrupted)
        code, out, err = call(create, min(15, deadline_seconds))
        need(code == 0, 'container create failed: ' + err[:512])
        cid = out.strip()
        need(re.fullmatch('[0-9a-f]{64}', cid), 'invalid created container ID')
        metadata = cidfile.lstat()
        need(stat.S_ISREG(metadata.st_mode) and metadata.st_nlink == 1 and
             metadata.st_size <= 65, 'invalid CID file')
        need(cidfile.read_text().strip() == cid, 'CID file/output mismatch')
        info = inspect(cid, record, min(5, deadline_seconds), cid)
        need(not info['State']['Running'], 'new container already running')
        result['container_id'] = cid
        save(log_path.with_name(log_path.name + '.created.json'),
             dict(**record, container_id=cid))
        with log_path.open('xb') as log:
            need(time.monotonic() < started + deadline_seconds, 'VM deadline before start')
            process = subprocess.Popen(['podman', 'start', '--attach', cid],
                                       stdout=log, stderr=subprocess.STDOUT,
                                       start_new_session=True)
            while process.poll() is None:
                need(log_path.stat().st_size <= LOG_LIMIT, 'VM console limit')
                if time.monotonic() >= started + deadline_seconds:
                    result['exit_code'] = 124
                    raise TimeoutError('independent VM deadline')
                time.sleep(0.05)
            result['exit_code'] = process.returncode
        need(log_path.stat().st_size <= LOG_LIMIT, 'final VM console limit')
    except Exception as error:
        result['error'] = type(error).__name__ + ': ' + str(error)
    finally:
        if record is not None and 'ownership_path' in result:
            for number in handlers:
                signal.signal(number, signal.SIG_IGN)
            try:
                cleanup(record, result, process)
            except Exception as error:
                result['cleanup']['errors'].append('unexpected cleanup failure: ' + str(error))
        for number, handler in handlers.items():
            signal.signal(number, handler)
        state = result['container_state']
        result['passed'] = bool('error' not in result and result['exit_code'] == 0 and
            result['cleanup']['confirmed'] and not result['cleanup']['errors'] and
            not result['cleanup']['forced_stop'] and state is not None and
            state['Running'] is False and state['OOMKilled'] is False and state['ExitCode'] == 0)
        result['duration_seconds'] = time.monotonic() - started
        if 'ownership_path' in result:
            save(Path(result['ownership_path']).with_suffix('.result.json'), result)
    return result
