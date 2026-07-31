#!/usr/bin/env bash
set -euo pipefail

repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
output_root=${1:?usage: build-headless-ssh-deployment-candidate.sh OUTPUT_ROOT}

[[ ${ALLOW_HEADLESS_SSH_DEPLOYMENT_BUILD:-} == 1 ]] || {
	echo 'FAIL set ALLOW_HEADLESS_SSH_DEPLOYMENT_BUILD=1 for one signed deployment build' >&2
	exit 1
}
[[ ${ALLOW_PHONE_CREDENTIAL_USE:-} == 1 ]] || {
	echo 'FAIL set ALLOW_PHONE_CREDENTIAL_USE=1 before using the signing key' >&2
	exit 1
}
[[ -n ${ROG5_DEPLOYMENT_CANDIDATE_RECORD:-} &&
	-n ${ROG5_DEPLOYMENT_SIGNING_KEY:-} ]] || {
	echo 'FAIL set deployment candidate record and signing key paths' >&2
	exit 1
}

ROG5_DEPLOYMENT_BUILD=1 \
ROG5_OFFLINE_CANDIDATE=headless-ssh-network-root-v3 \
ROG5_OFFLINE_EXPECTED_DTB=86e5cb81191e3de39c9527b838fa03d78744cd9b0d862336f0c1f36a9f534f46 \
ROG5_OFFLINE_EXPECTED_TARGET=headless-ssh-network-root \
	exec "$repo/scripts/host/build-corrected-headless-candidate-offline.sh" \
	"$output_root"
