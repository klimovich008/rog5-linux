#!/usr/bin/env bash
set -euo pipefail

fail() {
	echo "FAIL $*" >&2
	exit 1
}

repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
builder=$repo/scripts/host/build-headless-ssh-v2-candidate-offline.sh
base_builder=$repo/scripts/host/build-corrected-headless-candidate-offline.sh
candidate=$repo/configs/recovery-candidates/headless-ssh-network-root-v3.json
package=$repo/configs/network-roots/headless-ssh-network-root-v3.package

for path in "$builder" "$base_builder"; do
	[[ -f $path && ! -L $path && -x $path ]] ||
		fail "missing executable headless-ssh candidate input: ${path#"$repo"/}"
	bash -n "$path"
done
for path in "$candidate" "$package"; do
	[[ -f $path && ! -L $path ]] ||
		fail "missing headless-ssh candidate contract: ${path#"$repo"/}"
done

for token in \
	headless-ssh-network-root-v3 \
	86e5cb81191e3de39c9527b838fa03d78744cd9b0d862336f0c1f36a9f534f46 \
	headless-ssh-network-root \
	build-corrected-headless-candidate-offline.sh; do
	grep -Fq "$token" "$builder" ||
		fail "headless-ssh candidate builder omits contract token: $token"
done
for token in \
	'"status": "offline"' \
	'"authority": "none"' \
	'"profile": "network-root-v1"' \
	'"target_id": "headless-ssh-network-root"' \
	'"root_tree_entries": "37735"'; do
	grep -Fq "$token" "$candidate" ||
		fail "headless-ssh candidate omits contract token: $token"
done
for token in \
	'format=rog5-headless-network-root-package-v3' \
	'build_profile=headless-ssh-v2' \
	'authorized_key_fingerprint=SHA256:ylv66wbMSxVEAMiOFvMQOztcvtSB5wSbVe9FXePMLN0'; do
	grep -Fxq "$token" "$package" ||
		fail "headless-ssh package omits identity token: $token"
done

for name in \
	a660_command_manifest_sha256 \
	root_generation \
	root_tree_sha256 \
	root_seal_sha256 \
	root_tree_entries \
	root_subtree; do
	package_value=$(sed -n "s/^$name=//p" "$package")
	[[ -n $package_value ]] ||
		fail "headless-ssh package omits candidate field: $name"
	grep -Fq "\"$name\": \"$package_value\"" "$candidate" ||
		fail "headless-ssh candidate differs from package: $name"
done

if grep -Eq \
	'\b(fastboot|adb|scp|systemctl|pkexec|sudo)\b|(^|[[:space:]"'\''])ssh([[:space:]"'\'']|$)|/dev/(sd|nvme|ufs)' \
	"$builder" "$base_builder"; then
	fail 'headless-ssh candidate builder contains live or storage transport'
fi
grep -Fq 'unsupported offline candidate identity tuple' "$base_builder" ||
	fail 'shared candidate builder does not allowlist exact identity tuples'

if refusal=$(
	ROG5_OFFLINE_CANDIDATE=headless-ssh-network-root-v3 \
	ROG5_OFFLINE_EXPECTED_DTB=bad \
	ROG5_OFFLINE_EXPECTED_TARGET=headless-ssh-network-root \
		"$base_builder" "$repo/build/invalid-headless-ssh-candidate" 2>&1
); then
	fail 'shared candidate builder accepted a malformed DTB identity'
fi
grep -Fq 'offline candidate DTB identity is malformed' <<<"$refusal" ||
	fail 'shared candidate builder did not fail at the DTB identity boundary'

if refusal=$(
	ROG5_OFFLINE_CANDIDATE=headless-ssh-network-root-v3 \
	ROG5_OFFLINE_EXPECTED_DTB=57216474b4c8979161d964cef2ff3fe5d61500af3cef34598ee06e03e91f967d \
	ROG5_OFFLINE_EXPECTED_TARGET=headless-ssh-network-root \
		"$base_builder" "$repo/build/invalid-headless-ssh-candidate" 2>&1
); then
	fail 'shared candidate builder accepted a co-varied identity tuple'
fi
grep -Fq 'unsupported offline candidate identity tuple' <<<"$refusal" ||
	fail 'shared candidate builder did not fail at the tuple allowlist'

if refusal=$(
	ROG5_OFFLINE_CANDIDATE=headless-ssh-network-root-v3 \
	ROG5_OFFLINE_EXPECTED_DTB=86e5cb81191e3de39c9527b838fa03d78744cd9b0d862336f0c1f36a9f534f46 \
	ROG5_OFFLINE_EXPECTED_TARGET=headless-network-root \
		"$base_builder" "$repo/build/invalid-headless-ssh-candidate" 2>&1
); then
	fail 'shared candidate builder accepted a wrong target with the shared DTB'
fi
grep -Fq 'unsupported offline candidate identity tuple' <<<"$refusal" ||
	fail 'shared candidate builder did not bind the target within its tuple'

echo 'PASS headless-ssh candidate is key/package-bound, offline-only, and transport-free'
