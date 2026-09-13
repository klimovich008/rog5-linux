#!/usr/bin/env python3
"""Audit actual ARM64 loader closure inside a read-only, device-free runtime root."""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import signal
import stat
import subprocess
import time

REPO = Path(__file__).resolve().parents[2]
PROFILE = REPO / 'configs/denial/mobile-runtime-linkage.json'
LIMIT = 512 * 1024


def identity(path):
    with path.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    return {'path': str(path), 'sha256': digest, 'size': path.stat().st_size}


class Runtime:
    def __init__(self, root, rows):
        self.root = root
        self.rows = {row['path']: row for row in rows}
        if len(self.rows) != len(rows):
            raise ValueError('duplicate runtime manifest path')
        self.verified = {}

    def resolve(self, name):
        if not name.startswith('/'):
            raise ValueError('runtime name must be absolute')
        todo = list(PurePosixPath(name).parts[1:]); done = []; links = 0
        while todo:
            part = todo.pop(0)
            if part in ('', '.'):
                continue
            if part == '..':
                if not done:
                    raise ValueError('runtime path escapes root')
                done.pop(); continue
            key = '/'.join([*done, part]); path = self.root / key
            row = self.rows.get(key)
            if row is None:
                raise ValueError('unregistered runtime path: '+key)
            st = path.lstat()
            if row['type'] == 'symlink':
                if not stat.S_ISLNK(st.st_mode) or os.readlink(path) != row['target']:
                    raise ValueError('runtime link changed: '+key)
                links += 1
                if links > 40:
                    raise ValueError('runtime symlink loop')
                target = PurePosixPath(row['target'])
                if target.is_absolute():
                    done = []; target = target.relative_to('/')
                todo = [*target.parts, *todo]
            else:
                expected = stat.S_ISDIR if row['type'] == 'directory' else stat.S_ISREG
                if not expected(st.st_mode):
                    raise ValueError('runtime type changed: '+key)
                done.append(part)
                if todo and row['type'] != 'directory':
                    raise ValueError('non-directory runtime parent')
        key = '/'.join(done); row = self.rows.get(key)
        if not row or row['type'] != 'file':
            raise ValueError('runtime object is not a registered file')
        found = identity(self.root/key)
        if found['sha256'] != row['sha256'] or found['size'] != row['size']:
            raise ValueError('runtime bytes changed: '+key)
        self.verified[key] = found
        return self.root/key


def parse_receipt(text, library, symbols):
    lines = text.splitlines()
    prefix = ['LIBRARY '+library, *['SYMBOL '+s for s in symbols]]
    if lines[:len(prefix)] != prefix or not lines or lines[-1] != 'RESULT PASS_LINKAGE_ONLY':
        raise ValueError('incomplete or unexpected linkage receipt')
    rows = lines[len(prefix):-1]
    if not rows or len(rows) > 128 or any(not r.startswith('OBJECT ') for r in rows):
        raise ValueError('invalid loaded-object inventory')
    names = [r[7:] for r in rows]
    if len(names) != len(set(names)) or any(not re.fullmatch(r'[A-Za-z0-9_./+\-]+', n) for n in names):
        raise ValueError('invalid loaded-object names')
    return names


def bounded(command, output, label):
    unit = "rog5-linkage-"+hashlib.sha256(str(output).encode()).hexdigest()[:12]+"-"+label
    command = [*command[:1], "--unit="+unit, *command[1:]]
    path = output/(label+'.log'); started = time.monotonic(); failure = None
    process = None; original_error = None; cleanup_errors = []; service_state = None
    def cleanup_error(stage, error):
        nonlocal original_error
        cleanup_errors.append(stage+': '+str(error))
        if original_error is None and not isinstance(error, (OSError, subprocess.SubprocessError)):
            original_error = error
    with path.open('xb') as log:
        try:
            process = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
            while process.poll() is None:
                if path.stat().st_size > LIMIT or time.monotonic()-started > 45:
                    failure = 'log limit or deadline'; break
                time.sleep(.02)
        except BaseException as error:
            original_error = error
        finally:
            # systemd-run is only a client. Always stop the independently owned
            # service, including observation errors and operator interruption.
            # A client wait/kill error must not bypass service cleanup either.
            if process is not None:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                except BaseException as error:
                    cleanup_error('client kill', error)
                try:
                    process.wait(timeout=10)
                except BaseException as error:
                    cleanup_error('client wait', error)
            try:
                subprocess.run(['systemctl','--user','stop',unit], capture_output=True, timeout=10)
            except BaseException as error:
                cleanup_error('service stop', error)
            try:
                state = subprocess.run(['systemctl','--user','is-active',unit], capture_output=True, text=True, timeout=10)
                service_state = state.stdout.strip()
                if state.returncode not in (3, 4) or service_state not in ('inactive','failed','unknown'):
                    cleanup_errors.append('service shutdown could not be confirmed')
            except BaseException as error:
                cleanup_error('service state', error)
    if original_error is not None:
        if cleanup_errors:
            original_error.add_note('Probe cleanup: '+'; '.join(cleanup_errors))
        raise original_error
    if cleanup_errors:
        failure = '; '.join(([failure] if failure else [])+cleanup_errors)
    if path.stat().st_size > LIMIT:
        failure = 'log limit exceeded' + ('; '+failure if failure else '')
    result = {'command': command, 'unit': unit, 'exit_status': process.returncode,
              'seconds': time.monotonic()-started, 'log': identity(path),
              'service_state': service_state, 'cleanup': 'FAIL' if cleanup_errors else 'PASS'}
    if failure:
        result['failure'] = failure
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('root','tree','bundle','native','probe','output'):
        p.add_argument('--'+name, type=Path, required=True)
    p.add_argument('--tree-sha256', required=True)
    a = p.parse_args(); a.output.mkdir(parents=True, exist_ok=False)
    report = {'status': 'FAIL', 'scope': __doc__, 'authority': 'none', 'phone': 'NOT RUN',
              'graphics_initialization': 'NOT RUN', 'runs': []}
    interrupted = False
    try:
        for name in ('bwrap','qemu-aarch64-static','systemd-run'):
            if shutil.which(name) is None:
                report['status'] = 'BLOCKED'; raise ValueError('missing required tool: '+name)
        for path in (a.root,a.bundle,a.native,a.probe,a.tree):
            if path != path.resolve():
                raise ValueError('input must be canonical: '+str(path))
        tree = identity(a.tree)
        if tree['sha256'] != a.tree_sha256:
            raise ValueError('runtime tree identity mismatch')
        runtime = Runtime(a.root, json.loads(a.tree.read_text()))
        profile = json.loads(PROFILE.read_text())
        local = {'/tmp/deniald': a.native, '/tmp/linkage-probe': a.probe,
                 '/tmp/flutter/lib/libflutter_engine.so': a.bundle/'lib/libflutter_engine.so',
                 '/tmp/flutter/lib/libapp.so': a.bundle/'lib/libapp.so'}
        if any(path != path.resolve() or not path.is_file() for path in local.values()):
            raise ValueError('bound ELF input must be a canonical regular file')
        originals = {key: identity(path) for key,path in local.items()}
        report.update(profile=identity(PROFILE), tree=tree, inputs=originals,
                      root=str(a.root), bundle=str(a.bundle), tools={n:identity(Path(shutil.which(n)).resolve()) for n in ('bwrap','qemu-aarch64-static','systemd-run')})
        def verify(name):
            if name == 'linux-vdso.so.1':
                return # Kernel-provided virtual object, not a package file.
            path = local.get(name)
            if path is not None:
                if identity(path) != originals[name]:
                    raise ValueError('bound input changed: '+name)
            else:
                path = runtime.resolve(name)
            with path.open('rb') as stream:
                header = stream.read(20)
            if len(header)<20 or header[:6] != b'\x7fELF\x02\x01' or int.from_bytes(header[18:20],'little') != 183:
                raise ValueError('object is not little-endian ELF64 AArch64: '+name)
        loader = '/usr/lib/ld-linux-aarch64.so.1'; verify(loader)
        for key in local:
            verify(key)
        descriptors = []
        for row in profile['driver_descriptors']:
            path = runtime.resolve(row['path']); data = json.loads(path.read_text())
            if data['ICD']['library_path'] != row['library_path']:
                raise ValueError('driver descriptor target differs')
            descriptors.append(identity(path))
        report['driver_descriptors'] = descriptors
        base = ['systemd-run','--user','--quiet','--wait','--pipe','--collect',
                '-p','MemoryMax=512M','-p','MemorySwapMax=0','-p','TasksMax=64',
                '-p','CPUQuota=100%','-p','RuntimeMaxSec=35s',
                'bwrap','--unshare-all','--die-with-parent','--cap-drop','ALL',
                '--ro-bind',str(a.root),'/', '--dev','/dev','--proc','/proc','--tmpfs','/tmp',
                '--ro-bind',str(Path(shutil.which('qemu-aarch64-static')).resolve()),'/tmp/qemu',
                '--ro-bind',str(a.native),'/tmp/deniald','--ro-bind',str(a.probe),'/tmp/linkage-probe',
                '--ro-bind',str(a.bundle),'/tmp/flutter','--clearenv','--setenv','HOME','/tmp',
                '--setenv','LC_ALL','C','--setenv','LD_BIND_NOW','1',
                '--setenv','LD_LIBRARY_PATH','/tmp/flutter/lib:/usr/lib','--','/tmp/qemu']
        targets = [('executable', name, []) for name in profile['executables']]
        targets += [('library', row['path'], row['symbols']) for row in profile['libraries']]
        for i,(kind,name,symbols) in enumerate(targets):
            verify(name)
            command = base + ([loader,'--list',name] if kind=='executable' else ['/tmp/linkage-probe',name,*symbols])
            row = bounded(command,a.output,f'{i:02d}'); row.update(kind=kind,target=name,status='FAIL')
            report['runs'].append(row)
            if row['exit_status'] or 'failure' in row:
                raise ValueError('loader refused '+name)
            text = Path(row['log']['path']).read_text()
            if kind == 'library':
                names = parse_receipt(text,name,symbols)
            else:
                names=[]
                for line in text.splitlines():
                    match = re.fullmatch(r'\s*(?:\S+ => )?(/\S+) \(0x[0-9a-f]+\)\s*',line)
                    if match: names.append(match[1])
                    elif not re.fullmatch(r'\s*linux-vdso.so.1 \(0x[0-9a-f]+\)\s*',line):
                        raise ValueError('unexpected loader listing')
                if not names: raise ValueError('empty loader closure')
            for name in names: verify(name)
            row.update(status='PASS',loaded_objects=names)
        # Verify again after all loader runs; input changes cannot receive PASS.
        for name in local: verify(name)
        for key in list(runtime.verified): runtime.resolve('/'+key)
        report.update(status='PASS_LINKAGE_ONLY',runtime_files=list(runtime.verified.values()))
    except (OSError,ValueError,KeyError,subprocess.SubprocessError,KeyboardInterrupt) as error:
        if report['status'] != 'BLOCKED':
            report['status'] = 'FAIL'
        report['error'] = str(error)
        report['error_notes'] = list(getattr(error, '__notes__', []))
        interrupted = isinstance(error, KeyboardInterrupt)
    (a.output/'result.json').write_text(json.dumps(report,indent=2)+'\n')
    print(report['status'], report.get('error',''))
    if interrupted:
        return 130
    return 0 if report['status']=='PASS_LINKAGE_ONLY' else 2 if report['status']=='BLOCKED' else 1


if __name__ == '__main__':
    raise SystemExit(main())
