#!/bin/sh
# shellcheck disable=SC2016
set -eu

baseline=${1:?usage: verify-a660-gmu-resume-entry-v9-runtime-sources.sh BASELINE PROBE}
probe=${2:?missing probe}
repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)
builder=$repo/scripts/device/build-a660-gmu-resume-entry-v9-runtime.sh
v8_builder=$repo/scripts/device/build-a660-gmu-resume-entry-v8-runtime.sh
v8_report=$repo/test-results/2026-07-26-a660-gmu-resume-entry-v8-live-rejected.md
v8_consumed=$repo/scripts/host/test-consume-a660-gmu-resume-entry-v8.sh
trace_oracle=$repo/scripts/device/check-a660-gmu-resume-entry-v9-trace.sh
trace_oracle_test=$repo/scripts/device/test-a660-gmu-resume-entry-v9-trace-oracle.sh
relocation_verifier=$repo/scripts/device/verify-a660-gmu-resume-entry-vmap-relocations.sh
baseline_patch=$repo/patches/runtime/a660-gmu-resume-entry-v9-baseline.patch
probe_patch=$repo/patches/runtime/a660-gmu-resume-entry-v9-probe.patch
msm_module=$repo/artifacts/a660-gmu-resume-entry-build-a/drivers/gpu/drm/msm/msm.ko

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

line_once() {
	file=$1
	needle=$2
	label=$3
	stats=$(awk -v needle="$needle" '
		index($0, needle) { count++; line = NR }
		END { print count + 0 ":" line + 0 }
	' "$file")
	count=${stats%%:*}
	line=${stats#*:}
	[ "$count" -eq 1 ] ||
		fail "$label count is $count, expected 1"
	printf '%s\n' "$line"
}

for command in awk cut grep sha256sum; do
	command -v "$command" >/dev/null || fail "missing command: $command"
done
for input in "$baseline" "$probe"; do
	[ -f "$input" ] && [ ! -L "$input" ] && [ -r "$input" ] ||
		fail "runtime source is missing, linked, or unreadable: $input"
	sh -n "$input"
done

if [ "${ALLOW_UNPINNED_A660_GMU_ENTRY_V9_RUNTIME:-0}" != 1 ]; then
	check_hash "$baseline" \
		337535cda800963bc1887203d1f60d9340b8fc5e9956f652a75bf26ada5d4ecc \
		'generated v9 baseline'
	check_hash "$probe" \
		078bb4cb2e6e1edac0182a22023121f2f6fbef2ec02715b7f3f6a5fe9338f387 \
		'generated v9 probe'
fi

check_hash "$builder" \
	da8b18e6c995bbc2b7402b7be6d38577911c2258c2b131304865ab55ada0cafb \
	'v9 runtime builder'
check_hash "$v8_builder" \
	95cc98935677617ddf504701858b4a068a25b71a9a9853735a26c7e590cb5a9d \
	'immutable rejected-and-consumed v8 runtime builder'
check_hash "$v8_report" \
	fe5a6130cce3063ef6a0b1093d492d2a35763781f23af029c2959548cb092a9c \
	'v8 safe live-rejection report'
check_hash "$v8_consumed" \
	efbea8d09ecf81be8df32a0aaaffc55ecdd65209ef7fc1e1d71945a7d38180ec \
	'permanent v8 consumption test'
check_hash "$trace_oracle" \
	48325037a54fe737aa4c623a1be59f644952bd21d9f13f0bba6a6563fea6f223 \
	'signed device-scoped v9 trace oracle'
check_hash "$trace_oracle_test" \
	911d0cab1a0d312c4a217953e87189c3bfbcbd8b9fe32707019a8d112ddaf82c \
	'v9 trace-oracle mutation test'
check_hash "$relocation_verifier" \
	e602f61702093050f5faba7a28c8efe54f50bf74a68369aa6096c94427389bf1 \
	'unchanged v8 compiler-relocation verifier'
check_hash "$baseline_patch" \
	f5c996be5cccc8de45e87591ff1411ad1e6820c233bdcaadf078ecc76a0b0608 \
	'v9 baseline patch'
check_hash "$probe_patch" \
	83b1df2cd462a6ea16e5471888a8bad11b343861d441758995a5a059929be04c \
	'v9 probe patch'
check_hash "$msm_module" \
	b485e8719d6ddf80542a5dc2fdf5bba795d40c69fa220b44571323a8a1d7d861 \
	'unchanged v8 MSM module'
"$v8_consumed" >/dev/null
"$trace_oracle_test" >/dev/null
"$relocation_verifier" "$msm_module" >/dev/null

for contract in \
	'7.1.4-rog5-a660reg1' \
	'/.rog5/root-ro' \
	'rog5-a660-gmu-resume-entry-v9-open' \
	'rog5-a660-gmu-resume-entry-v9-trace-oracle' \
	'a660-gmu-resume-entry-v9-export' \
	'diagnostic_generation=v9' \
	'predecessor=v8_live_rejected_consumed' \
	fe5a6130cce3063ef6a0b1093d492d2a35763781f23af029c2959548cb092a9c \
	'predecessor_consumption_commit=ff1250f' \
	'compiler_policy=PINNED_V8_MSM_RELOCATIONS' \
	'trace_policy=PID_FILTERED_SIGNED32_GPU_DEVICE_AND_LOGICAL_VMAP' \
	'trace_oracle_sha256=48325037a54fe737aa4c623a1be59f644952bd21d9f13f0bba6a6563fea6f223' \
	'state_policy=PRE_POST_GEM_SNAPSHOT_EQUAL' \
	'gmu_entry_parameter_mode=0400' \
	'v8_reuse=FORBIDDEN' \
	'ALLOW_MAINLINE_A660_GMU_RESUME_ENTRY_V9' \
	b485e8719d6ddf80542a5dc2fdf5bba795d40c69fa220b44571323a8a1d7d861 \
	'gmu_resume_entry_only=1' \
	'gmu_resume_entry_only=Y' \
	'firmware_request_only=N' \
	'ucode_allocation_only=N' \
	'OPEN_ERRNO=117' \
	'A660 GMU resume entry reached before resource activation; reject resume' \
	'A660 GMU resume entry passed and rolled back; reject open' \
	"Couldn't power up the GPU: -117" \
	'rog5_gmu_v9' \
	'ret=$retval:u32' \
	'adreno_runtime_resume dev=$arg1:x64' \
	'__pm_runtime_resume dev=$arg1:x64' \
	'trace_oracle_output=$("$trace_oracle" "$trace_snapshot")' \
	'returns=-117/-117/-117 gpu_runtime_pm=1 generic_runtime_pm=' \
	'kernel_news=3' \
	'kernel_puts=2' \
	'wrapper_gets=1' \
	'wrapper_puts=2' \
	'logical_gets=4' \
	'logical_puts=4' \
	'gem.before' \
	'gem.after' \
	'gem_snapshot=equal' \
	'gpu_runtime_pm=1' \
	'generic_runtime_pm=' \
	'inner_runtime_pm=0' \
	'clocks=0' \
	'irq=0' \
	'hfi=0' \
	'devfreq=0' \
	'llc=0' \
	'hw_init=0' \
	'scm=0' \
	'drm_fds=0' \
	'storage=0 mounts=0' \
	'watchdog=disarmed'
do
	if ! grep -Fq "$contract" "$baseline" "$probe"; then
		fail "v9 runtime sources omit: $contract"
	fi
done

for rejected in \
	'ALLOW_MAINLINE_A660_GMU_RESUME_ENTRY_V8' \
	'rog5-a660-gmu-resume-entry-v8-open' \
	'events/rog5_gmu_v8' \
	'rog5_gmu_v9_runtime_resume_ret msm:adreno_runtime_resume ret=$retval:s64' \
	'rog5_gmu_v9_pm_resume_ret msm:a6xx_gmu_pm_resume ret=$retval:s64' \
	'rog5_gmu_v9_resume_ret msm:a6xx_gmu_resume ret=$retval:s64' \
	'require_event_count rog5_gmu_v9_runtime_pm 1' \
	'compiler=v9-relocations'
do
	if grep -Fq "$rejected" "$baseline" "$probe"; then
		fail "v9 retained rejected v8 oracle state: $rejected"
	fi
done

[ "$(grep -Fc 'ret=$retval:u32' "$probe")" -eq 3 ] ||
	fail 'signed-32 transport return registration count is not three'
[ "$(grep -Fc \
	'p:rog5_gmu_v9/rog5_gmu_v9_runtime_resume msm:adreno_runtime_resume dev=$arg1:x64' \
	"$probe")" -eq 1 ] ||
	fail 'Adreno runtime-resume device registration is not exact'
[ "$(grep -Fc \
	'p:rog5_gmu_v9/rog5_gmu_v9_runtime_pm __pm_runtime_resume dev=$arg1:x64' \
	"$probe")" -eq 1 ] ||
	fail 'generic runtime-PM device registration is not exact'
[ "$(grep -Fc \
	'trace_oracle_output=$("$trace_oracle" "$trace_snapshot")' \
	"$probe")" -eq 1 ] ||
	fail 'signed device-scoped trace oracle invocation is not exact'
[ "$(grep -Fc \
	'require_event_count rog5_gmu_v9_runtime_pm 1' "$probe")" -eq 0 ] ||
	fail 'process-global runtime-PM count-of-one oracle survived'
for stale_return in \
	'rog5_gmu_v9_runtime_resume_ret:.*ret=-117' \
	'rog5_gmu_v9_pm_resume_ret:.*ret=-117' \
	'rog5_gmu_v9_resume_ret:.*ret=-117'
do
	[ "$(grep -Fc "$stale_return" "$probe")" -eq 0 ] ||
		fail "stale signed-64 return oracle survived: $stale_return"
done

trace_registration_line=$(line_once "$probe" \
	"'p:rog5_gmu_v9/rog5_gmu_v9_load_gpu msm:adreno_load_gpu dev=\$arg1:x64'" \
	'v9 trace registration')
helper_line=$(line_once "$probe" \
	"sh -c 'kill -STOP \"\$\$\"; exec \"\$1\"' sh \"\$helper\"" \
	'one-open stopped helper')
trace_oracle_line=$(line_once "$probe" \
	'trace_oracle_output=$("$trace_oracle" "$trace_snapshot")' \
	'signed device-scoped trace oracle')
clock_zero_line=$(line_once "$probe" \
	"require_event_count rog5_gmu_v9_clk_rate 0 'clock-rate activation'" \
	'zero clock-rate count')
logical_line=$(line_once "$probe" \
	"logical_gets=\$(( \$(event_count rog5_gmu_v9_kernel_new) +" \
	'logical vmap balance')
settle_line=$(line_once "$probe" 'sleep "$settle_seconds"' \
	'post-open settle')
snapshot_line=$(line_once "$probe" \
	'cmp "$state_dir/gem.before" "$state_dir/gem.after"' \
	'GEM snapshot equality')
[ "$trace_registration_line" -lt "$helper_line" ] &&
	[ "$helper_line" -lt "$trace_oracle_line" ] &&
	[ "$trace_oracle_line" -lt "$clock_zero_line" ] &&
	[ "$clock_zero_line" -lt "$logical_line" ] &&
	[ "$logical_line" -lt "$settle_line" ] &&
	[ "$settle_line" -lt "$snapshot_line" ] ||
	fail 'trace/helper/oracle/zero-work/logical/settle/snapshot order changed'

for zero_block in \
	'for forbidden_event in rog5_gmu_v9_msm_pm_resume' \
	'rog5_gmu_v9_a6xx_pm_resume rog5_gmu_v9_hfi_start' \
	'rog5_gmu_v9_devfreq_resume rog5_gmu_v9_llc_activate' \
	'rog5_gmu_v9_initial_freq rog5_gmu_v9_hw_init' \
	'rog5_gmu_v9_a6xx_hw_init rog5_gmu_v9_zap_init' \
	'rog5_gmu_v9_scm_available rog5_gmu_v9_scm_gpu_init' \
	'rog5_gmu_v9_scm_pas rog5_gmu_v9_scm_aperture'
do
	[ "$(grep -Fc "$zero_block" "$probe")" -eq 1 ] ||
		fail "zero-work forbidden-event block changed: $zero_block"
done

if grep -Eq \
	'(^|[;&|[:space:]])(fastboot|adb|ssh|scp)([[:space:]]|$)|systemctl[[:space:]]+poweroff|dd[[:space:]].*of=/dev/|mount[[:space:]].*/dev/' \
	"$baseline" "$probe"
then
	fail 'v9 runtime source controls transport or writes phone storage'
fi
if grep -Fq 'systemctl reboot' "$baseline" "$probe"; then
	fail 'v9 baseline or probe bypasses the compound reboot gate'
fi

echo 'PASS A660 GMU resume-entry v9 runtime pins unchanged v8 kernel/module, signed-int propagation, one GPU-device outer PM, zero inner resources, v7-proven rollback, settle/snapshot, watchdog, and storage isolation'
