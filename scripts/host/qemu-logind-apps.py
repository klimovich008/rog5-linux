#!/usr/bin/env python3
"""Authenticated VM launcher/app/text observation and bounded completion handshake."""
import errno
import json
import os
from pathlib import Path
import re
import socket
import stat
import time

import importlib.util
SPEC = importlib.util.spec_from_file_location('apps_editor_base', Path(__file__).with_name('qemu-logind-editor.py'))
BASE = importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(BASE)
LAUNCHER = BASE.load_sibling('apps_launcher_protocol', 'qemu-launcher-protocol.py')


class AppProtocols:
    LINE_LIMIT = BASE.PROTOCOL.EditorProtocol.LINE_LIMIT

    def __init__(self, owner):
        self.owner = owner
        self.launcher = LAUNCHER.LauncherProtocol()
        self.editor = BASE.PROTOCOL.EditorProtocol()

    def feed(self, line):
        owner = self.owner
        if line == b'OBSERVE authenticated launcher flow-ready\n':
            if owner.ready or self.launcher.owners:
                raise ValueError('duplicate or late launcher readiness')
            owner.ready = True
        elif line == b'OBSERVE authenticated launcher teardown\n':
            if not owner.ack_sent or owner.teardown:
                raise ValueError('unapproved or duplicate launcher teardown')
            owner.teardown = True
            self.launcher.terminal = True
        else:
            if b'independently clocked Flutter KMS session complete' in line:
                raise ValueError('compositor terminal record belongs to separate serial oracle')
            self.launcher.feed(line)
            if not owner.teardown:
                self.editor.feed(line)
        if self.launcher.errors:
            raise ValueError('; '.join(self.launcher.errors))

    def result(self):
        return {'status': 'PASS' if self.launcher.result()['status'] == 'PASS'
                and self.editor.result()['status'] == 'PASS' else 'FAIL'}


class LiveApps(BASE.LiveEditor):
    """Reuse the strict file reader; one socket and one file writer own events.

    An exact DONE token is sent only after both production protocol oracles and
    the fixed UI action/capture sequence pass. Guest cleanup has a distinct
    approved boundary; genuine compositor counters remain in the serial oracle.
    """
    def __init__(self, directory, name, token, reference, *,
                 automatic_caret=False, client_factory=BASE.MOBILE.TextQMP, capture_backend=BASE.MOBILE.capture_vnc):
        if not re.fullmatch(r'ROG5_APPS_DONE_[0-9a-f]{32}', token):
            raise ValueError('invalid exact observation token')
        self.ready = self.teardown = self.ack_sent = self.peer_closed = False
        self.parser = AppProtocols(self)
        observer_class = (BASE.MOBILE.AutomaticCaretAppTextObserver if automatic_caret
                          else BASE.MOBILE.AppTextObserver)
        self.observer = observer_class(directory, name,
            protocol=self.parser.launcher, reference=reference,
            client_factory=client_factory, capture_backend=capture_backend)
        self.directory = self.observer.directory
        self.log_path = self.directory/'apps.log'
        self.stream = self.log_path.open('xb')
        os.fchmod(self.stream.fileno(), 0o600)
        self.transport = None
        self.socket_identity = None
        self.offset = 0
        self.pending = b''
        self.identity = None
        self.error = self.result = None
        self.token = (token+'\n').encode()
        self.sent = 0

    @property
    def complete(self):
        return not self.error and self.ack_sent and self.observer.complete and self.parser.result()['status'] == 'PASS'

    def update_focus(self, now):
        # Evaluate every event, including transient loss within one poll. Other
        # app stages intentionally change focus; the OSK stage must not.
        if not self.observer.complete and self.observer.STEPS[self.observer.stage][0] == 'editor':
            if not self.parser.launcher.focused('mousepad'):
                raise ValueError('editor focus lost during launcher OSK observation')

    def receive(self):
        path = self.directory/'apps.sock'
        if self.transport is None:
            try:
                metadata = path.lstat()
            except FileNotFoundError:
                return
            if not stat.S_ISSOCK(metadata.st_mode):
                raise ValueError('application endpoint must be a non-symlink socket')
            current = (metadata.st_dev, metadata.st_ino)
            if self.socket_identity is not None and current != self.socket_identity:
                raise ValueError('application endpoint replaced')
            self.socket_identity = current
            client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            client.setblocking(False)
            try:
                client.connect(str(path))
            except OSError as error:
                client.close()
                if error.errno in (errno.ENOENT, errno.ECONNREFUSED):
                    return
                raise
            self.transport = client
        if self.peer_closed:
            return
        while True:
            try:
                block = self.transport.recv(131072)
            except BlockingIOError:
                break
            if not block:
                self.peer_closed = True
                break
            if self.stream.tell()+len(block) > self.LOG_LIMIT:
                raise ValueError('application serial log exceeds 1 MiB bound')
            self.stream.write(block)
            self.stream.flush()

    def tick(self, now=None):
        if self.result is not None:
            return self.complete
        if self.error:
            raise ValueError(self.error)
        now = time.monotonic() if now is None else now
        try:
            self.receive()
            self.read_available(now)
            if self.peer_closed and not self.teardown:
                raise ValueError('application transport closed before approved teardown')
            self.observer.tick(now, self.ready)
            if (self.observer.complete and self.parser.result()['status'] == 'PASS'
                    and not self.ack_sent and not self.pending):
                try:
                    self.sent += self.transport.send(self.token[self.sent:])
                except BlockingIOError:
                    pass
                self.ack_sent = self.sent == len(self.token)
        except Exception as error:
            self.error = str(error)
            raise
        return self.complete

    def finish(self, error=None):
        if self.result is not None:
            return self.result
        try:
            self.receive()
            self.read_available(time.monotonic())
            if self.pending:
                raise ValueError('application stream ended with an incomplete line')
        except Exception as exception:
            self.error = self.error or str(exception)
        finally:
            if self.transport is not None:
                self.transport.close()
            self.stream.close()
        observation = self.observer.finish(error or self.error)
        launcher, editor = self.parser.launcher.result(), self.parser.editor.result()
        exits = sorted(self.parser.launcher.teardown)
        clean = exits == ['OBSERVE launcher app=foot exit=0', 'OBSERVE launcher app=mousepad exit=0']
        passed = (not (error or self.error) and self.complete and self.teardown and clean
                  and observation['status'] == 'PASS')
        self.result = {'status': 'PASS' if passed else 'FAIL',
            'scope': 'authenticated VM launcher-driven app switching and OSK; no phone proof',
            'observation': observation, 'launcher_protocol': launcher, 'editor_protocol': editor,
            'acknowledgement_sent': self.ack_sent, 'approved_teardown': self.teardown,
            'clean_client_exits': clean, 'stream_bytes': self.offset, 'phone': 'NOT RUN'}
        if not passed:
            self.result['error'] = str(error or self.error or 'incomplete application observation/cleanup')
        (self.directory/'apps-result.json').write_text(json.dumps(self.result, indent=2)+'\n')
        return self.result
