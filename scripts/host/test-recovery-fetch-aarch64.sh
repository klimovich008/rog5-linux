#!/usr/bin/env bash
set -euo pipefail

fail() {
	echo "FAIL $*" >&2
	exit 1
}

repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
image=${ROG5_FETCH_BUILD_IMAGE:-localhost/rog5-persistent-root-verifier:alpine-3.24-deck-v1}
expected_image_id=a085070738e277a354bc22bb033f84c7c1568ae45a35ebf951ff27510fd7fd0e
expected_image_digest=sha256:ab143fea42bd7780c2b69512397f9a33251ef9218c3258e5dd2995a905abddaa
runner=$repo/scripts/host/run-private-arm64-binfmt.sh
for command in cmp file podman python3 sha256sum; do
	command -v "$command" >/dev/null ||
		fail "missing fetcher AArch64-test command: $command"
done
[[ -x $runner && -f $runner && ! -L $runner ]] ||
	fail 'missing sealed private ARM64 runner'
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

# Match the existing sealed private-binfmt build path: label mediation is
# disabled only inside its private mount namespace, with the repository mounted
# read-only and one disposable output directory mounted writable.
build_one() {
	output=$1
	"$runner" podman run --rm --pull=never --network=none \
		--platform linux/arm64 --security-opt label=disable \
		-v "$repo:/workspace:ro" \
		-v "$test_tmp:/out" \
		"$image" \
		/workspace/scripts/device/build-recovery-bundle-fetcher.sh \
		/workspace/tools/recovery_control/rog5-bundle-fetch.c \
		"/out/$output"
}

build_one rog5-bundle-fetch-a
build_one rog5-bundle-fetch-b
cmp "$test_tmp/rog5-bundle-fetch-a" \
	"$test_tmp/rog5-bundle-fetch-b"

"$runner" podman run --rm --pull=never --network=none \
	--platform linux/arm64 --security-opt label=disable \
	-v "$repo:/workspace:ro" \
	-v "$test_tmp:/out" \
	"$image" \
	cc -std=c11 -O2 -static -fPIE -pie -fstack-protector-strong \
	-Wall -Wextra -Werror \
	-Wl,-z,relro,-z,now,-z,noexecstack,--build-id=none \
	-DROG5_FETCH_TESTING=1 \
	/workspace/tools/recovery_control/rog5-bundle-fetch.c \
	-o /out/rog5-bundle-fetch-test

"$runner" podman run --rm --pull=never --network=none \
	--platform linux/arm64 --security-opt label=disable \
	-v "$repo:/workspace:ro" \
	-v "$test_tmp:/out" \
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
ROG5_FETCH_TEST_RUNNER=$runner \
	python3 "$repo/scripts/host/test-recovery-fetch-native.py"

file "$test_tmp/rog5-bundle-fetch-a" |
	grep -q 'ARM aarch64.*static-pie linked, stripped'
[[ $(stat -c %a "$test_tmp/rog5-bundle-fetch-a") == 755 ]]
sha256sum "$test_tmp/rog5-bundle-fetch-a" \
	"$test_tmp/rog5-bundle-fetch-b"
printf 'build_image_id=%s build_image_digest=%s\n' \
	"$actual_image_id" "$actual_image_digest"
echo 'PASS reproducible production AArch64 fetcher and QEMU suite'
