"""Linux-only, single-threaded command ownership for this one host harness.

Not a repository-wide executor. No pre-existing children, SIGCHLD reaper,
threads, or concurrent users are permitted. Children are created only here.
PR_SET_CHILD_SUBREAPER is the same Linux prctl used by the supplied regression.
"""
from contextlib import contextmanager
import ctypes
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import shutil


class InfrastructureError(RuntimeError):
    pass


class Cancelled(InfrastructureError):
    pass


def children():
    """Direct children, including adopted orphans; never names or saved PIDs."""
    path = Path(f'/proc/self/task/{os.getpid()}/children')
    try:
        return [int(pid) for pid in path.read_text().split()]
    except FileNotFoundError:
        # Some host kernels omit task/children. Read-only PPID discovery is
        # equivalent for this one-thread owner; exited() validates waitability
        # again before signalling. Unrelated /proc entries are never signalled.
        found = []
        for item in Path('/proc').iterdir():
            if not item.name.isdigit():
                continue
            try:
                fields = (item / 'stat').read_text().rsplit(')', 1)[1].split()
                if int(fields[1]) == os.getpid():
                    found.append(int(item.name))
            except (FileNotFoundError, ProcessLookupError):
                continue
        return found


def exited(pid):
    # Also establishes that pid is still our waitable child. WNOWAIT reserves
    # its identity; no poll(), wait(), SIGCHLD handler or other thread reaps it.
    return os.waitid(os.P_PID, pid, os.WEXITED | os.WNOHANG | os.WNOWAIT)


def no_children():
    """Authoritative drain proof, not a potentially stale /proc inventory."""
    try:
        os.waitid(os.P_ALL, 0, os.WEXITED | os.WNOHANG | os.WNOWAIT)
    except ChildProcessError:
        return True
    return False


class OwnedCommands:
    CLEANUP_SECONDS = 2.0

    def __init__(self):
        self.cancelled = 0
        self.dirty = False
        self.handlers = {}

    def _interrupt(self, signum, frame):
        # Never raise out of Popen, registration, wait, or filesystem cleanup.
        # Repeated cancellation cannot interrupt reaping or replace first cause.
        if not self.cancelled:
            self.cancelled = signum

    def checkpoint(self):
        if self.cancelled:
            raise Cancelled(f'cancelled by signal {self.cancelled} (not a mutation kill)')

    def __enter__(self):
        if len(list(Path('/proc/self/task').iterdir())) != 1 or not no_children():
            raise InfrastructureError('command owner requires one thread and no existing children')
        if signal.getsignal(signal.SIGCHLD) != signal.SIG_DFL:
            raise InfrastructureError('command owner requires default SIGCHLD (no competing reaper)')
        libc = ctypes.CDLL(None, use_errno=True)
        if libc.prctl(36, 1, 0, 0, 0) != 0:  # PR_SET_CHILD_SUBREAPER
            raise OSError(ctypes.get_errno(), 'PR_SET_CHILD_SUBREAPER')
        for sig in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP):
            self.handlers[sig] = signal.signal(sig, self._interrupt)
        return self

    def __exit__(self, kind, value, tb):
        try:
            if not no_children():
                self._cleanup(None)
            if kind is None:
                self.checkpoint()
        finally:
            for sig, old in self.handlers.items():
                signal.signal(sig, old)
        # A first signal can be latched while its old handler is restored.
        # Once restoration finishes, it must still turn normal exit into failure.
        if kind is None:
            self.checkpoint()
        return False

    def _signal_child(self, pid):
        exited(pid)  # ChildProcessError fails closed before any signal.
        if os.getpgid(pid) == pid:
            # The unreaped child reserves this PGID until AFTER the signal.
            # Never signal a saved group ID after its leader has been reaped.
            os.killpg(pid, signal.SIGKILL)
        else:
            # An adopted descendant may have changed groups/sessions. It is
            # still our unreaped child; do not signal its unowned group ID.
            os.kill(pid, signal.SIGKILL)

    def _cleanup(self, proc):
        """Kill first; reap every adopted descendant; reap command leader last."""
        end = time.monotonic() + self.CLEANUP_SECONDS
        leader = proc.pid if proc is not None else None
        try:
            while True:
                owned = children()
                if not owned and no_children():
                    return
                for pid in owned:
                    self._signal_child(pid)
                for pid in owned:
                    if pid != leader and exited(pid) is not None:
                        os.waitpid(pid, 0)
                # Adoption can expose further generations, including setsid
                # descendants. Keep draining; never use waitpid(-1) or pid names.
                # Observe exit BEFORE taking a fresh inventory: exit itself
                # can adopt descendants after the previous /proc snapshot.
                if leader is not None and exited(leader) is not None and children() == [leader]:
                    proc.wait()  # Never signal this PID/PGID again.
                    proc = None
                    leader = None
                    continue  # Confirm kernel ECHILD even after leader reap.
                if time.monotonic() >= end:
                    raise InfrastructureError('owned children did not drain within 2 seconds')
                time.sleep(.005)
        except BaseException as error:
            self.dirty = True
            print('FAIL infrastructure: owned cleanup: ' + repr(error),
                  file=sys.stderr, flush=True)
            raise

    def _await(self, proc, end):
        while True:
            self.checkpoint()
            if time.monotonic() >= end:
                raise InfrastructureError('command timeout (not a mutation kill)')
            info = exited(proc.pid)
            if info is not None:
                if any(pid != proc.pid for pid in children()):
                    raise InfrastructureError('background descendants (not a mutation kill)')
                return info.si_status if info.si_code == os.CLD_EXITED else -info.si_status
            time.sleep(.005)

    def run(self, argv, stream, env, limit):
        self.checkpoint()
        if self.dirty or not no_children():
            raise InfrastructureError('previous command ownership not clean')
        proc = None
        end = time.monotonic() + limit
        try:
            # Handlers only latch: cancellation between creation and assignment
            # cannot strand a successfully launched child. A constructor error
            # is covered by the finally's adopted/direct-child drain as well.
            proc = subprocess.Popen(argv, stdout=stream, stderr=subprocess.STDOUT,
                                    env=env, start_new_session=True)
            returncode = self._await(proc, end)
        finally:
            self._cleanup(proc)
        self.checkpoint()  # A signal arriving during cleanup must not yield PASS.
        return returncode

    @contextmanager
    def scratch(self, parent):
        self.checkpoint()
        path = Path(tempfile.mkdtemp(prefix='fts3658u-input-core-', dir=parent))
        try:
            yield path
        finally:
            # No TemporaryDirectory finalizer: failure to prove drain retains
            # scratch rather than deleting files underneath a surviving child.
            if self.dirty or not no_children():
                print('FAIL infrastructure: scratch retained: ' + str(path),
                      file=sys.stderr, flush=True)
                raise InfrastructureError('scratch not removed: ownership drain unproven')
            shutil.rmtree(path)
