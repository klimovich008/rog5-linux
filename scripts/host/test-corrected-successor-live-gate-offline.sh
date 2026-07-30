#!/usr/bin/env bash
set -euo pipefail

fail() {
	echo "FAIL $*" >&2
	exit 1
}

repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
candidate=$repo/build/corrected-headless-candidate-20260730-successor
gate=$repo/scripts/host/run-stable-recovery-live-gate.sh

[[ -f $gate && ! -L $gate && -x $gate ]] ||
	fail 'missing stable-recovery live gate'
if [[ ! -d $candidate ]]; then
	echo 'SKIP retained corrected-successor live-gate integration'
	exit 0
fi
[[ ! -L $candidate ]] ||
	fail 'retained corrected-successor candidate is a symlink'

output=$(
	env \
		ROG5_STABLE_RECOVERY_PROFILE=corrected-headless-successor-2026-07-30 \
		LIVE_BUILD_ROOT="$candidate/wrapper" \
		RECOVERY_COMPONENT_ROOT="$candidate/recovery" \
		TRUST_KEY="$candidate/recovery/ephemeral-public.raw" \
		BUNDLE_ROOT="$candidate/bundle-a" \
		BUNDLE=headless-network-root-v1 \
		RECOVERY_SHA256=416d62e4f0d89e9184d8a362c8c9e5091bd265f4c48504916920706f08611430 \
		TRUST_KEY_SHA256=ce9f89c9c1859a3239615932da36617f3436f9a0355c8db9c852a1b764f2dfeb \
		MANIFEST_SHA256=d7a02a2403caf885a015060a8361019936e86efafde44f3bb7e6bdd48d2ee32d \
		HOST_VERIFIER_SHA256=9099f5f615144cf95655e6e169ac49b0cbe6f0a6d759441c59bc3130407ab78b \
		"$gate" artifact-preflight
)
grep -Fxq \
	'PASS stable-recovery artifact preflight profile=corrected-headless-successor-2026-07-30 image_sha256=416d62e4f0d89e9184d8a362c8c9e5091bd265f4c48504916920706f08611430' \
	<<<"$output" ||
	fail 'corrected-successor artifact preflight lacked exact success evidence'

echo 'PASS retained corrected successor satisfies the exact phone-free live-gate boundary'
