#!/bin/sh
# shellcheck disable=SC2016
set -eu

repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)
baseline=$repo/scripts/device/check-network-root-a660-ucode-allocation-baseline.sh
probe=$repo/scripts/device/probe-network-root-a660-ucode-allocation.sh
verifier=$repo/scripts/device/verify-a660-ucode-allocation-runtime-sources.sh

[ -x "$verifier" ] || {
	echo 'FAIL missing ucode-allocation runtime-source verifier' >&2
	exit 1
}
"$verifier" "$baseline" "$probe" >/dev/null

work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT INT TERM

expect_rejected() {
	name=$1
	mutated_baseline=$2
	mutated_probe=$3
	if ALLOW_UNPINNED_A660_UCODE_RUNTIME=1 \
		"$verifier" "$mutated_baseline" "$mutated_probe" \
		>"$work/$name.log" 2>&1
	then
		echo "FAIL ucode-allocation runtime mutation passed: $name" >&2
		exit 1
	fi
}

sed 's/ucode_allocation_only=1/ucode_allocation_only=0/' "$probe" \
	>"$work/unarmed-msm.sh"
expect_rejected unarmed-msm "$baseline" "$work/unarmed-msm.sh"

sed 's/firmware_request_only=N/firmware_request_only=Y/' "$probe" \
	>"$work/mutual-exclusion-lost.sh"
expect_rejected mutual-exclusion-lost "$baseline" \
	"$work/mutual-exclusion-lost.sh"

{
	cat "$probe"
	printf '%s\n' 'sh -c '\''kill -STOP "$$"; exec "$1"'\'' sh "$helper"'
} >"$work/second-open.sh"
expect_rejected second-open "$baseline" "$work/second-open.sh"

sed 's/\[ "$helper_status" -eq 117 \]/[ "$helper_status" -eq 0 ]/' \
	"$probe" >"$work/wrong-errno.sh"
expect_rejected wrong-errno "$baseline" "$work/wrong-errno.sh"

sed 's/set_event_pid/set_event_pidx/g' "$probe" \
	>"$work/no-pid-filter.sh"
expect_rejected no-pid-filter "$baseline" "$work/no-pid-filter.sh"

sed "s/require_event_count rog5_ucode_vma_map 3 'VMA map'/require_event_count rog5_ucode_vma_map 2 'VMA map'/" \
	"$probe" >"$work/two-maps.sh"
expect_rejected two-maps "$baseline" "$work/two-maps.sh"

sed '/p:rog5_ucode\/rog5_ucode_vma_unmap msm:msm_gem_vma_unmap/d' \
	"$probe" >"$work/no-unmap-probe.sh"
expect_rejected no-unmap-probe "$baseline" "$work/no-unmap-probe.sh"

sed '/cmp "$state_dir\/gem.before" "$state_dir\/gem.after"/d' "$probe" \
	>"$work/no-gem-snapshot.sh"
expect_rejected no-gem-snapshot "$baseline" "$work/no-gem-snapshot.sh"

sed '/p:rog5_ucode\/rog5_ucode_scm_aperture qcom_scm_set_gpu_smmu_aperture/d' \
	"$probe" >"$work/no-scm-boundary.sh"
expect_rejected no-scm-boundary "$baseline" "$work/no-scm-boundary.sh"

sed 's/d222f3fe290ef0516ee0ec43082596bad2df0fcbc2e0bbb26987623cef90cf76/0222f3fe290ef0516ee0ec43082596bad2df0fcbc2e0bbb26987623cef90cf76/' \
	"$baseline" >"$work/wrong-sqe.sh"
expect_rejected wrong-sqe "$work/wrong-sqe.sh" "$probe"

{
	printf 'systemctl reboot\n'
	cat "$probe"
} >"$work/reboot-bypass.sh"
expect_rejected reboot-bypass "$baseline" "$work/reboot-bypass.sh"

echo 'PASS ucode-allocation runtime rejects unarmed or mixed modes, second open, wrong errno, unfiltered or incomplete traces, unbalanced maps, missing state snapshot, wrong firmware, and reboot bypass'
