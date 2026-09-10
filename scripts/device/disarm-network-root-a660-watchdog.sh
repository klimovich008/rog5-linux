#!/bin/sh
set -eu

fail() {
	echo "FAIL $*" >&2
	exit 1
}

[ "${ALLOW_A660_NETWORK_ROOT_WATCHDOG_DISARM:-}" = 1 ] ||
	fail 'set ALLOW_A660_NETWORK_ROOT_WATCHDOG_DISARM=1 after the attended gate'
[ "$(uname -r)" = 7.1.4-rog5-a660reg1 ] || fail 'unexpected kernel'
[ "$(cat /proc/1/comm)" = systemd ] || fail 'PID 1 is not systemd'
[ "$(systemctl is-system-running 2>/dev/null || true)" = running ] ||
	fail 'systemd is not running'
[ "$(findmnt -n -o FSTYPE /)" = overlay ] || fail 'root is not OverlayFS'
[ "$(findmnt -n -o SOURCE /.rog5/root-ro)" = 169.254.77.1:/ ] ||
	fail 'unexpected NFS lower source'
findmnt -n -o OPTIONS /.rog5/root-ro | tr ',' '\n' | grep -qx ro ||
	fail 'NFS lower is not read-only'
[ "$(find /sys/class/block -mindepth 1 -maxdepth 1 -type l \
	-exec test -e {}/device \; -print 2>/dev/null | wc -l)" -eq 0 ] ||
	fail 'physical block device is present'
[ "$(findmnt -rn -o SOURCE |
	awk '/^\/dev\// { count++ } END { print count + 0 }')" -eq 0 ] ||
	fail 'block-backed mount is present'
[ "$(cat /sys/class/net/usb0/carrier)" = 1 ] ||
	fail 'USB network carrier is down'
[ "$(systemctl --failed --no-legend --plain 2>/dev/null |
	awk 'NF { count++ } END { print count + 0 }')" -eq 0 ] ||
	fail 'systemd has failed units'
fatal_pattern='Kernel panic|Oops:|BUG:|Unable to handle kernel|Synchronous External Abort|watchdog.*bite'
[ "$(dmesg | grep -Ec "$fatal_pattern" || true)" -eq 0 ] ||
	fail 'fatal kernel signature is present'

pid_file=/run/rog5-network-root-watchdog.pid
marker=/run/rog5-network-root-watchdog.disarmed.pid
[ -s "$pid_file" ] || fail 'watchdog PID file is absent'
[ ! -e "$marker" ] || fail 'watchdog already has a disarm marker'
pid=$(cat "$pid_file")
case $pid in *[!0-9]*|'') fail 'invalid watchdog PID' ;; esac
[ "$pid" -ne 1 ] && [ -d "/proc/$pid" ] ||
	fail 'watchdog process is absent'
[ "$(cat "/proc/$pid/comm")" = init ] ||
	fail 'watchdog process identity is unexpected'
[ "$(awk '{ print $4 }' "/proc/$pid/stat")" = 1 ] ||
	fail 'watchdog is not reparented to PID 1'
[ "$(readlink "/proc/$pid/fd/8")" = /dev/kmsg ] ||
	fail 'watchdog log descriptor is unexpected'
[ "$(readlink "/proc/$pid/fd/9")" = /proc/sysrq-trigger ] ||
	fail 'watchdog reset descriptor is unexpected'

frozen=0
resume_on_abort() {
	[ "$frozen" = 0 ] || kill -CONT "$pid" 2>/dev/null || true
}
trap resume_on_abort EXIT
trap 'resume_on_abort; exit 1' HUP INT TERM

kill -STOP "$pid"
frozen=1
case $(awk '/^State:/ { print $2 }' "/proc/$pid/status") in
	T|t) ;;
	*) fail 'watchdog did not stop' ;;
esac
children=$(cat "/proc/$pid/task/$pid/children" 2>/dev/null || true)
set -- $children
[ "$#" -le 1 ] || fail 'watchdog has unexpected children'
for child in "$@"; do
	[ "$(awk '{ print $4 }' "/proc/$child/stat")" = "$pid" ] ||
		fail 'watchdog child has an unexpected parent'
	[ "$(cat "/proc/$child/comm")" = sleep ] ||
		fail 'watchdog child is not sleep'
	kill -STOP "$child" 2>/dev/null || true
	kill -KILL "$child" 2>/dev/null || true
done
kill -KILL "$pid" 2>/dev/null || true

for unused in 1 2 3 4 5 6 7 8 9 10; do
	[ ! -e "/proc/$pid" ] && break
	sleep 1
done
[ ! -e "/proc/$pid" ] || fail 'watchdog process did not exit'
frozen=0
mv "$pid_file" "$marker"
[ -s "$marker" ] || fail 'watchdog disarm marker is absent'
trap - EXIT HUP INT TERM

echo 'PASS verified A660 network-root watchdog frozen, terminated, and marked disarmed'
