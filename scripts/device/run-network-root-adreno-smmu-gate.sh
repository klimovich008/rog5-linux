#!/bin/sh
set -eu

fail() {
	echo "FAIL $*" >&2
	exit 1
}

[ "${ALLOW_MAINLINE_ADRENO_SMMU_GATE:-}" = 1 ] ||
	fail 'set ALLOW_MAINLINE_ADRENO_SMMU_GATE=1 for the one-shot live gate'
[ "${ALLOW_MAINLINE_ADRENO_SMMU_REBOOT:-}" = 1 ] ||
	fail 'set ALLOW_MAINLINE_ADRENO_SMMU_REBOOT=1 for immediate fallback'
[ "$(id -u)" -eq 0 ] || fail 'compound live gate requires root'

for command in awk cat cut find findmnt grep id kill mktemp ps readlink \
	setsid sha256sum sleep stat systemctl tr uname wait wc; do
	command -v "$command" >/dev/null || fail "missing command: $command"
done

[ "$(uname -r)" = 7.1.4-g7a5cef0db479 ] || fail 'unexpected kernel'
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

module=/run/rog5-gpucc-diagnostic/gpucc-sm8350.ko
baseline=/run/rog5-gpucc-diagnostic/check-network-root-adreno-smmu-baseline.sh
disarm=/run/rog5-gpucc-diagnostic/disarm-network-root-watchdog.sh
probe=/run/rog5-gpucc-diagnostic/probe-network-root-adreno-smmu.sh

verify_file() {
	file=$1
	mode=$2
	expected=$3
	[ -f "$file" ] && [ ! -L "$file" ] ||
		fail "staged input is absent or linked: $file"
	[ "$(stat -c '%u:%g:%a' "$file")" = "0:0:$mode" ] ||
		fail "staged input ownership or mode is unexpected: $file"
	[ "$(sha256sum "$file" | cut -d ' ' -f 1)" = "$expected" ] ||
		fail "staged input hash mismatch: $file"
}

verify_file "$module" 400 \
	9ac07151490fe4844462945014e0a74674b43841e4cea1cfc4c3560231067d2a
verify_file "$baseline" 500 \
	db75fb268167a13b3f22b7fcdb73d17247d29e3551fcff5f3105022ca95fe402
verify_file "$disarm" 500 \
	b126182b615831e6f39784e4a2657cc60096ff906c26f1458be7d9a0d3ea065a
verify_file "$probe" 500 \
	c005963f206a7c325bdb08eaab4f7adc45e6d2ee1d5f9be5b1dc86f3c5317df6

pid_file=/run/rog5-network-root-watchdog.pid
marker=/run/rog5-network-root-watchdog.disarmed.pid
[ -s "$pid_file" ] || fail 'initial rollback watchdog is absent'
[ ! -e "$marker" ] || fail 'initial rollback watchdog is already disarmed'

"$baseline"

[ -s "$pid_file" ] || fail 'initial watchdog disappeared after baseline'
[ ! -e "$marker" ] || fail 'initial watchdog changed state after baseline'
[ -w /proc/sysrq-trigger ] || fail 'SysRq reset control is unavailable'

transition_timeout=120
state_dir=$(mktemp -d /run/rog5-adreno-smmu-transition.XXXXXX)
# Positional parameters are intentionally expanded by the child shell.
# shellcheck disable=SC2016
setsid sh -c '
	set -eu
	exec 8>/dev/kmsg
	exec 9>/proc/sysrq-trigger
	printf "armed\n" >"$2"
	sleep "$1"
	echo "rog5-adreno-smmu-transition: watchdog expired" >&8
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

echo "BEGIN Adreno-SMMU gate transition_watchdog=${transition_timeout}s"
ALLOW_NETWORK_ROOT_WATCHDOG_DISARM=1 "$disarm"
[ ! -e "$pid_file" ] && [ -s "$marker" ] ||
	fail 'initial watchdog handoff is incomplete'
kill -0 "$transition_pid" 2>/dev/null ||
	fail 'transition watchdog disappeared during handoff'

ALLOW_MAINLINE_ADRENO_SMMU_PROBE=1 "$probe"
kill -0 "$transition_pid" 2>/dev/null ||
	fail 'transition watchdog disappeared after probe'

systemctl reboot --no-block
echo 'PASS compound Adreno-SMMU gate transition_watchdog=armed reboot=requested'
wait "$transition_pid"
fail 'transition watchdog returned before fallback reboot'
