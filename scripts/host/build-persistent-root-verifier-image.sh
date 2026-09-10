#!/usr/bin/env bash
set -euo pipefail

fail() {
	echo "FAIL $*" >&2
	exit 1
}

repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
image=${ROG5_STATIC_BUILD_IMAGE:-localhost/rog5-persistent-root-verifier:alpine-3.24-deck-v1}
dockerfile=$repo/containers/persistent-root-verifier/Dockerfile
epoch=1681862400
expected_recipe_sha=3d074a3e8b7bc81f96086aa633b132a897ededa4349f88aa77be5fbea2e237f0
expected_image_id=a085070738e277a354bc22bb033f84c7c1568ae45a35ebf951ff27510fd7fd0e
expected_image_digest=sha256:ab143fea42bd7780c2b69512397f9a33251ef9218c3258e5dd2995a905abddaa

for command_name in cut podman sha256sum; do
	command -v "$command_name" >/dev/null ||
		fail "missing static-verifier image build command: $command_name"
done
[[ -f $dockerfile && ! -L $dockerfile ]] ||
	fail 'missing or linked persistent-root verifier Dockerfile'
[[ $(sha256sum "$dockerfile" | cut -d ' ' -f 1) == \
	"$expected_recipe_sha" ]] ||
	fail 'persistent-root verifier Dockerfile identity changed'

podman build --no-cache --platform linux/arm64 --network=host \
	--timestamp "$epoch" \
	-t "$image" \
	"$repo/containers/persistent-root-verifier"

[[ $(podman image inspect "$image" --format '{{.Architecture}}') == arm64 ]] ||
	fail 'persistent-root verifier build image is not arm64'
actual_image_id=$(podman image inspect "$image" --format '{{.Id}}')
actual_image_digest=$(podman image inspect "$image" --format '{{.Digest}}')
[[ $actual_image_id == "$expected_image_id" ]] ||
	fail "unexpected static-verifier image ID: $actual_image_id"
[[ $actual_image_digest == "$expected_image_digest" ]] ||
	fail "unexpected static-verifier image digest: $actual_image_digest"
printf 'source_date_epoch=%s\n' "$epoch"
printf 'recipe_sha256=%s\n' "$expected_recipe_sha"
printf 'image_id=%s image_digest=%s\n' \
	"$actual_image_id" "$actual_image_digest"
echo 'PASS pinned persistent-root static-verifier builder image'
