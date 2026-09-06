#!/bin/sh
set -eu

base_source=${1:?usage: prepare-mainline-gpucc-common-diagnostic.sh BASE_SOURCE TARGET_SOURCE}
target_source=${2:?missing target source}
repo=$(CDPATH= cd -- "$(dirname "$0")/../.." && pwd)
gpucc_patch=$repo/patches/linux-7.1.4/0005-gpucc-sm8350-add-attended-probe-trace.patch
common_patch=$repo/patches/linux-7.1.4/0006-qcom-cc-add-attended-registration-trace.patch
gpucc_verifier=$repo/scripts/device/verify-gpucc-sm8350-probe-trace-patch.sh
common_verifier=$repo/scripts/device/verify-qcom-cc-registration-trace-patch.sh
expected_base=7a5cef0db4795d9d453a12e0f61b5b7634fc4d40
expected_gpucc=86f3c68a666446d9bbcb9bd9f90df50f989ba8ea
expected_gpucc_tree=e22549ee4d4d788b6898f374e8edecfc714797ac
expected_common=d4bb00313e92514f89bc0a9e7a7dffcb4884834f
expected_common_tree=3b185820802b882d05830b9c6aee35bff984e07b

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
"$gpucc_verifier" "$gpucc_patch" "$base_source" >/dev/null
"$common_verifier" "$common_patch" "$gpucc_patch" "$base_source" >/dev/null

mkdir -p "$(dirname "$target_source")"
git clone -q --no-hardlinks "$base_source" "$target_source"
git -C "$target_source" checkout -q --detach "$expected_base"

export GIT_AUTHOR_NAME='ROG5 Linux Project'
export GIT_AUTHOR_EMAIL='rog5-linux@localhost'
export GIT_COMMITTER_NAME=$GIT_AUTHOR_NAME
export GIT_COMMITTER_EMAIL=$GIT_AUTHOR_EMAIL

git -C "$target_source" apply --check "$gpucc_patch"
git -C "$target_source" apply "$gpucc_patch"
git -C "$target_source" diff --check
git -C "$target_source" add drivers/clk/qcom/gpucc-sm8350.c
[ "$(git -C "$target_source" write-tree)" = "$expected_gpucc_tree" ]
export GIT_AUTHOR_DATE='2026-07-25T00:00:00Z'
export GIT_COMMITTER_DATE=$GIT_AUTHOR_DATE
git -C "$target_source" commit -q \
	-m 'clk: qcom: trace attended SM8350 GPUCC probe'
[ "$(git -C "$target_source" rev-parse HEAD)" = "$expected_gpucc" ]

git -C "$target_source" apply --check "$common_patch"
git -C "$target_source" apply "$common_patch"
git -C "$target_source" diff --check
git -C "$target_source" add drivers/clk/qcom/common.c
[ "$(git -C "$target_source" write-tree)" = "$expected_common_tree" ]
export GIT_AUTHOR_DATE='2026-07-25T01:00:00Z'
export GIT_COMMITTER_DATE=$GIT_AUTHOR_DATE
git -C "$target_source" commit -q -s \
	-m 'clk: qcom: trace attended common-clock registration' \
	-m 'Add a read-only, default-off core parameter which traces only the
SM8350 GPU clock controller through each common registration phase.' \
	-m 'A diagnostic-only 100 ms settle after each marker lets the USB log
follower deliver the last completed phase before a hardware stall. No
register, clock, reset, regulator, storage, or persistent-state operation
is added.'

[ "$(git -C "$target_source" rev-parse HEAD^^)" = "$expected_base" ]
[ "$(git -C "$target_source" rev-parse HEAD^)" = "$expected_gpucc" ]
[ "$(git -C "$target_source" rev-parse HEAD)" = "$expected_common" ]
[ "$(git -C "$target_source" rev-parse HEAD^{tree})" = \
	"$expected_common_tree" ]
[ -z "$(git -C "$target_source" status --porcelain)" ]

printf 'base_commit=%s\n' "$expected_base"
printf 'gpucc_commit=%s\n' "$expected_gpucc"
printf 'common_commit=%s\n' "$expected_common"
printf 'common_tree=%s\n' "$expected_common_tree"
sha256sum "$gpucc_patch" "$common_patch"
echo 'PASS deterministic Linux 7.1.4 GPUCC/common-clock diagnostic source'
