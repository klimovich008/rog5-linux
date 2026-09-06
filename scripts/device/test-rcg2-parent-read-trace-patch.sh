#!/bin/sh
set -eu

repo=$(CDPATH= cd -- "$(dirname "$0")/../.." && pwd)
patch=$repo/patches/linux-7.1.4/0010-clk-qcom-trace-attended-SM8350-DISPCC-RCG-parent-read.patch
verifier=$repo/scripts/device/verify-rcg2-parent-read-trace-patch.sh
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
		echo "FAIL RCG2 trace verifier accepted $label mutation" >&2
		exit 1
	fi
}

sed '/"parent-read-begin"/d' "$patch" >"$stage/incomplete.patch"
reject_mutation incomplete "$stage/incomplete.patch"

sed 's/bool, 0400/bool, 0644/' "$patch" >"$stage/writable.patch"
reject_mutation writable "$stage/writable.patch"

sed 's/rog5_rcg2_parent_trace &&/true \&\&/' "$patch" \
	>"$stage/broad-trace.patch"
reject_mutation broad-trace "$stage/broad-trace.patch"

sed 's/disp_cc_mdss_pclk0_clk_src/disp_cc_mdss_pclk1_clk_src/' "$patch" \
	>"$stage/wrong-clock.patch"
reject_mutation wrong-clock "$stage/wrong-clock.patch"

sed 's/msleep(100);/pm_runtime_resume_and_get(NULL);/' "$patch" \
	>"$stage/runtime-control.patch"
reject_mutation runtime-control "$stage/runtime-control.patch"

sed 's/+#[[:space:]]*define ROG5_CCF_ORPHAN_TRACE_LIMIT 2/+#define ROG5_CCF_ORPHAN_TRACE_LIMIT 4/' \
	"$patch" >"$stage/wide-orphan-scan.patch"
reject_mutation wide-orphan-scan "$stage/wide-orphan-scan.patch"

echo 'PASS RCG2 verifier rejects missing, writable, broad, wrong-clock, PM-control, and wide-scan mutations'
