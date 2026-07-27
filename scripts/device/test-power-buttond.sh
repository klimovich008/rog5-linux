#!/bin/sh
set -eu

repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)
target=${TARGET:-$repo/scripts/device/power-buttond.py}
unit=${UNIT:-$repo/packaging/arch/rog5-power-button.service}

fail() {
	echo "FAIL $*" >&2
	exit 1
}

[ -f "$target" ] && [ ! -L "$target" ] && [ -x "$target" ] ||
	fail 'missing executable power-button handler'
[ -f "$unit" ] && [ ! -L "$unit" ] ||
	fail 'missing power-button service'

work=$(mktemp -d)
trap 'rm -rf -- "$work"' EXIT HUP INT TERM
PYTHONPYCACHEPREFIX=$work/pycache python3 -m py_compile "$target"
command -v systemd-analyze >/dev/null ||
	fail 'missing systemd-analyze'

for contract in \
	'/sys/class/input' \
	'/dev/input' \
	'pmic_pwrkey' \
	'@llHHi' \
	'KEY_POWER = 116' \
	'VALUE_PRESS = 1' \
	'/usr/local/bin/rog5-screen-toggle.sh'
do
	grep -Fq "$contract" "$target" ||
		fail "power-button handler omits: $contract"
done

for contract in \
	'ConditionPathExists=/usr/local/bin/rog5-screen-toggle.sh' \
	'ExecStart=/usr/local/libexec/rog5-power-buttond' \
	'Restart=on-failure' \
	'DevicePolicy=closed' \
	'DeviceAllow=char-input r' \
	'NoNewPrivileges=yes' \
	'ProtectSystem=strict' \
	'ProtectHome=read-only' \
	'CapabilityBoundingSet=CAP_SETUID CAP_SETGID' \
	'RestrictAddressFamilies=AF_UNIX' \
	'WantedBy=multi-user.target'
do
	grep -Fqx "$contract" "$unit" ||
		fail "power-button service omits: $contract"
done

mkdir "$work/systemd"
sed "s|^ExecStart=/usr/local/libexec/rog5-power-buttond$|ExecStart=$target|" \
	"$unit" >"$work/systemd/rog5-power-button.service"
systemd-analyze verify "$work/systemd/rog5-power-button.service"

if grep -Eq \
	'shell[[:space:]]*=[[:space:]]*True|os[.]system|/dev/(block|disk)|(^|[^[:alnum:]_])(fastboot|adb|reboot|poweroff)([^[:alnum:]_]|$)' \
	"$target" "$unit"
then
	fail 'power-button path contains a shell, storage, or boot action'
fi

toggle=$work/toggle
cat >"$toggle" <<'EOF'
#!/bin/sh
printf '%s\n' "$*" >>"$TOGGLE_LOG"
EOF
chmod 0755 "$toggle"

ignored=$work/ignored-events
python3 - "$ignored" <<'PY'
import struct
import sys

event = struct.Struct("@llHHi")
records = (
    (0, 0, 1, 116, 0),
    (0, 0, 1, 116, 2),
    (0, 0, 1, 114, 1),
)
with open(sys.argv[1], "wb") as output:
    for record in records:
        output.write(event.pack(*record))
PY
if TOGGLE_LOG=$work/ignored.log \
	"$target" --input "$ignored" --toggle "$toggle" --once \
	>"$work/ignored.out" 2>&1
then
	fail 'release, repeat, or non-power key completed the monitor'
fi
[ ! -e "$work/ignored.log" ] ||
	fail 'release, repeat, or non-power key triggered a toggle'

events=$work/events
python3 - "$events" <<'PY'
import struct
import sys

event = struct.Struct("@llHHi")
records = (
    (0, 0, 0, 0, 0),
    (0, 0, 1, 116, 0),
    (0, 0, 1, 116, 2),
    (0, 0, 1, 114, 1),
    (0, 0, 1, 116, 1),
    (0, 0, 1, 116, 0),
)
with open(sys.argv[1], "wb") as output:
    for record in records:
        output.write(event.pack(*record))
PY

TOGGLE_LOG=$work/toggle.log \
	"$target" --input "$events" --toggle "$toggle" --once
[ "$(cat "$work/toggle.log")" = toggle ] ||
	fail 'one KEY_POWER press did not produce exactly one toggle'

printf short >"$work/short-event"
if "$target" --input "$work/short-event" --toggle "$toggle" --once \
	>"$work/short.out" 2>&1
then
	fail 'short input_event was accepted'
fi
grep -Fq 'short input_event' "$work/short.out" ||
	fail 'short input_event rejection was not explicit'

cat >"$work/failing-toggle" <<'EOF'
#!/bin/sh
exit 7
EOF
chmod 0755 "$work/failing-toggle"
python3 - "$work/press-event" <<'PY'
import struct
import sys

with open(sys.argv[1], "wb") as output:
    output.write(struct.pack("@llHHi", 0, 0, 1, 116, 1))
PY
if "$target" --input "$work/press-event" \
	--toggle "$work/failing-toggle" --once >"$work/failing.out" 2>&1
then
	fail 'toggle failure was ignored'
fi
grep -Fq 'screen toggle failed' "$work/failing.out" ||
	fail 'toggle failure rejection was not explicit'

echo 'PASS power button handles only KEY_POWER presses, rejects truncated input and failed toggles, and is device-confined'
