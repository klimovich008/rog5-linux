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

# Execute the runner's real cleanup and signal traps without starting suites.
# Signal handling must preserve failure even when the preceding command passed.
python3 - "$runner" <<'PY'
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile

source = Path(sys.argv[1]).read_text()
start = source.index("cleanup_parallel_tests() {\n")
end = source.index("set -m\nfor test_path", start)
cleanup_and_traps = source[start:end]
for action, expected in (("exit 0", 0), ("exit 23", 23),
                         ('/bin/kill -HUP "$$"', 129),
                         ('/bin/kill -INT "$$"', 130),
                         ('/bin/kill -TERM "$$"', 143)):
    with tempfile.TemporaryDirectory(prefix="rog5-runner-signal-") as tmp:
        parent = Path(tmp)
        (parent / "keep").write_text("unrelated fixture")
        script = ("set -euo pipefail\nparallel_pids=()\nparallel_root="
                  + shlex.quote(str(parent / "parallel")) + "\ntest_tmp_root="
                  + shlex.quote(str(parent / "tests"))
                  + '\nmkdir "$parallel_root" "$test_tmp_root"\n'
                  + cleanup_and_traps + "\ntrue\n" + action
                  + "\necho UNEXPECTED_CONTINUATION\n")
        result = subprocess.run(["bash", "-c", script], capture_output=True,
                                text=True, timeout=5)
        if result.returncode != expected or result.stdout or result.stderr:
            raise SystemExit(f"runner {action}: expected {expected}, got {result}")
        if {p.name for p in parent.iterdir()} != {"keep"}:
            raise SystemExit(f"runner {action}: incomplete or excessive cleanup")
print("PASS runner signals fail closed, preserve exit status and clean owned scratch")
PY

echo 'PASS repository runner defines shared tests once, times each suite, and isolates parallel work explicitly'


# Exercise the actual bounded launcher with tiny child fixtures, not repository
# suites. Events use a locked file so cap/ordering checks do not rely on timing.
python3 - "$runner" "$repo/scripts/host/repository-test-workers.py" <<'PYTEST'
import importlib.util
import json
import os
from pathlib import Path
import shlex
import signal
import subprocess
import sys
import tempfile
import time

spec = importlib.util.spec_from_file_location('worker_limit', sys.argv[2])
workers = importlib.util.module_from_spec(spec)
spec.loader.exec_module(workers)
for affinity, quotas, override, expected in (
        (8, ['max 100000'], None, 2), (1, ['max 100000'], None, 1),
        (8, ['max 100000', '200000 100000'], None, 2),
        (8, ['150000 100000'], '32', 1), (8, ['50000 100000'], None, 1),
        (8, ['400000 100000'], '3', 3), (8, ['200000 100000'], '32', 2),
        (8, ['max 100000'], '1', 1)):
    assert workers.worker_count(affinity, quotas, override) == expected
for invalid in ('', '0', '-1', '33', '1.5', '02', '999999999999'):
    try:
        workers.worker_count(8, [], invalid)
    except ValueError:
        pass
    else:
        raise SystemExit('accepted invalid worker limit ' + repr(invalid))
with tempfile.TemporaryDirectory(prefix='rog5-quota-') as tmp:
    root = Path(tmp); (root/'parent/child').mkdir(parents=True)
    (root/'cgroup').write_text('0::/parent/child\n')
    (root/'parent/cpu.max').write_text('150000 100000')
    (root/'parent/child/cpu.max').write_text('max 100000')
    assert workers.worker_count(8, workers.quotas_for_process(root/'cgroup', root)) == 1
    (root/'parent/child/cpu.max').write_text('2 0')
    try:
        workers.worker_count(8, workers.quotas_for_process(root/'cgroup', root))
    except ValueError:
        pass
    else:
        raise SystemExit('accepted invalid discovered quota')
    (root/'cgroup').write_text('2:cpu:/legacy\n')
    assert workers.worker_count(8, workers.quotas_for_process(root/'cgroup', root)) == 1
print('PASS worker limits honor affinity, inherited/fractional quota and explicit cap')

source = Path(sys.argv[1]).read_text()
start = source.index('parallel_root=$(mktemp -d)\n')
end = source.index('for test_path in "${tests[@]}"; do', start)
queue = source[start:end]
fixture = r"""
import fcntl, json, os, pathlib, subprocess, sys, time
root=pathlib.Path(sys.argv[1]); name=sys.argv[2]; mode=sys.argv[3]
def event(kind):
    with (root/'events').open('a') as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        f.write(json.dumps([kind,name,os.getpgrp()])+'\n');f.flush()
event('start')
(root/(name+'-started')).touch()
if mode=='backfill' and name=='first':
    deadline=time.monotonic()+4
    while not (root/'third-started').exists():
        if time.monotonic()>deadline:raise SystemExit(91)
        time.sleep(.01)
elif mode=='backfill' and name=='second':
    deadline=time.monotonic()+4
    while not (root/'first-started').exists():
        if time.monotonic()>deadline:raise SystemExit(93)
        time.sleep(.01)
elif mode=='backfill' and name=='third':
    (root/'third-started').touch()
elif mode=='fail' and name=='first':
    deadline=time.monotonic()+4
    while not (root/'second-started').exists():
        if time.monotonic()>deadline:raise SystemExit(92)
        time.sleep(.01)
    event('end');raise SystemExit(7)
elif mode=='fail' and name=='second':
    (root/'second-started').touch();time.sleep(30)
elif mode=='ready-failure' and name=='second':
    event('end');raise SystemExit(7)
elif mode=='descendant' and name=='first':
    subprocess.Popen(['sleep','30'])
event('end')
print('FIXTURE '+name)
"""
for mode, cap, expected in (('serial',1,0),('backfill',2,0),('fail',2,1),('descendant',1,1),('ready-failure',2,1)):
    with tempfile.TemporaryDirectory(prefix='rog5-worker-queue-') as tmp:
        root=Path(tmp); script=root/'fixture.py';script.write_text(fixture)
        (root/'scratch').mkdir()
        preamble=("set -euo pipefail\nfail() { echo \"FAIL $*\" >&2; exit 1; }\n"
                  "selected_test() { [[ $1 != skipped ]]; }\n"
                  "isolated_tests=(first second third skipped)\nparallel_running=0\n"
                  +f"parallel_workers={cap}\n"
                  +"test_tmp_root="+shlex.quote(str(root/'scratch'))+"\n"
                  +"export TMPDIR=$test_tmp_root\n"
                  +"run_test() { python3 "+shlex.quote(str(script))+" "+shlex.quote(str(root))
                  +' "$1" '+shlex.quote(mode)+"; }\n")
        # Observe enqueue itself, even if cleanup beats the new child's first instruction.
        preamble += ('mkfifo() { [[ ${!#} != */3.hold ]] || touch '
                     +shlex.quote(str(root/'third-enqueued'))+'; command mkfifo "$@"; }\n')
        exercised_queue=queue
        if mode=='ready-failure':
            # Publish both outcomes before entering the unchanged real reaper body.
            exercised_queue=queue.replace('reap_parallel_test() {','actual_reap_parallel_test() {')
            wrapper='''reap_parallel_test() {
 for ((attempt=0; attempt<400; attempt++)); do
  [[ ! -s $parallel_root/1.status || ! -s $parallel_root/2.status ]] || break
  sleep .01
 done
 [[ -s $parallel_root/1.status && -s $parallel_root/2.status ]] || exit 94
 actual_reap_parallel_test
}
'''
            exercised_queue=exercised_queue.replace('set -m\nfor test_path',wrapper+'set -m\nfor test_path')
        result=subprocess.run(['bash','-c',preamble+exercised_queue],capture_output=True,text=True,timeout=8)
        events=[json.loads(line)for line in (root/'events').read_text().splitlines()]
        groups={row[2]for row in events}
        try:
            if result.returncode != expected:
                raise SystemExit(f'{mode}: expected {expected}, got {result}')
            starts=[name for kind,name,_ in events if kind=='start']
            assert 'skipped' not in starts
            if expected==0:
                live=set();peak=0
                for kind,name,_ in events:
                    if kind=='start':live.add(name);peak=max(peak,len(live))
                    else:live.remove(name)
                assert not live and peak<=cap and sorted(starts)==['first','second','third']
                if mode=='serial':assert starts==['first','second','third']
                assert all('FIXTURE '+name in result.stdout for name in starts)
                if mode=='backfill':
                    assert peak==2
                    assert next(i for i,e in enumerate(events)if e[:2]==['start','third']) < next(i for i,e in enumerate(events)if e[:2]==['end','first'])
            else:
                assert 'third' not in starts
                assert not (root/'third-enqueued').exists()
                if mode=='ready-failure':assert 'isolated offline test failed: second' in result.stderr
                elif mode=='fail':assert 'isolated offline test failed: first' in result.stderr
                else:assert 'left background descendants: first' in result.stderr
            assert not (root/'scratch').exists()
            deadline=time.monotonic()+2
            while True:
                live=[]
                for group in groups:
                    try:os.killpg(group,0);live.append(group)
                    except ProcessLookupError:pass
                if not live:break
                if time.monotonic()>deadline:raise SystemExit('fixture groups survived cleanup')
                time.sleep(.01)
        finally:
            for group in groups:
                try:os.killpg(group,signal.SIGKILL)
                except ProcessLookupError:pass
print('PASS actual queue caps concurrency, backfills, preserves selection/logs and cleans failure/descendants')
PYTEST
