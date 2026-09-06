#!/bin/sh
set -eu

source_dir=${1:?usage: verify-a660-firmware-only-boundary.sh PINNED_SOURCE FIRMWARE_ROOT [LIVE_REPORT] [ACCEPTANCE_MARKER]}
firmware_root=${2:?missing firmware root}
repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)
report=${3:-$repo/test-results/2026-07-26-a660-registration-v3-live-accepted.md}
marker=${4:-$repo/manifests/acceptance/a660-registration-v3-live.accepted}

expected_commit=d9ac316489f4258d389d6298659d5e9c22183400
expected_tree=c796deb1cc54e942f8bb46a2c76a7199e19e5c92
report_sha=2af09c087c917b7d1325c0b8a361c7ec3594779983034be0736acac841f8da79
marker_sha=8d350d51d8f35583f6ba32f005fc9b9fc035c6f24186c5b1786b2f60a90a0f6f

msm_dir=$source_dir/drivers/gpu/drm/msm
msm_drv=$msm_dir/msm_drv.c
adreno_device=$msm_dir/adreno/adreno_device.c
adreno_gpu=$msm_dir/adreno/adreno_gpu.c
a6xx_catalog=$msm_dir/adreno/a6xx_catalog.c
a6xx_gpu=$msm_dir/adreno/a6xx_gpu.c
a6xx_gmu=$msm_dir/adreno/a6xx_gmu.c
dtsi=$source_dir/arch/arm64/boot/dts/qcom/sm8350.dtsi
hdk=$source_dir/arch/arm64/boot/dts/qcom/sm8350-hdk.dts
acceptance_verifier=$repo/scripts/device/verify-a660-registration-v3-live-acceptance.sh

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

for command in awk cut git grep sed sha256sum tr wc; do
	command -v "$command" >/dev/null ||
		fail "missing command: $command"
done

[ -d "$source_dir" ] || fail "missing source directory: $source_dir"
[ -d "$firmware_root" ] || fail "missing firmware root: $firmware_root"
[ -x "$acceptance_verifier" ] ||
	fail "missing executable acceptance verifier: $acceptance_verifier"
[ "$(git -C "$source_dir" rev-parse --is-inside-work-tree)" = true ] ||
	fail 'source is not a Git worktree'
[ "$(git -C "$source_dir" rev-parse HEAD)" = "$expected_commit" ] ||
	fail 'pinned source commit changed'
[ "$(git -C "$source_dir" rev-parse 'HEAD^{tree}')" = "$expected_tree" ] ||
	fail 'pinned source tree changed'
[ -z "$(git -C "$source_dir" status --porcelain)" ] ||
	fail 'pinned source worktree is not clean'

check_hash "$report" "$report_sha" 'A660 v3 live report'
check_hash "$marker" "$marker_sha" 'A660 v3 acceptance marker'
"$acceptance_verifier" "$report" "$marker" >/dev/null

check_hash "$msm_drv" \
	7f928abf51301516c63c834946e3b264b53416c016f4800729c2a9b1025f9c1e \
	'msm_drv.c'
check_hash "$adreno_device" \
	e7d3de968a744c61394e708cfc416a1aead514c09e71e2a68342260000479599 \
	'adreno_device.c'
check_hash "$adreno_gpu" \
	3bd1c6a4d15f1f31ecfbda2ea1d1a07d6b122eb2864adfaf6178e8942bc9fbe0 \
	'adreno_gpu.c'
check_hash "$a6xx_catalog" \
	f1089d825f7b52029520509a39de23c6c05c4ef432e6dff0b084dbdb4bf547b8 \
	'a6xx_catalog.c'
check_hash "$a6xx_gpu" \
	29733589c6375930852cb26cfee674f83008084e6bdb792fd86164ea487bf85d \
	'a6xx_gpu.c'
check_hash "$a6xx_gmu" \
	97b2fc130862f00445b509855b16121b2eba6e5a5228f92457c2923297fd4999 \
	'a6xx_gmu.c'
check_hash "$dtsi" \
	58d28a520a21e21f55703ae968d6e45c6b7750e6a2d3138dcb6cafe2bc6d0a3c \
	'sm8350.dtsi'
check_hash "$hdk" \
	23a033cf675cb898cfaf2f660ce3fc60a5728d85d5a6fe35e35ce169657dfd9f \
	'sm8350-hdk.dts'

sqe=$firmware_root/qcom/a660_sqe.fw
gmu_fw=$firmware_root/qcom/a660_gmu.bin
zap=$firmware_root/qcom/sm8350/a660_zap.mbn
check_hash "$sqe" \
	d222f3fe290ef0516ee0ec43082596bad2df0fcbc2e0bbb26987623cef90cf76 \
	'A660 SQE firmware'
check_hash "$gmu_fw" \
	8acab7b417d9ebde89a1de9ae1e2c261d352fcab122e31ecd580cec9fe2ae5e7 \
	'A660 GMU firmware'
check_hash "$zap" \
	5dbe91cb3fc9655ea2f2a9e1e169a0e30877bec84215899136a519444ca62a3d \
	'A660 ZAP firmware'
[ "$(wc -c <"$sqe" | tr -d ' ')" -eq 43292 ] ||
	fail 'A660 SQE firmware size changed'
[ "$(wc -c <"$gmu_fw" | tr -d ' ')" -eq 55252 ] ||
	fail 'A660 GMU firmware size changed'
[ "$(wc -c <"$zap" | tr -d ' ')" -eq 1054648 ] ||
	fail 'A660 ZAP firmware size changed'

a660_catalog=$(sed -n \
	'/[.]chip_ids = ADRENO_CHIP_IDS(0x06060001)/,/^[[:space:]]*}, {/p' \
	"$a6xx_catalog")
[ -n "$a660_catalog" ] || fail 'missing exact A660.1 catalog entry'
for catalog_contract in \
	'.revn = 660,' \
	'[ADRENO_FW_SQE] = "a660_sqe.fw",' \
	'[ADRENO_FW_GMU] = "a660_gmu.bin",' \
	'.funcs = &a6xx_gpu_funcs,'
do
	line_once "$a660_catalog" "$catalog_contract" \
		"A660 catalog contract $catalog_contract" >/dev/null
done
[ "$(printf '%s\n' "$a660_catalog" |
	grep -c '\[ADRENO_FW_')" -eq 2 ] ||
	fail 'A660.1 catalog firmware list is not exactly SQE plus GMU'

hdk_zap=$(sed -n '/^&gpu_zap_shader {/,/^};/p' "$hdk")
line_once "$hdk_zap" \
	'firmware-name = "qcom/sm8350/a660_zap.mbn";' \
	'A660 HDK ZAP firmware path' >/dev/null

adreno_gpu_refs=$(grep -R --include='*.c' -F 'adreno_load_gpu(' \
	"$msm_dir" | wc -l | tr -d ' ')
[ "$adreno_gpu_refs" -eq 2 ] ||
	fail "adreno_load_gpu(dev) C definition-plus-call count is $adreno_gpu_refs, expected 2"
adreno_fw_refs=$(grep -R --include='*.c' -F 'adreno_load_fw(' \
	"$msm_dir" | wc -l | tr -d ' ')
[ "$adreno_fw_refs" -eq 2 ] ||
	fail "adreno_load_fw(adreno_gpu) C definition-plus-call count is $adreno_fw_refs, expected 2"
load_gpu_calls=$(grep -R --include='*.c' -E \
	'^[[:space:]]*load_gpu\(dev\);[[:space:]]*$' \
	"$msm_dir" | wc -l | tr -d ' ')
[ "$load_gpu_calls" -eq 1 ] ||
	fail "load_gpu(dev) exact C call count is $load_gpu_calls, expected 1"

msm_open_block=$(sed -n '/^static int msm_open(/,/^}/p' "$msm_drv")
load_gpu_block=$(sed -n '/^static void load_gpu(/,/^}/p' "$msm_drv")
adreno_load_block=$(sed -n \
	'/^struct msm_gpu \*adreno_load_gpu(/,/^}/p' "$adreno_device")
firmware_load_block=$(sed -n '/^int adreno_load_fw(/,/^}/p' "$adreno_gpu")
firmware_request_block=$(sed -n \
	'/^adreno_request_fw(/,/^}/p' "$adreno_gpu")
gmu_resume_block=$(sed -n '/^int a6xx_gmu_resume(/,/^}/p' "$a6xx_gmu")

open_load_line=$(line_once "$msm_open_block" 'load_gpu(dev);' \
	'msm_open lazy GPU load')
open_context_line=$(line_once "$msm_open_block" \
	'return context_init(dev, file);' 'msm_open context initialization')
[ "$open_load_line" -lt "$open_context_line" ] ||
	fail 'msm_open no longer loads the GPU before creating a file context'
line_once "$load_gpu_block" 'priv->gpu = adreno_load_gpu(dev);' \
	'load_gpu Adreno call' >/dev/null

firmware_line=$(line_once "$adreno_load_block" \
	'adreno_load_fw(adreno_gpu)' 'Adreno firmware load')
ucode_line=$(line_once "$adreno_load_block" \
	'if (gpu->funcs->ucode_load) {' 'Adreno ucode boundary')
runtime_enable_line=$(line_once "$adreno_load_block" \
	'pm_runtime_enable(&pdev->dev);' 'GPU runtime-PM enable')
runtime_get_line=$(line_once "$adreno_load_block" \
	'pm_runtime_get_sync(&pdev->dev);' 'GPU runtime-PM resume')
hardware_line=$(line_once "$adreno_load_block" \
	'msm_gpu_hw_init(gpu);' 'GPU hardware initialization')
if [ "$firmware_line" -ge "$ucode_line" ] ||
	[ "$ucode_line" -ge "$runtime_enable_line" ] ||
	[ "$runtime_enable_line" -ge "$runtime_get_line" ] ||
	[ "$runtime_get_line" -ge "$hardware_line" ]
then
	fail 'Adreno first-open firmware/ucode/power/hardware order changed'
fi

for firmware_step in \
	'adreno_request_fw(adreno_gpu, adreno_gpu->info->fw[i])' \
	'adreno_gpu->fw[i] = fw;'
do
	line_once "$firmware_load_block" "$firmware_step" \
		"firmware-only step $firmware_step" >/dev/null
done
if printf '%s\n' "$firmware_load_block" |
	grep -Eq 'ucode_load|pm_runtime|msm_gpu_hw_init|a6xx_hfi_start|qcom_scm'
then
	fail 'adreno_load_fw now performs work beyond firmware requests'
fi
[ "$(printf '%s\n' "$firmware_request_block" |
	grep -Fc 'request_firmware_direct')" -eq 2 ] ||
	fail 'direct firmware request paths are not exact'

for deferred_step in \
	'ret = a6xx_gmu_resume(a6xx_gpu);' \
	'ret = a6xx_zap_shader_init(gpu);'
do
	grep -Fq "$deferred_step" "$a6xx_gpu" ||
		fail "A6xx deferred hardware path omits: $deferred_step"
done
for deferred_step in \
	'ret = a6xx_gmu_fw_start(gmu, status);' \
	'ret = a6xx_hfi_start(gmu, status);'
do
	line_once "$gmu_resume_block" "$deferred_step" \
		"GMU resume step $deferred_step" >/dev/null
done
grep -Fq 'request_firmware_direct(&fw, fwname, gpu->dev->dev);' \
	"$adreno_gpu" ||
	fail 'ZAP firmware direct-request path changed'
grep -Fq 'qcom_scm_pas_auth_and_reset(pasid)' "$adreno_gpu" ||
	fail 'qcom_scm_pas_auth_and_reset ZAP authentication path changed'

echo 'PASS firmware request can be isolated before ucode, runtime power, hardware init, HFI, and ZAP/SCM'
