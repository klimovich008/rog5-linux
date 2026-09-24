"""Virtual touchscreen for scripted gestures (uinput, no dependencies).

Clones the axis ranges of the real FTS3658U touchscreen so the compositor maps
it onto DSI-1 exactly like a finger, then replays taps and swipes at the
panel's own report cadence. Coordinates passed in are screen pixels.
"""
import fcntl, glob, os, struct, subprocess, time

EV_SYN, EV_KEY, EV_ABS = 0, 1, 3
SYN_REPORT = 0
BTN_TOUCH = 0x14a
ABS_X, ABS_Y = 0x00, 0x01
ABS_MT_SLOT, ABS_MT_TOUCH_MAJOR = 0x2f, 0x30
ABS_MT_POSITION_X, ABS_MT_POSITION_Y, ABS_MT_TRACKING_ID = 0x35, 0x36, 0x39
INPUT_PROP_DIRECT = 1
UI_SET_EVBIT, UI_SET_KEYBIT, UI_SET_ABSBIT, UI_SET_PROPBIT = 0x40045564, 0x40045565, 0x40045567, 0x4004556e
UI_DEV_SETUP, UI_ABS_SETUP, UI_DEV_CREATE, UI_DEV_DESTROY = 0x405c5503, 0x401c5504, 0x5501, 0x5502
AXES = (ABS_X, ABS_Y, ABS_MT_SLOT, ABS_MT_TOUCH_MAJOR, ABS_MT_POSITION_X, ABS_MT_POSITION_Y, ABS_MT_TRACKING_ID)


def _eviocgabs(code):
    return 0x80184540 + code


def real_touchscreen():
    for path in sorted(glob.glob('/sys/class/input/event*/device/name')):
        if 'fts' in open(path).read().lower():
            return '/dev/input/' + path.split('/')[4]
    raise RuntimeError('FTS3658U touchscreen not found')


class VirtualTouch:
    def __init__(self, width=1080, height=2448, rate_hz=120):
        src = os.open(real_touchscreen(), os.O_RDONLY)
        self.abs = {}
        try:
            for code in AXES:
                buf = bytearray(24)
                try:
                    fcntl.ioctl(src, _eviocgabs(code), buf, True)
                except OSError:
                    continue
                self.abs[code] = struct.unpack('<6i', buf)
        finally:
            os.close(src)
        self.w, self.h, self.period = width, height, 1.0 / rate_hz
        if not os.path.exists('/dev/uinput'):
            # production modules live in the published tree, not /lib/modules
            subprocess.run(['modprobe', '-d', '/run/rog5-modules', 'uinput'], check=False)
            time.sleep(0.5)
        self.fd = os.open('/dev/uinput', os.O_WRONLY | os.O_NONBLOCK)
        fcntl.ioctl(self.fd, UI_SET_EVBIT, EV_KEY)
        fcntl.ioctl(self.fd, UI_SET_EVBIT, EV_ABS)
        fcntl.ioctl(self.fd, UI_SET_KEYBIT, BTN_TOUCH)
        fcntl.ioctl(self.fd, UI_SET_PROPBIT, INPUT_PROP_DIRECT)
        for code, info in self.abs.items():
            fcntl.ioctl(self.fd, UI_SET_ABSBIT, code)
            fcntl.ioctl(self.fd, UI_ABS_SETUP, struct.pack('<HH6i', code, 0, *info))
        name = b'rog5-bench virtual touch'
        fcntl.ioctl(self.fd, UI_DEV_SETUP, struct.pack('<4H80sI', 0x06, 0x0b05, 0x5ee7, 1, name, 0))
        fcntl.ioctl(self.fd, UI_DEV_CREATE)
        self.tracking = 100
        time.sleep(1.0)  # let udev tag it and libinput add it

    def close(self):
        fcntl.ioctl(self.fd, UI_DEV_DESTROY)
        os.close(self.fd)

    def _scale(self, x, y):
        mx, my = self.abs[ABS_MT_POSITION_X][2], self.abs[ABS_MT_POSITION_Y][2]
        return round(x * (mx + 1) / self.w), round(y * (my + 1) / self.h)

    def _emit(self, events):
        now = time.time()
        sec, usec = int(now), int((now % 1) * 1e6)
        data = b''.join(struct.pack('<qqHHi', sec, usec, t, c, v) for t, c, v in events)
        os.write(self.fd, data + struct.pack('<qqHHi', sec, usec, EV_SYN, SYN_REPORT, 0))
        return time.monotonic()

    def down(self, x, y):
        self.tracking += 1
        ax, ay = self._scale(x, y)
        return self._emit([(EV_ABS, ABS_MT_SLOT, 0), (EV_ABS, ABS_MT_TRACKING_ID, self.tracking),
                           (EV_ABS, ABS_MT_POSITION_X, ax), (EV_ABS, ABS_MT_POSITION_Y, ay),
                           (EV_ABS, ABS_MT_TOUCH_MAJOR, 6), (EV_KEY, BTN_TOUCH, 1),
                           (EV_ABS, ABS_X, ax), (EV_ABS, ABS_Y, ay)])

    def move(self, x, y):
        ax, ay = self._scale(x, y)
        return self._emit([(EV_ABS, ABS_MT_SLOT, 0), (EV_ABS, ABS_MT_POSITION_X, ax),
                           (EV_ABS, ABS_MT_POSITION_Y, ay), (EV_ABS, ABS_X, ax), (EV_ABS, ABS_Y, ay)])

    def up(self):
        return self._emit([(EV_ABS, ABS_MT_SLOT, 0), (EV_ABS, ABS_MT_TRACKING_ID, -1), (EV_KEY, BTN_TOUCH, 0)])

    def tap(self, x, y, hold=0.06):
        t = self.down(x, y)
        time.sleep(hold)
        self.up()
        return t

    def swipe(self, x0, y0, x1, y1, duration=0.25, fling=True):
        """Linear drag at the panel report rate; fling=True lifts while moving."""
        steps = max(2, round(duration / self.period))
        t = self.down(x0, y0)
        start = time.monotonic()
        for i in range(1, steps + 1):
            f = i / steps
            self.move(x0 + (x1 - x0) * f, y0 + (y1 - y0) * f)
            delay = start + i * self.period - time.monotonic()
            if delay > 0:
                time.sleep(delay)
        if not fling:
            time.sleep(0.15)
        self.up()
        return t
