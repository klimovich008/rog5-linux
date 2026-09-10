#!/bin/sh
set -eu

repo=$(CDPATH= cd -- "$(dirname "$0")/../.." && pwd)
patch=$repo/patches/linux-7.1.4/0009-clk-trace-attended-SM8350-GPUCC-orphan-parent-lookup.patch
verifier=$repo/scripts/device/verify-ccf-orphan-parent-trace-patch.sh
source_dir=${SOURCE_DIR:-}
stage=$(mktemp -d)
trap 'rm -rf "$stage"' EXIT INT TERM

[ -r "$patch" ] && [ -x "$verifier" ]
"$verifier" "$patch" "$source_dir" >/dev/null

reject_mutation() {
	label=$1
	mutant=$2
	if ALLOW_UNPINNED_PATCH=1 "$verifier" "$mutant" "$source_dir" \
		>"$stage/$label.output" 2>&1
	then
		echo "FAIL parent trace verifier accepted $label mutation" >&2
		exit 1
	fi
}

sed '/"orphan-get-parent-begin"/d' "$patch" \
	>"$stage/incomplete.patch"
reject_mutation incomplete "$stage/incomplete.patch"

sed 's/pm_runtime_active(core->dev)/pm_runtime_resume_and_get(core->dev)/' \
	"$patch" >"$stage/runtime-control.patch"
reject_mutation runtime-control "$stage/runtime-control.patch"

sed 's/__clk_init_parent(core, NULL, false)/__clk_init_parent(core, core, true)/' \
	"$patch" >"$stage/broad-core-trace.patch"
reject_mutation broad-core-trace "$stage/broad-core-trace.patch"

sed '/^ 		index = core->ops->get_parent(core->hw);$/p' "$patch" \
	>"$stage/duplicate-callback.patch"
reject_mutation duplicate-callback "$stage/duplicate-callback.patch"

sed '/^[+]	parent = clk_core_get_parent_by_index(core, index);$/p' "$patch" \
	>"$stage/duplicate-cache-lookup.patch"
reject_mutation duplicate-cache-lookup "$stage/duplicate-cache-lookup.patch"

sed 's/clk_rog5_orphan_trace(rog5_trigger/clk_prepare_enable(NULL); clk_rog5_orphan_trace(rog5_trigger/' \
	"$patch" >"$stage/hardware-control.patch"
reject_mutation hardware-control "$stage/hardware-control.patch"

echo 'PASS parent trace verifier rejects missing phases, PM/hardware control, broad tracing, and duplicate lookups'
