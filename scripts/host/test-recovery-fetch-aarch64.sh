#!/usr/bin/env bash
set -euo pipefail

fail() {
	echo "FAIL $*" >&2
	exit 1
}

repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
image=${ROG5_FETCH_BUILD_IMAGE:-localhost/rog5-persistent-root-verifier:alpine-3.24}
expected_image_id=d5fb16636fadea937b74dc3e062617d74a12577fd3fcc3f61fec24d0f7364495
expected_image_digest=sha256:750150c51c8b5085d322ecaa5363356bb31ee243d6efab1035bd15f5ffe52355
for command in cmp file podman python3 qemu-aarch64-static sha256sum; do
	command -v "$command" >/dev/null ||
		fail "missing fetcher AArch64-test command: $command"
done
podman image exists "$image" ||
	fail "missing pinned local AArch64 build image: $image"
[[ $(podman image inspect "$image" --format '{{.Architecture}}') == arm64 ]] ||
	fail 'recovery bundle fetcher build image is not arm64'
actual_image_id=$(podman image inspect "$image" --format '{{.Id}}')
actual_image_digest=$(podman image inspect "$image" --format '{{.Digest}}')
[[ $actual_image_id == "$expected_image_id" ]] ||
	fail "unexpected AArch64 build image ID: $actual_image_id"
[[ $actual_image_digest == "$expected_image_digest" ]] ||
	fail "unexpected AArch64 build image digest: $actual_image_digest"

test_tmp=$(mktemp -d)
trap 'rm -rf -- "$test_tmp"' EXIT HUP INT TERM

build_one() {
	output=$1
	podman run --rm --network=none --platform linux/arm64 \
		-v "$repo:/workspace:ro,Z" \
		-v "$test_tmp:/out:Z" \
		"$image" \
		/workspace/scripts/device/build-recovery-bundle-fetcher.sh \
		/workspace/tools/recovery_control/rog5-bundle-fetch.c \
		"/out/$output"
}

build_one rog5-bundle-fetch-a
build_one rog5-bundle-fetch-b
cmp "$test_tmp/rog5-bundle-fetch-a" \
	"$test_tmp/rog5-bundle-fetch-b"

podman run --rm --network=none --platform linux/arm64 \
	-v "$repo:/workspace:ro,Z" \
	-v "$test_tmp:/out:Z" \
	"$image" \
	cc -std=c11 -O2 -static -fPIE -pie -fstack-protector-strong \
	-Wall -Wextra -Werror \
	-Wl,-z,relro,-z,now,-z,noexecstack,--build-id=none \
	-DROG5_FETCH_TESTING=1 \
	/workspace/tools/recovery_control/rog5-bundle-fetch.c \
	-o /out/rog5-bundle-fetch-test

podman run --rm --network=none --platform linux/arm64 \
	-v "$repo:/workspace:ro,Z" \
	-v "$test_tmp:/out:Z" \
	"$image" \
	sh -eu -c '
		cp /workspace/tools/recovery_control/rog5-bundle-fetch.c \
			/out/contaminated-fetcher.c
		printf "%s\n" \
			"const char rog5_contamination[] __attribute__((used)) = \"--bundle-root ROG5_FETCH_TEST http://\";" \
			>>/out/contaminated-fetcher.c
		if /workspace/scripts/device/build-recovery-bundle-fetcher.sh \
			/out/contaminated-fetcher.c \
			/out/contaminated-fetcher \
			>/out/contaminated-fetcher-build.log 2>&1; then
			echo "FAIL contaminated production fetcher passed" >&2
			exit 1
		fi
		grep -qx \
			"FAIL production fetcher contains forbidden token: ROG5_FETCH_TEST" \
			/out/contaminated-fetcher-build.log
	'

ROG5_FETCH_TEST_BINARY=$test_tmp/rog5-bundle-fetch-test \
ROG5_FETCH_TEST_RUNNER=$(command -v qemu-aarch64-static) \
	python3 "$repo/scripts/host/test-recovery-fetch-native.py"

file "$test_tmp/rog5-bundle-fetch-a" |
	grep -q 'ARM aarch64.*static-pie linked, stripped'
[[ $(stat -c %a "$test_tmp/rog5-bundle-fetch-a") == 755 ]]
sha256sum "$test_tmp/rog5-bundle-fetch-a" \
	"$test_tmp/rog5-bundle-fetch-b"
printf 'build_image_id=%s build_image_digest=%s\n' \
	"$actual_image_id" "$actual_image_digest"
echo 'PASS reproducible production AArch64 fetcher and QEMU suite'
