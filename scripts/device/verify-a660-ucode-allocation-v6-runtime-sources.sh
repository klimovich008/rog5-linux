#!/bin/sh
# shellcheck disable=SC2016
set -eu

baseline=${1:?usage: verify-a660-ucode-allocation-v6-runtime-sources.sh BASELINE PROBE}
probe=${2:?missing probe}
repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)
rejection=$repo/test-results/2026-07-26-a660-ucode-allocation-v5-live-rejected.md
relocation_verifier=$repo/scripts/device/verify-a660-ucode-vmap-relocations.sh
msm_module=$repo/artifacts/a660-ucode-allocation-build-a/drivers/gpu/drm/msm/msm.ko

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
[ -x "$relocation_verifier" ] ||
	fail 'accepted compiler-relocation verifier is absent'
for input in "$baseline" "$probe"; do
	[ -f "$input" ] && [ ! -L "$input" ] && [ -r "$input" ] ||
		fail "runtime source is missing, linked, or unreadable: $input"
	sh -n "$input"
done

if [ "${ALLOW_UNPINNED_A660_UCODE_V6_RUNTIME:-0}" != 1 ]; then
	check_hash "$baseline" \
		5ad24829bd347fcc22239d761029f3c0f8064efa1b16e9f01b6cf745902df854 \
		'generated v6 baseline'
	check_hash "$probe" \
		b90e33524da2558659a733c48d5670d2136208a9186d5abb3ecd79f1e28f2725 \
		'generated v6 probe'
fi
check_hash "$rejection" \
	0c65c98cc03a49d9e5c8a15b391dbe2b6014b5e791a8659c06cd7c2d0bf52fb9 \
	'v5 live rejection report'
"$relocation_verifier" "$msm_module" >/dev/null

for contract in \
	'7.1.4-rog5-a660reg1' \
	'/.rog5/root-ro' \
	'rog5-a660-ucode-allocation-v6-open' \
	'a660-ucode-allocation-v6-export' \
	'diagnostic_generation=v6' \
	'predecessor=v5_live_rejected_consumed' \
	0c65c98cc03a49d9e5c8a15b391dbe2b6014b5e791a8659c06cd7c2d0bf52fb9 \
	'compiler_policy=PINNED_MSM_RELOCATIONS' \
	'trace_policy=PID_FILTERED_LOGICAL_VMAP_BALANCE' \
	'state_policy=PRE_POST_GEM_SNAPSHOT_EQUAL' \
	'v5_reuse=FORBIDDEN' \
	'ALLOW_MAINLINE_A660_UCODE_ALLOCATION_V6' \
	fe5d59675e4f7d490c38cc7e9c02cadb7bbf89047ceb8056aa0a3e13353bcc45 \
	d3303a04182625606e0dfc343205f677a80fcf55ab6928de53fad82852863bae \
	d222f3fe290ef0516ee0ec43082596bad2df0fcbc2e0bbb26987623cef90cf76 \
	8acab7b417d9ebde89a1de9ae1e2c261d352fcab122e31ecd580cec9fe2ae5e7 \
	'a660_zap.mbn' \
	'/dev/dri/renderD128' \
	'ucode_allocation_only=1' \
	'firmware_request_only=N' \
	'separate_gpu_kms=1' \
	'A660 ucode-allocation-only passed and rolled back; reject open' \
	'OPEN_ERRNO=117' \
	'set_event_pid' \
	'rog5_ucode_v6' \
	'msm_gem_kernel_new' \
	'msm_gem_kernel_put' \
	'kernel GEM new sizes are not exact' \
	'public wrapper object identities differ' \
	'logical rollback and unpinned GEM object sets differ' \
	'logical CPU vmap balance is not four/four' \
	'4096\n4096\n45056\n' \
	'kernel_news=3' \
	'kernel_puts=2' \
	'wrapper_gets=1' \
	'wrapper_puts=2' \
	'logical_gets=4' \
	'logical_puts=4' \
	'gem.before' \
	'gem.after' \
	'gem_snapshot=equal' \
	'power=0' \
	'hfi=0' \
	'scm=0' \
	'drm_fds=0' \
	'storage=0 mounts=0' \
	'watchdog=disarmed'
do
	if ! grep -Fq "$contract" "$baseline" "$probe"; then
		fail "v6 runtime sources omit: $contract"
	fi
done

for exact_input in "$baseline" "$probe"; do
	for exact_contract in \
		d3303a04182625606e0dfc343205f677a80fcf55ab6928de53fad82852863bae \
		fe5d59675e4f7d490c38cc7e9c02cadb7bbf89047ceb8056aa0a3e13353bcc45 \
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

msm_line=$(line_once "$probe" \
	'insmod "$msm_module" separate_gpu_kms=1 ucode_allocation_only=1' \
	'exact ucode-allocation MSM load')
snapshot_before_line=$(line_once "$probe" \
	'cat "$gem_debugfs" >"$state_dir/gem.before"' \
	'pre-open GEM snapshot')
trace_registration_line=$(line_once "$probe" \
	"'p:rog5_ucode_v6/rog5_ucode_kernel_new msm:msm_gem_kernel_new size=\$arg2:u64'" \
	'kernel-new trace registration')
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
new_count_line=$(line_once "$probe" \
	"require_event_count rog5_ucode_kernel_new 3 'kernel GEM new'" \
	'exact kernel-new count')
logical_line=$(line_once "$probe" \
	"logical_gets=\$(( \$(event_count rog5_ucode_kernel_new) +" \
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
	[ "$status_line" -lt "$new_count_line" ] &&
	[ "$new_count_line" -lt "$logical_line" ] &&
	[ "$logical_line" -lt "$settle_line" ] &&
	[ "$settle_line" -lt "$snapshot_after_line" ] &&
	[ "$snapshot_after_line" -lt "$snapshot_cmp_line" ] ||
	fail 'module/snapshot/trace/open/logical-balance/settle order changed'

[ "$(grep -Fc 'sh -c '\''kill -STOP "$$"; exec "$1"'\'' sh "$helper"' \
	"$probe")" -eq 1 ] ||
	fail 'one-open helper invocation count changed'
[ "$(grep -Fc '"$helper_pid" >"$trace_root/set_event_pid"' \
	"$probe")" -eq 1 ] ||
	fail 'exact helper PID filter count changed'
[ "$(grep -Fc 'cmp "$state_dir/gem.before" "$state_dir/gem.after"' \
	"$probe")" -eq 1 ]
[ "$(grep -Fc 'cmp "$state_dir/logical-objects" "$state_dir/unpins"' \
	"$probe")" -eq 1 ]
[ "$(grep -Fc "require_event_count rog5_ucode_kernel_new 3" \
	"$probe")" -eq 1 ]
[ "$(grep -Fc "require_event_count rog5_ucode_kernel_put 2" \
	"$probe")" -eq 1 ]
[ "$(grep -Fc "require_event_count rog5_ucode_get_vaddr 1" \
	"$probe")" -eq 1 ]
[ "$(grep -Fc "require_event_count rog5_ucode_put_vaddr 2" \
	"$probe")" -eq 1 ]

for trace_contract in \
	'p:rog5_ucode_v6/rog5_ucode_diag msm:adreno_load_ucode_only' \
	'r:rog5_ucode_v6/rog5_ucode_diag_ret msm:adreno_load_ucode_only' \
	'p:rog5_ucode_v6/rog5_ucode_vma_map msm:msm_gem_vma_map' \
	'r:rog5_ucode_v6/rog5_ucode_vma_map_ret msm:msm_gem_vma_map' \
	'p:rog5_ucode_v6/rog5_ucode_vma_unmap msm:msm_gem_vma_unmap' \
	'p:rog5_ucode_v6/rog5_ucode_vma_close msm:msm_gem_vma_close' \
	'p:rog5_ucode_v6/rog5_ucode_gem_unpin msm:msm_gem_unpin_iova' \
	'p:rog5_ucode_v6/rog5_ucode_gem_free msm:msm_gem_free_object' \
	'p:rog5_ucode_v6/rog5_ucode_kernel_new msm:msm_gem_kernel_new' \
	'r:rog5_ucode_v6/rog5_ucode_kernel_new_ret msm:msm_gem_kernel_new' \
	'p:rog5_ucode_v6/rog5_ucode_kernel_put msm:msm_gem_kernel_put' \
	'p:rog5_ucode_v6/rog5_ucode_get_vaddr msm:msm_gem_get_vaddr' \
	'p:rog5_ucode_v6/rog5_ucode_put_vaddr msm:msm_gem_put_vaddr' \
	'p:rog5_ucode_v6/rog5_ucode_unload msm:a6xx_ucode_unload' \
	'p:rog5_ucode_v6/rog5_ucode_fw_request request_firmware_direct' \
	'p:rog5_ucode_v6/rog5_ucode_fw_release release_firmware' \
	'p:rog5_ucode_v6/rog5_ucode_pm_resume msm:msm_gpu_pm_resume' \
	'p:rog5_ucode_v6/rog5_ucode_runtime_resume msm:adreno_runtime_resume' \
	'p:rog5_ucode_v6/rog5_ucode_a6xx_pm_resume msm:a6xx_pm_resume' \
	'p:rog5_ucode_v6/rog5_ucode_gmu_resume msm:a6xx_gmu_resume' \
	'p:rog5_ucode_v6/rog5_ucode_hw_init msm:adreno_hw_init' \
	'p:rog5_ucode_v6/rog5_ucode_a6xx_hw_init msm:a6xx_hw_init' \
	'p:rog5_ucode_v6/rog5_ucode_zap_init msm:a6xx_zap_shader_init' \
	'p:rog5_ucode_v6/rog5_ucode_scm_pas qcom_scm_pas_auth_and_reset' \
	'p:rog5_ucode_v6/rog5_ucode_scm_aperture qcom_scm_set_gpu_smmu_aperture'
do
	[ "$(grep -Fc "$trace_contract" "$probe")" -eq 1 ] ||
		fail "logical-vmap trace registration changed: $trace_contract"
done

if grep -Fq "require_event_count rog5_ucode_get_vaddr 4 'CPU vmap'" "$probe" ||
	grep -Fq "require_event_count rog5_ucode_put_vaddr 4 'CPU vunmap'" "$probe" ||
	grep -Fq 'cmp "$state_dir/vmaps" "$state_dir/vunmaps"' "$probe"
then
	fail 'v6 retained the rejected public-wrapper oracle'
fi

if grep -Eq \
	'(^|[;&|[:space:]])(fastboot|adb|ssh|scp)([[:space:]]|$)|systemctl[[:space:]]+poweroff|dd[[:space:]].*of=/dev/|mount[[:space:]].*/dev/' \
	"$baseline" "$probe"
then
	fail 'v6 runtime source controls transport or writes phone storage'
fi
if grep -Fq 'systemctl reboot' "$baseline" "$probe"; then
	fail 'v6 baseline or probe bypasses the compound reboot gate'
fi

echo 'PASS A660 ucode-allocation v6 runtime pins compiler semantics, direct kernel-new/put traces, logical 4/4 vmap balance, equal GEM snapshots, watchdog, and storage isolation'
