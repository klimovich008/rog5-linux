#!/usr/bin/env bash
set -euo pipefail

fail() {
	echo "FAIL $*" >&2
	exit 1
}

repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
list_only=no
if [[ ${1:-} == --list ]]; then
	list_only=yes
	shift
fi
tier=${1:-quick}
case $tier in
	active|board|ci|nightly|probe|quick|rootfs) ;;
	*) fail 'usage: test-repository-linux.sh [--list] [active|board|ci|nightly|probe|quick|rootfs]' ;;
esac

repository_preflight() {
for command in bash date dirname dtc gcc git head nm openssl pkg-config python3 sh \
	ssh-keygen strings; do
	command -v "$command" >/dev/null ||
		fail "missing repository-test command: $command"
done
if [[ $tier == quick || $tier == rootfs ]]; then
	pkg-config --exists vulkan ||
		fail 'quick tier requires Vulkan headers and loader metadata'
	cgroup_relative=$(sed -n 's/^0:://p' /proc/self/cgroup)
	[[ -n $cgroup_relative && $cgroup_relative != / ]] ||
		fail 'quick tier requires a non-root delegated cgroup v2'
	cgroup_parent=/sys/fs/cgroup$cgroup_relative
	for control in cgroup.procs cgroup.events cgroup.kill; do
		[[ -f $cgroup_parent/$control ]] ||
			fail "quick tier delegated cgroup lacks $control"
	done
	[[ -w $cgroup_parent ]] ||
		fail 'quick tier cgroup is not delegated writable'
fi

# Entry points, Markdown links, secret scan and (outside active/probe) the
# shell/Python syntax of every tracked script: scripts/host/check-repository-static.py.
static_args=()
if [[ $tier == active || $tier == probe ]]; then
	static_args=(--skip-syntax)
fi
python3 "$repo/scripts/host/check-repository-static.py" --repo "$repo" "${static_args[@]}" ||
	fail 'static repository check'

}

# configs/repository-tests.json is the only test registry: each row names the
# tiers that select it. Keep the registry order; there are no shell lists.
list_tier_tests() {
	python3 - "$repo/configs/repository-tests.json" "$1" <<'PYTIER'
import json, sys
for row in json.load(open(sys.argv[1]))['tests']:
    if sys.argv[2] in row['tiers']:
        print(row['path'])
PYTIER
}
mapfile -t tests < <(list_tier_tests "$tier")
[[ ${#tests[@]} -gt 0 ]] || fail "registry selects no tests for tier $tier"
if [[ $list_only == yes ]]; then
	printf '%s\n' "${tests[@]}"
	exit 0
fi

# Union coverage without rerunning overlapping suites. Preserve first-seen
# order and the existing explicitly isolated/shared-state scheduling policy.
declare -A seen_tests=()
unique_tests=()
for selected in "${tests[@]}"; do
	[[ ! ${seen_tests[$selected]+yes} ]] || continue
	seen_tests[$selected]=1
	unique_tests+=("$selected")
done
tests=("${unique_tests[@]}")


report_root=${ROG5_TEST_REPORT_DIR:-$repo/build/test-reports/$(date -u +%Y%m%dT%H%M%S)-$$}
python3 "$repo/scripts/host/repository-test-report.py" init "$repo" "$report_root" "$tier" "${tests[@]}"
trap 'status=$?; python3 "$repo/scripts/host/repository-test-report.py" summary "$repo" "$report_root"; exit "$status"' EXIT
repository_preflight
for test_path in "${tests[@]}"; do
	test_file=$repo/$test_path
	[[ -f $test_file && ! -L $test_file ]] ||
		fail "missing core offline test: $test_path"
	case $test_file in
		*.py) ;;
		*) [[ -x $test_file ]] ||
			fail "offline test is not executable: $test_path" ;;
	esac
done


run_test() {
	test_path=$1
	test_file=$repo/$test_path
	started=$(date +%s%N)
	set +e
	python3 "$repo/scripts/host/repository-test-report.py" run "$repo" "$report_root" "$test_path"
	status=$?
	set -e
	finished=$(date +%s%N)
	elapsed_ms=$(((finished - started) / 1000000))
	printf 'DURATION %s %dms\n' "$test_path" "$elapsed_ms"
	return "$status"
}

isolated_tests=(
)
mapfile -t isolated_tests < <(python3 - "$repo/configs/repository-tests.json" <<'PYMANIFEST'
import json,sys
for row in json.load(open(sys.argv[1]))['tests']:
    if row['resource_class']=='isolated': print(row['path'])
PYMANIFEST
)
selected_test() {
	local candidate=$1
	local selected
	for selected in "${tests[@]}"; do
		[[ $selected != "$candidate" ]] || return 0
	done
	return 1
}
parallel_workers=$(python3 "$repo/scripts/host/repository-test-workers.py") ||
	fail 'cannot determine bounded isolated test worker count'
echo "ISOLATED_WORKERS $parallel_workers"
parallel_running=0
# An unset override preserves HOME; an explicitly empty override is invalid.
test_tmp_parent=${ROG5_TEST_TMP_PARENT-${HOME:-}}
[[ $test_tmp_parent == /* && -d $test_tmp_parent &&
	! -L $test_tmp_parent && -w $test_tmp_parent ]] ||
	fail 'repository test temporary parent is unavailable'
test_tmp_root=$(mktemp -d "$test_tmp_parent/.rog5-tests.XXXXXXXX")
chmod 0700 "$test_tmp_root"
# Prove the actual longest host-broker fixture path before costly suites.
# AF_UNIX has a byte limit even when the containing directory is writable.
if ! python3 - "$test_tmp_root" <<'PY'
from pathlib import Path
import socket
import sys
import tempfile

try:
    with tempfile.TemporaryDirectory(prefix="rog5-host-socket-test-", dir=sys.argv[1]) as fixture:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as listener:
            listener.bind(str(Path(fixture) / "broker-peer.sock"))
except OSError:
    raise SystemExit("test scratch cannot host the broker Unix socket; choose a shorter parent")
PY
then
	rmdir -- "$test_tmp_root"
	test_tmp_root=
	fail 'repository test temporary parent cannot host Unix sockets'
fi
export TMPDIR=$test_tmp_root
parallel_root=$(mktemp -d)
parallel_pids=()
parallel_paths=()
parallel_status_files=()
parallel_group_has_other_members() {
	local group_pid=$1
	local member_pid member_pgid
	while read -r member_pid member_pgid; do
		if [[ $member_pgid == "$group_pid" && $member_pid != "$group_pid" ]]; then
			return 0
		fi
	done < <(ps -e -o pid= -o pgid=)
	return 1
}
terminate_parallel_group() {
	local group_pid=$1
	local attempt=0
	/bin/kill -0 "$group_pid" 2>/dev/null || return 1
	/bin/kill -TERM -- "-$group_pid" 2>/dev/null || return 1
	while [[ $attempt -lt 100 ]]; do
		/bin/kill -0 "$group_pid" 2>/dev/null || return 1
		if ! parallel_group_has_other_members "$group_pid"; then
			/bin/kill -KILL "$group_pid" 2>/dev/null || return 1
			return 0
		fi
		sleep 0.01
		attempt=$((attempt + 1))
	done
	/bin/kill -0 "$group_pid" 2>/dev/null || return 1
	/bin/kill -KILL -- "-$group_pid" 2>/dev/null
}
finish_parallel_test() {
	local index=$1
	local log pid status_file wait_status had_descendants
	log=$parallel_root/$((index + 1)).log
	pid=${parallel_pids[$index]}
	status_file=${parallel_status_files[$index]}
	read -r wait_status <"$status_file"
	[[ $wait_status =~ ^[0-9]+$ ]] ||
		fail "isolated offline test returned an invalid status: ${parallel_paths[$index]}"
	had_descendants=false
	parallel_group_has_other_members "$pid" && had_descendants=true
	terminate_parallel_group "$pid" ||
		fail "isolated offline test supervisor identity was lost: ${parallel_paths[$index]}"
	wait "$pid" 2>/dev/null || true
	parallel_pids[$index]=
	if [[ $wait_status == 0 ]]; then
		if $had_descendants; then
			fail "isolated offline test left background descendants: ${parallel_paths[$index]}"
		fi
		cat "$log"
	else
		cat "$log" >&2
		fail "isolated offline test failed: ${parallel_paths[$index]}"
	fi
	parallel_running=$((parallel_running - 1))
}
reap_parallel_test() {
	local index pid reaped
	while :; do
		reaped=false
		for index in "${!parallel_pids[@]}"; do
			pid=${parallel_pids[$index]}
			[[ -n $pid ]] || continue
			if [[ -s ${parallel_status_files[$index]} ]]; then
				finish_parallel_test "$index"
				reaped=true
				continue
			fi
			/bin/kill -0 "$pid" 2>/dev/null || {
				wait "$pid" 2>/dev/null || true
				parallel_pids[$index]=
				fail "isolated offline test supervisor exited early: ${parallel_paths[$index]}"
			}
		done
		# Observe every already-ready failure before permitting a refill.
		$reaped && return
		sleep 0.01
	done
}
cleanup_parallel_tests() {
	cleanup_status=$?
	trap - EXIT HUP INT TERM
	for pid in "${parallel_pids[@]}"; do
		[[ -z $pid ]] || terminate_parallel_group "$pid" || true
	done
	for pid in "${parallel_pids[@]}"; do
		[[ -z $pid ]] || wait "$pid" 2>/dev/null || true
	done
	if [[ -n ${report_root:-} ]]; then
		if ! python3 "$repo/scripts/host/repository-test-report.py" summary "$repo" "$report_root"; then
			[[ $cleanup_status -ne 0 ]] || cleanup_status=1
		fi
	fi
	rm -rf -- "$parallel_root"
	[[ -z ${test_tmp_root:-} ]] || rm -rf -- "$test_tmp_root"
	exit "$cleanup_status"
}
trap cleanup_parallel_tests EXIT
trap 'exit 129' HUP
trap 'exit 130' INT
trap 'exit 143' TERM
set -m
for test_path in "${isolated_tests[@]}"; do
	selected_test "$test_path" || continue
	while [[ $parallel_running -ge $parallel_workers ]]; do
		reap_parallel_test
	done
	parallel_paths+=("$test_path")
	status_file=$parallel_root/${#parallel_paths[@]}.status
	hold_fifo=$parallel_root/${#parallel_paths[@]}.hold
	mkfifo -- "$hold_fifo"
	parallel_status_files+=("$status_file")
	(
		trap : TERM
		if run_test "$test_path"; then
			test_status=0
		else
			test_status=$?
		fi
		printf '%s\n' "$test_status" >"$status_file"
		while :; do
			read -r _ <"$hold_fifo" || true
		done
	) >"$parallel_root/${#parallel_paths[@]}.log" 2>&1 &
	parallel_pids+=("$!")
	parallel_running=$((parallel_running + 1))
done
set +m
while [[ $parallel_running -gt 0 ]]; do
	reap_parallel_test
done

for test_path in "${tests[@]}"; do
	case " ${isolated_tests[*]} " in
		*" $test_path "*) continue ;;
	esac
	if ! run_test "$test_path"; then
		fail "sequential offline test failed: $test_path"
	fi
done

echo "PASS repository Linux $tier tier"
