#!/bin/sh
# shellcheck disable=SC2016
set -eu

repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)
builder=$repo/scripts/device/build-a660-ucode-allocation-v6-runtime.sh
verifier=$repo/scripts/device/verify-a660-ucode-allocation-v6-runtime-sources.sh

for input in "$builder" "$verifier"; do
	[ -x "$input" ] || {
		echo "FAIL missing A660 ucode-allocation v6 runtime tool: $input" >&2
		exit 1
	}
done

work=$(mktemp -d)
trap 'rm -rf -- "$work"' EXIT HUP INT TERM
baseline=$work/baseline
probe=$work/probe
"$builder" "$baseline" "$probe" >/dev/null
"$verifier" "$baseline" "$probe" >/dev/null

expect_rejected() {
	name=$1
	mutated_baseline=$2
	mutated_probe=$3
	if ALLOW_UNPINNED_A660_UCODE_V6_RUNTIME=1 \
		"$verifier" "$mutated_baseline" "$mutated_probe" \
		>"$work/$name.log" 2>&1
	then
		echo "FAIL ucode-allocation v6 runtime mutation passed: $name" >&2
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

sed "s/require_event_count rog5_ucode_kernel_new 3 'kernel GEM new'/require_event_count rog5_ucode_kernel_new 2 'kernel GEM new'/" \
	"$probe" >"$work/two-kernel-news.sh"
expect_rejected two-kernel-news "$baseline" "$work/two-kernel-news.sh"

sed "s/require_event_count rog5_ucode_get_vaddr 1 'public CPU vmap wrapper'/require_event_count rog5_ucode_get_vaddr 4 'CPU vmap'/" \
	"$probe" >"$work/rejected-wrapper-oracle.sh"
expect_rejected rejected-wrapper-oracle "$baseline" \
	"$work/rejected-wrapper-oracle.sh"

sed '/p:rog5_ucode_v6\/rog5_ucode_kernel_new msm:msm_gem_kernel_new/d' \
	"$probe" >"$work/no-kernel-new-probe.sh"
expect_rejected no-kernel-new-probe "$baseline" \
	"$work/no-kernel-new-probe.sh"

sed '/p:rog5_ucode_v6\/rog5_ucode_kernel_put msm:msm_gem_kernel_put/d' \
	"$probe" >"$work/no-kernel-put-probe.sh"
expect_rejected no-kernel-put-probe "$baseline" \
	"$work/no-kernel-put-probe.sh"

sed '/cmp "$state_dir\/logical-objects" "$state_dir\/unpins"/d' "$probe" \
	>"$work/no-logical-object-set.sh"
expect_rejected no-logical-object-set "$baseline" \
	"$work/no-logical-object-set.sh"

sed '/cmp "$state_dir\/gem.before" "$state_dir\/gem.after"/d' "$probe" \
	>"$work/no-gem-snapshot.sh"
expect_rejected no-gem-snapshot "$baseline" "$work/no-gem-snapshot.sh"

sed '/p:rog5_ucode_v6\/rog5_ucode_scm_aperture qcom_scm_set_gpu_smmu_aperture/d' \
	"$probe" >"$work/no-scm-boundary.sh"
expect_rejected no-scm-boundary "$baseline" "$work/no-scm-boundary.sh"

sed 's/d222f3fe290ef0516ee0ec43082596bad2df0fcbc2e0bbb26987623cef90cf76/0222f3fe290ef0516ee0ec43082596bad2df0fcbc2e0bbb26987623cef90cf76/' \
	"$baseline" >"$work/wrong-sqe.sh"
expect_rejected wrong-sqe "$work/wrong-sqe.sh" "$probe"

sed 's/predecessor=v5_live_rejected_consumed/predecessor=v5_live_pending/' \
	"$baseline" >"$work/unconsumed-predecessor.sh"
expect_rejected unconsumed-predecessor "$work/unconsumed-predecessor.sh" \
	"$probe"

{
	printf 'systemctl reboot\n'
	cat "$probe"
} >"$work/reboot-bypass.sh"
expect_rejected reboot-bypass "$baseline" "$work/reboot-bypass.sh"

echo 'PASS A660 ucode-allocation v6 rejects unarmed or mixed modes, second open, wrong errno, unfiltered/incomplete traces, rejected wrapper oracle, missing logical/snapshot state, wrong predecessor/firmware, and reboot bypass'
