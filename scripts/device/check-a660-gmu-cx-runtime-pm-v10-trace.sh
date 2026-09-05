#!/bin/sh
set -eu

fail() {
	echo "FAIL $*" >&2
	exit 1
}

[ "$#" -eq 1 ] ||
	fail 'usage: check-a660-gmu-cx-runtime-pm-v10-trace.sh TRACE_OR_DASH'

input=$1
temporary=
if [ "$input" = - ]; then
	umask 077
	temporary=$(mktemp -d /tmp/rog5-a660-gmu-v10-trace.XXXXXX)
	trap 'rm -rf -- "$temporary"' EXIT HUP INT TERM
	trace=$temporary/trace
	cat >"$trace"
else
	[ -f "$input" ] && [ ! -L "$input" ] ||
		fail 'trace input is not a regular non-symlink file'
	trace=$input
fi
[ -s "$trace" ] || fail 'trace input is empty'
[ "$(wc -c <"$trace")" -le 1048576 ] ||
	fail 'trace input exceeds one MiB'
[ "$(wc -l <"$trace")" -le 8192 ] ||
	fail 'trace input exceeds 8192 lines'

event_count() {
	grep -Ec "rog5_gmu_v10_$1:" "$trace" || true
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
	grep -n -E "rog5_gmu_v10_$event:" "$trace" | cut -d: -f1
}

extract_one_field() {
	event=$1
	field=$2
	label=$3
	line=$(grep -E "rog5_gmu_v10_$event:" "$trace")
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

window_events() {
	event=$1
	first=$2
	last=$3
	awk -v marker="rog5_gmu_v10_$event:" \
		-v first="$first" -v last="$last" '
		NR > first && NR < last && index($0, marker) {
			print NR ":" $0
		}
	' "$trace"
}

window_field_rows() {
	event=$1
	field=$2
	first=$3
	last=$4
	awk -v marker="rog5_gmu_v10_$event:" -v wanted="$field=" \
		-v first="$first" -v last="$last" '
		NR > first && NR < last && index($0, marker) {
			for (i = 1; i <= NF; i++) {
				if (index($i, wanted) == 1) {
					value = $i
					sub(wanted, "", value)
					print NR ":" value
					found++
				}
			}
		}
		END {
			if (!found)
				exit 1
		}
	' "$trace"
}

rpm_name_rows() {
	event=$1
	name=$2
	first=$3
	last=$4
	awk -v event="$event:" -v wanted="$name" \
		-v first="$first" -v last="$last" '
		NR > first && NR < last {
			line = $0
			if (!match(line, "(^|[[:space:]])" event "[[:space:]]"))
				next
			line = substr(line, RSTART + RLENGTH)
			split(line, fields, /[[:space:]]+/)
			if (fields[1] == wanted)
				print NR
		}
	' "$trace"
}

if awk '
	match($0, /(^|[[:space:]])rpm_(resume|suspend):[[:space:]]/) {
		line = substr($0, RSTART + RLENGTH)
		split(line, fields, /[[:space:]]+/)
		if (fields[1] == "genpd:1:3d6a000.gmu")
			found = 1
	}
	/rog5_gmu_v10_gx_/ { found = 1 }
	END { exit found ? 0 : 1 }
' "$trace"
then
	fail 'GX-domain runtime-PM activity is present'
fi

if grep -Eq \
	'rog5_gmu_v10_(clk_rate|clk_bulk|secure_init|mmio|enable_irq|gmu_start|hfi_start|msm_pm_resume|a6xx_pm_resume|devfreq_resume|llc_activate|initial_freq|hw_init|a6xx_hw_init|zap_init|scm_available|scm_gpu_init|scm_pas|scm_aperture):' \
	"$trace"
then
	fail 'forbidden post-GMU/CX boundary activity is present'
fi

require_event_count runtime_resume 1 'Adreno runtime-resume entry'
require_event_count pm_resume 1 'A6xx GMU PM-resume entry'
require_event_count resume 1 'A6xx GMU-resume entry'
require_event_count runtime_resume_ret 1 'Adreno runtime-resume return'
require_event_count pm_resume_ret 1 'A6xx GMU PM-resume return'
require_event_count resume_ret 1 'A6xx GMU-resume return'
require_event_count mark_attempt 1 'GMU/CX one-shot attempt'
require_event_count mark_attempt_ret 1 'GMU/CX one-shot attempt return'
require_event_count mark_passed 1 'GMU/CX one-shot passed transition'
require_event_count mark_passed_ret 1 'GMU/CX one-shot passed return'
require_event_count rollback 1 'GPU-load rollback entry'
require_event_count rollback_ret 1 'GPU-load rollback return'

gpu_device=$(extract_one_field runtime_resume dev \
	'Adreno runtime-resume device')
printf '%s\n' "$gpu_device" | grep -Eq '^0x[0-9A-Fa-f]+$' ||
	fail 'Adreno runtime-resume device is malformed'
if printf '%s\n' "$gpu_device" | grep -Eq '^0x0+$'; then
	fail 'Adreno runtime-resume device is null'
fi

generic_resume=$(event_count runtime_pm_resume)
generic_resume_ret=$(event_count runtime_pm_resume_ret)
generic_suspend=$(event_count runtime_pm_suspend)
generic_suspend_ret=$(event_count runtime_pm_suspend_ret)
[ "$generic_resume" -gt 0 ] || fail 'generic runtime-resume trace is empty'

classified_resume=$(grep -Ec \
	'rog5_gmu_v10_runtime_pm_resume:.* dev=0x[0-9A-Fa-f]+([[:space:]]|$)' \
	"$trace" || true)
classified_suspend=$(grep -Ec \
	'rog5_gmu_v10_runtime_pm_suspend:.* dev=0x[0-9A-Fa-f]+([[:space:]]|$)' \
	"$trace" || true)
[ "$classified_resume" -eq "$generic_resume" ] ||
	fail 'generic runtime-resume trace contains an unclassified device'
[ "$classified_suspend" -eq "$generic_suspend" ] ||
	fail 'generic runtime-suspend trace contains an unclassified device'
if grep -Eq \
	'rog5_gmu_v10_runtime_pm_(resume|suspend):.* dev=0x0+([[:space:]]|$)' \
	"$trace"
then
	fail 'generic runtime-PM trace contains a null device'
fi

gpu_runtime_pm=$(grep -Ec \
	"rog5_gmu_v10_runtime_pm_resume:.* dev=$gpu_device([[:space:]]|$)" \
	"$trace" || true)
[ "$gpu_runtime_pm" -eq 1 ] ||
	fail "GPU device outer runtime-PM count is $gpu_runtime_pm, expected 1"

gpu_runtime_pm_line=$(grep -n -E \
	"rog5_gmu_v10_runtime_pm_resume:.* dev=$gpu_device([[:space:]]|$)" \
	"$trace" | cut -d: -f1)
runtime_resume_line=$(event_line runtime_resume)
pm_resume_line=$(event_line pm_resume)
resume_line=$(event_line resume)
mark_attempt_line=$(event_line mark_attempt)
mark_attempt_ret_line=$(event_line mark_attempt_ret)
mark_passed_line=$(event_line mark_passed)
mark_passed_ret_line=$(event_line mark_passed_ret)
resume_ret_line=$(event_line resume_ret)
pm_resume_ret_line=$(event_line pm_resume_ret)
runtime_resume_ret_line=$(event_line runtime_resume_ret)
rollback_line=$(event_line rollback)
rollback_ret_line=$(event_line rollback_ret)

[ "$gpu_runtime_pm_line" -lt "$runtime_resume_line" ] &&
	[ "$runtime_resume_line" -lt "$pm_resume_line" ] &&
	[ "$pm_resume_line" -lt "$resume_line" ] &&
	[ "$resume_line" -lt "$mark_attempt_line" ] &&
	[ "$mark_attempt_line" -lt "$mark_attempt_ret_line" ] &&
	[ "$mark_attempt_ret_line" -lt "$mark_passed_line" ] &&
	[ "$mark_passed_line" -lt "$mark_passed_ret_line" ] &&
	[ "$mark_passed_ret_line" -lt "$resume_ret_line" ] &&
	[ "$resume_ret_line" -lt "$pm_resume_ret_line" ] &&
	[ "$pm_resume_ret_line" -lt "$runtime_resume_ret_line" ] &&
	[ "$runtime_resume_ret_line" -lt "$rollback_line" ] &&
	[ "$rollback_line" -lt "$rollback_ret_line" ] ||
	fail 'GMU/CX resume, state, and rollback nesting changed'

attempt_result=$(extract_one_field mark_attempt_ret ret \
	'GMU/CX one-shot attempt return')
[ "$attempt_result" = 1 ] ||
	fail 'GMU/CX one-shot attempt was already consumed'
passed_result=$(extract_one_field mark_passed_ret ret \
	'GMU/CX one-shot passed return')
[ "$passed_result" = 1 ] ||
	fail 'GMU/CX one-shot did not reach passed state'

diagnostic_resume_count=$(window_events runtime_pm_resume \
	"$mark_attempt_ret_line" "$mark_passed_line" | wc -l)
[ "$diagnostic_resume_count" -eq 2 ] ||
	fail "diagnostic runtime-resume entry count is $diagnostic_resume_count, expected 2"
diagnostic_resume_ret_count=$(window_events runtime_pm_resume_ret \
	"$mark_attempt_ret_line" "$mark_passed_line" | wc -l)
[ "$diagnostic_resume_ret_count" -eq 2 ] ||
	fail "diagnostic runtime-resume return count is $diagnostic_resume_ret_count, expected 2"
diagnostic_suspend_count=$(window_events runtime_pm_suspend \
	"$mark_attempt_ret_line" "$mark_passed_line" | wc -l)
[ "$diagnostic_suspend_count" -eq 2 ] ||
	fail "diagnostic runtime-suspend entry count is $diagnostic_suspend_count, expected 2"
diagnostic_suspend_ret_count=$(window_events runtime_pm_suspend_ret \
	"$mark_attempt_ret_line" "$mark_passed_line" | wc -l)
[ "$diagnostic_suspend_ret_count" -eq 2 ] ||
	fail "diagnostic runtime-suspend return count is $diagnostic_suspend_ret_count, expected 2"
[ "$generic_resume" -eq "$generic_resume_ret" ] ||
	fail 'generic runtime-resume entry/return counts differ'
[ "$generic_suspend" -eq "$generic_suspend_ret" ] ||
	fail 'generic runtime-suspend entry/return counts differ'

resume_rows=$(window_field_rows runtime_pm_resume dev \
	"$mark_attempt_ret_line" "$mark_passed_line")
gmu_resume_row=$(printf '%s\n' "$resume_rows" | sed -n '1p')
cx_resume_row=$(printf '%s\n' "$resume_rows" | sed -n '2p')
gmu_resume_line=${gmu_resume_row%%:*}
gmu_device=${gmu_resume_row#*:}
cx_resume_line=${cx_resume_row%%:*}
cx_device=${cx_resume_row#*:}

suspend_rows=$(window_field_rows runtime_pm_suspend dev \
	"$mark_attempt_ret_line" "$mark_passed_line")
gmu_suspend_row=$(printf '%s\n' "$suspend_rows" | sed -n '1p')
cx_suspend_row=$(printf '%s\n' "$suspend_rows" | sed -n '2p')
gmu_suspend_line=${gmu_suspend_row%%:*}
gmu_suspend_device=${gmu_suspend_row#*:}
cx_suspend_line=${cx_suspend_row%%:*}
cx_suspend_device=${cx_suspend_row#*:}

[ "$gmu_device" = "$gmu_suspend_device" ] ||
	fail 'GMU consumer resume/suspend device identity differs'
[ "$cx_device" = "$cx_suspend_device" ] ||
	fail 'linked CX supplier resume/suspend device identity differs'
[ "$gmu_device" != "$cx_device" ] &&
	[ "$gmu_device" != "$gpu_device" ] &&
	[ "$cx_device" != "$gpu_device" ] ||
	fail 'GPU, GMU consumer, and linked CX supplier identities are not distinct'

gmu_resume_names=$(rpm_name_rows rpm_resume 3d6a000.gmu \
	"$mark_attempt_ret_line" "$mark_passed_line")
gmu_resume_name_count=$(printf '%s\n' "$gmu_resume_names" |
	awk 'NF { count++ } END { print count + 0 }')
[ "$gmu_resume_name_count" -eq 1 ] ||
	fail "exact GMU consumer runtime-resume identity count is $gmu_resume_name_count, expected 1"
cx_resume_names=$(rpm_name_rows rpm_resume genpd:0:3d6a000.gmu \
	"$mark_attempt_ret_line" "$mark_passed_line")
cx_resume_name_count=$(printf '%s\n' "$cx_resume_names" |
	awk 'NF { count++ } END { print count + 0 }')
[ "$cx_resume_name_count" -eq 1 ] ||
	fail "exact linked CX supplier runtime-resume identity count is $cx_resume_name_count, expected 1"
gmu_resume_name_line=$(printf '%s\n' "$gmu_resume_names" | sed -n '1p')
cx_resume_name_line=$(printf '%s\n' "$cx_resume_names" | sed -n '1p')
[ "$gmu_resume_name_line" -lt "$cx_resume_name_line" ] ||
	fail 'GMU consumer and linked CX supplier resume ordering changed'

gmu_suspend_names=$(rpm_name_rows rpm_suspend 3d6a000.gmu \
	"$mark_attempt_ret_line" "$mark_passed_line")
gmu_suspend_name_count=$(printf '%s\n' "$gmu_suspend_names" |
	awk 'NF { count++ } END { print count + 0 }')
[ "$gmu_suspend_name_count" -eq 1 ] ||
	fail "exact GMU consumer runtime-suspend identity count is $gmu_suspend_name_count, expected 1"
cx_suspend_names=$(rpm_name_rows rpm_suspend genpd:0:3d6a000.gmu \
	"$mark_attempt_ret_line" "$mark_passed_line")
cx_suspend_name_count=$(printf '%s\n' "$cx_suspend_names" |
	awk 'NF { count++ } END { print count + 0 }')
[ "$cx_suspend_name_count" -eq 1 ] ||
	fail "exact linked CX supplier runtime-suspend identity count is $cx_suspend_name_count, expected 1"
gmu_suspend_name_line=$(printf '%s\n' "$gmu_suspend_names" | sed -n '1p')
cx_suspend_name_line=$(printf '%s\n' "$cx_suspend_names" | sed -n '1p')

resume_ret_rows=$(window_field_rows runtime_pm_resume_ret ret \
	"$mark_attempt_ret_line" "$mark_passed_line")
cx_resume_raw=$(printf '%s\n' "$resume_ret_rows" | sed -n '1p')
cx_resume_raw=${cx_resume_raw#*:}
gmu_resume_raw=$(printf '%s\n' "$resume_ret_rows" | sed -n '2p')
gmu_resume_raw=${gmu_resume_raw#*:}
cx_resume_status=$(normalize_s32 "$cx_resume_raw" \
	'linked CX supplier runtime resume')
gmu_resume_status=$(normalize_s32 "$gmu_resume_raw" \
	'GMU consumer runtime resume')
[ "$cx_resume_status" -eq 0 ] ||
	fail 'linked CX supplier runtime resume did not return zero'
[ "$gmu_resume_status" -eq 0 ] ||
	fail 'GMU consumer runtime resume did not return zero'

suspend_ret_rows=$(window_field_rows runtime_pm_suspend_ret ret \
	"$mark_attempt_ret_line" "$mark_passed_line")
gmu_suspend_raw=$(printf '%s\n' "$suspend_ret_rows" | sed -n '1p')
gmu_suspend_raw=${gmu_suspend_raw#*:}
cx_suspend_raw=$(printf '%s\n' "$suspend_ret_rows" | sed -n '2p')
cx_suspend_raw=${cx_suspend_raw#*:}
gmu_suspend_status=$(normalize_s32 "$gmu_suspend_raw" \
	'GMU consumer runtime suspend')
cx_suspend_status=$(normalize_s32 "$cx_suspend_raw" \
	'linked CX supplier runtime suspend')
[ "$gmu_suspend_status" -eq 0 ] ||
	fail 'GMU consumer runtime suspend did not return zero'
case $cx_suspend_status in
	0|1) ;;
	*) fail 'linked CX supplier runtime suspend did not return zero or already-suspended' ;;
esac

[ "$mark_attempt_ret_line" -lt "$gmu_resume_line" ] &&
	[ "$gmu_resume_line" -lt "$gmu_resume_name_line" ] &&
	[ "$gmu_resume_name_line" -lt "$cx_resume_line" ] &&
	[ "$cx_resume_line" -lt "$cx_resume_name_line" ] &&
	[ "$cx_resume_name_line" -lt "$gmu_suspend_line" ] &&
	[ "$gmu_suspend_line" -lt "$gmu_suspend_name_line" ] &&
	[ "$gmu_suspend_name_line" -lt "$cx_suspend_line" ] &&
	[ "$cx_suspend_line" -lt "$cx_suspend_name_line" ] &&
	[ "$cx_suspend_name_line" -lt "$mark_passed_line" ] ||
	fail 'GMU/CX runtime-PM call and device-name ordering changed'

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

outer_return_rows=$(window_field_rows runtime_pm_resume_ret ret \
	"$runtime_resume_ret_line" "$rollback_line")
outer_return_count=$(printf '%s\n' "$outer_return_rows" |
	awk 'NF { count++ } END { print count + 0 }')
[ "$outer_return_count" -eq 1 ] ||
	fail "outer GPU runtime-PM return count is $outer_return_count, expected 1"
outer_return_raw=${outer_return_rows#*:}
outer_return_status=$(normalize_s32 "$outer_return_raw" \
	'outer GPU runtime resume')
[ "$outer_return_status" -eq -117 ] ||
	fail 'outer GPU runtime resume return is not signed EUCLEAN'

rollback_raw=$(extract_one_field rollback_ret ret 'GPU-load rollback return')
rollback_status=$(normalize_s32 "$rollback_raw" 'GPU-load rollback')
[ "$rollback_status" -eq 0 ] ||
	fail 'GPU-load rollback did not return zero'

printf 'PASS A660 GMU/CX runtime-PM v10 trace oracle returns=%s/%s/%s gpu_runtime_pm=%s gmu_runtime_pm=1/1 cx_runtime_pm=1/1 cx_suspend_ret=%s generic_resume=%s generic_suspend=%s\n' \
	"$runtime_resume_status" "$pm_resume_status" "$resume_status" \
	"$gpu_runtime_pm" "$cx_suspend_status" "$generic_resume" \
	"$generic_suspend"
