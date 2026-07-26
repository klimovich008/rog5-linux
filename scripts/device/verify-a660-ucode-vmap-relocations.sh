#!/bin/bash
set -euo pipefail

repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)
module=${1:-$repo/artifacts/a660-ucode-allocation-build-a/drivers/gpu/drm/msm/msm.ko}
expected_sha256=fe5d59675e4f7d490c38cc7e9c02cadb7bbf89047ceb8056aa0a3e13353bcc45

fail() {
	echo "FAIL $*" >&2
	exit 1
}

for command in awk cut grep nm readelf sha256sum; do
	command -v "$command" >/dev/null ||
		fail "missing command: $command"
done

[ -f "$module" ] && [ ! -L "$module" ] && [ -r "$module" ] ||
	fail "MSM module is missing, linked, or unreadable: $module"
actual_sha256=$(sha256sum "$module" | cut -d ' ' -f 1)
[[ $actual_sha256 == "$expected_sha256" ]] ||
	fail "MSM module hash mismatch: expected $expected_sha256, got $actual_sha256"

symbols=$(nm -n -S --defined-only "$module")
for symbol in \
	'0000000000003468 0000000000000020 T msm_gem_get_vaddr_locked' \
	'00000000000035d4 0000000000000050 T msm_gem_get_vaddr' \
	'0000000000003644 0000000000000080 T msm_gem_put_vaddr_locked' \
	'00000000000036c4 0000000000000088 T msm_gem_put_vaddr' \
	'0000000000004734 0000000000000124 T msm_gem_kernel_new' \
	'0000000000004858 0000000000000104 T msm_gem_kernel_put' \
	'0000000000013ea4 00000000000001b8 T adreno_load_ucode_only' \
	'00000000000159f8 000000000000009c T adreno_fw_create_bo' \
	'00000000000225a0 0000000000000150 T a6xx_ucode_unload' \
	'0000000000025158 0000000000000374 t a6xx_ucode_load'
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

# Clang inlined the public wrapper bodies into these two convenience helpers.
# Kprobes on the public wrapper symbols therefore cannot count these logical
# acquisitions and releases.
require_count 0000000000004734 0000000000000124 \
	msm_gem_get_vaddr 0 'msm_gem_kernel_new'
require_count 0000000000004734 0000000000000124 \
	msm_gem_get_vaddr_locked 0 'msm_gem_kernel_new'
require_count 0000000000004858 0000000000000104 \
	msm_gem_put_vaddr 0 'msm_gem_kernel_put'
require_count 0000000000004858 0000000000000104 \
	msm_gem_put_vaddr_locked 0 'msm_gem_kernel_put'

# The exact A660 allocation path has three kernel_new call sites: one SQE
# object plus shadow and power-up-reglist objects. Its rollback has two
# kernel_put call sites; SQE uses its dedicated unpin/object-put path.
require_count 00000000000159f8 000000000000009c \
	msm_gem_kernel_new 1 'adreno_fw_create_bo'
require_count 00000000000159f8 000000000000009c \
	msm_gem_put_vaddr 1 'adreno_fw_create_bo'
require_count 0000000000025158 0000000000000374 \
	msm_gem_kernel_new 2 'a6xx_ucode_load'
require_count 0000000000025158 0000000000000374 \
	msm_gem_get_vaddr 1 'a6xx_ucode_load'
require_count 0000000000025158 0000000000000374 \
	msm_gem_put_vaddr 2 'a6xx_ucode_load'
require_count 00000000000225a0 0000000000000150 \
	msm_gem_kernel_put 2 'a6xx_ucode_unload'

for call in \
	'0000000000015a40 msm_gem_kernel_new' \
	'0000000000015a60 msm_gem_put_vaddr' \
	'00000000000251b8 msm_gem_kernel_new' \
	'00000000000251f4 msm_gem_kernel_new' \
	'00000000000252d8 msm_gem_get_vaddr' \
	'0000000000025418 msm_gem_put_vaddr' \
	'0000000000025460 msm_gem_put_vaddr' \
	'00000000000226a4 msm_gem_kernel_put' \
	'00000000000226bc msm_gem_kernel_put'
do
	require_call "${call% *}" "${call#* }"
done

# On the accepted A660 success branch, one of the two version-check put
# branches executes. Together with adreno_fw_create_bo, that produces the
# wrapper counts seen live. The inlined operations must be counted through
# kernel_new/kernel_put probes, and a post-settle GEM snapshot remains an
# independent acceptance condition.
contract='logical_gets=4 logical_puts=4 wrapper_gets=1 wrapper_puts=2 kernel_news=3 kernel_puts=2 snapshot=still-required'

echo "PASS A660 ucode vmap relocations module=$actual_sha256 $contract"
