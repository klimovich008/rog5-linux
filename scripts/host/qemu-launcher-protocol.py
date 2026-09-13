#!/usr/bin/env python3
"""Attributed native-client evidence for the bounded two-app VM observation.

The client debug stream proves protocol requests/events, not pixels or phone
hardware. Prefixes come only from the guest-owned launcher supervisors. Object
IDs are scoped to each client; presentation intervals only gate observation.
"""
import re


class LauncherProtocol:
    PREFIXES = {'EDITOR_WAYLAND ': 'mousepad', 'FOOT_WAYLAND ': 'foot'}
    APP_IDS = {'mousepad': 'org.xfce.mousepad', 'foot': 'foot'}
    LINE_LIMIT = 16384
    LOG_LIMIT = 8 * 1024 * 1024
    DEFAULT_SEQUENCE = ('mousepad', 'foot', 'mousepad', 'foot')

    def __init__(self):
        self.pending = b''
        self.total = self.offset = 0
        self.errors = []
        self.owners = {}
        self.clients = {app: {'surfaces': {}, 'toplevels': {}, 'focus': {},
                             'mapped': False, 'interval_seen': False, 'ready': False}
                        for app in self.APP_IDS}
        self.focus_history = []
        self.focus_visits = []
        self.active_app = None
        self.terminal = False
        self.teardown = []

    def fail(self, reason):
        if reason not in self.errors:
            if len(self.errors) >= 64:
                raise ValueError('launcher error bound exceeded')
            self.errors.append(reason)

    def feed(self, data):
        self.total += len(data)
        if self.total > self.LOG_LIMIT:
            raise ValueError('launcher protocol exceeds serial log bound')
        lines = (self.pending + data).split(b'\n')
        self.pending = lines.pop()
        if any(len(line) > self.LINE_LIMIT for line in [*lines, self.pending]):
            raise ValueError('launcher protocol line exceeds 16 KiB bound')
        for raw in lines:
            self.line(re.sub(r'\x1b\[[0-?]*[ -/]*[@-~]', '', raw.decode(errors='replace')).rstrip('\r'))

    def read_available(self, path):
        if path.stat().st_size < self.offset:
            raise ValueError('launcher serial log truncated')
        with path.open('rb') as stream:
            stream.seek(self.offset)
            data = stream.read(131072)
        self.offset += len(data)
        self.feed(data)
        return not self.errors

    def ready(self, app):
        return not self.errors and self.clients[app]['ready'] and self.clients[app]['mapped']

    def focused(self, app):
        return (self.ready(app) and self.active_app == app and bool(self.focus_visits)
                and self.focus_visits[-1]['presented_interval'])

    @property
    def focus_generation(self):
        return len(self.focus_history)

    def line(self, line):
        # Only the unprefixed supervisor can establish launch ownership.
        owner = re.fullmatch(r'OBSERVE launcher app=(mousepad|foot) owner=([1-9]\d*) start=([1-9]\d*)', line)
        if owner:
            app, pid, start = owner.groups()
            if app in self.owners or (pid, start) in self.owners.values():
                self.fail('duplicate launcher owner')
            else:
                self.owners[app] = (pid, start)
            return
        if line.startswith('FAIL launcher '):
            self.fail(line)
            return
        exited = re.fullmatch(r'OBSERVE launcher app=(mousepad|foot) exit=(\d+)', line)
        if exited:
            if self.terminal:
                self.teardown.append(line)
            else:
                self.fail('client exited before terminal session: '+line)
            return
        if 'independently clocked Flutter KMS session complete' in line and not any(
                line.startswith(prefix) for prefix in self.PREFIXES):
            # This is only a teardown boundary; harness session_result separately
            # validates terminal counters/errors. It never manufactures readiness.
            self.terminal = True
            return
        for prefix, app in self.PREFIXES.items():
            if line.startswith(prefix):
                if app not in self.owners:
                    self.fail('client protocol before owned launch: '+app)
                    return
                if self.terminal:
                    return
                self.protocol(app, line[len(prefix):])
                return
        if 'Denial/Volition output scheduler audit' in line:
            counts = re.findall(r'\bpresentations=(\d+)\b', line)
            if len(counts) != 1:
                return
            for client in self.clients.values():
                if client['mapped']:
                    if client['interval_seen'] and int(counts[0]) > 0:
                        client['ready'] = True
                    client['interval_seen'] = True
            if self.active_app and self.focus_visits:
                visit = self.focus_visits[-1]
                if visit['interval_seen'] and int(counts[0]) > 0 and self.ready(self.active_app):
                    visit['presented_interval'] = True
                visit['interval_seen'] = True

    @staticmethod
    def title_valid(app, args):
        if app == 'mousepad':
            return bool(re.fullmatch(r'"\*?(?:/tmp/)?rog5-text-probe\.txt(?: - Mousepad)?"', args))
        # Foot's app_id is fixed; its shell may legitimately update its title.
        return bool(re.fullmatch(r'"[^"\x00-\x1f]{1,512}"', args))

    def protocol(self, app, line):
        match = re.search(r'(-> )?([a-z_]+)[#@](\d+)\.([a-z_]+)\((.*)\)\s*$', line)
        if not match:
            return
        outgoing, interface, oid, method, args = match.groups()
        client = self.clients[app]
        surfaces, tops = client['surfaces'], client['toplevels']
        if interface == 'xdg_wm_base' and method == 'get_xdg_surface' and outgoing:
            linked = re.fullmatch(r'new id xdg_surface[#@](\d+), wl_surface[#@](\d+)', args)
            if linked:
                xdg, surface = linked.groups()
                if xdg in surfaces or any(s['surface'] == surface for s in surfaces.values()):
                    self.fail('duplicate live surface: '+app)
                    return
                if len(surfaces) >= 64:
                    raise ValueError('launcher surface bound exceeded')
                surfaces[xdg] = dict(surface=surface, title=False, app_id=False,
                                     configured=False, serial=None, ack=False,
                                     pending_attach=None, committed=False, dead=False)
        elif interface == 'xdg_surface' and oid in surfaces:
            state = surfaces[oid]
            if method == 'get_toplevel' and outgoing:
                linked = re.fullmatch(r'new id xdg_toplevel[#@](\d+)', args)
                if linked:
                    if linked[1] in tops or oid in tops.values():
                        self.fail('duplicate live toplevel: '+app)
                        return
                    if len(tops) >= 64:
                        raise ValueError('launcher toplevel bound exceeded')
                    tops[linked[1]] = oid
            elif method == 'configure' and not outgoing and args.isdecimal():
                state.update(serial=args if state['configured'] else None, ack=False)
            elif method == 'ack_configure' and outgoing:
                state['ack'] = state['configured'] and args == state['serial']
            elif method == 'destroy' and outgoing:
                state['dead'] = True
                self.fail('surface destroyed before terminal session: '+app)
        elif interface == 'xdg_toplevel' and oid in tops:
            state = surfaces[tops[oid]]
            if method == 'set_title' and outgoing:
                state['title'] = self.title_valid(app, args)
            elif method == 'set_app_id' and outgoing:
                state['app_id'] = args == '"'+self.APP_IDS[app]+'"'
            elif method == 'configure' and not outgoing:
                state['configured'] = bool(re.fullmatch(r'\d+, \d+, array\[\d+\]', args))
            elif method == 'destroy' and outgoing:
                state['dead'] = True
                self.fail('toplevel destroyed before terminal session: '+app)
        elif interface == 'wl_surface' and outgoing:
            for state in surfaces.values():
                if state['surface'] != oid:
                    continue
                if method == 'attach':
                    state['pending_attach'] = bool(state['ack'] and re.fullmatch(
                        r'wl_buffer[#@]\d+, -?\d+, -?\d+', args))
                elif method == 'commit' and state['pending_attach'] is not None:
                    state['committed'] = state['pending_attach']
                    state['pending_attach'] = None
                elif method == 'destroy':
                    state['dead'] = True
                    self.fail('wl_surface destroyed before terminal session: '+app)
        elif interface == 'wl_keyboard' and not outgoing:
            if method == 'enter':
                focused = re.fullmatch(r'\d+, wl_surface[#@](\d+), array\[\d+\]', args)
                if focused:
                    if len(client['focus']) >= 64 and oid not in client['focus']:
                        raise ValueError('launcher keyboard bound exceeded')
                    client['focus'][oid] = focused[1]
            elif method == 'leave':
                left = re.fullmatch(r'\d+, wl_surface[#@](\d+)', args)
                if not left or client['focus'].get(oid) != left[1]:
                    self.fail('keyboard leave object mismatch: '+app)
                else:
                    del client['focus'][oid]
        self.refresh(app)

    def refresh(self, app):
        client = self.clients[app]
        valid = [s for s in client['surfaces'].values()
                 if s['committed'] and s['title'] and s['app_id'] and not s['dead']]
        mapped = bool(valid)
        if client['mapped'] and not mapped:
            self.fail('previously mapped client lost its toplevel: '+app)
        if mapped != client['mapped']:
            client['ready'] = client['interval_seen'] = False
        client['mapped'] = mapped
        focused = any(s['surface'] in client['focus'].values() for s in valid)
        if self.active_app == app and not focused:
            self.active_app = None
        if focused and self.active_app != app:
            other = self.active_app
            if other:
                self.fail('new client focus before previous leave: '+other+' -> '+app)
            self.active_app = app
            if len(self.focus_history) >= 64:
                raise ValueError('launcher focus transition bound exceeded')
            self.focus_history.append(app)
            self.focus_visits.append(dict(app=app, interval_seen=False, presented_interval=False))

    def result(self, expected_sequence=DEFAULT_SEQUENCE):
        expected = list(expected_sequence)
        matched = (self.focus_history == expected and all(
            visit['presented_interval'] for visit in self.focus_visits))
        valid = bool(expected) and matched and not self.errors and all(
            app in self.owners and self.clients[app]['mapped'] for app in self.APP_IDS)
        return {'status': 'PASS' if valid else 'FAIL',
                'scope': 'owned native Wayland toplevels and observed focus intervals; not visual or phone proof',
                'owners': {app: {'pid': pid, 'start': start} for app, (pid, start) in self.owners.items()},
                'mapped': {app: c['mapped'] for app, c in self.clients.items()},
                'ready': {app: self.ready(app) for app in self.clients},
                'focus_history': list(self.focus_history), 'focus_generation': self.focus_generation,
                'active_app': self.active_app, 'expected_sequence': expected,
                'client_state': {app: {
                    'interval_seen': c['interval_seen'],
                    'keyboard_focus': dict(c['focus']),
                    'surfaces': {oid: dict(s) for oid, s in c['surfaces'].items()},
                    'toplevels': dict(c['toplevels'])} for app, c in self.clients.items()},
                'focus_visits': [dict(visit) for visit in self.focus_visits],
                'errors': list(self.errors), 'post_terminal_exits': list(self.teardown),
                'visual_semantics': 'NOT RUN', 'phone': 'NOT RUN'}
