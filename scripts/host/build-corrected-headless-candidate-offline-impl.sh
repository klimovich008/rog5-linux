#!/usr/bin/bash
# Internal implementation. A credentialed public launcher executes these
# exact bytes from a sealed memfd with a fixed, startup-hook-free environment.
set -euo pipefail

PATH=/usr/bin:/bin
export PATH
unset -f bash chmod cmp cp cut dirname env find git grep id mkdir mktemp mv \
	openssl podman python3 realpath rm sed sha256sum stat tail 2>/dev/null || true

# Credential paths may arrive as exported wrapper inputs. Capture them in an
# unexportable array and remove the source environment before any child can
# inherit them.
unset deployment_credential_paths deployment_candidate_record \
	deployment_private_key secret_root private_key public_key \
	candidate_record private_key_path internal_repository \
	internal_checkpoint_repository internal_repository_commit \
	internal_implementation_sealed
internal_repository=${ROG5_INTERNAL_REPOSITORY_ROOT:-}
internal_checkpoint_repository=${ROG5_INTERNAL_CHECKPOINT_REPOSITORY_ROOT:-}
internal_repository_commit=${ROG5_INTERNAL_REPOSITORY_COMMIT:-}
internal_implementation_sealed=${ROG5_INTERNAL_IMPLEMENTATION_SEALED:-0}
deployment_credential_paths=(
	"${ROG5_DEPLOYMENT_CANDIDATE_RECORD:-}"
	"${ROG5_DEPLOYMENT_SIGNING_KEY:-}"
)
unset ROG5_DEPLOYMENT_CANDIDATE_RECORD ROG5_DEPLOYMENT_SIGNING_KEY
unset ROG5_INTERNAL_REPOSITORY_ROOT \
	ROG5_INTERNAL_CHECKPOINT_REPOSITORY_ROOT \
	ROG5_INTERNAL_REPOSITORY_COMMIT ROG5_INTERNAL_IMPLEMENTATION_SEALED
deployment_candidate_record=${deployment_credential_paths[0]}
deployment_private_key=${deployment_credential_paths[1]}
unset deployment_credential_paths

fail() {
	echo "FAIL $*" >&2
	exit 1
}

if [[ -n $internal_repository ]]; then
	case $internal_repository in
	/*) ;;
	*) fail 'internal repository root is not absolute' ;;
	esac
	[[ -d $internal_repository && ! -L $internal_repository ]] ||
		fail 'internal repository root metadata is unsafe'
	[[ $(realpath -e -- "$internal_repository") == "$internal_repository" ]] ||
		fail 'internal repository root is not canonical'
	repo=$internal_repository
else
	repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
fi
checkpoint_repository=$repo
requested_output_root=${1:?usage: build-corrected-headless-candidate-offline.sh OUTPUT_ROOT}
candidate=${ROG5_OFFLINE_CANDIDATE:-headless-network-root-v1}
expected_dtb=${ROG5_OFFLINE_EXPECTED_DTB:-86e5cb81191e3de39c9527b838fa03d78744cd9b0d862336f0c1f36a9f534f46}
expected_target=${ROG5_OFFLINE_EXPECTED_TARGET:-headless-network-root}
wrapper_jobs=${ROG5_OFFLINE_WRAPPER_JOBS:-8}
deployment_build=${ROG5_DEPLOYMENT_BUILD:-0}
deployment_input_preflight=${ROG5_DEPLOYMENT_SIGNING_INPUT_PREFLIGHT:-0}
builder_image=localhost/rog5-kernel-builder:ubuntu-24.04
builder_verifier=$repo/scripts/host/verify-steam-deck-builder.sh
qualified_shims=$repo/scripts/host/qualified-tool-shims
qualified_cpio_path=$repo/scripts/host/qualified-cpio-path
arm64_runner=$repo/scripts/host/run-private-arm64-binfmt.sh
deployment_input_stager=$repo/scripts/host/stage-recovery-deployment-signing-inputs.py
secret_root=
snapshot_active=0

[[ $expected_dtb =~ ^[0-9a-f]{64}$ ]] ||
	fail 'offline candidate DTB identity is malformed'
[[ $wrapper_jobs =~ ^[1-9][0-9]*$ ]] ||
	fail 'offline wrapper jobs must be a positive integer'
case $deployment_build in
0|1) ;;
*) fail 'deployment-build selector must be zero or one' ;;
esac
case $deployment_input_preflight in
0|1) ;;
*) fail 'deployment signing-input preflight selector must be zero or one' ;;
esac
[[ $deployment_input_preflight == 0 || $deployment_build == 1 ]] ||
	fail 'signing-input preflight requires a deployment build'
case "$candidate:$expected_dtb:$expected_target" in
	headless-network-root-v1:86e5cb81191e3de39c9527b838fa03d78744cd9b0d862336f0c1f36a9f534f46:headless-network-root)
		expected_profile=network-root-v1
		expected_candidate_sha=b8a1f70f394e1a13831f46377c193de5f705d1a3768bc6acb6f84cdf13c17f3c
		expected_manifest=d7a02a2403caf885a015060a8361019936e86efafde44f3bb7e6bdd48d2ee32d ;;
	headless-core-network-root-v2:57216474b4c8979161d964cef2ff3fe5d61500af3cef34598ee06e03e91f967d:headless-core-network-root)
		expected_profile=network-root-v1
		expected_candidate_sha=b5a1a25c2a79b08373fdf6222f793e80d92af2cf3c62aa278dd339ca168e008f
		expected_manifest=f7316f6a02c041f345c4e079d93bccb8b1b566a6ecf3a9c16d16cc46a4affa32 ;;
	headless-ssh-network-root-v3:86e5cb81191e3de39c9527b838fa03d78744cd9b0d862336f0c1f36a9f534f46:headless-ssh-network-root)
		expected_profile=network-root-v1
		expected_candidate_sha=09e14f26e1cd3e6b6b033a4c565148187c55c3320a0fb2640c2937ff2e00b306
		expected_manifest=a409f0ebad410edf8fb36e31d322029bf69d4c6621ddab84a660ff471da48e11 ;;
	headless-netroot-early-diag-v1:86e5cb81191e3de39c9527b838fa03d78744cd9b0d862336f0c1f36a9f534f46:headless-netroot-early-diag)
		expected_profile=diagnostic-initramfs-v1
		expected_candidate_sha=7081a0c77158ed695e62751e152baff101b18a9b364640c0cbffd6ef8ba1c6e8
		expected_manifest=4eacb90f08a80af1bdfed704c4a5e0d8eff600e94191c18c066b23b1228f7e76 ;;
	headless-netroot-early-diag-v2:86e5cb81191e3de39c9527b838fa03d78744cd9b0d862336f0c1f36a9f534f46:headless-netroot-early-diag-v2)
		expected_profile=diagnostic-initramfs-v1
		expected_candidate_sha=f23626d6ad0b15a660835bd8419cde40a8f8c3c79f83b6feca5cb57952f7b1ab
		expected_manifest=98a4c4381c90c5d8edd7252309fe438d18f66af0a5ccd47f2cec7ec39e8f971d ;;
	headless-full-ucsi-charging-v1:3f4305d7fbbd2c74d15c1011bb8a2e8e24b3a5228f31ed86281917d16cf18f11:headless-full-ucsi-charging)
		expected_profile=network-root-v1
		expected_candidate_sha=24f1289d31061295c3656029ed31d6a83bc0e3de68b0e40fb61b2022930fa626
		expected_manifest=edb9ca09bd059134647428083cc834fcbe3299a1228890d368244be7d9a68bc0 ;;
	headless-full-ucsi-charging-v2:3f4305d7fbbd2c74d15c1011bb8a2e8e24b3a5228f31ed86281917d16cf18f11:headless-full-ucsi-charging-v2)
		expected_profile=network-root-v1
		expected_candidate_sha=23200e26557bdc66f942faa64c36dadde37c6d09e98feadd6c38a0439ab3b3c2
		expected_manifest=085a2173cf3bb1c0066a63cbf864773b53a4c9df40a66160129b0c4e64f6ac21 ;;
	headless-full-ucsi-charging-v3:3f4305d7fbbd2c74d15c1011bb8a2e8e24b3a5228f31ed86281917d16cf18f11:headless-full-ucsi-charging-v3)
		expected_profile=network-root-v1
		expected_candidate_sha=6e0bcb6704550f000623590e476eb0b58f00279043b47bfb7a21bcdc08130f1f
		expected_manifest=c3a3baded37ec0f7e1259d13efdc7c31712573cc834e497e7f830bef6d7de3dc ;;
	headless-full-ucsi-charging-early-v1:3f4305d7fbbd2c74d15c1011bb8a2e8e24b3a5228f31ed86281917d16cf18f11:headless-full-ucsi-charging-early-v1)
		expected_profile=diagnostic-initramfs-v1
		expected_candidate_sha=680c6663ee87cbfea3d5cb00dfc786014996ed14c2cc30086b996a0e45bac2ce
		expected_manifest=20f9815ab7e3b5942e4cb60c98d265d168276ae0a321f26fb53f38092837c786 ;;
	headless-full-ucsi-charging-early-v2:3f4305d7fbbd2c74d15c1011bb8a2e8e24b3a5228f31ed86281917d16cf18f11:headless-full-ucsi-charging-early-v2)
		expected_profile=diagnostic-initramfs-v1
		expected_candidate_sha=0959802879b4bd1c8d6df3690702fa8ff15b55c55968a3a79d1655b2dc483717
		expected_manifest=ed232a25b03bdd08e0d97b2f90a38f27fab8c1b8aae23f6dac57fd495e5ccc43 ;;
	headless-full-ucsi-charging-early-v3:3f4305d7fbbd2c74d15c1011bb8a2e8e24b3a5228f31ed86281917d16cf18f11:headless-full-ucsi-charging-early-v3)
		expected_profile=diagnostic-initramfs-v1
		expected_candidate_sha=8bb76aea6f654c0492f1208befd52d95accd5a30ef749989a399ebb6b4f443a0
		expected_manifest=11051f42876caaa1b4129a7abba352b7d23e1494c7799ba2df20d0177df238fd ;;
	headless-power-usb-observer-v1:3f4305d7fbbd2c74d15c1011bb8a2e8e24b3a5228f31ed86281917d16cf18f11:headless-power-usb-observer-v1)
		expected_profile=network-root-v1
		expected_candidate_sha=b95def86bdae25781b04e2e4d2d534440374f73cfa6080e5949de18961eb2a0f
		expected_manifest=c8e367e3a90966511d22759fe2e650e39a339ea2df554c4a1b9dc6c5409149dd ;;
	*) fail 'unsupported offline candidate identity tuple' ;;
esac
if [[ $deployment_build == 1 ]]; then
	[[ $internal_implementation_sealed == 1 &&
		-n $internal_repository &&
		-n $internal_checkpoint_repository &&
		$internal_repository_commit =~ ^[0-9a-f]{40}$ ]] ||
		fail 'credentialed build requires a sealed implementation snapshot'
	case $internal_checkpoint_repository in
	/*) ;;
	*) fail 'checkpoint repository root is not absolute' ;;
	esac
	[[ -d $internal_checkpoint_repository &&
		! -L $internal_checkpoint_repository &&
		$(realpath -e -- "$internal_checkpoint_repository") == "$internal_checkpoint_repository" ]] ||
		fail 'checkpoint repository root metadata is unsafe'
	checkpoint_repository=$internal_checkpoint_repository
	[[ $(git -C "$repo" rev-parse HEAD) == "$internal_repository_commit" &&
		-z $(git -C "$repo" status --porcelain --untracked-files=all) ]] ||
		fail 'reviewed checkpoint worktree identity changed'
	case $repo in
	"$checkpoint_repository"/build/.rog5-reviewed-checkpoint-*) ;;
	*) fail 'reviewed checkpoint worktree location is unsafe' ;;
	esac
	snapshot_active=1
	[[ ${ALLOW_RECOVERY_DEPLOYMENT_BUILD:-} == 1 ]] ||
		fail 'set ALLOW_RECOVERY_DEPLOYMENT_BUILD=1 for one signed recovery build'
	[[ ${ALLOW_PHONE_CREDENTIAL_USE:-} == 1 ]] ||
		fail 'set ALLOW_PHONE_CREDENTIAL_USE=1 before using the signing key'
	case "$candidate:$expected_target" in
		headless-ssh-network-root-v3:headless-ssh-network-root | \
		headless-core-network-root-v2:headless-core-network-root | \
		headless-netroot-early-diag-v2:headless-netroot-early-diag-v2) ;;
		*) fail 'credentialed build is limited to one fixed deployment candidate' ;;
	esac
	[[ -n $deployment_candidate_record && -n $deployment_private_key ]] ||
		fail 'deployment candidate record and signing key are required'
else
	[[ -z $deployment_candidate_record && -z $deployment_private_key ]] ||
		fail 'offline build rejects deployment credential inputs'
	tracked_candidate=$repo/configs/recovery-candidates/$candidate.json
fi

cleanup_secret() {
	if [[ -n $secret_root && -d $secret_root && $secret_root != / ]]; then
		chmod -R u+rwX -- "$secret_root" 2>/dev/null || true
		rm -rf -- "$secret_root"
	fi
}

cleanup_snapshot() {
	local snapshot_path
	[[ $snapshot_active == 1 ]] || return 0
	snapshot_path=$repo
	case $snapshot_path in
	"$checkpoint_repository"/build/.rog5-reviewed-checkpoint-*) ;;
	*) return 1 ;;
	esac
	if ! /usr/bin/git -C "$checkpoint_repository" worktree remove --force \
		"$snapshot_path" >/dev/null 2>&1; then
		chmod -R u+rwX -- "$snapshot_path" 2>/dev/null || true
		rm -rf -- "$snapshot_path"
		/usr/bin/git -C "$checkpoint_repository" worktree prune \
			>/dev/null 2>&1 || true
	fi
	[[ ! -e $snapshot_path && ! -L $snapshot_path ]] || return 1
	snapshot_active=0
}

cleanup() {
	cleanup_secret
	cleanup_snapshot || true
}
trap cleanup EXIT HUP INT TERM

for command in chmod cmp cut env find git grep id mkdir mktemp mv openssl \
	python3 realpath rm sed sha256sum stat tail; do
	command -v "$command" >/dev/null ||
		fail "missing corrected-candidate command: $command"
done
if [[ $deployment_build == 0 ]]; then
	[[ -f $tracked_candidate && ! -L $tracked_candidate ]] ||
		fail 'offline candidate record identity changed'
	observed_candidate_sha=$(
		sha256sum "$tracked_candidate" | cut -d ' ' -f 1
	)
	[[ $observed_candidate_sha == "$expected_candidate_sha" ]] ||
		fail 'offline candidate record identity changed'
fi

requested_output_root=$(realpath -m "$requested_output_root")
case $requested_output_root in
	"$checkpoint_repository"/build/*) ;;
	*) fail 'output root must be below the ignored repository build directory' ;;
esac
git -C "$checkpoint_repository" check-ignore -q "$requested_output_root" ||
	fail 'output root is not ignored by Git'
if [[ $deployment_build == 1 ]]; then
	[[ ! -e $requested_output_root && ! -L $requested_output_root ]] ||
		fail 'credentialed output root must not already exist'
	output_root=$repo/build/deployment-output
	git -C "$repo" check-ignore -q "$output_root" ||
		fail 'checkpoint output root is not ignored by Git'
else
	output_root=$requested_output_root
	[[ ! -d $output_root ||
		-z $(find "$output_root" -mindepth 1 -maxdepth 1 -print -quit) ]] ||
		fail 'refusing nonempty corrected-candidate output root'
fi

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
	/usr/bin/env -i \
		PATH=/usr/bin:/bin \
		LC_ALL=C \
		/usr/bin/python3 -I -S "$deployment_input_stager" \
		--repository "$checkpoint_repository" \
		--expected-repository-commit "$internal_repository_commit" \
		--signing-key "$deployment_private_key" \
		--candidate-record "$deployment_candidate_record" \
		--candidate-id "$candidate" \
		--staged-key "$private_key" \
		--staged-candidate "$candidate_record" \
		--raw-public-key "$public_key" \
		>"$secret_root/deployment-input-admission.txt"
	grep -Fxq \
		'format=rog5-recovery-deployment-signing-inputs-v2' \
		"$secret_root/deployment-input-admission.txt" ||
		fail 'deployment signing-input admission did not pass'
	grep -Fxq "candidate=$candidate" \
		"$secret_root/deployment-input-admission.txt" ||
		fail 'deployment signing-input candidate did not match the build'
	grep -Fxq 'authority=none' \
		"$secret_root/deployment-input-admission.txt" ||
		fail 'deployment signing-input admission returned authority'
	grep -Fxq "repository_commit=$internal_repository_commit" \
		"$secret_root/deployment-input-admission.txt" ||
		fail 'deployment signing-input checkpoint did not match the launcher'
	candidate_record_sha256=$(
		sed -n 's/^candidate_record_sha256=//p' \
			"$secret_root/deployment-input-admission.txt"
	)
	[[ $candidate_record_sha256 =~ ^[0-9a-f]{64}$ &&
		$candidate_record_sha256 == \
		"$(sha256sum "$candidate_record" | cut -d ' ' -f 1)" ]] ||
		fail 'staged deployment candidate identity changed'
	unset ROG5_DEPLOYMENT_SIGNING_KEY \
		ROG5_DEPLOYMENT_CANDIDATE_RECORD \
		ROG5_DEPLOYMENT_BUILD \
		ALLOW_PHONE_CREDENTIAL_USE \
		ALLOW_RECOVERY_DEPLOYMENT_BUILD \
		ALLOW_HEADLESS_SSH_DEPLOYMENT_BUILD
	deployment_private_key=
	deployment_candidate_record=
	if env | grep -Eq \
		'^(ROG5_DEPLOYMENT_(SIGNING_KEY|CANDIDATE_RECORD|BUILD)|ALLOW_PHONE_CREDENTIAL_USE|ALLOW_(RECOVERY|HEADLESS_SSH)_DEPLOYMENT_BUILD)='; then
		fail 'deployment credential path or authorization leaked after staging'
	fi
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

if [[ $deployment_input_preflight == 1 ]]; then
	private_key_path=$private_key
	checkpoint_path=$repo
	cleanup
	secret_root=
	[[ ! -e $private_key_path ]] ||
		fail 'private signing-key snapshot survived input preflight'
	[[ ! -e $checkpoint_path && ! -L $checkpoint_path ]] ||
		fail 'reviewed checkpoint worktree survived input preflight'
	echo 'PASS guarded deployment signing inputs staged, validated, scrubbed from the child environment, and destroyed without signing'
	exit 0
fi

command -v podman >/dev/null ||
	fail 'missing corrected-candidate command: podman'

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
bundle_id_a=$(sed -n 's/^bundle=//p' "$output_root/candidate-a.txt")
bundle_id_b=$(sed -n 's/^bundle=//p' "$output_root/candidate-b.txt")
[[ $manifest_a =~ ^[0-9a-f]{64}$ && $manifest_a == "$manifest_b" ]] ||
	fail 'twin corrected candidate manifests differ'
[[ $deployment_build == 1 && $candidate != headless-netroot-early-diag-v2 ||
	$manifest_a == "$expected_manifest" ]] ||
	fail 'offline candidate manifest identity changed'
[[ $trust_a =~ ^[0-9a-f]{64}$ && $trust_a == "$trust_b" &&
	$trust_a == "$(sha256sum "$public_key" | cut -d ' ' -f 1)" ]] ||
	fail 'corrected candidate trust-root identity differs'
[[ $bundle_id_a =~ ^[a-z0-9][a-z0-9._-]{0,63}$ &&
	$bundle_id_a == "$bundle_id_b" ]] ||
	fail 'twin corrected candidate bundle identities differ'

bundle_path_a=$bundle_a/$bundle_id_a
bundle_path_b=$bundle_b/$bundle_id_b
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
		--trust-key "$public_key" "$bundle_id_a" "$manifest_a"
)
plan_b=$(
	"$host_verifier" --bundle-root "$bundle_b" \
		--trust-key "$public_key" "$bundle_id_b" "$manifest_b"
)
[[ $plan_a == "$plan_b" ]] ||
	fail 'native verifier produced different twin execution plans'
grep -Fxq "bundle=$bundle_id_a" <<<"$plan_a"
grep -Fxq "manifest_sha256=$manifest_a" <<<"$plan_a"
grep -Fxq "profile=$expected_profile" <<<"$plan_a"
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
cleanup_secret
secret_root=
[[ ! -e $private_key_path ]] ||
	fail 'private signing-key snapshot survived candidate build'
if [[ $deployment_build == 1 ]]; then
	internal_output_root=$output_root
	mv --no-clobber -T -- "$internal_output_root" "$requested_output_root"
	[[ ! -e $internal_output_root && -d $requested_output_root ]] ||
		fail 'credentialed output publication refused an occupied destination'
	output_root=$requested_output_root
	cleanup_snapshot || fail 'reviewed checkpoint worktree cleanup failed'
fi

printf 'candidate=%s\nbundle=%s\nmanifest_sha256=%s\ntrust_key_sha256=%s\n' \
	"$candidate" "$bundle_id_a" "$manifest_a" "$trust_a"
echo 'authority=none'
if [[ $deployment_build == 1 ]]; then
	echo 'PASS twin credential-bound deployment candidate, signed bundle, recovery wrapper, and hardware-free gate; source key verified and private snapshot destroyed'
else
	echo 'PASS twin corrected-DTB candidate, signed bundle, recovery wrapper, and hardware-free gate; disposable private key destroyed'
fi
