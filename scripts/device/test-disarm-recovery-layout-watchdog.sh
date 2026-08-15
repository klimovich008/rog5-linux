#!/bin/sh
set -eu

repo=$(CDPATH= cd -- "$(dirname "$0")/../.." && pwd -P)
target=$repo/scripts/device/disarm-recovery-layout-watchdog.sh
work=$(mktemp -d)
fixture_pid=

cleanup_fixture() {
	case $fixture_pid in ''|*[!0-9]*|0|1) return ;; esac
	if [ -r "/proc/$fixture_pid/task/$fixture_pid/children" ]; then
		for child in $(cat "/proc/$fixture_pid/task/$fixture_pid/children"); do
			kill -CONT "$child" 2>/dev/null || true
			kill -KILL "$child" 2>/dev/null || true
		done
	fi
	kill -CONT "$fixture_pid" 2>/dev/null || true
	kill -KILL "$fixture_pid" 2>/dev/null || true
}

cleanup() {
	cleanup_fixture
	rm -rf -- "$work"
}
trap cleanup EXIT HUP INT TERM

spawn_fixture() {
	children=$1
	fixture=$work/watchdog-fixture
	pid_file=$work/fixture.pid
	if [ "$children" = 1 ]; then
		printf '%s\n' '#!/bin/sh' 'sleep 600' 'exit 0' >"$fixture"
	else
		printf '%s\n' '#!/bin/sh' 'sleep 600 &' 'sleep 600 &' 'wait' >"$fixture"
	fi
	chmod 0700 "$fixture"
	sh -c '"$1" </dev/null >/dev/null 2>&1 & echo $! >"$2"' sh \
		"$fixture" "$pid_file"
	fixture_pid=$(cat "$pid_file")
	attempt=0
	while [ "$attempt" -lt 100 ]; do
		if [ -r "/proc/$fixture_pid/stat" ]; then
			set -- $(cat "/proc/$fixture_pid/task/$fixture_pid/children")
			[ "$#" -eq "$children" ] && return 0
		fi
		sleep 0.05
		attempt=$((attempt + 1))
	done
	echo 'FAIL watchdog fixture did not stabilize' >&2
	exit 1
}

prepare_helper() {
	case_dir=$1
	mkdir -m 0700 "$case_dir"
	lease=$case_dir/lease
	armed=$case_dir/armed
	marker=$case_dir/disarmed
	sed \
		-e "s|^lease=.*|lease=$lease|" \
		-e "s|^armed=.*|armed=$armed|" \
		-e "s|^marker=.*|marker=$marker|" \
		-e "s|^expected_uid=.*|expected_uid=$(id -u)|" \
		-e "s|^expected_gid=.*|expected_gid=$(id -g)|" \
		-e "s|^expected_parent=.*|expected_parent=$(awk '{ print $4 }' "/proc/$fixture_pid/stat")|" \
		"$target" >"$case_dir/helper"
	chmod 0700 "$case_dir/helper"
	: >"$armed"
	chmod 0600 "$armed"
	start=$(awk '{ print $22 }' "/proc/$fixture_pid/stat")
	printf 'pid=%s\nstarttime=%s\n' "$fixture_pid" "$start" >"$lease"
	chmod 0600 "$lease"
}

[ -x "$target" ]
sh -n "$target"

spawn_fixture 1
prepare_helper "$work/success"
"$work/success/helper" >/dev/null
[ ! -e "/proc/$fixture_pid" ]
[ ! -e "$work/success/armed" ]
[ -f "$work/success/disarmed" ]
fixture_pid=

spawn_fixture 1
prepare_helper "$work/stale"
sed -i 's/^starttime=.*/starttime=1/' "$work/stale/lease"
if "$work/stale/helper" >/dev/null 2>&1; then
	echo 'FAIL stale watchdog lease was accepted' >&2
	exit 1
fi
[ -e "/proc/$fixture_pid" ]
[ -f "$work/stale/armed" ]
cleanup_fixture
fixture_pid=

spawn_fixture 2
prepare_helper "$work/two-children"
if "$work/two-children/helper" >/dev/null 2>&1; then
	echo 'FAIL multiple watchdog timer children were accepted' >&2
	exit 1
fi
[ -e "/proc/$fixture_pid" ]
[ -f "$work/two-children/armed" ]
case $(awk '/^State:/ { print $2 }' "/proc/$fixture_pid/status") in
	T|t) echo 'FAIL refused watchdog remained frozen' >&2; exit 1 ;;
esac
cleanup_fixture
fixture_pid=

echo 'PASS recovery layout watchdog disarm succeeds exactly and rejects stale or ambiguous identities'
