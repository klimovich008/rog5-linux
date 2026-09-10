#!/bin/sh
set -eu

repo=${REPO_ROOT:-/workspace/repo}
RCG2_TRACE_PATCH=${RCG2_TRACE_PATCH:-$repo/patches/linux-7.1.4/0010-clk-qcom-trace-attended-SM8350-DISPCC-RCG-parent-read.patch}
export RCG2_TRACE_PATCH

exec "$repo/scripts/device/build-mainline-gpucc-parent-diagnostic.sh"
