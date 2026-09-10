#!/bin/sh
set -eu

base_source=${1:?usage: prepare-mainline-gpucc-diagnostic.sh BASE_SOURCE TARGET_SOURCE}
target_source=${2:?missing target source}
repo=$(CDPATH= cd -- "$(dirname "$0")/../.." && pwd)
patch=$repo/patches/linux-7.1.4/0005-gpucc-sm8350-add-attended-probe-trace.patch
verifier=$repo/scripts/device/verify-gpucc-sm8350-probe-trace-patch.sh
expected_base=7a5cef0db4795d9d453a12e0f61b5b7634fc4d40
expected_patched=86f3c68a666446d9bbcb9bd9f90df50f989ba8ea
expected_tree=e22549ee4d4d788b6898f374e8edecfc714797ac

[ -d "$base_source/.git" ] || {
	echo 'FAIL missing pinned Linux source' >&2
	exit 1
}
[ "$(git -C "$base_source" rev-parse HEAD)" = "$expected_base" ]
[ -z "$(git -C "$base_source" status --porcelain)" ]
[ ! -e "$target_source" ] || {
	echo 'FAIL target source path already exists' >&2
	exit 1
}
"$verifier" "$patch" "$base_source" >/dev/null

mkdir -p "$(dirname "$target_source")"
git clone -q --no-hardlinks "$base_source" "$target_source"
git -C "$target_source" checkout -q --detach "$expected_base"
git -C "$target_source" apply --check "$patch"
git -C "$target_source" apply "$patch"
git -C "$target_source" diff --check
git -C "$target_source" add drivers/clk/qcom/gpucc-sm8350.c
[ "$(git -C "$target_source" write-tree)" = "$expected_tree" ] || {
	echo 'FAIL patched GPUCC source tree hash mismatch' >&2
	exit 1
}

export GIT_AUTHOR_NAME='ROG5 Linux Project'
export GIT_AUTHOR_EMAIL='rog5-linux@localhost'
export GIT_COMMITTER_NAME=$GIT_AUTHOR_NAME
export GIT_COMMITTER_EMAIL=$GIT_AUTHOR_EMAIL
export GIT_AUTHOR_DATE='2026-07-25T00:00:00Z'
export GIT_COMMITTER_DATE=$GIT_AUTHOR_DATE
git -C "$target_source" commit -q \
	-m 'clk: qcom: trace attended SM8350 GPUCC probe'

[ "$(git -C "$target_source" rev-parse HEAD^)" = "$expected_base" ]
[ "$(git -C "$target_source" rev-parse HEAD)" = "$expected_patched" ]
[ "$(git -C "$target_source" rev-parse HEAD^{tree})" = "$expected_tree" ]
[ -z "$(git -C "$target_source" status --porcelain)" ]

printf 'base_commit=%s\n' "$expected_base"
printf 'patched_commit=%s\n' "$expected_patched"
printf 'patched_tree=%s\n' "$expected_tree"
sha256sum "$patch"
echo 'PASS deterministic Linux 7.1.4 GPUCC diagnostic source'
