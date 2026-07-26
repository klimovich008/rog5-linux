#!/bin/sh
# shellcheck disable=SC2016
set -eu

baseline=${1:?usage: verify-a660-gmu-resume-entry-v8-runtime-sources.sh BASELINE PROBE}
probe=${2:?missing probe}
repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)
live_report=$repo/test-results/2026-07-26-a660-ucode-allocation-v7-live-accepted.md
boundary_report=$repo/test-results/2026-07-26-a660-gmu-resume-entry-boundary.md
build_report=$repo/test-results/2026-07-26-a660-gmu-resume-entry-v8-offline.md
kernel_patch=$repo/patches/linux-7.1.4/0015-drm-msm-add-a660-gmu-resume-entry-diagnostic.patch
patch_verifier=$repo/scripts/device/verify-a660-gmu-resume-entry-patch.sh
relocation_verifier=$repo/scripts/device/verify-a660-gmu-resume-entry-vmap-relocations.sh
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
[ -x "$patch_verifier" ] ||
	fail 'verify-a660-gmu-resume-entry-patch.sh is absent'
[ -x "$relocation_verifier" ] ||
	fail 'v8 compiler-relocation verifier is absent'
for input in "$baseline" "$probe"; do
	[ -f "$input" ] && [ ! -L "$input" ] && [ -r "$input" ] ||
		fail "runtime source is missing, linked, or unreadable: $input"
	sh -n "$input"
done

if [ "${ALLOW_UNPINNED_A660_GMU_ENTRY_V8_RUNTIME:-0}" != 1 ]; then
	check_hash "$baseline" \
		3a4bcdcd9a96b896f22fda3be3f73c68a3b16e5d154558da9ad299c969faaf23 \
		'generated v8 baseline'
	check_hash "$probe" \
		832a96db228a9f0771c0ff364ed943100f243fbbce51ec4c0e2532e211a9e255 \
		'generated v8 probe'
fi
check_hash "$live_report" \
	ea4a4a87a264728be3bfcd86a2f12888496dd51c7421cbee166ad19afdb5ee6a \
	'accepted and consumed v7 live report'
check_hash "$boundary_report" \
	41c06dcd895fcc873638ddf40dce0b0d5dd5bbf9e148f5d3abd5521b072c320d \
	'GMU resume-entry source boundary report'
check_hash "$build_report" \
	6c50a822d30368bba4564daa77633b6e22ae1e167cd3486670b786e430153b7c \
	'reproducible v8 kernel build report'
check_hash "$kernel_patch" \
	a179ff9e31792238a3bd254297008d805e6a37b5d08125712c0151b1f39b3051 \
	'accepted GMU resume-entry kernel patch'
check_hash "$patch_verifier" \
	a380016efd29dd23d6037b2dbbfefef1fb9687860a63355d3a09e3477bbd7c49 \
	'static GMU resume-entry patch verifier'
check_hash "$relocation_verifier" \
	e602f61702093050f5faba7a28c8efe54f50bf74a68369aa6096c94427389bf1 \
	'v8 compiler-relocation verifier'
"$relocation_verifier" "$msm_module" >/dev/null

for boundary in \
	'exact chip ID `0x06060001`' \
	'before software mutation, PM domains, clocks, MMIO, IRQ, firmware start, HFI, hardware init, ZAP, or SCM' \
	'complete v7-proven ucode and firmware cleanup' \
	'deliberate `EUCLEAN`'
do
	grep -Fq "$boundary" "$boundary_report" ||
		fail "source boundary omits: $boundary"
done

for contract in \
	'7.1.4-rog5-a660reg1' \
	'/.rog5/root-ro' \
	'rog5-a660-gmu-resume-entry-v8-open' \
	'a660-gmu-resume-entry-v8-export' \
	'diagnostic_generation=v8' \
	'predecessor=v7_live_accepted_consumed' \
	ea4a4a87a264728be3bfcd86a2f12888496dd51c7421cbee166ad19afdb5ee6a \
	'predecessor_consumption_commit=12ad39c' \
	41c06dcd895fcc873638ddf40dce0b0d5dd5bbf9e148f5d3abd5521b072c320d \
	6c50a822d30368bba4564daa77633b6e22ae1e167cd3486670b786e430153b7c \
	a179ff9e31792238a3bd254297008d805e6a37b5d08125712c0151b1f39b3051 \
	'compiler_policy=PINNED_V8_MSM_RELOCATIONS' \
	'trace_policy=PID_FILTERED_GMU_ENTRY_AND_LOGICAL_VMAP' \
	'state_policy=PRE_POST_GEM_SNAPSHOT_EQUAL' \
	'gmu_entry_parameter_mode=0400' \
	'v7_reuse=FORBIDDEN' \
	'ALLOW_MAINLINE_A660_GMU_RESUME_ENTRY_V8' \
	b485e8719d6ddf80542a5dc2fdf5bba795d40c69fa220b44571323a8a1d7d861 \
	d222f3fe290ef0516ee0ec43082596bad2df0fcbc2e0bbb26987623cef90cf76 \
	8acab7b417d9ebde89a1de9ae1e2c261d352fcab122e31ecd580cec9fe2ae5e7 \
	'a660_zap.mbn' \
	'/dev/dri/renderD128' \
	'gmu_resume_entry_only=1' \
	'gmu_resume_entry_only=Y' \
	'firmware_request_only=N' \
	'ucode_allocation_only=N' \
	'OPEN_ERRNO=117' \
	'A660 GMU resume entry reached before resource activation; reject resume' \
	'A660 GMU resume entry passed and rolled back; reject open' \
	"Couldn't power up the GPU: -117" \
	'set_event_pid' \
	'rog5_gmu_v8' \
	'adreno_load_gpu' \
	'adreno_runtime_resume' \
	'a6xx_gmu_pm_resume' \
	'a6xx_gmu_resume' \
	'msm_a660_gmu_resume_entry_only_mark_hit' \
	'adreno_rollback_gpu_load_only' \
	'a6xx_ucode_unload' \
	'__pm_runtime_resume' \
	'clk_set_rate' \
	'enable_irq' \
	'a6xx_hfi_start' \
	'msm_devfreq_resume' \
	'a6xx_llc_activate' \
	'a6xx_gmu_set_initial_freq' \
	'adreno_hw_init' \
	'a6xx_hw_init' \
	'a6xx_zap_shader_init' \
	'qcom_scm_is_available' \
	'qcom_scm_gpu_init_regs' \
	'qcom_scm_pas_auth_and_reset' \
	'qcom_scm_set_gpu_smmu_aperture' \
	'4\n4096\n43288\n' \
	'kernel_news=3' \
	'kernel_puts=2' \
	'wrapper_gets=1' \
	'wrapper_puts=2' \
	'logical_gets=4' \
	'logical_puts=4' \
	'gem.before' \
	'gem.after' \
	'gem_snapshot=equal' \
	'outer_runtime_pm=1' \
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
	'watchdog=disarmed' \
	'v8 retained accepted v7 allocation and rollback state'
do
	if ! grep -Fq "$contract" "$baseline" "$probe"; then
		fail "v8 runtime sources omit: $contract"
	fi
done

for exact_input in "$baseline" "$probe"; do
	for exact_contract in \
		b485e8719d6ddf80542a5dc2fdf5bba795d40c69fa220b44571323a8a1d7d861 \
		d222f3fe290ef0516ee0ec43082596bad2df0fcbc2e0bbb26987623cef90cf76 \
		8acab7b417d9ebde89a1de9ae1e2c261d352fcab122e31ecd580cec9fe2ae5e7 \
		'a660_zap.mbn' \
		'drm_fds=0' \
		'storage=0'
	do
		grep -Fq "$exact_contract" "$exact_input" ||
			fail "runtime source omits exact boundary: $exact_input: $exact_contract"
	done
done

for rejected in \
	'ALLOW_MAINLINE_A660_UCODE_ALLOCATION_V7' \
	'events/rog5_ucode_v7' \
	'rog5-a660-ucode-allocation-v7-open' \
	'ucode_allocation_only=1' \
	'4096\n4096\n45056\n'
do
	if grep -Fq "$rejected" "$baseline" "$probe"; then
		fail "v8 retained runnable or rejected v7 runtime state: $rejected"
	fi
done

msm_line=$(line_once "$probe" \
	'insmod "$msm_module" separate_gpu_kms=1 gmu_resume_entry_only=1' \
	'exact GMU resume-entry MSM load')
snapshot_before_line=$(line_once "$probe" \
	'cat "$gem_debugfs" >"$state_dir/gem.before"' \
	'pre-open GEM snapshot')
trace_registration_line=$(line_once "$probe" \
	"'p:rog5_gmu_v8/rog5_gmu_v8_load_gpu msm:adreno_load_gpu dev=\$arg1:x64'" \
	'GMU trace registration')
helper_line=$(line_once "$probe" \
	"sh -c 'kill -STOP \"\$\$\"; exec \"\$1\"' sh \"\$helper\"" \
	'one-open stopped helper')
pid_filter_line=$(line_once "$probe" \
	'"$helper_pid" >"$trace_root/set_event_pid"' \
	'exact helper PID filter')
trace_start_line=$(line_once "$probe" \
	"post_fail 'trace start failed'" \
	'trace start')
continue_line=$(line_once "$probe" 'kill -CONT "$helper_pid"' \
	'helper trace-barrier release')
wait_line=$(line_once "$probe" 'wait "$helper_pid"' \
	'one-open helper wait')
stop_line=$(line_once "$probe" 'if ! stop_trace; then' \
	'trace stop and cleanup')
status_line=$(line_once "$probe" '[ "$helper_status" -eq 117 ]' \
	'EUCLEAN status check')
resume_count_line=$(line_once "$probe" \
	"require_event_count rog5_gmu_v8_resume 1 'A6xx GMU-resume entry'" \
	'exact GMU-resume count')
clock_zero_line=$(line_once "$probe" \
	"require_event_count rog5_gmu_v8_clk_rate 0 'clock-rate activation'" \
	'zero clock-rate count')
new_count_line=$(line_once "$probe" \
	"require_event_count rog5_gmu_v8_kernel_new 3 'kernel GEM new'" \
	'exact kernel-new count')
logical_line=$(line_once "$probe" \
	"logical_gets=\$(( \$(event_count rog5_gmu_v8_kernel_new) +" \
	'logical vmap balance')
settle_line=$(line_once "$probe" 'sleep "$settle_seconds"' \
	'post-open settle')
snapshot_after_line=$(line_once "$probe" \
	'cat "$gem_debugfs" >"$state_dir/gem.after"' \
	'post-open GEM snapshot')
snapshot_cmp_line=$(line_once "$probe" \
	'cmp "$state_dir/gem.before" "$state_dir/gem.after"' \
	'GEM snapshot equality')

[ "$msm_line" -lt "$snapshot_before_line" ] &&
	[ "$snapshot_before_line" -lt "$trace_registration_line" ] &&
	[ "$trace_registration_line" -lt "$helper_line" ] &&
	[ "$helper_line" -lt "$pid_filter_line" ] &&
	[ "$pid_filter_line" -lt "$trace_start_line" ] &&
	[ "$trace_start_line" -lt "$continue_line" ] &&
	[ "$continue_line" -lt "$wait_line" ] &&
	[ "$wait_line" -lt "$stop_line" ] &&
	[ "$stop_line" -lt "$status_line" ] &&
	[ "$status_line" -lt "$resume_count_line" ] &&
	[ "$resume_count_line" -lt "$new_count_line" ] &&
	[ "$new_count_line" -lt "$clock_zero_line" ] &&
	[ "$clock_zero_line" -lt "$logical_line" ] &&
	[ "$logical_line" -lt "$settle_line" ] &&
	[ "$settle_line" -lt "$snapshot_after_line" ] &&
	[ "$snapshot_after_line" -lt "$snapshot_cmp_line" ] ||
	fail 'module/snapshot/trace/open/GMU/zero-work/logical/settle order changed'

[ "$(grep -Fc 'sh -c '\''kill -STOP "$$"; exec "$1"'\'' sh "$helper"' \
	"$probe")" -eq 1 ] ||
	fail 'one-open helper invocation count changed'
[ "$(grep -Fc '"$helper_pid" >"$trace_root/set_event_pid"' \
	"$probe")" -eq 1 ] ||
	fail 'exact helper PID filter count changed'
[ "$(grep -Fc 'cmp "$state_dir/gem.before" "$state_dir/gem.after"' \
	"$probe")" -eq 1 ] ||
	fail 'GEM snapshot equality count changed'
[ "$(grep -Fc 'cmp "$state_dir/logical-objects" "$state_dir/unpins"' \
	"$probe")" -eq 1 ] ||
	fail 'logical rollback identity comparison changed'
[ "$(grep -Fxc "printf '4\\n4096\\n43288\\n' >\"\$state_dir/kernel-new-sizes.expected\"" \
	"$probe")" -eq 1 ] ||
	fail 'raw allocation-size oracle changed'

for requirement in \
	"rog5_gmu_v8_load_gpu 1 'adreno_load_gpu entry'" \
	"rog5_gmu_v8_runtime_resume 1 'Adreno runtime-resume entry'" \
	"rog5_gmu_v8_pm_resume 1 'A6xx GMU PM-resume entry'" \
	"rog5_gmu_v8_resume 1 'A6xx GMU-resume entry'" \
	"rog5_gmu_v8_mark_hit 1 'GMU resume-entry one-shot hit'" \
	"rog5_gmu_v8_rollback 1 'GPU-load rollback entry'" \
	"rog5_gmu_v8_kernel_new 3 'kernel GEM new'" \
	"rog5_gmu_v8_kernel_put 2 'kernel GEM put'" \
	"rog5_gmu_v8_get_vaddr 1 'public CPU vmap wrapper'" \
	"rog5_gmu_v8_put_vaddr 2 'public CPU vunmap wrapper'" \
	"rog5_gmu_v8_ucode_unload 1 'ucode unload'" \
	"rog5_gmu_v8_fw_request 2 'firmware request'" \
	"rog5_gmu_v8_fw_release 2 'firmware release'" \
	"rog5_gmu_v8_runtime_pm 1" \
	"rog5_gmu_v8_clk_rate 0" \
	"rog5_gmu_v8_enable_irq 0"
do
	[ "$(grep -Fc "require_event_count $requirement" "$probe")" -eq 1 ] ||
		fail "runtime count oracle changed: $requirement"
done

for trace_contract in \
	'p:rog5_gmu_v8/rog5_gmu_v8_load_gpu msm:adreno_load_gpu' \
	'r:rog5_gmu_v8/rog5_gmu_v8_load_gpu_ret msm:adreno_load_gpu' \
	'p:rog5_gmu_v8/rog5_gmu_v8_runtime_resume msm:adreno_runtime_resume' \
	'p:rog5_gmu_v8/rog5_gmu_v8_pm_resume msm:a6xx_gmu_pm_resume' \
	'p:rog5_gmu_v8/rog5_gmu_v8_resume msm:a6xx_gmu_resume' \
	'p:rog5_gmu_v8/rog5_gmu_v8_mark_hit msm:msm_a660_gmu_resume_entry_only_mark_hit' \
	'p:rog5_gmu_v8/rog5_gmu_v8_rollback msm:adreno_rollback_gpu_load_only' \
	'p:rog5_gmu_v8/rog5_gmu_v8_vma_map msm:msm_gem_vma_map' \
	'p:rog5_gmu_v8/rog5_gmu_v8_kernel_new msm:msm_gem_kernel_new' \
	'p:rog5_gmu_v8/rog5_gmu_v8_kernel_put msm:msm_gem_kernel_put' \
	'p:rog5_gmu_v8/rog5_gmu_v8_ucode_unload msm:a6xx_ucode_unload' \
	'p:rog5_gmu_v8/rog5_gmu_v8_fw_request request_firmware_direct' \
	'p:rog5_gmu_v8/rog5_gmu_v8_fw_release release_firmware' \
	'p:rog5_gmu_v8/rog5_gmu_v8_runtime_pm __pm_runtime_resume' \
	'p:rog5_gmu_v8/rog5_gmu_v8_clk_rate clk_set_rate' \
	'p:rog5_gmu_v8/rog5_gmu_v8_enable_irq enable_irq' \
	'p:rog5_gmu_v8/rog5_gmu_v8_hfi_start msm:a6xx_hfi_start' \
	'p:rog5_gmu_v8/rog5_gmu_v8_devfreq_resume msm:msm_devfreq_resume' \
	'p:rog5_gmu_v8/rog5_gmu_v8_llc_activate msm:a6xx_llc_activate' \
	'p:rog5_gmu_v8/rog5_gmu_v8_hw_init msm:adreno_hw_init' \
	'p:rog5_gmu_v8/rog5_gmu_v8_a6xx_hw_init msm:a6xx_hw_init' \
	'p:rog5_gmu_v8/rog5_gmu_v8_zap_init msm:a6xx_zap_shader_init' \
	'p:rog5_gmu_v8/rog5_gmu_v8_scm_available qcom_scm_is_available' \
	'p:rog5_gmu_v8/rog5_gmu_v8_scm_gpu_init qcom_scm_gpu_init_regs' \
	'p:rog5_gmu_v8/rog5_gmu_v8_scm_pas qcom_scm_pas_auth_and_reset' \
	'p:rog5_gmu_v8/rog5_gmu_v8_scm_aperture qcom_scm_set_gpu_smmu_aperture'
do
	[ "$(grep -Fc "$trace_contract" "$probe")" -eq 1 ] ||
		fail "GMU resume-entry trace registration changed: $trace_contract"
done

for zero_block in \
	'for forbidden_event in rog5_gmu_v8_msm_pm_resume' \
	'rog5_gmu_v8_a6xx_pm_resume rog5_gmu_v8_hfi_start' \
	'rog5_gmu_v8_devfreq_resume rog5_gmu_v8_llc_activate' \
	'rog5_gmu_v8_initial_freq rog5_gmu_v8_hw_init' \
	'rog5_gmu_v8_a6xx_hw_init rog5_gmu_v8_zap_init' \
	'rog5_gmu_v8_scm_available rog5_gmu_v8_scm_gpu_init' \
	'rog5_gmu_v8_scm_pas rog5_gmu_v8_scm_aperture'
do
	[ "$(grep -Fc "$zero_block" "$probe")" -eq 1 ] ||
		fail "zero-work forbidden-event block changed: $zero_block"
done

if grep -Eq \
	'(^|[;&|[:space:]])(fastboot|adb|ssh|scp)([[:space:]]|$)|systemctl[[:space:]]+poweroff|dd[[:space:]].*of=/dev/|mount[[:space:]].*/dev/' \
	"$baseline" "$probe"
then
	fail 'v8 runtime source controls transport or writes phone storage'
fi
if grep -Fq 'systemctl reboot' "$baseline" "$probe"; then
	fail 'v8 baseline or probe bypasses the compound reboot gate'
fi

echo 'PASS A660 GMU resume-entry v8 runtime pins accepted-v7 cleanup, compiler semantics, one outer and zero inner PM, zero resources/HFI/hardware/SCM, equal GEM snapshots, watchdog, and storage isolation'
