#!/usr/bin/env python3
"""Live authenticated-VM editor observation; no phone or keyboard injection."""
import importlib.util
import json
from pathlib import Path
import stat
import time


def load_sibling(name, filename):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(filename))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


PROTOCOL = load_sibling('logind_editor_protocol', 'test-qemu-virtio-drm.py')
MOBILE = load_sibling('logind_editor_mobile', 'qemu-mobile-observer.py')


class LiveEditor:
    """Consume one raw virtserial writer and retain both independent oracles.

    The guest launches Mousepad after Foot closes normally. A titled, committed
    editor must retain keyboard focus for 1.5 seconds before pointer actions.
    This uses focus/commit evidence, not scheduler audit timing. The coordinator
    owns VM deadlines; tick never waits for input or starts a process.
    """
    LOG_LIMIT = 1024 * 1024
    STABLE_SECONDS = 1.5

    def __init__(self, directory, name, *, client_factory=MOBILE.QMP,
                 capture_backend=MOBILE.capture_vnc):
        self.observer = MOBILE.EditorObserver(directory, name, client_factory,
                                              capture_backend)
        self.directory = self.observer.directory
        self.log_path = self.directory / 'editor.log'
        self.parser = PROTOCOL.EditorProtocol()
        self.offset = 0
        self.pending = b''
        self.identity = None
        self.focus = None
        self.focus_since = None
        self.error = None
        self.result = None

    @property
    def complete(self):
        return (not self.error and self.observer.complete
                and self.parser.result()['status'] == 'PASS')

    def focused_editor(self):
        committed = {state['surface'] for state in self.parser.surfaces.values()
                     if state['committed'] and state['title']}
        focused = set(self.parser.focus.values())
        if self.parser.mapped and len(focused) == 1 and focused <= committed:
            return tuple(sorted(self.parser.focus.items()))
        return None

    def update_focus(self, now):
        current = self.focused_editor()
        if self.observer.client is not None and not self.observer.complete:
            if current is None or current != self.focus:
                raise ValueError('editor focus lost during pointer observation')
        if current != self.focus:
            self.focus, self.focus_since = current, now if current is not None else None

    def read_available(self, now):
        try:
            metadata = self.log_path.lstat()
        except FileNotFoundError:
            if self.identity is not None:
                raise ValueError('editor serial log disappeared')
            return
        if not stat.S_ISREG(metadata.st_mode):
            raise ValueError('editor serial log must be a regular non-symlink file')
        identity = (metadata.st_dev, metadata.st_ino)
        if self.identity is not None and identity != self.identity:
            raise ValueError('editor serial log replaced')
        self.identity = identity
        if metadata.st_size < self.offset:
            raise ValueError('editor serial log truncated')
        if metadata.st_size > self.LOG_LIMIT:
            raise ValueError('editor serial log exceeds 1 MiB bound')
        # Drain the bounded snapshot before readiness; a later queued leave
        # must not be hidden behind an earlier ready event or a read chunk.
        remaining = metadata.st_size - self.offset
        with self.log_path.open('rb') as source:
            source.seek(self.offset)
            while remaining:
                block = source.read(min(131072, remaining))
                if not block:
                    raise ValueError('editor serial log truncated while reading')
                self.offset += len(block)
                remaining -= len(block)
                lines = (self.pending + block).split(b'\n')
                self.pending = lines.pop()
                if any(len(line) > self.parser.LINE_LIMIT for line in [*lines, self.pending]):
                    raise ValueError('editor protocol line exceeds 16 KiB bound')
                for line in lines:
                    self.parser.feed(line + b'\n')
                    # Inspect each event, including a leave and re-enter within
                    # the same host poll, rather than just its final state.
                    self.update_focus(now)

    def tick(self, now=None):
        if self.result is not None:
            return self.complete
        if self.error:
            raise ValueError(self.error)
        now = time.monotonic() if now is None else now
        try:
            self.read_available(now)
            ready = (self.focus_since is not None
                     and now - self.focus_since >= self.STABLE_SECONDS)
            self.observer.tick(now, ready)
        except Exception as exception:
            self.error = str(exception)
            raise
        return self.complete

    def finish(self, error=None):
        if self.result is not None:
            return self.result
        try:
            self.read_available(time.monotonic())
            if self.pending:
                raise ValueError('editor serial log ended with an incomplete line')
        except Exception as exception:
            self.error = self.error or str(exception)
        observation = self.observer.finish(error or self.error)
        protocol = self.parser.result()
        failure = error or self.error
        if not failure and (observation['status'] != 'PASS' or protocol['status'] != 'PASS'):
            failure = 'editor observation or protocol incomplete'
        self.result = {'status': 'FAIL' if failure else 'PASS',
                       'scope': 'authenticated VM pointer-only OSK and native editor protocol',
                       'phone_touch': 'NOT RUN', 'observation': observation,
                       'protocol': protocol, 'stream_bytes': self.offset,
                       'stable_focus_seconds_required': self.STABLE_SECONDS}
        if failure:
            self.result['error'] = str(failure)
        (self.directory / 'editor-result.json').write_text(json.dumps(self.result, indent=2) + '\n')
        return self.result
