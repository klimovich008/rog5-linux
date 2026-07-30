#!/usr/bin/env bash
set -euo pipefail

repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
output_root=${1:?usage: build-headless-ssh-v2-candidate-offline.sh OUTPUT_ROOT}

ROG5_OFFLINE_CANDIDATE=headless-ssh-network-root-v3 \
ROG5_OFFLINE_EXPECTED_DTB=86e5cb81191e3de39c9527b838fa03d78744cd9b0d862336f0c1f36a9f534f46 \
ROG5_OFFLINE_EXPECTED_TARGET=headless-ssh-network-root \
	exec "$repo/scripts/host/build-corrected-headless-candidate-offline.sh" \
	"$output_root"
