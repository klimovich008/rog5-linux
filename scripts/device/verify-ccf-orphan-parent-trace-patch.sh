#!/bin/sh
set -eu

patch=${1:?usage: verify-ccf-orphan-parent-trace-patch.sh PATCH [PINNED_V12_SOURCE]}
source_dir=${2:-}
expected_sha=6531645c80d9e07e40baf7d8af8ba6732f5ddfc75a3255a6dd75c8c3b8f7b5b5
expected_parent=b2059b161861d6d7d1aeb9b7d93ad86b13d85048

[ -r "$patch" ]
patch=$(CDPATH= cd -- "$(dirname "$patch")" && pwd)/$(basename "$patch")
if [ "${ALLOW_UNPINNED_PATCH:-0}" != 1 ]; then
	[ "$(sha256sum "$patch" | cut -d ' ' -f 1)" = "$expected_sha" ]
fi
[ "$(git apply --numstat "$patch" | wc -l)" -eq 1 ]
git apply --numstat "$patch" |
	grep -Eq '^[0-9]+[[:space:]]+[0-9]+[[:space:]]+drivers/clk/clk[.]c$'

for contract in \
	'clk_rog5_orphan_runtime_state(const struct clk_core *core)' \
	'pm_runtime_status_suspended(core->dev)' \
	'pm_runtime_active(core->dev)' \
	'__clk_init_parent(struct clk_core *core,' \
	'const struct clk_core *rog5_trigger, bool rog5_trace)' \
	'parent = __clk_init_parent(orphan, rog5_trigger,' \
	'rog5_trace_this);' \
	'core->parent = __clk_init_parent(core, NULL, false);' \
	'parent = core->parent;'
do
	grep -Fq "$contract" "$patch"
done

for phase in \
	orphan-parent-shape \
	orphan-runtime-state \
	orphan-get-parent-begin \
	orphan-get-parent-complete \
	orphan-parent-cache-begin \
	orphan-parent-cache-complete
do
	[ "$(grep -Fc "\"$phase\"" "$patch")" -eq 1 ]
done

added=$(sed -n 's/^+//p' "$patch")
removed=$(sed -n 's/^-//p' "$patch")

[ "$(grep -Fc 'index = core->ops->get_parent(core->hw)' "$patch")" -eq 1 ]
[ "$(printf '%s\n' "$added" |
	grep -Fc 'index = core->ops->get_parent(core->hw)')" -eq 0 ]
[ "$(printf '%s\n' "$removed" |
	grep -Fc 'index = core->ops->get_parent(core->hw)')" -eq 0 ]
[ "$(printf '%s\n' "$added" |
	grep -Fc 'parent = clk_core_get_parent_by_index(core, index)')" -eq 1 ]
[ "$(printf '%s\n' "$removed" |
	grep -Fc 'return clk_core_get_parent_by_index(core, index)')" -eq 1 ]
[ "$(printf '%s\n' "$added" |
	grep -Fc 'return parent')" -eq 1 ]
[ "$(printf '%s\n' "$added" |
	grep -Fc 'core->num_parents > 1 && core->ops->get_parent')" -eq 1 ]

if printf '%s\n' "$added" |
	grep -Eq 'regmap_(read|write|update_bits)|read[ql]|write[ql]|clk_(prepare_)?enable|regulator_(enable|set_voltage)|reset_control_|gdsc_(enable|disable)|pm_runtime_(get|put|resume|suspend|enable|disable|forbid|allow|set_active|set_suspended)|fastboot|/dev/|mount[[:space:]]|status[[:space:]]*=[[:space:]]*"okay"'
then
	echo 'FAIL parent trace patch adds hardware/runtime-PM control or persistent I/O' >&2
	exit 1
fi

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

echo 'PASS orphan parent trace is exact-scan-gated, operation-preserving, read-only, and hardware-control-free'
