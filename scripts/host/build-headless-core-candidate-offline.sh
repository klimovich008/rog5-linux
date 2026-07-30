#!/usr/bin/env bash
set -euo pipefail

repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
output_root=${1:?usage: build-headless-core-candidate-offline.sh OUTPUT_ROOT}

ROG5_OFFLINE_CANDIDATE=headless-core-network-root-v2 \
ROG5_OFFLINE_EXPECTED_DTB=57216474b4c8979161d964cef2ff3fe5d61500af3cef34598ee06e03e91f967d \
ROG5_OFFLINE_EXPECTED_TARGET=headless-core-network-root \
	exec "$repo/scripts/host/build-corrected-headless-candidate-offline.sh" \
	"$output_root"
