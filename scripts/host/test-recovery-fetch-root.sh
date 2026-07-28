#!/usr/bin/env bash
set -euo pipefail

fail() {
	echo "FAIL $*" >&2
	exit 1
}

repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
image=${ROG5_FETCH_ROOT_TEST_IMAGE:-localhost/rog5-kernel-builder:ubuntu-24.04}
expected_image_id=34ecc17078b364df195ad61253520b1cac487dca05773dc4b2fc2bacb0941941
expected_image_digest=sha256:7b2e3415dc638ca4864912c9aa4905425561e21b9d08f1e60e4cfb0a3aa6ff8c

command -v podman >/dev/null ||
	fail 'missing privileged fetch-test command: podman'
podman image exists "$image" ||
	fail "missing pinned local privileged fetch-test image: $image"
[[ $(podman image inspect "$image" --format '{{.Architecture}}') == amd64 ]] ||
	fail 'privileged fetch-test image is not amd64'
actual_image_id=$(podman image inspect "$image" --format '{{.Id}}')
actual_image_digest=$(podman image inspect "$image" --format '{{.Digest}}')
[[ $actual_image_id == "$expected_image_id" ]] ||
	fail "unexpected privileged fetch-test image ID: $actual_image_id"
[[ $actual_image_digest == "$expected_image_digest" ]] ||
	fail "unexpected privileged fetch-test image digest: $actual_image_digest"

podman run --rm --network=none --platform linux/amd64 \
	-v "$repo:/workspace:ro,Z" \
	"$image" \
	bash -euo pipefail -c '
		gcc -std=c11 -O2 -fPIE -pie -fstack-protector-strong \
			-Wall -Wextra -Werror \
			-Wl,-z,relro,-z,now,-z,noexecstack,--build-id=none \
			-DROG5_FETCH_TESTING=1 \
			/workspace/tools/recovery_control/rog5-bundle-fetch.c \
			-o /tmp/rog5-bundle-fetch-test
		ROG5_FETCH_TEST_BINARY=/tmp/rog5-bundle-fetch-test \
			python3 \
			/workspace/scripts/host/test-recovery-fetch-native.py
	'

printf 'root_test_image_id=%s root_test_image_digest=%s\n' \
	"$actual_image_id" "$actual_image_digest"
echo 'PASS root credential-drop, chroot, seccomp, and parent-death fetch suite'
