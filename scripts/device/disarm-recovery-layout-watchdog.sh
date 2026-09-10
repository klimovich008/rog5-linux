#!/bin/sh
set -eu

lease=/run/rog5-recovery-watchdog.lease
armed=/run/rog5-recovery-armed
marker=/run/rog5-recovery-watchdog.disarmed
expected_uid=0
expected_gid=0
expected_parent=1
watchdog_pid=
frozen=0

fail() {
	echo "FAIL $*" >&2
	exit 1
}

resume_on_abort() {
	[ "$frozen" = 0 ] || kill -CONT "$watchdog_pid" 2>/dev/null || true
}
trap resume_on_abort EXIT
trap 'resume_on_abort; exit 1' HUP INT TERM

[ -f "$lease" ] && [ ! -L "$lease" ] || fail 'watchdog lease is unavailable'
[ "$(stat -c %u "$lease")" = "$expected_uid" ] || fail 'watchdog lease owner changed'
[ "$(stat -c %g "$lease")" = "$expected_gid" ] || fail 'watchdog lease group changed'
[ "$(stat -c %a "$lease")" = 600 ] || fail 'watchdog lease mode changed'
[ "$(stat -c %h "$lease")" = 1 ] || fail 'watchdog lease link count changed'
[ "$(wc -l <"$lease")" = 2 ] || fail 'watchdog lease line count changed'
[ "$(stat -c %s "$lease")" -lt 128 ] || fail 'watchdog lease is too large'
[ ! -e "$marker" ] && [ ! -L "$marker" ] || fail 'watchdog already has a disarm marker'
[ -f "$armed" ] && [ ! -L "$armed" ] || fail 'watchdog armed marker is unavailable'
[ "$(stat -c %u "$armed")" = "$expected_uid" ] || fail 'watchdog armed marker owner changed'
[ "$(stat -c %a "$armed")" = 600 ] || fail 'watchdog armed marker mode changed'
[ "$(stat -c %h "$armed")" = 1 ] || fail 'watchdog armed marker link count changed'

[ "$(grep -c '^pid=[0-9][0-9]*$' "$lease")" = 1 ] || fail 'watchdog PID record changed'
[ "$(grep -c '^starttime=[0-9][0-9]*$' "$lease")" = 1 ] ||
	fail 'watchdog start-time record changed'
watchdog_pid=$(sed -n 's/^pid=//p' "$lease")
expected_start=$(sed -n 's/^starttime=//p' "$lease")
case $watchdog_pid:$expected_start in
	*[!0-9:]*|0:*|1:*|*:0|*:) fail 'watchdog lease identity is invalid' ;;
esac

process_stat=$(cat "/proc/$watchdog_pid/stat" 2>/dev/null) ||
	fail 'watchdog process is absent'
process_tail=${process_stat##*) }
observed_parent=$(printf '%s\n' "$process_tail" | awk '{ print $2 }')
observed_start=$(printf '%s\n' "$process_tail" | awk '{ print $20 }')
[ "$observed_parent" = "$expected_parent" ] ||
	fail 'watchdog is not a direct child of init'
[ "$observed_start" = "$expected_start" ] || fail 'watchdog lease is stale'

frozen=1
kill -STOP "$watchdog_pid" || fail 'cannot freeze rollback watchdog'
case $(awk '/^State:/ { print $2 }' "/proc/$watchdog_pid/status" 2>/dev/null) in
	T|t) ;;
	*) fail 'rollback watchdog did not stop' ;;
esac
process_stat=$(cat "/proc/$watchdog_pid/stat" 2>/dev/null) ||
	fail 'watchdog vanished after freeze'
process_tail=${process_stat##*) }
[ "$(printf '%s\n' "$process_tail" | awk '{ print $20 }')" = "$expected_start" ] ||
	fail 'watchdog identity changed after freeze'

rm -f -- "$armed" || fail 'cannot disarm rollback marker'
kill -KILL "$watchdog_pid" 2>/dev/null || true

attempt=0
while [ "$attempt" -lt 100 ] && [ -e "/proc/$watchdog_pid" ]; do
	remaining_stat=$(cat "/proc/$watchdog_pid/stat" 2>/dev/null) || break
	remaining_tail=${remaining_stat##*) }
	[ "$(printf '%s\n' "$remaining_tail" | awk '{ print $1 }')" != Z ] || break
	sleep 0.1
	attempt=$((attempt + 1))
done
if [ -e "/proc/$watchdog_pid" ]; then
	remaining_stat=$(cat "/proc/$watchdog_pid/stat" 2>/dev/null) ||
		fail 'cannot verify killed rollback watchdog'
	remaining_tail=${remaining_stat##*) }
	[ "$(printf '%s\n' "$remaining_tail" | awk '{ print $1 }')" = Z ] &&
		[ "$(printf '%s\n' "$remaining_tail" | awk '{ print $2 }')" = "$expected_parent" ] &&
		[ "$(printf '%s\n' "$remaining_tail" | awk '{ print $20 }')" = "$expected_start" ] ||
		fail 'rollback watchdog did not exit or become the exact inert zombie'
fi
frozen=0
mv "$lease" "$marker" || fail 'cannot publish watchdog disarm marker'
[ -f "$marker" ] && [ ! -L "$marker" ] || fail 'watchdog disarm marker is invalid'
[ ! -e "$armed" ] && [ ! -L "$armed" ] || fail 'watchdog remained armed'
trap - EXIT HUP INT TERM

echo 'PASS exact recovery rollback watchdog frozen, terminated, and marked disarmed'
