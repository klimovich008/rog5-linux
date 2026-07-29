#!/usr/bin/env bash
set -euo pipefail

fail() {
	echo "FAIL $*" >&2
	exit 1
}

repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
output_root=${1:?usage: build-corrected-headless-candidate-offline.sh OUTPUT_ROOT}
candidate=headless-network-root-v1
expected_dtb=86e5cb81191e3de39c9527b838fa03d78744cd9b0d862336f0c1f36a9f534f46
builder_image=localhost/rog5-kernel-builder:ubuntu-24.04
expected_builder_id=c5b80647ddd7fb29464b4735abbe27012ee4dc89be559b44b25c9b1ff59c9cec
expected_builder_digest=sha256:8513960144bb1ca77878a1364c03fb100c8b87fffb8440fd37a6cc4fc0043b41
secret_root=

cleanup() {
	if [[ -n $secret_root && -d $secret_root && $secret_root != / ]]; then
		chmod -R u+rwX -- "$secret_root" 2>/dev/null || true
		rm -rf -- "$secret_root"
	fi
}
trap cleanup EXIT HUP INT TERM

for command in cmp cut find gcc git grep mkdir mktemp openssl podman \
	python3 realpath rm sed sha256sum stat tail; do
	command -v "$command" >/dev/null ||
		fail "missing corrected-candidate command: $command"
done

output_root=$(realpath -m "$output_root")
case $output_root in
	"$repo"/build/*) ;;
	*) fail 'output root must be below the ignored repository build directory' ;;
esac
git -C "$repo" check-ignore -q "$output_root" ||
	fail 'output root is not ignored by Git'
[[ ! -d $output_root ||
	-z $(find "$output_root" -mindepth 1 -maxdepth 1 -print -quit) ]] ||
	fail 'refusing nonempty corrected-candidate output root'

podman image exists "$builder_image" ||
	fail 'accepted snapshot kernel builder is unavailable'
[[ $(podman image inspect "$builder_image" --format '{{.Id}}') == \
	"$expected_builder_id" ]] ||
	fail 'accepted snapshot kernel builder ID changed'
[[ $(podman image inspect "$builder_image" --format '{{.Digest}}') == \
	"$expected_builder_digest" ]] ||
	fail 'accepted snapshot kernel builder digest changed'

secret_root=$(mktemp -d)
private_key=$secret_root/disposable-ed25519.pem
public_key=$secret_root/disposable-ed25519.raw
openssl genpkey -algorithm ED25519 -out "$private_key" 2>/dev/null
chmod 0600 "$private_key"
openssl pkey -in "$private_key" -pubout -outform DER 2>/dev/null |
	tail -c 32 >"$public_key"
chmod 0400 "$public_key"
[[ $(stat -c '%u:%a:%s' "$private_key") == "$(id -u):600:"* &&
	$(stat -c %s "$private_key") -gt 0 ]] ||
	fail 'disposable private key metadata is unsafe'
[[ $(stat -c '%u:%a:%s' "$public_key") == "$(id -u):400:32" ]] ||
	fail 'disposable public key metadata is unsafe'

mkdir -p "$output_root"
RECOVERY_TEST_PUBLIC_KEY=$public_key \
	"$repo/scripts/host/test-stable-recovery-initramfs.sh" \
	"$output_root/recovery"
cmp "$public_key" "$output_root/recovery/ephemeral-public.raw"

bundle_a=$output_root/bundle-a
bundle_b=$output_root/bundle-b
mkdir -m 0700 "$bundle_a" "$bundle_b"
for suffix in a b; do
	bundle_root=$output_root/bundle-$suffix
	"$repo/scripts/host/prepare-recovery-candidate.py" \
		"$candidate" \
		--private-key "$private_key" \
		--bundle-root "$bundle_root" \
		>"$output_root/candidate-$suffix.txt"
	grep -Fxq "candidate=$candidate" "$output_root/candidate-$suffix.txt"
	grep -Fxq 'status=offline' "$output_root/candidate-$suffix.txt"
	grep -Fxq 'authority=none' "$output_root/candidate-$suffix.txt"
done

manifest_a=$(
	sed -n 's/^manifest_sha256=//p' "$output_root/candidate-a.txt"
)
manifest_b=$(
	sed -n 's/^manifest_sha256=//p' "$output_root/candidate-b.txt"
)
trust_a=$(sed -n 's/^trust_key_sha256=//p' "$output_root/candidate-a.txt")
trust_b=$(sed -n 's/^trust_key_sha256=//p' "$output_root/candidate-b.txt")
[[ $manifest_a =~ ^[0-9a-f]{64}$ && $manifest_a == "$manifest_b" ]] ||
	fail 'twin corrected candidate manifests differ'
[[ $trust_a =~ ^[0-9a-f]{64}$ && $trust_a == "$trust_b" &&
	$trust_a == "$(sha256sum "$public_key" | cut -d ' ' -f 1)" ]] ||
	fail 'corrected candidate trust-root identity differs'

bundle_path_a=$bundle_a/$candidate
bundle_path_b=$bundle_b/$candidate
for name in Image board.dtb initramfs.cpio.gz manifest manifest.sig; do
	cmp "$bundle_path_a/$name" "$bundle_path_b/$name"
	[[ $(stat -c '%a:%s' "$bundle_path_a/$name") == \
		"$(stat -c '%a:%s' "$bundle_path_b/$name")" ]] ||
		fail "twin corrected candidate metadata differs: $name"
done
[[ $(sha256sum "$bundle_path_a/board.dtb" | cut -d ' ' -f 1) == \
	"$expected_dtb" ]] ||
	fail 'corrected candidate does not contain the accepted isolated DTB'

host_verifier=$output_root/recovery/components/rog5-bundle-verify-host-test
gcc -std=c11 -O2 -fPIE -pie -fstack-protector-strong \
	-Wall -Wextra -Werror \
	-Wl,-z,relro,-z,now,-z,noexecstack,--build-id=none \
	-DROG5_BUNDLE_TESTING=1 \
	"$repo/tools/recovery_control/rog5-bundle-verify.c" \
	-o "$host_verifier" -lcrypto -lz
chmod 0755 "$host_verifier"

plan_a=$(
	"$host_verifier" --bundle-root "$bundle_a" \
		--trust-key "$public_key" "$candidate" "$manifest_a"
)
plan_b=$(
	"$host_verifier" --bundle-root "$bundle_b" \
		--trust-key "$public_key" "$candidate" "$manifest_b"
)
[[ $plan_a == "$plan_b" ]] ||
	fail 'native verifier produced different twin execution plans'
grep -Fxq "bundle=$candidate" <<<"$plan_a"
grep -Fxq "manifest_sha256=$manifest_a" <<<"$plan_a"
grep -Fxq 'profile=network-root-v1' <<<"$plan_a"
grep -Fxq 'target_id=headless-network-root' <<<"$plan_a"
grep -Fxq 'target_release=7.1.4-g7a5cef0db479' <<<"$plan_a"

KERNEL_BUILDER_IMAGE=$builder_image \
	"$repo/scripts/host/test-stable-recovery-wrapper-offline.sh" \
	"$output_root/recovery/initramfs-a/rog5-stable-recovery.cpio.gz" \
	"$output_root/recovery/initramfs-b/rog5-stable-recovery.cpio.gz" \
	"$output_root/wrapper"

python3 "$repo/scripts/host/test-prepare-recovery-candidate.py"
python3 "$repo/scripts/host/test-recovery-candidate-integration.py"

sha256sum \
	"$output_root/recovery/ephemeral-public.raw" \
	"$output_root/recovery/initramfs-a/rog5-stable-recovery.cpio.gz" \
	"$bundle_path_a/manifest" \
	"$bundle_path_a/board.dtb" \
	"$output_root/wrapper/wrapper-a/asus-kexec-stage/arch/arm64/boot/Image" \
	"$output_root/wrapper/repack/stable-recovery-a.raw.img" \
	"$output_root/wrapper/repack/stable-recovery-a.avb.img" \
	>"$output_root/SHA256SUMS"

private_key_path=$private_key
cleanup
secret_root=
[[ ! -e $private_key_path ]] ||
	fail 'disposable private key survived offline candidate build'

printf 'candidate=%s\nmanifest_sha256=%s\ntrust_key_sha256=%s\n' \
	"$candidate" "$manifest_a" "$trust_a"
echo 'authority=none'
echo 'PASS twin corrected-DTB candidate, signed bundle, recovery wrapper, and hardware-free gate; disposable private key destroyed'
