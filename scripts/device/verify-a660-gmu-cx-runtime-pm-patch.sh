#!/bin/sh
set -eu

patch=${1:?usage: verify-a660-gmu-cx-runtime-pm-patch.sh PATCH PINNED_SOURCE}
source_dir=${2:?missing pinned source}
repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)
accepted_patch=$repo/patches/linux-7.1.4/0016-drm-msm-add-a660-gmu-cx-runtime-pm-diagnostic.patch
patch12=$repo/patches/linux-7.1.4/0012-drm-msm-a6xx-propagate-gmu-pwrlevels-error.patch
patch13=$repo/patches/linux-7.1.4/0013-drm-msm-add-a660-firmware-request-only-diagnostic.patch
patch14=$repo/patches/linux-7.1.4/0014-drm-msm-add-a660-ucode-allocation-diagnostic.patch
patch15=$repo/patches/linux-7.1.4/0015-drm-msm-add-a660-gmu-resume-entry-diagnostic.patch
boundary=$repo/scripts/device/verify-a660-gmu-cx-runtime-pm-boundary.sh

expected_commit=d9ac316489f4258d389d6298659d5e9c22183400
expected_tree=c796deb1cc54e942f8bb46a2c76a7199e19e5c92
expected_boundary=6ba90691000f9369b5fdfdbf235495f9afeba4984c11596888cc1213717d7b06
expected_patch=5eef04eb711443acaaf4295e926577f90073b8ab62414cff3d18de2272d3a152

msm_drv_rel=drivers/gpu/drm/msm/msm_drv.c
msm_gpu_h_rel=drivers/gpu/drm/msm/msm_gpu.h
adreno_device_rel=drivers/gpu/drm/msm/adreno/adreno_device.c
a6xx_gpu_rel=drivers/gpu/drm/msm/adreno/a6xx_gpu.c
a6xx_gpu_h_rel=drivers/gpu/drm/msm/adreno/a6xx_gpu.h
a6xx_gmu_rel=drivers/gpu/drm/msm/adreno/a6xx_gmu.c

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
	text=$1
	needle=$2
	label=$3
	stats=$(printf '%s\n' "$text" |
		awk -v needle="$needle" '
			index($0, needle) { count++; line = NR }
			END { print count + 0 ":" line + 0 }
		')
	count=${stats%%:*}
	line=${stats#*:}
	[ "$count" -eq 1 ] ||
		fail "$label count is $count, expected 1"
	printf '%s\n' "$line"
}

for command in awk cp cut git grep mkdir mktemp sed sha256sum; do
	command -v "$command" >/dev/null ||
		fail "missing command: $command"
done

[ -d "$source_dir" ] || fail "missing source directory: $source_dir"
[ -x "$boundary" ] || fail 'missing executable GMU/CX boundary verifier'
[ -f "$patch" ] && [ ! -L "$patch" ] ||
	fail "missing or linked candidate patch: $patch"
[ "$(git -C "$source_dir" rev-parse --is-inside-work-tree)" = true ] ||
	fail 'source is not a Git worktree'
[ "$(git -C "$source_dir" rev-parse HEAD)" = "$expected_commit" ] ||
	fail 'pinned source commit changed'
[ "$(git -C "$source_dir" rev-parse 'HEAD^{tree}')" = "$expected_tree" ] ||
	fail 'pinned source tree changed'
[ -z "$(git -C "$source_dir" status --porcelain)" ] ||
	fail 'pinned source worktree is not clean'

check_hash "$boundary" "$expected_boundary" \
	'GMU/CX runtime-PM boundary verifier'
"$boundary" "$source_dir" >/dev/null
check_hash "$patch12" \
	0d223284805217246efaefa2fc8ad431d94d05e4fa9269f2ef86e3fb29378637 \
	'GMU power-level base patch'
check_hash "$patch13" \
	3413678758f97ea16d8e53e7a24a2bc62a871b333851c32bd8242687bbdc1054 \
	'firmware-request-only base patch'
check_hash "$patch14" \
	6966d868585e11c5f614598368eb70595025c9543653582e0234aa313edfa3f2 \
	'ucode-allocation base patch'
check_hash "$patch15" \
	a179ff9e31792238a3bd254297008d805e6a37b5d08125712c0151b1f39b3051 \
	'GMU resume-entry base patch'

if [ "${ALLOW_UNPINNED_PATCH:-0}" != 1 ]; then
	[ "$patch" = "$accepted_patch" ] ||
		fail 'patch path is not the accepted 0016 diagnostic'
	check_hash "$patch" "$expected_patch" \
		'A660 GMU/CX runtime-PM diagnostic patch'
fi

expected_numstat=$(printf '%s\n' \
	"33	0	$a6xx_gmu_rel" \
	"52	1	$msm_drv_rel" \
	"4	0	$msm_gpu_h_rel")
actual_numstat=$(git -C "$source_dir" apply --numstat "$patch")
[ "$actual_numstat" = "$expected_numstat" ] ||
	fail 'patch does not contain the exact three-file GMU/CX diff'

if git -C "$source_dir" apply --check "$patch" >/dev/null 2>&1; then
	fail '0016 unexpectedly applies without its accepted base patches'
fi
"$source_dir/scripts/checkpatch.pl" --strict --no-tree "$patch" >/dev/null

stage=$(mktemp -d)
trap 'rm -rf "$stage"' EXIT INT TERM
mkdir -p "$stage/drivers/gpu/drm/msm/adreno"
for rel in "$msm_drv_rel" "$msm_gpu_h_rel" "$adreno_device_rel" \
	"$a6xx_gpu_rel" "$a6xx_gpu_h_rel" "$a6xx_gmu_rel"
do
	cp "$source_dir/$rel" "$stage/$rel"
done
(cd "$stage" &&
	git apply --check "$patch12" &&
	git apply "$patch12" &&
	git apply --check "$patch13" &&
	git apply "$patch13" &&
	git apply --check "$patch14" &&
	git apply "$patch14" &&
	git apply --check "$patch15" &&
	git apply "$patch15" &&
	git apply --check "$patch" &&
	git apply "$patch")

patched_msm_drv=$stage/$msm_drv_rel
patched_msm_gpu_h=$stage/$msm_gpu_h_rel
patched_adreno_device=$stage/$adreno_device_rel
patched_a6xx_gpu=$stage/$a6xx_gpu_rel
patched_a6xx_gpu_h=$stage/$a6xx_gpu_h_rel
patched_a6xx_gmu=$stage/$a6xx_gmu_rel
if [ "${ALLOW_UNPINNED_PATCH:-0}" != 1 ]; then
	check_hash "$patched_msm_drv" \
		ec7e4a1820b03b27ba51691a2b6afaa993384a467c68db353fc691adec8b5957 \
		'patched msm_drv.c'
	check_hash "$patched_msm_gpu_h" \
		5fa397c9fd1dade1040074ec3dbbf67258eee3a6f23ef4da30169a40b3d4393a \
		'patched msm_gpu.h'
	check_hash "$patched_a6xx_gmu" \
		cc76b2865877853f5e9d9508f704d242dc35847625ce94aa4fa14f608743c1a4 \
		'patched a6xx_gmu.c'
	check_hash "$patched_adreno_device" \
		2e72b3ce7aa47fad1d5c82d6ab662e6f98895bad15876b631ecafecad0308b45 \
		'unchanged accepted adreno_device.c'
	check_hash "$patched_a6xx_gpu" \
		34ba40a1de4705b471a09266c51a1b5d20f06534faea6bff70d2b0025d185ae7 \
		'unchanged accepted a6xx_gpu.c'
	check_hash "$patched_a6xx_gpu_h" \
		5d6a982bea8fca55959cbc0cdd1b5ba7a6b64e884c8efd619adbba6490319ea5 \
		'unchanged accepted a6xx_gpu.h'
fi

for exact_line in \
	'static bool gmu_cx_runtime_pm_only;' \
	'module_param(gmu_cx_runtime_pm_only, bool, 0400);' \
	'static atomic_t gmu_cx_runtime_pm_only_open_consumed = ATOMIC_INIT(0);' \
	'static atomic_t gmu_cx_runtime_pm_only_state = ATOMIC_INIT(0);'
do
	[ "$(grep -Fxc "$exact_line" "$patched_msm_drv")" -eq 1 ] ||
		fail "GMU/CX declaration is not exact: $exact_line"
done
if grep -Eq 'gmu_cx_runtime_pm_only[[:space:]]*=[[:space:]]*true' \
	"$patched_msm_drv"
then
	fail 'GMU/CX runtime-PM diagnostic is enabled by source assignment'
fi

for declaration in \
	'bool msm_a660_gmu_cx_runtime_pm_only_enabled(void);' \
	'bool msm_a660_gmu_cx_runtime_pm_only_mark_attempt(void);' \
	'bool msm_a660_gmu_cx_runtime_pm_only_mark_passed(void);' \
	'bool msm_a660_gmu_cx_runtime_pm_only_was_passed(void);'
do
	[ "$(grep -Fxc "$declaration" "$patched_msm_gpu_h")" -eq 1 ] ||
		fail "missing exact GMU/CX declaration: $declaration"
done

enabled=$(sed -n \
	'/^bool msm_a660_gmu_cx_runtime_pm_only_enabled(/,/^}/p' \
	"$patched_msm_drv")
mark_attempt=$(sed -n \
	'/^bool msm_a660_gmu_cx_runtime_pm_only_mark_attempt(/,/^}/p' \
	"$patched_msm_drv")
mark_passed=$(sed -n \
	'/^bool msm_a660_gmu_cx_runtime_pm_only_mark_passed(/,/^}/p' \
	"$patched_msm_drv")
was_passed=$(sed -n \
	'/^bool msm_a660_gmu_cx_runtime_pm_only_was_passed(/,/^}/p' \
	"$patched_msm_drv")
msm_open=$(sed -n '/^static int msm_open(/,/^}/p' "$patched_msm_drv")
cx_open=$(printf '%s\n' "$msm_open" |
	sed -n '/if (gmu_cx_runtime_pm_only) {/,/if (ucode_allocation_only) {/p')
rollback=$(sed -n \
	'/^int adreno_rollback_gpu_load_only(/,/^}/p' \
	"$patched_adreno_device")
gmu_resume=$(sed -n '/^int a6xx_gmu_resume(/,/^}/p' \
	"$patched_a6xx_gmu")
cx_resume=$(printf '%s\n' "$gmu_resume" |
	sed -n \
		'/if (msm_a660_gmu_cx_runtime_pm_only_enabled()) {/,/gmu->hung = false;/p')
normal_resume=$(printf '%s\n' "$gmu_resume" |
	sed -n '/gmu->hung = false;/,$p')
for block in "$enabled" "$mark_attempt" "$mark_passed" "$was_passed" \
	"$msm_open" "$cx_open" "$rollback" "$gmu_resume" "$cx_resume" \
	"$normal_resume"
do
	[ -n "$block" ] || fail 'one or more GMU/CX diagnostic blocks are missing'
done

line_once "$enabled" 'return gmu_cx_runtime_pm_only;' \
	'default-off enable query' >/dev/null
line_once "$mark_attempt" \
	'atomic_cmpxchg(&gmu_cx_runtime_pm_only_state, 0, 1) == 0' \
	'atomic unused-to-attempted transition' >/dev/null
line_once "$mark_passed" \
	'atomic_cmpxchg(&gmu_cx_runtime_pm_only_state, 1, 2) == 1' \
	'atomic attempted-to-passed transition' >/dev/null
line_once "$was_passed" \
	'atomic_read(&gmu_cx_runtime_pm_only_state) == 2' \
	'passed-state query' >/dev/null

conflict_first=$(line_once "$msm_open" \
	'firmware_request_only + ucode_allocation_only +' \
	'four-way diagnostic conflict start')
conflict_second=$(line_once "$msm_open" \
	'gmu_resume_entry_only + gmu_cx_runtime_pm_only > 1' \
	'four-way diagnostic conflict end')
full_cx_line=$(line_once "$msm_open" 'if (gmu_cx_runtime_pm_only) {' \
	'GMU/CX open branch position')
cx_branch_line=$(line_once "$cx_open" \
	'if (gmu_cx_runtime_pm_only) {' 'GMU/CX open branch')
consume_line=$(line_once "$cx_open" \
	'atomic_cmpxchg(&gmu_cx_runtime_pm_only_open_consumed, 0, 1)' \
	'atomic GMU/CX open consume')
load_line=$(line_once "$cx_open" 'load_gpu(dev);' \
	'normal lazy-load invocation')
passed_line=$(line_once "$cx_open" \
	'msm_a660_gmu_cx_runtime_pm_only_was_passed()' \
	'passed-state observation')
active_line=$(line_once "$cx_open" 'if (priv->gpu)' \
	'unexpected active GPU rejection')
rollback_line=$(line_once "$cx_open" 'adreno_rollback_gpu_load_only(dev)' \
	'accepted load-state rollback')
check_passed_line=$(line_once "$cx_open" 'if (!passed)' \
	'incomplete-transition rejection')
marker_line=$(line_once "$cx_open" \
	'A660 GMU/CX runtime PM passed and GPU load rolled back; reject open' \
	'complete rollback marker')
open_euclean_line=$(line_once "$cx_open" 'return -EUCLEAN;' \
	'deliberate failed open')
context_line=$(line_once "$msm_open" 'context_init(dev, file)' \
	'unchanged normal context creation')
if [ "$conflict_first" -ge "$conflict_second" ] ||
	[ "$conflict_second" -ge "$full_cx_line" ] ||
	[ "$full_cx_line" -ge "$context_line" ] ||
	[ "$cx_branch_line" -ge "$consume_line" ] ||
	[ "$consume_line" -ge "$load_line" ] ||
	[ "$load_line" -ge "$passed_line" ] ||
	[ "$passed_line" -ge "$active_line" ] ||
	[ "$active_line" -ge "$rollback_line" ] ||
	[ "$rollback_line" -ge "$check_passed_line" ] ||
	[ "$check_passed_line" -ge "$marker_line" ] ||
	[ "$marker_line" -ge "$open_euclean_line" ]
then
	fail 'GMU/CX one-shot/load/state/rollback/failed-open order changed'
fi
line_once "$cx_open" 'return -EALREADY;' \
	'repeated-open rejection' >/dev/null
[ "$(printf '%s\n' "$cx_open" | grep -Fxc '			return -EPROTO;')" \
	-eq 2 ] ||
	fail 'GMU/CX open lacks exact active-GPU and incomplete-state rejects'

for rollback_contract in \
	'adreno_gpu->chip_id != 0x06060001' \
	'pm_runtime_enabled(&pdev->dev)' \
	'a6xx_ucode_unload(gpu);' \
	'adreno_release_diagnostic_fw(adreno_gpu);'
do
	line_once "$rollback" "$rollback_contract" \
		"rollback contract $rollback_contract" >/dev/null
done

initialized_line=$(line_once "$gmu_resume" \
	'if (WARN(!gmu->initialized,' 'GMU initialized guard')
full_diag_line=$(line_once "$gmu_resume" \
	'if (msm_a660_gmu_cx_runtime_pm_only_enabled()) {' \
	'GMU/CX diagnostic branch position')
diag_line=$(line_once "$cx_resume" \
	'if (msm_a660_gmu_cx_runtime_pm_only_enabled()) {' \
	'GMU/CX diagnostic branch')
chip_line=$(line_once "$cx_resume" \
	'adreno_gpu->chip_id != 0x06060001' 'exact A660.1 restriction')
attempt_line=$(line_once "$cx_resume" \
	'msm_a660_gmu_cx_runtime_pm_only_mark_attempt()' \
	'atomic attempt transition')
get_line=$(line_once "$cx_resume" \
	'ret = pm_runtime_get_sync(gmu->dev);' \
	'GMU/CX runtime-PM get')
get_balance_line=$(line_once "$cx_resume" \
	'pm_runtime_put_noidle(gmu->dev);' \
	'failed-get count balance')
consumer_put_line=$(line_once "$cx_resume" \
	'ret = pm_runtime_put_sync_suspend(gmu->dev);' \
	'synchronous GMU consumer rollback')
cx_suspend_line=$(line_once "$cx_resume" \
	'ret = pm_runtime_suspend(gmu->cxpd);' \
	'non-counted synchronous CX suspend')
consumer_state_line=$(line_once "$cx_resume" \
	'!pm_runtime_suspended(gmu->dev)' 'settled GMU state')
cx_state_line=$(line_once "$cx_resume" \
	'!pm_runtime_suspended(gmu->cxpd)' 'settled CX state')
pass_line=$(line_once "$cx_resume" \
	'msm_a660_gmu_cx_runtime_pm_only_mark_passed()' \
	'atomic passed transition')
resume_marker_line=$(line_once "$cx_resume" \
	'A660 GMU/CX runtime PM resumed and synchronously suspended; reject resume' \
	'GMU/CX settled marker')
resume_euclean_line=$(line_once "$cx_resume" 'return -EUCLEAN;' \
	'GMU/CX deliberate resume rejection')
hung_line=$(line_once "$cx_resume" 'gmu->hung = false;' \
	'first normal-path software mutation')
normal_get_line=$(line_once "$normal_resume" \
	'pm_runtime_get_sync(gmu->dev);' 'normal GMU/CX get')
normal_gx_line=$(line_once "$normal_resume" \
	'pm_runtime_get_sync(gmu->gxpd);' 'normal GX get')
if [ "$initialized_line" -ge "$full_diag_line" ] ||
	[ "$diag_line" -ge "$chip_line" ] ||
	[ "$chip_line" -ge "$attempt_line" ] ||
	[ "$attempt_line" -ge "$get_line" ] ||
	[ "$get_line" -ge "$get_balance_line" ] ||
	[ "$get_balance_line" -ge "$consumer_put_line" ] ||
	[ "$consumer_put_line" -ge "$cx_suspend_line" ] ||
	[ "$cx_suspend_line" -ge "$consumer_state_line" ] ||
	[ "$consumer_state_line" -ge "$cx_state_line" ] ||
	[ "$cx_state_line" -ge "$pass_line" ] ||
	[ "$pass_line" -ge "$resume_marker_line" ] ||
	[ "$resume_marker_line" -ge "$resume_euclean_line" ] ||
	[ "$resume_euclean_line" -ge "$hung_line" ] ||
	[ "$normal_get_line" -ge "$normal_gx_line" ]
then
	fail 'GMU/CX attempt/get/rollback/state/pass boundary order changed'
fi

get_error=$(printf '%s\n' "$cx_resume" |
	sed -n \
		'/ret = pm_runtime_get_sync(gmu->dev);/,/ret = pm_runtime_put_sync_suspend(gmu->dev);/p')
for get_contract in \
	'if (ret < 0) {' \
	'pm_runtime_put_noidle(gmu->dev);' \
	'return ret;'
do
	line_once "$get_error" "$get_contract" \
		"failed-get contract $get_contract" >/dev/null
done

[ "$(printf '%s\n' "$cx_resume" | grep -Fc 'pm_runtime_')" -eq 6 ] ||
	fail 'GMU/CX branch does not contain the exact six runtime-PM calls/checks'
for forbidden in \
	'pm_runtime_get_sync(gmu->gxpd)' \
	'pm_runtime_put(gmu->gxpd)' \
	'gmu->hung = true' \
	'clk_set_rate' \
	'clk_bulk_prepare_enable' \
	'a6xx_gmu_secure_init' \
	'a6xx_gmu_set_initial_bw' \
	'gmu_write' \
	'gpu_write' \
	'enable_irq' \
	'a6xx_gmu_fw_start' \
	'a6xx_hfi_start' \
	'adreno_zap_shader_load' \
	'qcom_scm'
do
	if printf '%s\n' "$cx_resume" | grep -Fq "$forbidden"; then
		fail "GMU/CX branch reaches forbidden operation: $forbidden"
	fi
done

echo 'PASS A660 GMU/CX runtime-PM patch is default-off, exact-chip, atomic-stateful, get-error-balanced, synchronously rolled back, settled, failed-open, CX-only, and pre-GX'
