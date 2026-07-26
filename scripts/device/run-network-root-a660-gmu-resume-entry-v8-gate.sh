#!/bin/sh
set -eu

fail() {
	echo "FAIL $*" >&2
	exit 1
}

[ "${ALLOW_MAINLINE_A660_GMU_RESUME_ENTRY_V8_GATE:-}" = 1 ] ||
	fail 'set ALLOW_MAINLINE_A660_GMU_RESUME_ENTRY_V8_GATE=1 for the one-shot gate'
[ "${ALLOW_MAINLINE_A660_GMU_RESUME_ENTRY_V8_REBOOT:-}" = 1 ] ||
	fail 'set ALLOW_MAINLINE_A660_GMU_RESUME_ENTRY_V8_REBOOT=1 for immediate fallback'
[ "$(id -u)" -eq 0 ] ||
	fail 'compound A660 GMU resume-entry v8 gate requires root'

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

baseline=/.rog5/root-ro/usr/local/sbin/rog5-a660-gmu-resume-entry-v8-baseline
probe=/.rog5/root-ro/usr/local/sbin/rog5-a660-gmu-resume-entry-v8-probe
disarm=/run/rog5-a660-gmu-resume-entry-v8-control/disarm-network-root-a660-watchdog.sh

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
	3a4bcdcd9a96b896f22fda3be3f73c68a3b16e5d154558da9ad299c969faaf23
verify_file "$probe" 755 \
	832a96db228a9f0771c0ff364ed943100f243fbbce51ec4c0e2532e211a9e255
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
state_dir=$(mktemp -d /run/rog5-a660-gmu-resume-entry-v8-transition.XXXXXX)
# Positional parameters are intentionally expanded by the child shell.
# shellcheck disable=SC2016
setsid sh -c '
	set -eu
	exec 8>/dev/kmsg
	exec 9>/proc/sysrq-trigger
	printf "armed\n" >"$2"
	sleep "$1"
	echo "rog5-a660-gmu-resume-entry-v8-transition: watchdog expired" >&8
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

echo "BEGIN A660 GMU resume-entry v8 gate transition_watchdog=${transition_timeout}s expected=OPEN_ERRNO=117"
ALLOW_A660_NETWORK_ROOT_WATCHDOG_DISARM=1 "$disarm"
[ ! -e "$pid_file" ] && [ -s "$marker" ] ||
	fail 'initial watchdog handoff is incomplete'
kill -0 "$transition_pid" 2>/dev/null ||
	fail 'transition watchdog disappeared during handoff'

ALLOW_MAINLINE_A660_GMU_RESUME_ENTRY_V8=1 "$probe"
kill -0 "$transition_pid" 2>/dev/null ||
	fail 'transition watchdog disappeared after probe'

systemctl reboot --no-block
echo 'PASS compound A660 GMU resume-entry v8 gate open_errno=117 gmu_resume_entry_only=Y firmware_request_only=N ucode_allocation_only=N firmware_requests=2 firmware_releases=2 gmu_resume=1 rollback=1 outer_runtime_pm=1 inner_runtime_pm=0 clocks=0 irq=0 hfi=0 devfreq=0 llc=0 hw_init=0 scm=0 maps=3 unmaps=3 closes=3 gem_frees=3 kernel_news=3 kernel_puts=2 wrapper_gets=1 wrapper_puts=2 logical_gets=4 logical_puts=4 gem_snapshot=equal transition_watchdog=armed reboot=requested'
wait "$transition_pid"
fail 'transition watchdog returned before fallback reboot'
