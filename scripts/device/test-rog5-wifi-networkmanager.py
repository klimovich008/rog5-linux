#!/usr/bin/env python3
"""Offline tests of the wpa_supplicant -> NetworkManager keyfile importer in
scripts/device/rog5-wifi-networkmanager.sh (its embedded Python, run on
synthetic saved networks; no NetworkManager or systemd). Audit 2026-10-02
(07-device-rest): a quoted "}" ended the network block and the passphrase
"abcdefgh}ijklmnop" became "abcdefg", and values were written to the
keyfile unescaped. Also checks that "apply" restarts NetworkManager and
restores the old units when it does not start."""
from __future__ import annotations

import configparser
import os
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / 'scripts/device/rog5-wifi-networkmanager.sh'
failures = 0


def check(cond, what):
    global failures
    print(('PASS ' if cond else 'FAIL ') + what)
    if not cond:
        failures += 1


def importer() -> str:
    text = SCRIPT.read_text()
    start = text.index("<<'EOF'\n") + len("<<'EOF'\n")
    return text[start:text.index('\nEOF\n', start) + 1]


def run(conf: str):
    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp) / 'network.conf'
        src.write_text(conf)
        out = Path(tmp) / 'conn'
        out.mkdir()
        r = subprocess.run([sys.executable, '-', str(src), str(out)], input=importer(), text=True,
                           capture_output=True)
        files = list(out.iterdir())
        if not files:
            return r, None, None
        raw = files[0].read_text()
        mode = files[0].stat().st_mode & 0o777
        return r, raw, mode


def glib_unescape(value: str) -> str:
    out, i = [], 0
    while i < len(value):
        c = value[i]
        if c == '\\' and i + 1 < len(value):
            out.append({'s': ' ', 'n': '\n', 't': '\t', 'r': '\r', '\\': '\\'}[value[i + 1]])
            i += 2
            continue
        out.append(c)
        i += 1
    return ''.join(out)


def keyfile(raw: str):
    cp = configparser.RawConfigParser(interpolation=None, delimiters=('=',))
    cp.optionxform = str
    cp.read_string(raw)
    return cp


def net(ssid='"home"', psk='"abcdefgh}ijklmnop"', extra=''):
    return f'ctrl_interface=/run/wpa_supplicant\nnetwork={{\n\tssid={ssid}\n\tpsk={psk}\n{extra}}}\n'


r, raw, mode = run(net())
check(r.returncode == 0 and raw is not None, 'a passphrase with "}" imports')
if raw:
    kf = keyfile(raw)
    check(glib_unescape(kf['wifi-security']['psk']) == 'abcdefgh}ijklmnop', 'the passphrase is kept whole')
    check(kf['wifi']['ssid'] == 'home' and mode == 0o600, 'ssid and 0600 keyfile')
    check('abcdefgh}ijklmnop' not in r.stdout + r.stderr, 'the passphrase is never printed')

r, raw, _ = run(net(psk='"back\\\\slash x"'))
check(raw is not None and glib_unescape(keyfile(raw)['wifi-security']['psk']) == 'back\\\\slash x',
      'backslashes in a passphrase are escaped for the keyfile')

r, raw, _ = run(net(psk='" lead space"'))
check(raw is not None and keyfile(raw)['wifi-security']['psk'].startswith('\\s'), 'a leading space is escaped')

r, raw, _ = run(net(psk='"quote"inside"'))
check(raw is not None and glib_unescape(keyfile(raw)['wifi-security']['psk']) == 'quote"inside',
      'a quote inside the passphrase (wpa_supplicant takes the last one)')

r, raw, _ = run(net(psk='"short"'))
check(r.returncode != 0 and raw is None, 'a passphrase shorter than 8 characters is refused')
r, raw, _ = run(net(psk='notquoted'))
check(r.returncode != 0 and raw is None, 'an unquoted non-hex psk is refused')
r, raw, _ = run(net(psk='a' * 64))
check(r.returncode == 0 and raw is not None and 'pmf=1' in raw, 'a 64-hex PSK imports with PMF off')

r, raw, _ = run(net(ssid='"a;b"'))
check(r.returncode != 0 and raw is None, 'an ssid with ";" is refused (NM would read a byte list)')
r, raw, _ = run(net(ssid='"a\\\\b"'))
check(r.returncode != 0 and raw is None, 'an ssid with a backslash is refused')
r, raw, _ = run(net(ssid='"' + 'x' * 33 + '"'))
check(r.returncode != 0 and raw is None, 'an ssid over 32 bytes is refused')
r, raw, _ = run(net(ssid='636166c3a9'))
check(raw is not None and keyfile(raw)['wifi']['ssid'] == 'café', 'a hex ssid decodes as UTF-8')

r, raw, _ = run('network={\n\tssid="home"\n\tpsk="abcdefgh}"\n')
check(r.returncode != 0 and raw is None, 'an unterminated block is refused')
r, raw, _ = run('network={\n\tssid="open"\n\tkey_mgmt=NONE\n}\n')
check(raw is not None and 'wifi-security' not in raw, 'an open network has no security section')

with tempfile.TemporaryDirectory() as tmp:
    src = Path(tmp) / 'network.conf'
    src.write_text(net())
    out = Path(tmp) / 'conn'
    out.mkdir()
    (out / 'home.nmconnection').symlink_to(Path(tmp) / 'elsewhere')
    r = subprocess.run([sys.executable, '-', str(src), str(out)], input=importer(), text=True, capture_output=True)
    check(not (Path(tmp) / 'elsewhere').exists(), 'a symlink at the keyfile path is not followed')

for extra in ('key_mgmt=WPA-EAP\n', 'key_mgmt=NONE\nwep_key0="secret"\n', 'key_mgmt=SAE\n'):
    r, raw, _ = run(net(psk='', extra=extra))
    check(r.returncode != 0 and raw is None, 'unsupported or missing credentials cannot become an open network')
r, raw, _ = run(net(psk='', extra='key_mgmt=NONE\n'))
check(r.returncode == 0 and '[wifi-security]' not in raw, 'an explicitly open network imports as open')
r, raw, _ = run(net(psk='a' * 64, extra='key_mgmt=SAE\n'))
check(r.returncode != 0 and raw is None, 'an SAE network cannot use a derived WPA2 PSK')

text = SCRIPT.read_text()
apply = text[text.index('\napply)'):text.index('\nrevert)')]
check('systemctl restart NetworkManager.service' in apply and 'enable --now NetworkManager' not in apply,
      'apply restarts NetworkManager (a running one keeps its old backend otherwise)')
check('systemctl unmask rog5-wifi-dhcp.service rog5-wifi-wpa.service' in apply,
      'apply restores the old units when NetworkManager does not start')
rollback = apply[apply.index('did not start'):]
check(rollback.index('disable --now iwd.service') < rollback.index('systemctl restart rog5-wifi-wpa'),
      'the rollback stops iwd before the old units take the interface again')
check(apply.index('import_network') < apply.index('systemctl stop rog5-wifi-dhcp'),
      'the import (and its refusals) comes before the working link is stopped')
r = subprocess.run(['sh', '-n', str(SCRIPT)])
check(r.returncode == 0, 'sh -n')

print('PASS rog5-wifi-networkmanager importer' if not failures else f'FAIL {failures} check(s)')
sys.exit(1 if failures else 0)
