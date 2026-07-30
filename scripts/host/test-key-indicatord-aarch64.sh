#!/usr/bin/env bash
set -euo pipefail

repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
image=${ROG5_AARCH64_BUILD_IMAGE:-localhost/rog5-persistent-root-verifier:alpine-3.24}
expected_image_id=d5fb16636fadea937b74dc3e062617d74a12577fd3fcc3f61fec24d0f7364495
expected_image_digest=sha256:750150c51c8b5085d322ecaa5363356bb31ee243d6efab1035bd15f5ffe52355
expected_source_size=20530
expected_source_sha256=3d597f919d71a76f2aef0ae2aa269e219ffe7c0bdca0e9b73481d52dff686939
expected_binary_size=67520
expected_binary_sha256=3792745382a390ebeef37a081e532884aae07bbcd73fd9f0da1c94e67bdabbc8
artifact=$repo/artifacts/headless-indicator-v1/rog5-key-indicatord

fail() {
	echo "FAIL $*" >&2
	exit 1
}

for command in cmp file podman qemu-aarch64-static sha256sum; do
	command -v "$command" >/dev/null ||
		fail "missing AArch64 key-indicator test command: $command"
done
podman image exists "$image" ||
	fail "missing pinned local AArch64 build image: $image"
[[ $(podman image inspect "$image" --format '{{.Architecture}}') == arm64 ]] ||
	fail 'key-indicator build image is not arm64'
actual_image_id=$(podman image inspect "$image" --format '{{.Id}}')
actual_image_digest=$(podman image inspect "$image" --format '{{.Digest}}')
[[ $actual_image_id == "$expected_image_id" ]] ||
	fail "unexpected AArch64 build image ID: $actual_image_id"
[[ $actual_image_digest == "$expected_image_digest" ]] ||
	fail "unexpected AArch64 build image digest: $actual_image_digest"
[[ -f $artifact && ! -L $artifact && -x $artifact ]] ||
	fail 'missing sealed key-indicator artifact'
[[ $(stat -c %s "$repo/tools/key-indicator/rog5-key-indicatord.c") == \
	"$expected_source_size" ]]
[[ $(sha256sum "$repo/tools/key-indicator/rog5-key-indicatord.c" |
	cut -d' ' -f1) == "$expected_source_sha256" ]]

work=$(mktemp -d)
trap 'rm -rf -- "$work"' EXIT HUP INT TERM

build_one() {
	local output=$1

	podman run --rm --network=none --platform linux/arm64 \
		-v "$repo:/workspace:ro,Z" \
		-v "$work:/out:Z" \
		"$image" \
		/workspace/scripts/device/build-key-indicatord.sh \
		/workspace/tools/key-indicator/rog5-key-indicatord.c \
		"/out/$output"
}

build_one rog5-key-indicatord-a
build_one rog5-key-indicatord-b
cmp "$work/rog5-key-indicatord-a" "$work/rog5-key-indicatord-b"
cmp "$work/rog5-key-indicatord-a" "$artifact"
[[ $(stat -c %s "$work/rog5-key-indicatord-a") == \
	"$expected_binary_size" ]]
[[ $(sha256sum "$work/rog5-key-indicatord-a" | cut -d' ' -f1) == \
	"$expected_binary_sha256" ]]

podman run --rm --network=none --platform linux/arm64 \
	-v "$repo:/workspace:ro,Z" \
	-v "$work:/out:Z" \
	"$image" \
	cc -std=c11 -O2 -static -fPIE -pie -fstack-protector-strong \
	-Wall -Wextra -Werror \
	-Wl,-z,relro,-z,now,-z,noexecstack,--build-id=none \
	-DROG5_INDICATOR_TESTING=1 \
	/workspace/tools/key-indicator/rog5-key-indicatord.c \
	-o /out/rog5-key-indicatord-fixture

ROG5_INDICATOR_PRODUCTION_BINARY=$work/rog5-key-indicatord-a \
ROG5_INDICATOR_FIXTURE_BINARY=$work/rog5-key-indicatord-fixture \
ROG5_INDICATOR_TEST_RUNNER=$(command -v qemu-aarch64-static) \
	"$repo/scripts/host/test-key-indicatord.sh"

file "$work/rog5-key-indicatord-a" |
	grep -q 'ARM aarch64.*static-pie linked, stripped'
[[ $(stat -c %a "$work/rog5-key-indicatord-a") == 755 ]]
sha256sum "$work/rog5-key-indicatord-a" \
	"$work/rog5-key-indicatord-b"
printf 'build_image_id=%s build_image_digest=%s\n' \
	"$actual_image_id" "$actual_image_digest"
echo 'PASS reproducible static AArch64 key indicator and QEMU fixture suite'
