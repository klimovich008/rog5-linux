"""Short KEY_POWER press from a uinput device (press and release in one write).

Usage: python3 vpower.py [presses] [gap_seconds]
Press and release go out in a single write, so no reader (logind included)
ever sees a held key.
"""
import fcntl, os, struct, sys, time

EV_SYN, EV_KEY, SYN_REPORT, KEY_POWER = 0, 1, 0, 116
UI_SET_EVBIT, UI_SET_KEYBIT = 0x40045564, 0x40045565
UI_DEV_SETUP, UI_DEV_CREATE, UI_DEV_DESTROY = 0x405c5503, 0x5501, 0x5502


def ev(t, c, v):
    now = time.time()
    return struct.pack('<qqHHi', int(now), int((now % 1) * 1e6), t, c, v)


presses = int(sys.argv[1]) if len(sys.argv) > 1 else 1
gap = float(sys.argv[2]) if len(sys.argv) > 2 else 3.0
fd = os.open('/dev/uinput', os.O_WRONLY | os.O_NONBLOCK)
fcntl.ioctl(fd, UI_SET_EVBIT, EV_KEY)
fcntl.ioctl(fd, UI_SET_KEYBIT, KEY_POWER)
fcntl.ioctl(fd, UI_DEV_SETUP, struct.pack('<4H80sI', 0x06, 0x0b05, 0x5ee9, 1, b'rog5-bench virtual power key', 0))
fcntl.ioctl(fd, UI_DEV_CREATE)
try:
    time.sleep(1.0)
    for i in range(presses):
        if i:
            time.sleep(gap)
        os.write(fd, ev(EV_KEY, KEY_POWER, 1) + ev(EV_SYN, SYN_REPORT, 0) +
                 ev(EV_KEY, KEY_POWER, 0) + ev(EV_SYN, SYN_REPORT, 0))
        print('pressed', time.strftime('%H:%M:%S'), flush=True)
    time.sleep(0.5)
finally:
    fcntl.ioctl(fd, UI_DEV_DESTROY)
    os.close(fd)
