#!/bin/sh
set -eu

source_dir=${SOURCE_DIR:-}
[ -n "$source_dir" ] || {
	echo 'FAIL set SOURCE_DIR to the pinned v12 Linux source' >&2
	exit 1
}
repo=$(CDPATH= cd -- "$(dirname "$0")/../.." && pwd)
patch=$repo/patches/linux-7.1.4/0009-clk-trace-attended-SM8350-GPUCC-orphan-parent-lookup.patch
verifier=$repo/scripts/device/verify-ccf-orphan-parent-trace-patch.sh
expected_parent=b2059b161861d6d7d1aeb9b7d93ad86b13d85048
expected_commit=f7c0a9d067db77f05a40a5bc242c1e14ac297ac5
expected_tree=adec6b40ce25145e3e18cd82a788aa458514017d
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

extract_init_parent() {
	awk '
		/__clk_init_parent[(]struct clk_core [*]core/ { found = 1 }
		found { print }
		found && /^}/ { exit }
	' "$1/drivers/clk/clk.c"
}

base_function=$(extract_init_parent "$source_dir")
patched_function=$(extract_init_parent "$patched")
[ -n "$base_function" ] && [ -n "$patched_function" ]

for operation in \
	'core->num_parents > 1 && core->ops->get_parent' \
	'index = core->ops->get_parent(core->hw)' \
	'clk_core_get_parent_by_index(core, index)'
do
	[ "$(printf '%s\n' "$base_function" | grep -Fc "$operation")" -eq 1 ]
	[ "$(printf '%s\n' "$patched_function" | grep -Fc "$operation")" -eq 1 ]
done

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
	'"orphan-parent-shape"' \
	'"orphan-runtime-state"' \
	'core->num_parents > 1 && core->ops->get_parent' \
	'"orphan-get-parent-begin"' \
	'index = core->ops->get_parent(core->hw)' \
	'"orphan-get-parent-complete"' \
	'"orphan-parent-cache-begin"' \
	'parent = clk_core_get_parent_by_index(core, index)' \
	'"orphan-parent-cache-complete"' \
	'return parent'

[ "$(printf '%s\n' "$patched_function" |
	grep -Ec '^[[:space:]]*(break|continue)([[:space:];]|$)')" -eq 0 ]
[ "$(grep -Fc 'parent = __clk_init_parent(orphan, rog5_trigger,' \
	"$patched/drivers/clk/clk.c")" -eq 1 ]
[ "$(grep -Fc 'core->parent = __clk_init_parent(core, NULL, false);' \
	"$patched/drivers/clk/clk.c")" -eq 1 ]
[ "$(git -C "$patched" diff -- drivers/clk/clk.c |
	grep -Ec '^[+][[:space:]]+parent = core->parent;$')" -eq 1 ]
[ "$(grep -Fc '__clk_init_parent(orphan);' \
	"$patched/drivers/clk/clk.c")" -eq 0 ]
[ "$(grep -Fc '__clk_init_parent(core);' \
	"$patched/drivers/clk/clk.c")" -eq 0 ]
[ "$(git -C "$patched" diff -- drivers/clk/clk.c |
	grep -Ec '^[+].*pm_runtime_status_suspended[(]core->dev[)]')" -eq 1 ]
[ "$(git -C "$patched" diff -- drivers/clk/clk.c |
	grep -Ec '^[+].*pm_runtime_active[(]core->dev[)]')" -eq 1 ]

git -C "$patched" add drivers/clk/clk.c
[ "$(git -C "$patched" write-tree)" = "$expected_tree" ]
export GIT_AUTHOR_NAME='ROG5 Linux Project'
export GIT_AUTHOR_EMAIL='rog5-linux@localhost'
export GIT_COMMITTER_NAME=$GIT_AUTHOR_NAME
export GIT_COMMITTER_EMAIL=$GIT_AUTHOR_EMAIL
export GIT_AUTHOR_DATE='2026-07-25T06:00:00Z'
export GIT_COMMITTER_DATE=$GIT_AUTHOR_DATE
git -C "$patched" commit -q -s \
	-m 'clk: trace attended orphan parent lookup' \
	-m 'Bracket the clock callback and generic parent-cache lookup only while the
bounded exact SM8350 GPUCC orphan diagnostic is active.' \
	-m 'Record parent shape and read-only provider runtime state without changing
clock or runtime-PM behavior.'
[ "$(git -C "$patched" rev-parse HEAD)" = "$expected_commit" ]

echo 'PASS inner markers preserve one callback and one parent-cache lookup in exact source order'
