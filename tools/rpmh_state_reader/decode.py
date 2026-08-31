#!/usr/bin/env python3
"""Decode fixed RPMh APPS vote fields, never physical regulator state."""
import json
from pathlib import Path
import re
import sys

# Qualcomm's regulator readback masks: regulator.git commit09d99ff7fc3c.
# Keep all other bits visible; their meaning is not inferred here.
FIELDS = {
    rail + '-' + kind: kind
    for rail in ('s12', 'reference-l6')
    for kind in ('voltage', 'enable', 'mode')
}
MASK = {'voltage': 0x1fff, 'enable': 1, 'mode': 7}
SMPS_MODE = {3: 'retention', 4: 'pfm', 6: 'auto', 7: 'pwm'}


def decode(text):
    if len(text) > 2048 or not text.endswith('\n') or '\r' in text or '\0' in text:
        raise ValueError('invalid bounded snapshot framing')
    text.encode('ascii')
    lines = text.splitlines()
    if lines and lines[0] == 'READBACK_INSMOD_STATUS=0':
        lines = lines[1:]
    if (len(lines) < 3 or lines[0] != 'format=rog5-rpmh-readonly-v1'
            or not re.fullmatch(r'kernel=[A-Za-z0-9._+-]{1,96}', lines[1])
            or lines[2] != 'scope=APPS-votes-not-physical-measurements'):
        raise ValueError('unexpected readback format or scope')
    fields = {name: {'status': 'absent'} for name in FIELDS}
    seen = set()
    for line in lines[3:]:
        match = re.fullmatch(r'([a-z0-9-]+) result=(0|-[1-9][0-9]{0,3}) raw=(unavailable|0x[0-9a-f]{1,8})', line)
        if not match:
            raise ValueError('malformed readback field')
        name, result, raw = match.groups()
        if name not in fields or name in seen:
            raise ValueError('unknown or duplicated readback field')
        seen.add(name)
        if result != '0':
            if raw != 'unavailable':
                raise ValueError('failed read cannot carry a value')
            fields[name] = {'status': 'error', 'errno': int(result)}
            continue
        if raw == 'unavailable':
            raise ValueError('successful read lacks its raw value')
        value = int(raw, 16)
        kind = FIELDS[name]
        entry = {'status': 'present', 'raw': raw,
                 'uninterpreted_bits': hex(value & ~MASK[kind])}
        value &= MASK[kind]
        entry[{'voltage': 'millivolt_vote', 'enable': 'enable_vote', 'mode': 'mode_code'}[kind]] = value
        if name == 's12-mode':
            entry['mode'] = SMPS_MODE.get(value, 'unmapped')
        fields[name] = entry
    return {'format': 'rog5-rpmh-readonly-decoded-v1', 'kernel': lines[1][7:],
            'scope': 'APPS-votes-not-physical-measurements', 'fields': fields}


if __name__ == '__main__':
    if len(sys.argv) != 2:
        raise SystemExit('usage: decode.py SNAPSHOT')
    with Path(sys.argv[1]).open(encoding='ascii') as source:
        snapshot = source.read(2049)
    print(json.dumps(decode(snapshot), indent=2))
