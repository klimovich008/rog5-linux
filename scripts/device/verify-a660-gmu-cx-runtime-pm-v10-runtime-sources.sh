#!/bin/sh
# shellcheck disable=SC2016
set -eu

baseline=${1:?usage: verify-a660-gmu-cx-runtime-pm-v10-runtime-sources.sh BASELINE PROBE}
probe=${2:?missing probe}
repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)
builder=$repo/scripts/device/build-a660-gmu-cx-runtime-pm-v10-runtime.sh
v9_builder=$repo/scripts/device/build-a660-gmu-resume-entry-v9-runtime.sh
v9_verifier=$repo/scripts/device/verify-a660-gmu-resume-entry-v9-runtime-sources.sh
v9_report=$repo/test-results/2026-07-27-a660-gmu-resume-entry-v9-live-accepted.md
v9_consumed=$repo/scripts/host/test-consume-a660-gmu-resume-entry-v9.sh
offline_report=$repo/test-results/2026-07-27-a660-gmu-cx-runtime-pm-v10-offline.md
kernel_patch=$repo/patches/linux-7.1.4/0016-drm-msm-add-a660-gmu-cx-runtime-pm-diagnostic.patch
trace_oracle=$repo/scripts/device/check-a660-gmu-cx-runtime-pm-v10-trace.sh
trace_oracle_test=$repo/scripts/device/test-a660-gmu-cx-runtime-pm-v10-trace-oracle.sh
baseline_patch=$repo/patches/runtime/a660-gmu-cx-runtime-pm-v10-baseline.patch
probe_patch=$repo/patches/runtime/a660-gmu-cx-runtime-pm-v10-probe.patch
msm_module=${A660_GMU_CX_RUNTIME_PM_V10_MSM_MODULE:-$repo/artifacts/a660-gmu-cx-runtime-pm-v10-build/drivers/gpu/drm/msm/msm.ko}

fail() {
	echo "FAIL $*" >&2
	exit 1
}

check_hash() {
	file=$1
	expected=$2
	label=$3
	[ -f "$file" ] && [ ! -L "$file" ] && [ -r "$file" ] ||
		fail "$label is missing, linked, or unreadable"
	actual=$(sha256sum "$file" | cut -d ' ' -f 1)
	[ "$actual" = "$expected" ] ||
		fail "$label hash mismatch: expected $expected, got $actual"
}

count_fixed() {
	grep -Fc "$2" "$1" || true
}

require_once() {
	file=$1
	needle=$2
	label=$3
	count=$(count_fixed "$file" "$needle")
	[ "$count" -eq 1 ] ||
		fail "$label count is $count, expected 1"
}

reject_fixed() {
	needle=$1
	label=$2
	if grep -Fq "$needle" "$baseline" "$probe"; then
		fail "$label survived: $needle"
	fi
}

line_once() {
	file=$1
	needle=$2
	label=$3
	matches=$(grep -Fn -- "$needle" "$file" || true)
	count=$(printf '%s\n' "$matches" |
		awk 'NF { count++ } END { print count + 0 }')
	[ "$count" -eq 1 ] ||
		fail "$label count is $count, expected 1"
	line=${matches%%:*}
	printf '%s\n' "$line"
}

for command in awk cut grep modinfo nm readelf sha256sum; do
	command -v "$command" >/dev/null || fail "missing command: $command"
done
for input in "$baseline" "$probe"; do
	[ -f "$input" ] && [ ! -L "$input" ] && [ -r "$input" ] ||
		fail "runtime source is missing, linked, or unreadable: $input"
	sh -n "$input"
done

if [ "${ALLOW_UNPINNED_A660_GMU_CX_RUNTIME_PM_V10:-0}" != 1 ]; then
	check_hash "$baseline" \
		a68960aa1ac84dbc6f3b469d8369d1c66dcd343f9adfc0a9f4e9909e9ee4245d \
		'generated v10 baseline'
	check_hash "$probe" \
		f28b1c28ec43da21747ce7e17247d33074bfa01f7c9c6171e80806a98eb70b36 \
		'generated v10 probe'
fi

check_hash "$builder" \
	a0bd091b1304581fe41bfcf1ceaa77a84fbbdd606d3797144a1e6685e1179942 \
	'v10 runtime builder'
check_hash "$v9_builder" \
	da8b18e6c995bbc2b7402b7be6d38577911c2258c2b131304865ab55ada0cafb \
	'immutable accepted-and-consumed v9 runtime builder'
check_hash "$v9_verifier" \
	9e3f39e60d5edb06ea50ff2673bd818029274960af0e95c84f3e438a3d1c5ef1 \
	'immutable v9 runtime verifier'
check_hash "$v9_report" \
	57af6b4d0ddf6faaa708e7b409197dcf7aa8fcdb52a5a9612b59094aebc9dd2c \
	'accepted v9 live report'
check_hash "$v9_consumed" \
	e876ff87452aa02e60f3135801a3f6d2da0042c680fd14bf0ae7319e9adc4a7f \
	'permanent v9 consumption test'
check_hash "$offline_report" \
	9ae66678340437c4a38b2d6ee390cc375e661548be97cb108bb8f891a418dee4 \
	'accepted v10 offline report'
check_hash "$kernel_patch" \
	5eef04eb711443acaaf4295e926577f90073b8ab62414cff3d18de2272d3a152 \
	'accepted v10 kernel patch'
check_hash "$trace_oracle" \
	33ccadc6ae1e5f6f12ed83de0ddc192d30d204e229ec1b97aa813e1d0ac9c7e6 \
	'exact GMU/linked-CX v10 trace oracle'
check_hash "$trace_oracle_test" \
	ca942002debee58a0437218ba4b49410c2a50d7a5d93a9d6872890a8c565f915 \
	'v10 trace-oracle mutation test'
check_hash "$baseline_patch" \
	5732f9b170aa133d00a2eafd7b2fab2c262c1e98765ba05c8a848e3e5b85f674 \
	'v10 baseline patch'
check_hash "$probe_patch" \
	e8ab58ac1efab6441500532574f34b8fe55734b6c0816b3cc28fc977eb9547e4 \
	'v10 probe patch'
check_hash "$msm_module" \
	c36fd352c48d624eff9f17fb8200c8f151209eae066d1f276ab3bff67c5d465d \
	'accepted v10 MSM module'

modinfo -p "$msm_module" | grep -Fxq \
	'gmu_cx_runtime_pm_only:Resume and synchronously roll back exact A660 GMU/CX power once before GX (bool)' ||
	fail 'accepted v10 MSM module lacks the diagnostic parameter'
readelf -S "$msm_module" | grep -Eq '[[:space:]][.]BTF[[:space:]]' ||
	fail 'accepted v10 MSM module lacks BTF'
for symbol in msm_a660_gmu_cx_runtime_pm_only_enabled \
	msm_a660_gmu_cx_runtime_pm_only_mark_attempt \
	msm_a660_gmu_cx_runtime_pm_only_mark_passed \
	msm_a660_gmu_cx_runtime_pm_only_was_passed
do
	[ "$(nm -n "$msm_module" | grep -Ec \
		"[[:space:]]T[[:space:]]$symbol$")" -eq 1 ] ||
		fail "accepted v10 MSM symbol is not exact: $symbol"
done

require_once "$baseline" 'diagnostic_generation=v10' \
	'v10 diagnostic generation'
require_once "$baseline" 'predecessor=v9_live_accepted_consumed' \
	'accepted-and-consumed v9 predecessor'
require_once "$baseline" \
	'predecessor_report_sha256=57af6b4d0ddf6faaa708e7b409197dcf7aa8fcdb52a5a9612b59094aebc9dd2c' \
	'v9 predecessor report identity'
require_once "$baseline" 'predecessor_consumption_commit=3d708cd' \
	'v9 consumption commit'
require_once "$baseline" \
	'offline_acceptance_report_sha256=9ae66678340437c4a38b2d6ee390cc375e661548be97cb108bb8f891a418dee4' \
	'v10 offline report identity'
require_once "$baseline" \
	'gmu_cx_runtime_pm_patch_sha256=5eef04eb711443acaaf4295e926577f90073b8ab62414cff3d18de2272d3a152' \
	'v10 kernel patch identity'
require_once "$baseline" \
	'trace_policy=PID_FILTERED_S32_EXACT_GMU_LINKED_CX_RPM_AND_LOGICAL_VMAP' \
	'v10 trace policy'
require_once "$baseline" \
	'trace_oracle_sha256=33ccadc6ae1e5f6f12ed83de0ddc192d30d204e229ec1b97aa813e1d0ac9c7e6' \
	'v10 trace-oracle identity'
require_once "$baseline" 'gmu_cx_runtime_pm_parameter_mode=0400' \
	'read-only diagnostic parameter seal'
require_once "$baseline" 'v9_reuse=FORBIDDEN' \
	'v9 live-root reuse prohibition'
require_once "$baseline" 'kernel/module delta=v10-msm-only' \
	'v10 module-only delta'
require_once "$baseline" \
	'PASS A660-gmu-cx-runtime-pm-v10 baseline storage=0' \
	'v10 baseline result'

require_once "$probe" \
	'[ "${ALLOW_MAINLINE_A660_GMU_CX_RUNTIME_PM_V10:-}" = 1 ]' \
	'fresh v10 live authorization'
require_once "$probe" \
	'insmod "$msm_module" separate_gpu_kms=1 gmu_cx_runtime_pm_only=1' \
	'v10-only module load'
require_once "$probe" \
	'[ "$(cat /sys/module/msm/parameters/gmu_cx_runtime_pm_only)" = Y ]' \
	'enabled v10 diagnostic state'
require_once "$probe" \
	'[ "$(cat /sys/module/msm/parameters/gmu_resume_entry_only)" = N ]' \
	'disabled predecessor diagnostic state'
require_once "$probe" \
	c36fd352c48d624eff9f17fb8200c8f151209eae066d1f276ab3bff67c5d465d \
	'v10 MSM module identity'
require_once "$probe" 'gmu_name" = 3d6a000.gmu' \
	'exact GMU consumer name'
require_once "$probe" 'cx_name=genpd:0:3d6a000.gmu' \
	'exact linked CX supplier name'
require_once "$probe" 'gx_name=genpd:1:3d6a000.gmu' \
	'exact forbidden GX supplier name'
require_once "$probe" 'events/rpm/rpm_resume/enable' \
	'built-in RPM resume event'
require_once "$probe" 'events/rpm/rpm_suspend/enable' \
	'built-in RPM suspend event'
require_once "$probe" \
	'rog5_gmu_v10_runtime_pm_resume __pm_runtime_resume dev=$arg1:x64' \
	'generic runtime-resume device trace'
require_once "$probe" \
	'rog5_gmu_v10_runtime_pm_suspend __pm_runtime_suspend dev=$arg1:x64' \
	'generic runtime-suspend device trace'
require_once "$probe" \
	'trace_oracle_output=$("$trace_oracle" "$trace_snapshot")' \
	'exact trace-oracle invocation'
require_once "$probe" 'gmu_runtime_status=suspended' \
	'GMU suspended-state oracle'
require_once "$probe" 'cx_runtime_status=suspended' \
	'linked CX suspended-state oracle'
require_once "$probe" 'gx_runtime_status=suspended' \
	'GX suspended-state oracle'
require_once "$probe" \
	'cmp "$state_dir/gem.before" "$state_dir/gem.after"' \
	'GEM snapshot equality'
require_once "$probe" '[ "$helper_output" = OPEN_ERRNO=117 ]' \
	'fail-closed open result'
require_once "$probe" \
	'A660 GMU/CX runtime PM resumed and synchronously suspended; reject resume' \
	'v10 transition marker'
require_once "$probe" \
	'A660 GMU/CX runtime PM passed and GPU load rolled back; reject open' \
	'v10 rollback marker'
require_once "$probe" \
	'gmu_runtime_pm=1/1 cx_runtime_pm=1/1 cx_suspend_ret=%s' \
	'exact GMU/CX runtime-PM result'
require_once "$probe" 'gx_runtime_pm=0' \
	'zero-GX runtime-PM result'
require_once "$probe" \
	'clocks=0 secure=0 mmio=0 irq=0 firmware_start=0 hfi=0' \
	'zero post-boundary work result'
require_once "$probe" 'gem_snapshot=equal' \
	'equal GEM snapshot result'

reject_fixed 'ALLOW_MAINLINE_A660_GMU_RESUME_ENTRY_V9' \
	'inherited v9 authorization'
reject_fixed 'gmu_resume_entry_only=1' \
	'enabled predecessor diagnostic'
reject_fixed 'gmu_cx_runtime_pm_only=0' \
	'disabled v10 diagnostic'
reject_fixed 'cx_name=genpd:1:3d6a000.gmu' \
	'GX substituted for linked CX'
reject_fixed 'gx_runtime_pm=1' \
	'allowed GX runtime PM'
reject_fixed 'OPEN_OK' \
	'successful open'

trace_register_line=$(line_once "$probe" \
	"'p:rog5_gmu_v10/rog5_gmu_v10_load_gpu msm:adreno_load_gpu dev=\$arg1:x64'" \
	'v10 trace registration')
rpm_resume_enable_line=$(line_once "$probe" \
	"printf '1\\n' >\"\$trace_root/events/rpm/rpm_resume/enable\"" \
	'RPM resume enable')
rpm_suspend_enable_line=$(line_once "$probe" \
	"printf '1\\n' >\"\$trace_root/events/rpm/rpm_suspend/enable\"" \
	'RPM suspend enable')
helper_line=$(line_once "$probe" \
	"sh -c 'kill -STOP \"\$\$\"; exec \"\$1\"' sh \"\$helper\"" \
	'one-open stopped helper')
pid_filter_line=$(line_once "$probe" \
	"printf '%s\\n' \"\$helper_pid\" >\"\$trace_root/set_event_pid\"" \
	'exact helper PID filter')
trace_start_line=$(line_once "$probe" \
	"printf '1\\n' >\"\$trace_root/tracing_on\"" \
	'trace start')
oracle_line=$(line_once "$probe" \
	'trace_oracle_output=$("$trace_oracle" "$trace_snapshot")' \
	'v10 trace oracle')
zero_gx_line=$(line_once "$probe" 'gx_runtime_pm=0' \
	'zero-GX result')
settle_line=$(line_once "$probe" 'sleep "$settle_seconds"' \
	'post-open settle')
snapshot_line=$(line_once "$probe" \
	'cmp "$state_dir/gem.before" "$state_dir/gem.after"' \
	'GEM snapshot equality')
cx_state_line=$(line_once "$probe" 'cx_runtime_status=suspended' \
	'linked CX suspended state')
[ "$trace_register_line" -lt "$rpm_resume_enable_line" ] &&
	[ "$rpm_resume_enable_line" -lt "$rpm_suspend_enable_line" ] &&
	[ "$rpm_suspend_enable_line" -lt "$helper_line" ] &&
	[ "$helper_line" -lt "$pid_filter_line" ] &&
	[ "$pid_filter_line" -lt "$trace_start_line" ] &&
	[ "$trace_start_line" -lt "$oracle_line" ] &&
	[ "$oracle_line" -lt "$settle_line" ] &&
	[ "$settle_line" -lt "$snapshot_line" ] &&
	[ "$snapshot_line" -lt "$cx_state_line" ] &&
	[ "$cx_state_line" -lt "$zero_gx_line" ] ||
	fail 'trace, helper, oracle, zero-GX, settle, snapshot, and state order changed'

if grep -Eq \
	'(^|[;&|[:space:]])(fastboot|adb|ssh|scp)([[:space:]]|$)|systemctl[[:space:]]+poweroff|dd[[:space:]].*of=/dev/|mount[[:space:]].*/dev/' \
	"$baseline" "$probe"
then
	fail 'v10 runtime source controls transport or writes phone storage'
fi
if grep -Fq 'systemctl reboot' "$baseline" "$probe"; then
	fail 'v10 runtime source bypasses the compound reboot gate'
fi

echo 'PASS A660 GMU/CX runtime-PM v10 runtime sources pin accepted v9 ancestry, v10 MSM-only artifact, exact GMU/linked-CX PM, zero GX/post-boundary work, settled state, rollback snapshot, fresh authorization, watchdog, and storage isolation'
