#!/usr/bin/env python3
"""Explicit offline ARM64 PAM/logind VM test; never a phone test or installer."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import resource
import shutil
import signal
import subprocess
import sys
import time
import tarfile
import uuid

REPO = Path(__file__).resolve().parents[2]
SOURCES = REPO / 'tools/qemu-virtio-drm'
RESERVE = 3 * 1024**3
LOG_LIMIT = 8 * 1024**2
SUCCESS = 'PASS authenticated local logind session, mediated devices and removed scope'
INTERRUPTS = {signal.SIGINT, signal.SIGTERM}
APPS_CLEANUP_GRACE = 30


STARTUP_UNITS = ('systemd-hwdb-update.service', 'ldconfig.service',
                 'systemd-journal-catalog-update.service', 'systemd-tmpfiles-setup.service',
                 'systemd-tmpfiles-setup-dev-early.service', 'systemd-udevd.service',
                 'systemd-udev-trigger.service', 'systemd-logind.service', 'sysinit.target')


def startup_result(serial):
    """Decode bounded diagnostic data without treating it as session proof."""
    failures = re.findall(r'^(?:bash\[[1-9][0-9]*\]: )?DIAGNOSTIC_UNIT_TIMINGS status=failed code=(\d+) bytes=(\d+) hex=[0-9a-f]*$', serial, re.M)
    if failures:
        code, size = failures[0]
        raise ValueError(f'startup timing query failed (code={code}, bytes={size}); inventory unqualified')
    packet = re.findall(r'^(?:bash\[[1-9][0-9]*\]: )?DIAGNOSTIC_UNIT_TIMINGS status=read bytes=(\d+) hex=([0-9a-f]+)$', serial, re.M)
    handoff = re.findall(r'^OBSERVE pid1-handoff boottime=([0-9]+\.[0-9]+)$', serial, re.M)
    ready = 'PASS startup-only authenticated readiness; Denial NOT RUN'
    readiness = re.findall(r'^(?:bash\[[1-9][0-9]*\]: )?'+re.escape(ready)+r'$', serial, re.M)
    if len(packet) != 1 or len(handoff) != 1 or len(readiness) != 1:
        raise ValueError('missing or duplicate startup timing/readiness records')
    size, encoded = packet[0]
    if not 0 < int(size) <= 16384 or len(encoded) != 2 * int(size):
        raise ValueError('startup timing payload bound or size mismatch')
    decoded = bytes.fromhex(encoded).decode('ascii')
    units = {}
    numeric = {'ActiveEnterTimestampMonotonic', 'InactiveExitTimestampMonotonic',
               'ExecMainStartTimestampMonotonic', 'ExecMainExitTimestampMonotonic',
               'ConditionTimestampMonotonic', 'ExecMainStatus'}
    fields = numeric | {'Id', 'LoadState', 'ActiveState', 'ConditionResult', 'Result'}
    for block in decoded.strip().split('\n\n'):
        row = {}
        for line in block.splitlines():
            key, sep, value = line.partition('=')
            if not sep or key not in fields or key in row:
                raise ValueError('unknown or duplicate startup unit field')
            if key in numeric:
                if not value.isascii() or not value.isdecimal():
                    raise ValueError('invalid startup timestamp/status')
                value = int(value)
            row[key] = value
        unit = row.get('Id')
        if (unit not in STARTUP_UNITS or unit in units or row.get('LoadState') != 'loaded'
                or not {'ActiveState', 'ActiveEnterTimestampMonotonic', 'InactiveExitTimestampMonotonic'} <= row.keys()):
            raise ValueError('missing, unloaded or unexpected startup unit')
        units[unit] = row
    if set(units) != set(STARTUP_UNITS):
        raise ValueError('incomplete startup unit inventory')
    return {'status': 'PASS', 'scope': 'complete pre-PAM sysinit timing inventory; unit success not inferred', 'units': units,
            'unit_clock': 'systemd monotonic microseconds; zero means no recorded transition',
            'pid1_handoff_boottime_seconds': float(handoff[0]),
            'clock_limit': 'handoff uses /proc/uptime BOOTTIME; do not subtract across clock domains'}


def install_handlers():
    def interrupted(number, _frame):
        # Finish owned-process/container cleanup even if cancellation is repeated.
        for item in INTERRUPTS:
            signal.signal(item, signal.SIG_IGN)
        raise InterruptedError(f'interrupted by signal {number}')
    for item in INTERRUPTS:
        signal.signal(item, interrupted)


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def regular(path):
    path = Path(path).resolve(strict=True)
    if not path.is_file():
        raise ValueError(f'not a regular file: {path}')
    return path


def identity(path):
    path = regular(path)
    before = path.stat()
    with path.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    after = path.stat()
    stable = lambda s: (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns)
    if stable(before) != stable(after):
        raise ValueError(f'input changed while hashing: {path}')
    return {'path': str(path), 'sha256': digest, 'bytes': after.st_size}


def limits():
    for item in INTERRUPTS:
        signal.signal(item, signal.SIG_DFL)
    signal.pthread_sigmask(signal.SIG_UNBLOCK, INTERRUPTS)
    resource.setrlimit(resource.RLIMIT_FSIZE, (LOG_LIMIT, LOG_LIMIT))


def apps_cleanup_ready(observer):
    return bool(observer and observer.complete and observer.ack_sent and observer.teardown and not observer.error)


def execute(command, log, deadline, steps, *, cwd=None, data=None, stdout=None, accepted=(0,), poll=None,
            cleanup_ready=None):
    """Own a process group and bound output, wall time, and descendant lifetime."""
    if poll is not None and data is not None:
        raise ValueError('live observation excludes command stdin')
    if cleanup_ready is not None and poll is None:
        raise ValueError('cleanup allowance requires live observation')
    row = {'command': list(map(str, command)), 'started_utc': now(), 'deadline_seconds': deadline}
    if cwd is not None:
        row['cwd'] = str(cwd)
    if data is not None:
        row['stdin_sha256'] = hashlib.sha256(data).hexdigest()
    steps.append(row)
    started = time.monotonic()
    child = None
    row['status'] = 'FAIL'
    try:
        with log.open('xb') as output:
            previous_mask = signal.pthread_sigmask(signal.SIG_BLOCK, INTERRUPTS)
            try:
                child = subprocess.Popen(row['command'], cwd=cwd, stdin=subprocess.PIPE if data is not None else subprocess.DEVNULL,
                                         stdout=stdout if stdout is not None else output,
                                         stderr=output if stdout is not None else subprocess.STDOUT,
                                         start_new_session=True, preexec_fn=limits)
            finally:
                # Publish ownership before delivering a pending cancellation.
                signal.pthread_sigmask(signal.SIG_SETMASK, previous_mask)
            try:
                if poll is None:
                    child.communicate(input=data, timeout=deadline)
                else:
                    end = time.monotonic() + deadline
                    original_end = end
                    eligible = granted = False
                    def check_deadline():
                        nonlocal end, granted
                        if time.monotonic() >= end:
                            if eligible and not granted:
                                # A single reserve for already approved teardown;
                                # messages cannot reset it or extend startup.
                                end = original_end + APPS_CLEANUP_GRACE
                                granted = True
                                row['cleanup_grace_seconds'] = APPS_CLEANUP_GRACE
                                row['cleanup_granted_seconds'] = time.monotonic() - started
                                row['effective_deadline_seconds'] = deadline + APPS_CLEANUP_GRACE
                            if time.monotonic() >= end:
                                raise subprocess.TimeoutExpired(command, row.get('effective_deadline_seconds', deadline))
                    while True:
                        check_deadline()
                        if child.poll() is not None:
                            poll()
                            check_deadline()
                            break
                        poll()
                        # A tick that crosses the original cutoff cannot grant
                        # extra time using evidence received after that cutoff.
                        if cleanup_ready is not None and time.monotonic() < original_end:
                            candidate = cleanup_ready() is True
                            sampled = time.monotonic()
                            eligible = candidate and sampled < original_end
                            if eligible and 'cleanup_eligible_seconds' not in row:
                                row['cleanup_eligible_seconds'] = sampled - started
                        time.sleep(.02)
            except subprocess.TimeoutExpired:
                row['status'] = 'FAIL_TIMEOUT'
                raise RuntimeError(f'command exceeded {row.get("effective_deadline_seconds", deadline)}s: {command[0]}')
            row['exit_status'] = child.returncode
            if child.returncode not in accepted:
                raise RuntimeError(f'command failed ({child.returncode}): {command[0]}')
            row['status'] = 'PASS'
    except OSError as error:
        row['error'] = str(error)
        raise
    finally:
        if child is not None:
            # Also terminate a background descendant after its parent has exited.
            try:
                os.killpg(child.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            child.wait(timeout=10)
            row.setdefault('exit_status', child.returncode)
        row['duration_seconds'] = time.monotonic() - started
        row['ended_utc'] = now()
        if log.exists():
            row['log'] = identity(log)


def container(command, name, log, deadline, steps, *, poll=None, finalize=None, cleanup_ready=None):
    """Only the uniquely named container created by this invocation is cleaned."""
    original = None
    try:
        execute(command, log, deadline, steps, poll=poll, cleanup_ready=cleanup_ready)
    except BaseException as error:
        original = error
    finally:
        cleanup_error = None
        if finalize is not None:
            try:
                finalize(original)
            except BaseException as error:
                original = original or error
        try:
            execute(['podman', 'rm', '--force', '--ignore', name], log.with_suffix('.cleanup.log'), 15, steps)
            # `exists` has useful nonzero semantics; preserve its exact result.
            execute(['podman', 'container', 'exists', name], log.with_suffix('.absence.log'), 10, steps, accepted=(1,))
            steps[-1]['interpretation'] = 'exit 1 proves named container absent'
        except BaseException as error:
            cleanup_error = error
    if original or cleanup_error:
        raise RuntimeError(f'operation={original}; cleanup={cleanup_error}')


def disk_guard(output):
    if shutil.disk_usage(output).free < RESERVE:
        raise RuntimeError('host free disk fell below 3 GiB reserve')


def require_vm_poweroff(serial):
    serial = re.sub(r'\x1b\[[0-?]*[ -/]*[@-~]', '', serial)
    # A recovered CPU stall still invalidates a successful qualification. Both
    # forms occur in the retained VM evidence; normal RCU boot messages do not.
    if re.search(r'\brcu: INFO: \S+ (?:self-)?detected stalls?\b', serial):
        raise RuntimeError('VM recorded an RCU CPU stall')
    if 'Kernel panic' in serial or 'reboot: Power down' not in serial:
        raise RuntimeError('VM lacks normal poweroff or recorded a kernel panic')


def validate_session_archive(archive, receipt):
    """Verify the retained composition and every regular member before guest extraction."""
    record = json.loads(receipt.read_text())
    if record.get('status') != 'PREPARED_NOT_INSTALLED' or record.get('authority') != 'none':
        raise ValueError('requires an unsigned session composition receipt')
    if identity(archive)['sha256'] != record['sha256'] or archive.stat().st_size != record['size']:
        raise ValueError('session archive identity differs from receipt')
    entries = record['metadata']['files']
    expected = {row['name']: row for row in entries}
    if len(expected) != len(entries):
        raise ValueError('duplicate session inventory path')
    required = {'usr/bin/deniald', 'usr/bin/denialctl', 'usr/bin/denial-session',
                'usr/bin/denial-mobile-session', 'usr/lib/systemd/user/denial-session.target',
                'usr/lib/denial/flutter/lib/libapp.so', 'usr/lib/denial/flutter/lib/libflutter_engine.so'}
    if not required <= expected.keys():
        raise ValueError('incomplete session inventory')
    allowed_dirs = {str(parent) for name in set(expected) | {'usr/share/rog5-denial/payload.json'}
                    for parent in Path(name).parents if str(parent) != '.'}
    seen = set()
    seen_files = set()
    total = 0
    with tarfile.open(archive, 'r|gz') as stream:
        for member in stream:
            name = member.name
            if (name.startswith('/') or Path(name).as_posix() != name or '..' in Path(name).parts
                    or name in seen or member.uid != 0 or member.gid != 0):
                raise ValueError('unsafe session archive member')
            seen.add(name)
            if member.isdir():
                if name not in allowed_dirs or member.mode != 0o755 or member.size != 0:
                    raise ValueError('unexpected session directory')
                continue
            if not member.isfile():
                raise ValueError('unsafe session archive member')
            seen_files.add(name)
            total += member.size
            if total > 128 * 1024**2:
                raise ValueError('session archive exceeds RAM fixture bound')
            with stream.extractfile(member) as data:
                digest = hashlib.file_digest(data, 'sha256').hexdigest()
            if name == 'usr/share/rog5-denial/payload.json':
                continue
            row = expected.get(name)
            if row is None or (member.size, member.mode, digest) != (row['size'], row['mode'], row['sha256']):
                raise ValueError('session member differs from inventory: '+name)
    if seen_files != set(expected) | {'usr/share/rog5-denial/payload.json'}:
        raise ValueError('session archive file set differs from inventory')
    return record


def validate_apps_inputs(reference, writer):
    # Fail before compilation or VM startup. The semantic PNG check is shared
    # with the actual observer; the supplied executable must target the guest.
    import importlib.util
    spec = importlib.util.spec_from_file_location('apps_preflight', REPO/'scripts/host/qemu-mobile-observer.py')
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    module.launcher_tile_signatures(reference)
    with writer.open('rb') as stream:
        header = stream.read(20)
    if len(header) != 20 or header[:7] != b'\x7fELF\x02\x01\x01' or header[18:20] != b'\xb7\x00':
        raise ValueError('evidence writer must be a little-endian ARM64 ELF executable')


def validate_settings_sync_diagnostic(source):
    source = Path(source)
    if source.is_symlink() or not source.is_file() or source.stat().st_size > 1024**2:
        raise ValueError('settings diagnostic requires a regular bounded ARM64 shared ELF')
    with source.open('rb') as stream:
        header = stream.read(64)
    if (len(header) != 64 or header[:7] != b'\x7fELF\x02\x01\x01'
            or header[16:20] != b'\x03\x00\xb7\x00'):
        raise ValueError('settings diagnostic requires an ARM64 shared ELF')
    return source


def stage_settings_sync_diagnostic(source, stage):
    """Stage an explicit, bounded VM-only ARM64 DSO without replacing an output."""
    source = validate_settings_sync_diagnostic(source)
    target = stage/'settings-sync-diagnostic.so'
    with source.open('rb') as stream, target.open('xb') as output:
        shutil.copyfileobj(stream, output, 1024*1024)
    target.chmod(0o644)
    return target


def linker_cache_module():
    import importlib.util
    spec = importlib.util.spec_from_file_location('linker_cache', REPO/'scripts/host/prepare-qemu-linker-cache.py')
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def hwdb_cache_module():
    import importlib.util
    spec = importlib.util.spec_from_file_location('hwdb_cache', REPO/'scripts/host/stage-qemu-hwdb-cache.py')
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def stage_hwdb_cache(directory, runtime, receipt, output, result):
    # Admit and copy once, before compiler/container work. The copied bytes are
    # verified by the guest before the generator-suppression marker is published.
    # Large data belongs on the existing read-only 9p payload mount, outside
    # the 8 MiB initramfs/tool-output budget. The guest copies it to private RAM.
    stage = output/'payload'
    stage.mkdir(parents=True, exist_ok=True)
    record = hwdb_cache_module().stage(directory, runtime, receipt, stage)
    result['hwdb_cache'] = record
    for member in ('hwdb-cache', 'hwdb-cache.sha256'):
        result['outputs']['payload/'+member] = identity(stage/member)


def observation_channel(apps):
    if apps:
        # Host is the sole event-log writer. Duplex channel returns the exact
        # completion token only after the observation oracles pass.
        return ['-chardev', 'socket,id=apps,path=/observe/apps.sock,server=on,wait=off',
                '-device', 'virtserialport,chardev=apps,name=rog5.apps,nr=1']
    return ['-chardev', 'file,id=editor,path=/observe/editor.log',
            '-device', 'virtserialport,chardev=editor,name=rog5.editor,nr=1']


def stage_render_audit(enabled, stage):
    target = stage / 'denial-render-audit'
    with target.open('x') as stream:
        stream.write('1\n' if enabled else '0\n')
    return target


def session_observer(module, args, directory, name, token):
    if args.observe_apps:
        options = {'automatic_caret': args.automatic_caret}
        if getattr(args, 'close_only', False):
            options['close_only'] = True
        if getattr(args, 'bottom_caret', False):
            options['bottom_caret'] = True
        return module.LiveApps(directory, name, token, args.launcher_reference, **options)
    return module.LiveEditor(directory, name)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('runtime-view', 'runtime-receipt', 'kernel', 'qemu-image', 'toolchain-image', 'libc', 'libloading', 'output'):
        parser.add_argument('--' + name, required=True)
    parser.add_argument('--session-archive', type=Path)
    parser.add_argument('--session-receipt', type=Path)
    parser.add_argument('--host-render-node', type=Path)
    parser.add_argument('--tcg-thread', choices=('multi', 'single'), default='multi',
                        help='TCG host-thread mode; preserves guest CPU count and existing limits')
    parser.add_argument('--disable-mops', action='store_true',
                        help='explicit generic-VM diagnostic: append arm64.nomops; no default CPU-feature workaround')
    parser.add_argument('--startup-only', action='store_true',
                        help='combined VM preparation and PAM readiness/cleanup only; no Denial execution')
    parser.add_argument('--render-audit', action='store_true',
                        help='opt in to verbose Denial/engine render tracing; terminal counters remain enabled without it')
    observation = parser.add_mutually_exclusive_group()
    observation.add_argument('--observe-editor', action='store_true',
                        help='pointer-only OSK editor test in authenticated session; VM only')
    observation.add_argument('--observe-apps', action='store_true',
                             help='launcher-driven app switching and OSK in authenticated VM')
    parser.add_argument('--close-only', action='store_true',
                        help='observe-apps only: map both clients and exercise existing close handshake; no text entry')
    parser.add_argument('--automatic-caret', action='store_true',
                        help='observe-apps only: omit manual viewport pan and inverse; VM only')
    parser.add_argument('--bottom-caret', action='store_true',
                        help='automatic-caret only: long RAM document and strict low-caret pointer mapping probe')
    parser.add_argument('--launcher-reference', type=Path)
    parser.add_argument('--evidence-writer', type=Path)
    parser.add_argument('--settings-sync-diagnostic', type=Path,
                        help='observe-apps only: explicit VM settings-sync probe DSO; no phone installation')
    parser.add_argument('--app-close-probe', action='store_true',
                        help='close-only diagnostic: bounded read-only owned Mousepad proc sampler')
    parser.add_argument('--linker-cache', type=Path,
                        help='exact-runtime cache directory from prepare-qemu-linker-cache.py; VM-only RAM staging')
    parser.add_argument('--hwdb-cache', type=Path,
                        help='retained exact-runtime ARM64 hardware database; verified VM-only RAM staging')
    args = parser.parse_args()
    combined = args.session_archive is not None
    if len([p for p in (args.session_archive, args.session_receipt, args.host_render_node) if p is not None]) not in (0, 3):
        parser.error('combined session requires archive, receipt and explicit host render node')
    if (args.observe_editor or args.observe_apps) and not combined:
        parser.error('observation requires combined authenticated session')
    if args.observe_apps != (args.launcher_reference is not None and args.evidence_writer is not None) or (
            not args.observe_apps and (args.launcher_reference is not None or args.evidence_writer is not None)):
        parser.error('apps observation requires exactly launcher-reference and evidence-writer')
    if args.automatic_caret and not args.observe_apps:
        parser.error('automatic-caret requires observe-apps')
    if args.bottom_caret and not (args.observe_apps and args.automatic_caret):
        parser.error('bottom-caret requires observe-apps and automatic-caret')
    if args.close_only and (not args.observe_apps or args.automatic_caret or args.bottom_caret):
        parser.error('close-only requires observe-apps and excludes caret/text observation')
    if args.startup_only and (not combined or args.observe_apps or args.observe_editor):
        parser.error('startup-only requires combined inputs and excludes UI observation')
    if args.render_audit and (not combined or args.startup_only):
        parser.error('render-audit requires a combined Denial session')
    if args.settings_sync_diagnostic is not None and not args.observe_apps:
        parser.error('settings-sync-diagnostic requires observe-apps')
    if args.app_close_probe and not (args.close_only and args.settings_sync_diagnostic is not None):
        parser.error('app-close-probe requires close-only and settings-sync-diagnostic')
    install_handlers()
    output = Path(args.output).resolve()
    if os.geteuid() == 0:
        parser.error('run as an ordinary host user; only rootless containers are supported')
    if output.exists():
        parser.error('output must be fresh; existing results are never replaced')
    if not output.parent.is_dir() or shutil.disk_usage(output.parent).free < RESERVE + 16 * 1024**2:
        parser.error('output parent must exist with at least 3 GiB + 16 MiB free')
    runtime = Path(args.runtime_view).resolve()
    if output.is_relative_to(runtime):
        parser.error('output may not be inside the immutable runtime view')
    # Inspect both retained roots before creating any output. Full receipt and
    # inventory admission still follows; this guard must not modify its inputs.
    try:
        original_name = json.loads(regular(args.runtime_receipt).read_text())['runtime']
        if not isinstance(original_name, str) or not Path(original_name).is_absolute():
            raise ValueError('receipt requires an absolute original runtime path')
        original_runtime = Path(original_name).resolve()
    except (OSError, ValueError, KeyError, TypeError) as error:
        parser.error('cannot protect original runtime: ' + str(error))
    if output.is_relative_to(original_runtime):
        parser.error('output may not be inside the immutable original runtime')
    output.mkdir(mode=0o700)
    result = {'status': 'FAIL', 'authority': 'none', 'physical_status': 'NOT RUN',
              'scope': 'generic ARM64 systemd PID1, original PAM login profile, local logind and mediated virtual devices',
              'started_utc': now(), 'command': [sys.executable, str(Path(__file__).resolve()), *sys.argv[1:]],
              'steps': [], 'inputs': {}, 'outputs': {},
              'runtime_limit': 'Runtime receipt identity is bound; complete runtime inventory/authentication is a prior external prerequisite, not rerun here.'}
    started = time.monotonic()
    observer = None
    observation_key = 'apps_observation' if args.observe_apps else 'editor_observation'
    try:
        for image in (args.qemu_image, args.toolchain_image):
            if not re.fullmatch(r'[0-9a-f]{64}', image):
                raise ValueError('container images must be immutable full 64-hex image IDs')
        if not runtime.is_dir():
            raise ValueError('runtime-view is not a directory')
        receipt = regular(args.runtime_receipt)
        receipt_data = json.loads(receipt.read_text())
        if (receipt_data.get('status') != 'PASS_VIEW_PREPARED'
                or receipt_data.get('security_model') != 'mapped-file'
                or receipt_data.get('readonly_required') is not True
                or Path(receipt_data.get('root', '')).resolve() != runtime):
            raise ValueError('runtime receipt does not identify this prepared read-only mapped-file view')
        if args.linker_cache is not None:
            result['linker_cache'] = linker_cache_module().validate(args.linker_cache, runtime, receipt)
        if args.hwdb_cache is not None:
            stage_hwdb_cache(args.hwdb_cache, runtime, receipt, output, result)
            result['runtime_limit'] = 'Hardware-database admission reverified complete original/mapped runtime inventories, bytes and metadata before staging.'
        if combined:
            session_record = validate_session_archive(regular(args.session_archive), regular(args.session_receipt))
            if args.host_render_node != Path('/dev/dri/renderD128') or not args.host_render_node.is_char_device():
                raise ValueError('requires the explicitly retained host renderD128 fixture node')
            result['session_composition'] = session_record
            result['scope'] += ('; startup-only combined preparation and authenticated readiness; Denial NOT RUN'
                                if args.startup_only else '; actual mobile launcher, VirGL rendering and native clients')
            node = args.host_render_node.stat()
            result['host_render_node'] = {'path': str(args.host_render_node), 'rdev': node.st_rdev, 'resolved': str(args.host_render_node.resolve())}
        if args.observe_apps:
            validate_apps_inputs(regular(args.launcher_reference), regular(args.evidence_writer))
        if args.settings_sync_diagnostic is not None:
            validate_settings_sync_diagnostic(args.settings_sync_diagnostic)
        result['runtime_view'] = str(runtime)
        result['container_images'] = {'qemu': args.qemu_image, 'toolchain': args.toolchain_image}
        for key, command in [('commit', ['rev-parse', 'HEAD']), ('tree', ['rev-parse', 'HEAD^{tree}']),
                             ('worktree_status', ['status', '--porcelain=v1'])]:
            result.setdefault('source', {})[key] = subprocess.check_output(['git', '-C', str(REPO), *command], text=True, timeout=10).strip()
        result['source']['dirty'] = bool(result['source']['worktree_status'])
        kernel, libc, libloading = map(regular, (args.kernel, args.libc, args.libloading))
        source_names = ['init.c', 'logind-seat-probe.rs', 'logind-pam-session.rs',
                        'logind-boot.sh', 'logind-session.sh', 'logind-user.sh', 'logind-observer.sh',
                        'logind-linker-cache.sh']
        if combined:
            source_names += ['logind-denial.sh', 'logind-denial-prepare.sh', 'logind-font-cache.sh', 'logind-gtk-im-cache.sh', 'logind-icon-cache.sh']
        input_files = [regular(SOURCES / name) for name in source_names] + [kernel, libc, libloading, receipt, Path(__file__).resolve()]
        if args.linker_cache is not None:
            input_files += [args.linker_cache/'ld.so.cache', args.linker_cache/'result.json',
                            REPO/'scripts/host/prepare-qemu-linker-cache.py']
        if args.hwdb_cache is not None:
            input_files += [args.hwdb_cache/'hwdb.bin', args.hwdb_cache/'result.json',
                            REPO/'scripts/host/stage-qemu-hwdb-cache.py',
                            REPO/'scripts/host/prepare-qemu-linker-cache.py']
        if combined:
            input_files += [regular(args.session_archive), regular(args.session_receipt), REPO/'scripts/host/test-qemu-virtio-drm.py']
        if args.observe_apps:
            source_names_extra = ['logind-apps.sh', 'launcher-apps.sh', 'launcher-evidence.sh', 'evidence-writer.rs']
            input_files += [SOURCES/name for name in source_names_extra]
            input_files += [regular(args.launcher_reference), regular(args.evidence_writer),
                            REPO/'scripts/host/qemu-logind-apps.py',
                            REPO/'scripts/host/qemu-launcher-protocol.py']
            if args.bottom_caret:
                input_files.append(REPO/'scripts/host/qemu-caret-protocol.py')
        if args.settings_sync_diagnostic is not None:
            input_files += [regular(args.settings_sync_diagnostic), SOURCES/'settings-sync-diagnostic.c']
        if args.app_close_probe:
            input_files.append(SOURCES/'app-close-probe.rs')
        if args.observe_editor or args.observe_apps:
            input_files += [SOURCES/'logind-editor.sh', REPO/'scripts/host/qemu-logind-editor.py',
                            REPO/'scripts/host/qemu-mobile-observer.py']
        # libloading's retained Linux dependency is cfg-if. Freeze matching cached
        # candidates too; the compiler chooses the compatible crate metadata.
        dependency_dirs = sorted({libc.parent, libloading.parent})
        for directory in dependency_dirs:
            input_files.extend(sorted(directory.glob('libcfg_if-*.rlib')))
        for path in input_files:
            result['inputs'][str(path)] = identity(path)
        for tool in ('podman', 'clang', 'bash', 'cpio', 'gzip'):
            found = shutil.which(tool)
            if not found:
                raise RuntimeError(f'mandatory host tool missing: {tool}')
            result.setdefault('host_tools', {})[tool] = identity(Path(found))
        payload = output / 'payload'
        payload.mkdir(exist_ok=True)
        stage = output / 'initramfs'
        for directory in ('dev', 'sysroot', 'stage/payload'):
            (stage / directory).mkdir(parents=True, exist_ok=True)
        helpers = [('logind-seat-probe.rs', 'logind-seat-probe'), ('logind-pam-session.rs', 'pam-session')]
        if args.app_close_probe:
            helpers.append(('app-close-probe.rs', 'app-close-probe'))
        for source_name, binary_name in helpers:
            disk_guard(output)
            source = output / source_name
            shutil.copyfile(SOURCES / source_name, source)
            name = 'rog5-logind-build-' + uuid.uuid4().hex[:16]
            rust = ['/opt/denial-rust/bin/rustc', '--edition=2024', '--target=aarch64-unknown-linux-gnu',
                    '--crate-name=' + binary_name.replace('-', '_'), '-Dwarnings', '-C', 'linker=/usr/bin/aarch64-linux-gnu-gcc',
                    '-C', 'opt-level=2', '-C', 'lto=thin', '-C', 'codegen-units=1', '-C', 'strip=debuginfo',
                    '--remap-path-prefix', str(output) + '=/logind-fixture', str(source), '-o', str(payload / binary_name),
                    '--extern', 'libc=' + str(libc), '--extern', 'libloading=' + str(libloading)]
            if combined and binary_name == 'pam-session':
                rust += ['--cfg', 'denial_session']
                if args.startup_only:
                    rust += ['--cfg', 'startup_only']
            command = ['podman', 'run', '--rm', '--name', name, '--pull=never', '--network=none', '--read-only',
                       '--memory=512m', '--memory-swap=512m', '--cpus=1', '--pids-limit=128']
            for directory in dependency_dirs:
                command += ['-v', f'{directory}:{directory}:ro']
                rust += ['-L', 'dependency=' + str(directory)]
            command += ['-v', f'{output}:{output}:rw', '--env', 'TMPDIR=' + str(output), args.toolchain_image, *rust]
            container(command, name, output / (binary_name + '.build.log'), 60, result['steps'])
            result['outputs'][binary_name] = identity(payload / binary_name)
        execute(['clang', '--target=aarch64-none-elf', '-fuse-ld=lld', '-nostdlib', '-static', '-fno-pic',
                 '-fno-stack-protector', '-DROG5_SYSTEMD_PID1', '-Werror', '-Wall', '-Wextra',
                 '-Wl,--build-id=none,--entry=_start', str(SOURCES / 'init.c'), '-o', str(stage / 'init')],
                output / 'init.build.log', 30, result['steps'])
        scripts = {'logind-boot.sh': 'guest.sh', 'logind-session.sh': 'logind-probe.sh',
                   'logind-user.sh': 'logind-user.sh', 'logind-observer.sh': 'independent-observer.sh',
                   'logind-linker-cache.sh': 'logind-linker-cache.sh'}
        if combined:
            scripts.update({'logind-denial.sh': 'logind-denial.sh', 'logind-denial-prepare.sh': 'logind-denial-prepare.sh',
                            'logind-font-cache.sh': 'logind-font-cache.sh',
                            'logind-gtk-im-cache.sh': 'logind-gtk-im-cache.sh',
                            'logind-icon-cache.sh': 'logind-icon-cache.sh'})
            (stage / 'stage/session-sha256').write_text(session_record['sha256']+'\n')
            audit_policy = stage_render_audit(args.render_audit, stage / 'stage')
            result['outputs']['stage/denial-render-audit'] = identity(audit_policy)
            os.link(args.session_archive, payload / 'session.tar.gz')
        if args.startup_only:
            (stage / 'stage/startup-only').write_text('1\n')
            result['outputs']['stage/startup-only'] = identity(stage / 'stage/startup-only')
        if args.observe_editor:
            scripts['logind-editor.sh'] = 'logind-editor.sh'
            (stage / 'stage/editor-probe').write_text('1\n')
        if args.observe_apps:
            scripts.update({name: name for name in ['logind-apps.sh', 'launcher-apps.sh', 'launcher-evidence.sh']})
            token = 'ROG5_APPS_DONE_' + uuid.uuid4().hex
            (stage / 'stage/apps-probe').write_text('1\n')
            (stage / 'stage/apps-observe-token').write_text(token+'\n')
            shutil.copyfile(args.evidence_writer, stage / 'stage/evidence-writer')
            (stage / 'stage/evidence-writer').chmod(0o755)
            for name in ['apps-probe', 'apps-observe-token', 'evidence-writer']:
                result['outputs']['stage/'+name] = identity(stage / 'stage' / name)
            if args.bottom_caret:
                (stage / 'stage/bottom-caret-probe').write_text('1\n')
                result['outputs']['stage/bottom-caret-probe'] = identity(stage / 'stage/bottom-caret-probe')
        if args.linker_cache is not None:
            linker_cache_module().stage(args.linker_cache, runtime, receipt, stage/'stage')
            for member in ('linker-cache', 'linker-cache.sha256'):
                result['outputs']['stage/'+member] = identity(stage/'stage'/member)
        if args.settings_sync_diagnostic is not None:
            target = stage_settings_sync_diagnostic(args.settings_sync_diagnostic, stage/'stage')
            result['outputs']['stage/settings-sync-diagnostic.so'] = identity(target)
        for original, staged in scripts.items():
            target = stage / 'stage' / staged
            shutil.copyfile(SOURCES / original, target)
            target.chmod(0o755)
            execute(['bash', '-n', str(target)], output / (staged + '.syntax.log'), 10, result['steps'])
        members = sorted(str(path.relative_to(stage)) for path in stage.rglob('*'))
        archive = output / 'initramfs.cpio'
        with archive.open('xb') as stream:
            execute(['cpio', '--null', '-o', '--quiet', '--format=newc', '--owner=0:0'],
                    output / 'cpio.log', 10, result['steps'], cwd=stage,
                    data=('\0'.join(members) + '\0').encode(), stdout=stream)
        with (output / 'initramfs.gz').open('xb') as stream:
            execute(['gzip', '-n', '-c', str(archive)], output / 'gzip.log', 10, result['steps'], stdout=stream)
        for path in [stage / 'init', output / 'initramfs.gz', *[stage / 'stage' / name for name in scripts.values()]]:
            result['outputs'][str(path.relative_to(output))] = identity(path)
        disk_guard(output)
        name = 'rog5-logind-vm-' + uuid.uuid4().hex[:16]
        command = ['podman', 'run', '--rm', '--name', name, '--pull=never', '--network=none', '--read-only',
                   '--memory=1024m', '--memory-swap=1024m', '--cpus=2', '--pids-limit=64',
                   '-v', f'{runtime}:/runtime:ro', '-v', f'{kernel}:/Image:ro',
                   '-v', f'{output / "initramfs.gz"}:/initramfs.gz:ro', '-v', f'{payload}:/payload:ro', args.qemu_image,
                   'qemu-system-aarch64', '-M', 'virt', '-cpu', 'max', '-smp', '1', '-m', '512M',
                   '-accel', 'tcg,thread='+args.tcg_thread, '-global', 'virtio-mmio.force-legacy=false', '-display', 'none',
                   '-device', 'virtio-gpu-device', '-device', 'virtio-keyboard-device', '-monitor', 'none', '-nic', 'none',
                   '-serial', 'stdio', '-no-reboot', '-kernel', '/Image', '-initrd', '/initramfs.gz',
                   '-append', 'console=ttyAMA0 rdinit=/init panic=-1 rog5.virtual_drm=1 rog5.logind_fixture=1'
                   + (' arm64.nomops' if args.disable_mops else ''),
                   '-fsdev', 'local,id=rootfs,path=/runtime,security_model=mapped-file,readonly=on',
                   '-device', 'virtio-9p-device,fsdev=rootfs,mount_tag=rootfs',
                   '-fsdev', 'local,id=payload,path=/payload,security_model=none,readonly=on',
                   '-device', 'virtio-9p-device,fsdev=payload,mount_tag=payload']
        if combined:
            command[command.index('--memory=1024m')] = '--memory=2048m'
            command[command.index('--memory-swap=1024m')] = '--memory-swap=2048m'
            command[command.index('-m')+1] = '1024M'
            command[command.index('-smp')+1] = '2'
            command[command.index('-display')+1] = 'egl-headless,rendernode=/dev/dri/renderD128'
            command[command.index('virtio-gpu-device')] = 'virtio-gpu-gl-device,xres=540,yres=1224'
            pos = command.index(args.qemu_image)
            command[pos:pos] = ['--security-opt=no-new-privileges', '--device', str(args.host_render_node)+':/dev/dri/renderD128:rw',
                                '-e', 'XDG_CACHE_HOME=/tmp/rog5-qemu-cache']
        if args.observe_editor or args.observe_apps:
            import importlib.util
            filename = 'qemu-logind-apps.py' if args.observe_apps else 'qemu-logind-editor.py'
            spec = importlib.util.spec_from_file_location('logind_observer', REPO/'scripts/host'/filename)
            module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
            observer = session_observer(module, args, output/'observe', name, token)
            pos = command.index(args.qemu_image)
            command[pos:pos] = ['-v', f'{output / "observe"}:/observe:rw']
            command += ['-name', name, '-qmp', 'unix:/observe/qmp.sock,server=on,wait=off',
                        '-vnc', 'unix:/observe/vnc.sock', '-device', 'virtio-tablet-device',
                        '-device', 'virtio-serial-device']
            command += observation_channel(args.observe_apps)
        def finish_observer(error):
            nonlocal observer
            if observer:
                current, observer = observer, None
                result[observation_key] = current.finish(error)
        # Full session:180s boot reserve +260s guest fixture (230s PAM and
        # 30s surrounding work). Keep startup-only/basic limits unchanged.
        # Existing one-shot approved-cleanup grace remains separately bounded.
        container(command, name, output / 'serial.log',
                  (300 if args.startup_only else 440) if combined else 180, result['steps'],
                  poll=observer.tick if observer else None, finalize=finish_observer,
                  cleanup_ready=(lambda: apps_cleanup_ready(observer)) if args.observe_apps else None)
        serial = (output / 'serial.log').read_text(errors='replace')
        # Preserve shutdown/panic evidence even when the requested UI probe failed.
        require_vm_poweroff(serial)
        if (args.observe_editor or args.observe_apps) and result[observation_key]['status'] != 'PASS':
            raise RuntimeError('requested UI observation incomplete or failed')
        if SUCCESS not in serial:
            raise RuntimeError('VM exited without authenticated session/device/scope-removal success evidence')
        if args.startup_only:
            result['rendering'] = {'status': 'NOT RUN', 'reason': 'explicit startup-only mode'}
            result['startup'] = startup_result(serial)
        elif combined:
            import importlib.util
            spec = importlib.util.spec_from_file_location('drm_check', REPO/'scripts/host/test-qemu-virtio-drm.py')
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            result['rendering'] = module.session_result(serial)
            if result['rendering']['status'] != 'PASS' or 'PASS authenticated Denial launcher and native clients stopped' not in serial:
                raise RuntimeError('combined session lacks rendering/client/cleanup proof')
        for path, before in result['inputs'].items():
            if identity(Path(path)) != before:
                raise RuntimeError(f'input changed during run: {path}')
        disk_guard(output)
        result['status'] = 'PASS'
    except Exception as error:
        result['error'] = f'{type(error).__name__}: {error}'
    finally:
        if observer:
            result[observation_key] = observer.finish(result.get('error', 'VM incomplete'))
        result['duration_seconds'] = time.monotonic() - started
        result['ended_utc'] = now()
        for path in output.glob('*.log'):
            result['outputs'][path.name] = identity(path)
        temporary = output / '.result.json.partial'
        with temporary.open('x') as stream:
            json.dump(result, stream, indent=2)
            stream.write('\n')
            stream.flush()
            os.fsync(stream.fileno())
        temporary.rename(output / 'result.json')
    print(json.dumps({'status': result['status'], 'result': str(output / 'result.json'),
                      'duration_seconds': result['duration_seconds'], 'error': result.get('error')}))
    return 0 if result['status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
