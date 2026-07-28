#!/usr/bin/env bash
set -euo pipefail

fail() {
	echo "FAIL $*" >&2
	exit 1
}

repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
base=$repo/artifacts/recovery-stage-v18/rog5-recovery-initramfs.cpio.gz
wrapper_config=$repo/artifacts/recovery-stage-v18/config-5.4.210-kexec-stage-builtin-recovery
kexec_apk=$repo/artifacts/recovery-inputs/kexec-tools-2.0.32-r2.apk
xz_apk=$repo/artifacts/recovery-inputs/xz-libs-5.8.3-r0.apk
zstd_apk=$repo/artifacts/recovery-inputs/zstd-libs-1.5.7-r2.apk
base_image=localhost/rog5-persistent-root-verifier:alpine-3.24
verifier_image=localhost/rog5-recovery-bundle-verifier:alpine-3.24-openssl-3.5.7

for command in cmp head openssl podman sha256sum tail; do
	command -v "$command" >/dev/null ||
		fail "missing stable-recovery test command: $command"
done
for input in "$base" "$wrapper_config" "$kexec_apk" "$xz_apk" "$zstd_apk"; do
	[[ -f $input && ! -L $input ]] ||
		fail "missing regular ignored recovery input: $input"
done
[[ $(sha256sum "$base" | cut -d ' ' -f 1) == \
	852b02a2cbcb2dfd43598269ff1b2b10cb1542e90ab7a7aa32d1a26c7cc645fc ]] ||
	fail 'unexpected accepted v18 recovery-base hash'
[[ $(sha256sum "$wrapper_config" | cut -d ' ' -f 1) == \
	df28224e6e8d2dfc825ac49dc9f6bdeb12bbcdae2dff92cbbf14a8a94177578f ]] ||
	fail 'unexpected accepted v18 wrapper-config hash'
for setting in \
	CONFIG_KEXEC=y \
	CONFIG_MEMFD_CREATE=y \
	CONFIG_NAMESPACES=y \
	CONFIG_NET_NS=y \
	CONFIG_SECCOMP=y \
	CONFIG_SECCOMP_FILTER=y \
	CONFIG_TMPFS=y \
	CONFIG_USB_CONFIGFS=y \
	CONFIG_USB_F_ACM=y \
	CONFIG_USB_F_NCM=y
do
	grep -qx "$setting" "$wrapper_config" ||
		fail "wrapper kernel lacks fixed-control prerequisite: $setting"
done

for image in "$base_image" "$verifier_image"; do
	podman image exists "$image" ||
		fail "missing pinned local AArch64 image: $image"
	[[ $(podman image inspect "$image" --format '{{.Architecture}}') == arm64 ]] ||
		fail "build image is not arm64: $image"
done
[[ $(podman image inspect "$base_image" --format '{{.Id}}') == \
	d5fb16636fadea937b74dc3e062617d74a12577fd3fcc3f61fec24d0f7364495 ]] ||
	fail 'unexpected base AArch64 builder image ID'
[[ $(podman image inspect "$base_image" --format '{{.Digest}}') == \
	sha256:750150c51c8b5085d322ecaa5363356bb31ee243d6efab1035bd15f5ffe52355 ]] ||
	fail 'unexpected base AArch64 builder digest'
[[ $(podman image inspect "$verifier_image" --format '{{.Id}}') == \
	e2e90f8ad3cfc4f9b7660ee8828fcae008792f05567fb9b4efd3ab0102063d8e ]] ||
	fail 'unexpected verifier AArch64 builder image ID'
[[ $(podman image inspect "$verifier_image" --format '{{.Digest}}') == \
	sha256:b4946b74324785d005aa3067dd18788f90cc65215a519c8735dce03aa01d1268 ]] ||
	fail 'unexpected verifier AArch64 builder digest'

test_tmp=$(mktemp -d)
trap 'rm -rf -- "$test_tmp"' EXIT HUP INT TERM

build_static() {
	image=$1
	build_script=$2
	source_file=$3
	output=$4
	podman run --rm --network=none --platform linux/arm64 \
		-v "$repo:/workspace:ro,Z" \
		-v "$test_tmp:/out:Z" \
		"$image" \
		"/workspace/$build_script" \
		"/workspace/$source_file" "/out/$output"
}

for suffix in a b; do
	build_static "$base_image" \
		scripts/device/build-recovery-control.sh \
		tools/recovery_control/rog5-recovery-control.c \
		"rog5-recovery-control-$suffix"
	build_static "$base_image" \
		scripts/device/build-recovery-bundle-fetcher.sh \
		tools/recovery_control/rog5-bundle-fetch.c \
		"rog5-bundle-fetch-$suffix"
	build_static "$verifier_image" \
		scripts/device/build-recovery-bundle-verifier.sh \
		tools/recovery_control/rog5-bundle-verify.c \
		"rog5-bundle-verify-$suffix"
done
for binary in rog5-recovery-control rog5-bundle-fetch rog5-bundle-verify; do
	cmp "$test_tmp/$binary-a" "$test_tmp/$binary-b"
done

# The ephemeral private key exists only in the pipeline and is never written.
openssl genpkey -algorithm ED25519 2>/dev/null |
	openssl pkey -pubout -outform DER 2>/dev/null |
	tail -c 32 >"$test_tmp/ephemeral-public.raw"
chmod 0600 "$test_tmp/ephemeral-public.raw"
[[ $(stat -c %s "$test_tmp/ephemeral-public.raw") == 32 ]]

for suffix in a b; do
	"$repo/scripts/device/build-stable-recovery-initramfs.sh" \
		"$base" "$repo/initramfs/recovery-init" \
		"$test_tmp/rog5-recovery-control-a" \
		"$test_tmp/rog5-bundle-fetch-a" \
		"$test_tmp/rog5-bundle-verify-a" \
		"$kexec_apk" "$xz_apk" "$zstd_apk" \
		"$test_tmp/ephemeral-public.raw" \
		"$test_tmp/stable-recovery-$suffix.cpio.gz"
	"$repo/scripts/device/verify-stable-recovery-initramfs.sh" \
		"$test_tmp/stable-recovery-$suffix.cpio.gz" \
		"$repo/initramfs/recovery-init" \
		"$test_tmp/rog5-recovery-control-a" \
		"$test_tmp/rog5-bundle-fetch-a" \
		"$test_tmp/rog5-bundle-verify-a" \
		"$test_tmp/ephemeral-public.raw"
done
cmp "$test_tmp/stable-recovery-a.cpio.gz" \
	"$test_tmp/stable-recovery-b.cpio.gz"

head -c 31 "$test_tmp/ephemeral-public.raw" >"$test_tmp/short-public.raw"
if "$repo/scripts/device/build-stable-recovery-initramfs.sh" \
	"$base" "$repo/initramfs/recovery-init" \
	"$test_tmp/rog5-recovery-control-a" \
	"$test_tmp/rog5-bundle-fetch-a" \
	"$test_tmp/rog5-bundle-verify-a" \
	"$kexec_apk" "$xz_apk" "$zstd_apk" \
	"$test_tmp/short-public.raw" \
	"$test_tmp/should-not-build.cpio.gz" \
	>"$test_tmp/short-key.log" 2>&1
then
	fail '31-byte public key passed the stable recovery builder'
fi
grep -qx 'FAIL Ed25519 public key must contain exactly 32 raw bytes' \
	"$test_tmp/short-key.log"

head -c 32 /dev/zero >"$test_tmp/zero-public.raw"
if "$repo/scripts/device/build-stable-recovery-initramfs.sh" \
	"$base" "$repo/initramfs/recovery-init" \
	"$test_tmp/rog5-recovery-control-a" \
	"$test_tmp/rog5-bundle-fetch-a" \
	"$test_tmp/rog5-bundle-verify-a" \
	"$kexec_apk" "$xz_apk" "$zstd_apk" \
	"$test_tmp/zero-public.raw" \
	"$test_tmp/should-not-build-zero.cpio.gz" \
	>"$test_tmp/zero-key.log" 2>&1
then
	fail 'all-zero public key passed the stable recovery builder'
fi
grep -qx 'FAIL Ed25519 public key must not be all zero' \
	"$test_tmp/zero-key.log"

sha256sum \
	"$test_tmp/rog5-recovery-control-a" \
	"$test_tmp/rog5-bundle-fetch-a" \
	"$test_tmp/rog5-bundle-verify-a" \
	"$test_tmp/stable-recovery-a.cpio.gz" \
	"$test_tmp/stable-recovery-b.cpio.gz"
echo 'PASS reproducible stable-recovery integration with ephemeral public-key test boundary'
