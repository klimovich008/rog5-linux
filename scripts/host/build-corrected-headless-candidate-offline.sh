#!/usr/bin/env bash
set -euo pipefail

fail() {
	echo "FAIL $*" >&2
	exit 1
}

repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
output_root=${1:?usage: build-corrected-headless-candidate-offline.sh OUTPUT_ROOT}
candidate=${ROG5_OFFLINE_CANDIDATE:-headless-network-root-v1}
expected_dtb=${ROG5_OFFLINE_EXPECTED_DTB:-86e5cb81191e3de39c9527b838fa03d78744cd9b0d862336f0c1f36a9f534f46}
expected_target=${ROG5_OFFLINE_EXPECTED_TARGET:-headless-network-root}
wrapper_jobs=${ROG5_OFFLINE_WRAPPER_JOBS:-8}
deployment_build=${ROG5_DEPLOYMENT_BUILD:-0}
deployment_candidate_record=${ROG5_DEPLOYMENT_CANDIDATE_RECORD:-}
deployment_private_key=${ROG5_DEPLOYMENT_SIGNING_KEY:-}
builder_image=localhost/rog5-kernel-builder:ubuntu-24.04
builder_verifier=$repo/scripts/host/verify-steam-deck-builder.sh
qualified_shims=$repo/scripts/host/qualified-tool-shims
qualified_cpio_path=$repo/scripts/host/qualified-cpio-path
arm64_runner=$repo/scripts/host/run-private-arm64-binfmt.sh
deployment_input_stager=$repo/scripts/host/stage-headless-ssh-deployment-signing-inputs.py
secret_root=

[[ $expected_dtb =~ ^[0-9a-f]{64}$ ]] ||
	fail 'offline candidate DTB identity is malformed'
[[ $wrapper_jobs =~ ^[1-9][0-9]*$ ]] ||
	fail 'offline wrapper jobs must be a positive integer'
case $deployment_build in
0|1) ;;
*) fail 'deployment-build selector must be zero or one' ;;
esac
case "$candidate:$expected_dtb:$expected_target" in
	headless-network-root-v1:86e5cb81191e3de39c9527b838fa03d78744cd9b0d862336f0c1f36a9f534f46:headless-network-root) ;;
	headless-core-network-root-v2:57216474b4c8979161d964cef2ff3fe5d61500af3cef34598ee06e03e91f967d:headless-core-network-root) ;;
	headless-ssh-network-root-v3:86e5cb81191e3de39c9527b838fa03d78744cd9b0d862336f0c1f36a9f534f46:headless-ssh-network-root) ;;
	*) fail 'unsupported offline candidate identity tuple' ;;
esac
if [[ $deployment_build == 1 ]]; then
	[[ ${ALLOW_HEADLESS_SSH_DEPLOYMENT_BUILD:-} == 1 ]] ||
		fail 'set ALLOW_HEADLESS_SSH_DEPLOYMENT_BUILD=1 for one signed deployment build'
	[[ ${ALLOW_PHONE_CREDENTIAL_USE:-} == 1 ]] ||
		fail 'set ALLOW_PHONE_CREDENTIAL_USE=1 before using the signing key'
	[[ $candidate == headless-ssh-network-root-v3 &&
		$expected_target == headless-ssh-network-root ]] ||
		fail 'credentialed build is limited to the SSH deployment candidate'
	[[ -n $deployment_candidate_record && -n $deployment_private_key ]] ||
		fail 'deployment candidate record and signing key are required'
else
	[[ -z $deployment_candidate_record && -z $deployment_private_key ]] ||
		fail 'offline build rejects deployment credential inputs'
fi

cleanup() {
	if [[ -n $secret_root && -d $secret_root && $secret_root != / ]]; then
		chmod -R u+rwX -- "$secret_root" 2>/dev/null || true
		rm -rf -- "$secret_root"
	fi
}
trap cleanup EXIT HUP INT TERM

for command in cmp cut find git grep mkdir mktemp openssl podman python3 \
	realpath rm sed sha256sum stat tail; do
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

[[ -f $builder_verifier && ! -L $builder_verifier &&
	-x $builder_verifier ]] ||
	fail 'missing qualified Steam Deck builder verifier'
[[ -x $qualified_shims/cpio && -f $qualified_shims/cpio &&
	! -L $qualified_shims/cpio ]] ||
	fail 'missing qualified Steam Deck cpio shim'
[[ -x $qualified_cpio_path/cpio && -f $qualified_cpio_path/cpio &&
	! -L $qualified_cpio_path/cpio ]] ||
	fail 'missing isolated qualified cpio command path'
[[ -x $arm64_runner && -f $arm64_runner && ! -L $arm64_runner ]] ||
	fail 'missing private rootless ARM64 runner'
[[ -x $deployment_input_stager && -f $deployment_input_stager &&
	! -L $deployment_input_stager ]] ||
	fail 'missing deployment signing-input stager'

secret_root=$(mktemp -d)
private_key=$secret_root/signing-ed25519.pem
public_key=$secret_root/signing-ed25519.raw
if [[ $deployment_build == 1 ]]; then
	candidate_record=$secret_root/candidate.json
	"$deployment_input_stager" \
		--repository "$repo" \
		--signing-key "$deployment_private_key" \
		--candidate-record "$deployment_candidate_record" \
		--staged-key "$private_key" \
		--staged-candidate "$candidate_record" \
		--raw-public-key "$public_key" \
		>"$secret_root/deployment-input-admission.txt"
	grep -Fxq \
		'format=rog5-headless-ssh-deployment-signing-inputs-v1' \
		"$secret_root/deployment-input-admission.txt" ||
		fail 'deployment signing-input admission did not pass'
	grep -Fxq 'authority=none' \
		"$secret_root/deployment-input-admission.txt" ||
		fail 'deployment signing-input admission returned authority'
	candidate_record_sha256=$(
		sed -n 's/^candidate_record_sha256=//p' \
			"$secret_root/deployment-input-admission.txt"
	)
	[[ $candidate_record_sha256 =~ ^[0-9a-f]{64}$ &&
		$candidate_record_sha256 == \
		"$(sha256sum "$candidate_record" | cut -d ' ' -f 1)" ]] ||
		fail 'staged deployment candidate identity changed'
else
	openssl genpkey -algorithm ED25519 -out "$private_key" 2>/dev/null
	chmod 0600 "$private_key"
	openssl pkey -in "$private_key" -pubout -outform DER 2>/dev/null |
		tail -c 32 >"$public_key"
	chmod 0400 "$public_key"
fi
[[ $(stat -c '%u:%a:%s' "$private_key") == "$(id -u):600:"* &&
	$(stat -c %s "$private_key") -gt 0 ]] ||
	fail 'private signing-key snapshot metadata is unsafe'
[[ $(stat -c '%u:%a:%s' "$public_key") == "$(id -u):400:32" ]] ||
	fail 'raw Ed25519 public-key metadata is unsafe'

mkdir -p "$output_root"
"$builder_verifier" "$builder_image" \
	>"$output_root/builder-qualification.txt"
grep -Fxq 'PASS qualified Steam Deck ASUS 5.4 kernel builder' \
	"$output_root/builder-qualification.txt" ||
	fail 'Steam Deck builder verifier did not return its success marker'
"$arm64_runner" env \
	PATH="$qualified_cpio_path:/usr/bin:/bin:/usr/sbin:/sbin" \
	RECOVERY_TEST_PUBLIC_KEY="$public_key" \
	ROG5_RECOVERY_BASE_PROFILE=reconstructed-v18r-v1 \
	"$repo/scripts/host/test-stable-recovery-initramfs.sh" \
	"$output_root/recovery"
cmp "$public_key" "$output_root/recovery/ephemeral-public.raw"

bundle_a=$output_root/bundle-a
bundle_b=$output_root/bundle-b
mkdir -m 0700 "$bundle_a" "$bundle_b"
candidate_record_arguments=()
if [[ $deployment_build == 1 ]]; then
	candidate_record_arguments=(
		--candidate-record
		"$candidate_record"
		--candidate-record-sha256
		"$candidate_record_sha256"
	)
fi
for suffix in a b; do
	bundle_root=$output_root/bundle-$suffix
	"$repo/scripts/host/prepare-recovery-candidate.py" \
		"$candidate" \
		--private-key "$private_key" \
		--bundle-root "$bundle_root" \
		"${candidate_record_arguments[@]}" \
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
host_verifier_relative=${host_verifier#"$output_root"/}
podman run --rm --network=none --security-opt label=disable \
	-v "$repo:/workspace:ro" \
	-v "$output_root:/out" \
	--workdir /workspace \
	"$builder_image" \
	gcc -std=c11 -O2 -fPIE -pie -fstack-protector-strong \
	-Wall -Wextra -Werror \
	-Wl,-z,relro,-z,now,-z,noexecstack,--build-id=none \
	-DROG5_BUNDLE_TESTING=1 \
	tools/recovery_control/rog5-bundle-verify.c \
	-o "/out/$host_verifier_relative" -lcrypto -lz
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
grep -Fxq "target_id=$expected_target" <<<"$plan_a"
grep -Fxq 'target_release=7.1.4-g7a5cef0db479' <<<"$plan_a"

KERNEL_BUILDER_IMAGE=$builder_image \
ROG5_WRAPPER_BUILDER_PROFILE=steam-deck-asus-5.4-v1 \
JOBS=$wrapper_jobs \
	"$repo/scripts/host/test-stable-recovery-wrapper-offline.sh" \
	"$output_root/recovery/initramfs-a/rog5-stable-recovery.cpio.gz" \
	"$output_root/recovery/initramfs-b/rog5-stable-recovery.cpio.gz" \
	"$output_root/wrapper"

for test_script in \
	scripts/host/test-prepare-recovery-candidate.py \
	scripts/host/test-recovery-candidate-integration.py; do
	podman run --rm --network=none --security-opt label=disable \
		-v "$repo:/workspace:ro" \
		--workdir /workspace \
		"$builder_image" python3 "$test_script"
done

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
	fail 'private signing-key snapshot survived candidate build'

printf 'candidate=%s\nmanifest_sha256=%s\ntrust_key_sha256=%s\n' \
	"$candidate" "$manifest_a" "$trust_a"
echo 'authority=none'
if [[ $deployment_build == 1 ]]; then
	echo 'PASS twin credential-bound deployment candidate, signed bundle, recovery wrapper, and hardware-free gate; source key verified and private snapshot destroyed'
else
	echo 'PASS twin corrected-DTB candidate, signed bundle, recovery wrapper, and hardware-free gate; disposable private key destroyed'
fi
