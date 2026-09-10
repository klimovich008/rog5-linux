#!/bin/sh
# shellcheck disable=SC2016
set -eu

baseline=${1:?usage: verify-a660-ucode-allocation-v7-runtime-sources.sh BASELINE PROBE}
probe=${2:?missing probe}
repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)
boundary_report=$repo/test-results/2026-07-26-a660-ucode-allocation-boundary.md
rejection=$repo/test-results/2026-07-26-a660-ucode-allocation-v6-live-rejected.md
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

if [ "${ALLOW_UNPINNED_A660_UCODE_V7_RUNTIME:-0}" != 1 ]; then
	check_hash "$baseline" \
		d8c2d697d20c213f3528d6a4cf99ca7d0243bf83222a34ff6f665ab22fc27386 \
		'generated v7 baseline'
	check_hash "$probe" \
		01a681bdf9fc17b3c676797cafadc43338eee49f2a5e3b7c6789edc1c7056cf0 \
		'generated v7 probe'
fi
check_hash "$boundary_report" \
	a17847d18c21d5b2c039df4353a899abce37159ec0009b5afaa0dda6067d146f \
	'ucode-allocation source boundary report'
check_hash "$rejection" \
	cfdd0837e6da7d06ba74e0557c6abeea396f12f02e345d9ab87ba1a47ade89e6 \
	'v6 live rejection report'
"$relocation_verifier" "$msm_module" >/dev/null

for boundary in \
	'| SQE firmware | 43,288 | 45,056 | 11 |' \
	'| RPTR shadow | 4 | 4,096 | 1 |' \
	'| power-up reglist | 4,096 | 4,096 | 1 |' \
	'`msm_gem_new()` page-aligns every object.'
do
	grep -Fq "$boundary" "$boundary_report" ||
		fail "source boundary omits raw/object size proof: $boundary"
done

for contract in \
	'7.1.4-rog5-a660reg1' \
	'/.rog5/root-ro' \
	'rog5-a660-ucode-allocation-v7-open' \
	'a660-ucode-allocation-v7-export' \
	'diagnostic_generation=v7' \
	'predecessor=v6_live_rejected_consumed' \
	cfdd0837e6da7d06ba74e0557c6abeea396f12f02e345d9ab87ba1a47ade89e6 \
	'predecessor_consumption_commit=664fd09' \
	a17847d18c21d5b2c039df4353a899abce37159ec0009b5afaa0dda6067d146f \
	'compiler_policy=PINNED_MSM_RELOCATIONS' \
	'size_policy=RAW_KERNEL_NEW_ENTRY_ARGUMENTS' \
	'raw_size_contract=4,4096,43288' \
	'object_size_policy=SOURCE_PINNED_PAGE_ALIGN' \
	'object_size_contract=4096,4096,45056' \
	'trace_policy=PID_FILTERED_LOGICAL_VMAP_BALANCE' \
	'state_policy=PRE_POST_GEM_SNAPSHOT_EQUAL' \
	'v6_reuse=FORBIDDEN' \
	'ALLOW_MAINLINE_A660_UCODE_ALLOCATION_V7' \
	fe5d59675e4f7d490c38cc7e9c02cadb7bbf89047ceb8056aa0a3e13353bcc45 \
	'd222f3fe290ef0516ee0ec43082596bad2df0fcbc2e0bbb26987623cef90cf76' \
	'8acab7b417d9ebde89a1de9ae1e2c261d352fcab122e31ecd580cec9fe2ae5e7' \
	'a660_zap.mbn' \
	'/dev/dri/renderD128' \
	'ucode_allocation_only=1' \
	'firmware_request_only=N' \
	'OPEN_ERRNO=117' \
	'set_event_pid' \
	'rog5_ucode_v7' \
	'msm_gem_kernel_new' \
	'msm_gem_kernel_put' \
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
	'power=0' \
	'hfi=0' \
	'scm=0' \
	'drm_fds=0' \
	'storage=0 mounts=0' \
	'watchdog=disarmed'
do
	if ! grep -Fq "$contract" "$baseline" "$probe"; then
		fail "v7 runtime sources omit: $contract"
	fi
done

for exact_input in "$baseline" "$probe"; do
	for exact_contract in \
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

for rejected in \
	'ALLOW_MAINLINE_A660_UCODE_ALLOCATION_V6' \
	'events/rog5_ucode_v6' \
	'rog5-a660-ucode-allocation-v6-open' \
	'4096\n4096\n45056\n'
do
	if grep -Fq "$rejected" "$baseline" "$probe"; then
		fail "v7 retained rejected v6 runtime state: $rejected"
	fi
done

msm_line=$(line_once "$probe" \
	'insmod "$msm_module" separate_gpu_kms=1 ucode_allocation_only=1' \
	'exact ucode-allocation MSM load')
snapshot_before_line=$(line_once "$probe" \
	'cat "$gem_debugfs" >"$state_dir/gem.before"' \
	'pre-open GEM snapshot')
trace_registration_line=$(line_once "$probe" \
	"'p:rog5_ucode_v7/rog5_ucode_kernel_new msm:msm_gem_kernel_new size=\$arg2:u64'" \
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
raw_size_line=$(line_once "$probe" \
	"post_fail 'kernel GEM new sizes are not exact'" \
	'raw kernel-new size oracle')
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
	[ "$new_count_line" -lt "$raw_size_line" ] &&
	[ "$raw_size_line" -lt "$logical_line" ] &&
	[ "$logical_line" -lt "$settle_line" ] &&
	[ "$settle_line" -lt "$snapshot_after_line" ] &&
	[ "$snapshot_after_line" -lt "$snapshot_cmp_line" ] ||
	fail 'module/snapshot/trace/open/raw-size/logical/settle order changed'

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
[ "$(grep -Fxc "printf '4\\n4096\\n43288\\n' >\"\$state_dir/kernel-new-sizes.expected\"" \
	"$probe")" -eq 1 ]

for trace_contract in \
	'p:rog5_ucode_v7/rog5_ucode_diag msm:adreno_load_ucode_only' \
	'r:rog5_ucode_v7/rog5_ucode_diag_ret msm:adreno_load_ucode_only' \
	'p:rog5_ucode_v7/rog5_ucode_vma_map msm:msm_gem_vma_map' \
	'r:rog5_ucode_v7/rog5_ucode_vma_map_ret msm:msm_gem_vma_map' \
	'p:rog5_ucode_v7/rog5_ucode_vma_unmap msm:msm_gem_vma_unmap' \
	'p:rog5_ucode_v7/rog5_ucode_vma_close msm:msm_gem_vma_close' \
	'p:rog5_ucode_v7/rog5_ucode_gem_unpin msm:msm_gem_unpin_iova' \
	'p:rog5_ucode_v7/rog5_ucode_gem_free msm:msm_gem_free_object' \
	'p:rog5_ucode_v7/rog5_ucode_kernel_new msm:msm_gem_kernel_new' \
	'r:rog5_ucode_v7/rog5_ucode_kernel_new_ret msm:msm_gem_kernel_new' \
	'p:rog5_ucode_v7/rog5_ucode_kernel_put msm:msm_gem_kernel_put' \
	'p:rog5_ucode_v7/rog5_ucode_get_vaddr msm:msm_gem_get_vaddr' \
	'p:rog5_ucode_v7/rog5_ucode_put_vaddr msm:msm_gem_put_vaddr' \
	'p:rog5_ucode_v7/rog5_ucode_unload msm:a6xx_ucode_unload' \
	'p:rog5_ucode_v7/rog5_ucode_fw_request request_firmware_direct' \
	'p:rog5_ucode_v7/rog5_ucode_fw_release release_firmware' \
	'p:rog5_ucode_v7/rog5_ucode_pm_resume msm:msm_gpu_pm_resume' \
	'p:rog5_ucode_v7/rog5_ucode_runtime_resume msm:adreno_runtime_resume' \
	'p:rog5_ucode_v7/rog5_ucode_a6xx_pm_resume msm:a6xx_pm_resume' \
	'p:rog5_ucode_v7/rog5_ucode_gmu_resume msm:a6xx_gmu_resume' \
	'p:rog5_ucode_v7/rog5_ucode_hw_init msm:adreno_hw_init' \
	'p:rog5_ucode_v7/rog5_ucode_a6xx_hw_init msm:a6xx_hw_init' \
	'p:rog5_ucode_v7/rog5_ucode_zap_init msm:a6xx_zap_shader_init' \
	'p:rog5_ucode_v7/rog5_ucode_scm_pas qcom_scm_pas_auth_and_reset' \
	'p:rog5_ucode_v7/rog5_ucode_scm_aperture qcom_scm_set_gpu_smmu_aperture'
do
	[ "$(grep -Fc "$trace_contract" "$probe")" -eq 1 ] ||
		fail "logical-vmap trace registration changed: $trace_contract"
done

if grep -Eq \
	'(^|[;&|[:space:]])(fastboot|adb|ssh|scp)([[:space:]]|$)|systemctl[[:space:]]+poweroff|dd[[:space:]].*of=/dev/|mount[[:space:]].*/dev/' \
	"$baseline" "$probe"
then
	fail 'v7 runtime source controls transport or writes phone storage'
fi
if grep -Fq 'systemctl reboot' "$baseline" "$probe"; then
	fail 'v7 baseline or probe bypasses the compound reboot gate'
fi

echo 'PASS A660 ucode-allocation v7 runtime pins raw and page-rounded size layers, compiler semantics, logical 4/4 vmap balance, equal GEM snapshots, watchdog, and storage isolation'
