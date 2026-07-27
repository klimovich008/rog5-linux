#!/bin/sh
# shellcheck disable=SC2016
set -eu

fail() {
	echo "FAIL $*" >&2
	exit 1
}

[ "${ALLOW_MAINLINE_WCN6855_GATE:-}" = 1 ] ||
	fail 'set ALLOW_MAINLINE_WCN6855_GATE=1 for the one-shot gate'
[ "${ALLOW_MAINLINE_WCN6855_REBOOT:-}" = 1 ] ||
	fail 'set ALLOW_MAINLINE_WCN6855_REBOOT=1 for immediate fallback'
[ "$(id -u)" -eq 0 ] || fail 'compound WCN6855 gate requires root'

for command in awk cat cut find findmnt grep id ip kill mktemp ps \
	readlink setsid sha256sum sleep stat systemctl tr uname wait wc; do
	command -v "$command" >/dev/null || fail "missing command: $command"
done

[ "$(uname -r)" = 7.1.4-g7a5cef0db479 ] || fail 'unexpected kernel'
[ "$(cat /proc/1/comm)" = systemd ] || fail 'PID 1 is not systemd'
system_state=
for _ in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 \
	21 22 23 24 25 26 27 28 29 30; do
	system_state=$(systemctl is-system-running 2>/dev/null || true)
	[ "$system_state" != running ] || break
	case $system_state in
		starting|initializing) sleep 1 ;;
		*) break ;;
	esac
done
[ "$system_state" = running ] || fail 'systemd is not running'
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
[ "$(ip -4 -o address show dev usb0 |
	awk '$4 == "169.254.77.2/30" { count++ }
		END { print count + 0 }')" -eq 1 ] ||
	fail 'USB network address is not exact'

seal=/.rog5/root-ro/etc/rog5/wifi-enumeration-v1
probe=/.rog5/root-ro/usr/local/sbin/rog5-wifi-enumeration-probe
disarm=/run/rog5-wifi-control/disarm-network-root-watchdog.sh

verify_file() {
	file=$1
	mode=$2
	expected=$3
	[ -f "$file" ] && [ ! -L "$file" ] ||
		fail "gate input is absent or linked: $file"
	[ "$(stat -c '%u:%g:%a' "$file")" = "0:0:$mode" ] ||
		fail "gate input ownership or mode is unexpected: $file"
	[ "$(sha256sum "$file" | cut -d ' ' -f 1)" = "$expected" ] ||
		fail "gate input hash mismatch: $file"
}

verify_file "$seal" 444 \
	897608e6a4cf1725512ed22fc1332af680de103cf6947fd9f05dc64e20e8e9eb
verify_file "$probe" 755 \
	699039d117cb3ba23a4b5e3a5897777c6a661afc1ece95c230f67c98166854cb
verify_file "$disarm" 500 \
	b126182b615831e6f39784e4a2657cc60096ff906c26f1458be7d9a0d3ea065a
grep -qx 'generation=wifi-enumeration-v1' "$seal"
grep -qx \
	'wifi_modules_sha256=e7a2eed91e20742012cc0a1fb893545fc61870ec94ca0ca4add3ee6c41e5300d' \
	"$seal"
grep -qx 'promotion_state=UNBOOTED_HOLD' "$seal"

pid_file=/run/rog5-network-root-watchdog.pid
marker=/run/rog5-network-root-watchdog.disarmed.pid
[ -s "$pid_file" ] || fail 'initial rollback watchdog is absent'
[ ! -e "$marker" ] || fail 'initial rollback watchdog is already disarmed'
[ -w /proc/sysrq-trigger ] || fail 'SysRq reset control is unavailable'

transition_timeout=240
state_dir=$(mktemp -d /run/rog5-wifi-transition.XXXXXX)
setsid sh -c '
	set -eu
	exec 8>/dev/kmsg
	exec 9>/proc/sysrq-trigger
	printf "armed\n" >"$2"
	sleep "$1"
	echo "rog5-wifi-transition: watchdog expired" >&8
	echo b >&9
' sh "$transition_timeout" "$state_dir/armed" \
	</dev/null >/dev/null 2>&1 &
transition_pid=$!

transition_pgid=$(ps -o pgid= -p "$transition_pid" | tr -d ' ')
[ "$transition_pgid" = "$transition_pid" ] ||
	fail 'transition watchdog is not in an independent process group'
armed=0
for _ in 1 2 3 4 5; do
	if [ -s "$state_dir/armed" ] &&
		kill -0 "$transition_pid" 2>/dev/null; then
		armed=1
		break
	fi
	sleep 1
done
[ "$armed" -eq 1 ] || fail 'transition watchdog did not arm'
trap 'exit 1' HUP INT TERM

echo "BEGIN compound WCN6855 enumeration-only gate watchdog=${transition_timeout}s"
ALLOW_NETWORK_ROOT_WATCHDOG_DISARM=1 "$disarm"
[ ! -e "$pid_file" ] && [ -s "$marker" ] ||
	fail 'initial watchdog handoff is incomplete'
kill -0 "$transition_pid" 2>/dev/null ||
	fail 'transition watchdog disappeared during handoff'

ALLOW_MAINLINE_WCN6855_ENUMERATION_PROBE=1 "$probe"
kill -0 "$transition_pid" 2>/dev/null ||
	fail 'transition watchdog disappeared after probe'

systemctl reboot --no-block
echo 'PASS compound WCN6855 enumeration-only gate watchdog=armed probe=passed reboot=requested'
wait "$transition_pid"
fail 'transition watchdog returned before fallback reboot'
