#!/bin/sh
set -eu

repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd -P)
runner=$repo/scripts/host/test-repository-linux.sh
work=$(mktemp -d)
cleanup_pid=
cleanup() {
	[ -z "$cleanup_pid" ] ||
		/bin/kill -TERM -- "-$cleanup_pid" 2>/dev/null || true
	[ -z "$cleanup_pid" ] ||
		/bin/kill -KILL -- "-$cleanup_pid" 2>/dev/null || true
	rm -rf -- "$work"
}
trap cleanup EXIT HUP INT TERM

[ -f "$runner" ] && [ ! -L "$runner" ] && [ -x "$runner" ]
[ "$(grep -Fc 'shared_tests=(' "$runner")" -eq 1 ]
[ "$(grep -Fc 'tier_tests=()' "$runner")" -eq 1 ]
for token in \
	'DURATION %s %dms' \
	'isolated_tests=(' \
	'parallel_pids=(' \
	'parallel_status_files=(' \
	'selected_test() {' \
	'selected_test "$test_path" || continue' \
	'parallel_group_has_other_members() {' \
	'terminate_parallel_group() {' \
	'cleanup_parallel_tests() {' \
	'/bin/kill -0 "$group_pid"' \
	'/bin/kill -TERM -- "-$group_pid"' \
	'/bin/kill -KILL -- "-$group_pid"' \
	'wait "$pid"' \
	'set -m' \
	'set +m' \
	'status_file=${parallel_status_files[$index]}' \
	'parallel_pids[$index]=' \
	'isolated offline test left background descendants' \
	'for test_path in "${tests[@]}"' \
	'fail "sequential offline test failed: $test_path"' \
	'cancel-in-progress: true'; do
	case $token in
		'cancel-in-progress: true')
			grep -Fq "$token" "$repo/.github/workflows/offline-smoke.yml"
			;;
		*) grep -Fq "$token" "$runner" ;;
	esac
done

shared=$(sed -n '/^shared_tests=(/,/^)/p' "$runner" |
	sed -n 's|^[[:space:]]*\(scripts/[^[:space:]]*\)$|\1|p')
[ -n "$shared" ]
duplicates=$(printf '%s\n' "$shared" | sort | uniq -d)
[ -z "$duplicates" ] || {
	echo "FAIL shared repository test is duplicated: $duplicates" >&2
	exit 1
}
for isolated in $(sed -n '/^isolated_tests=(/,/^)/p' "$runner" |
	sed -n 's|^[[:space:]]*\(scripts/[^[:space:]]*\)$|\1|p'); do
	printf '%s\n' "$shared" | grep -Fxq "$isolated" || {
		echo "FAIL isolated suite is outside the shared test list: $isolated" >&2
		exit 1
	}
done

set +e
RUNNER="$runner" PID_FILE="$work/isolated.pid" \
	PARALLEL_ROOT="$work/parallel-output" bash -c '
	set -u
	eval "$(sed -n "/^parallel_group_has_other_members() {/,/^cleanup_parallel_tests() {/p" "$RUNNER" | sed '\''$d'\'')"
	eval "$(sed -n "/^cleanup_parallel_tests() {/,/^}/p" "$RUNNER")"
	mkdir -p "$PARALLEL_ROOT"
	parallel_root=$PARALLEL_ROOT
	set -m
	DESCENDANT_READY="$PARALLEL_ROOT/descendant.ready" sh -c '\''
		trap : TERM
		sh -c "trap : TERM; while :; do sleep 1; done" &
		: >"$DESCENDANT_READY"
		while :; do sleep 1; done
	'\'' &
	parallel_pids=("$!")
	set +m
	printf "%s\n" "${parallel_pids[0]}" >"$PID_FILE"
	attempt=0
	while [ ! -e "$PARALLEL_ROOT/descendant.ready" ] &&
		[ "$attempt" -lt 100 ]; do
		sleep 0.01
		attempt=$((attempt + 1))
	done
	[ -e "$PARALLEL_ROOT/descendant.ready" ] || exit 98
	false
	cleanup_parallel_tests
'
cleanup_status=$?
set -e
cleanup_pid=$(cat "$work/isolated.pid")
[ "$cleanup_status" -eq 1 ] || {
	echo "FAIL parallel cleanup changed failure status: $cleanup_status" >&2
	exit 1
}
attempt=0
while /bin/kill -0 -- "-$cleanup_pid" 2>/dev/null &&
	[ "$attempt" -lt 100 ]; do
	sleep 0.01
	attempt=$((attempt + 1))
done
if /bin/kill -0 -- "-$cleanup_pid" 2>/dev/null; then
	echo 'FAIL isolated process group survived runner cleanup' >&2
	exit 1
fi
cleanup_pid=
[ ! -e "$work/parallel-output" ] || {
	echo 'FAIL parallel output directory survived runner cleanup' >&2
	exit 1
}

set +e
RUNNER="$runner" PID_FILE="$work/completed.pid" \
	PARALLEL_ROOT="$work/completed-output" bash -c '
	set -u
	eval "$(sed -n "/^parallel_group_has_other_members() {/,/^cleanup_parallel_tests() {/p" "$RUNNER" | sed '\''$d'\'')"
	mkdir -p "$PARALLEL_ROOT"
	mkfifo "$PARALLEL_ROOT/hold"
	set -m
	DESCENDANT_READY="$PARALLEL_ROOT/descendant.ready" \
		STATUS_FILE="$PARALLEL_ROOT/status" \
		HOLD_FIFO="$PARALLEL_ROOT/hold" sh -c '\''
		trap : TERM
		sh -c "trap : TERM; while :; do sleep 1; done" &
		: >"$DESCENDANT_READY"
		printf "0\n" >"$STATUS_FILE"
		while :; do
			read -r _ <"$HOLD_FIFO" || true
		done
	'\'' &
	group_pid=$!
	set +m
	printf "%s\n" "$group_pid" >"$PID_FILE"
	attempt=0
	while [ ! -s "$PARALLEL_ROOT/status" ] && [ "$attempt" -lt 100 ]; do
		sleep 0.01
		attempt=$((attempt + 1))
	done
	[ -s "$PARALLEL_ROOT/status" ]
	/bin/kill -0 "$group_pid"
	parallel_group_has_other_members "$group_pid"
	terminate_parallel_group "$group_pid"
	wait "$group_pid" 2>/dev/null || true
	! /bin/kill -0 -- "-$group_pid" 2>/dev/null
'
completed_status=$?
set -e
cleanup_pid=$(cat "$work/completed.pid")
[ "$completed_status" -eq 0 ] || {
	echo 'FAIL completed isolated group descendant was not terminated' >&2
	exit 1
}
cleanup_pid=

leader_probe_line=$(sed -n '/^terminate_parallel_group() {/,/^}/p' "$runner" |
	grep -n -F '/bin/kill -0 "$group_pid"' | head -n 1 | cut -d: -f1)
group_signal_line=$(sed -n '/^terminate_parallel_group() {/,/^}/p' "$runner" |
	grep -n -F '/bin/kill -TERM -- "-$group_pid"' | head -n 1 | cut -d: -f1)
[ -n "$leader_probe_line" ] && [ -n "$group_signal_line" ] &&
	[ "$leader_probe_line" -lt "$group_signal_line" ] || {
	echo 'FAIL recycled PGID can be signalled without a live supervisor identity' >&2
	exit 1
}

echo 'PASS repository runner defines shared tests once, times each suite, and isolates parallel work explicitly'
