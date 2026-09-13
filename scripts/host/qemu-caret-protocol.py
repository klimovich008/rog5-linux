#!/usr/bin/env python3
"""Bounded editor WAYLAND_DEBUG evidence, not compositor acknowledgment.

feed() accepts one complete byte line. A caller must frame its stream and impose
its own total log/time limits. Ownership changes discard geometry; object ID
reuse is deliberately refused because a mixed/stale log cannot prove generation.
Caret sequence identifies the commit; rectangle_sequence identifies the latest
committed set_cursor_rectangle request, so a repeated commit cannot freshen it.
"""
import math
import re


class CaretProtocol:
    MAX_LINE = 8192
    MAX_OBJECTS = 64
    MAX_PRESSES = 64
    MAX_RECORDS = 1000000
    MAX_COORD = 16384
    PREFIX = b'EDITOR_WAYLAND '
    RECORD = re.compile(
        r'^(?:\[[0-9:. ]+\]\s*)?(?:\{[^{}\r\n]{1,80}\}\s*)?'
        r'(?P<request>->\s*)?(?P<interface>[a-z][a-z0-9_]*)#'
        r'(?P<id>[0-9]{1,10})\.(?P<method>[a-z_]+)\((?P<args>.*)\)$')

    def __init__(self):
        self.sequence = 0
        self.caret = None
        self.presses = []
        self.geometries = {}
        self.error = None
        self._objects = {}
        self._dead_surfaces = set()
        self._owner = None

    def _fail(self, reason):
        self.error = reason
        self.caret = None
        self.presses.clear()
        self.geometries.clear()

    @staticmethod
    def _uint(value):
        if not re.fullmatch(r'[0-9]{1,10}', value):
            raise ValueError('invalid unsigned integer')
        number = int(value)
        if number > 0xffffffff:
            raise ValueError('unsigned integer overflow')
        return number

    def _surface(self, value):
        if not value.startswith('wl_surface#'):
            raise ValueError('invalid surface')
        number = self._uint(value[11:])
        if not number or number in self._dead_surfaces:
            raise ValueError('dead or invalid surface')
        return number

    def _coord(self, value, integer=False):
        pattern = r'-?[0-9]{1,8}' if integer else r'-?[0-9]{1,8}(?:\.[0-9]{1,12})?'
        if not re.fullmatch(pattern, value):
            raise ValueError('invalid coordinate')
        number = int(value) if integer else float(value)
        if not math.isfinite(number) or abs(number) > self.MAX_COORD:
            raise ValueError('coordinate exceeds observation bound')
        return number

    def _object(self, oid, kind, create=False):
        current = self._objects.get(oid)
        if current is not None:
            if create or current['kind'] != kind or current['dead']:
                raise ValueError('ambiguous object generation')
            return current
        if len(self._objects) >= self.MAX_OBJECTS:
            raise ValueError('object limit exceeded')
        current = dict(kind=kind, dead=False, surface=None, enabled=False,
                       pending_enable=False, rect=None, pending_rect=None,
                       rectangle_sequence=None, pending_rectangle_sequence=None,
                       x=None, y=None, pressed=False)
        self._objects[oid] = current
        return current

    def _invalidate(self, oid, obj):
        if self._owner == oid:
            self.caret = None
            self._owner = None
        obj.update(enabled=False, pending_enable=False, rect=None, pending_rect=None,
                   rectangle_sequence=None, pending_rectangle_sequence=None)

    def feed(self, line):
        if self.error or not isinstance(line, bytes) or not line.startswith(self.PREFIX):
            return
        if len(line) > self.MAX_LINE:
            self._fail('editor line limit exceeded')
            return
        try:
            body = line[len(self.PREFIX):].decode('utf-8').rstrip('\r\n')
            if '\n' in body or '\r' in body:
                raise ValueError('multiple records in one feed')
            match = self.RECORD.fullmatch(body.strip())
            if not match:
                if any(name in body for name in ('zwp_text_input_v3', 'wl_pointer', 'wl_surface', 'xdg_surface')):
                    raise ValueError('malformed relevant protocol record')
                return
            interface, method = match['interface'], match['method']
            request = bool(match['request'])
            creation = ((interface == 'zwp_text_input_manager_v3' and method == 'get_text_input')
                        or (interface == 'wl_seat' and method == 'get_pointer'))
            relevant = (interface in ('zwp_text_input_v3', 'wl_pointer') or creation
                        or (interface == 'wl_surface' and method in ('destroy', 'commit'))
                        or (interface == 'xdg_surface' and method in ('set_window_geometry', 'destroy'))
                        or (interface == 'xdg_wm_base' and method == 'get_xdg_surface'))
            if not relevant:
                return
            self.sequence += 1
            if self.sequence > self.MAX_RECORDS:
                raise ValueError('record limit exceeded')
            oid = self._uint(match['id'])
            if not oid:
                raise ValueError('invalid object ID')
            args = [] if not match['args'] else [s.strip() for s in match['args'].split(',')]
            if creation:
                kind = 'zwp_text_input_v3' if interface == 'zwp_text_input_manager_v3' else 'wl_pointer'
                expected = 2 if kind == 'zwp_text_input_v3' else 1
                if not request or len(args) != expected or not args[0].startswith('new id ' + kind + '#'):
                    raise ValueError('invalid object creation')
                if expected == 2 and not re.fullmatch(r'wl_seat#[1-9][0-9]{0,9}', args[1]):
                    raise ValueError('invalid text input seat')
                child = self._uint(args[0][len('new id ' + kind + '#'):])
                if not child:
                    raise ValueError('invalid child object ID')
                self._object(child, kind, create=True)
            elif interface == 'zwp_text_input_v3':
                self._text(oid, method, args, request)
            elif interface == 'wl_pointer':
                self._pointer(oid, method, args, request)
            elif interface in ('xdg_wm_base', 'xdg_surface'):
                self._geometry(oid, interface, method, args, request)
            elif method == 'commit':
                if not request or args or oid in self._dead_surfaces:
                    raise ValueError('invalid surface commit')
                for obj in self._objects.values():
                    if obj['kind'] == 'xdg_surface' and obj['surface'] == oid and not obj['dead']:
                        if obj['pending_rect'] is not None:
                            x, y, width, height = obj['pending_rect']
                            self.geometries[oid] = dict(x=x, y=y, width=width, height=height,
                                                        sequence=self.sequence)
                            obj['pending_rect'] = None
            else:
                if not request or args or oid in self._dead_surfaces:
                    raise ValueError('invalid surface destruction')
                if len(self._dead_surfaces) >= self.MAX_OBJECTS:
                    raise ValueError('surface limit exceeded')
                self._dead_surfaces.add(oid)
                self.geometries.pop(oid, None)
                for key, obj in self._objects.items():
                    if obj['surface'] == oid:
                        self._invalidate(key, obj)
                        obj.update(surface=None, x=None, y=None, pressed=False)
                self.presses[:] = [p for p in self.presses if p['surface'] != oid]
        except (ValueError, UnicodeError) as exc:
            self._fail(str(exc))

    def _geometry(self, oid, interface, method, args, request):
        if not request:
            raise ValueError('wrong geometry direction')
        if interface == 'xdg_wm_base':
            if len(args) != 2 or not args[0].startswith('new id xdg_surface#'):
                raise ValueError('invalid xdg surface creation')
            child = self._uint(args[0][len('new id xdg_surface#'):])
            surface = self._surface(args[1])
            if not child or any(o['kind'] == 'xdg_surface' and o['surface'] == surface
                                and not o['dead'] for o in self._objects.values()):
                raise ValueError('ambiguous xdg surface ownership')
            self._object(child, 'xdg_surface', create=True)['surface'] = surface
            return
        obj = self._objects.get(oid)
        if obj is None or obj['kind'] != 'xdg_surface' or obj['dead'] or obj['surface'] is None:
            raise ValueError('unknown xdg surface ownership')
        if method == 'destroy':
            if args:
                raise ValueError('invalid xdg surface destroy')
            self.geometries.pop(obj['surface'], None)
            obj.update(dead=True, surface=None, pending_rect=None)
            return
        if len(args) != 4:
            raise ValueError('invalid window geometry arguments')
        rect = tuple(self._coord(a, integer=True) for a in args)
        x, y, width, height = rect
        if width <= 0 or height <= 0 or abs(x + width) > self.MAX_COORD or abs(y + height) > self.MAX_COORD:
            raise ValueError('invalid window geometry extent')
        obj['pending_rect'] = rect

    def _text(self, oid, method, args, request):
        if method not in ('enter', 'leave', 'enable', 'disable', 'set_cursor_rectangle', 'commit', 'destroy'):
            return
        obj = self._object(oid, 'zwp_text_input_v3')
        if request != (method not in ('enter', 'leave')):
            raise ValueError('wrong text input direction')
        expected = 1 if method in ('enter', 'leave') else 4 if method == 'set_cursor_rectangle' else 0
        if len(args) != expected:
            raise ValueError('invalid text input arguments')
        if method == 'enter':
            surface = self._surface(args[0])
            if obj['surface'] is not None:
                raise ValueError('duplicate text input enter')
            self._invalidate(oid, obj)
            obj['surface'] = surface
        elif method == 'leave':
            if self._surface(args[0]) != obj['surface']:
                raise ValueError('text input leave surface mismatch')
            self._invalidate(oid, obj)
            obj['surface'] = None
        elif method == 'disable':
            self._invalidate(oid, obj)
        elif method == 'destroy':
            self._invalidate(oid, obj)
            obj.update(dead=True, surface=None)
        elif method == 'enable':
            self._invalidate(oid, obj)
            obj['pending_enable'] = obj['surface'] is not None
        elif method == 'set_cursor_rectangle':
            rect = tuple(self._coord(a, integer=True) for a in args)
            x, y, width, height = rect
            if width < 0 or height <= 0 or abs(x + width) > self.MAX_COORD or abs(y + height) > self.MAX_COORD:
                raise ValueError('invalid caret extent')
            if obj['surface'] is not None and (obj['enabled'] or obj['pending_enable']):
                obj['pending_rect'] = rect
                obj['pending_rectangle_sequence'] = self.sequence
        elif method == 'commit':
            if obj['surface'] is None or not (obj['enabled'] or obj['pending_enable']):
                return
            obj['enabled'] = True
            obj['pending_enable'] = False
            if obj['pending_rect'] is not None:
                obj['rect'] = obj['pending_rect']
                obj['rectangle_sequence'] = obj['pending_rectangle_sequence']
                obj['pending_rect'] = None
                obj['pending_rectangle_sequence'] = None
            if obj['rect'] is not None:
                if self._owner is not None and self._owner != oid:
                    raise ValueError('ambiguous active text input ownership')
                x, y, width, height = obj['rect']
                self._owner = oid
                self.caret = dict(surface=obj['surface'], x=x, y=y, width=width,
                                  height=height, sequence=self.sequence,
                                  rectangle_sequence=obj['rectangle_sequence'])

    def _pointer(self, oid, method, args, request):
        if method not in ('enter', 'leave', 'motion', 'button', 'release'):
            return
        obj = self._object(oid, 'wl_pointer')
        if request != (method == 'release'):
            raise ValueError('wrong pointer direction')
        expected = dict(enter=4, leave=2, motion=3, button=4, release=0)[method]
        if len(args) != expected:
            raise ValueError('invalid pointer arguments')
        if method == 'enter':
            self._uint(args[0])
            surface = self._surface(args[1])
            if obj['surface'] is not None:
                raise ValueError('duplicate pointer enter')
            obj.update(surface=surface, x=self._coord(args[2]), y=self._coord(args[3]), pressed=False)
        elif method == 'leave':
            self._uint(args[0])
            if self._surface(args[1]) != obj['surface']:
                raise ValueError('pointer leave surface mismatch')
            obj.update(surface=None, x=None, y=None, pressed=False)
        elif method == 'motion':
            self._uint(args[0])
            x, y = self._coord(args[1]), self._coord(args[2])
            if obj['surface'] is not None:
                obj.update(x=x, y=y)
        elif method == 'release':
            obj.update(dead=True, surface=None, x=None, y=None, pressed=False)
        elif method == 'button':
            values = [self._uint(a) for a in args]
            button, state = values[2:]
            if state not in (0, 1):
                raise ValueError('invalid pointer button state')
            if button != 272:
                return
            if state and obj['pressed']:
                raise ValueError('duplicate pointer press')
            obj['pressed'] = bool(state)
            if state and obj['surface'] is not None:
                self.presses.append(dict(surface=obj['surface'], x=obj['x'], y=obj['y'],
                                         sequence=self.sequence, button=button))
                del self.presses[:-self.MAX_PRESSES]

    def result(self):
        """Return diagnostics only; requests do not prove compositor acceptance."""
        return dict(error=self.error, sequence=self.sequence,
                    caret=None if self.caret is None else dict(self.caret),
                    presses=[dict(press) for press in self.presses],
                    geometries={key: dict(value) for key, value in self.geometries.items()},
                    objects=len(self._objects), evidence='client-protocol-only')
