#!/bin/sh
set -eu

patch=${1:?usage: verify-a660-gmu-clock-preparation-patch.sh PATCH PINNED_SOURCE}
source_dir=${2:?missing pinned source}
repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)
accepted_patch=$repo/patches/linux-7.1.4/0017-drm-msm-add-a660-gmu-clock-preparation-diagnostic.patch
patch12=$repo/patches/linux-7.1.4/0012-drm-msm-a6xx-propagate-gmu-pwrlevels-error.patch
patch13=$repo/patches/linux-7.1.4/0013-drm-msm-add-a660-firmware-request-only-diagnostic.patch
patch14=$repo/patches/linux-7.1.4/0014-drm-msm-add-a660-ucode-allocation-diagnostic.patch
patch15=$repo/patches/linux-7.1.4/0015-drm-msm-add-a660-gmu-resume-entry-diagnostic.patch
patch16=$repo/patches/linux-7.1.4/0016-drm-msm-add-a660-gmu-cx-runtime-pm-diagnostic.patch
boundary=$repo/scripts/device/verify-a660-gmu-clock-preparation-boundary.sh
v10_verifier=$repo/scripts/device/verify-a660-gmu-cx-runtime-pm-patch.sh

expected_commit=d9ac316489f4258d389d6298659d5e9c22183400
expected_tree=c796deb1cc54e942f8bb46a2c76a7199e19e5c92
expected_boundary=844c7cdc1ab21078ff345474e9cbea2e8bbeb8606d55211df3ca7a62a9e5a4c8
expected_v10_verifier=7fff8e1c43d1230bd4a16fa9a31d472ce2c89dad50b3ccda940638bb1ab7e548
expected_patch=e7512f8e0589187bddb93f53d83a31b415ce779b3093623fad5515210cf1258b

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

require_count() {
	text=$1
	needle=$2
	expected=$3
	label=$4
	actual=$(printf '%s\n' "$text" | grep -Fc "$needle" || true)
	[ "$actual" -eq "$expected" ] ||
		fail "$label count is $actual, expected $expected"
}

for command in awk cp cut git grep mkdir mktemp sed sha256sum; do
	command -v "$command" >/dev/null ||
		fail "missing command: $command"
done

[ -d "$source_dir" ] || fail "missing source directory: $source_dir"
[ -x "$boundary" ] || fail 'missing executable clock-preparation boundary verifier'
[ -x "$v10_verifier" ] || fail 'missing executable v10 patch verifier'
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
	'GMU clock-preparation boundary verifier'
"$boundary" "$source_dir" >/dev/null
check_hash "$v10_verifier" "$expected_v10_verifier" \
	'GMU/CX runtime-PM v10 patch verifier'
SKIP_V9_UMBRELLA_RUN=1 "$v10_verifier" "$patch16" "$source_dir" >/dev/null
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
check_hash "$patch16" \
	5eef04eb711443acaaf4295e926577f90073b8ab62414cff3d18de2272d3a152 \
	'GMU/CX runtime-PM v10 base patch'

if [ "${ALLOW_UNPINNED_PATCH:-0}" != 1 ]; then
	[ "$patch" = "$accepted_patch" ] ||
		fail 'patch path is not the accepted 0017 diagnostic'
	check_hash "$patch" "$expected_patch" \
		'A660 GMU clock-preparation diagnostic patch'
fi

expected_numstat=$(printf '%s\n' \
	"126	0	$a6xx_gmu_rel" \
	"53	1	$msm_drv_rel" \
	"4	0	$msm_gpu_h_rel")
actual_numstat=$(git -C "$source_dir" apply --numstat "$patch")
[ "$actual_numstat" = "$expected_numstat" ] ||
	fail 'patch does not contain the exact three-file clock-preparation diff'

if git -C "$source_dir" apply --check "$patch" >/dev/null 2>&1; then
	fail '0017 unexpectedly applies without its accepted base patches'
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
	git apply --check "$patch16" &&
	git apply "$patch16" &&
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
		44b9d1281819a3812711786d488fac8ac727dc24f079c6d0e886ee2cb5a60c14 \
		'patched msm_drv.c'
	check_hash "$patched_msm_gpu_h" \
		9065053f0ed68a0a200270aa42548cb021e6e26c035dcb0c4ce53341d3c0bfca \
		'patched msm_gpu.h'
	check_hash "$patched_a6xx_gmu" \
		176391492beacf6b08a0e5d9f45bec7147809779da3a1a2f511cccaebf548c17 \
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
	'static bool gmu_clock_preparation_only;' \
	'module_param(gmu_clock_preparation_only, bool, 0400);' \
	'static atomic_t gmu_clock_preparation_only_open_consumed = ATOMIC_INIT(0);' \
	'static atomic_t gmu_clock_preparation_only_state = ATOMIC_INIT(0);'
do
	[ "$(grep -Fxc "$exact_line" "$patched_msm_drv")" -eq 1 ] ||
		fail "clock-preparation declaration is not exact: $exact_line"
done
if grep -Eq 'gmu_clock_preparation_only[[:space:]]*=[[:space:]]*true' \
	"$patched_msm_drv"
then
	fail 'clock-preparation diagnostic is enabled by source assignment'
fi

for declaration in \
	'bool msm_a660_gmu_clock_preparation_only_enabled(void);' \
	'bool msm_a660_gmu_clock_preparation_only_mark_attempt(void);' \
	'bool msm_a660_gmu_clock_preparation_only_mark_passed(void);' \
	'bool msm_a660_gmu_clock_preparation_only_was_passed(void);'
do
	[ "$(grep -Fxc "$declaration" "$patched_msm_gpu_h")" -eq 1 ] ||
		fail "missing exact clock-preparation declaration: $declaration"
done

enabled=$(sed -n \
	'/^bool msm_a660_gmu_clock_preparation_only_enabled(/,/^}/p' \
	"$patched_msm_drv")
mark_attempt=$(sed -n \
	'/^bool msm_a660_gmu_clock_preparation_only_mark_attempt(/,/^}/p' \
	"$patched_msm_drv")
mark_passed=$(sed -n \
	'/^bool msm_a660_gmu_clock_preparation_only_mark_passed(/,/^}/p' \
	"$patched_msm_drv")
was_passed=$(sed -n \
	'/^bool msm_a660_gmu_clock_preparation_only_was_passed(/,/^}/p' \
	"$patched_msm_drv")
msm_open=$(sed -n '/^static int msm_open(/,/^}/p' "$patched_msm_drv")
clock_open=$(printf '%s\n' "$msm_open" |
	sed -n \
		'/if (gmu_clock_preparation_only) {/,/if (ucode_allocation_only) {/p')
helper=$(sed -n \
	'/^static int a6xx_gmu_clock_preparation_only(/,/^}/p' \
	"$patched_a6xx_gmu")
gmu_resume=$(sed -n '/^int a6xx_gmu_resume(/,/^}/p' \
	"$patched_a6xx_gmu")

for block in "$enabled" "$mark_attempt" "$mark_passed" "$was_passed" \
	"$msm_open" "$clock_open" "$helper" "$gmu_resume"
do
	[ -n "$block" ] ||
		fail 'one or more clock-preparation diagnostic blocks are missing'
done

line_once "$enabled" 'return gmu_clock_preparation_only;' \
	'default-off enable query' >/dev/null
line_once "$mark_attempt" \
	'atomic_cmpxchg(&gmu_clock_preparation_only_state, 0, 1) == 0' \
	'atomic unused-to-attempted transition' >/dev/null
line_once "$mark_passed" \
	'atomic_cmpxchg(&gmu_clock_preparation_only_state, 1, 2) == 1' \
	'atomic attempted-to-passed transition' >/dev/null
line_once "$was_passed" \
	'atomic_read(&gmu_clock_preparation_only_state) == 2' \
	'passed-state query' >/dev/null

conflict_first=$(line_once "$msm_open" \
	'firmware_request_only + ucode_allocation_only +' \
	'five-way diagnostic conflict start')
conflict_second=$(line_once "$msm_open" \
	'gmu_resume_entry_only + gmu_cx_runtime_pm_only +' \
	'five-way diagnostic conflict middle')
conflict_third=$(line_once "$msm_open" \
	'gmu_clock_preparation_only > 1' \
	'five-way diagnostic conflict end')
full_clock_line=$(line_once "$msm_open" \
	'if (gmu_clock_preparation_only) {' \
	'clock-preparation open branch position')
context_line=$(line_once "$msm_open" 'context_init(dev, file)' \
	'unchanged normal context creation')
if [ "$conflict_first" -ge "$conflict_second" ] ||
	[ "$conflict_second" -ge "$conflict_third" ] ||
	[ "$conflict_third" -ge "$full_clock_line" ] ||
	[ "$full_clock_line" -ge "$context_line" ]
then
	fail 'clock-preparation conflict/open boundary order changed'
fi

consume_line=$(line_once "$clock_open" \
	'atomic_cmpxchg(&gmu_clock_preparation_only_open_consumed,' \
	'atomic clock-preparation open consume')
load_line=$(line_once "$clock_open" 'load_gpu(dev);' \
	'normal lazy-load invocation')
passed_line=$(line_once "$clock_open" \
	'msm_a660_gmu_clock_preparation_only_was_passed()' \
	'passed-state observation')
active_line=$(line_once "$clock_open" 'if (priv->gpu)' \
	'unexpected active GPU rejection')
rollback_line=$(line_once "$clock_open" \
	'adreno_rollback_gpu_load_only(dev)' 'GPU-load rollback')
check_passed_line=$(line_once "$clock_open" 'if (!passed)' \
	'incomplete-transition rejection')
marker_line=$(line_once "$clock_open" \
	'A660 GMU clock preparation passed and GPU load rolled back; reject open' \
	'complete rollback marker')
open_euclean_line=$(line_once "$clock_open" 'return -EUCLEAN;' \
	'deliberate failed open')
if [ "$consume_line" -ge "$load_line" ] ||
	[ "$load_line" -ge "$passed_line" ] ||
	[ "$passed_line" -ge "$active_line" ] ||
	[ "$active_line" -ge "$rollback_line" ] ||
	[ "$rollback_line" -ge "$check_passed_line" ] ||
	[ "$check_passed_line" -ge "$marker_line" ] ||
	[ "$marker_line" -ge "$open_euclean_line" ]
then
	fail 'clock-preparation one-shot/load/state/rollback/open order changed'
fi
line_once "$clock_open" 'return -EALREADY;' \
	'repeated-open rejection' >/dev/null
require_count "$clock_open" 'return -EPROTO;' 2 \
	'clock-preparation active/incomplete rejection'

for exact in \
	'adreno_gpu->chip_id != 0x06060001' \
	'gmu->nr_clocks != 7' \
	'IS_ERR_OR_NULL(gmu->core_clk)' \
	'IS_ERR_OR_NULL(gmu->hub_clk)' \
	'IS_ERR_OR_NULL(gmu->cxpd)' \
	'IS_ERR_OR_NULL(gmu->gxpd)'
do
	line_once "$helper" "$exact" "precondition $exact" >/dev/null
done

require_count "$helper" 'pm_runtime_suspended(gmu->dev)' 2 \
	'GMU suspended checks'
require_count "$helper" 'pm_runtime_suspended(gmu->cxpd)' 2 \
	'CX suspended checks'
require_count "$helper" 'pm_runtime_suspended(gmu->gxpd)' 2 \
	'GX suspended checks'
require_count "$helper" 'pm_runtime_get_sync(gmu->dev)' 1 \
	'GMU/CX runtime-PM get'
require_count "$helper" 'pm_runtime_put_noidle(gmu->dev)' 1 \
	'failed GMU/CX get balance'
require_count "$helper" 'pm_runtime_get_sync(gmu->gxpd)' 1 \
	'GX runtime-PM get'
require_count "$helper" 'pm_runtime_put_noidle(gmu->gxpd)' 1 \
	'failed GX get balance'
require_count "$helper" 'clk_get_rate(gmu->core_clk)' 3 \
	'core-rate capture/verification'
require_count "$helper" 'clk_get_rate(gmu->hub_clk)' 3 \
	'hub-rate capture/verification'
require_count "$helper" \
	'clk_set_rate(gmu->core_clk, 200000000)' 1 \
	'core-rate programming'
require_count "$helper" \
	'clk_set_rate(gmu->hub_clk, 150000000)' 1 \
	'hub-rate programming'
require_count "$helper" 'clk_set_rate(gmu->core_clk, core_rate)' 1 \
	'core-rate restoration'
require_count "$helper" 'clk_set_rate(gmu->hub_clk, hub_rate)' 1 \
	'hub-rate restoration'
require_count "$helper" \
	'clk_bulk_prepare_enable(gmu->nr_clocks, gmu->clocks)' 1 \
	'seven-clock bulk prepare/enable'
require_count "$helper" \
	'clk_bulk_disable_unprepare(gmu->nr_clocks, gmu->clocks)' 1 \
	'seven-clock bulk disable/unprepare'
require_count "$helper" 'pm_runtime_put_sync_suspend(gmu->gxpd)' 1 \
	'synchronous GX rollback'
require_count "$helper" 'pm_runtime_put_sync_suspend(gmu->dev)' 1 \
	'synchronous GMU/CX rollback'
require_count "$helper" 'pm_runtime_suspend(gmu->cxpd)' 1 \
	'synchronous linked-CX settle'

attempt_line=$(line_once "$helper" \
	'msm_a660_gmu_clock_preparation_only_mark_attempt()' \
	'atomic attempt transition')
gmu_get_line=$(line_once "$helper" \
	'ret = pm_runtime_get_sync(gmu->dev);' 'GMU/CX get')
gx_get_line=$(line_once "$helper" \
	'ret = pm_runtime_get_sync(gmu->gxpd);' 'GX get')
capture_line=$(line_once "$helper" \
	'core_rate = clk_get_rate(gmu->core_clk);' 'rate capture')
core_set_line=$(line_once "$helper" \
	'ret = clk_set_rate(gmu->core_clk, 200000000);' 'core-rate set')
hub_set_line=$(line_once "$helper" \
	'ret = clk_set_rate(gmu->hub_clk, 150000000);' 'hub-rate set')
bulk_line=$(line_once "$helper" \
	'ret = clk_bulk_prepare_enable(gmu->nr_clocks, gmu->clocks);' \
	'clock enable')
out_line=$(line_once "$helper" 'out:' 'single cleanup target')
disable_line=$(line_once "$helper" \
	'clk_bulk_disable_unprepare(gmu->nr_clocks, gmu->clocks);' \
	'clock disable')
hub_restore_line=$(line_once "$helper" \
	'cleanup_ret = clk_set_rate(gmu->hub_clk, hub_rate);' \
	'hub-rate restore')
core_restore_line=$(line_once "$helper" \
	'cleanup_ret = clk_set_rate(gmu->core_clk, core_rate);' \
	'core-rate restore')
gx_put_line=$(line_once "$helper" \
	'cleanup_ret = pm_runtime_put_sync_suspend(gmu->gxpd);' \
	'GX rollback')
gmu_put_line=$(line_once "$helper" \
	'cleanup_ret = pm_runtime_put_sync_suspend(gmu->dev);' \
	'GMU/CX rollback')
cx_suspend_line=$(line_once "$helper" \
	'cleanup_ret = pm_runtime_suspend(gmu->cxpd);' \
	'CX settle')
pass_line=$(line_once "$helper" \
	'msm_a660_gmu_clock_preparation_only_mark_passed()' \
	'atomic pass transition')
euclean_line=$(line_once "$helper" 'return -EUCLEAN;' \
	'deliberate resume rejection')
if [ "$attempt_line" -ge "$gmu_get_line" ] ||
	[ "$gmu_get_line" -ge "$gx_get_line" ] ||
	[ "$gx_get_line" -ge "$capture_line" ] ||
	[ "$capture_line" -ge "$core_set_line" ] ||
	[ "$core_set_line" -ge "$hub_set_line" ] ||
	[ "$hub_set_line" -ge "$bulk_line" ] ||
	[ "$bulk_line" -ge "$out_line" ] ||
	[ "$out_line" -ge "$disable_line" ] ||
	[ "$disable_line" -ge "$hub_restore_line" ] ||
	[ "$hub_restore_line" -ge "$core_restore_line" ] ||
	[ "$core_restore_line" -ge "$gx_put_line" ] ||
	[ "$gx_put_line" -ge "$gmu_put_line" ] ||
	[ "$gmu_put_line" -ge "$cx_suspend_line" ] ||
	[ "$cx_suspend_line" -ge "$pass_line" ] ||
	[ "$pass_line" -ge "$euclean_line" ]
then
	fail 'clock-preparation acquire/enable/reverse-rollback order changed'
fi

resume_diag_line=$(line_once "$gmu_resume" \
	'msm_a660_gmu_clock_preparation_only_enabled()' \
	'clock-preparation resume branch')
hung_line=$(line_once "$gmu_resume" 'gmu->hung = false;' \
	'first normal-path software mutation')
[ "$resume_diag_line" -lt "$hung_line" ] ||
	fail 'clock-preparation branch no longer stops before normal GMU mutation'

for forbidden in \
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
	if printf '%s\n' "$helper" | grep -Fq "$forbidden"; then
		fail "clock-preparation helper reaches forbidden operation: $forbidden"
	fi
done

echo 'PASS A660 GMU clock-preparation patch is default-off, exact-chip, atomic-stateful, seven-clock, rate-restoring, synchronously rolled back, settled, failed-open, and pre-secure'
