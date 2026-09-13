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


def missing_runtime_inputs(runtime, shell, mobile=False, editor=False, native=False, launcher=False, nonroot=False):
    commands = ['bash', 'cat', 'chmod', 'mkdir', 'uname', 'timeout', 'modetest']
    commands += ['seatd', 'sleep', 'Xwayland', 'dbus-daemon'] if shell else []
    paths = ['usr/bin/'+name for name in commands]
    if mobile:
        paths += ['usr/bin/udevadm', 'usr/lib/systemd/systemd-udevd',
                  'usr/lib/udev/rules.d/60-input-id.rules']
    if editor or launcher:
        paths += ['usr/bin/'+name for name in ('mousepad', 'mkfifo', 'sed', 'cp',
                    'sha256sum', 'glib-compile-schemas', 'update-mime-database')]
        paths += ['usr/share/glib-2.0/schemas/org.xfce.mousepad.gschema.xml',
                  'usr/share/mime/packages/freedesktop.org.xml']
    if launcher:
        paths += ['usr/bin/'+name for name in ('foot', 'awk', 'env')]
        paths += ['usr/share/applications/foot.desktop',
                  'usr/share/applications/org.xfce.mousepad.desktop']
    if native:
        paths += ['usr/bin/mv', 'usr/lib/libwayland-client.so.0']
    if nonroot:
        paths += ['usr/bin/'+name for name in ('setpriv', 'mount', 'chown')]
        paths += ['etc/passwd', 'etc/group']
    return [path for path in paths if not (runtime/path).is_file()]


def link_payload_file(source, destination):
    """Explicit disk-saving fixture mode; never alter shared inode permissions."""
    if not stat.S_ISREG(os.lstat(source).st_mode):
        raise ValueError('linked payload requires regular non-symlink files')
    os.link(source, destination, follow_symlinks=False)
    return destination


def reject_payload_links(directory, names):
    for name in names:
        if (Path(directory)/name).is_symlink():
            raise ValueError('linked payload excludes symlinks, including directory links')
    return []


def nonroot_result(serial, protocol):
    expected = 'uid=1000 gid=1000 groups=none caps=zero nnp=1'
    roles = {}
    for role, text in [('bus', serial), ('denial', serial),
                       ('mousepad', protocol), ('foot', protocol)]:
        lines = [line for line in text.splitlines() if line.startswith('OBSERVE nonroot exec='+role+' ')]
        roles[role] = len(lines) == 1 and lines[0] == 'OBSERVE nonroot exec='+role+' '+expected
    return {'status': 'PASS' if all(roles.values()) else 'FAIL', 'exec_paths': roles,
            'scope': 'VM UID1000 exec paths, empty groups/capabilities and NoNewPrivs; '
                     'seatd fixture, not logind/login/lock-screen or phone qualification'}


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


class EditorProtocol:
    """Bounded, attributed client protocol state; never infer mapping from a title alone."""
    PREFIX = 'EDITOR_WAYLAND '
    LINE_LIMIT = 16384
    LOG_LIMIT = 8 * 1024 * 1024

    def __init__(self):
        self.pending = b''
        self.total = self.offset = 0
        self.surfaces = {}
        self.toplevels = {}
        self.focus = {}
        self.keys = []
        self.bad_keys = False
        self.mapped = False
        self.ever_mapped = False
        self.interval_seen = False
        self.ready = False

    def feed(self, data):
        self.total += len(data)
        if self.total > self.LOG_LIMIT:
            raise ValueError('editor protocol exceeds serial log bound')
        parts = (self.pending + data).split(b'\n')
        self.pending = parts.pop()
        if any(len(line) > self.LINE_LIMIT for line in [*parts, self.pending]):
            raise ValueError('editor protocol line exceeds 16 KiB bound')
        for line in parts:
            self.line(re.sub(r'\x1b\[[0-?]*[ -/]*[@-~]', '', line.decode(errors='replace')))

    def read_available(self, path):
        if path.stat().st_size < self.offset:
            raise ValueError('editor serial log truncated')
        with path.open('rb') as source:
            source.seek(self.offset)
            block = source.read(131072)
        self.offset += len(block)
        self.feed(block)
        return self.ready

    def line(self, line):
        if not line.startswith(self.PREFIX):
            if self.mapped and 'Denial/Volition output scheduler audit' in line:
                values = re.findall(r'\bpresentations=(\d+)\b', line)
                if len(values) == 1:
                    # These are interval counts, not cumulative counters. The
                    # first audit can straddle commit; require a later interval.
                    if self.interval_seen and int(values[0]) > 0:
                        self.ready = True
                    self.interval_seen = True
            return
        line = line[len(self.PREFIX):]
        match = re.search(r'(-> )?([a-z_]+)[#@](\d+)\.([a-z_]+)\((.*)\)\s*$', line)
        if not match:
            return
        outgoing, interface, object_id, method, args = match.groups()
        if interface == 'xdg_wm_base' and method == 'get_xdg_surface' and outgoing:
            linked = re.fullmatch(r'new id xdg_surface[#@](\d+), wl_surface[#@](\d+)', args)
            if linked:
                xdg, surface = linked.groups()
                if len(self.surfaces) >= 64:
                    raise ValueError('editor surface bound exceeded')
                self.surfaces[xdg] = dict(surface=surface, title=False, configured=False,
                                          serial=None, ack=False, pending_attach=None, committed=False)
        elif interface == 'xdg_surface' and object_id in self.surfaces:
            state = self.surfaces[object_id]
            if method == 'get_toplevel' and outgoing:
                linked = re.fullmatch(r'new id xdg_toplevel[#@](\d+)', args)
                if linked:
                    self.toplevels[linked[1]] = object_id
                    if len(self.toplevels) > 64:
                        raise ValueError('editor toplevel bound exceeded')
            elif method == 'configure' and not outgoing and args.isdecimal():
                state.update(serial=args if state['configured'] else None, ack=False)
            elif method == 'ack_configure' and outgoing:
                state['ack'] = state['configured'] and args == state['serial']
            elif method == 'destroy' and outgoing:
                state.update(title=False, committed=False)
        elif interface == 'xdg_toplevel' and object_id in self.toplevels:
            state = self.surfaces[self.toplevels[object_id]]
            if method == 'set_title' and outgoing:
                state['title'] = bool(re.fullmatch(r'"\*?(?:/tmp/)?rog5-text-probe\.txt(?: - Mousepad)?"', args))
            elif method == 'configure' and not outgoing:
                state['configured'] = bool(re.fullmatch(r'\d+, \d+, array\[\d+\]', args))
            elif method == 'destroy' and outgoing:
                state.update(title=False, committed=False)
        elif interface == 'wl_surface' and outgoing:
            for state in self.surfaces.values():
                if state['surface'] != object_id:
                    continue
                if method == 'attach':
                    state['pending_attach'] = bool(state['ack'] and re.fullmatch(
                        r'wl_buffer[#@]\d+, -?\d+, -?\d+', args))
                elif method == 'commit':
                    # No attach retains current contents. An explicit NULL
                    # attach changes contents only when that state is committed.
                    if state['pending_attach'] is not None:
                        state['committed'] = state['title'] and state['pending_attach']
                        state['pending_attach'] = None
                elif method == 'destroy':
                    state.update(title=False, committed=False)
        elif interface == 'wl_keyboard' and not outgoing:
            if method == 'enter':
                focused = re.fullmatch(r'\d+, wl_surface[#@](\d+), array\[\d+\]', args)
                if focused:
                    self.focus[object_id] = focused[1]
                    if len(self.focus) > 64:
                        raise ValueError('editor keyboard bound exceeded')
            elif method == 'leave':
                self.focus.pop(object_id, None)
            elif method == 'key':
                key = re.fullmatch(r'\d+, \d+, (\d+), ([01])', args)
                if key:
                    focused = any(state['committed'] and state['title'] and
                                  state['surface'] == self.focus.get(object_id)
                                  for state in self.surfaces.values())
                    self.bad_keys |= not focused
                    if len(self.keys) >= 64:
                        raise ValueError('editor key event bound exceeded')
                    self.keys.append(tuple(map(int, key.groups())))
        active = any(state['committed'] and state['title'] for state in self.surfaces.values())
        if active != self.mapped:
            self.ready = self.interval_seen = False
        self.mapped = active
        self.ever_mapped |= active

    def result(self):
        expected = [(key, state) for key in (20, 18, 31, 20, 14, 20) for state in (1, 0)]
        native = self.ever_mapped
        return {'status': 'PASS' if native and not self.bad_keys and self.keys == expected else 'FAIL',
                'scope': 'native client Wayland protocol and OSK key lifecycle; visual text checked separately',
                'native_toplevel_observed': native, 'keys': self.keys, 'expected_keys': expected,
                'unfocused_keys': self.bad_keys}


def editor_result(log):
    """Use the same attributed parser for readiness and final key evidence."""
    parser = EditorProtocol()
    data = log.encode()
    for offset in range(0, len(data), 131072):
        parser.feed(data[offset:offset+131072])
    if parser.pending:
        parser.feed(b'\n')
    return parser.result()


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


def launcher_discovery_result(log):
    lines = log.splitlines()
    prepared = lines.count('PASS launcher desktop overrides prepared; apps NOT STARTED') == 1
    cleaned = lines.count('PASS launcher apps cleanup') == 1
    unexpected = any('OBSERVE launcher app=' in line or 'FAIL launcher' in line for line in lines)
    return {'status': 'PASS' if prepared and cleaned and not unexpected else 'FAIL',
            'prepared': prepared, 'cleanup': cleaned,
            'unexpected_app_or_failure': unexpected, 'app_launch_and_switch': 'NOT RUN'}


def observer_poll_delay(observer, now):
    """Honor the scripted action clock without busy polling or extending bounds."""
    if observer is None or observer.complete or observer.client is None:
        return .2
    return min(.2, max(.01, observer.next_at-now))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtime', required=True, type=Path)
    parser.add_argument('--runtime-security-model', choices=('none', 'mapped-file'), default='none')
    parser.add_argument('--non-root-session', action='store_true',
                        help='UID1000 seatd VM fixture; requires mapped-file runtime and app observation')
    parser.add_argument('--link-payload', action='store_true',
                        help='hardlink regular immutable fixture files; changes source nlink/ctime, never permissions')
    parser.add_argument('--kernel', required=True, type=Path)
    program = parser.add_mutually_exclusive_group(required=True)
    program.add_argument('--deniald', type=Path)
    program.add_argument('--egl-thread-probe', type=Path,
                         help='standalone ARM64 EGL transfer comparison; no Denial execution')
    parser.add_argument('--flutter-bundle', type=Path)
    parser.add_argument('--observe-mobile-editor', action='store_true',
                        help='native Wayland Mousepad text probe; requires mobile observation')
    parser.add_argument('--observe-mobile-launcher', action='store_true',
                        help='unlocked launcher discovery captures; app interaction NOT RUN')
    parser.add_argument('--observe-mobile-apps', action='store_true',
                        help='launch/switch native apps; requires inspected launcher reference')
    parser.add_argument('--observe-mobile-apps-text', action='store_true',
                        help='OSK text probe during launcher-based two-app flow')
    parser.add_argument('--launcher-reference', type=Path)
    parser.add_argument('--evidence-writer', type=Path, help='ARM64 bounded record writer; required for app observation')
    parser.add_argument('--trace-focus', action='store_true',
                        help='opt-in bounded shell/native focus diagnostics; requires app observation')
    parser.add_argument('--native-screencopy', type=Path,
                        help='ARM64 native capture client; pair initial/final editor VNC captures')
    parser.add_argument('--observe-mobile', action='store_true',
                        help='portrait mobile profile, bounded QMP screenshots and OSK pointer gestures')
    parser.add_argument('--render-node', type=Path,
                        help='explicit host DRM render node for virtual VirGL; default uses software')
    parser.add_argument('--image', required=True)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--deadline', type=int, default=120)
    args = parser.parse_args()
    if args.non_root_session and (not args.observe_mobile_apps or args.native_screencopy
                                  or args.runtime_security_model != 'mapped-file'):
        parser.error('non-root session requires app observation and mapped-file runtime; excludes native capture')
    if args.observe_mobile_apps_text and not args.observe_mobile_apps:
        parser.error('launcher text observation requires --observe-mobile-apps')
    if args.trace_focus and not args.observe_mobile_apps:
        parser.error('focus tracing requires --observe-mobile-apps')
    if args.egl_thread_probe and (args.flutter_bundle or not args.render_node):
        parser.error('EGL thread probe requires VirGL and excludes Flutter bundle')
    if args.observe_mobile and (not args.flutter_bundle or not args.render_node):
        parser.error('mobile observation requires Flutter and an explicit VirGL render node')
    if args.observe_mobile_editor and not args.observe_mobile:
        parser.error('native editor probe requires --observe-mobile')
    if args.observe_mobile_launcher and (not args.observe_mobile or args.observe_mobile_editor):
        parser.error('launcher discovery requires mobile and excludes editor autolaunch')
    if args.observe_mobile_apps and (not args.observe_mobile or args.observe_mobile_editor
                                    or args.observe_mobile_launcher or not args.launcher_reference):
        parser.error('app interaction requires mobile/reference and excludes editor/discovery')
    if args.launcher_reference and not args.observe_mobile_apps:
        parser.error('launcher reference is only used for app interaction')
    if bool(args.evidence_writer) != bool(args.observe_mobile_apps):
        parser.error('app interaction requires --evidence-writer; other modes exclude it')
    launcher = args.observe_mobile_launcher or args.observe_mobile_apps
    if args.native_screencopy and not args.observe_mobile_editor:
        parser.error('native screencopy requires editor observation')
    render_node = render_node_identity(args.render_node) if args.render_node else None
    if not 30 <= args.deadline <= 300:
        parser.error('deadline must be between 30 and 300 seconds')
    if len(args.image) != 64 or any(c not in '0123456789abcdef' for c in args.image):
        parser.error('image must be a retained immutable container ID')
    for tool in ('clang', 'cpio', 'gzip', 'podman'):
        if not shutil.which(tool):
            parser.error(f'BLOCKED missing {tool}')
    if args.link_payload and ((args.egl_thread_probe or args.deniald).is_symlink()
                              or (args.flutter_bundle and args.flutter_bundle.is_symlink())):
        parser.error('linked payload excludes symlink executable/bundle inputs')
    runtime = args.runtime.resolve(strict=True)
    kernel = args.kernel.resolve(strict=True)
    executable = (args.egl_thread_probe or args.deniald).resolve(strict=True)
    if not (runtime/'usr/bin/bash').is_file() or runtime == Path('/'):
        parser.error('expected an explicitly materialized guest runtime')
    if not kernel.is_file() or not executable.is_file():
        parser.error('kernel and executable must be regular files')
    if args.evidence_writer:
        with args.evidence_writer.open('rb') as source:
            header = source.read(20)
        if header[:6] != b'\x7fELF\x02\x01' or header[18:20] != b'\xb7\x00':
            parser.error('evidence writer must be little-endian ARM64 ELF')
    output = args.output.absolute()
    output.mkdir(parents=True, exist_ok=False)
    repo = Path(__file__).resolve().parents[2]
    missing = missing_runtime_inputs(runtime, bool(args.flutter_bundle), args.observe_mobile,
                                     args.observe_mobile_editor, bool(args.native_screencopy), launcher, args.non_root_session)
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
    payload_copy = link_payload_file if args.link_payload else shutil.copy2
    payload_copy(executable, payload/('egl-thread-probe' if args.egl_thread_probe else 'deniald'))
    if args.native_screencopy:
        shutil.copy2(args.native_screencopy.resolve(strict=True), payload/'screencopy')
        (stage/'stage/native-capture').mkdir()
        (stage/'stage/native-capture-enabled').write_text('1\n')
        shutil.copy2(repo/'tools/qemu-virtio-drm/native-capture.sh', stage/'stage/native-capture.sh')
    if args.flutter_bundle:
        bundle = args.flutter_bundle.resolve(strict=True)
        for required in ('lib/libflutter_engine.so', 'lib/libapp.so', 'data/icudtl.dat'):
            if not (bundle/required).is_file():
                parser.error(f'missing Flutter bundle input: {required}')
        shutil.copytree(bundle, payload/'flutter', copy_function=payload_copy,
                        ignore=reject_payload_links if args.link_payload else None)
    shutil.copy2(repo/'tools/qemu-virtio-drm/guest.sh', stage/'stage/guest.sh')
    if args.non_root_session:
        (stage/'stage/nonroot-session').write_text('1\n')
        shutil.copy2(repo/'tools/qemu-virtio-drm/nonroot-session.sh', stage/'stage/nonroot-session.sh')
    (stage/'stage/graphics-mode').write_text('virgl\n' if render_node else 'software\n')
    if args.trace_focus:
        (stage/'stage/focus-trace').write_text('1\n')
    if args.observe_mobile:
        (stage/'stage/shell-profile').write_text('mobile\n')
    if args.observe_mobile_editor:
        (stage/'stage/mobile-editor').write_text('mousepad\n')
    if launcher:
        (stage/'stage/mobile-launcher').write_text('apps\n' if args.observe_mobile_apps else 'discover\n')
        shutil.copy2(repo/'tools/qemu-virtio-drm/launcher-apps.sh', stage/'stage/launcher-apps.sh')
    protocol_path_output = None
    if args.observe_mobile_apps:
        shutil.copy2(args.evidence_writer, stage/'stage/evidence-writer')
        shutil.copy2(repo/'tools/qemu-virtio-drm/launcher-evidence.sh', stage/'stage/launcher-evidence.sh')
        (output/'protocol').mkdir(mode=0o700)
        protocol_path_output = output/'protocol/events.log'
        protocol_path_output.touch(mode=0o600, exist_ok=False)
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
              'runtime_security_model': args.runtime_security_model,
              'non_root_session_requested': args.non_root_session,
              'payload_hardlinks': args.link_payload,
              'payload_files': {str(path.relative_to(payload)): {
                  'sha256': digest(path), 'bytes': path.stat().st_size,
                  'mode': oct(stat.S_IMODE(path.stat().st_mode))}
                  for path in sorted(payload.rglob('*')) if path.is_file()},
              'flutter_bundle': str(args.flutter_bundle) if args.flutter_bundle else None,
              'graphics_mode': 'virgl' if render_node else 'software',
              'host_render_node': render_node,
              'harness_sha256': digest(Path(__file__)),
              'init_source_sha256': digest(repo/'tools/qemu-virtio-drm/init.c'),
              'compile_command': compile_command, 'status': 'FAIL'}
    name = 'rog5-virtual-drm-' + uuid.uuid4().hex[:12]
    launched = False
    observer = None
    native_capture = None
    editor_readiness = EditorProtocol() if args.observe_mobile_editor else None
    launcher_protocol = None
    observer_finalized = False
    observation_error = None
    try:
        if args.observe_mobile:
            observer_path = Path(__file__).with_name('qemu-mobile-observer.py')
            spec = importlib.util.spec_from_file_location('qemu_mobile_observer', observer_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            observer_class = module.EditorObserver if args.observe_mobile_editor else module.MobileObserver
            if args.observe_mobile_launcher:
                observer_class = module.LauncherObserver
            observer_options = {}
            if args.observe_mobile_apps:
                protocol_path = Path(__file__).with_name('qemu-launcher-protocol.py')
                protocol_spec = importlib.util.spec_from_file_location('qemu_launcher_protocol', protocol_path)
                protocol_module = importlib.util.module_from_spec(protocol_spec)
                protocol_spec.loader.exec_module(protocol_module)
                launcher_protocol = protocol_module.LauncherProtocol()
                observer_class = module.AppTextObserver if args.observe_mobile_apps_text else module.AppSwitchObserver
                observer_options = dict(protocol=launcher_protocol, reference=args.launcher_reference)
                report['launcher_protocol_sha256'] = digest(protocol_path)
                report['app_binary_hashes'] = {app: digest(runtime/'usr/bin'/app) for app in ('foot', 'mousepad')}
            backend = module.capture_vnc
            if args.native_screencopy:
                native_path = Path(__file__).with_name('qemu-native-capture.py')
                native_spec = importlib.util.spec_from_file_location('qemu_native_capture', native_path)
                native_module = importlib.util.module_from_spec(native_spec)
                native_spec.loader.exec_module(native_module)
                native_capture = native_module.NativeCapture(output/'native', backend, module.png_identity)
                backend = native_capture
                report['native_capture_inputs'] = {'client_sha256': digest(payload/'screencopy'),
                    'host_sha256': digest(native_path), 'worker_sha256': digest(stage/'stage/native-capture.sh')}
            observer = observer_class(output/'observe', name, capture_backend=backend, **observer_options)
            report['mobile_editor'] = args.observe_mobile_editor
            report['mobile_launcher'] = args.observe_mobile_launcher
            report['mobile_apps'] = args.observe_mobile_apps
            report['mobile_apps_text'] = args.observe_mobile_apps_text
            if launcher:
                report['launcher_apps_sha256'] = digest(stage/'stage/launcher-apps.sh')
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
                   '-fsdev', 'local,id=rootfs,path=/runtime,security_model='+args.runtime_security_model+',readonly=on',
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
        if protocol_path_output:
            index = command.index(args.image)
            command[index:index] = ['-v', str(output/'protocol')+':/protocol:rw']
            command += ['-device', 'virtio-serial-device',
                        '-chardev', 'file,id=protocol,path=/protocol/events.log',
                        '-device', 'virtserialport,chardev=protocol,name=rog5.launcher,nr=1']
            report['protocol_transport'] = {'scope': 'dedicated virtual serial; bounded atomic FIFO records',
                'writer_sha256': digest(stage/'stage/evidence-writer'),
                'setup_sha256': digest(stage/'stage/launcher-evidence.sh'), 'limit_bytes': 3*1024*1024}
        if native_capture:
            index = command.index(args.image)
            command[index:index] = ['-v', str(output/'native')+':/native:rw']
            command += ['-fsdev', 'local,id=capture,path=/native,security_model=none',
                        '-device', 'virtio-9p-device,fsdev=capture,mount_tag=capture']
        report['command'] = command
        logpath = output/'serial.log'
        with logpath.open('xb') as log:
            launched = True
            with subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT) as process:
                try:
                    end = time.monotonic() + args.deadline
                    while process.poll() is None:
                        if native_capture:
                            native_capture.check_bound()
                        if time.monotonic() >= end or logpath.stat().st_size > 8*1024*1024:
                            raise TimeoutError('guest deadline or 8 MiB log bound exceeded')
                        if launcher_protocol:
                            if protocol_path_output.stat().st_size > 3*1024*1024:
                                raise ValueError("launcher evidence exceeds 3 MiB bound")
                            launcher_protocol.read_available(protocol_path_output)
                            if launcher_protocol.errors:
                                raise ValueError("launcher protocol rejected: "+str(launcher_protocol.errors))
                        if observer and not observer.complete:
                            if editor_readiness:
                                ready = editor_readiness.read_available(logpath)
                            else:
                                with logpath.open('rb') as source:
                                    source.seek(max(0, logpath.stat().st_size-131072))
                                    ready = mobile_ready(source.read(131072))
                            observer.tick(time.monotonic(), ready)
                        time.sleep(observer_poll_delay(observer, time.monotonic()))
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
        if args.observe_mobile_launcher:
            report['launcher_discovery'] = launcher_discovery_result(log)
        if args.observe_mobile_apps:
            final_protocol = protocol_module.LauncherProtocol()
            if protocol_path_output.stat().st_size > 3*1024*1024:
                raise ValueError("launcher evidence exceeds 3 MiB bound")
            data = protocol_path_output.read_bytes()
            for offset in range(0, len(data), 131072):
                final_protocol.feed(data[offset:offset+131072])
            if final_protocol.pending:
                final_protocol.fail('truncated final protocol record')
            if not final_protocol.terminal:
                final_protocol.fail('missing dedicated terminal boundary')
            report['launcher_protocol'] = final_protocol.result()
            if args.non_root_session:
                report['non_root_session'] = nonroot_result(log, data.decode(errors='replace'))
            if args.observe_mobile_apps_text:
                report['launcher_text_protocol'] = editor_result(data.decode(errors='replace'))
            report['launcher_apps_cleanup'] = 'PASS' if log.splitlines().count('PASS launcher apps cleanup') == 1 else 'FAIL'
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
        if launcher_protocol and 'launcher_protocol' not in report:
            report['launcher_protocol'] = launcher_protocol.result()
        if observer and not observer_finalized:
            report['mobile_observation'] = observer.finish(observation_error)
        if report.get('mobile_observation', {}).get('status', 'PASS') != 'PASS':
            report['status'] = 'FAIL'
        if args.observe_mobile_editor and report.get('editor_protocol', {}).get('status') != 'PASS':
            report['status'] = 'FAIL'
        if args.observe_mobile_launcher and report.get('launcher_discovery', {}).get('status') != 'PASS':
            report['status'] = 'FAIL'
        if args.observe_mobile_apps_text and report.get('launcher_text_protocol', {}).get('status') != 'PASS':
            report['status'] = 'FAIL'
        if args.observe_mobile_apps and (report.get('launcher_protocol', {}).get('status') != 'PASS'
                or report.get('launcher_apps_cleanup') != 'PASS'):
            report['status'] = 'FAIL'
        if args.non_root_session and report.get('non_root_session', {}).get('status') != 'PASS':
            report['status'] = 'FAIL'
        if native_capture:
            report['native_capture'] = {'records': native_capture.records,
                'status': 'PASS' if len(native_capture.records) == 2 else 'FAIL',
                'scope': 'capture transport only; inspect visual content independently'}
            if len(native_capture.records) != 2:
                report['status'] = 'FAIL'
        if launched:
            check = subprocess.run(['podman', 'container', 'exists', name], timeout=10)
            report['container_removed'] = check.returncode == 1
            if not report['container_removed']:
                report['status'] = 'FAIL'
        report['duration_seconds'] = time.monotonic() - start
        for path in (stage/'init', stage/'stage/guest.sh', output/'initramfs.cpio.gz',
                     stage/'stage/graphics-mode', stage/'stage/nonroot-session', stage/'stage/nonroot-session.sh', stage/'stage/focus-trace', stage/'stage/shell-profile', stage/'stage/mobile-editor', stage/'stage/mobile-launcher',
                     stage/'stage/launcher-apps.sh', stage/'stage/evidence-writer', stage/'stage/launcher-evidence.sh', output/'protocol/events.log', output/'serial.log'):
            if path.is_file():
                report.setdefault('hashes', {})[str(path.relative_to(output))] = digest(path)
        (output/'result.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report, indent=2))
    return 0 if report['status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
