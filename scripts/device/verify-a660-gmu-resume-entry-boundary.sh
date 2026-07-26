#!/bin/sh
set -eu

source_dir=${1:?usage: verify-a660-gmu-resume-entry-boundary.sh PINNED_SOURCE}
repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)
v7_report=$repo/test-results/2026-07-26-a660-ucode-allocation-v7-live-accepted.md
v7_contract=$repo/scripts/device/test-a660-ucode-allocation-v7-contract.sh

expected_commit=d9ac316489f4258d389d6298659d5e9c22183400
expected_tree=c796deb1cc54e942f8bb46a2c76a7199e19e5c92
expected_v7_report=ea4a4a87a264728be3bfcd86a2f12888496dd51c7421cbee166ad19afdb5ee6a
expected_v7_contract=b212534041828bd81fc7e6684d87fea3f9b53151017a734e2ea77301d1905adc

msm_drv=$source_dir/drivers/gpu/drm/msm/msm_drv.c
msm_gpu_h=$source_dir/drivers/gpu/drm/msm/msm_gpu.h
adreno_device=$source_dir/drivers/gpu/drm/msm/adreno/adreno_device.c
a6xx_gpu=$source_dir/drivers/gpu/drm/msm/adreno/a6xx_gpu.c
a6xx_gmu=$source_dir/drivers/gpu/drm/msm/adreno/a6xx_gmu.c

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

for command in awk cut git grep sed sha256sum; do
	command -v "$command" >/dev/null ||
		fail "missing command: $command"
done

[ -d "$source_dir" ] || fail "missing source directory: $source_dir"
[ "$(git -C "$source_dir" rev-parse --is-inside-work-tree)" = true ] ||
	fail 'source is not a Git worktree'
[ "$(git -C "$source_dir" rev-parse HEAD)" = "$expected_commit" ] ||
	fail 'pinned source commit changed'
[ "$(git -C "$source_dir" rev-parse 'HEAD^{tree}')" = "$expected_tree" ] ||
	fail 'pinned source tree changed'
[ -z "$(git -C "$source_dir" status --porcelain)" ] ||
	fail 'pinned source worktree is not clean'

check_hash "$v7_report" "$expected_v7_report" \
	'accepted A660 ucode-allocation v7 report'
check_hash "$v7_contract" "$expected_v7_contract" \
	'A660 ucode-allocation v7 umbrella'
if [ "${SKIP_V7_UMBRELLA_RUN:-0}" != 1 ]; then
	"$v7_contract" >/dev/null
fi

check_hash "$msm_drv" \
	7f928abf51301516c63c834946e3b264b53416c016f4800729c2a9b1025f9c1e \
	'msm_drv.c'
check_hash "$msm_gpu_h" \
	b477ecc7f2396b4b65cb28eda9f454c885368277b421e5a11a2209ea4b317b2d \
	'msm_gpu.h'
check_hash "$adreno_device" \
	e7d3de968a744c61394e708cfc416a1aead514c09e71e2a68342260000479599 \
	'adreno_device.c'
check_hash "$a6xx_gpu" \
	29733589c6375930852cb26cfee674f83008084e6bdb792fd86164ea487bf85d \
	'a6xx_gpu.c'
check_hash "$a6xx_gmu" \
	97b2fc130862f00445b509855b16121b2eba6e5a5228f92457c2923297fd4999 \
	'a6xx_gmu.c'

msm_open=$(sed -n '/^static int msm_open(/,/^}/p' "$msm_drv")
load_gpu=$(sed -n '/^static void load_gpu(/,/^}/p' "$msm_drv")
adreno_load=$(sed -n \
	'/^struct msm_gpu \*adreno_load_gpu(/,/^}/p' "$adreno_device")
runtime_resume=$(sed -n \
	'/^static int adreno_runtime_resume(/,/^}/p' "$adreno_device")
gmu_pm_resume=$(sed -n \
	'/^static int a6xx_gmu_pm_resume(/,/^}/p' "$a6xx_gpu")
gmu_resume=$(sed -n '/^int a6xx_gmu_resume(/,/^}/p' "$a6xx_gmu")
gpu_hw_init=$(sed -n '/^int msm_gpu_hw_init(/,/^}/p' \
	"$source_dir/drivers/gpu/drm/msm/msm_gpu.c")

for block in "$msm_open" "$load_gpu" "$adreno_load" "$runtime_resume" \
	"$gmu_pm_resume" "$gmu_resume" "$gpu_hw_init"
do
	[ -n "$block" ] || fail 'one or more first-open blocks are missing'
done

line_once "$msm_open" 'load_gpu(dev);' 'DRM open load call' >/dev/null
line_once "$load_gpu" 'priv->gpu = adreno_load_gpu(dev);' \
	'Adreno lazy-load assignment' >/dev/null

fw_line=$(line_once "$adreno_load" 'ret = adreno_load_fw(adreno_gpu);' \
	'catalog firmware load')
ucode_line=$(line_once "$adreno_load" 'if (gpu->funcs->ucode_load) {' \
	'ucode allocation')
enable_line=$(line_once "$adreno_load" 'pm_runtime_enable(&pdev->dev);' \
	'GPU runtime-PM enable')
outer_get_line=$(line_once "$adreno_load" \
	'ret = pm_runtime_get_sync(&pdev->dev);' 'GPU runtime-PM get')
outer_put_line=$(line_once "$adreno_load" \
	'pm_runtime_put_noidle(&pdev->dev);' 'failed GPU runtime-PM put')
disable_line=$(line_once "$adreno_load" \
	'pm_runtime_disable(&pdev->dev);' 'failed GPU runtime-PM disable')
hardware_line=$(line_once "$adreno_load" \
	'ret = msm_gpu_hw_init(gpu);' 'GPU hardware initialization')
if [ "$fw_line" -ge "$ucode_line" ] ||
	[ "$ucode_line" -ge "$enable_line" ] ||
	[ "$enable_line" -ge "$outer_get_line" ] ||
	[ "$outer_get_line" -ge "$hardware_line" ] ||
	[ "$outer_get_line" -ge "$outer_put_line" ] ||
	[ "$outer_put_line" -ge "$disable_line" ]
then
	fail 'first-open firmware/ucode/runtime-PM/error order changed'
fi

line_once "$runtime_resume" 'return gpu->funcs->pm_resume(gpu);' \
	'Adreno runtime-resume dispatch' >/dev/null
pm_call_line=$(line_once "$gmu_pm_resume" \
	'ret = a6xx_gmu_resume(a6xx_gpu);' 'A6xx GMU-resume call')
pm_error_line=$(line_once "$gmu_pm_resume" 'if (ret)' \
	'A6xx GMU-resume error test')
pm_return_line=$(printf '%s\n' "$gmu_pm_resume" | nl -ba |
	awk '/if \(ret\)/ { after_error = 1 }
		after_error && /return ret;/ { print $1; exit }')
[ -n "$pm_return_line" ] ||
	fail 'A6xx GMU-resume error return is missing'
devfreq_line=$(line_once "$gmu_pm_resume" 'msm_devfreq_resume(gpu);' \
	'deferred devfreq resume')
llc_line=$(line_once "$gmu_pm_resume" 'a6xx_llc_activate(a6xx_gpu);' \
	'deferred A6xx LLC activation')
if [ "$pm_call_line" -ge "$pm_error_line" ] ||
	[ "$pm_error_line" -ge "$devfreq_line" ] ||
	[ "$pm_error_line" -ge "$pm_return_line" ] ||
	[ "$pm_return_line" -ge "$devfreq_line" ] ||
	[ "$devfreq_line" -ge "$llc_line" ]
then
	fail 'GMU-resume error no longer excludes devfreq and LLC activation'
fi

initialized_line=$(line_once "$gmu_resume" \
	'if (WARN(!gmu->initialized,' \
	'GMU initialized guard')
hung_line=$(line_once "$gmu_resume" 'gmu->hung = false;' \
	'first GMU software mutation')
cx_line=$(line_once "$gmu_resume" 'pm_runtime_get_sync(gmu->dev);' \
	'GMU CX runtime-PM get')
gx_line=$(line_once "$gmu_resume" 'pm_runtime_get_sync(gmu->gxpd);' \
	'GMU GX runtime-PM get')
rate_line=$(line_once "$gmu_resume" \
	'clk_set_rate(gmu->core_clk, 200000000);' 'GMU clock rate')
clock_line=$(line_once "$gmu_resume" \
	'clk_bulk_prepare_enable(gmu->nr_clocks, gmu->clocks);' \
	'GMU clock enable')
secure_line=$(line_once "$gmu_resume" \
	'ret = a6xx_gmu_secure_init(a6xx_gpu);' 'GMU secure init')
bw_line=$(line_once "$gmu_resume" \
	'a6xx_gmu_set_initial_bw(gpu, gmu);' 'GMU bandwidth vote')
irq_line=$(line_once "$gmu_resume" 'enable_irq(gmu->gmu_irq);' \
	'GMU IRQ enable')
firmware_start_line=$(line_once "$gmu_resume" \
	'ret = a6xx_gmu_fw_start(gmu, status);' 'GMU firmware start')
hfi_line=$(line_once "$gmu_resume" \
	'ret = a6xx_hfi_start(gmu, status);' 'GMU HFI start')
if [ "$initialized_line" -ge "$hung_line" ] ||
	[ "$hung_line" -ge "$cx_line" ] ||
	[ "$cx_line" -ge "$gx_line" ] ||
	[ "$gx_line" -ge "$rate_line" ] ||
	[ "$rate_line" -ge "$clock_line" ] ||
	[ "$clock_line" -ge "$secure_line" ] ||
	[ "$secure_line" -ge "$bw_line" ] ||
	[ "$bw_line" -ge "$irq_line" ] ||
	[ "$irq_line" -ge "$firmware_start_line" ] ||
	[ "$firmware_start_line" -ge "$hfi_line" ]
then
	fail 'GMU resume side-effect order changed'
fi

for deferred in \
	'a6xx_gmu_secure_init' \
	'a6xx_gmu_set_initial_bw' \
	'a6xx_gmu_fw_start' \
	'a6xx_hfi_start' \
	'adreno_zap_shader_load' \
	'qcom_scm_pas_auth_and_reset'
do
	grep -R -Fq "$deferred" "$source_dir/drivers/gpu/drm/msm" \
		"$source_dir/drivers/firmware/qcom" ||
		fail "missing deferred boundary symbol: $deferred"
done

printf '%s\n' \
	'PASS A660 GMU resume has an entry-only seam after initialization validation and before software mutation, PM domains, clocks, MMIO, IRQ, firmware start, HFI, hardware init, ZAP, or SCM'
