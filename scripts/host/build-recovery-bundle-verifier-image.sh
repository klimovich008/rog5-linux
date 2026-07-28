#!/usr/bin/env bash
set -euo pipefail

fail() {
	echo "FAIL $*" >&2
	exit 1
}

repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
image=${ROG5_BUNDLE_BUILD_IMAGE:-localhost/rog5-recovery-bundle-verifier:alpine-3.24-openssl-3.5.7}
epoch=1681862400
expected_image_id=e2e90f8ad3cfc4f9b7660ee8828fcae008792f05567fb9b4efd3ab0102063d8e
expected_image_digest=sha256:b4946b74324785d005aa3067dd18788f90cc65215a519c8735dce03aa01d1268

command -v podman >/dev/null ||
	fail 'missing verifier-image build command: podman'
[[ -f $repo/containers/recovery-bundle-verifier/Dockerfile ]] ||
	fail 'missing recovery bundle verifier Dockerfile'

podman build --no-cache --platform linux/arm64 --network=host \
	--timestamp "$epoch" \
	-t "$image" \
	"$repo/containers/recovery-bundle-verifier"

[[ $(podman image inspect "$image" --format '{{.Architecture}}') == arm64 ]] ||
	fail 'recovery bundle verifier build image is not arm64'
actual_image_id=$(podman image inspect "$image" --format '{{.Id}}')
actual_image_digest=$(podman image inspect "$image" --format '{{.Digest}}')
[[ $actual_image_id == "$expected_image_id" ]] ||
	fail "unexpected verifier builder image ID: $actual_image_id"
[[ $actual_image_digest == "$expected_image_digest" ]] ||
	fail "unexpected verifier builder image digest: $actual_image_digest"
printf 'source_date_epoch=%s\n' "$epoch"
printf 'image_id=%s image_digest=%s\n' \
	"$actual_image_id" "$actual_image_digest"
echo 'PASS pinned recovery bundle verifier builder image'
