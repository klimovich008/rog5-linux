#!/usr/bin/env python3
"""Bounded USB data isolation for the already authenticated ROG5 RAM trial.

Caller must first prove the signed target's early stage on the anchored link.
Descriptors alone are not authentication. This changes only that instance's
authorized attribute, never hub defaults, port power, storage, or boot state.
"""
import json
import os
from pathlib import Path
import signal
import stat
import sys
import time

USB = Path('/sys/devices/pci0000:00/0000:00:08.1/0000:04:00.3/usb1/1-1/1-1.2')
IDENTITY = {'idVendor': '1d6b', 'idProduct': '0104', 'bcdDevice': '0701',
            'product': 'ROG5 persistent root'}


def attribute(directory, name):
    fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=directory)
    try:
        data = os.read(fd, 256)
        if len(data) >= 256:
            raise RuntimeError('oversized USB attribute')
        return data.decode('ascii').rstrip('\n')
    finally:
        os.close(fd)


class NativeDevice:
    def __init__(self, number):
        if not 1 <= number <= 127:
            raise ValueError('invalid USB device number')
        self.number = str(number)
        self.fd = os.open(USB, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
        self.identity = os.fstat(self.fd)
        try:
            self.verify()
            if attribute(self.fd, 'authorized') != '1':
                raise RuntimeError('device is not initially authorized')
        except BaseException:
            os.close(self.fd)
            raise

    def verify(self):
        current = os.stat(USB, follow_symlinks=False)
        if (not stat.S_ISDIR(current.st_mode) or current.st_uid != 0 or
                (current.st_dev, current.st_ino) != (self.identity.st_dev, self.identity.st_ino)):
            raise RuntimeError('USB instance replaced or topology changed')
        if attribute(self.fd, 'devnum') != self.number:
            raise RuntimeError('USB device number changed')
        for name, expected in IDENTITY.items():
            if attribute(self.fd, name) != expected:
                raise RuntimeError('USB descriptor identity changed: ' + name)

    def authorize(self, value):
        if value not in ('0', '1'):
            raise ValueError('invalid authorization value')
        self.verify()
        fd = os.open('authorized', os.O_WRONLY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=self.fd)
        try:
            self.verify()
            if os.write(fd, (value+'\n').encode()) != 2:
                raise RuntimeError('ambiguous USB authorization write; never repeat')
        finally:
            os.close(fd)
        self.verify()
        if attribute(self.fd, 'authorized') != value:
            raise RuntimeError('USB authorization did not match requested state')

    def restore(self):
        # A disconnected instance's state dies with it. Never touch a replacement.
        try:
            self.verify()
        except FileNotFoundError:
            return 'instance-gone'
        except RuntimeError:
            return 'replacement-untouched'
        value = attribute(self.fd, 'authorized')
        if value == '0':
            self.authorize('1')
        elif value != '1':
            raise RuntimeError('unexpected authorization state during restoration')
        return 'restored'

    def close(self):
        os.close(self.fd)


def emit(event, **fields):
    print(json.dumps(dict(event=event, monotonic=time.monotonic(), wall=time.time(), **fields)), flush=True)


def quiesce(number, seconds, clock=time.monotonic, pause=time.sleep, report=emit):
    if not 1 <= seconds <= 300:
        raise ValueError('USB isolation must be between1 and300 seconds')
    device = NativeDevice(number)
    try:
        report('USB_DATA_ISOLATION_ENTER', devnum=number, seconds=seconds)
        device.authorize('0')
        report('USB_DATA_DISABLED', devnum=number)
        deadline = clock() + seconds
        while clock() < deadline:
            device.verify()
            if attribute(device.fd, 'authorized') != '0':
                raise RuntimeError('another actor changed authorization')
            pause(min(0.1, max(0, deadline-clock())))
    finally:
        try:
            report('USB_DATA_ISOLATION_CLEANUP', result=device.restore(), devnum=number)
        finally:
            device.close()


def main():
    if len(sys.argv) != 3 or os.geteuid() != 0:
        raise SystemExit('usage (root): quiesce-native-usb-data.py DEVNUM SECONDS')
    def interrupted(signum, _frame):
        raise InterruptedError('isolation interrupted by signal'+str(signum))
    for signum in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
        signal.signal(signum, interrupted)
    quiesce(int(sys.argv[1]), int(sys.argv[2]))


if __name__ == '__main__':
    main()
