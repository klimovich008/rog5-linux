#!/bin/sh
set -eu

source_dir=${SOURCE_DIR:-}
[ -n "$source_dir" ] || {
	echo 'FAIL set SOURCE_DIR to the pinned v14 Linux source' >&2
	exit 1
}
repo=$(CDPATH= cd -- "$(dirname "$0")/../.." && pwd)
patch=$repo/patches/linux-7.1.4/0011-clk-guard-orphan-reparent-with-runtime-PM.patch
verifier=$repo/scripts/device/verify-clk-orphan-runtime-pm-patch.sh
expected_parent=6e40861cc51c067f9989c4513003e8fbd046c22f
expected_commit=d9ac316489f4258d389d6298659d5e9c22183400
expected_tree=c796deb1cc54e942f8bb46a2c76a7199e19e5c92
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

extract_function() {
	start=$1
	file=$2
	awk -v start="$start" '
		index($0, start) == 1 { found = 1 }
		found { print }
		found && /^}/ { exit }
	' "$file"
}

base_clk=$source_dir/drivers/clk/clk.c
patched_clk=$patched/drivers/clk/clk.c
base_core=$(extract_function \
	'static int __clk_core_init(struct clk_core *core)' "$base_clk")
patched_core=$(extract_function \
	'static int __clk_core_init(struct clk_core *core)' "$patched_clk")
base_orphans=$(extract_function \
	'clk_core_reparent_orphans_nolock(const struct clk_core *rog5_trigger)' \
	"$base_clk")
patched_orphans=$(extract_function \
	'clk_core_reparent_orphans_nolock(const struct clk_core *rog5_trigger)' \
	"$patched_clk")
base_rcg=$(extract_function \
	'static u8 clk_rcg2_get_parent(struct clk_hw *hw)' \
	"$source_dir/drivers/clk/qcom/clk-rcg2.c")
patched_rcg=$(extract_function \
	'static u8 clk_rcg2_get_parent(struct clk_hw *hw)' \
	"$patched/drivers/clk/qcom/clk-rcg2.c")

[ -n "$base_core" ] && [ -n "$patched_core" ]
[ "$base_orphans" = "$patched_orphans" ]
[ "$base_rcg" = "$patched_rcg" ]
[ "$(printf '%s\n' "$base_core" |
	grep -Fc 'ret = clk_pm_runtime_get(core);')" -eq 1 ]
[ "$(printf '%s\n' "$base_core" |
	grep -Fc 'clk_pm_runtime_put(core);')" -eq 1 ]
[ "$(printf '%s\n' "$patched_core" |
	grep -Fc 'ret = clk_pm_runtime_get_all();')" -eq 1 ]
[ "$(printf '%s\n' "$patched_core" |
	grep -Fc 'clk_pm_runtime_put_all();')" -eq 1 ]
! printf '%s\n' "$patched_core" | grep -Fq 'clk_pm_runtime_get(core)'
! printf '%s\n' "$patched_core" | grep -Fq 'clk_pm_runtime_put(core)'

[ "$(git -C "$patched" diff --name-only | wc -l)" -eq 1 ]
[ "$(git -C "$patched" diff --name-only)" = drivers/clk/clk.c ]

git -C "$patched" add drivers/clk/clk.c
[ "$(git -C "$patched" write-tree)" = "$expected_tree" ]
export GIT_AUTHOR_NAME='ROG5 Linux Project'
export GIT_AUTHOR_EMAIL='rog5-linux@localhost'
export GIT_COMMITTER_NAME=$GIT_AUTHOR_NAME
export GIT_COMMITTER_EMAIL=$GIT_AUTHOR_EMAIL
export GIT_AUTHOR_DATE='2026-07-25T12:00:00Z'
export GIT_COMMITTER_DATE=$GIT_AUTHOR_DATE
git -C "$patched" commit -q -s \
	-m 'clk: guard orphan reparenting with runtime PM' \
	-m 'Resume registered runtime-PM clock providers before taking the CCF
prepare lock, then release the references after unlocking.' \
	-m 'Apply the same ordering to both OF provider orphan-reparent paths.
This is an experimental partial backport of the March 2025 RFC.'
[ "$(git -C "$patched" rev-parse HEAD)" = "$expected_commit" ]

echo 'PASS CCF candidate preserves orphan/RCG behavior and deterministically moves runtime PM outside prepare_lock'
