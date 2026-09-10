#!/bin/sh
# shellcheck disable=SC2016
set -eu

baseline=${1:?usage: verify-a660-ucode-allocation-runtime-sources.sh BASELINE PROBE}
probe=${2:?missing probe}
repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)
accepted_baseline=$repo/scripts/device/check-network-root-a660-ucode-allocation-baseline.sh
accepted_probe=$repo/scripts/device/probe-network-root-a660-ucode-allocation.sh
baseline_hash=4f2e50fd492c9fff06198396c1fd80fa877b1447f18920d9895ad82c4034e041
probe_hash=63adc85bdd3b4f5b08130722d30615fad1a439eb3aa2a43a4b161e826c36c3ef

fail() {
	echo "FAIL $*" >&2
	exit 1
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
	command -v "$command" >/dev/null ||
		fail "missing command: $command"
done
for input in "$baseline" "$probe"; do
	[ -f "$input" ] && [ ! -L "$input" ] && [ -r "$input" ] ||
		fail "runtime source is missing, linked, or unreadable: $input"
	sh -n "$input"
done

if [ "${ALLOW_UNPINNED_A660_UCODE_RUNTIME:-0}" != 1 ]; then
	[ "$baseline" = "$accepted_baseline" ] ||
		fail 'baseline path is not accepted'
	[ "$probe" = "$accepted_probe" ] ||
		fail 'probe path is not accepted'
	[ "$(sha256sum "$baseline" | cut -d ' ' -f 1)" = \
		"$baseline_hash" ] ||
		fail 'baseline hash mismatch'
	[ "$(sha256sum "$probe" | cut -d ' ' -f 1)" = "$probe_hash" ] ||
		fail 'probe hash mismatch'
fi

for contract in \
	'7.1.4-rog5-a660reg1' \
	'/.rog5/root-ro' \
	'a660-registration-v3-live.accepted' \
	8d350d51d8f35583f6ba32f005fc9b9fc035c6f24186c5b1786b2f60a90a0f6f \
	2af09c087c917b7d1325c0b8a361c7ec3594779983034be0736acac841f8da79 \
	d3303a04182625606e0dfc343205f677a80fcf55ab6928de53fad82852863bae \
	fe5d59675e4f7d490c38cc7e9c02cadb7bbf89047ceb8056aa0a3e13353bcc45 \
	d222f3fe290ef0516ee0ec43082596bad2df0fcbc2e0bbb26987623cef90cf76 \
	8acab7b417d9ebde89a1de9ae1e2c261d352fcab122e31ecd580cec9fe2ae5e7 \
	'a660_zap.mbn' \
	'/dev/dri/renderD128' \
	'ucode_allocation_only=1' \
	'firmware_request_only=N' \
	'separate_gpu_kms=1' \
	'A660 ucode-allocation-only passed and rolled back; reject open' \
	'A660 ucode-allocation-only failed:' \
	'OPEN_ERRNO=117' \
	'CONFIG_KPROBE_EVENTS=y' \
	'CONFIG_KALLSYMS_ALL=y' \
	'CONFIG_DEBUG_FS=y' \
	'set_event_pid' \
	'msm_gem_vma_map' \
	'msm_gem_vma_unmap' \
	'msm_gem_vma_close' \
	'msm_gem_free_object' \
	'msm_gem_get_vaddr' \
	'msm_gem_put_vaddr' \
	'request_firmware_direct' \
	'release_firmware' \
	'qcom_scm_pas_auth_and_reset' \
	'qcom_scm_set_gpu_smmu_aperture' \
	'gem.before' \
	'gem.after' \
	'gem_snapshot=equal' \
	'maps=3' \
	'unmaps=3' \
	'closes=3' \
	'gem_frees=3' \
	'cpu_vmaps=4' \
	'cpu_vunmaps=4' \
	'firmware_requests=2' \
	'firmware_releases=2' \
	'power=0' \
	'hfi=0' \
	'scm=0' \
	'drm_fds=0' \
	'storage=0 mounts=0'
do
	if ! grep -Fq "$contract" "$baseline" "$probe"; then
		fail "runtime sources omit: $contract"
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
	"'p:rog5_ucode/rog5_ucode_vma_map msm:msm_gem_vma_map vma=\$arg1:x64'" \
	'VMA map trace registration')
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
map_count_line=$(line_once "$probe" \
	"require_event_count rog5_ucode_vma_map 3 'VMA map'" \
	'exact map count')
pointer_line=$(line_once "$probe" \
	'cmp "$state_dir/maps" "$state_dir/unmaps"' \
	'map/unmap pointer equality')
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
	[ "$status_line" -lt "$map_count_line" ] &&
	[ "$map_count_line" -lt "$pointer_line" ] &&
	[ "$pointer_line" -lt "$settle_line" ] &&
	[ "$settle_line" -lt "$snapshot_after_line" ] &&
	[ "$snapshot_after_line" -lt "$snapshot_cmp_line" ] ||
	fail 'module/snapshot/trace/open/evidence/settle order changed'

[ "$(grep -Fc 'sh -c '\''kill -STOP "$$"; exec "$1"'\'' sh "$helper"' \
	"$probe")" -eq 1 ] ||
	fail 'one-open helper invocation count changed'
[ "$(grep -Fc '"$helper_pid" >"$trace_root/set_event_pid"' \
	"$probe")" -eq 1 ] ||
	fail 'exact helper PID filter count changed'
[ "$(grep -Fc 'grep -Fc "$success_marker"' "$probe")" -eq 2 ] ||
	fail 'success marker is not checked before and after settling'
[ "$(grep -Fc 'grep -Fc "$failure_marker"' "$probe")" -eq 2 ] ||
	fail 'failure marker is not checked before and after settling'
[ "$(grep -Fc 'check_no_drm_fds ||' "$probe")" -ge 4 ] ||
	fail 'DRM descriptor boundary is not repeatedly checked'
[ "$(grep -Fc 'runtime_status' "$probe")" -ge 4 ] ||
	fail 'runtime-suspend boundary is not checked'
[ "$(grep -Fc 'cmp "$state_dir/maps" "$state_dir/unmaps"' "$probe")" -eq 1 ]
[ "$(grep -Fc 'cmp "$state_dir/maps" "$state_dir/closes"' "$probe")" -eq 1 ]
[ "$(grep -Fc 'cmp "$state_dir/unpins" "$state_dir/frees"' "$probe")" -eq 1 ]
[ "$(grep -Fc 'cmp "$state_dir/vmaps" "$state_dir/vunmaps"' "$probe")" -eq 1 ]
[ "$(grep -Fc 'cmp "$state_dir/gem.before" "$state_dir/gem.after"' \
	"$probe")" -eq 1 ]

for trace_contract in \
	'p:rog5_ucode/rog5_ucode_diag msm:adreno_load_ucode_only' \
	'r:rog5_ucode/rog5_ucode_diag_ret msm:adreno_load_ucode_only' \
	'p:rog5_ucode/rog5_ucode_vma_map msm:msm_gem_vma_map' \
	'r:rog5_ucode/rog5_ucode_vma_map_ret msm:msm_gem_vma_map' \
	'p:rog5_ucode/rog5_ucode_vma_unmap msm:msm_gem_vma_unmap' \
	'p:rog5_ucode/rog5_ucode_vma_close msm:msm_gem_vma_close' \
	'p:rog5_ucode/rog5_ucode_gem_unpin msm:msm_gem_unpin_iova' \
	'p:rog5_ucode/rog5_ucode_gem_free msm:msm_gem_free_object' \
	'p:rog5_ucode/rog5_ucode_get_vaddr msm:msm_gem_get_vaddr' \
	'p:rog5_ucode/rog5_ucode_put_vaddr msm:msm_gem_put_vaddr' \
	'p:rog5_ucode/rog5_ucode_kernel_put msm:msm_gem_kernel_put' \
	'p:rog5_ucode/rog5_ucode_unload msm:a6xx_ucode_unload' \
	'p:rog5_ucode/rog5_ucode_fw_request request_firmware_direct' \
	'p:rog5_ucode/rog5_ucode_fw_release release_firmware' \
	'p:rog5_ucode/rog5_ucode_pm_resume msm:msm_gpu_pm_resume' \
	'p:rog5_ucode/rog5_ucode_runtime_resume msm:adreno_runtime_resume' \
	'p:rog5_ucode/rog5_ucode_a6xx_pm_resume msm:a6xx_pm_resume' \
	'p:rog5_ucode/rog5_ucode_gmu_resume msm:a6xx_gmu_resume' \
	'p:rog5_ucode/rog5_ucode_hw_init msm:adreno_hw_init' \
	'p:rog5_ucode/rog5_ucode_a6xx_hw_init msm:a6xx_hw_init' \
	'p:rog5_ucode/rog5_ucode_zap_init msm:a6xx_zap_shader_init' \
	'p:rog5_ucode/rog5_ucode_scm_pas qcom_scm_pas_auth_and_reset' \
	'p:rog5_ucode/rog5_ucode_scm_aperture qcom_scm_set_gpu_smmu_aperture'
do
	[ "$(grep -Fc "$trace_contract" "$probe")" -eq 1 ] ||
		fail "required trace registration count changed: $trace_contract"
done

for forbidden_event in rog5_ucode_pm_resume rog5_ucode_runtime_resume \
	rog5_ucode_a6xx_pm_resume rog5_ucode_gmu_resume rog5_ucode_hw_init \
	rog5_ucode_a6xx_hw_init rog5_ucode_zap_init rog5_ucode_scm_pas \
	rog5_ucode_scm_aperture
do
	[ "$(grep -Fc "$forbidden_event" "$probe")" -ge 2 ] ||
		fail "forbidden trace event is not registered and checked: $forbidden_event"
done

if grep -Eq \
	'(^|[;&|[:space:]])(fastboot|adb|ssh|scp)([[:space:]]|$)|systemctl[[:space:]]+poweroff|dd[[:space:]].*of=/dev/|mount[[:space:]].*/dev/' \
	"$baseline" "$probe"
then
	fail 'runtime source can control transport or write phone storage'
fi
if grep -Fq 'systemctl reboot' "$baseline" "$probe"; then
	fail 'baseline or probe can bypass the compound reboot gate'
fi

echo 'PASS ucode-allocation runtime sources pin exact firmware and module, PID-filtered balanced mapping/GEM/firmware traces, equal state snapshots, watchdog, and storage isolation'
