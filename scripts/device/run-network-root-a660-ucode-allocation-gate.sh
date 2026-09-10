#!/bin/sh
set -eu

fail() {
	echo "FAIL $*" >&2
	exit 1
}

[ "${ALLOW_MAINLINE_A660_UCODE_ALLOCATION_GATE:-}" = 1 ] ||
	fail 'set ALLOW_MAINLINE_A660_UCODE_ALLOCATION_GATE=1 for the one-shot gate'
[ "${ALLOW_MAINLINE_A660_UCODE_ALLOCATION_REBOOT:-}" = 1 ] ||
	fail 'set ALLOW_MAINLINE_A660_UCODE_ALLOCATION_REBOOT=1 for immediate fallback'
[ "$(id -u)" -eq 0 ] ||
	fail 'compound A660 ucode-allocation gate requires root'

for command in awk cat cut find findmnt grep id kill mktemp ps readlink \
	setsid sha256sum sleep stat systemctl tr uname wait wc; do
	command -v "$command" >/dev/null || fail "missing command: $command"
done

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

baseline=/.rog5/root-ro/usr/local/sbin/rog5-a660-ucode-allocation-baseline
probe=/.rog5/root-ro/usr/local/sbin/rog5-a660-ucode-allocation-probe
disarm=/run/rog5-a660-ucode-allocation-control/disarm-network-root-a660-watchdog.sh

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

verify_file "$baseline" 755 \
	4f2e50fd492c9fff06198396c1fd80fa877b1447f18920d9895ad82c4034e041
verify_file "$probe" 755 \
	63adc85bdd3b4f5b08130722d30615fad1a439eb3aa2a43a4b161e826c36c3ef
verify_file "$disarm" 500 \
	733a2ba85e192e982883de1afee04e9fee0d137d737a611ad0914f185885fbbc

pid_file=/run/rog5-network-root-watchdog.pid
marker=/run/rog5-network-root-watchdog.disarmed.pid
[ -s "$pid_file" ] || fail 'initial rollback watchdog is absent'
[ ! -e "$marker" ] || fail 'initial rollback watchdog is already disarmed'

"$baseline"
[ -s "$pid_file" ] || fail 'initial watchdog disappeared after baseline'
[ ! -e "$marker" ] || fail 'initial watchdog changed state after baseline'
[ -w /proc/sysrq-trigger ] || fail 'SysRq reset control is unavailable'

transition_timeout=240
state_dir=$(mktemp -d /run/rog5-a660-ucode-allocation-transition.XXXXXX)
# Positional parameters are intentionally expanded by the child shell.
# shellcheck disable=SC2016
setsid sh -c '
	set -eu
	exec 8>/dev/kmsg
	exec 9>/proc/sysrq-trigger
	printf "armed\n" >"$2"
	sleep "$1"
	echo "rog5-a660-ucode-allocation-transition: watchdog expired" >&8
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

echo "BEGIN A660 ucode-allocation gate transition_watchdog=${transition_timeout}s expected=OPEN_ERRNO=117"
ALLOW_A660_NETWORK_ROOT_WATCHDOG_DISARM=1 "$disarm"
[ ! -e "$pid_file" ] && [ -s "$marker" ] ||
	fail 'initial watchdog handoff is incomplete'
kill -0 "$transition_pid" 2>/dev/null ||
	fail 'transition watchdog disappeared during handoff'

ALLOW_MAINLINE_A660_UCODE_ALLOCATION=1 "$probe"
kill -0 "$transition_pid" 2>/dev/null ||
	fail 'transition watchdog disappeared after probe'

systemctl reboot --no-block
echo 'PASS compound A660 ucode-allocation gate open_errno=117 maps=3 unmaps=3 closes=3 gem_frees=3 gem_snapshot=equal transition_watchdog=armed reboot=requested'
wait "$transition_pid"
fail 'transition watchdog returned before fallback reboot'
