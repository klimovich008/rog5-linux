#!/usr/bin/env bash
set -euo pipefail

fail() {
	echo "FAIL $*" >&2
	exit 1
}

repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
profile=$repo/configs/kernel-builder/steam-deck-recovery-arm64-v1.json
runner=$repo/scripts/host/run-private-arm64-binfmt.sh
sealed_runner=$repo/scripts/host/run-sealed-arm64-binfmt.py
extractor=$repo/scripts/host/extract-qualified-qemu-aarch64-static.sh
manifest_script=$repo/scripts/host/kernel-builder-rootfs-manifest.sh
qemu=$repo/artifacts/host-tools/qemu-aarch64-static
expected_profile=18fc6f392d4a84cf15eab867de89b7a8760c54568793d5fe07f5a50725402278
expected_runner=972831d9c4bde3c440e905bdb7beac6b3e74a0a02dc04d0eeb1060c6bfaeb50d
expected_sealed_runner=354ea9b62a7ec9f19501858e3e0d2c4f848faa93e639dccc36bb23f5a016c301
expected_extractor=5b0e991cb1112b21f5c40c8e1504020d8638ac6bff611964c96059d658cd6ecd
expected_manifest=3a2644f7a128fac3a3c8bd44d9a58cd00304e3459f2aee81d8930a4659919c84
responder_image=localhost/rog5-persistent-root-verifier:alpine-3.24-deck-v1
responder_id=a085070738e277a354bc22bb033f84c7c1568ae45a35ebf951ff27510fd7fd0e
responder_digest=sha256:ab143fea42bd7780c2b69512397f9a33251ef9218c3258e5dd2995a905abddaa
responder_rootfs=89fde8f4651efe47ce5b2e78d44307520547f7e693ec8e2b2672e1a979119fcd
responder_packages=a0b976c4df8050064f88664f97c1762a11a32321a282b34c523c9e829d75334c
verifier_image=localhost/rog5-recovery-bundle-verifier:alpine-3.24-openssl-3.5.7-deck-v1
verifier_id=13d758cd4c708ddb798dd539d1b6c4e3546ea5ef9129ed309c74bd8f4e620689
verifier_digest=sha256:75f5179fe0164ffefa2f9bc5dba5a47eac47674d347311602256476aa2ee7a01
verifier_rootfs=e6ab755c445f3388ccc04717346337f65c8d24ee892e078977b6bbe99f0b26b3
verifier_packages=6b52a32d2720a6e9e391601f483f7f37c625667eb65e465a58a989350590c8ae

for command_name in cut grep gzip podman sed sha256sum stat; do
	command -v "$command_name" >/dev/null ||
		fail "missing recovery-builder verification command: $command_name"
done
for input in "$profile" "$runner" "$sealed_runner" "$extractor" \
	"$manifest_script" "$qemu"; do
	[[ -f $input && ! -L $input ]] ||
		fail "missing or linked recovery-builder input: ${input#"$repo"/}"
done
[[ -x $runner && -x $sealed_runner && -x $extractor && -x $qemu ]] ||
	fail 'recovery-builder executable input lost its mode'
[[ $(sha256sum "$profile" | cut -d ' ' -f 1) == "$expected_profile" ]] ||
	fail 'recovery-builder profile changed'
[[ $(sha256sum "$runner" | cut -d ' ' -f 1) == "$expected_runner" ]] ||
	fail 'private ARM64 runner changed'
[[ $(sha256sum "$sealed_runner" | cut -d ' ' -f 1) == \
	"$expected_sealed_runner" ]] ||
	fail 'sealed ARM64 binfmt runner changed'
[[ $(sha256sum "$extractor" | cut -d ' ' -f 1) == \
	"$expected_extractor" ]] ||
	fail 'qualified QEMU extractor changed'
[[ $(sha256sum "$manifest_script" | cut -d ' ' -f 1) == \
	"$expected_manifest" ]] ||
	fail 'rootfs manifest implementation changed'

check_archive() {
	path=$1
	size=$2
	archive_sha=$3
	content_sha=$4
	[[ -f $path && ! -L $path ]] ||
		fail "missing or linked builder manifest: ${path#"$repo"/}"
	[[ $(stat -c %s "$path") == "$size" ]] ||
		fail "builder manifest size changed: ${path#"$repo"/}"
	[[ $(sha256sum "$path" | cut -d ' ' -f 1) == "$archive_sha" ]] ||
		fail "builder manifest archive changed: ${path#"$repo"/}"
	gzip -t "$path"
	[[ $(gzip -dc "$path" | sha256sum | cut -d ' ' -f 1) == \
		"$content_sha" ]] ||
		fail "builder manifest content changed: ${path#"$repo"/}"
}

check_archive \
	"$repo/artifacts/recovery-builder-deck-v1/responder-rootfs.tsv.gz" \
	103012 613a6c47c60411b2b1715af2f7e6ccb53141b12134063d668aa40c091f998104 \
	"$responder_rootfs"
check_archive \
	"$repo/artifacts/recovery-builder-deck-v1/responder-packages.txt.gz" \
	959 909b98b65e895156872b4ccb34b0d8e7f2582415bef0f1fe78556aad607847b5 \
	"$responder_packages"
check_archive \
	"$repo/artifacts/recovery-builder-deck-v1/verifier-rootfs.tsv.gz" \
	110193 171adcb04ffdc4db79ed3dc494ed3e29bc1664afcc024dfaa9e22a31f194ac54 \
	"$verifier_rootfs"
check_archive \
	"$repo/artifacts/recovery-builder-deck-v1/verifier-packages.txt.gz" \
	1063 f1a195750b2b7c40b5aaba3ce1be3fa7f9aeef6959ffaee5108a7283b62f468c \
	"$verifier_packages"

check_image() {
	image=$1
	expected_id=$2
	expected_digest=$3
	expected_rootfs=$4
	expected_packages=$5
	podman image exists "$image" ||
		fail "missing qualified recovery-builder image: $image"
	[[ $(podman image inspect "$image" --format '{{.Architecture}}') == arm64 ]] ||
		fail "recovery-builder architecture changed: $image"
	[[ $(podman image inspect "$image" --format '{{.Id}}') == \
		"$expected_id" ]] ||
		fail "recovery-builder image ID changed: $image"
	[[ $(podman image inspect "$image" --format '{{.Digest}}') == \
		"$expected_digest" ]] ||
		fail "recovery-builder image digest changed: $image"
	live_rootfs=$(
		"$runner" podman run --rm --pull=never --network=none \
			--platform linux/arm64 \
			-v "$repo:/workspace:ro" "$image" \
			/workspace/scripts/host/kernel-builder-rootfs-manifest.sh |
			sha256sum | cut -d ' ' -f 1
	)
	[[ $live_rootfs == "$expected_rootfs" ]] ||
		fail "recovery-builder rootfs identity changed: $image"
	live_packages=$(
		"$runner" podman run --rm --pull=never --network=none \
			--platform linux/arm64 "$image" sh -c \
			'apk info -vv 2>/dev/null | LC_ALL=C sort' |
			sha256sum | cut -d ' ' -f 1
	)
	[[ $live_packages == "$expected_packages" ]] ||
		fail "recovery-builder package identity changed: $image"
}

check_image "$responder_image" "$responder_id" "$responder_digest" \
	"$responder_rootfs" "$responder_packages"
check_image "$verifier_image" "$verifier_id" "$verifier_digest" \
	"$verifier_rootfs" "$verifier_packages"

printf 'profile_sha256=%s\n' "$expected_profile"
printf 'responder_image_id=%s responder_rootfs=%s\n' \
	"$responder_id" "$responder_rootfs"
printf 'verifier_image_id=%s verifier_rootfs=%s\n' \
	"$verifier_id" "$verifier_rootfs"
echo 'PASS qualified rootless Steam Deck ARM64 recovery builders'
