#!/bin/sh
set -eu
repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)
helper=$repo/scripts/device/load-native-ram-bundle.sh
sh -n "$helper"
work=$(mktemp -d)
trap 'rm -rf -- "$work"' EXIT HUP INT TERM
awk '/^exact\(\) \{/ { copy=1 } copy { print } copy && /^}/ { exit }' "$helper" >"$work/exact.sh"
. "$work/exact.sh"
stat() { printf '0\n'; }
printf 'fixture\n' >"$work/input"
hash=$(sha256sum "$work/input" | cut -d ' ' -f 1)
exact "$work/input" "$hash"
printf x >>"$work/input"
! exact "$work/input" "$hash"
ln -s input "$work/link"
! exact "$work/link" "$(sha256sum "$work/input" | cut -d ' ' -f 1)"
python3 - "$helper" <<'PY'
from pathlib import Path
import sys
s=Path(sys.argv[1]).read_text()
ordered = ['source boot changed', 'source kernel changed', 'battery temperature',
           'runtime library identity', '"$verifier" "$bundle" "$manifest"',
           'invalid optional serial logger', 'persistent state remains mounted', 'storage inventory changed',
           'mkdir "$root/entered"', '"$kexec" -c -l', 'cmp "$tools/shutdown"',
           'logger staging', 'systemctl kexec --no-block']
positions=[s.index(token) for token in ordered]
assert positions == sorted(positions)
for forbidden in ('fastboot', 'set_active', 'mkfs', 'blockdev --setrw', 'sgdisk', 'parted'):
    assert forbidden not in s
assert '"$kexec" -e' not in s
assert s.count('systemctl kexec --no-block') == 1
assert 'candidate remains consumed' in s
assert '[ ! -e /run/initramfs/rog5-exitrd-log ] && [ ! -L /run/initramfs/rog5-exitrd-log ]' in s
PY
echo 'PASS native RAM loader checks identity, signed payload, exact runtime and read-only storage before one execute'
