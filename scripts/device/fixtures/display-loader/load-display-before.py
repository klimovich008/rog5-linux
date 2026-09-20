"""Fixed REFGEN/panel load and early blank; import-only, admitted target owner.

The caller supplies current full health/monitor authorization, durable one-use
entry, and independent same-boot cleanup ownership. No unload or insertion retry.
Successful insertion is not successful probing, scanout or physical darkness.
"""
import hashlib
import importlib.util
import os
from pathlib import Path
import selectors
import stat
import subprocess
import time

HERE = Path(__file__).resolve().parent
ENDPOINT_SHA = '1c8c173d59a69cc514365844d179813b16d5ae6e7696ecfc9e12ccb999e654ca'
PAYLOAD = Path('/run/rog5-native-wifi')
HELPER = ('module-once', 219912, '744361997ed149b6bae2df502f0d3bcf849de1a3f0bd70f450e8cc82adbac939', 0o755)
MODULES = (('qcom_refgen_regulator', 'qcom-refgen-regulator.ko', 338496, 'a662267d08c1d99b5dd56433502e58acfd1d2e292f230927ad19dcad9921f063'), ('panel_asus_rog5_ams678', 'panel-asus-rog5-ams678.ko', 395528, '7fb9028f9039a574abcc63b9b0539bc972551a6771c0a87726b58f91b2a00aa6'))
INSERT_SECONDS = 5.0
DISCOVERY_SECONDS = 5.0
clock = time.monotonic
pause = time.sleep


def need(ok, why):
    if not ok:
        raise ValueError(why)


path = HERE/'endpoint.py'
need(path.resolve() == path and path.stat().st_size < 16384
     and hashlib.sha256(path.read_bytes()).hexdigest() == ENDPOINT_SHA, 'endpoint source changed')
spec = importlib.util.spec_from_file_location('module_endpoint', path)
E = importlib.util.module_from_spec(spec)
spec.loader.exec_module(E)


def stamp(st):
    return (st.st_dev, st.st_ino, st.st_mode, st.st_uid, st.st_gid,
            st.st_nlink, st.st_size, st.st_mtime_ns, st.st_ctime_ns)


def open_directory(path):
    """Hold each no-symlink directory; root-sticky /run protects root children."""
    need(path.is_absolute() and '..' not in path.parts, 'payload directory path')
    fd = os.open('/', os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    current = Path('/')
    try:
        for part in path.parts[1:]:
            current = current / part
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=fd)
            try:
                st = os.fstat(child)
                named = os.stat(part, dir_fd=fd, follow_symlinks=False)
                mode = stat.S_IMODE(st.st_mode)
                sticky_run = current == Path('/run') and mode == 0o1777
                need(st.st_uid == st.st_gid == 0
                     and (not mode & 0o022 or sticky_run), 'payload directory owner/mode')
                need((st.st_dev, st.st_ino, st.st_mode, st.st_uid, st.st_gid)
                     == (named.st_dev, named.st_ino, named.st_mode, named.st_uid, named.st_gid),
                     'payload directory replaced')
            except Exception:
                os.close(child)
                raise
            os.close(fd)
            fd = child
        result, fd = fd, None
        return result
    finally:
        if fd is not None:
            os.close(fd)


def exact_file(directory, name, size, pin, mode):
    fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC, dir_fd=directory)
    try:
        st = os.fstat(fd)
        need(stat.S_ISREG(st.st_mode) and st.st_uid == st.st_gid == 0
             and st.st_nlink == 1 and st.st_size == size
             and stat.S_IMODE(st.st_mode) == mode, 'payload file metadata: '+name)
        digest = hashlib.sha256()
        total = 0
        while data := os.read(fd, 65536):
            total += len(data)
            need(total <= size, 'payload grew')
            digest.update(data)
        need(total == size and digest.hexdigest() == pin, 'payload digest: '+name)
        need(stamp(st) == stamp(os.fstat(fd))
             == stamp(os.stat(name, dir_fd=directory, follow_symlinks=False)), 'payload replaced: '+name)
        os.lseek(fd, 0, os.SEEK_SET)
        result, fd = fd, None
        return result, stamp(st)
    finally:
        if fd is not None:
            os.close(fd)


def command(helper_fd, directory_fd, filename):
    # module-once rejects a final symlink. Its leaf is an actual regular file
    # below our held directory descriptor, not a /proc/.../fd module symlink.
    return ['/proc/self/fd/'+str(helper_fd), '/proc/self/fd/'+str(directory_fd)+'/'+filename]


def insert(helper_fd, directory_fd, filename, authorize, observe=None):
    start = clock()
    child = None
    streams = {'stdout': bytearray(), 'stderr': bytearray()}
    error = None
    try:
        need(authorize() is True, 'module authorization before spawn')
        child = subprocess.Popen(command(helper_fd, directory_fd, filename), stdin=subprocess.DEVNULL,
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                 pass_fds=(helper_fd, directory_fd),
                                 env={'PATH': '/usr/bin:/bin', 'LC_ALL': 'C'})
        with selectors.DefaultSelector() as selector:
            for name in streams:
                stream = getattr(child, name)
                os.set_blocking(stream.fileno(), False)
                selector.register(stream, selectors.EVENT_READ, name)
            deadline = start+INSERT_SECONDS
            while selector.get_map() or child.poll() is None:
                if observe is not None:
                    observe()
                need(clock() < deadline, 'module insertion deadline')
                need(authorize() is True, 'module authorization during insertion')
                for key, _ in selector.select(min(.05, max(0, deadline-clock()))):
                    data = os.read(key.fd, 4097)
                    if not data:
                        selector.unregister(key.fileobj)
                    else:
                        need(len(streams[key.data])+len(data) <= 4096, 'module output bound')
                        streams[key.data].extend(data)
            child.wait(timeout=max(.001, deadline-clock()))
            need(child.returncode == 0 and not any(streams.values()), 'module insertion exit/output')
    except Exception as exc:
        error = dict(type=type(exc).__name__, reason=str(exc)[:512])
    finally:
        if child is not None:
            try:
                if child.poll() is None:
                    child.kill()
                child.wait(timeout=2)
            except Exception as exc:
                error = dict(type=type(exc).__name__, reason='module child cleanup: '+str(exc)[:400], prior=error)
            finally:
                for name in streams:
                    getattr(child, name).close()
    return dict(status='PASS_INSERTION' if error is None else 'FAIL_INSERTION',
                filename=filename, seconds=clock()-start, pid=child.pid if child else None,
                returncode=child.returncode if child else None,
                reaped=child is not None and child.poll() is not None,
                stdout=bytes(streams['stdout']).decode(errors='replace'),
                stderr=bytes(streams['stderr']).decode(errors='replace'), error=error,
                retry_allowed=False)


def refgen(boot):
    E.identity(boot)
    device = E.SYS/'bus/platform/devices/88e7000.regulator'
    need((device/'driver').resolve(strict=True) == E.SYS/'bus/platform/drivers/qcom-refgen-regulator',
         'REFGEN driver not bound')
    need((E.SYS/'module/qcom_refgen_regulator').is_dir(), 'REFGEN module missing')
    names = []
    for entry in (E.SYS/'class/regulator').iterdir():
        need(len(names) < 256, 'regulator inventory bound')
        names.append(entry)
    matches = [p for p in names if E.read(p/'name', 128) == b'refgen\n']
    need(len(matches) == 1, 'REFGEN regulator count')
    return dict(driver='qcom-refgen-regulator', regulator=str(matches[0]))


class LoadError(ValueError):
    def __init__(self, evidence):
        super().__init__('OLED module load failed: '+str(evidence))
        self.evidence = evidence


class Loader:
    def __init__(self):
        self.attempted = False

    def load_once(self, boot, authorize, enter, cleanup_authorize):
        """enter must durably reserve both insertions once before returning True.

        All callbacks are bounded, preinstalled and nonblocking. The outer owner
        enforces full health, boot-capture closure and persistent attempt guards.
        A new Python object does not grant permission to retry a entered load.
        """
        start = clock()
        fds = []
        rows = []
        entered = panel_attempted = False
        blank = cleanup_blank = binding = endpoint = error = None
        cleanup_errors = []
        try:
            need(not self.attempted, 'module load object already attempted')
            need(all(callable(f) for f in (authorize, enter, cleanup_authorize)), 'module callbacks required')
            identity = E.identity(boot)
            need(authorize() is True and cleanup_authorize() is True, 'module ownership/health required')
            for name, *_ in MODULES:
                need(not os.path.lexists(E.SYS/'module'/name), 'display module already present')
            need(not list((E.SYS/'class/backlight').iterdir())
                 and not os.path.lexists(E.SYS/'class/graphics/fb0'), 'display unexpectedly active before load')
            parent = open_directory(PAYLOAD)
            fds.append(parent)
            modules = open_directory(PAYLOAD/'display-trial')
            fds.append(modules)
            helper, helper_metadata = exact_file(parent, *HELPER)
            fds.append(helper)
            inventory = []
            for name, filename, size, pin in MODULES:
                fd, metadata = exact_file(modules, filename, size, pin, 0o644)
                fds.append(fd)
                inventory.append(dict(module=name, filename=filename, bytes=size, sha256=pin,
                                      descriptor=fd, metadata=metadata))
            self.attempted = True
            intent = dict(identity=identity, modules=[{k:v for k,v in r.items() if k not in ('descriptor','metadata')}
                                                     for r in inventory], helper_sha256=HELPER[2],
                          maximum_insertions=2, per_module_seconds=INSERT_SECONDS, cleanup_brightness=0)
            need(enter(intent) is True, 'durable module entry not acknowledged')
            entered = True
            for index, row in enumerate(inventory):
                need(E.identity(boot) == identity and authorize() is True, 'module identity/health changed')
                need(stamp(os.fstat(helper)) == helper_metadata
                     == stamp(os.stat(HELPER[0], dir_fd=parent, follow_symlinks=False)), 'module helper changed')
                need(stamp(os.fstat(row['descriptor'])) == row['metadata']
                     == stamp(os.stat(row['filename'], dir_fd=modules, follow_symlinks=False)), 'module file changed')
                if index:
                    binding = refgen(boot)
                    panel_attempted = True
                def observe_panel():
                    nonlocal blank
                    if blank is None and os.path.lexists(E.SYS/'class/backlight'/E.NAME):
                        blank = E.blank(boot, cleanup_authorize)
                result = insert(helper, modules, row['filename'], authorize,
                                observe_panel if index else None)
                rows.append(result)
                # Cleanup runs even if a panel insertion has uncertain outcome.
                if index:
                    deadline = clock()+DISCOVERY_SECONDS
                    while blank is None:
                        observe_panel()
                        if blank is not None:
                            break
                        E.identity(boot)
                        need(cleanup_authorize() is True, 'module cleanup ownership lost')
                        need(clock() < deadline, 'panel backlight discovery deadline')
                        pause(.05)
                need(result['status'] == 'PASS_INSERTION' and result['reaped'], 'module insertion failed; no retry')
                need((E.SYS/'module'/row['module']).is_dir(), 'inserted module absent')
            need(authorize() is True, 'module post-load health/monitor lost')
            binding = refgen(boot)
            deadline = clock()+DISCOVERY_SECONDS
            while not os.path.lexists(E.SYS/'class/graphics/fb0'):
                E.identity(boot)
                need(authorize() is True and clock() < deadline, 'framebuffer discovery deadline/health')
                need(E.backlight(boot)['brightness'] == 0, 'post-load blank state changed')
                pause(.05)
            endpoint = E.framebuffer(boot)
        except Exception as exc:
            error = dict(type=type(exc).__name__, reason=str(exc)[:1000])
        finally:
            if panel_attempted and (blank is None or error is not None):
                try:
                    cleanup_blank = E.blank(boot, cleanup_authorize)
                except Exception as exc:
                    cleanup_errors.append(dict(stage='early-blank', type=type(exc).__name__, reason=str(exc)[:512]))
            for fd in reversed(fds):
                try:
                    os.close(fd)
                except OSError as exc:
                    cleanup_errors.append(dict(stage='close', reason=str(exc)[:512]))
        result = dict(status='PASS_MODULES_AND_BLANK' if error is None and not cleanup_errors else 'FAIL_MODULE_LOAD',
                      seconds=clock()-start, entered=entered, panel_attempted=panel_attempted,
                      insertions=rows, refgen=binding, blank=blank, cleanup_blank=cleanup_blank, endpoint=endpoint,
                      error=error, cleanup_errors=cleanup_errors, retry_allowed=False,
                      physical_scanout_verified=False, physical_darkness_verified=False,
                      full_health_verified=False, admission_granted=False)
        if result['status'] != 'PASS_MODULES_AND_BLANK':
            raise LoadError(result)
        return result


if __name__ == '__main__':
    raise SystemExit('Import-only: requires admitted target owner, full health and independent blank cleanup')
