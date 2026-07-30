#!/usr/bin/env bash
set -euo pipefail

fail() {
	echo "FAIL $*" >&2
	exit 1
}

repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
baseline=${1:?usage: generate-stable-wrapper-slim-config.sh BASELINE_CONFIG OUTPUT_ROOT}
output_root=${2:?missing ignored output root}
profile=$repo/configs/kernel/rog5-stable-wrapper-slim-v1.json
fragment=$repo/configs/kernel/rog5-stable-wrapper-slim-v1.fragment
auditor=$repo/scripts/host/verify-stable-wrapper-slim-config.py
seal_tool=$repo/scripts/host/kernel-source-seal.py
source_volume=rog5-asus-v12a-source
builder_image=localhost/rog5-kernel-builder:ubuntu-24.04
expected_baseline=df28224e6e8d2dfc825ac49dc9f6bdeb12bbcdae2dff92cbbf14a8a94177578f
expected_fragment=a302ef08910b24a638da63230e6496f3c93a2828baa3ed6e51d7cbc393916231
expected_profile=3fb9eaf91f32cf01c09cc8653feb4a52c421f4a95bdd8e022576211ad7cff9f0
expected_auditor=6d988b18c3ae70f5bd91be8e6051119911886be0b4eaeb3759eddf3f5a8ac744
expected_seal_tool=b5ed3261a858680b05a3a7247e2d7948e722f71be812fcdc66972594d22c097a
expected_source_tree=592aefb37589f9f9483b43677e29702ed927fc56a251616e33e81f2645e9c35a
expected_builder_id=c5b80647ddd7fb29464b4735abbe27012ee4dc89be559b44b25c9b1ff59c9cec
expected_builder_digest=sha256:8513960144bb1ca77878a1364c03fb100c8b87fffb8440fd37a6cc4fc0043b41

for command in cut git grep mkdir podman python3 realpath sha256sum; do
	command -v "$command" >/dev/null ||
		fail "missing slim-config command: $command"
done
for input in "$baseline" "$profile" "$fragment" "$auditor" "$seal_tool"; do
	[[ -f $input && ! -L $input ]] ||
		fail "missing regular nonsymlink slim-config input: $input"
done
[[ $(sha256sum "$baseline" | cut -d ' ' -f 1) == "$expected_baseline" ]] ||
	fail 'accepted wrapper baseline identity changed'
[[ $(sha256sum "$fragment" | cut -d ' ' -f 1) == "$expected_fragment" ]] ||
	fail 'stable-wrapper slimming fragment identity changed'
[[ $(sha256sum "$profile" | cut -d ' ' -f 1) == "$expected_profile" ]] ||
	fail 'stable-wrapper slimming profile identity changed'
[[ $(sha256sum "$auditor" | cut -d ' ' -f 1) == "$expected_auditor" ]] ||
	fail 'stable-wrapper slimming auditor identity changed'
[[ $(sha256sum "$seal_tool" | cut -d ' ' -f 1) == "$expected_seal_tool" ]] ||
	fail 'kernel source-seal tool identity changed'
grep -Fqx \
	"  \"fragment_sha256\": \"$expected_fragment\"," "$profile" ||
	fail 'profile and fragment identities disagree'
grep -Fqx \
	"  \"builder_id\": \"$expected_builder_id\"," "$profile" ||
	fail 'profile and generator builder IDs disagree'
grep -Fqx \
	"  \"builder_digest\": \"$expected_builder_digest\"," "$profile" ||
	fail 'profile and generator builder digests disagree'
python3 "$auditor" --profile "$profile" --baseline "$baseline" >/dev/null

baseline=$(realpath -e "$baseline")
output_root=$(realpath -m "$output_root")
case $output_root in
	"$repo"/build/*) ;;
	*) fail 'slim-config output must be below the ignored build directory' ;;
esac
git -C "$repo" check-ignore -q "$output_root" ||
	fail 'slim-config output is not ignored by Git'
[[ ! -e $output_root && ! -L $output_root ]] ||
	fail 'refusing existing slim-config output'

podman image exists "$builder_image" ||
	fail "missing pinned kernel builder: $builder_image"
[[ $(podman image inspect "$builder_image" --format '{{.Id}}') == \
	"$expected_builder_id" ]] ||
	fail 'unexpected kernel-builder image ID'
[[ $(podman image inspect "$builder_image" --format '{{.Digest}}') == \
	"$expected_builder_digest" ]] ||
	fail 'unexpected kernel-builder image digest'
podman volume exists "$source_volume" ||
	fail "missing ASUS source volume: $source_volume"

mkdir "$output_root"
source_seal=$output_root/source-seal.txt
podman run --rm --network=none --security-opt label=disable \
	-v "$source_volume:/root/src:ro" \
	-v "$repo:/workspace:ro" \
	"$builder_image" \
	python3 /workspace/scripts/host/kernel-source-seal.py \
	/root/src/msm-5.4 >"$source_seal"
[[ $(grep -E '^tree_sha256=[0-9a-f]{64}$' "$source_seal" | cut -d= -f2) == \
	"$expected_source_tree" ]] ||
	fail 'ASUS source tree identity changed'

podman run --rm --network=none --security-opt label=disable \
	-v "$source_volume:/root/src:ro" \
	-v "$baseline:/inputs/accepted.config:ro" \
	-v "$fragment:/inputs/slim.fragment:ro" \
	-v "$output_root:/root/build" \
	"$builder_image" \
	/bin/sh -eu -c '
		mkdir /root/build/merge
		cd /root/build/merge
		export ARCH=arm64
		export CROSS_COMPILE=aarch64-linux-gnu-
		export LLVM=1
		export LLVM_IAS=1
		export DISABLE_WRAPPER=1
		export ASUS_BUILD_PROJECT=ZS673KS
		/root/src/msm-5.4/scripts/kconfig/merge_config.sh \
			-m -r -O /root/build \
			/inputs/accepted.config /inputs/slim.fragment \
			>/root/build/merge-config.log
		make -C /root/src/msm-5.4 O=/root/build olddefconfig \
			>/root/build/olddefconfig.log
		rmdir /root/build/merge
	'

python3 "$auditor" \
	--profile "$profile" \
	--baseline "$baseline" \
	--candidate "$output_root/.config" |
	tee "$output_root/audit.txt"
{
	printf 'format=rog5-stable-wrapper-slim-generation-v1\n'
	printf 'status=experiment\n'
	printf 'authority=none\n'
	printf 'baseline_config_sha256=%s\n' "$expected_baseline"
	printf 'fragment_sha256=%s\n' "$expected_fragment"
	printf 'source_tree_sha256=%s\n' "$expected_source_tree"
	printf 'builder_id=%s\n' "$expected_builder_id"
	printf 'builder_digest=%s\n' "$expected_builder_digest"
	printf 'candidate_config_sha256=%s\n' \
		"$(sha256sum "$output_root/.config" | cut -d ' ' -f 1)"
} >"$output_root/generation-meta.txt"
echo "candidate_config=$output_root/.config"
echo 'status=experiment'
echo 'authority=none'
echo 'PASS generated hardware-free stable-wrapper slim config; not boot-authorized'
