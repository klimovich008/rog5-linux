#!/usr/bin/env python3
"""Static checks of shipped configuration fixed after the 2026-10-02 audit
(09-configs): the VNC listeners are Unix sockets only the phone user (and
root) can open, never TCP ports that every local account reaches; the ALSA
state sanitizer's udev rule can match the card. No device or systemd."""
from __future__ import annotations

import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
failures = 0


def check(cond, what):
    global failures
    print(('PASS ' if cond else 'FAIL ') + what)
    if not cond:
        failures += 1


def unit(path):
    return [l.strip() for l in (REPO / path).read_text().splitlines()
            if l.strip() and not l.lstrip().startswith(('#', ';'))]


def values(lines, key):
    return [l.split('=', 1)[1] for l in lines if l.startswith(key + '=')]



sock = unit('configs/systemd-user/rog5-wayvnc-phone.socket')
listen = values(sock, 'ListenStream')
check(listen == ['%t/rog5-vnc-phone.sock'], f'phone mirror socket is a runtime-dir Unix socket: {listen}')
check(values(sock, 'SocketMode') == ['0600'], 'phone mirror socket mode 0600')

wayvnc = unit('configs/systemd-user/rog5-wayvnc-phone.service')
start = values(wayvnc, 'ExecStart')
check(len(start) == 1 and '--unix-socket %t/rog5-vnc-phone-server.sock' in start[0]
      and not re.search(r'\b127\.0\.0\.1\b|\b0\.0\.0\.0\b|\s59\d\d\b', start[0]),
      'wayvnc (phone) listens on a Unix socket only')
check(values(wayvnc, 'UMask') == ['0077'], 'wayvnc (phone) creates its socket 0700')
proxy = values(unit('configs/systemd-user/rog5-wayvnc-phone-proxy.service'), 'ExecStart')
check(len(proxy) == 1 and proxy[0].endswith(' %t/rog5-vnc-phone-server.sock'),
      'the proxy forwards to wayvnc\'s Unix socket')

sway = (REPO / 'configs/rog5-desktop/sway.conf').read_text()
execs = [l for l in sway.splitlines() if l.startswith('exec') and 'wayvnc' in l]
check(len(execs) == 1 and '--unix-socket "$XDG_RUNTIME_DIR/rog5-vnc-desktop.sock"' in execs[0]
      and 'umask 077' in execs[0] and not re.search(r'127\.0\.0\.1|0\.0\.0\.0|\s59\d\d\b', execs[0]),
      'the virtual desktop serves VNC on a private Unix socket only')
for path in ('configs/systemd-user/rog5-wayvnc-phone.socket', 'configs/systemd-user/rog5-wayvnc-phone.service',
             'configs/systemd-user/rog5-wayvnc-phone-proxy.service', 'configs/systemd-user/rog5-desktop.service',
             'configs/rog5-desktop/sway.conf'):
    body = '\n'.join(l for l in (REPO / path).read_text().splitlines() if not l.lstrip().startswith('#'))
    check('127.0.0.1' not in body and '0.0.0.0' not in body, f'{path}: no IP listener')
helper = (REPO / 'scripts/device/rog5-desktop').read_text()
check('rog5-vnc-phone.sock' in helper and 'rog5-vnc-desktop.sock' in helper and 'ssh -N -L' in helper,
      'rog5-desktop documents the SSH forward to the sockets')
check('127.0.0.1:59' not in helper, 'rog5-desktop no longer points at loopback ports')

rule = [l for l in (REPO / 'configs/udev/89-rog5-alsa-state.rules').read_text().splitlines()
        if l and not l.startswith('#')]
check(len(rule) == 1 and 'ATTRS{id}=="ASUSROGPhone5"' in rule[0] and 'KERNELS' not in rule[0],
      'ALSA sanitizer rule: ATTRS{id} is not paired with a KERNELS key that excludes the card')

print('PASS rog5 security config' if not failures else f'FAIL {failures} check(s)')
sys.exit(1 if failures else 0)
