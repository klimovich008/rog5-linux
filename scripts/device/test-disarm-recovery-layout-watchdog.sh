#!/bin/sh
set -eu

repo=$(CDPATH= cd -- "$(dirname "$0")/../.." && pwd -P)
target=$repo/scripts/device/disarm-recovery-layout-watchdog.sh
work=$(mktemp -d)
fixture_pid=
fixture_supervisor_pid=

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
	case $fixture_supervisor_pid in
		''|*[!0-9]*|0|1) ;;
		*) kill -KILL "$fixture_supervisor_pid" 2>/dev/null || true ;;
	esac
	fixture_supervisor_pid=
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

spawn_unreaped_fixture() {
	fixture=$work/watchdog-unreaped-fixture
	pid_file=$work/unreaped.pid
	printf '%s\n' '#!/bin/sh' 'exec sleep 600' >"$fixture"
	chmod 0700 "$fixture"
	python3 - "$fixture" "$pid_file" <<'PY' &
import pathlib
import subprocess
import sys
import time

child = subprocess.Popen([sys.argv[1]])
pathlib.Path(sys.argv[2]).write_text(f"{child.pid}\n", encoding="ascii")
time.sleep(600)
PY
	fixture_supervisor_pid=$!
	attempt=0
	while [ "$attempt" -lt 100 ] && [ ! -s "$pid_file" ]; do
		sleep 0.05
		attempt=$((attempt + 1))
	done
	[ -s "$pid_file" ] || {
		echo 'FAIL unreaped watchdog fixture did not start' >&2
		exit 1
	}
	fixture_pid=$(cat "$pid_file")
	[ "$(awk '{ print $4 }' "/proc/$fixture_pid/stat")" = "$fixture_supervisor_pid" ] || {
		echo 'FAIL unreaped watchdog parent is not stable' >&2
		exit 1
	}
	[ ! -s "/proc/$fixture_pid/task/$fixture_pid/children" ] || {
		echo 'FAIL unreaped watchdog fixture created an orphanable child' >&2
		exit 1
	}
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

spawn_unreaped_fixture
prepare_helper "$work/unreaped"
if ! "$work/unreaped/helper" >/dev/null 2>&1; then
	echo 'FAIL an exact killed but unreaped watchdog was rejected' >&2
	exit 1
fi
[ "$(awk '{ print $3 }' "/proc/$fixture_pid/stat")" = Z ] || {
	echo 'FAIL unreaped watchdog did not become an inert zombie' >&2
	exit 1
}
[ ! -e "$work/unreaped/armed" ]
[ -f "$work/unreaped/disarmed" ]
cleanup_fixture
fixture_pid=

echo 'PASS recovery layout watchdog disarm succeeds exactly and rejects stale identities'
