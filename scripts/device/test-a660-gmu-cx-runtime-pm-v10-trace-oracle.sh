#!/bin/sh
set -eu

repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)
oracle=$repo/scripts/device/check-a660-gmu-cx-runtime-pm-v10-trace.sh

[ -x "$oracle" ] || {
	echo 'FAIL missing executable A660 GMU/CX runtime-PM v10 trace oracle' >&2
	exit 1
}
sh -n "$oracle"

valid_unsigned='helper-1 [000] 1.000: rog5_gmu_v10_runtime_pm_resume: dev=0x100
helper-1 [000] 1.001: rpm_resume: 3d00000.gpu flags-4 cnt-1 dep-0 auto-1 p-0 irq-0 child-0
helper-1 [000] 1.002: rog5_gmu_v10_runtime_resume: dev=0x100
helper-1 [000] 1.003: rog5_gmu_v10_pm_resume:
helper-1 [000] 1.004: rog5_gmu_v10_resume:
helper-1 [000] 1.005: rog5_gmu_v10_mark_attempt:
helper-1 [000] 1.006: rog5_gmu_v10_mark_attempt_ret: ret=1
helper-1 [000] 1.007: rog5_gmu_v10_runtime_pm_resume: dev=0x200
helper-1 [000] 1.008: rpm_resume: 3d6a000.gmu flags-4 cnt-1 dep-0 auto-1 p-0 irq-0 child-0
helper-1 [000] 1.009: rog5_gmu_v10_runtime_pm_resume: dev=0x300
helper-1 [000] 1.010: rpm_resume: genpd:0:3d6a000.gmu flags-4 cnt-1 dep-0 auto-1 p-0 irq-0 child-0
helper-1 [000] 1.011: rog5_gmu_v10_runtime_pm_resume_ret: ret=0
helper-1 [000] 1.012: rog5_gmu_v10_runtime_pm_resume_ret: ret=0
helper-1 [000] 1.013: rog5_gmu_v10_runtime_pm_suspend: dev=0x200
helper-1 [000] 1.014: rpm_suspend: 3d6a000.gmu flags-5 cnt-0 dep-0 auto-1 p-0 irq-0 child-0
helper-1 [000] 1.015: rog5_gmu_v10_runtime_pm_suspend_ret: ret=0
helper-1 [000] 1.016: rog5_gmu_v10_runtime_pm_suspend: dev=0x300
helper-1 [000] 1.017: rpm_suspend: genpd:0:3d6a000.gmu flags-0 cnt-0 dep-0 auto-1 p-0 irq-0 child-0
helper-1 [000] 1.018: rog5_gmu_v10_runtime_pm_suspend_ret: ret=0
helper-1 [000] 1.019: rog5_gmu_v10_mark_passed:
helper-1 [000] 1.020: rog5_gmu_v10_mark_passed_ret: ret=1
helper-1 [000] 1.021: rog5_gmu_v10_resume_ret: ret=4294967179
helper-1 [000] 1.022: rog5_gmu_v10_pm_resume_ret: ret=4294967179
helper-1 [000] 1.023: rog5_gmu_v10_runtime_resume_ret: ret=4294967179
helper-1 [000] 1.024: rog5_gmu_v10_runtime_pm_resume_ret: ret=4294967179
helper-1 [000] 1.025: rog5_gmu_v10_rollback:
helper-1 [000] 1.026: rog5_gmu_v10_rollback_ret: ret=0'

expected_unsigned='PASS A660 GMU/CX runtime-PM v10 trace oracle returns=-117/-117/-117 gpu_runtime_pm=1 gmu_runtime_pm=1/1 cx_runtime_pm=1/1 cx_suspend_ret=0 generic_resume=3 generic_suspend=2'

run_accept() {
	label=$1
	fixture=$2
	expected=$3
	output=$(printf '%s\n' "$fixture" | "$oracle" -) || {
		echo "FAIL v10 trace oracle rejected $label" >&2
		exit 1
	}
	[ "$output" = "$expected" ] || {
		echo "FAIL v10 trace oracle changed $label output" >&2
		exit 1
	}
}

run_reject() {
	label=$1
	fixture=$2
	expected=$3
	set +e
	output=$(printf '%s\n' "$fixture" | "$oracle" - 2>&1)
	status=$?
	set -e
	[ "$status" -eq 1 ] || {
		echo "FAIL v10 trace oracle accepted $label" >&2
		exit 1
	}
	[ "$output" = "FAIL $expected" ] || {
		echo "FAIL v10 trace oracle changed $label rejection" >&2
		exit 1
	}
}

run_accept zero-extended "$valid_unsigned" "$expected_unsigned"

valid_signed=$(printf '%s\n' "$valid_unsigned" |
	sed 's/ret=4294967179/ret=-117/g')
run_accept signed "$valid_signed" "$expected_unsigned"

cx_already_suspended=$(printf '%s\n' "$valid_unsigned" |
	sed '/runtime_pm_suspend_ret: ret=0/{
		x
		s/^$/first/
		x
		b
	}
	/runtime_pm_suspend_ret: ret=0/s/ret=0/ret=1/')
run_accept cx-already-suspended "$cx_already_suspended" \
	'PASS A660 GMU/CX runtime-PM v10 trace oracle returns=-117/-117/-117 gpu_runtime_pm=1 gmu_runtime_pm=1/1 cx_runtime_pm=1/1 cx_suspend_ret=1 generic_resume=3 generic_suspend=2'

ambient='helper-1 [000] 0.998: rog5_gmu_v10_runtime_pm_resume: dev=0x888
helper-1 [000] 0.999: rog5_gmu_v10_runtime_pm_resume_ret: ret=1'
run_accept classified-ambient "$ambient
$valid_unsigned" \
	'PASS A660 GMU/CX runtime-PM v10 trace oracle returns=-117/-117/-117 gpu_runtime_pm=1 gmu_runtime_pm=1/1 cx_runtime_pm=1/1 cx_suspend_ret=0 generic_resume=4 generic_suspend=2'

wrong_gx=$(printf '%s\n' "$valid_unsigned" |
	sed 's/genpd:0:3d6a000[.]gmu/genpd:1:3d6a000.gmu/g')
run_reject GX-domain "$wrong_gx" 'GX-domain runtime-PM activity is present'

wrong_gmu_name=$(printf '%s\n' "$valid_unsigned" |
	sed 's/rpm_resume: 3d6a000[.]gmu/rpm_resume: 3d6a001.gmu/')
run_reject wrong-GMU-device "$wrong_gmu_name" \
	'exact GMU consumer runtime-resume identity count is 0, expected 1'

reversed_names=$(printf '%s\n' "$valid_unsigned" |
	sed 's/rpm_resume: 3d6a000[.]gmu/rpm_resume: TEMP.gmu/;
		s/rpm_resume: genpd:0:3d6a000[.]gmu/rpm_resume: 3d6a000.gmu/;
		s/rpm_resume: TEMP[.]gmu/rpm_resume: genpd:0:3d6a000.gmu/')
run_reject reversed-GMU-CX "$reversed_names" \
	'GMU consumer and linked CX supplier resume ordering changed'

wrong_gmu_suspend_pointer=$(printf '%s\n' "$valid_unsigned" |
	sed 's/runtime_pm_suspend: dev=0x200/runtime_pm_suspend: dev=0x400/')
run_reject GMU-pointer-mismatch "$wrong_gmu_suspend_pointer" \
	'GMU consumer resume/suspend device identity differs'

wrong_cx_suspend_pointer=$(printf '%s\n' "$valid_unsigned" |
	sed 's/runtime_pm_suspend: dev=0x300/runtime_pm_suspend: dev=0x400/')
run_reject CX-pointer-mismatch "$wrong_cx_suspend_pointer" \
	'linked CX supplier resume/suspend device identity differs'

duplicate_resume=$(printf '%s\n' "$valid_unsigned" |
	sed '/runtime_pm_resume: dev=0x300/p')
run_reject extra-diagnostic-resume "$duplicate_resume" \
	'diagnostic runtime-resume entry count is 3, expected 2'

missing_suspend=$(printf '%s\n' "$valid_unsigned" |
	sed '/runtime_pm_suspend: dev=0x300/d')
run_reject missing-CX-suspend "$missing_suspend" \
	'diagnostic runtime-suspend entry count is 1, expected 2'

bad_gmu_resume=$(printf '%s\n' "$valid_unsigned" |
	sed '0,/runtime_pm_resume_ret: ret=0/s//runtime_pm_resume_ret: ret=4294967280/')
run_reject failed-CX-resume "$bad_gmu_resume" \
	'linked CX supplier runtime resume did not return zero'

bad_gmu_suspend=$(printf '%s\n' "$valid_unsigned" |
	sed '0,/runtime_pm_suspend_ret: ret=0/s//runtime_pm_suspend_ret: ret=4294967280/')
run_reject failed-GMU-suspend "$bad_gmu_suspend" \
	'GMU consumer runtime suspend did not return zero'

bad_cx_suspend=$(printf '%s\n' "$valid_unsigned" |
	sed '/runtime_pm_suspend_ret: ret=0/{
		x
		s/^$/first/
		x
		b
	}
	/runtime_pm_suspend_ret: ret=0/s/ret=0/ret=2/')
run_reject invalid-CX-suspend "$bad_cx_suspend" \
	'linked CX supplier runtime suspend did not return zero or already-suspended'

failed_attempt=$(printf '%s\n' "$valid_unsigned" |
	sed 's/mark_attempt_ret: ret=1/mark_attempt_ret: ret=0/')
run_reject consumed-attempt "$failed_attempt" \
	'GMU/CX one-shot attempt was already consumed'

failed_pass=$(printf '%s\n' "$valid_unsigned" |
	sed 's/mark_passed_ret: ret=1/mark_passed_ret: ret=0/')
run_reject failed-pass-state "$failed_pass" \
	'GMU/CX one-shot did not reach passed state'

wrong_outer_return=$(printf '%s\n' "$valid_unsigned" |
	sed '0,/resume_ret: ret=4294967179/s//resume_ret: ret=4294967178/')
run_reject non-EUCLEAN "$wrong_outer_return" \
	'A6xx GMU resume return is not signed EUCLEAN'

forbidden_clock="$valid_unsigned
helper-1 [000] 1.027: rog5_gmu_v10_clk_rate:"
run_reject clock-work "$forbidden_clock" \
	'forbidden post-GMU/CX boundary activity is present'

successful_rollback=$(printf '%s\n' "$valid_unsigned" |
	sed 's/rollback_ret: ret=0/rollback_ret: ret=1/')
run_reject failed-rollback "$successful_rollback" \
	'GPU-load rollback did not return zero'

zero_gpu=$(printf '%s\n' "$valid_unsigned" |
	sed 's/dev=0x100/dev=0x0/g')
run_reject null-GPU "$zero_gpu" 'Adreno runtime-resume device is null'

echo 'PASS A660 GMU/CX runtime-PM v10 trace oracle accepts exact balanced GMU/index-0-CX PM and rejects identity, order, state, rollback, or boundary mutations'
