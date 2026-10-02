#!/usr/bin/env python3
"""Malformed FastRPC requests against hexagonrpcd's listener, built from the
pinned third_party/hexagonrpc archive plus every 0*.patch (as
scripts/device/install-rog5-sensors.sh builds it on the phone), with
AddressSanitizer and UBSan when the compiler has them. Covers the 2026-10-02
audit finding (07-device-rest): output buffers counted short, then written
out of bounds. Also builds the whole daemon, so a patch that breaks it fails
here first. No FastRPC device is used."""
from __future__ import annotations

import hashlib
import shutil
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SRC = REPO / 'third_party/hexagonrpc'
HARNESS = REPO / 'scripts/device/fixtures/hexagonrpc/listener-test.c'
INSTALLER = REPO / 'scripts/device/install-rog5-sensors.sh'


def pinned():
    text = INSTALLER.read_text()
    archive = text.split('archive=', 1)[1].split('\n', 1)[0]
    digest = text.split('archive_sha256=', 1)[1].split('\n', 1)[0]
    return archive, digest


def cc_flags(cc, tmp):
    probe = tmp / 'probe.c'
    probe.write_text('int main(void) { return 0; }\n')
    flags = ['-fsanitize=address,undefined', '-fno-sanitize-recover=undefined', '-fno-omit-frame-pointer']
    if subprocess.run([cc, *flags, '-o', str(tmp / 'probe'), str(probe)], capture_output=True).returncode == 0:
        return flags
    print('note: no sanitizers in this compiler; plain build')
    return []


UNIT = REPO / 'configs/systemd/rog5-sensors.service'


def check_unit() -> list[str]:
    """rog5-sensors.service runs hexagonrpcd sandboxed; only the module
    loader and the device hand-over keep root ("+")."""
    errors = []
    lines = [l.strip() for l in UNIT.read_text().splitlines() if l.strip() and not l.startswith('#')]
    for need in ('DynamicUser=yes', 'CapabilityBoundingSet=', 'NoNewPrivileges=yes', 'ProtectSystem=strict',
                 'ProtectHome=yes', 'PrivateTmp=yes', 'PrivateNetwork=yes', 'DevicePolicy=closed',
                 'DeviceAllow=char-misc rw', 'RestrictAddressFamilies=AF_UNIX', 'MemoryDenyWriteExecute=yes',
                 'SystemCallFilter=@system-service', 'Restart=always',
                 'ExecStartPre=+/run/rog5-platform/modules sensor-modules',
                 'ExecStart=/usr/local/bin/hexagonrpcd -f /dev/fastrpc-sdsp -d sdsp -s -R /usr/share/qcom/sm8350/ASUS/ZS673KS'):
        if need not in lines:
            errors.append(f'rog5-sensors.service lacks {need!r}')
    for line in lines:
        if line.startswith(('User=', 'Group=')) and line.split('=', 1)[1] in ('root', '0'):
            errors.append(f'rog5-sensors.service runs as root: {line}')
        if line.startswith('Exec'):
            # systemd expands $NAME itself: shell variables need $$
            body = line.replace('$$', '')
            if '$' in body:
                errors.append(f'unescaped $ in {line}')
    privileged = [l for l in lines if l.startswith('Exec') and '=+' in l]
    if len(privileged) != 4:
        errors.append(f'expected 4 privileged commands (modules, data owners, device, release), got {len(privileged)}')
    if any('hexagonrpcd -f' in l for l in privileged):
        errors.append('hexagonrpcd itself runs privileged')
    return errors


def main() -> int:
    errors = check_unit()
    for e in errors:
        print(f'FAIL {e}')
    if errors:
        return 1
    print('PASS rog5-sensors.service sandbox')
    cc = shutil.which('cc') or shutil.which('gcc')
    if not cc:
        print('FAIL no C compiler (cc)')
        return 1
    archive, digest = pinned()
    data = (SRC / archive).read_bytes()
    if hashlib.sha256(data).hexdigest() != digest:
        print(f'FAIL {archive} does not match the installer pin')
        return 1
    with tempfile.TemporaryDirectory(prefix='hexagonrpcd-test.') as tmpdir:
        tmp = Path(tmpdir)
        with tarfile.open(SRC / archive) as tar:
            tar.extractall(tmp, filter='data')
        tree = tmp / archive.removesuffix('.tar.gz')
        patches = sorted(SRC.glob('0*.patch'))
        if not any('validate-output-buffer' in p.name for p in patches):
            print('FAIL the listener hardening patch is missing')
            return 1
        for patch in patches:
            r = subprocess.run(['patch', '-p1', '--batch', '--forward', '-i', str(patch)], cwd=tree,
                               capture_output=True, text=True)
            if r.returncode:
                print(f'FAIL {patch.name} does not apply\n{r.stdout}{r.stderr}')
                return 1
        common = ['-O1', '-g', '-Wall', '-Wno-unused-parameter', f'-I{tree}/include', f'-I{tree}/hexagonrpcd']
        lib = sorted(str(p) for p in (tree / 'libhexagonrpc').rglob('*.c'))
        daemon = sorted(str(p) for p in (tree / 'hexagonrpcd').rglob('*.c'))
        # the daemon as the installer builds it
        r = subprocess.run([cc, '-O2', *common[2:], '-o', str(tmp / 'hexagonrpcd'), *lib, *daemon],
                           capture_output=True, text=True)
        if r.returncode:
            print(f'FAIL hexagonrpcd does not build\n{r.stderr}')
            return 1
        print('PASS hexagonrpcd builds with all patches')
        # the harness includes listener.c; leave it and main() out of the link
        others = [p for p in daemon if Path(p).name not in ('listener.c', 'rpcd.c')]
        flags = cc_flags(cc, tmp)
        r = subprocess.run([cc, *common, *flags, '-o', str(tmp / 'listener-test'), str(HARNESS), *lib, *others],
                           capture_output=True, text=True)
        if r.returncode:
            print(f'FAIL the listener harness does not build\n{r.stderr}')
            return 1
        r = subprocess.run([str(tmp / 'listener-test')], capture_output=True, text=True, timeout=60,
                           env={'ASAN_OPTIONS': 'detect_leaks=0:abort_on_error=0', 'PATH': '/usr/bin:/bin'})
        print(r.stdout, end='')
        if r.returncode:
            print(f'FAIL listener harness exit {r.returncode}\n{r.stderr[-4000:]}')
            return 1
    print('PASS hexagonrpcd listener')
    return 0


if __name__ == '__main__':
    sys.exit(main())
