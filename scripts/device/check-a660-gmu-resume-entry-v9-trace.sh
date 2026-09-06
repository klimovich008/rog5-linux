#!/bin/sh
set -eu

fail() {
	echo "FAIL $*" >&2
	exit 1
}

[ "$#" -eq 1 ] ||
	fail 'usage: check-a660-gmu-resume-entry-v9-trace.sh TRACE_OR_DASH'

input=$1
temporary=
if [ "$input" = - ]; then
	umask 077
	temporary=$(mktemp -d /tmp/rog5-a660-gmu-v9-trace.XXXXXX)
	trap 'rm -rf -- "$temporary"' EXIT HUP INT TERM
	trace=$temporary/trace
	cat >"$trace"
else
	[ -f "$input" ] && [ ! -L "$input" ] ||
		fail 'trace input is not a regular non-symlink file'
	trace=$input
fi
[ -s "$trace" ] || fail 'trace input is empty'

event_count() {
	grep -Ec "rog5_gmu_v9_$1:" "$trace" || true
}

require_event_count() {
	event=$1
	expected=$2
	label=$3
	observed=$(event_count "$event")
	[ "$observed" -eq "$expected" ] ||
		fail "$label count is $observed, expected $expected"
}

event_line() {
	event=$1
	grep -n -E "rog5_gmu_v9_$event:" "$trace" | cut -d: -f1
}

extract_one_field() {
	event=$1
	field=$2
	label=$3
	line=$(grep -E "rog5_gmu_v9_$event:" "$trace")
	case $line in
		*" $field="*)
			value=${line##*" $field="}
			value=${value%%[[:space:]]*}
			[ -n "$value" ] || fail "$label is missing"
			printf '%s\n' "$value"
			;;
		*)
			fail "$label is missing"
			;;
	esac
}

normalize_s32() {
	raw=$1
	label=$2
	printf '%s\n' "$raw" | grep -Eq '^-?[0-9]+$' ||
		fail "$label return is malformed"
	case $raw in
		-*)
			[ "$raw" -ge -2147483648 ] &&
				[ "$raw" -le 2147483647 ] ||
				fail "$label return is outside signed-32 transport"
			normalized=$raw
			;;
		*)
			[ "$raw" -le 4294967295 ] ||
				fail "$label return is outside signed-32 transport"
			if [ "$raw" -ge 2147483648 ]; then
				normalized=$((raw - 4294967296))
			else
				normalized=$raw
			fi
			;;
	esac
	printf '%s\n' "$normalized"
}

require_event_count runtime_resume 1 'Adreno runtime-resume entry'
require_event_count pm_resume 1 'A6xx GMU PM-resume entry'
require_event_count resume 1 'A6xx GMU-resume entry'
require_event_count runtime_resume_ret 1 'Adreno runtime-resume return'
require_event_count pm_resume_ret 1 'A6xx GMU PM-resume return'
require_event_count resume_ret 1 'A6xx GMU-resume return'

gpu_device=$(extract_one_field runtime_resume dev \
	'Adreno runtime-resume device')
printf '%s\n' "$gpu_device" | grep -Eq '^0x[0-9A-Fa-f]+$' ||
	fail 'Adreno runtime-resume device is malformed'
if printf '%s\n' "$gpu_device" | grep -Eq '^0x0+$'; then
	fail 'Adreno runtime-resume device is null'
fi

generic_runtime_pm=$(event_count runtime_pm)
[ "$generic_runtime_pm" -gt 0 ] ||
	fail 'generic runtime-PM trace is empty'
classified_runtime_pm=$(grep -Ec \
	'rog5_gmu_v9_runtime_pm:.* dev=0x[0-9A-Fa-f]+([[:space:]]|$)' \
	"$trace" || true)
[ "$classified_runtime_pm" -eq "$generic_runtime_pm" ] ||
	fail 'generic runtime-PM trace contains an unclassified device'

gpu_runtime_pm=$(grep -Ec \
	"rog5_gmu_v9_runtime_pm:.* dev=$gpu_device([[:space:]]|$)" \
	"$trace" || true)
[ "$gpu_runtime_pm" -eq 1 ] ||
	fail "GPU device outer runtime-PM count is $gpu_runtime_pm, expected 1"

gpu_runtime_pm_line=$(grep -n -E \
	"rog5_gmu_v9_runtime_pm:.* dev=$gpu_device([[:space:]]|$)" \
	"$trace" | cut -d: -f1)
runtime_resume_line=$(event_line runtime_resume)
[ "$gpu_runtime_pm_line" -lt "$runtime_resume_line" ] ||
	fail 'GPU device outer runtime-PM did not precede runtime-resume callback'

pm_resume_line=$(event_line pm_resume)
resume_line=$(event_line resume)
resume_ret_line=$(event_line resume_ret)
pm_resume_ret_line=$(event_line pm_resume_ret)
runtime_resume_ret_line=$(event_line runtime_resume_ret)
[ "$runtime_resume_line" -lt "$pm_resume_line" ] &&
	[ "$pm_resume_line" -lt "$resume_line" ] &&
	[ "$resume_line" -lt "$resume_ret_line" ] &&
	[ "$resume_ret_line" -lt "$pm_resume_ret_line" ] &&
	[ "$pm_resume_ret_line" -lt "$runtime_resume_ret_line" ] ||
	fail 'GMU resume entry/return nesting changed'

resume_raw=$(extract_one_field resume_ret ret 'A6xx GMU resume return')
resume_status=$(normalize_s32 "$resume_raw" 'A6xx GMU resume')
[ "$resume_status" -eq -117 ] ||
	fail 'A6xx GMU resume return is not signed EUCLEAN'

pm_resume_raw=$(extract_one_field pm_resume_ret ret \
	'A6xx GMU PM resume return')
pm_resume_status=$(normalize_s32 "$pm_resume_raw" 'A6xx GMU PM resume')
[ "$pm_resume_status" -eq -117 ] ||
	fail 'A6xx GMU PM resume return is not signed EUCLEAN'

runtime_resume_raw=$(extract_one_field runtime_resume_ret ret \
	'Adreno runtime resume return')
runtime_resume_status=$(normalize_s32 "$runtime_resume_raw" \
	'Adreno runtime resume')
[ "$runtime_resume_status" -eq -117 ] ||
	fail 'Adreno runtime resume return is not signed EUCLEAN'

printf 'PASS A660 GMU resume-entry v9 trace oracle returns=%s/%s/%s gpu_runtime_pm=%s generic_runtime_pm=%s\n' \
	"$runtime_resume_status" "$pm_resume_status" "$resume_status" \
	"$gpu_runtime_pm" "$generic_runtime_pm"
