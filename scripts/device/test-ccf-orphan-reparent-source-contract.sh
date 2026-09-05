#!/bin/sh
set -eu

source_dir=${SOURCE_DIR:-}
[ -n "$source_dir" ] || {
	echo 'FAIL set SOURCE_DIR to the pinned v11 Linux source' >&2
	exit 1
}
repo=$(CDPATH= cd -- "$(dirname "$0")/../.." && pwd)
patch=$repo/patches/linux-7.1.4/0008-clk-trace-attended-SM8350-GPUCC-orphan-reparent.patch
verifier=$repo/scripts/device/verify-ccf-orphan-reparent-trace-patch.sh
prepare=$repo/scripts/device/prepare-mainline-gpucc-orphan-diagnostic.sh
build=$repo/scripts/device/build-mainline-gpucc-orphan-diagnostic.sh
build_verifier=$repo/scripts/device/verify-mainline-gpucc-orphan-diagnostic-build.sh
compare=$repo/scripts/device/compare-mainline-gpucc-orphan-diagnostic-builds.sh
expected_parent=6eef0ab56609f5a5ee6d2de9807178daf1065fa7
expected_orphan=b2059b161861d6d7d1aeb9b7d93ad86b13d85048
expected_tree=040d5f9b7be022489079b2ea9cab20a04934d85f
stage=$(mktemp -d)
trap 'rm -rf "$stage"' EXIT INT TERM
patched=$stage/linux-7.1.4

[ -d "$source_dir/.git" ]
[ "$(git -C "$source_dir" rev-parse HEAD)" = "$expected_parent" ]
[ -z "$(git -C "$source_dir" status --porcelain)" ]
[ -r "$patch" ] && [ -x "$verifier" ]
for file in "$prepare" "$build" "$build_verifier" "$compare"; do
	[ -x "$file" ]
done
for file in "$prepare" "$build"; do
	grep -Fq "expected_orphan=$expected_orphan" "$file"
	grep -Fq "expected_tree=$expected_tree" "$file"
done
grep -Fq 'repro_source_dir=/root/src/linux-7.1.4' "$build"
grep -Fq \
	'repro_output_dir=/root/build/rog5-linux-7.1.4-network-root' "$build"
grep -Fq 'orphan_trace_patch_sha256=' "$build"
grep -Fq \
	'ORPHAN_TRACE_PATCH:-/workspace/repo/patches/linux-7.1.4/0008-clk-trace-attended-SM8350-GPUCC-orphan-reparent.patch' \
	"$build"
"$verifier" "$patch" "$source_dir" >/dev/null

git -c advice.detachedHead=false clone -q --shared "$source_dir" "$patched"
git -C "$patched" apply "$patch"
git -C "$patched" diff --check

extract_scan() {
	awk '
		/clk_core_reparent_orphans_nolock[(]/ { found = 1 }
		found { print }
		found && /^}/ { exit }
	' "$1/drivers/clk/clk.c"
}

base_scan=$(extract_scan "$source_dir")
patched_scan=$(extract_scan "$patched")
[ -n "$base_scan" ] && [ -n "$patched_scan" ]

assert_count_preserved() {
	operation=$1
	base_count=$(printf '%s\n' "$base_scan" | grep -Fc "$operation")
	patched_count=$(printf '%s\n' "$patched_scan" | grep -Fc "$operation")
	[ "$base_count" -eq 1 ] && [ "$patched_count" -eq "$base_count" ]
}

for operation in \
	'hlist_for_each_entry_safe(orphan, tmp2, &clk_orphan_list, child_node)' \
	'parent = __clk_init_parent(orphan)' \
	'__clk_set_parent_before(orphan, parent)' \
	'__clk_set_parent_after(orphan, parent, NULL)' \
	'__clk_recalc_accuracies(orphan)' \
	'__clk_recalc_rates(orphan, true, 0)' \
	'orphan->req_rate = orphan->rate'
do
	assert_count_preserved "$operation"
done

assert_order() {
	previous=0
	for operation in "$@"; do
		line=$(printf '%s\n' "$patched_scan" | grep -nF "$operation" |
			sed -n '1s/:.*//p')
		[ -n "$line" ] && [ "$line" -gt "$previous" ]
		previous=$line
	done
}

assert_order \
	'"orphan-scan-entry"' \
	'"orphan-parent-lookup-begin"' \
	'parent = __clk_init_parent(orphan)' \
	'"orphan-parent-lookup-complete"' \
	'"orphan-parent-resolved"' \
	'"orphan-set-parent-before-begin"' \
	'__clk_set_parent_before(orphan, parent)' \
	'"orphan-set-parent-before-complete"' \
	'"orphan-set-parent-after-begin"' \
	'__clk_set_parent_after(orphan, parent, NULL)' \
	'"orphan-set-parent-after-complete"' \
	'"orphan-accuracy-begin"' \
	'__clk_recalc_accuracies(orphan)' \
	'"orphan-accuracy-complete"' \
	'"orphan-rates-begin"' \
	'__clk_recalc_rates(orphan, true, 0)' \
	'"orphan-rates-complete"' \
	'orphan->req_rate = orphan->rate' \
	'"orphan-req-rate-complete"' \
	'"orphan-scan-complete"'

[ "$(printf '%s\n' "$patched_scan" |
	grep -Ec '^[[:space:]]*(break|continue|return)([[:space:];]|$)')" -eq 0 ]
[ "$(grep -Fc 'clk_core_reparent_orphans_nolock(core);' \
	"$patched/drivers/clk/clk.c")" -eq 1 ]
[ "$(grep -Fc 'clk_core_reparent_orphans_nolock(NULL);' \
	"$patched/drivers/clk/clk.c")" -eq 1 ]
[ "$(grep -Fc 'clk_core_reparent_orphans_nolock();' \
	"$patched/drivers/clk/clk.c")" -eq 0 ]

echo 'PASS per-orphan boundaries preserve exact list walk, parent lookup, reparent, recalculation, and req-rate operations'
