#!/bin/sh
set -eu
repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)
helper=$repo/scripts/device/load-native-ram-bundle.sh
transaction=$repo/scripts/device/execute-native-ram-bundle-transaction.sh
sh -n "$helper"
sh -n "$transaction"
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
           'invalid optional serial logger', 'persistent state remains mounted',
           'storage inventory changed', 'mkdir "$root/entered"',
           '"$kexec" -c -l', 'cmp "$tools/shutdown"',
           'logger staging', 'systemctl kexec --no-block']
positions=[s.index(token) for token in ordered]
assert positions == sorted(positions)
for forbidden in ('fastboot', 'set_active', 'mkfs', 'blockdev --setrw', 'sgdisk', 'parted'):
    assert forbidden not in s
assert '"$kexec" -e' not in s
assert s.count('systemctl kexec --no-block') == 1
assert 'candidate remains consumed' in s
assert 'local transaction helper performs this quiesce' in s
assert '[ ! -e /run/initramfs/rog5-exitrd-log ] && [ ! -L /run/initramfs/rog5-exitrd-log ]' in s
PY
python3 - "$transaction" <<'PY'
from pathlib import Path
import sys
s = Path(sys.argv[1]).read_text()
ordered = [
    '"$loader" check "$@"',
    'rollback_required=1',
    'systemctl stop rog5-tailscaled.service',
    'systemctl stop rog5-persistent-state.service',
    '[ ! -e "$runtime_record" ]',
    '[ "$count" -eq 117 ]',
    '"$loader" execute "$@"',
]
positions = [s.index(token) for token in ordered]
assert positions == sorted(positions)
assert s.count('"$loader" execute "$@"') == 1
assert s.index('rollback_required=0', positions[-1]) > positions[-1]
assert 'systemctl reboot --no-block' in s
for forbidden in ('fastboot', 'set_active', 'mkfs', 'blockdev --setrw',
                  'sgdisk', 'parted', 'kexec -e'):
    assert forbidden not in s
PY
for contract in \
	'detach_persistent_state || mark_unclean detach' \
	'blockdev --setro "$device"' \
	'try_native_kexec "${1:-}" || true'; do
	grep -Fq "$contract" "$repo/initramfs/persistent-root-shutdown-standalone"
done

fixture=$work/transaction
mkdir -p "$fixture/bin" "$fixture/run/kexec" "$fixture/run" "$fixture/sys"
sed \
	-e "s@^PATH=.*@PATH=$fixture/bin:/usr/bin:/bin@" \
	-e "s@^root=/run/rog5-native-kexec@root=$fixture/run/kexec@" \
	-e "s@^runtime_record=/run/rog5-persistent-state.runtime@runtime_record=$fixture/run/state.runtime@" \
	-e "s@^block_class=/sys/class/block@block_class=$fixture/sys@" \
	-e "s@>/dev/kmsg@>>$fixture/kmsg@" \
	"$transaction" >"$fixture/transaction.sh"
cat >"$fixture/bin/id" <<'EOF'
#!/bin/sh
test "$1" = -u
echo 0
EOF
cat >"$fixture/bin/systemctl" <<EOF
#!/bin/sh
echo "systemctl-\$*" >>"$fixture/events"
case "\$*" in
  'stop rog5-tailscaled.service') ;;
  'stop rog5-persistent-state.service')
    test ! -e "$fixture/fail-stop" || exit 1
    rm -f "$fixture/run/state.runtime"
    for ro in "$fixture"/sys/sd*/ro; do echo 1 >"\$ro"; done
    ;;
  'reboot --no-block') ;;
  *) exit 2 ;;
esac
EOF
cat >"$fixture/run/kexec/load-native-ram-bundle.sh" <<EOF
#!/bin/sh
echo "loader-\$1" >>"$fixture/events"
if test "\$1" = execute; then
  test ! -e "$fixture/run/state.runtime"
  test "\$(grep -L '^1\$' "$fixture"/sys/sd*/ro | wc -l)" = 0
fi
EOF
chmod 700 "$fixture/bin/id" "$fixture/bin/systemctl" \
	"$fixture/run/kexec/load-native-ram-bundle.sh"
i=0
while [ "$i" -lt 117 ]; do
	node=$(printf '%s/sys/sd%03d' "$fixture" "$i")
	mkdir "$node"
	: >"$node/dev"
	echo 0 >"$node/ro"
	i=$((i + 1))
done
echo active >"$fixture/run/state.runtime"
sh "$fixture/transaction.sh" bundle manifest boot tools
cat >"$fixture/expected" <<'EOF'
loader-check
systemctl-stop rog5-tailscaled.service
systemctl-stop rog5-persistent-state.service
loader-execute
EOF
cmp "$fixture/expected" "$fixture/events"
! grep -Fq 'systemctl-reboot' "$fixture/events"

: >"$fixture/events"
touch "$fixture/fail-stop"
echo active >"$fixture/run/state.runtime"
if sh "$fixture/transaction.sh" bundle manifest boot tools; then
	echo 'FAIL transaction accepted a failed persistent-state stop' >&2
	exit 1
fi
grep -Fxq 'loader-check' "$fixture/events"
grep -Fxq 'systemctl-stop rog5-persistent-state.service' "$fixture/events"
grep -Fxq 'systemctl-reboot --no-block' "$fixture/events"
! grep -Fxq 'loader-execute' "$fixture/events"
echo 'PASS local transaction quiesces state before the loader and preserves one exact exitrd-backed execute'
