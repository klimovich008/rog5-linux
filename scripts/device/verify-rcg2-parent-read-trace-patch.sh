#!/bin/sh
set -eu

patch=${1:?usage: verify-rcg2-parent-read-trace-patch.sh PATCH [PINNED_V13_SOURCE]}
source_dir=${2:-}
expected_sha=ac7975bf5f4cb2791f45a2fe8b5b811c7e60fd4692f8aff4cd71a2f2150fa3c6
expected_parent=f7c0a9d067db77f05a40a5bc242c1e14ac297ac5

[ -r "$patch" ]
patch=$(CDPATH= cd -- "$(dirname "$patch")" && pwd)/$(basename "$patch")
if [ "${ALLOW_UNPINNED_PATCH:-0}" != 1 ]; then
	[ "$(sha256sum "$patch" | cut -d ' ' -f 1)" = "$expected_sha" ]
fi
[ "$(git apply --numstat "$patch" | wc -l)" -eq 2 ]
git apply --numstat "$patch" |
	grep -Eq '^[0-9]+[[:space:]]+[0-9]+[[:space:]]+drivers/clk/clk[.]c$'
git apply --numstat "$patch" |
	grep -Eq '^[0-9]+[[:space:]]+[0-9]+[[:space:]]+drivers/clk/qcom/clk-rcg2[.]c$'

for contract in \
	'core_param(rog5_rcg2_parent_trace, rog5_rcg2_parent_trace, bool, 0400);' \
	'rog5_rcg2_parent_trace &&' \
	'!strcmp(clk_hw_get_name(hw), "disp_cc_mdss_pclk0_clk_src")' \
	'ROG5 RCG2 diagnostic: phase=%s clock=%s ret=%d' \
	'"parent-read-begin"' \
	'"parent-read-complete"' \
	'msleep(100);'
do
	grep -Fq "$contract" "$patch"
done

[ "$(grep -Fc '"parent-read-begin"' "$patch")" -eq 1 ]
[ "$(grep -Fc '"parent-read-complete"' "$patch")" -eq 1 ]
[ "$(grep -Fc \
	'core_param(rog5_rcg2_parent_trace, rog5_rcg2_parent_trace, bool, 0400);' \
	"$patch")" -eq 1 ]
[ "$(grep -Ec '^-#define ROG5_CCF_ORPHAN_TRACE_LIMIT 4$' "$patch")" -eq 1 ]
[ "$(grep -Ec '^[+]#define ROG5_CCF_ORPHAN_TRACE_LIMIT 2$' "$patch")" -eq 1 ]

added=$(sed -n 's/^+//p' "$patch")
if printf '%s\n' "$added" |
	grep -Eq 'regmap_(read|write|update_bits)|read[ql]|write[ql]|clk_(prepare_)?enable|regulator_(enable|set_voltage)|reset_control_|gdsc_(enable|disable)|pm_runtime_(get|put|resume|suspend|enable|disable|forbid|allow|set_active|set_suspended)|fastboot|/dev/|mount[[:space:]]|status[[:space:]]*=[[:space:]]*"okay"'
then
	echo 'FAIL RCG2 trace patch adds hardware/runtime-PM control or persistent I/O' >&2
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

echo 'PASS RCG2 parent-read trace is default-off, exact-clock-gated, bounded, and hardware-control-free'
