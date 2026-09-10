#!/bin/sh
set -eu

base_source=${1:?usage: prepare-mainline-gpucc-ccf-diagnostic.sh BASE_SOURCE TARGET_SOURCE}
target_source=${2:?missing target source}
repo=$(CDPATH= cd -- "$(dirname "$0")/../.." && pwd)
prepare_v10=$repo/scripts/device/prepare-mainline-gpucc-common-diagnostic.sh
patch=$repo/patches/linux-7.1.4/0007-clk-trace-attended-SM8350-GPUCC-CCF-registration.patch
verifier=$repo/scripts/device/verify-ccf-registration-trace-patch.sh
expected_base=7a5cef0db4795d9d453a12e0f61b5b7634fc4d40
expected_gpucc=86f3c68a666446d9bbcb9bd9f90df50f989ba8ea
expected_common=d4bb00313e92514f89bc0a9e7a7dffcb4884834f
expected_ccf=6eef0ab56609f5a5ee6d2de9807178daf1065fa7
expected_tree=743a976fd13c1a5c30d93c7dac9b9b4d1cbc3b11

[ -x "$prepare_v10" ] && [ -x "$verifier" ] && [ -r "$patch" ]
"$prepare_v10" "$base_source" "$target_source" >/dev/null
[ "$(git -C "$target_source" rev-parse HEAD)" = "$expected_common" ]
[ -z "$(git -C "$target_source" status --porcelain)" ]
"$verifier" "$patch" "$target_source" >/dev/null

export GIT_AUTHOR_NAME='ROG5 Linux Project'
export GIT_AUTHOR_EMAIL='rog5-linux@localhost'
export GIT_COMMITTER_NAME=$GIT_AUTHOR_NAME
export GIT_COMMITTER_EMAIL=$GIT_AUTHOR_EMAIL
export GIT_AUTHOR_DATE='2026-07-25T02:00:00Z'
export GIT_COMMITTER_DATE=$GIT_AUTHOR_DATE

git -C "$target_source" apply --check "$patch"
git -C "$target_source" apply "$patch"
git -C "$target_source" diff --check
git -C "$target_source" add \
	drivers/clk/clk.c \
	drivers/clk/qcom/clk-regmap.c \
	drivers/clk/qcom/common.c \
	drivers/clk/qcom/common.h
[ "$(git -C "$target_source" write-tree)" = "$expected_tree" ]
git -C "$target_source" commit -q -s \
	-m 'clk: trace attended SM8350 GPUCC CCF registration' \
	-m 'Add a read-only, default-off trace around the Qualcomm regmap
wrapper and generic CCF registration path. Gate every marker to the
SM8350 GPU clock controller.' \
	-m 'Record allocation, lock, runtime-PM, parent/orphan, callback, debug,
and managed-resource boundaries. Add no clock, register, power,
storage, or persistent-state operation.'

[ "$(git -C "$target_source" rev-parse HEAD^^^)" = "$expected_base" ]
[ "$(git -C "$target_source" rev-parse HEAD^^)" = "$expected_gpucc" ]
[ "$(git -C "$target_source" rev-parse HEAD^)" = "$expected_common" ]
[ "$(git -C "$target_source" rev-parse HEAD)" = "$expected_ccf" ]
[ "$(git -C "$target_source" rev-parse HEAD^{tree})" = "$expected_tree" ]
[ -z "$(git -C "$target_source" status --porcelain)" ]

printf 'base_commit=%s\n' "$expected_base"
printf 'gpucc_commit=%s\n' "$expected_gpucc"
printf 'common_commit=%s\n' "$expected_common"
printf 'ccf_commit=%s\n' "$expected_ccf"
printf 'ccf_tree=%s\n' "$expected_tree"
sha256sum "$patch"
echo 'PASS deterministic Linux 7.1.4 GPUCC/CCF diagnostic source'
