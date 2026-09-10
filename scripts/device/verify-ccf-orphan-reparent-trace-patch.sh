#!/bin/sh
set -eu

patch=${1:?usage: verify-ccf-orphan-reparent-trace-patch.sh PATCH [PINNED_V11_SOURCE]}
source_dir=${2:-}
expected_sha=bc026e783fe3b7f1f15cb0e3ac6ca914d4b45897da07db0f887565b1722172e6
expected_parent=6eef0ab56609f5a5ee6d2de9807178daf1065fa7

[ -r "$patch" ]
patch=$(CDPATH= cd -- "$(dirname "$patch")" && pwd)/$(basename "$patch")
if [ "${ALLOW_UNPINNED_PATCH:-0}" != 1 ]; then
	[ "$(sha256sum "$patch" | cut -d ' ' -f 1)" = "$expected_sha" ]
fi
[ "$(git apply --numstat "$patch" | wc -l)" -eq 1 ]
git apply --numstat "$patch" |
	grep -Eq '^[0-9]+[[:space:]]+[0-9]+[[:space:]]+drivers/clk/clk[.]c$'

grep -Fq '#define ROG5_CCF_ORPHAN_TRACE_LIMIT 4' "$patch"
grep -Fq \
	'static void clk_rog5_orphan_trace(const struct clk_core *trigger,' \
	"$patch"
grep -Fq \
	'clk_core_reparent_orphans_nolock(const struct clk_core *rog5_trigger)' \
	"$patch"
grep -Fq \
	'clk_rog5_register_trace_enabled(rog5_trigger ?' "$patch"
grep -Fq \
	'rog5_trace_count < ROG5_CCF_ORPHAN_TRACE_LIMIT' "$patch"
[ "$(grep -Ec '^[+]	clk_core_reparent_orphans_nolock[(]core[)];$' \
	"$patch")" -eq 1 ]
[ "$(grep -Ec '^[+]	clk_core_reparent_orphans_nolock[(]NULL[)];$' \
	"$patch")" -eq 1 ]

for phase in \
	orphan-scan-entry \
	orphan-parent-lookup-begin \
	orphan-parent-lookup-complete \
	orphan-parent-resolved \
	orphan-set-parent-before-begin \
	orphan-set-parent-before-complete \
	orphan-set-parent-after-begin \
	orphan-set-parent-after-complete \
	orphan-accuracy-begin \
	orphan-accuracy-complete \
	orphan-rates-begin \
	orphan-rates-complete \
	orphan-req-rate-complete \
	orphan-scan-complete
do
	[ "$(grep -Fc "\"$phase\"" "$patch")" -eq 1 ]
done

added=$(sed -n 's/^+//p' "$patch")
if printf '%s\n' "$added" |
	grep -Eq 'regmap_(write|update_bits)|write[ql]|clk_(prepare_)?enable|regulator_(enable|set_voltage)|reset_control_|gdsc_(enable|disable)|pm_runtime_(enable|disable)|fastboot|/dev/|mount[[:space:]]|status[[:space:]]*=[[:space:]]*"okay"'
then
	echo 'FAIL orphan trace patch adds hardware control or persistent I/O' >&2
	exit 1
fi

removed=$(sed -n 's/^-//p' "$patch")
[ "$(printf '%s\n' "$added" |
	grep -Fc 'parent = __clk_init_parent(orphan)')" -eq 1 ]
[ "$(printf '%s\n' "$removed" |
	grep -Fc 'parent = __clk_init_parent(orphan)')" -eq 1 ]
for operation in \
	'__clk_set_parent_before(orphan, parent)' \
	'__clk_set_parent_after(orphan, parent, NULL)' \
	'__clk_recalc_accuracies(orphan)' \
	'__clk_recalc_rates(orphan, true, 0)' \
	'orphan->req_rate = orphan->rate'
do
	[ "$(printf '%s\n' "$added" | grep -Fc "$operation")" -eq 0 ]
done

if [ -n "$source_dir" ]; then
	[ -d "$source_dir/.git" ]
	[ "$(git -C "$source_dir" rev-parse HEAD)" = "$expected_parent" ]
	[ -z "$(git -C "$source_dir" status --porcelain)" ]
	git -C "$source_dir" apply --check "$patch"
	checkpatch=$source_dir/scripts/checkpatch.pl
	if [ -x "$checkpatch" ]; then
		"$checkpatch" --no-tree --strict --terse "$patch" >/dev/null
	fi
fi

echo 'PASS orphan trace is exact-device-gated, bounded, operation-preserving, and hardware-control-free'
