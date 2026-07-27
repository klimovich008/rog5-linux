#!/bin/sh
set -eu

repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)
oracle=$repo/scripts/device/check-a660-gmu-resume-entry-v9-trace.sh

[ -x "$oracle" ] || {
	echo 'FAIL missing executable A660 GMU resume-entry v9 trace oracle' >&2
	exit 1
}
sh -n "$oracle"

valid_unsigned='helper-1 [000] 1.000: rog5_gmu_v9_runtime_pm: dev=0x111
helper-1 [000] 1.001: rog5_gmu_v9_runtime_pm: dev=0x222
helper-1 [000] 1.002: rog5_gmu_v9_runtime_pm: dev=0x333
helper-1 [000] 1.003: rog5_gmu_v9_runtime_resume: dev=0x222
helper-1 [000] 1.004: rog5_gmu_v9_pm_resume:
helper-1 [000] 1.005: rog5_gmu_v9_resume:
helper-1 [000] 1.006: rog5_gmu_v9_resume_ret: ret=4294967179
helper-1 [000] 1.007: rog5_gmu_v9_pm_resume_ret: ret=4294967179
helper-1 [000] 1.008: rog5_gmu_v9_runtime_resume_ret: ret=4294967179'

run_accept() {
	label=$1
	fixture=$2
	expected=$3
	output=$(printf '%s\n' "$fixture" | "$oracle" -) || {
		echo "FAIL v9 trace oracle rejected $label" >&2
		exit 1
	}
	[ "$output" = "$expected" ] || {
		echo "FAIL v9 trace oracle changed $label output" >&2
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
		echo "FAIL v9 trace oracle accepted $label" >&2
		exit 1
	}
	[ "$output" = "FAIL $expected" ] || {
		echo "FAIL v9 trace oracle changed $label rejection" >&2
		exit 1
	}
}

run_accept zero-extended "$valid_unsigned" \
	'PASS A660 GMU resume-entry v9 trace oracle returns=-117/-117/-117 gpu_runtime_pm=1 generic_runtime_pm=3'

valid_signed=$(printf '%s\n' "$valid_unsigned" |
	sed 's/ret=4294967179/ret=-117/g')
run_accept signed "$valid_signed" \
	'PASS A660 GMU resume-entry v9 trace oracle returns=-117/-117/-117 gpu_runtime_pm=1 generic_runtime_pm=3'

wrong_return=$(printf '%s\n' "$valid_unsigned" |
	sed '0,/ret=4294967179/s//ret=4294967178/')
run_reject non-EUCLEAN "$wrong_return" \
	'A6xx GMU resume return is not signed EUCLEAN'

malformed_return=$(printf '%s\n' "$valid_unsigned" |
	sed '0,/ret=4294967179/s//ret=not-an-int/')
run_reject malformed-return "$malformed_return" \
	'A6xx GMU resume return is malformed'

overflow_return=$(printf '%s\n' "$valid_unsigned" |
	sed '0,/ret=4294967179/s//ret=4294967296/')
run_reject overflow-return "$overflow_return" \
	'A6xx GMU resume return is outside signed-32 transport'

missing_gpu_pm=$(printf '%s\n' "$valid_unsigned" |
	sed '/runtime_pm: dev=0x222/d')
run_reject missing-GPU-runtime-PM "$missing_gpu_pm" \
	'GPU device outer runtime-PM count is 0, expected 1'

duplicate_gpu_pm=$(printf '%s\n' "$valid_unsigned" |
	sed '/runtime_pm: dev=0x222/p')
run_reject duplicate-GPU-runtime-PM "$duplicate_gpu_pm" \
	'GPU device outer runtime-PM count is 2, expected 1'

reversed_order=$(printf '%s\n' "$valid_unsigned" |
	sed '/runtime_pm: dev=0x222/d; /runtime_resume: dev=0x222/a\
helper-1 [000] 1.009: rog5_gmu_v9_runtime_pm: dev=0x222')
run_reject reversed-GPU-runtime-PM "$reversed_order" \
	'GPU device outer runtime-PM did not precede runtime-resume callback'

missing_generic_device=$(printf '%s\n' "$valid_unsigned" |
	sed 's/runtime_pm: dev=0x111/runtime_pm:/')
run_reject unclassified-runtime-PM "$missing_generic_device" \
	'generic runtime-PM trace contains an unclassified device'

duplicate_callback=$(printf '%s\n' "$valid_unsigned" |
	sed '/runtime_resume: dev=0x222/p')
run_reject duplicate-runtime-resume "$duplicate_callback" \
	'Adreno runtime-resume entry count is 2, expected 1'

zero_device=$(printf '%s\n' "$valid_unsigned" |
	sed 's/dev=0x222/dev=0x0/g')
run_reject zero-GPU-device "$zero_device" \
	'Adreno runtime-resume device is null'

echo 'PASS A660 GMU resume-entry v9 trace oracle accepts signed/zero-extended EUCLEAN and rejects malformed returns or unscoped GPU runtime PM'
