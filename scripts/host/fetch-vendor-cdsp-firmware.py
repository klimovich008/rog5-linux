#!/usr/bin/env python3
"""Build an extra-firmware kit = BASE kit + the phone's own vendor_a CDSP image.

    fetch-vendor-cdsp-firmware.py BASE_KIT OUTPUT_KIT

BASE_KIT is the current PRODUCTION_EXTRA_FIRMWARE directory
(display-firmware-r4, SHA256SUMS 390cf505...). OUTPUT_KIT (new) gets the same
files plus qcom/sm8350/cdsp.{mdt,b00..b16}, read over SSH from the phone's
vendor_a (super partition extent, the same one install-rog5-sensors.sh uses)
with e2fsprogs debugfs, which opens the image read-only: no loop device, no
mount, nothing written on the phone. The SLPI only boots with the vendor_a
variant (modem_a differs, 2026-09-25), so the CDSP uses the vendor copy too.
Every file is checked against the hashes read on 2026-09-30 (WW33 vendor_a).
Pass the printed SHA256SUMS hash as PRODUCTION_EXTRA_FIRMWARE_SHA256.
"""
import hashlib
import importlib.util
import os
from pathlib import Path
import shutil
import sys

REPO = Path(__file__).resolve().parents[2]
BASE_SUMS = '390cf505ab99d7931c291b15f7a0e945ed75f26390cc7825fd450a75edc5cef9'
VENDOR_OFFSET = 11894784 * 512
CDSP = {
    'cdsp.mdt': 'cc996895cc23dfebd57620cd63a71971ab15b71df7bb21885954ee867e70485f',
    'cdsp.b00': '2b542f500f97161717f16b56ec2caf5c508b40d2ecf5f759324a8f5187731125',
    'cdsp.b01': '60a98f7f2cd68fb2dfb9ddcaa3da6cd98b1389d4333cc53180cd850d3d6308d4',
    'cdsp.b02': '5bf87f95a8726937c9b1303b4951f16c0af5289867fda648fb0ec550c989ebfc',
    'cdsp.b03': '933d00303a9e933d7278378920d5f40aacf7d7e0f84984a81f34000561b98ebe',
    'cdsp.b04': '74eebc4f11ff0c4209959a46833e8723322a7fefd8b76f87b9db73816fd2b85b',
    'cdsp.b05': 'c6a830b829cc2459ac64ebcff9959d54f7b589c1fbb96343cdd7f692441d5299',
    'cdsp.b06': '5330f473a9ea5308277a0a93635f72fd5ba3ec7c8ba5df408b727a2e943a6a0f',
    'cdsp.b07': '807f96a891c27887708041f2e68d3d9b445641895484e6a72bdfe025b01907a7',
    'cdsp.b08': '7f4863066169dc30f3eb14ce1565cfcd920c5d014c956bb92ddbb436c9b92157',
    'cdsp.b09': 'e04a745ede02443ab33472a8798cf7c8901439be982e9e6763893963aa0dc6e5',
    'cdsp.b10': 'b45fbbe9a38c7a07e5b3c3fff9e343afc845edf08cf658be853a207c23fc5a00',
    'cdsp.b11': '271097f462d94e52eb8f77ae3c0378922f6de9a18f3c4f85078d31fcc2706d92',
    'cdsp.b12': '1e5d6a3b445c396def1c8027241f07b459285fdf8fa2fcabd92a21f4c55a56b2',
    'cdsp.b13': 'c0a8fb46125e3acd56669375863436406fabcc7d076c465941e6dacb47294fe7',
    'cdsp.b14': '8fa441ff84b65b05ac036115efc21183ffc4c0c5fe23075528295c87caa7aa5c',
    'cdsp.b15': 'd3d1f873ff48fb75c3235f9d57a45f4c3275a3de637f68ea7baf4e30f6cc86ed',
    'cdsp.b16': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    base, out = Path(sys.argv[1]), Path(sys.argv[2])
    if sha((base/'SHA256SUMS').read_bytes()) != BASE_SUMS:
        sys.exit('FAIL base kit is not display-firmware-r4')
    if out.exists():
        sys.exit('FAIL output exists')
    spec = importlib.util.spec_from_file_location('trial', REPO/'scripts/host/production-ram-trial.py')
    trial = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(trial)
    address = os.environ.get('PHONE_ADDR', '10.77.0.2')
    find_super = ('for b in /sys/class/block/*; do grep -qx PARTNAME=super "$b/uevent" 2>/dev/null && '
                  'echo "/dev/${b##*/}"; done; true')
    result = trial.ssh(address, find_super, 30, None)
    supers = result.stdout.decode().split()
    if result.returncode or len(supers) != 1:
        sys.exit('FAIL cannot resolve the super partition')
    image = f'{supers[0]}?offset={VENDOR_OFFSET}'
    label = trial.ssh(address, f"debugfs -R 'stats -h' '{image}' 2>/dev/null | "
                      "sed -n 's/^Filesystem volume name: *//p'", 60, None)
    if label.stdout.decode().strip() != 'vendor':
        sys.exit('FAIL the vendor_a extent does not hold the vendor ext4')
    files = {}
    for name, digest in CDSP.items():
        got = trial.ssh(address, f"debugfs -R 'cat /firmware/{name}' '{image}' 2>/dev/null", 120, None)
        if got.returncode or sha(got.stdout) != digest:
            sys.exit(f'FAIL vendor_a {name} does not match its pin')
        files['qcom/sm8350/'+name] = got.stdout
    tmp = out.with_name(out.name+'.tmp')
    if tmp.exists() or tmp.is_symlink():
        sys.exit('FAIL temporary output exists')
    shutil.copytree(base, tmp)
    # The manifest is pinned; every copied byte must match it before the kit
    # is extended and re-hashed.
    sums = (tmp/'SHA256SUMS').read_bytes()
    if sha(sums) != BASE_SUMS:
        sys.exit('FAIL copied base manifest changed')
    expected = dict(reversed(row.split('  ', 1)) for row in sums.decode().splitlines())
    actual = {str(p.relative_to(tmp)) for p in tmp.rglob('*') if p.is_file() and p != tmp/'SHA256SUMS'}
    if actual != set(expected) or any(p.is_symlink() for p in tmp.rglob('*')):
        sys.exit('FAIL copied base inventory differs from its manifest')
    for relative, digest in expected.items():
        if sha((tmp/relative).read_bytes()) != digest:
            sys.exit('FAIL copied base file changed: '+relative)
    (tmp/'SHA256SUMS').unlink()
    for relative, data in files.items():
        if (tmp/relative).exists():
            sys.exit('FAIL base kit already has '+relative)
        (tmp/relative).write_bytes(data)
        (tmp/relative).chmod(0o644)
    rows = sorted(str(p.relative_to(tmp)) for p in tmp.rglob('*') if p.is_file())
    (tmp/'SHA256SUMS').write_text(''.join(f'{sha((tmp/r).read_bytes())}  {r}\n' for r in rows))
    tmp.rename(out)
    print(f'{sha((out/"SHA256SUMS").read_bytes())}  {out}/SHA256SUMS ({len(rows)} files)')


if __name__ == '__main__':
    main()
