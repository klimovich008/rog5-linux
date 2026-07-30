#!/usr/bin/env bash
set -euo pipefail

fail() {
	echo "FAIL $*" >&2
	exit 1
}

repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
image=${ROG5_BUNDLE_BUILD_IMAGE:-localhost/rog5-recovery-bundle-verifier:alpine-3.24-openssl-3.5.7-deck-v1}
expected_image_id=13d758cd4c708ddb798dd539d1b6c4e3546ea5ef9129ed309c74bd8f4e620689
expected_image_digest=sha256:75f5179fe0164ffefa2f9bc5dba5a47eac47674d347311602256476aa2ee7a01
for command in cmp dtc file gcc openssl podman python3 strings \
	qemu-aarch64-static sha256sum; do
	command -v "$command" >/dev/null ||
		fail "missing AArch64-test command: $command"
done
podman image exists "$image" ||
	fail "missing pinned local AArch64 build image: $image"
[ "$(podman image inspect "$image" --format '{{.Architecture}}')" = arm64 ] ||
	fail 'recovery bundle verifier build image is not arm64'
actual_image_id=$(podman image inspect "$image" --format '{{.Id}}')
actual_image_digest=$(podman image inspect "$image" --format '{{.Digest}}')
[ "$actual_image_id" = "$expected_image_id" ] ||
	fail "unexpected AArch64 build image ID: $actual_image_id"
[ "$actual_image_digest" = "$expected_image_digest" ] ||
	fail "unexpected AArch64 build image digest: $actual_image_digest"

test_tmp=$(mktemp -d)
trap 'rm -rf -- "$test_tmp"' EXIT HUP INT TERM

build_one() {
	output=$1
	podman run --rm --network=none --platform linux/arm64 \
		-v "$repo:/workspace:ro,Z" \
		-v "$test_tmp:/out:Z" \
		"$image" \
		/workspace/scripts/device/build-recovery-bundle-verifier.sh \
		/workspace/tools/recovery_control/rog5-bundle-verify.c \
		"/out/$output"
}

build_one rog5-bundle-verify-a
build_one rog5-bundle-verify-b
cmp "$test_tmp/rog5-bundle-verify-a" \
	"$test_tmp/rog5-bundle-verify-b"

podman run --rm --network=none --platform linux/arm64 \
	-v "$repo:/workspace:ro,Z" \
	-v "$test_tmp:/out:Z" \
	"$image" \
	cc -std=c11 -O2 -static -fPIE -pie -fstack-protector-strong \
	-Wall -Wextra -Werror \
	-Wl,-z,relro,-z,now,-z,noexecstack,--build-id=none \
	-DROG5_BUNDLE_TESTING=1 \
	/workspace/tools/recovery_control/rog5-bundle-verify.c \
	-o /out/rog5-bundle-verify-test -lcrypto -lz

podman run --rm --network=none --platform linux/arm64 \
	-v "$repo:/workspace:ro,Z" \
	-v "$test_tmp:/out:Z" \
	"$image" \
	sh -eu -c '
		cp /workspace/tools/recovery_control/rog5-bundle-verify.c \
			/out/contaminated-verifier.c
		printf "%s\n" \
			"const char rog5_contamination[] __attribute__((used)) = \"--trust-key ROG5_BUNDLE_TEST\";" \
			>>/out/contaminated-verifier.c
		if /workspace/scripts/device/build-recovery-bundle-verifier.sh \
			/out/contaminated-verifier.c \
			/out/contaminated-verifier \
			>/out/contaminated-build.log 2>&1; then
			echo "FAIL contaminated production verifier passed" >&2
			exit 1
		fi
		grep -qx \
			"FAIL production verifier contains trust-key override" \
			/out/contaminated-build.log
	'

ROG5_BUNDLE_TEST_BINARY=$test_tmp/rog5-bundle-verify-test \
ROG5_BUNDLE_TEST_RUNNER=$(command -v qemu-aarch64-static) \
	python3 "$repo/scripts/host/test-recovery-bundle-native.py"

file "$test_tmp/rog5-bundle-verify-a" |
	grep -q 'ARM aarch64.*static-pie linked, stripped'
[ "$(stat -c %a "$test_tmp/rog5-bundle-verify-a")" = 755 ]
sha256sum "$test_tmp/rog5-bundle-verify-a" \
	"$test_tmp/rog5-bundle-verify-b"
printf 'build_image_id=%s build_image_digest=%s\n' \
	"$actual_image_id" "$actual_image_digest"
echo 'PASS reproducible production AArch64 verifier and QEMU suite'
