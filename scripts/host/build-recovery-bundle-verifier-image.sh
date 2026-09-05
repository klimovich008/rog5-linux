#!/usr/bin/env bash
set -euo pipefail

fail() {
	echo "FAIL $*" >&2
	exit 1
}

repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
image=${ROG5_BUNDLE_BUILD_IMAGE:-localhost/rog5-recovery-bundle-verifier:alpine-3.24-openssl-3.5.7-deck-v1}
dockerfile=$repo/containers/recovery-bundle-verifier/Dockerfile
epoch=1681862400
expected_recipe_sha=f64ee4ef377e2e44d968237e1a6819b6c0e3a2c22f84654ec67456d4c2871080
expected_image_id=13d758cd4c708ddb798dd539d1b6c4e3546ea5ef9129ed309c74bd8f4e620689
expected_image_digest=sha256:75f5179fe0164ffefa2f9bc5dba5a47eac47674d347311602256476aa2ee7a01

for command_name in cut podman sha256sum; do
	command -v "$command_name" >/dev/null ||
		fail "missing verifier-image build command: $command_name"
done
[[ -f $dockerfile && ! -L $dockerfile ]] ||
	fail 'missing or linked recovery bundle verifier Dockerfile'
[[ $(sha256sum "$dockerfile" | cut -d ' ' -f 1) == \
	"$expected_recipe_sha" ]] ||
	fail 'recovery bundle verifier Dockerfile identity changed'

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
printf 'recipe_sha256=%s\n' "$expected_recipe_sha"
printf 'image_id=%s image_digest=%s\n' \
	"$actual_image_id" "$actual_image_digest"
echo 'PASS pinned recovery bundle verifier builder image'
