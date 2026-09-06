#!/bin/sh
set -eu

patch=${1:?usage: verify-a660-firmware-request-only-patch.sh PATCH PINNED_SOURCE}
source_dir=${2:?missing pinned source}
repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)
accepted_patch=$repo/patches/linux-7.1.4/0013-drm-msm-add-a660-firmware-request-only-diagnostic.patch
expected_commit=d9ac316489f4258d389d6298659d5e9c22183400
expected_tree=c796deb1cc54e942f8bb46a2c76a7199e19e5c92
expected_patch=3413678758f97ea16d8e53e7a24a2bc62a871b333851c32bd8242687bbdc1054

msm_drv_rel=drivers/gpu/drm/msm/msm_drv.c
msm_gpu_rel=drivers/gpu/drm/msm/msm_gpu.h
adreno_device_rel=drivers/gpu/drm/msm/adreno/adreno_device.c
msm_drv=$source_dir/$msm_drv_rel
msm_gpu=$source_dir/$msm_gpu_rel
adreno_device=$source_dir/$adreno_device_rel

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

check_hash "$msm_drv" \
	7f928abf51301516c63c834946e3b264b53416c016f4800729c2a9b1025f9c1e \
	'pinned msm_drv.c'
check_hash "$msm_gpu" \
	b477ecc7f2396b4b65cb28eda9f454c885368277b421e5a11a2209ea4b317b2d \
	'pinned msm_gpu.h'
check_hash "$adreno_device" \
	e7d3de968a744c61394e708cfc416a1aead514c09e71e2a68342260000479599 \
	'pinned adreno_device.c'

if [ "${ALLOW_UNPINNED_PATCH:-0}" != 1 ]; then
	[ "$patch" = "$accepted_patch" ] ||
		fail 'patch path is not the accepted 0013 diagnostic'
	check_hash "$patch" "$expected_patch" 'A660 firmware request-only patch'
fi

expected_numstat=$(printf '%s\n' \
	"23	0	$adreno_device_rel" \
	"23	0	$msm_drv_rel" \
	"1	0	$msm_gpu_rel")
actual_numstat=$(git -C "$source_dir" apply --numstat "$patch")
[ "$actual_numstat" = "$expected_numstat" ] ||
	fail 'patch does not contain the exact three-file addition-only diff'

git -C "$source_dir" apply --check "$patch"
"$source_dir/scripts/checkpatch.pl" --strict --no-tree "$patch" >/dev/null

for symbol in firmware_request_only firmware_request_only_consumed \
	adreno_load_fw_only
do
	if grep -R -Fq "$symbol" "$source_dir/drivers/gpu/drm/msm"; then
		fail "pinned source unexpectedly contains diagnostic symbol: $symbol"
	fi
done

stage=$(mktemp -d)
trap 'rm -rf "$stage"' EXIT INT TERM
mkdir -p "$stage/drivers/gpu/drm/msm/adreno"
cp "$msm_drv" "$stage/$msm_drv_rel"
cp "$msm_gpu" "$stage/$msm_gpu_rel"
cp "$adreno_device" "$stage/$adreno_device_rel"
(cd "$stage" && git apply --check "$patch" && git apply "$patch")

patched_msm_drv=$stage/$msm_drv_rel
patched_msm_gpu=$stage/$msm_gpu_rel
patched_adreno_device=$stage/$adreno_device_rel
if [ "${ALLOW_UNPINNED_PATCH:-0}" != 1 ]; then
	check_hash "$patched_msm_drv" \
		c350e28c18ca723372fc044240a69b452b3698ce57df269a2dad0ad9e2cb569e \
		'patched msm_drv.c'
	check_hash "$patched_msm_gpu" \
		431f78761bbbfe92eab44f685aba653c6e05b54f140fd24fef1358667f05a6c7 \
		'patched msm_gpu.h'
	check_hash "$patched_adreno_device" \
		3654f703a3930add3c131e2bc77453fd1bc506a374075168a5ddbcd66f558379 \
		'patched adreno_device.c'
fi

for exact_line in \
	'static bool firmware_request_only;' \
	'module_param(firmware_request_only, bool, 0400);' \
	'static atomic_t firmware_request_only_consumed = ATOMIC_INIT(0);'
do
	[ "$(grep -Fxc "$exact_line" "$patched_msm_drv")" -eq 1 ] ||
		fail "MSM diagnostic declaration is not exact: $exact_line"
done
[ "$(grep -Fc 'MODULE_PARM_DESC(firmware_request_only,' \
	"$patched_msm_drv")" -eq 1 ] ||
	fail 'firmware request-only parameter description is not exact'
if grep -Eq 'firmware_request_only[[:space:]]*=' "$patched_msm_drv"; then
	fail 'firmware request-only parameter is enabled by source assignment'
fi
[ "$(grep -Fxc 'int adreno_load_fw_only(struct drm_device *dev);' \
	"$patched_msm_gpu")" -eq 1 ] ||
	fail 'firmware-only helper declaration is not exact'

msm_open=$(sed -n '/^static int msm_open(/,/^}/p' "$patched_msm_drv")
helper=$(sed -n '/^int adreno_load_fw_only(/,/^}/p' \
	"$patched_adreno_device")
if [ -z "$msm_open" ] || [ -z "$helper" ]; then
	fail 'patched diagnostic functions are missing'
fi

armed_line=$(line_once "$msm_open" 'if (firmware_request_only) {' \
	'diagnostic arm branch')
consume_line=$(line_once "$msm_open" \
	'atomic_cmpxchg(&firmware_request_only_consumed, 0, 1)' \
	'atomic one-shot consume')
already_line=$(line_once "$msm_open" 'return -EALREADY;' \
	'second-open rejection')
helper_line=$(line_once "$msm_open" 'adreno_load_fw_only(dev)' \
	'firmware-only helper call')
failed_open_line=$(line_once "$msm_open" 'return -EUCLEAN;' \
	'successful-request failed-open result')
normal_load_line=$(line_once "$msm_open" 'load_gpu(dev);' \
	'unchanged normal GPU load')
context_line=$(line_once "$msm_open" 'context_init(dev, file)' \
	'unchanged normal context creation')
if [ "$armed_line" -ge "$consume_line" ] ||
	[ "$consume_line" -ge "$already_line" ] ||
	[ "$already_line" -ge "$helper_line" ] ||
	[ "$helper_line" -ge "$failed_open_line" ] ||
	[ "$failed_open_line" -ge "$normal_load_line" ] ||
	[ "$normal_load_line" -ge "$context_line" ]
then
	fail 'one-shot failed-open and unchanged normal-path order changed'
fi
if printf '%s\n' "$msm_open" | grep -Fq 'return 0;'; then
	fail 'diagnostic DRM open gained a successful return'
fi

chip_line=$(line_once "$helper" \
	'adreno_gpu->chip_id != 0x06060001' 'exact A660.1 restriction')
firmware_line=$(line_once "$helper" \
	'return adreno_load_fw(adreno_gpu);' 'firmware-only request')
[ "$chip_line" -lt "$firmware_line" ] ||
	fail 'firmware request occurs before exact A660.1 validation'
for forbidden in adreno_load_gpu ucode_load pm_runtime msm_gpu_hw_init \
	a6xx_hfi_start qcom_scm_pas_auth_and_reset context_init 'priv->gpu ='
do
	if printf '%s\n' "$helper" | grep -Fq "$forbidden"; then
		fail "firmware-only helper reaches forbidden work: $forbidden"
	fi
done
if grep -Fq 'EXPORT_SYMBOL' "$patch"; then
	fail 'firmware-only helper is exported outside the MSM module'
fi

echo 'PASS firmware-request-only patch is default-off, exact-A660, one-shot, failed-open, and pre-power'
