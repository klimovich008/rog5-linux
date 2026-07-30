#!/usr/bin/env bash
set -euo pipefail

fail() {
	echo "FAIL $*" >&2
	exit 1
}

repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
image=${ROG5_AARCH64_BUILD_IMAGE:-localhost/rog5-persistent-root-verifier:alpine-3.24-deck-v1}
expected_image_id=a085070738e277a354bc22bb033f84c7c1568ae45a35ebf951ff27510fd7fd0e
expected_image_digest=sha256:ab143fea42bd7780c2b69512397f9a33251ef9218c3258e5dd2995a905abddaa
for command in cmp file podman qemu-aarch64-static sha256sum; do
	command -v "$command" >/dev/null ||
		fail "missing AArch64-test command: $command"
done
podman image exists "$image" ||
	fail "missing pinned local AArch64 build image: $image"
[ "$(podman image inspect "$image" --format '{{.Architecture}}')" = arm64 ] ||
	fail 'recovery responder build image is not arm64'
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
		/workspace/scripts/device/build-recovery-control.sh \
		/workspace/tools/recovery_control/rog5-recovery-control.c \
		"/out/$output"
}

build_one rog5-recovery-control-a
build_one rog5-recovery-control-b
cmp "$test_tmp/rog5-recovery-control-a" \
	"$test_tmp/rog5-recovery-control-b"

podman run --rm --network=none --platform linux/arm64 \
	-v "$repo:/workspace:ro,Z" \
	-v "$test_tmp:/out:Z" \
	"$image" \
	cc -std=c11 -O2 -static -fPIE -pie -fstack-protector-strong \
	-Wall -Wextra -Werror \
	-Wl,-z,relro,-z,now,-z,noexecstack,--build-id=none \
	-DROG5_CONTROL_TESTING=1 \
	/workspace/tools/recovery_control/rog5-recovery-control.c \
	-o /out/rog5-recovery-control-test

podman run --rm --network=none --platform linux/arm64 \
	-v "$repo:/workspace:ro,Z" \
	-v "$test_tmp:/out:Z" \
	"$image" \
	sh -eu -c '
		cp /workspace/tools/recovery_control/rog5-recovery-control.c \
			/out/contaminated-responder.c
		printf "%s\n" \
			"const char rog5_contamination[] __attribute__((used)) = \"ROG5_TEST_CONTAMINATION\";" \
			>>/out/contaminated-responder.c
		if /workspace/scripts/device/build-recovery-control.sh \
			/out/contaminated-responder.c \
			/out/contaminated-responder \
			>/out/contaminated-responder-build.log 2>&1; then
			echo "FAIL contaminated production responder passed" >&2
			exit 1
		fi
		grep -qx \
			"FAIL production responder contains a test interface" \
			/out/contaminated-responder-build.log
	'

ROG5_CONTROL_TEST_BINARY=$test_tmp/rog5-recovery-control-test \
ROG5_CONTROL_TEST_RUNNER=$(command -v qemu-aarch64-static) \
	python3 "$repo/scripts/host/test-recovery-control-native.py"

file "$test_tmp/rog5-recovery-control-a" |
	grep -q 'ARM aarch64.*static-pie linked, stripped'
[ "$(stat -c %a "$test_tmp/rog5-recovery-control-a")" = 755 ]
sha256sum "$test_tmp/rog5-recovery-control-a" \
	"$test_tmp/rog5-recovery-control-b"
printf 'build_image_id=%s build_image_digest=%s\n' \
	"$actual_image_id" "$actual_image_digest"
echo 'PASS reproducible production AArch64 responder and QEMU PTY suite'
