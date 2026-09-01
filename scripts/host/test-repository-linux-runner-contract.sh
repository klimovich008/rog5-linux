#!/bin/sh
set -eu

repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd -P)
runner=$repo/scripts/host/test-repository-linux.sh
work=$(mktemp -d)
cleanup_pid=
explicit_parent=
cleanup() {
	[ -z "$cleanup_pid" ] ||
		/bin/kill -TERM -- "-$cleanup_pid" 2>/dev/null || true
	[ -z "$cleanup_pid" ] ||
		/bin/kill -KILL -- "-$cleanup_pid" 2>/dev/null || true
	rm -rf -- "$work"
	[ -z "$explicit_parent" ] || rmdir -- "$explicit_parent"
}
trap cleanup EXIT HUP INT TERM

[ -f "$runner" ] && [ ! -L "$runner" ] && [ -x "$runner" ]
[ "$(grep -Fc 'shared_tests=(' "$runner")" -eq 1 ]
[ "$(grep -Fc 'tier_tests=()' "$runner")" -eq 1 ]
for token in \
	'DURATION %s %dms' \
	'if [[ $tier != active && $tier != probe ]]; then' \
	'isolated_tests=(' \
	'parallel_pids=(' \
	'parallel_status_files=(' \
	'test_tmp_parent=${ROG5_TEST_TMP_PARENT-${HOME:-}}' \
	'test_tmp_root=$(mktemp -d "$test_tmp_parent/.rog5-tests.XXXXXXXX")' \
	'export TMPDIR=$test_tmp_root' \
	'rm -rf -- "$test_tmp_root"' \
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

# Exercise only the actual scratch setup, never the repository suites. Leave
# HOME untouched and use a private, empty mktemp child even for the default.
check_tmp_parent() {
	expected_parent=$1
	shift
	RUNNER="$runner" EXPECTED_PARENT="$expected_parent" "$@" bash -c '
		set -euo pipefail
		fail() { echo "FAIL $*" >&2; exit 1; }
		test_tmp_root=
		trap '\''[[ -z $test_tmp_root ]] || rmdir -- "$test_tmp_root"'\'' EXIT
		eval "$(sed -n '\''/^test_tmp_parent=/,/^export TMPDIR=/p'\'' "$RUNNER")"
		[[ $test_tmp_parent == "$EXPECTED_PARENT" ]]
		[[ $test_tmp_root == "$EXPECTED_PARENT"/.rog5-tests.* ]]
		[[ $TMPDIR == "$test_tmp_root" && -d $TMPDIR && ! -L $TMPDIR ]]
		[[ $(stat -c %a "$TMPDIR") == 700 ]]
		child=$(mktemp -d)
		[[ $child == "$TMPDIR"/* ]]
		rmdir -- "$child"
	'
}

check_tmp_parent "${HOME:-}" env -u ROG5_TEST_TMP_PARENT
# Exercise a real short override independently of the outer test's nesting.
explicit_parent=$(mktemp -d '/tmp/r5 parent.XXXXXXXX')
check_tmp_parent "$explicit_parent" env ROG5_TEST_TMP_PARENT="$explicit_parent"
[ -z "$(ls -A "$explicit_parent")" ]
printf 'not a directory\n' >"$work/not-a-directory"
ln -s "$explicit_parent" "$work/linked-parent"
for invalid_parent in '' relative/path "$work/missing-parent" \
	"$work/not-a-directory" "$work/linked-parent"; do
	if check_tmp_parent "$invalid_parent" env ROG5_TEST_TMP_PARENT="$invalid_parent" \
		>"$work/parent.stdout" 2>"$work/parent.stderr"; then
		echo "FAIL invalid temporary parent accepted: $invalid_parent" >&2
		exit 1
	fi
	grep -Fxq 'FAIL repository test temporary parent is unavailable' "$work/parent.stderr"
done
# Root can write despite mode bits, so this effective-access check is non-root.
if [ "$(id -u)" -ne 0 ]; then
	mkdir "$work/read-only-parent"
	chmod 0500 "$work/read-only-parent"
	if check_tmp_parent "$work/read-only-parent" env ROG5_TEST_TMP_PARENT="$work/read-only-parent" \
		>"$work/parent.stdout" 2>"$work/parent.stderr"; then
		echo 'FAIL non-writable temporary parent accepted' >&2
		exit 1
	fi
	grep -Fxq 'FAIL repository test temporary parent is unavailable' "$work/parent.stderr"
	chmod 0700 "$work/read-only-parent"
fi
[ -z "$(sed -n '/^active_tests=(/,/^)/p' "$runner" |
	grep -F 'scripts/host/test-repository-linux-runner-contract.sh' || true)" ]
sed -n '/^shared_tests=(/,/^)/p' "$runner" |
	grep -Fq 'scripts/host/test-repository-linux-runner-contract.sh'
[ "$(grep -Fc 'scripts/host/test-repository-linux-runner-contract.sh' "$runner")" -eq 1 ]
echo 'PASS runner scratch uses explicit parent or unchanged HOME and rejects invalid parents'

# Reproduce the RAM-scratch regression without paying for the full suite.
long_parent=$work/abcdefghijklmnopqrstuvwxyzabcdefghijklmnopqrstuvwxyzabcdefghijklmnopqrstuvwxyz
mkdir "$long_parent"
if check_tmp_parent "$long_parent" env ROG5_TEST_TMP_PARENT="$long_parent" \
	>"$work/parent.stdout" 2>"$work/parent.stderr"; then
	echo 'FAIL overlong Unix socket scratch path accepted' >&2
	exit 1
fi
grep -Fxq 'FAIL repository test temporary parent cannot host Unix sockets' "$work/parent.stderr"
[ -z "$(ls -A "$long_parent")" ]
echo 'PASS overlong broker socket path refuses before repository suites'

shared=$(sed -n '/^shared_tests=(/,/^)/p' "$runner" |
	sed -n 's|^[[:space:]]*\(scripts/[^[:space:]]*\)$|\1|p')
[ -n "$shared" ]
duplicates=$(printf '%s\n' "$shared" | sort | uniq -d)
[ -z "$duplicates" ] || {
	echo "FAIL shared repository test is duplicated: $duplicates" >&2
	exit 1
}
declared=$(sed -n '/^active_tests=(/,/^)/p; /^shared_tests=(/,/^)/p' "$runner" |
	sed -n 's|^[[:space:]]*\(scripts/[^[:space:]]*\)$|\1|p')
for isolated in $(sed -n '/^isolated_tests=(/,/^)/p' "$runner" |
	sed -n 's|^[[:space:]]*\(scripts/[^[:space:]]*\)$|\1|p'); do
	printf '%s\n' "$declared" | grep -Fxq "$isolated" || {
		echo "FAIL isolated suite is outside the active/shared test lists: $isolated" >&2
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
	attempt=0
	while /bin/kill -0 -- "-$group_pid" 2>/dev/null &&
		[ "$attempt" -lt 100 ]; do
		sleep 0.01
		attempt=$((attempt + 1))
	done
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
