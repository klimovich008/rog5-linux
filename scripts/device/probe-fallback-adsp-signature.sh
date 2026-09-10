#!/bin/sh
set -eu

fail() {
	echo "FAIL $*" >&2
	exit 1
}

[ "${ALLOW_FALLBACK_ADSP_PROBE:-}" = 1 ] ||
	fail 'set ALLOW_FALLBACK_ADSP_PROBE=1 for one attended stock-driver probe'

probe_timeout=${ROG5_PROBE_TIMEOUT:-75}
hold_seconds=${ROG5_PROBE_HOLD:-5}
case $probe_timeout:$hold_seconds in
	*[!0-9:]*|:*|*:) fail 'probe timeout and hold interval must be integers' ;;
esac
[ "$probe_timeout" -ge 60 ] && [ "$probe_timeout" -le 120 ] ||
	fail 'ROG5_PROBE_TIMEOUT must be between 60 and 120 seconds'
[ "$hold_seconds" -ge 3 ] && [ "$hold_seconds" -le 15 ] ||
	fail 'ROG5_PROBE_HOLD must be between 3 and 15 seconds'
[ "$probe_timeout" -ge $((hold_seconds + 45)) ] ||
	fail 'probe timeout must exceed the hold interval by at least 45 seconds'

for command in awk cat dmesg find grep id kill mktemp rm rmdir sed setsid \
	sleep sort stat tail tr uname wc
do
	command -v "$command" >/dev/null || fail "missing command: $command"
done

[ "$(id -u)" -eq 0 ] || fail 'probe must run as root'
[ "$(uname -r)" = 5.4.134-qgki-perf-00001-g6c308144c23e ] ||
	fail 'unexpected fallback kernel'
[ -c /dev/subsys_adsp ] || fail 'stock ADSP subsystem device is absent'

subsys=/sys/devices/platform/soc/17300000.qcom,lpass/subsys5
[ "$(cat "$subsys/name")" = adsp ] || fail 'unexpected subsystem mapping'
initial_state=$(cat "$subsys/state")
[ "$initial_state" != ONLINE ] || fail 'ADSP is already online'
initial_crashes=$(cat "$subsys/crash_count")
case $initial_crashes in
	''|*[!0-9]*) fail 'invalid initial ADSP crash count' ;;
esac

expected_firmware_files='adsp.b00
adsp.b01
adsp.b02
adsp.b03
adsp.b04
adsp.b05
adsp.b06
adsp.b07
adsp.b08
adsp.b09
adsp.b10
adsp.b11
adsp.b12
adsp.b13
adsp.b14
adsp.b15
adsp.b16
adsp.b17
adsp.b18
adsp.b19
adsp.b20
adsp.b21
adsp.b22
adsp.b23
adsp.b24
adsp.b25
adsp.b26
adsp.mbn
adsp.mdt'
actual_firmware_files=$(find /lib/firmware -mindepth 1 -maxdepth 1 -type f \
	-name 'adsp.*' -printf '%f\n' | sort)
[ "$actual_firmware_files" = "$expected_firmware_files" ] ||
	fail 'fallback ADSP firmware set is not exact'
[ "$(find /lib/firmware -mindepth 1 -maxdepth 1 -type f \
	-name 'adsp.*' -printf '%s\n' |
	awk '{ total += $1 } END { print total + 0 }')" -eq 30889541 ] ||
	fail 'fallback ADSP firmware size contract failed'
[ "$(stat -c %s /lib/firmware/adsp.mdt)" -eq 8628 ] ||
	fail 'fallback ADSP metadata size changed'
[ "$(stat -c %s /lib/firmware/adsp.mbn)" -eq 15473660 ] ||
	fail 'fallback combined ADSP image size changed'
[ ! -s /lib/firmware/adsp.b26 ] ||
	fail 'stock zero-length ADSP segment changed'

fatal_pattern='Kernel panic|Oops:|BUG:|Unable to handle kernel|Synchronous External Abort|watchdog.*bite'
[ "$(dmesg | grep -Ec "$fatal_pattern" || true)" -eq 0 ] ||
	fail 'fatal kernel signature exists before probe'
dmesg_start=$(( $(dmesg | wc -l) + 1 ))

probe_safe=0
watchdog_pid=
state_dir=
disarm_watchdog() {
	[ "$probe_safe" = 1 ] || return 0
	set +e
	if [ -n "$watchdog_pid" ]; then
		kill -STOP "-$watchdog_pid" 2>/dev/null
		kill -KILL "-$watchdog_pid" 2>/dev/null
		wait "$watchdog_pid" 2>/dev/null
	fi
	if [ -n "$state_dir" ]; then
		rm -f "$state_dir/armed"
		rmdir "$state_dir" 2>/dev/null
	fi
	watchdog_pid=
	state_dir=
	set -e
}
trap disarm_watchdog EXIT
trap 'exit 1' HUP INT TERM

state_dir=$(mktemp -d /run/rog5-fallback-adsp-probe.XXXXXX)
setsid sh -c '
	set -eu
	exec 8>/dev/kmsg
	exec 9>/proc/sysrq-trigger
	printf "armed\n" >"$2"
	sleep "$1"
	echo "rog5-fallback-adsp-probe: watchdog expired" >&8
	echo b >&9
' sh "$probe_timeout" "$state_dir/armed" \
	</dev/null >/dev/null 2>&1 &
watchdog_pid=$!

watchdog_pgid=$(awk '{ print $5 }' "/proc/$watchdog_pid/stat")
[ "$watchdog_pgid" = "$watchdog_pid" ] ||
	fail 'probe watchdog is not in an independent process group'
armed=0
for unused in 1 2 3 4 5; do
	if [ -s "$state_dir/armed" ] && kill -0 "$watchdog_pid" 2>/dev/null; then
		armed=1
		break
	fi
	sleep 1
done
[ "$armed" -eq 1 ] || fail 'probe watchdog did not arm'

post_fail() {
	reason=$1
	echo "EVIDENCE reason=$reason initial_state=$initial_state current_state=$(cat "$subsys/state" 2>/dev/null || true)"
	echo 'EVIDENCE new_adsp_dmesg_begin'
	dmesg | tail -n +"$dmesg_start" |
		grep -Ei 'adsp|lpass|subsys-pil|pil-tz|remoteproc|scm' |
		tail -n 180
	echo 'EVIDENCE new_adsp_dmesg_end'
	fail "$reason"
}

echo "BEGIN fallback-adsp-signature watchdog=${probe_timeout}s hold=${hold_seconds}s"
echo 'rog5-fallback-adsp-probe: begin' >/dev/kmsg
if ! exec 9</dev/subsys_adsp; then
	post_fail 'stock ADSP subsystem open failed'
fi

online=0
for unused in 1 2 3 4 5 6 7 8 9 10; do
	if [ "$(cat "$subsys/state")" = ONLINE ]; then
		online=1
		break
	fi
	sleep 1
done
[ "$online" -eq 1 ] || post_fail 'stock ADSP did not reach ONLINE'
[ "$(cat "$subsys/crash_count")" -eq "$initial_crashes" ] ||
	post_fail 'stock ADSP crash count changed during startup'

sleep "$hold_seconds"
[ "$(cat "$subsys/state")" = ONLINE ] ||
	post_fail 'stock ADSP stopped during hold'
[ "$(dmesg | grep -Ec "$fatal_pattern" || true)" -eq 0 ] ||
	post_fail 'fatal kernel signature appeared'

exec 9<&-
offline=0
for unused in 1 2 3 4 5 6 7 8 9 10; do
	if [ "$(cat "$subsys/state")" = OFFLINE ]; then
		offline=1
		break
	fi
	sleep 1
done
[ "$offline" -eq 1 ] || post_fail 'stock ADSP did not return to OFFLINE'
[ "$(cat "$subsys/crash_count")" -eq "$initial_crashes" ] ||
	post_fail 'stock ADSP crash count changed'

echo 'EVIDENCE stock_loader=accepted adsp_state=OFFLINE crash_delta=0'
probe_safe=1
disarm_watchdog
trap - EXIT HUP INT TERM
echo 'PASS fallback stock loader authenticated, started, and stopped the exact ADSP firmware without a crash'
