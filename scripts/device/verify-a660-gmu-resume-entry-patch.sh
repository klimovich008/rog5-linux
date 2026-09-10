#!/bin/sh
set -eu

patch=${1:?usage: verify-a660-gmu-resume-entry-patch.sh PATCH PINNED_SOURCE}
source_dir=${2:?missing pinned source}
repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)
accepted_patch=$repo/patches/linux-7.1.4/0015-drm-msm-add-a660-gmu-resume-entry-diagnostic.patch
patch12=$repo/patches/linux-7.1.4/0012-drm-msm-a6xx-propagate-gmu-pwrlevels-error.patch
patch13=$repo/patches/linux-7.1.4/0013-drm-msm-add-a660-firmware-request-only-diagnostic.patch
patch14=$repo/patches/linux-7.1.4/0014-drm-msm-add-a660-ucode-allocation-diagnostic.patch
boundary=$repo/scripts/device/verify-a660-gmu-resume-entry-boundary.sh

expected_commit=d9ac316489f4258d389d6298659d5e9c22183400
expected_tree=c796deb1cc54e942f8bb46a2c76a7199e19e5c92
expected_patch=a179ff9e31792238a3bd254297008d805e6a37b5d08125712c0151b1f39b3051

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
[ -x "$boundary" ] || fail 'missing executable resume-entry boundary verifier'
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

if [ "${ALLOW_UNPINNED_PATCH:-0}" != 1 ]; then
	[ "$patch" = "$accepted_patch" ] ||
		fail 'patch path is not the accepted 0015 diagnostic'
	check_hash "$patch" "$expected_patch" \
		'A660 GMU resume-entry diagnostic patch'
fi

expected_numstat=$(printf '%s\n' \
	"12	0	$a6xx_gmu_rel" \
	"27	0	$adreno_device_rel" \
	"48	1	$msm_drv_rel" \
	"4	0	$msm_gpu_h_rel")
actual_numstat=$(git -C "$source_dir" apply --numstat "$patch")
[ "$actual_numstat" = "$expected_numstat" ] ||
	fail 'patch does not contain the exact four-file resume-entry diff'

if git -C "$source_dir" apply --check "$patch" >/dev/null 2>&1; then
	fail '0015 unexpectedly applies without its accepted base patches'
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
	git apply --check "$patch" &&
	git apply "$patch")

patched_msm_drv=$stage/$msm_drv_rel
patched_msm_gpu_h=$stage/$msm_gpu_h_rel
patched_adreno_device=$stage/$adreno_device_rel
patched_a6xx_gmu=$stage/$a6xx_gmu_rel
if [ "${ALLOW_UNPINNED_PATCH:-0}" != 1 ]; then
	check_hash "$patched_msm_drv" \
		43e97deb263e5f845b95249612433ca183d4fd7f55be75e23be93b2a0bc83d26 \
		'patched msm_drv.c'
	check_hash "$patched_msm_gpu_h" \
		32dd6be7c82e25cb44377717ffb97cd941a99269c6bf977a2eb49454c0d3cfb4 \
		'patched msm_gpu.h'
	check_hash "$patched_adreno_device" \
		2e72b3ce7aa47fad1d5c82d6ab662e6f98895bad15876b631ecafecad0308b45 \
		'patched adreno_device.c'
	check_hash "$patched_a6xx_gmu" \
		e42eb79a417a6eace46358f5e2666b87dd4138eb8e1af843789b2e99b84fd395 \
		'patched a6xx_gmu.c'
fi

for exact_line in \
	'static bool gmu_resume_entry_only;' \
	'module_param(gmu_resume_entry_only, bool, 0400);' \
	'static atomic_t gmu_resume_entry_only_open_consumed = ATOMIC_INIT(0);' \
	'static atomic_t gmu_resume_entry_only_hit = ATOMIC_INIT(0);'
do
	[ "$(grep -Fxc "$exact_line" "$patched_msm_drv")" -eq 1 ] ||
		fail "resume-entry declaration is not exact: $exact_line"
done
if grep -Eq 'gmu_resume_entry_only[[:space:]]*=[[:space:]]*true' \
	"$patched_msm_drv"
then
	fail 'resume-entry diagnostic is enabled by source assignment'
fi

for declaration in \
	'bool msm_a660_gmu_resume_entry_only_enabled(void);' \
	'bool msm_a660_gmu_resume_entry_only_mark_hit(void);' \
	'bool msm_a660_gmu_resume_entry_only_was_hit(void);' \
	'int adreno_rollback_gpu_load_only(struct drm_device *dev);'
do
	[ "$(grep -Fxc "$declaration" "$patched_msm_gpu_h")" -eq 1 ] ||
		fail "missing exact diagnostic declaration: $declaration"
done

enabled=$(sed -n \
	'/^bool msm_a660_gmu_resume_entry_only_enabled(/,/^}/p' \
	"$patched_msm_drv")
mark_hit=$(sed -n \
	'/^bool msm_a660_gmu_resume_entry_only_mark_hit(/,/^}/p' \
	"$patched_msm_drv")
was_hit=$(sed -n \
	'/^bool msm_a660_gmu_resume_entry_only_was_hit(/,/^}/p' \
	"$patched_msm_drv")
msm_open=$(sed -n '/^static int msm_open(/,/^}/p' "$patched_msm_drv")
entry_open=$(printf '%s\n' "$msm_open" |
	sed -n '/if (gmu_resume_entry_only) {/,/if (ucode_allocation_only) {/p')
rollback=$(sed -n \
	'/^int adreno_rollback_gpu_load_only(/,/^}/p' \
	"$patched_adreno_device")
gmu_resume=$(sed -n '/^int a6xx_gmu_resume(/,/^}/p' \
	"$patched_a6xx_gmu")
for block in "$enabled" "$mark_hit" "$was_hit" "$msm_open" "$entry_open" \
	"$rollback" "$gmu_resume"
do
	[ -n "$block" ] || fail 'one or more diagnostic blocks are missing'
done

line_once "$enabled" 'return gmu_resume_entry_only;' \
	'default-off enable query' >/dev/null
line_once "$mark_hit" \
	'atomic_cmpxchg(&gmu_resume_entry_only_hit, 0, 1) == 0' \
	'atomic resume-entry hit' >/dev/null
line_once "$was_hit" 'atomic_read(&gmu_resume_entry_only_hit) != 0' \
	'resume-entry hit query' >/dev/null

conflict_line=$(line_once "$msm_open" \
	'firmware_request_only + ucode_allocation_only +' \
	'three-way diagnostic conflict')
full_entry_line=$(line_once "$msm_open" \
	'if (gmu_resume_entry_only) {' 'resume-entry open branch position')
entry_branch_line=$(line_once "$entry_open" \
	'if (gmu_resume_entry_only) {' 'resume-entry open branch')
consume_line=$(line_once "$entry_open" \
	'atomic_cmpxchg(&gmu_resume_entry_only_open_consumed, 0, 1)' \
	'atomic open consume')
load_line=$(line_once "$entry_open" 'load_gpu(dev);' \
	'normal lazy-load invocation')
hit_line=$(line_once "$entry_open" \
	'msm_a660_gmu_resume_entry_only_was_hit()' 'entry-hit observation')
rollback_line=$(line_once "$entry_open" \
	'adreno_rollback_gpu_load_only(dev)' 'load-state rollback')
marker_line=$(line_once "$entry_open" \
	'A660 GMU resume entry passed and rolled back; reject open' \
	'rollback marker')
euclean_line=$(line_once "$entry_open" 'return -EUCLEAN;' \
	'deliberate failed open')
context_line=$(line_once "$msm_open" 'context_init(dev, file)' \
	'unchanged normal context creation')
if [ "$conflict_line" -ge "$full_entry_line" ] ||
	[ "$full_entry_line" -ge "$context_line" ] ||
	[ "$entry_branch_line" -ge "$consume_line" ] ||
	[ "$consume_line" -ge "$load_line" ] ||
	[ "$load_line" -ge "$hit_line" ] ||
	[ "$hit_line" -ge "$rollback_line" ] ||
	[ "$rollback_line" -ge "$marker_line" ] ||
	[ "$marker_line" -ge "$euclean_line" ]
then
	fail 'resume-entry one-shot/load/rollback/failed-open order changed'
fi

for open_contract in \
	'return -EALREADY;' \
	'if (priv->gpu)' \
	'if (ret)' \
	'return ret;'
do
	line_once "$entry_open" "$open_contract" \
		"open contract $open_contract" >/dev/null
done
[ "$(printf '%s\n' "$entry_open" | grep -Fxc '			return -EPROTO;')" \
	-eq 2 ] ||
	fail 'resume-entry open does not have exact active-GPU and missed-hit EPROTO rejects'

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
	'if (WARN(!gmu->initialized,' \
	'GMU initialized guard')
diag_line=$(line_once "$gmu_resume" \
	'if (msm_a660_gmu_resume_entry_only_enabled()) {' \
	'resume-entry stop')
chip_line=$(line_once "$gmu_resume" \
	'adreno_gpu->chip_id != 0x06060001' 'exact A660.1 stop')
mark_line=$(line_once "$gmu_resume" \
	'msm_a660_gmu_resume_entry_only_mark_hit()' 'atomic stop hit')
resume_marker_line=$(line_once "$gmu_resume" \
	'A660 GMU resume entry reached before resource activation; reject resume' \
	'resume-entry marker')
resume_euclean_line=$(line_once "$gmu_resume" 'return -EUCLEAN;' \
	'resume rejection')
hung_line=$(line_once "$gmu_resume" 'gmu->hung = false;' \
	'first normal-path mutation')
inner_pm_line=$(line_once "$gmu_resume" \
	'pm_runtime_get_sync(gmu->dev);' 'first inner runtime-PM operation')
if [ "$initialized_line" -ge "$diag_line" ] ||
	[ "$diag_line" -ge "$chip_line" ] ||
	[ "$chip_line" -ge "$mark_line" ] ||
	[ "$mark_line" -ge "$resume_marker_line" ] ||
	[ "$resume_marker_line" -ge "$resume_euclean_line" ] ||
	[ "$resume_euclean_line" -ge "$hung_line" ] ||
	[ "$hung_line" -ge "$inner_pm_line" ]
then
	fail 'resume-entry stop is not before all GMU mutation and power'
fi

entry_stop=$(printf '%s\n' "$gmu_resume" |
	sed -n '/if (msm_a660_gmu_resume_entry_only_enabled()) {/,/gmu->hung = false;/p')
for forbidden in \
	'pm_runtime_get_sync' \
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
	if printf '%s\n' "$entry_stop" | grep -Fq "$forbidden"; then
		fail "resume-entry stop reaches forbidden operation: $forbidden"
	fi
done

echo 'PASS A660 GMU resume-entry patch is default-off, exact-chip, atomic-one-shot, rollback-complete, failed-open, and before all GMU resource activation'
