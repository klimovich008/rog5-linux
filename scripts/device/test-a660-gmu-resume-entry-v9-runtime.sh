#!/bin/sh
# shellcheck disable=SC2016
set -eu

repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)
builder=$repo/scripts/device/build-a660-gmu-resume-entry-v9-runtime.sh
verifier=$repo/scripts/device/verify-a660-gmu-resume-entry-v9-runtime-sources.sh
baseline_patch=$repo/patches/runtime/a660-gmu-resume-entry-v9-baseline.patch
probe_patch=$repo/patches/runtime/a660-gmu-resume-entry-v9-probe.patch
trace_oracle=$repo/scripts/device/check-a660-gmu-resume-entry-v9-trace.sh
trace_oracle_test=$repo/scripts/device/test-a660-gmu-resume-entry-v9-trace-oracle.sh
consumed_v8_test=$repo/scripts/host/test-consume-a660-gmu-resume-entry-v8.sh

for input in "$builder" "$verifier" "$trace_oracle" "$trace_oracle_test" \
	"$consumed_v8_test"; do
	[ -x "$input" ] || {
		echo "FAIL missing executable A660 GMU resume-entry v9 runtime tool: $input" >&2
		exit 1
	}
	sh -n "$input"
done
for input in "$baseline_patch" "$probe_patch"; do
	[ -f "$input" ] && [ ! -L "$input" ] || {
		echo "FAIL missing A660 GMU resume-entry v9 runtime patch: $input" >&2
		exit 1
	}
done

for contract in \
	'build-a660-gmu-resume-entry-v8-runtime.sh' \
	'2026-07-26-a660-gmu-resume-entry-v8-live-rejected.md' \
	'test-consume-a660-gmu-resume-entry-v8.sh' \
	'check-a660-gmu-resume-entry-v9-trace.sh' \
	'test-a660-gmu-resume-entry-v9-trace-oracle.sh' \
	fe5a6130cce3063ef6a0b1093d492d2a35763781f23af029c2959548cb092a9c \
	48325037a54fe737aa4c623a1be59f644952bd21d9f13f0bba6a6563fea6f223 \
	b485e8719d6ddf80542a5dc2fdf5bba795d40c69fa220b44571323a8a1d7d861 \
	'predecessor=v8_live_rejected_consumed' \
	'predecessor_consumption_commit=ff1250f' \
	'diagnostic_generation=v9' \
	'ALLOW_MAINLINE_A660_GMU_RESUME_ENTRY_V9' \
	'ret=$retval:u32' \
	'adreno_runtime_resume dev=$arg1:x64' \
	'__pm_runtime_resume dev=$arg1:x64' \
	'trace_oracle_output=$("$trace_oracle" "$trace_snapshot")' \
	'gpu_runtime_pm=1 generic_runtime_pm=' \
	'inner_runtime_pm=0 clocks=0 irq=0 hfi=0' \
	'gem_snapshot=equal' \
	'sed '\''s/v8/v9/g'\''' \
	'kernel/module unchanged'
do
	grep -Fq "$contract" "$builder" "$verifier" "$baseline_patch" \
		"$probe_patch" "$trace_oracle" "$trace_oracle_test" || {
		echo "FAIL A660 GMU resume-entry v9 runtime path omits: $contract" >&2
		exit 1
	}
done

if grep -Eq \
	'(^|[;&|[:space:]])(fastboot|adb|ssh|scp)([[:space:]]|$)|dd[[:space:]].*of=/dev/|mount[[:space:]].*/dev/' \
	"$builder" "$verifier"
then
	echo 'FAIL A660 GMU resume-entry v9 runtime tooling controls a device or storage' >&2
	exit 1
fi

"$trace_oracle_test" >/dev/null
"$consumed_v8_test" >/dev/null

stage=$(mktemp -d)
trap 'rm -rf -- "$stage"' EXIT HUP INT TERM
install -d "$stage/a" "$stage/b" "$stage/mutations"
"$builder" "$stage/a/baseline" "$stage/a/probe" >/dev/null
"$builder" "$stage/b/baseline" "$stage/b/probe" >/dev/null
cmp "$stage/a/baseline" "$stage/b/baseline"
cmp "$stage/a/probe" "$stage/b/probe"
"$verifier" "$stage/a/baseline" "$stage/a/probe" >/dev/null
"$verifier" "$stage/b/baseline" "$stage/b/probe" >/dev/null

set +e
"$builder" "$stage/a/baseline" "$stage/a/probe" >/dev/null 2>&1
existing_output=$?
"$builder" "$stage/missing/baseline" "$stage/missing/probe" \
	>/dev/null 2>&1
missing_parent=$?
set -e
[ "$existing_output" -ne 0 ]
[ "$missing_parent" -ne 0 ]

expect_rejected() {
	name=$1
	mutated_baseline=$2
	mutated_probe=$3
	if ALLOW_UNPINNED_A660_GMU_ENTRY_V9_RUNTIME=1 \
		"$verifier" "$mutated_baseline" "$mutated_probe" \
		>"$stage/mutations/$name.log" 2>&1
	then
		echo "FAIL v9 runtime verifier accepts mutation: $name" >&2
		exit 1
	fi
}

mutation=0
mutate_probe() {
	name=$1
	expression=$2
	mutation=$((mutation + 1))
	output=$stage/mutations/probe.$mutation
	sed "$expression" "$stage/a/probe" >"$output"
	expect_rejected "$name" "$stage/a/baseline" "$output"
}

mutate_baseline() {
	name=$1
	expression=$2
	mutation=$((mutation + 1))
	output=$stage/mutations/baseline.$mutation
	sed "$expression" "$stage/a/baseline" >"$output"
	expect_rejected "$name" "$output" "$stage/a/probe"
}

mutate_probe signed-64-return \
	's/rog5_gmu_v9_runtime_resume_ret msm:adreno_runtime_resume ret=$retval:u32/rog5_gmu_v9_runtime_resume_ret msm:adreno_runtime_resume ret=$retval:s64/'
mutate_probe missing-runtime-resume-device \
	's/adreno_runtime_resume dev=$arg1:x64/adreno_runtime_resume/'
mutate_probe missing-generic-runtime-pm-device \
	's/__pm_runtime_resume dev=$arg1:x64/__pm_runtime_resume/'
mutate_probe bypass-trace-oracle \
	'/trace_oracle_output=$("$trace_oracle" "$trace_snapshot")/d'
mutate_probe restore-global-runtime-pm-count \
	"s/require_event_count rog5_gmu_v9_clk_rate 0/require_event_count rog5_gmu_v9_runtime_pm 1/"
mutate_probe allow-inner-runtime-pm \
	's/rog5_gmu_v9_a6xx_pm_resume rog5_gmu_v9_hfi_start/rog5_gmu_v9_a6xx_pm_resume rog5_gmu_v9_resume/'
mutate_probe missing-snapshot \
	'/cmp "$state_dir\/gem.before" "$state_dir\/gem.after"/d'
mutate_probe successful-open \
	's/OPEN_ERRNO=117/OPEN_OK/'
mutate_probe inherited-v8-authorization \
	's/ALLOW_MAINLINE_A660_GMU_RESUME_ENTRY_V9/ALLOW_MAINLINE_A660_GMU_RESUME_ENTRY_V8/g'
mutate_baseline wrong-predecessor \
	's/predecessor=v8_live_rejected_consumed/predecessor=v8_live_accepted_consumed/'
mutate_baseline writable-entry-mode \
	's/gmu_entry_parameter_mode=0400/gmu_entry_parameter_mode=0600/'
mutate_baseline changed-oracle-hash \
	's/48325037a54fe737aa4c623a1be59f644952bd21d9f13f0bba6a6563fea6f223/08325037a54fe737aa4c623a1be59f644952bd21d9f13f0bba6a6563fea6f223/g'

echo 'PASS A660 GMU resume-entry v9 runtime is reproducibly generated and rejects signed-width, device-scope, oracle, global-PM, inner-PM, snapshot, errno, authorization, predecessor, mode, and oracle-hash mutations'
