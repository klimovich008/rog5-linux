#!/bin/sh
set -eu

repo=$(CDPATH= cd -- "$(dirname "$0")/../.." && pwd)
patch=$repo/patches/linux-7.1.4/0008-clk-trace-attended-SM8350-GPUCC-orphan-reparent.patch
verifier=$repo/scripts/device/verify-ccf-orphan-reparent-trace-patch.sh
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
		echo "FAIL orphan trace verifier accepted $label mutation" >&2
		exit 1
	fi
}

sed 's/ROG5_CCF_ORPHAN_TRACE_LIMIT 4/ROG5_CCF_ORPHAN_TRACE_LIMIT 64/' \
	"$patch" >"$stage/unbounded-count.patch"
reject_mutation unbounded-count "$stage/unbounded-count.patch"

sed 's/clk_rog5_register_trace_enabled(rog5_trigger ?/true || (rog5_trigger ?/' \
	"$patch" >"$stage/broad.patch"
reject_mutation broad "$stage/broad.patch"

sed 's/rog5_trace_count < ROG5_CCF_ORPHAN_TRACE_LIMIT/true/' \
	"$patch" >"$stage/no-runtime-bound.patch"
reject_mutation no-runtime-bound "$stage/no-runtime-bound.patch"

sed '/"orphan-parent-lookup-begin"/d' "$patch" \
	>"$stage/incomplete.patch"
reject_mutation incomplete "$stage/incomplete.patch"

sed 's/clk_rog5_orphan_trace(rog5_trigger/clk_prepare_enable(NULL); clk_rog5_orphan_trace(rog5_trigger/' \
	"$patch" >"$stage/hardware-control.patch"
reject_mutation hardware-control "$stage/hardware-control.patch"

sed '/^[+]	clk_core_reparent_orphans_nolock(core);$/p' "$patch" \
	>"$stage/duplicate-registration-call.patch"
reject_mutation duplicate-registration-call \
	"$stage/duplicate-registration-call.patch"

sed 's/clk_core_reparent_orphans_nolock(NULL);/clk_core_reparent_orphans_nolock(core);/' \
	"$patch" >"$stage/provider-trigger.patch"
reject_mutation provider-trigger "$stage/provider-trigger.patch"

echo 'PASS orphan trace verifier rejects broad, unbounded, incomplete, hardware-changing, duplicate-call, and provider-triggered mutations'
