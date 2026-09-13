#!/usr/bin/env python3
"""Bounded, offline generic ARM64 DRM guest. Does not qualify phone hardware."""
import argparse
import datetime
import hashlib
import importlib.util
import json
import os
import re
from pathlib import Path
import shutil
import stat
import subprocess
import time
import uuid


def digest(path):
    with path.open('rb') as source:
        return hashlib.file_digest(source, 'sha256').hexdigest()


def missing_runtime_inputs(runtime, shell, mobile=False, editor=False):
    commands = ['bash', 'cat', 'chmod', 'mkdir', 'uname', 'timeout', 'modetest']
    commands += ['seatd', 'sleep', 'Xwayland', 'dbus-daemon'] if shell else []
    paths = ['usr/bin/'+name for name in commands]
    if mobile:
        paths += ['usr/bin/udevadm', 'usr/lib/systemd/systemd-udevd',
                  'usr/lib/udev/rules.d/60-input-id.rules']
    if editor:
        paths += ['usr/bin/mousepad']
    return [path for path in paths if not (runtime/path).is_file()]


def mobile_ready(log):
    text = re.sub(r'\x1b\[[0-?]*[ -/]*[@-~]', '', log.decode(errors='replace'))
    for line in text.splitlines():
        if 'Denial/Volition output scheduler audit' in line:
            values = re.findall(r'\bpresentations=(\d+)\b', line)
            if len(values) == 1 and int(values[0]) > 0:
                return True
    return False


def session_result(log):
    """Interpret actual Denial terminal counters; exit 0 is insufficient."""
    text = re.sub(r'\x1b\[[0-?]*[ -/]*[@-~]', '', log)
    summaries = [line for line in text.splitlines()
                 if 'independently clocked Flutter KMS session complete' in line]
    result = {'status': 'FAIL', 'scope': 'Denial terminal counters; not visual or phone proof'}
    if len(summaries) != 1:
        return dict(result, reason='missing or duplicate terminal session counters')
    counts = {}
    for name in ('raster_frames', 'output_page_flips'):
        values = re.findall(r'\b' + name + r'=(\d+)\b', summaries[0])
        if len(values) != 1:
            return dict(result, reason='missing or duplicate frame count')
        counts[name] = int(values[0])
    errors = [message for message in (
        'required Flutter native fence export failed',
        'Could not create the embedder backing store',
        'Unhandled Exception', 'deniald: fatal error:',
        'could not bind Flutter context for output-target cleanup',
        'Could not make the context current to destroy Impeller surface resources.',
        'Could not clear the context after Impeller surface cleanup.',
        'Could not clear the Impeller IO resource context.',
    ) if message in text]
    result.update(counts, render_errors=errors)
    if all(counts.values()) and not errors:
        result['status'] = 'PASS'
    else:
        result['reason'] = 'zero frames/page flips or observed rendering errors'
    return result


def editor_result(log):
    """Native Wayland key delivery; text appearance needs separate inspection."""
    text = re.sub(r'\x1b\[[0-?]*[ -/]*[@-~]', '', log)
    keys = [(int(key), int(state)) for key, state in re.findall(
        r'wl_keyboard[#@]\d+\.key\(\d+,\s*\d+,\s*(\d+),\s*([01])\)', text)]
    expected = [(key, state) for key in (20, 18, 31, 20, 14, 20) for state in (1, 0)]
    native = all(re.search(pattern, text) for pattern in (
        r'xdg_wm_base[#@]\d+\.get_xdg_surface\(',
        r'xdg_surface[#@]\d+\.get_toplevel\(',
        r'xdg_toplevel[#@]\d+\.set_title\([^\n]*rog5-text-probe\.txt',
    ))
    return {'status': 'PASS' if native and keys == expected else 'FAIL',
            'scope': 'native client Wayland protocol and OSK key lifecycle; visual text checked separately',
            'native_toplevel_observed': native, 'keys': keys, 'expected_keys': expected}


def render_node_identity(path):
    if path.parent != Path('/dev/dri') or not re.fullmatch(r'renderD\d+', path.name):
        raise ValueError('VirGL requires an explicit /dev/dri/renderD* node')
    info = path.lstat()
    if (not stat.S_ISCHR(info.st_mode) or os.major(info.st_rdev) != 226
            or not 128 <= os.minor(info.st_rdev) <= 255):
        raise ValueError('VirGL input is not a DRM render node')
    return {'path': str(path), 'major': os.major(info.st_rdev),
            'minor': os.minor(info.st_rdev), 'scope': 'host rendering only; no phone device'}


def egl_thread_result(log):
    """A completed comparison is not evidence that Denial teardown is fixed."""
    result = {'status': 'FAIL', 'scope': 'standalone virtual EGL thread transfer; not Denial',
              'after_join': {}}
    for mode in ('exit', 'unbind', 'release'):
        if log.count('PASS EGL thread probe mode='+mode) != 1:
            return dict(result, reason='missing or duplicate mode completion')
        collision = re.findall(r'EGL_THREAD mode='+mode+
                               r' stage=live-collision ok=(\d+) error=(0x[0-9a-f]+)', log)
        joined = re.findall(r'EGL_THREAD mode='+mode+
                            r' stage=after-join ok=(\d+) error=(0x[0-9a-f]+)', log)
        if collision != [('0', '0x3002')] or len(joined) != 1:
            return dict(result, reason='missing or inconsistent transfer observation')
        ok, error = joined[0]
        if ((ok, error) not in [('1', '0x3000'), ('0', '0x3002')] or
                (mode != 'exit' and ok != '1')):
            return dict(result, reason='unexpected transfer error')
        result['after_join'][mode] = {'acquired': ok == '1', 'egl_error': error}
    if 'FAIL EGL thread probe' in log:
        return dict(result, reason='probe reported failure')
    return dict(result, status='PASS')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtime', required=True, type=Path)
    parser.add_argument('--kernel', required=True, type=Path)
    program = parser.add_mutually_exclusive_group(required=True)
    program.add_argument('--deniald', type=Path)
    program.add_argument('--egl-thread-probe', type=Path,
                         help='standalone ARM64 EGL transfer comparison; no Denial execution')
    parser.add_argument('--flutter-bundle', type=Path)
    parser.add_argument('--observe-mobile-editor', action='store_true',
                        help='native Wayland Mousepad text probe; requires mobile observation')
    parser.add_argument('--observe-mobile', action='store_true',
                        help='portrait mobile profile, bounded QMP screenshots and OSK pointer gestures')
    parser.add_argument('--render-node', type=Path,
                        help='explicit host DRM render node for virtual VirGL; default uses software')
    parser.add_argument('--image', required=True)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--deadline', type=int, default=120)
    args = parser.parse_args()
    if args.egl_thread_probe and (args.flutter_bundle or not args.render_node):
        parser.error('EGL thread probe requires VirGL and excludes Flutter bundle')
    if args.observe_mobile and (not args.flutter_bundle or not args.render_node):
        parser.error('mobile observation requires Flutter and an explicit VirGL render node')
    if args.observe_mobile_editor and not args.observe_mobile:
        parser.error('native editor probe requires --observe-mobile')
    render_node = render_node_identity(args.render_node) if args.render_node else None
    if not 30 <= args.deadline <= 300:
        parser.error('deadline must be between 30 and 300 seconds')
    if len(args.image) != 64 or any(c not in '0123456789abcdef' for c in args.image):
        parser.error('image must be a retained immutable container ID')
    for tool in ('clang', 'cpio', 'gzip', 'podman'):
        if not shutil.which(tool):
            parser.error(f'BLOCKED missing {tool}')
    runtime = args.runtime.resolve(strict=True)
    kernel = args.kernel.resolve(strict=True)
    executable = (args.egl_thread_probe or args.deniald).resolve(strict=True)
    if not (runtime/'usr/bin/bash').is_file() or runtime == Path('/'):
        parser.error('expected an explicitly materialized guest runtime')
    if not kernel.is_file() or not executable.is_file():
        parser.error('kernel and executable must be regular files')
    output = args.output.absolute()
    output.mkdir(parents=True, exist_ok=False)
    repo = Path(__file__).resolve().parents[2]
    missing = missing_runtime_inputs(runtime, bool(args.flutter_bundle), args.observe_mobile, args.observe_mobile_editor)
    if missing:
        report = {'status': 'BLOCKED', 'scope': 'offline guest prerequisites',
                  'missing_runtime_inputs': missing, 'vm_started': False,
                  'phone_hardware': 'NOT RUN', 'runtime': str(runtime)}
        (output/'result.json').write_text(json.dumps(report, indent=2)+'\n')
        print(json.dumps(report, indent=2))
        return 2
    stage = output/'initramfs'
    for directory in ('dev', 'sysroot', 'stage/payload'):
        (stage/directory).mkdir(parents=True, exist_ok=True)
    payload = output/'payload'
    payload.mkdir()
    shutil.copy2(executable, payload/('egl-thread-probe' if args.egl_thread_probe else 'deniald'))
    if args.flutter_bundle:
        bundle = args.flutter_bundle.resolve(strict=True)
        for required in ('lib/libflutter_engine.so', 'lib/libapp.so', 'data/icudtl.dat'):
            if not (bundle/required).is_file():
                parser.error(f'missing Flutter bundle input: {required}')
        shutil.copytree(bundle, payload/'flutter')
    shutil.copy2(repo/'tools/qemu-virtio-drm/guest.sh', stage/'stage/guest.sh')
    (stage/'stage/graphics-mode').write_text('virgl\n' if render_node else 'software\n')
    if args.observe_mobile:
        (stage/'stage/shell-profile').write_text('mobile\n')
    if args.observe_mobile_editor:
        (stage/'stage/mobile-editor').write_text('mousepad\n')
    compile_command = ['clang', '--target=aarch64-none-elf', '-fuse-ld=lld',
                       '-nostdlib', '-static', '-fno-pic', '-fno-stack-protector',
                       '-Werror', '-Wall', '-Wextra',
                       '-Wl,--build-id=none,--entry=_start',
                       str(repo/'tools/qemu-virtio-drm/init.c'), '-o', str(stage/'init')]
    start = time.monotonic()
    report = {'scope': 'generic ARM64 virtual DRM; phone hardware NOT RUN',
              'started': datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'kernel_sha256': digest(kernel),
              'deniald_sha256': None if args.egl_thread_probe else digest(executable),
              'egl_thread_probe_sha256': digest(executable) if args.egl_thread_probe else None,
              'container': args.image, 'runtime': str(runtime),
              'runtime_inventory_verified_by_this_runner': False,
              'flutter_bundle': str(args.flutter_bundle) if args.flutter_bundle else None,
              'graphics_mode': 'virgl' if render_node else 'software',
              'host_render_node': render_node,
              'harness_sha256': digest(Path(__file__)),
              'init_source_sha256': digest(repo/'tools/qemu-virtio-drm/init.c'),
              'compile_command': compile_command, 'status': 'FAIL'}
    name = 'rog5-virtual-drm-' + uuid.uuid4().hex[:12]
    launched = False
    observer = None
    observer_finalized = False
    observation_error = None
    try:
        if args.observe_mobile:
            observer_path = Path(__file__).with_name('qemu-mobile-observer.py')
            spec = importlib.util.spec_from_file_location('qemu_mobile_observer', observer_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            observer_class = module.EditorObserver if args.observe_mobile_editor else module.MobileObserver
            observer = observer_class(output/'observe', name, capture_backend=module.capture_vnc)
            report['mobile_editor'] = args.observe_mobile_editor
            if args.observe_mobile_editor:
                report['editor_binary_sha256'] = digest(runtime/'usr/bin/mousepad')
            report['observer_sha256'] = digest(observer_path)
            report['shell_profile'] = 'mobile'
        subprocess.run(compile_command, check=True, timeout=30,
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        members = sorted(str(p.relative_to(stage)) for p in stage.rglob('*'))
        archive = subprocess.run(['cpio', '--null', '-o', '--quiet', '--format=newc',
                                  '--owner=0:0'], input=('\0'.join(members)+'\0').encode(),
                                 cwd=stage, capture_output=True, check=True, timeout=10)
        with (output/'initramfs.cpio.gz').open('xb') as packed:
            subprocess.run(['gzip', '-n'], input=archive.stdout, stdout=packed,
                           check=True, timeout=10)
        command = ['podman', 'run', '--rm', '--name', name, '--network', 'none',
                   '--read-only', '--memory', '1536m', '--memory-swap', '1536m',
                   '--cpus', '2', '--pids-limit', '64', '--security-opt', 'no-new-privileges',
                   '-v', str(runtime)+':/runtime:ro',
                   '-v', str(kernel)+':/Image:ro',
                   '-v', str(output/'initramfs.cpio.gz')+':/initramfs.gz:ro',
                   '-v', str(payload)+':/payload:ro', args.image,
                   'qemu-system-aarch64', '-M', 'virt', '-cpu', 'max', '-smp', '2',
                   '-m', '1024M', '-accel', 'tcg,thread=multi',
                   '-global', 'virtio-mmio.force-legacy=false', '-display', 'none',
                   '-monitor', 'none', '-nic', 'none', '-serial', 'stdio', '-no-reboot',
                   '-kernel', '/Image', '-initrd', '/initramfs.gz',
                   '-append', 'console=ttyAMA0 rdinit=/init panic=-1 rog5.virtual_drm=1',
                   '-device', 'virtio-gpu-device,xres=640,yres=480',
                   '-device', 'virtio-keyboard-device', '-device', 'virtio-tablet-device',
                   '-device', 'virtio-rng-device',
                   '-fsdev', 'local,id=rootfs,path=/runtime,security_model=none,readonly=on',
                   '-device', 'virtio-9p-device,fsdev=rootfs,mount_tag=rootfs',
                   '-fsdev', 'local,id=payload,path=/payload,security_model=none,readonly=on',
                   '-device', 'virtio-9p-device,fsdev=payload,mount_tag=payload']
        if render_node:
            index = command.index(args.image)
            command[index:index] = [
                '--device', str(args.render_node)+':'+str(args.render_node)+':rw',
                '-e', 'XDG_CACHE_HOME=/tmp/rog5-qemu-cache']
            command[command.index('-display')+1] = 'egl-headless,rendernode='+str(args.render_node)
            index = command.index('virtio-gpu-device,xres=640,yres=480')
            command[index] = 'virtio-gpu-gl-device,xres=640,yres=480'
        if observer:
            index = command.index(args.image)
            command[index:index] = ['-v', str(output/'observe')+':/observe:rw']
            command += ['-name', name, '-qmp', 'unix:/observe/qmp.sock,server=on,wait=off',
                        '-vnc', 'unix:/observe/vnc.sock']
            index = command.index('virtio-gpu-gl-device,xres=640,yres=480')
            command[index] = 'virtio-gpu-gl-device,xres=540,yres=1224'
        report['command'] = command
        logpath = output/'serial.log'
        with logpath.open('xb') as log:
            launched = True
            with subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT) as process:
                try:
                    end = time.monotonic() + args.deadline
                    while process.poll() is None:
                        if time.monotonic() >= end or logpath.stat().st_size > 8*1024*1024:
                            raise TimeoutError('guest deadline or 8 MiB log bound exceeded')
                        if observer and not observer.complete:
                            with logpath.open('rb') as source:
                                source.seek(max(0, logpath.stat().st_size-131072))
                                ready = mobile_ready(source.read(131072))
                            observer.tick(time.monotonic(), ready)
                        time.sleep(0.2)
                except BaseException as error:
                    observation_error = error
                    raise
                finally:
                    if observer:
                        try:
                            report['mobile_observation'] = observer.finish(observation_error)
                        except Exception as error:
                            report['mobile_observation'] = {'status': 'FAIL', 'error': str(error)}
                        observer_finalized = True
                    if process.poll() is None:
                        subprocess.run(['podman', 'stop', '--time', '2', name],
                                       capture_output=True, timeout=10)
                        try:
                            process.wait(timeout=5)
                        except subprocess.TimeoutExpired:
                            process.kill()
                            process.wait(timeout=5)
                report['qemu_exit_status'] = process.returncode
        log = logpath.read_text(errors='replace')
        report['drm_discovery'] = 'PASS' if 'PASS virtual DRM discovery' in log else 'FAIL'
        report['deniald_kms'] = 'NOT RUN: discovery/CLI are separate from frames'
        report['deniald_cli'] = 'PASS' if 'PASS actual deniald guest CLI' in log else 'NOT RUN'
        if args.egl_thread_probe:
            report['egl_thread_probe'] = egl_thread_result(log)
        if args.flutter_bundle:
            report['deniald_kms'] = 'NOT RUN'
            report['shell_exit'] = 'PASS' if 'PASS actual deniald shell bounded exit' in log else 'FAIL'
            report['shell_rendering'] = session_result(log)
        if args.observe_mobile_editor:
            report['editor_protocol'] = editor_result(log)
        if (process.returncode == 0 and
                report['drm_discovery'] == 'PASS' and
                ((report.get('shell_exit') == 'PASS' and
                  report['shell_rendering']['status'] == 'PASS') or report['deniald_cli'] == 'PASS'
                 or (args.egl_thread_probe and report['egl_thread_probe']['status'] == 'PASS'))
                and 'PASS guest-script exited cleanly' in log and 'FAIL guest-' not in log):
            report['status'] = 'PASS'
    except Exception as error:
        observation_error = error
        report['error'] = str(error)
        if isinstance(error, subprocess.CalledProcessError) and error.stderr:
            report['stderr'] = error.stderr.decode(errors='replace')[-4000:]
    finally:
        if observer and not observer_finalized:
            report['mobile_observation'] = observer.finish(observation_error)
        if report.get('mobile_observation', {}).get('status', 'PASS') != 'PASS':
            report['status'] = 'FAIL'
        if args.observe_mobile_editor and report.get('editor_protocol', {}).get('status') != 'PASS':
            report['status'] = 'FAIL'
        if launched:
            check = subprocess.run(['podman', 'container', 'exists', name], timeout=10)
            report['container_removed'] = check.returncode == 1
            if not report['container_removed']:
                report['status'] = 'FAIL'
        report['duration_seconds'] = time.monotonic() - start
        for path in (stage/'init', stage/'stage/guest.sh', output/'initramfs.cpio.gz',
                     stage/'stage/graphics-mode', stage/'stage/shell-profile', stage/'stage/mobile-editor', output/'serial.log'):
            if path.is_file():
                report.setdefault('hashes', {})[str(path.relative_to(output))] = digest(path)
        (output/'result.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report, indent=2))
    return 0 if report['status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
