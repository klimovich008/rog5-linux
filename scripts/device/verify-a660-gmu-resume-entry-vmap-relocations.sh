#!/bin/bash
set -euo pipefail

repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)
module=${1:-$repo/artifacts/a660-gmu-resume-entry-build-a/drivers/gpu/drm/msm/msm.ko}
expected_sha256=b485e8719d6ddf80542a5dc2fdf5bba795d40c69fa220b44571323a8a1d7d861

fail() {
	echo "FAIL $*" >&2
	exit 1
}

for command in awk cut grep nm readelf sha256sum; do
	command -v "$command" >/dev/null ||
		fail "missing command: $command"
done

[ -f "$module" ] && [ ! -L "$module" ] && [ -r "$module" ] ||
	fail "GMU resume-entry MSM module is missing, linked, or unreadable: $module"
actual_sha256=$(sha256sum "$module" | cut -d ' ' -f 1)
[[ $actual_sha256 == "$expected_sha256" ]] ||
	fail "MSM module hash mismatch: expected $expected_sha256, got $actual_sha256"

symbols=$(nm -n -S --defined-only "$module")
for symbol in \
	'0000000000000694 0000000000000010 T msm_a660_gmu_resume_entry_only_enabled' \
	'00000000000006a4 000000000000005c T msm_a660_gmu_resume_entry_only_mark_hit' \
	'0000000000000700 0000000000000018 T msm_a660_gmu_resume_entry_only_was_hit' \
	'0000000000000d00 0000000000000340 t msm_open' \
	'00000000000035d4 0000000000000020 T msm_gem_get_vaddr_locked' \
	'0000000000003740 0000000000000050 T msm_gem_get_vaddr' \
	'00000000000037b0 0000000000000080 T msm_gem_put_vaddr_locked' \
	'0000000000003830 0000000000000088 T msm_gem_put_vaddr' \
	'00000000000048a0 0000000000000124 T msm_gem_kernel_new' \
	'00000000000049c4 0000000000000104 T msm_gem_kernel_put' \
	'000000000001422c 00000000000000b8 T adreno_rollback_gpu_load_only' \
	'00000000000142e4 00000000000001d4 T adreno_load_gpu' \
	'0000000000014cd4 0000000000000034 t adreno_runtime_resume' \
	'0000000000015c1c 000000000000009c T adreno_fw_create_bo' \
	'00000000000227c4 0000000000000150 T a6xx_ucode_unload' \
	'000000000002537c 0000000000000374 t a6xx_ucode_load' \
	'0000000000025794 0000000000000124 t a6xx_gmu_pm_resume' \
	'000000000002aaa0 0000000000001274 T a6xx_gmu_resume'
do
	grep -Fqx "$symbol" <<<"$symbols" ||
		fail "compiled symbol identity changed: $symbol"
done

relocations=$(readelf -Wr "$module" |
	awk '
		/^Relocation section '\''[.]rela[.]text'\''/ { in_text = 1; next }
		/^Relocation section / { in_text = 0 }
		in_text { print }
	')
[[ -n $relocations ]] || fail 'module has no .rela.text records'

call_count() {
	local start_hex=$1
	local size_hex=$2
	local target=$3
	local start=$((16#$start_hex))
	local end=$((start + 16#$size_hex))
	local count=0
	local offset type symbol off

	while read -r offset _ type _ symbol _; do
		[[ $type == R_AARCH64_CALL26 ]] || continue
		[[ $offset =~ ^[[:xdigit:]]+$ ]] || continue
		off=$((16#$offset))
		if ((off >= start && off < end)) && [[ $symbol == "$target" ]]; then
			((count += 1))
		fi
	done <<<"$relocations"
	printf '%d\n' "$count"
}

require_count() {
	local start=$1
	local size=$2
	local target=$3
	local expected=$4
	local label=$5
	local actual

	actual=$(call_count "$start" "$size" "$target")
	[[ $actual == "$expected" ]] ||
		fail "$label has $actual calls to $target, expected $expected"
}

require_call() {
	local offset=$1
	local target=$2

	awk -v offset="$offset" -v target="$target" '
		$1 == offset && $3 == "R_AARCH64_CALL26" && $5 == target {
			count++
		}
		END { exit count == 1 ? 0 : 1 }
	' <<<"$relocations" ||
		fail "missing exact CALL26 relocation $offset -> $target"
}

# Clang inlined the public vmap wrappers into these convenience helpers.
# The runtime therefore combines their entry probes with the public wrappers.
require_count 00000000000048a0 0000000000000124 \
	msm_gem_get_vaddr 0 'msm_gem_kernel_new'
require_count 00000000000048a0 0000000000000124 \
	msm_gem_get_vaddr_locked 0 'msm_gem_kernel_new'
require_count 00000000000049c4 0000000000000104 \
	msm_gem_put_vaddr 0 'msm_gem_kernel_put'
require_count 00000000000049c4 0000000000000104 \
	msm_gem_put_vaddr_locked 0 'msm_gem_kernel_put'

# Preserve the accepted v7 three-object allocation and logical 4/4 rollback.
require_count 0000000000015c1c 000000000000009c \
	msm_gem_kernel_new 1 'adreno_fw_create_bo'
require_count 0000000000015c1c 000000000000009c \
	msm_gem_put_vaddr 1 'adreno_fw_create_bo'
require_count 000000000002537c 0000000000000374 \
	msm_gem_kernel_new 2 'a6xx_ucode_load'
require_count 000000000002537c 0000000000000374 \
	msm_gem_get_vaddr 1 'a6xx_ucode_load'
require_count 000000000002537c 0000000000000374 \
	msm_gem_put_vaddr 2 'a6xx_ucode_load'
require_count 00000000000227c4 0000000000000150 \
	msm_gem_kernel_put 2 'a6xx_ucode_unload'

for call in \
	'0000000000015c64 msm_gem_kernel_new' \
	'0000000000015c84 msm_gem_put_vaddr' \
	'00000000000253dc msm_gem_kernel_new' \
	'0000000000025418 msm_gem_kernel_new' \
	'00000000000254fc msm_gem_get_vaddr' \
	'000000000002563c msm_gem_put_vaddr' \
	'0000000000025684 msm_gem_put_vaddr' \
	'00000000000228c8 msm_gem_kernel_put' \
	'00000000000228e0 msm_gem_kernel_put'
do
	require_call "${call% *}" "${call#* }"
done

# Pin the new one-open route, failed outer runtime resume, and cleanup route.
require_count 0000000000000d00 0000000000000340 \
	adreno_load_gpu 2 'msm_open'
require_count 0000000000000d00 0000000000000340 \
	adreno_rollback_gpu_load_only 1 'msm_open'
require_call 0000000000000d88 adreno_load_gpu
require_call 0000000000000db4 adreno_rollback_gpu_load_only
require_count 000000000001422c 00000000000000b8 \
	a6xx_ucode_unload 1 'adreno_rollback_gpu_load_only'
require_count 000000000001422c 00000000000000b8 \
	release_firmware 4 'adreno_rollback_gpu_load_only'
for call in \
	'000000000001427c a6xx_ucode_unload' \
	'0000000000014288 release_firmware' \
	'0000000000014298 release_firmware' \
	'00000000000142a8 release_firmware' \
	'00000000000142b8 release_firmware' \
	'0000000000014380 __pm_runtime_resume'
do
	require_call "${call% *}" "${call#* }"
done
require_count 00000000000142e4 00000000000001d4 \
	__pm_runtime_resume 1 'adreno_load_gpu'

# The diagnostic hit is compiled before every inner power/resource call.
require_count 0000000000025794 0000000000000124 \
	a6xx_gmu_resume 1 'a6xx_gmu_pm_resume'
require_count 0000000000025794 0000000000000124 \
	msm_devfreq_resume 1 'a6xx_gmu_pm_resume'
require_call 00000000000257c4 a6xx_gmu_resume
require_call 00000000000257dc msm_devfreq_resume
require_count 000000000002aaa0 0000000000001274 \
	msm_a660_gmu_resume_entry_only_enabled 1 'a6xx_gmu_resume'
require_count 000000000002aaa0 0000000000001274 \
	msm_a660_gmu_resume_entry_only_mark_hit 1 'a6xx_gmu_resume'
require_count 000000000002aaa0 0000000000001274 \
	__pm_runtime_resume 2 'a6xx_gmu_resume'
require_count 000000000002aaa0 0000000000001274 \
	clk_set_rate 2 'a6xx_gmu_resume'
require_count 000000000002aaa0 0000000000001274 \
	enable_irq 2 'a6xx_gmu_resume'
require_count 000000000002aaa0 0000000000001274 \
	a6xx_hfi_start 1 'a6xx_gmu_resume'
for call in \
	'000000000002aad4 msm_a660_gmu_resume_entry_only_enabled' \
	'000000000002aaf0 msm_a660_gmu_resume_entry_only_mark_hit' \
	'000000000002ab24 __pm_runtime_resume' \
	'000000000002ab3c __pm_runtime_resume' \
	'000000000002ab54 clk_set_rate' \
	'000000000002ab80 clk_set_rate' \
	'000000000002ad4c enable_irq' \
	'000000000002ba20 a6xx_hfi_start' \
	'000000000002ba6c enable_irq'
do
	require_call "${call% *}" "${call#* }"
done

contract='gmu_hit_before_inner_pm=1 logical_gets=4 logical_puts=4 wrapper_gets=1 wrapper_puts=2 kernel_news=3 kernel_puts=2 snapshot=still-required'
echo "PASS A660 GMU resume-entry v8 relocations module=$actual_sha256 $contract"
