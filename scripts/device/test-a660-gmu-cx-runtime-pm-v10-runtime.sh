#!/bin/sh
# shellcheck disable=SC2016
set -eu

repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)
builder=$repo/scripts/device/build-a660-gmu-cx-runtime-pm-v10-runtime.sh
verifier=$repo/scripts/device/verify-a660-gmu-cx-runtime-pm-v10-runtime-sources.sh
baseline_patch=$repo/patches/runtime/a660-gmu-cx-runtime-pm-v10-baseline.patch
probe_patch=$repo/patches/runtime/a660-gmu-cx-runtime-pm-v10-probe.patch
trace_oracle=$repo/scripts/device/check-a660-gmu-cx-runtime-pm-v10-trace.sh
trace_oracle_test=$repo/scripts/device/test-a660-gmu-cx-runtime-pm-v10-trace-oracle.sh
consumed_v9_test=$repo/scripts/host/test-consume-a660-gmu-resume-entry-v9.sh
offline_report=$repo/test-results/2026-07-27-a660-gmu-cx-runtime-pm-v10-offline.md

for input in "$builder" "$verifier" "$trace_oracle" "$trace_oracle_test" \
	"$consumed_v9_test"; do
	[ -x "$input" ] || {
		echo "FAIL missing executable A660 GMU/CX runtime-PM v10 tool: $input" >&2
		exit 1
	}
	sh -n "$input"
done
for input in "$baseline_patch" "$probe_patch" "$offline_report"; do
	[ -f "$input" ] && [ ! -L "$input" ] || {
		echo "FAIL missing immutable A660 GMU/CX runtime-PM v10 input: $input" >&2
		exit 1
	}
done

for contract in \
	'build-a660-gmu-resume-entry-v9-runtime.sh' \
	'test-consume-a660-gmu-resume-entry-v9.sh' \
	'check-a660-gmu-cx-runtime-pm-v10-trace.sh' \
	'test-a660-gmu-cx-runtime-pm-v10-trace-oracle.sh' \
	'2026-07-27-a660-gmu-cx-runtime-pm-v10-offline.md' \
	'diagnostic_generation=v10' \
	'predecessor=v9_live_accepted_consumed' \
	'gmu_cx_runtime_pm_only=1' \
	'gmu_cx_runtime_pm_only=Y' \
	'gmu_resume_entry_only=N' \
	'ALLOW_MAINLINE_A660_GMU_CX_RUNTIME_PM_V10' \
	'rog5_gmu_v10_runtime_pm_resume' \
	'rog5_gmu_v10_runtime_pm_suspend' \
	'events/rpm/rpm_resume/enable' \
	'events/rpm/rpm_suspend/enable' \
	'3d6a000.gmu' \
	'genpd:0:3d6a000.gmu' \
	'genpd:1:3d6a000.gmu' \
	'trace_oracle_output=$("$trace_oracle" "$trace_snapshot")' \
	'gmu_runtime_pm=1/1 cx_runtime_pm=1/1' \
	'cx_suspend_ret=' \
	'gmu_runtime_status=suspended' \
	'cx_runtime_status=suspended' \
	'gx_runtime_pm=0' \
	'clocks=0 secure=0 mmio=0 irq=0 firmware_start=0 hfi=0' \
	'gem_snapshot=equal' \
	'c36fd352c48d624eff9f17fb8200c8f151209eae066d1f276ab3bff67c5d465d' \
	'5eef04eb711443acaaf4295e926577f90073b8ab62414cff3d18de2272d3a152' \
	'kernel/module delta=v10-msm-only'
do
	grep -Fq "$contract" "$builder" "$verifier" "$baseline_patch" \
		"$probe_patch" "$trace_oracle" "$trace_oracle_test" \
		"$offline_report" || {
		echo "FAIL A660 GMU/CX runtime-PM v10 path omits: $contract" >&2
		exit 1
	}
done

if grep -Eq \
	'(^|[;&|[:space:]])(fastboot|adb|ssh|scp)([[:space:]]|$)|dd[[:space:]].*of=/dev/|mount[[:space:]].*/dev/' \
	"$builder" "$verifier"
then
	echo 'FAIL A660 GMU/CX runtime-PM v10 runtime tooling controls a device or storage' >&2
	exit 1
fi

"$trace_oracle_test" >/dev/null
"$consumed_v9_test" >/dev/null

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
	if ALLOW_UNPINNED_A660_GMU_CX_RUNTIME_PM_V10=1 \
		"$verifier" "$mutated_baseline" "$mutated_probe" \
		>"$stage/mutations/$name.log" 2>&1
	then
		echo "FAIL v10 runtime verifier accepts mutation: $name" >&2
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

mutate_probe inherited-v9-authorization \
	's/ALLOW_MAINLINE_A660_GMU_CX_RUNTIME_PM_V10/ALLOW_MAINLINE_A660_GMU_RESUME_ENTRY_V9/g'
mutate_probe predecessor-diagnostic-enabled \
	's/gmu_cx_runtime_pm_only=1/gmu_resume_entry_only=1/'
mutate_probe missing-generic-resume \
	'/rog5_gmu_v10_runtime_pm_resume __pm_runtime_resume/d'
mutate_probe missing-generic-suspend \
	'/rog5_gmu_v10_runtime_pm_suspend __pm_runtime_suspend/d'
mutate_probe missing-rpm-resume-names \
	'/events\/rpm\/rpm_resume\/enable/d'
mutate_probe bypass-trace-oracle \
	'/trace_oracle_output=$("$trace_oracle" "$trace_snapshot")/d'
mutate_probe wrong-cx-index \
	's/genpd:0:3d6a000.gmu/genpd:1:3d6a000.gmu/g'
mutate_probe allow-gx \
	's/gx_runtime_pm=0/gx_runtime_pm=1/'
mutate_probe missing-suspended-state \
	'/cx_runtime_status=suspended/d'
mutate_probe missing-snapshot \
	'/cmp "$state_dir\/gem.before" "$state_dir\/gem.after"/d'
mutate_probe successful-open \
	's/OPEN_ERRNO=117/OPEN_OK/'
mutate_probe changed-msm-module \
	's/c36fd352c48d624eff9f17fb8200c8f151209eae066d1f276ab3bff67c5d465d/b485e8719d6ddf80542a5dc2fdf5bba795d40c69fa220b44571323a8a1d7d861/'
mutate_baseline wrong-predecessor \
	's/predecessor=v9_live_accepted_consumed/predecessor=v9_live_rejected_consumed/'
mutate_baseline writable-parameter \
	's/gmu_cx_runtime_pm_parameter_mode=0400/gmu_cx_runtime_pm_parameter_mode=0600/'

echo 'PASS A660 GMU/CX runtime-PM v10 runtime is reproducibly generated and rejects authorization, mode, trace, device, order, GX, state, snapshot, errno, module, predecessor, and parameter mutations'
