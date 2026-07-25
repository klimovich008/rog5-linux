#!/bin/sh
set -eu

base_source=${1:?usage: prepare-mainline-gpucc-orphan-diagnostic.sh BASE_SOURCE TARGET_SOURCE}
target_source=${2:?missing target source}
repo=$(CDPATH= cd -- "$(dirname "$0")/../.." && pwd)
prepare_v11=$repo/scripts/device/prepare-mainline-gpucc-ccf-diagnostic.sh
patch=$repo/patches/linux-7.1.4/0008-clk-trace-attended-SM8350-GPUCC-orphan-reparent.patch
verifier=$repo/scripts/device/verify-ccf-orphan-reparent-trace-patch.sh
expected_base=7a5cef0db4795d9d453a12e0f61b5b7634fc4d40
expected_gpucc=86f3c68a666446d9bbcb9bd9f90df50f989ba8ea
expected_common=d4bb00313e92514f89bc0a9e7a7dffcb4884834f
expected_ccf=6eef0ab56609f5a5ee6d2de9807178daf1065fa7
expected_orphan=b2059b161861d6d7d1aeb9b7d93ad86b13d85048
expected_tree=040d5f9b7be022489079b2ea9cab20a04934d85f

[ -x "$prepare_v11" ] && [ -x "$verifier" ] && [ -r "$patch" ]
"$prepare_v11" "$base_source" "$target_source" >/dev/null
[ "$(git -C "$target_source" rev-parse HEAD)" = "$expected_ccf" ]
[ -z "$(git -C "$target_source" status --porcelain)" ]
"$verifier" "$patch" "$target_source" >/dev/null

export GIT_AUTHOR_NAME='ROG5 Linux Project'
export GIT_AUTHOR_EMAIL='rog5-linux@localhost'
export GIT_COMMITTER_NAME=$GIT_AUTHOR_NAME
export GIT_COMMITTER_EMAIL=$GIT_AUTHOR_EMAIL
export GIT_AUTHOR_DATE='2026-07-25T03:00:00Z'
export GIT_COMMITTER_DATE=$GIT_AUTHOR_DATE

git -C "$target_source" apply --check "$patch"
git -C "$target_source" apply "$patch"
git -C "$target_source" diff --check
git -C "$target_source" add drivers/clk/clk.c
[ "$(git -C "$target_source" write-tree)" = "$expected_tree" ]
git -C "$target_source" commit -q -s \
	-m 'clk: trace attended CCF orphan reparenting' \
	-m 'Bound diagnostic markers to the first four orphan clocks while an exact
SM8350 GPUCC registration is active.' \
	-m 'Bracket parent lookup, topology migration, accuracy and rate recalculation
without adding or removing an existing operation.'

[ "$(git -C "$target_source" rev-parse HEAD^^^^)" = "$expected_base" ]
[ "$(git -C "$target_source" rev-parse HEAD^^^)" = "$expected_gpucc" ]
[ "$(git -C "$target_source" rev-parse HEAD^^)" = "$expected_common" ]
[ "$(git -C "$target_source" rev-parse HEAD^)" = "$expected_ccf" ]
[ "$(git -C "$target_source" rev-parse HEAD)" = "$expected_orphan" ]
[ "$(git -C "$target_source" rev-parse HEAD^{tree})" = "$expected_tree" ]
[ -z "$(git -C "$target_source" status --porcelain)" ]

printf 'base_commit=%s\n' "$expected_base"
printf 'gpucc_commit=%s\n' "$expected_gpucc"
printf 'common_commit=%s\n' "$expected_common"
printf 'ccf_commit=%s\n' "$expected_ccf"
printf 'orphan_commit=%s\n' "$expected_orphan"
printf 'orphan_tree=%s\n' "$expected_tree"
sha256sum "$patch"
echo 'PASS deterministic Linux 7.1.4 GPUCC orphan-reparent diagnostic source'
