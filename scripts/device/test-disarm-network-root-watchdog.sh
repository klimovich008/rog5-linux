#!/bin/sh
set -eu

repo=$(CDPATH= cd -- "$(dirname "$0")/../.." && pwd)
target=$repo/scripts/device/disarm-network-root-watchdog.sh

[ -x "$target" ]
sh -n "$target"

for contract in \
	'ALLOW_NETWORK_ROOT_WATCHDOG_DISARM' \
	'7.1.4-g7a5cef0db479' \
	'findmnt -n -o SOURCE /.rog5/root-ro' \
	'physical block device is present' \
	'block-backed mount is present' \
	'/sys/class/net/usb0/carrier' \
	'/run/rog5-network-root-watchdog.pid' \
	'/run/rog5-network-root-watchdog.disarmed.pid' \
	'/proc/$pid/fd/8' \
	'/proc/$pid/fd/9' \
	'kill -STOP "$pid"' \
	'kill -CONT "$pid"' \
	'kill -KILL "$pid"' \
	'watchdog child is not sleep' \
	'trap resume_on_abort EXIT' \
	"trap 'resume_on_abort; exit 1' HUP INT TERM" \
	'mv "$pid_file" "$marker"'; do
	grep -Fq "$contract" "$target" || {
		echo "FAIL watchdog disarm contract missing: $contract" >&2
		exit 1
	}
done

stop_line=$(grep -n '^kill -STOP "\$pid"$' "$target" | cut -d: -f1)
child_line=$(grep -n '^children=' "$target" | cut -d: -f1)
kill_line=$(grep -n '^kill -KILL "\$pid"' "$target" | cut -d: -f1)
dead_line=$(grep -n "watchdog process did not exit" "$target" | cut -d: -f1)
thaw_line=$(grep -n '^frozen=0$' "$target" | tail -n 1 | cut -d: -f1)
move_line=$(grep -n '^mv "\$pid_file" "\$marker"$' "$target" | cut -d: -f1)
[ "$stop_line" -lt "$child_line" ]
[ "$child_line" -lt "$kill_line" ]
[ "$kill_line" -lt "$dead_line" ]
[ "$dead_line" -lt "$thaw_line" ]
[ "$thaw_line" -lt "$move_line" ]

if grep -Eq 'fastboot[[:space:]]+flash|dd[[:space:]].*of=/dev/|hwclock.*--systohc' \
	"$target"; then
	echo 'FAIL watchdog disarm tool contains a persistent-write command' >&2
	exit 1
fi

set +e
"$target" >/dev/null 2>&1
missing_guard=$?
set -e
[ "$missing_guard" -ne 0 ]

echo 'PASS watchdog disarm is explicit, storage-safe, race-safe, and fail-resumable'
