#!/usr/bin/env bash
set -euo pipefail

repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
output_root=${1:?usage: build-headless-core-candidate-offline.sh OUTPUT_ROOT}

exec "$repo/scripts/host/build-corrected-headless-candidate-offline.sh" \
	--candidate headless-core-network-root-v2 \
	--expected-dtb 57216474b4c8979161d964cef2ff3fe5d61500af3cef34598ee06e03e91f967d \
	--expected-target headless-core-network-root \
	"$output_root"
