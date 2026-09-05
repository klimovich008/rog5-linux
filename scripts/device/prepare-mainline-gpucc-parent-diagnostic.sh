#!/bin/sh
set -eu

base_source=${1:?usage: prepare-mainline-gpucc-parent-diagnostic.sh BASE_SOURCE TARGET_SOURCE}
target_source=${2:?missing target source}
repo=$(CDPATH= cd -- "$(dirname "$0")/../.." && pwd)
prepare_v12=$repo/scripts/device/prepare-mainline-gpucc-orphan-diagnostic.sh
patch=$repo/patches/linux-7.1.4/0009-clk-trace-attended-SM8350-GPUCC-orphan-parent-lookup.patch
verifier=$repo/scripts/device/verify-ccf-orphan-parent-trace-patch.sh
expected_base=7a5cef0db4795d9d453a12e0f61b5b7634fc4d40
expected_gpucc=86f3c68a666446d9bbcb9bd9f90df50f989ba8ea
expected_common=d4bb00313e92514f89bc0a9e7a7dffcb4884834f
expected_ccf=6eef0ab56609f5a5ee6d2de9807178daf1065fa7
expected_orphan=b2059b161861d6d7d1aeb9b7d93ad86b13d85048
expected_parent=f7c0a9d067db77f05a40a5bc242c1e14ac297ac5
expected_tree=adec6b40ce25145e3e18cd82a788aa458514017d

[ -x "$prepare_v12" ] && [ -x "$verifier" ] && [ -r "$patch" ]
"$prepare_v12" "$base_source" "$target_source" >/dev/null
[ "$(git -C "$target_source" rev-parse HEAD)" = "$expected_orphan" ]
[ -z "$(git -C "$target_source" status --porcelain)" ]
"$verifier" "$patch" "$target_source" >/dev/null

export GIT_AUTHOR_NAME='ROG5 Linux Project'
export GIT_AUTHOR_EMAIL='rog5-linux@localhost'
export GIT_COMMITTER_NAME=$GIT_AUTHOR_NAME
export GIT_COMMITTER_EMAIL=$GIT_AUTHOR_EMAIL
export GIT_AUTHOR_DATE='2026-07-25T06:00:00Z'
export GIT_COMMITTER_DATE=$GIT_AUTHOR_DATE

git -C "$target_source" apply --check "$patch"
git -C "$target_source" apply "$patch"
git -C "$target_source" diff --check
git -C "$target_source" add drivers/clk/clk.c
[ "$(git -C "$target_source" write-tree)" = "$expected_tree" ]
git -C "$target_source" commit -q -s \
	-m 'clk: trace attended orphan parent lookup' \
	-m 'Bracket the clock callback and generic parent-cache lookup only while the
bounded exact SM8350 GPUCC orphan diagnostic is active.' \
	-m 'Record parent shape and read-only provider runtime state without changing
clock or runtime-PM behavior.'

[ "$(git -C "$target_source" rev-parse HEAD^^^^^)" = "$expected_base" ]
[ "$(git -C "$target_source" rev-parse HEAD^^^^)" = "$expected_gpucc" ]
[ "$(git -C "$target_source" rev-parse HEAD^^^)" = "$expected_common" ]
[ "$(git -C "$target_source" rev-parse HEAD^^)" = "$expected_ccf" ]
[ "$(git -C "$target_source" rev-parse HEAD^)" = "$expected_orphan" ]
[ "$(git -C "$target_source" rev-parse HEAD)" = "$expected_parent" ]
[ "$(git -C "$target_source" rev-parse HEAD^{tree})" = "$expected_tree" ]
[ -z "$(git -C "$target_source" status --porcelain)" ]

printf 'base_commit=%s\n' "$expected_base"
printf 'gpucc_commit=%s\n' "$expected_gpucc"
printf 'common_commit=%s\n' "$expected_common"
printf 'ccf_commit=%s\n' "$expected_ccf"
printf 'orphan_commit=%s\n' "$expected_orphan"
printf 'parent_commit=%s\n' "$expected_parent"
printf 'parent_tree=%s\n' "$expected_tree"
sha256sum "$patch"
echo 'PASS deterministic Linux 7.1.4 GPUCC orphan-parent diagnostic source'
