#!/usr/bin/env bash
set -euo pipefail

fail() {
	echo "FAIL $*" >&2
	exit 1
}

repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
builder=$repo/scripts/host/build-headless-core-candidate-offline.sh
base_builder=$repo/scripts/host/build-corrected-headless-candidate-offline.sh
candidate=$repo/configs/recovery-candidates/headless-core-network-root-v2.json
package=$repo/configs/network-roots/headless-core-network-root-v2.package

for path in "$builder" "$base_builder"; do
	[[ -f $path && ! -L $path && -x $path ]] ||
		fail "missing executable headless-core candidate input: ${path#"$repo"/}"
	bash -n "$path"
done
for path in "$candidate" "$package"; do
	[[ -f $path && ! -L $path ]] ||
		fail "missing headless-core candidate contract: ${path#"$repo"/}"
done

for token in \
	headless-core-network-root-v2 \
	57216474b4c8979161d964cef2ff3fe5d61500af3cef34598ee06e03e91f967d \
	headless-core-network-root \
	build-corrected-headless-candidate-offline.sh; do
	grep -Fq "$token" "$builder" ||
		fail "headless-core candidate builder omits contract token: $token"
done
for token in \
	'"status": "offline"' \
	'"authority": "none"' \
	'"profile": "network-root-v1"' \
	'"target_id": "headless-core-network-root"' \
	'"root_tree_entries": "37675"'; do
	grep -Fq "$token" "$candidate" ||
		fail "headless-core candidate omits contract token: $token"
done
grep -Fxq 'format=rog5-headless-network-root-package-v2' "$package"
grep -Fxq 'build_profile=headless-core-v2' "$package"

if grep -Eq \
	'\b(fastboot|adb|scp|systemctl|pkexec|sudo)\b|(^|[[:space:]"'\''])ssh([[:space:]"'\'']|$)|/dev/(sd|nvme|ufs)' \
	"$builder" "$base_builder"; then
	fail 'headless-core candidate builder contains live or storage transport'
fi
grep -Fq 'unsupported offline candidate identity tuple' "$base_builder" ||
	fail 'shared candidate builder does not allowlist exact identity tuples'

if refusal=$(
	ROG5_OFFLINE_CANDIDATE=headless-core-network-root-v2 \
	ROG5_OFFLINE_EXPECTED_DTB=bad \
	ROG5_OFFLINE_EXPECTED_TARGET=headless-core-network-root \
		"$base_builder" "$repo/build/invalid-offline-candidate" 2>&1
); then
	fail 'shared candidate builder accepted a malformed DTB identity'
fi
grep -Fq 'offline candidate DTB identity is malformed' <<<"$refusal" ||
	fail 'shared candidate builder did not fail at the DTB identity boundary'

if refusal=$(
	ROG5_OFFLINE_CANDIDATE=headless-core-network-root-v2 \
	ROG5_OFFLINE_EXPECTED_DTB=86e5cb81191e3de39c9527b838fa03d78744cd9b0d862336f0c1f36a9f534f46 \
	ROG5_OFFLINE_EXPECTED_TARGET=headless-core-network-root \
		"$base_builder" "$repo/build/invalid-offline-candidate" 2>&1
); then
	fail 'shared candidate builder accepted a co-varied identity tuple'
fi
grep -Fq 'unsupported offline candidate identity tuple' <<<"$refusal" ||
	fail 'shared candidate builder did not fail at the tuple allowlist'

echo 'PASS headless-core successor candidate is package-bound, offline-only, and transport-free'
