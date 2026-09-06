#!/usr/bin/env bash
set -euo pipefail

fail() {
	echo "FAIL $*" >&2
	exit 1
}

repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
image=${ROG5_FETCH_ROOT_TEST_IMAGE:-localhost/rog5-kernel-builder:ubuntu-24.04}
builder_verifier=$repo/scripts/host/verify-steam-deck-builder.sh

command -v podman >/dev/null ||
	fail 'missing privileged fetch-test command: podman'
[[ -x $builder_verifier && -f $builder_verifier && ! -L $builder_verifier ]] ||
	fail 'missing qualified Steam Deck builder verifier'
podman image exists "$image" ||
	fail "missing pinned local privileged fetch-test image: $image"
$builder_verifier "$image" >/dev/null
[[ $(podman image inspect "$image" --format '{{.Architecture}}') == amd64 ]] ||
	fail 'qualified privileged fetch-test image is not amd64'
actual_image_id=$(podman image inspect "$image" --format '{{.Id}}')
actual_image_digest=$(podman image inspect "$image" --format '{{.Digest}}')
# Local object IDs can change when the same qualified rootfs is reconstructed.
# The verifier above pins the snapshot, package closure, recipe, tools, and
# complete rootfs identity; these transport identities remain canonical audit
# output rather than the trust root.
[[ $actual_image_id =~ ^[0-9a-f]{64}$ &&
	$actual_image_digest =~ ^sha256:[0-9a-f]{64}$ ]] ||
	fail 'qualified privileged fetch-test image identity is invalid'

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
