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
import uuid

REPO = Path(__file__).resolve().parents[2]
SOURCES = REPO / 'tools/qemu-virtio-drm'
RESERVE = 3 * 1024**3
LOG_LIMIT = 8 * 1024**2
SUCCESS = 'PASS authenticated local logind session, mediated devices and removed scope'
INTERRUPTS = {signal.SIGINT, signal.SIGTERM}


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


def execute(command, log, deadline, steps, *, cwd=None, data=None, stdout=None, accepted=(0,)):
    """Own a process group and bound output, wall time, and descendant lifetime."""
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
                child.communicate(input=data, timeout=deadline)
            except subprocess.TimeoutExpired:
                row['status'] = 'FAIL_TIMEOUT'
                raise RuntimeError(f'command exceeded {deadline}s: {command[0]}')
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


def container(command, name, log, deadline, steps):
    """Only the uniquely named container created by this invocation is cleaned."""
    original = None
    try:
        execute(command, log, deadline, steps)
    except BaseException as error:
        original = error
    finally:
        cleanup_error = None
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


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('runtime-view', 'runtime-receipt', 'kernel', 'qemu-image', 'toolchain-image', 'libc', 'libloading', 'output'):
        parser.add_argument('--' + name, required=True)
    args = parser.parse_args()
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
    output.mkdir(mode=0o700)
    result = {'status': 'FAIL', 'authority': 'none', 'physical_status': 'NOT RUN',
              'scope': 'generic ARM64 systemd PID1, original PAM login profile, local logind and mediated virtual devices',
              'started_utc': now(), 'command': [sys.executable, str(Path(__file__).resolve()), *sys.argv[1:]],
              'steps': [], 'inputs': {}, 'outputs': {},
              'runtime_limit': 'Runtime receipt identity is bound; complete runtime inventory/authentication is a prior external prerequisite, not rerun here.'}
    started = time.monotonic()
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
        result['runtime_view'] = str(runtime)
        result['container_images'] = {'qemu': args.qemu_image, 'toolchain': args.toolchain_image}
        for key, command in [('commit', ['rev-parse', 'HEAD']), ('tree', ['rev-parse', 'HEAD^{tree}']),
                             ('worktree_status', ['status', '--porcelain=v1'])]:
            result.setdefault('source', {})[key] = subprocess.check_output(['git', '-C', str(REPO), *command], text=True, timeout=10).strip()
        result['source']['dirty'] = bool(result['source']['worktree_status'])
        kernel, libc, libloading = map(regular, (args.kernel, args.libc, args.libloading))
        source_names = ['init.c', 'logind-seat-probe.rs', 'logind-pam-session.rs',
                        'logind-boot.sh', 'logind-session.sh', 'logind-user.sh', 'logind-observer.sh']
        input_files = [regular(SOURCES / name) for name in source_names] + [kernel, libc, libloading, receipt, Path(__file__).resolve()]
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
        payload.mkdir()
        stage = output / 'initramfs'
        for directory in ('dev', 'sysroot', 'stage/payload'):
            (stage / directory).mkdir(parents=True, exist_ok=True)
        for source_name, binary_name in [('logind-seat-probe.rs', 'logind-seat-probe'), ('logind-pam-session.rs', 'pam-session')]:
            disk_guard(output)
            source = output / source_name
            shutil.copyfile(SOURCES / source_name, source)
            name = 'rog5-logind-build-' + uuid.uuid4().hex[:16]
            rust = ['/opt/denial-rust/bin/rustc', '--edition=2024', '--target=aarch64-unknown-linux-gnu',
                    '--crate-name=' + binary_name.replace('-', '_'), '-Dwarnings', '-C', 'linker=/usr/bin/aarch64-linux-gnu-gcc',
                    '-C', 'opt-level=2', '-C', 'lto=thin', '-C', 'codegen-units=1', '-C', 'strip=debuginfo',
                    '--remap-path-prefix', str(output) + '=/logind-fixture', str(source), '-o', str(payload / binary_name),
                    '--extern', 'libc=' + str(libc), '--extern', 'libloading=' + str(libloading)]
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
                   'logind-user.sh': 'logind-user.sh', 'logind-observer.sh': 'independent-observer.sh'}
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
                   '--memory=768m', '--memory-swap=768m', '--cpus=2', '--pids-limit=64',
                   '-v', f'{runtime}:/runtime:ro', '-v', f'{kernel}:/Image:ro',
                   '-v', f'{output / "initramfs.gz"}:/initramfs.gz:ro', '-v', f'{payload}:/payload:ro', args.qemu_image,
                   'qemu-system-aarch64', '-M', 'virt', '-cpu', 'max', '-smp', '1', '-m', '512M',
                   '-accel', 'tcg,thread=multi', '-global', 'virtio-mmio.force-legacy=false', '-display', 'none',
                   '-device', 'virtio-gpu-device', '-device', 'virtio-keyboard-device', '-monitor', 'none', '-nic', 'none',
                   '-serial', 'stdio', '-no-reboot', '-kernel', '/Image', '-initrd', '/initramfs.gz',
                   '-append', 'console=ttyAMA0 rdinit=/init panic=-1 rog5.virtual_drm=1 rog5.logind_fixture=1',
                   '-fsdev', 'local,id=rootfs,path=/runtime,security_model=mapped-file,readonly=on',
                   '-device', 'virtio-9p-device,fsdev=rootfs,mount_tag=rootfs',
                   '-fsdev', 'local,id=payload,path=/payload,security_model=none,readonly=on',
                   '-device', 'virtio-9p-device,fsdev=payload,mount_tag=payload']
        container(command, name, output / 'serial.log', 180, result['steps'])
        serial = (output / 'serial.log').read_text(errors='replace')
        if SUCCESS not in serial:
            raise RuntimeError('VM exited without authenticated session/device/scope-removal success evidence')
        for path, before in result['inputs'].items():
            if identity(Path(path)) != before:
                raise RuntimeError(f'input changed during run: {path}')
        disk_guard(output)
        result['status'] = 'PASS'
    except Exception as error:
        result['error'] = f'{type(error).__name__}: {error}'
    finally:
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
