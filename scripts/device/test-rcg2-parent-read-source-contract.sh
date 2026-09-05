#!/bin/sh
set -eu

source_dir=${SOURCE_DIR:-}
[ -n "$source_dir" ] || {
	echo 'FAIL set SOURCE_DIR to the pinned v13 Linux source' >&2
	exit 1
}
repo=$(CDPATH= cd -- "$(dirname "$0")/../.." && pwd)
patch=$repo/patches/linux-7.1.4/0010-clk-qcom-trace-attended-SM8350-DISPCC-RCG-parent-read.patch
verifier=$repo/scripts/device/verify-rcg2-parent-read-trace-patch.sh
expected_parent=f7c0a9d067db77f05a40a5bc242c1e14ac297ac5
expected_commit=6e40861cc51c067f9989c4513003e8fbd046c22f
expected_tree=49ef6cb95768496b8f926b11e428ea224406464e
stage=$(mktemp -d)
trap 'rm -rf "$stage"' EXIT INT TERM
patched=$stage/linux-7.1.4

[ -d "$source_dir/.git" ]
[ "$(git -C "$source_dir" rev-parse HEAD)" = "$expected_parent" ]
[ -z "$(git -C "$source_dir" status --porcelain)" ]
[ -r "$patch" ] && [ -x "$verifier" ]
"$verifier" "$patch" "$source_dir" >/dev/null

git -c advice.detachedHead=false clone -q --shared "$source_dir" "$patched"
git -C "$patched" apply "$patch"
git -C "$patched" diff --check

extract_get_parent() {
	awk '
		/^static u8 clk_rcg2_get_parent[(]struct clk_hw [*]hw[)]/ {
			found = 1
		}
		found { print }
		found && /^}/ { exit }
	' "$1/drivers/clk/qcom/clk-rcg2.c"
}

base_function=$(extract_get_parent "$source_dir")
patched_function=$(extract_get_parent "$patched")
[ -n "$base_function" ] && [ -n "$patched_function" ]

read_call='ret = regmap_read(rcg->clkr.regmap, RCG_CFG_OFFSET(rcg), &cfg);'
[ "$(printf '%s\n' "$base_function" | grep -Fc "$read_call")" -eq 1 ]
[ "$(printf '%s\n' "$patched_function" | grep -Fc "$read_call")" -eq 1 ]

assert_order() {
	previous=0
	for operation in "$@"; do
		line=$(printf '%s\n' "$patched_function" | grep -nF "$operation" |
			sed -n '1s/:.*//p')
		[ -n "$line" ] && [ "$line" -gt "$previous" ]
		previous=$line
	done
}

assert_order \
	'clk_rcg2_rog5_parent_trace(hw, "parent-read-begin", 0);' \
	"$read_call" \
	'clk_rcg2_rog5_parent_trace(hw, "parent-read-complete", ret);' \
	'if (ret)' \
	'return __clk_rcg2_get_parent(hw, cfg);'

[ "$(grep -Fc '#define ROG5_CCF_ORPHAN_TRACE_LIMIT 2' \
	"$patched/drivers/clk/clk.c")" -eq 1 ]
[ "$(grep -Fc '#define ROG5_CCF_ORPHAN_TRACE_LIMIT 4' \
	"$patched/drivers/clk/clk.c")" -eq 0 ]
[ "$(git -C "$patched" diff -- drivers/clk/qcom/clk-rcg2.c |
	grep -Ec '^[+].*regmap_read')" -eq 0 ]
[ "$(git -C "$patched" diff -- drivers/clk/qcom/clk-rcg2.c |
	grep -Ec '^[-].*regmap_read')" -eq 0 ]

git -C "$patched" add drivers/clk/clk.c drivers/clk/qcom/clk-rcg2.c
[ "$(git -C "$patched" write-tree)" = "$expected_tree" ]
export GIT_AUTHOR_NAME='ROG5 Linux Project'
export GIT_AUTHOR_EMAIL='rog5-linux@localhost'
export GIT_COMMITTER_NAME=$GIT_AUTHOR_NAME
export GIT_COMMITTER_EMAIL=$GIT_AUTHOR_EMAIL
export GIT_AUTHOR_DATE='2026-07-25T08:00:00Z'
export GIT_COMMITTER_DATE=$GIT_AUTHOR_DATE
git -C "$patched" commit -q -s \
	-m 'clk: trace attended DISPCC RCG parent read' \
	-m 'Bracket the existing parent-selection regmap read only for the exact
SM8350 display pixel clock while the default-off diagnostic is active.' \
	-m 'Reduce the inherited orphan trace to the two entries already localized
by v13. Add no clock, register, runtime-PM, or hardware-control operation.'
[ "$(git -C "$patched" rev-parse HEAD)" = "$expected_commit" ]

echo 'PASS RCG2 trace preserves one parent regmap read and exact return behavior'
