#!/bin/sh
set -eu

patch=${1:?usage: verify-a660-ucode-allocation-patch.sh PATCH PINNED_SOURCE}
source_dir=${2:?missing pinned source}
repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)
base_patch=$repo/patches/linux-7.1.4/0013-drm-msm-add-a660-firmware-request-only-diagnostic.patch
accepted_patch=$repo/patches/linux-7.1.4/0014-drm-msm-add-a660-ucode-allocation-diagnostic.patch
base_verifier=$repo/scripts/device/verify-a660-firmware-request-only-patch.sh

expected_commit=d9ac316489f4258d389d6298659d5e9c22183400
expected_tree=c796deb1cc54e942f8bb46a2c76a7199e19e5c92
expected_base_patch=3413678758f97ea16d8e53e7a24a2bc62a871b333851c32bd8242687bbdc1054
expected_patch=6966d868585e11c5f614598368eb70595025c9543653582e0234aa313edfa3f2

msm_drv_rel=drivers/gpu/drm/msm/msm_drv.c
msm_gpu_rel=drivers/gpu/drm/msm/msm_gpu.h
adreno_device_rel=drivers/gpu/drm/msm/adreno/adreno_device.c
a6xx_gpu_rel=drivers/gpu/drm/msm/adreno/a6xx_gpu.c
a6xx_gpu_h_rel=drivers/gpu/drm/msm/adreno/a6xx_gpu.h

fail() {
	echo "FAIL $*" >&2
	exit 1
}

check_hash() {
	file=$1
	expected=$2
	label=$3
	if [ ! -f "$file" ] || [ -L "$file" ] || [ ! -r "$file" ]; then
		fail "$label is missing, linked, or unreadable: $file"
	fi
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
[ -x "$base_verifier" ] ||
	fail "missing executable base-patch verifier: $base_verifier"
if [ ! -f "$patch" ] || [ -L "$patch" ]; then
	fail "missing or linked patch: $patch"
fi
[ "$(git -C "$source_dir" rev-parse --is-inside-work-tree)" = true ] ||
	fail 'source is not a Git worktree'
[ "$(git -C "$source_dir" rev-parse HEAD)" = "$expected_commit" ] ||
	fail 'pinned source commit changed'
[ "$(git -C "$source_dir" rev-parse 'HEAD^{tree}')" = "$expected_tree" ] ||
	fail 'pinned source tree changed'
[ -z "$(git -C "$source_dir" status --porcelain)" ] ||
	fail 'pinned source worktree is not clean'

check_hash "$base_patch" "$expected_base_patch" \
	'A660 firmware-request-only base patch'
"$base_verifier" "$base_patch" "$source_dir" >/dev/null

check_hash "$source_dir/$msm_drv_rel" \
	7f928abf51301516c63c834946e3b264b53416c016f4800729c2a9b1025f9c1e \
	'pinned msm_drv.c'
check_hash "$source_dir/$msm_gpu_rel" \
	b477ecc7f2396b4b65cb28eda9f454c885368277b421e5a11a2209ea4b317b2d \
	'pinned msm_gpu.h'
check_hash "$source_dir/$adreno_device_rel" \
	e7d3de968a744c61394e708cfc416a1aead514c09e71e2a68342260000479599 \
	'pinned adreno_device.c'
check_hash "$source_dir/$a6xx_gpu_rel" \
	29733589c6375930852cb26cfee674f83008084e6bdb792fd86164ea487bf85d \
	'pinned a6xx_gpu.c'
check_hash "$source_dir/$a6xx_gpu_h_rel" \
	fefca6579b234fda7c0afdcf07d5c2dbb80aade92674c45380c661e259d9f9bb \
	'pinned a6xx_gpu.h'

if [ "${ALLOW_UNPINNED_PATCH:-0}" != 1 ]; then
	[ "$patch" = "$accepted_patch" ] ||
		fail 'patch path is not the accepted 0014 diagnostic'
	check_hash "$patch" "$expected_patch" \
		'A660 ucode-allocation diagnostic patch'
fi

expected_numstat=$(printf '%s\n' \
	"32	14	$a6xx_gpu_rel" \
	"1	0	$a6xx_gpu_h_rel" \
	"71	0	$adreno_device_rel" \
	"26	0	$msm_drv_rel" \
	"1	0	$msm_gpu_rel")
actual_numstat=$(git -C "$source_dir" apply --numstat "$patch")
[ "$actual_numstat" = "$expected_numstat" ] ||
	fail 'patch does not contain the exact five-file rollback diff'

if git -C "$source_dir" apply --check "$patch" >/dev/null 2>&1; then
	fail '0014 unexpectedly applies without the accepted 0013 base patch'
fi
"$source_dir/scripts/checkpatch.pl" --strict --no-tree "$patch" >/dev/null

for symbol in ucode_allocation_only adreno_load_ucode_only \
	a6xx_ucode_unload
do
	if grep -R -Fq "$symbol" "$source_dir/drivers/gpu/drm/msm"; then
		fail "pinned source unexpectedly contains diagnostic symbol: $symbol"
	fi
done

stage=$(mktemp -d)
trap 'rm -rf "$stage"' EXIT INT TERM
mkdir -p "$stage/drivers/gpu/drm/msm/adreno"
for rel in "$msm_drv_rel" "$msm_gpu_rel" "$adreno_device_rel" \
	"$a6xx_gpu_rel" "$a6xx_gpu_h_rel"
do
	cp "$source_dir/$rel" "$stage/$rel"
done
(cd "$stage" &&
	git apply --check "$base_patch" &&
	git apply "$base_patch" &&
	git apply --check "$patch" &&
	git apply "$patch")

patched_msm_drv=$stage/$msm_drv_rel
patched_msm_gpu=$stage/$msm_gpu_rel
patched_adreno_device=$stage/$adreno_device_rel
patched_a6xx_gpu=$stage/$a6xx_gpu_rel
patched_a6xx_gpu_h=$stage/$a6xx_gpu_h_rel
if [ "${ALLOW_UNPINNED_PATCH:-0}" != 1 ]; then
	check_hash "$patched_msm_drv" \
		bf109068950c2e04d6121a5aea8bee7c20d7c3535a05107728e197351fc6e3c6 \
		'patched msm_drv.c'
	check_hash "$patched_msm_gpu" \
		d3312f908da1702a4f0e63b3e9aed9f77ed7fe352381c2e31647b8225e2993ec \
		'patched msm_gpu.h'
	check_hash "$patched_adreno_device" \
		0954e9cc45a948c02dbecca34d41f1343f004880a983403baa668b3c96a095c2 \
		'patched adreno_device.c'
	check_hash "$patched_a6xx_gpu" \
		34ba40a1de4705b471a09266c51a1b5d20f06534faea6bff70d2b0025d185ae7 \
		'patched a6xx_gpu.c'
	check_hash "$patched_a6xx_gpu_h" \
		5d6a982bea8fca55959cbc0cdd1b5ba7a6b64e884c8efd619adbba6490319ea5 \
		'patched a6xx_gpu.h'
fi

for exact_line in \
	'static bool ucode_allocation_only;' \
	'module_param(ucode_allocation_only, bool, 0400);' \
	'static atomic_t ucode_allocation_only_consumed = ATOMIC_INIT(0);'
do
	[ "$(grep -Fxc "$exact_line" "$patched_msm_drv")" -eq 1 ] ||
		fail "ucode diagnostic declaration is not exact: $exact_line"
done
[ "$(grep -Fc 'MODULE_PARM_DESC(ucode_allocation_only,' \
	"$patched_msm_drv")" -eq 1 ] ||
	fail 'ucode-allocation parameter description is not exact'
if grep -Eq 'ucode_allocation_only[[:space:]]*=' "$patched_msm_drv"; then
	fail 'ucode-allocation parameter is enabled by source assignment'
fi
[ "$(grep -Fxc 'int adreno_load_ucode_only(struct drm_device *dev);' \
	"$patched_msm_gpu")" -eq 1 ] ||
	fail 'ucode-only helper declaration is not exact'
[ "$(grep -Fxc 'void a6xx_ucode_unload(struct msm_gpu *gpu);' \
	"$patched_a6xx_gpu_h")" -eq 1 ] ||
	fail 'A6xx ucode-unload declaration is not exact'
[ "$(grep -Fxc '#include "a6xx_gpu.h"' \
	"$patched_adreno_device")" -eq 1 ] ||
	fail 'Adreno diagnostic does not include the exact A6xx contract'

msm_open=$(sed -n '/^static int msm_open(/,/^}/p' "$patched_msm_drv")
ucode_open=$(printf '%s\n' "$msm_open" |
	sed -n '/if (ucode_allocation_only) {/,/if (firmware_request_only) {/p')
helper=$(sed -n '/^int adreno_load_ucode_only(/,/^}/p' \
	"$patched_adreno_device")
release_helper=$(sed -n \
	'/^static void adreno_release_diagnostic_fw(/,/^}/p' \
	"$patched_adreno_device")
unload=$(sed -n '/^void a6xx_ucode_unload(/,/^}/p' \
	"$patched_a6xx_gpu")
destroy=$(sed -n '/^static void a6xx_destroy(/,/^}/p' \
	"$patched_a6xx_gpu")
for block in "$msm_open" "$ucode_open" "$helper" "$release_helper" \
	"$unload" "$destroy"
do
	[ -n "$block" ] || fail 'one or more patched diagnostic blocks are missing'
done

conflict_line=$(line_once "$msm_open" \
	'if (firmware_request_only && ucode_allocation_only)' \
	'mutually exclusive diagnostics')
armed_line=$(line_once "$ucode_open" 'if (ucode_allocation_only) {' \
	'ucode diagnostic arm branch')
consume_line=$(line_once "$ucode_open" \
	'atomic_cmpxchg(&ucode_allocation_only_consumed, 0, 1)' \
	'atomic one-shot consume')
already_line=$(line_once "$ucode_open" 'return -EALREADY;' \
	'second-open rejection')
helper_line=$(line_once "$ucode_open" 'adreno_load_ucode_only(dev)' \
	'ucode-only helper call')
marker_line=$(line_once "$ucode_open" \
	'A660 ucode-allocation-only passed and rolled back; reject open' \
	'rollback-complete marker')
failed_open_line=$(line_once "$ucode_open" 'return -EUCLEAN;' \
	'successful diagnostic failed-open result')
firmware_branch_line=$(line_once "$msm_open" \
	'if (firmware_request_only) {' 'firmware-only predecessor branch')
normal_load_line=$(line_once "$msm_open" 'load_gpu(dev);' \
	'unchanged normal GPU load')
context_line=$(line_once "$msm_open" 'context_init(dev, file)' \
	'unchanged normal context creation')
if [ "$conflict_line" -ge "$firmware_branch_line" ] ||
	[ "$armed_line" -ge "$consume_line" ] ||
	[ "$consume_line" -ge "$already_line" ] ||
	[ "$already_line" -ge "$helper_line" ] ||
	[ "$helper_line" -ge "$marker_line" ] ||
	[ "$marker_line" -ge "$failed_open_line" ] ||
	[ "$failed_open_line" -ge "$normal_load_line" ] ||
	[ "$normal_load_line" -ge "$context_line" ]
then
	fail 'one-shot rollback and unchanged normal-path order changed'
fi
if printf '%s\n' "$ucode_open" | grep -Fq 'return 0;'; then
	fail 'ucode-allocation DRM open gained a successful return'
fi

chip_line=$(line_once "$helper" \
	'adreno_gpu->chip_id != 0x06060001' 'exact A660.1 restriction')
empty_line=$(line_once "$helper" \
	'if (a6xx_gpu->sqe_bo || a6xx_gpu->aqe_bo ||' \
	'empty ucode-state precondition')
firmware_line=$(line_once "$helper" \
	'ret = adreno_load_fw(adreno_gpu);' 'catalog firmware request')
ucode_line=$(line_once "$helper" \
	'ret = gpu->funcs->ucode_load(gpu);' 'ucode allocation call')
postcondition_line=$(line_once "$helper" \
	'if (!a6xx_gpu->sqe_bo || a6xx_gpu->aqe_bo ||' \
	'exact three-object postcondition')
unload_line=$(line_once "$helper" \
	'a6xx_ucode_unload(gpu);' 'all-object rollback')
release_line=$(line_once "$helper" \
	'adreno_release_diagnostic_fw(adreno_gpu);' \
	'all-firmware rollback')
if [ "$chip_line" -ge "$empty_line" ] ||
	[ "$empty_line" -ge "$firmware_line" ] ||
	[ "$firmware_line" -ge "$ucode_line" ] ||
	[ "$ucode_line" -ge "$postcondition_line" ] ||
	[ "$postcondition_line" -ge "$unload_line" ] ||
	[ "$unload_line" -ge "$release_line" ]
then
	fail 'exact-chip request/allocation/rollback order changed'
fi
for helper_contract in \
	'goto out_release_fw;' \
	'goto out_unload;' \
	'!a6xx_gpu->pwrup_reglist_bo || !a6xx_gpu->pwrup_reglist_ptr ||' \
	'!a6xx_gpu->sqe_iova || !a6xx_gpu->shadow_iova ||' \
	'ret = -EPROTO;'
do
	line_once "$helper" "$helper_contract" \
		"diagnostic helper contract $helper_contract" >/dev/null
done
for forbidden in pm_runtime regulator_ clk_ icc_ msm_gpu_hw_init \
	a6xx_hfi_start a6xx_gmu_resume adreno_zap qcom_scm \
	qcom_scm_pas_auth_and_reset gpu_write gpu_read gmu_write gmu_read
do
	if printf '%s\n' "$helper" | grep -Fq "$forbidden"; then
		fail "ucode-only helper reaches forbidden work: $forbidden"
	fi
done

for release_contract in \
	'release_firmware(adreno_gpu->fw[i]);' \
	'adreno_gpu->fw[i] = NULL;'
do
	line_once "$release_helper" "$release_contract" \
		"firmware rollback $release_contract" >/dev/null
done

[ "$(printf '%s\n' "$unload" |
	grep -Fc 'msm_gem_unpin_iova')" -eq 2 ] ||
	fail 'SQE/AQE rollback does not contain exactly two IOVA unpins'
[ "$(printf '%s\n' "$unload" |
	grep -Fc 'drm_gem_object_put')" -eq 2 ] ||
	fail 'SQE/AQE rollback does not contain exactly two object puts'
[ "$(printf '%s\n' "$unload" |
	grep -Fc 'msm_gem_kernel_put')" -eq 2 ] ||
	fail 'shadow/reglist rollback does not contain exactly two kernel puts'
for rollback_contract in \
	'msm_gem_unpin_iova(a6xx_gpu->sqe_bo, gpu->vm);' \
	'msm_gem_unpin_iova(a6xx_gpu->aqe_bo, gpu->vm);' \
	'msm_gem_kernel_put(a6xx_gpu->shadow_bo, gpu->vm);' \
	'msm_gem_kernel_put(a6xx_gpu->pwrup_reglist_bo, gpu->vm);' \
	'a6xx_gpu->sqe_bo = NULL;' \
	'a6xx_gpu->sqe_iova = 0;' \
	'a6xx_gpu->aqe_bo = NULL;' \
	'a6xx_gpu->aqe_iova = 0;' \
	'a6xx_gpu->shadow_bo = NULL;' \
	'a6xx_gpu->shadow = NULL;' \
	'a6xx_gpu->shadow_iova = 0;' \
	'a6xx_gpu->pwrup_reglist_bo = NULL;' \
	'a6xx_gpu->pwrup_reglist_ptr = NULL;' \
	'a6xx_gpu->pwrup_reglist_iova = 0;' \
	'a6xx_gpu->pwrup_reglist_emitted = false;'
do
	line_once "$unload" "$rollback_contract" \
		"ucode rollback $rollback_contract" >/dev/null
done
line_once "$destroy" 'a6xx_ucode_unload(gpu);' \
	'normal A6xx balanced ucode destruction' >/dev/null
if printf '%s\n' "$destroy" |
	grep -Eq 'msm_gem_unpin_iova|msm_gem_kernel_put|drm_gem_object_put'
then
	fail 'normal A6xx destroy retains a second partial ucode cleanup'
fi

if grep -Fq 'EXPORT_SYMBOL' "$patch"; then
	fail 'ucode diagnostic helper is exported outside the MSM module'
fi

echo 'PASS ucode-allocation patch is default-off, exact-A660, one-shot, rollback-complete, failed-open, and pre-power'
