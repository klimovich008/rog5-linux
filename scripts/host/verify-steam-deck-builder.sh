#!/usr/bin/env bash
set -euo pipefail

fail() {
	echo "FAIL $*" >&2
	exit 1
}

repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
profile=$repo/configs/kernel-builder/steam-deck-asus-5.4-v1.json
bootstrap=$repo/scripts/host/bootstrap-kernel-builder.sh
manifest_script=$repo/scripts/host/kernel-builder-rootfs-manifest.sh
manifest_artifact=$repo/artifacts/kernel-builder-steamdeck-v1/rootfs-manifest.tsv.gz
image=${1:-localhost/rog5-kernel-builder:ubuntu-24.04}
expected_profile=1bc7ee578bb59ce53c92ccf8e666b84ba2560c573d1f9392061b88831deb904b
expected_bootstrap=6b6aed304febe0c595bfe379d7a48e0f1216d58dd858cd785e931a708fc136d2
expected_recipe=28dca69fd5c7f0fb1cf3418fd5a8bc5d2d8d04cdd1cf09919667e32faefb54bd
expected_lock=9dce7979f2b55e0f56c6dd803986d127107e5a7ead15cd69e780aebaccacc101
expected_manifest_script=3a2644f7a128fac3a3c8bd44d9a58cd00304e3459f2aee81d8930a4659919c84
expected_manifest_archive=7680447aa94ed11de4313347face7b7b2168d73c92b243f733eeb656cf6bd94b
expected_rootfs=a82749a50365d864714594cc40ce27a28af4f132ef0e540946338b4681bf1fda

for command_name in cut grep gzip podman sed sha256sum; do
	command -v "$command_name" >/dev/null ||
		fail "missing Steam Deck builder command: $command_name"
done
for input in \
	"$profile" "$bootstrap" "$manifest_script" "$manifest_artifact"; do
	[[ -f $input && ! -L $input ]] ||
		fail "missing regular Steam Deck builder input: ${input#"$repo"/}"
done
[[ $(sha256sum "$profile" | cut -d ' ' -f 1) == "$expected_profile" ]] ||
	fail 'Steam Deck builder profile changed'
[[ $(sha256sum "$bootstrap" | cut -d ' ' -f 1) == "$expected_bootstrap" ]] ||
	fail 'kernel builder bootstrap changed'
[[ $(sha256sum "$manifest_script" | cut -d ' ' -f 1) == \
	"$expected_manifest_script" ]] ||
	fail 'kernel builder rootfs manifest implementation changed'
[[ $(sha256sum "$manifest_artifact" | cut -d ' ' -f 1) == \
	"$expected_manifest_archive" ]] ||
	fail 'tracked Steam Deck rootfs manifest archive changed'
gzip -t "$manifest_artifact"
[[ $(gzip -dc "$manifest_artifact" | sha256sum | cut -d ' ' -f 1) == \
	"$expected_rootfs" ]] ||
	fail 'tracked Steam Deck rootfs manifest identity changed'

report=$("$bootstrap" verify "$image")
value() {
	local key=$1
	local matches
	matches=$(sed -n "s/^${key}=//p" <<<"$report")
	[[ -n $matches && $matches != *$'\n'* ]] ||
		fail "builder report has missing or duplicate $key"
	printf '%s\n' "$matches"
}
[[ $(value ubuntu_snapshot) == 20260728T000000Z ]] ||
	fail 'Steam Deck builder snapshot changed'
[[ $(value package_lock_sha256) == "$expected_lock" ]] ||
	fail 'Steam Deck builder package closure changed'
[[ $(value builder_recipe_sha256) == "$expected_recipe" ]] ||
	fail 'Steam Deck builder recipe changed'
[[ $(value rootfs_manifest_script_sha256) == "$expected_manifest_script" ]] ||
	fail 'Steam Deck builder rootfs manifest report changed'
[[ $(value rootfs_identity) == "$expected_rootfs" ]] ||
	fail 'Steam Deck builder rootfs identity changed'
for tool in \
	'Ubuntu clang version 18.1.3 (1ubuntu1)' \
	'Ubuntu LLD 18.1.3 (compatible with GNU linkers)' \
	'ccache version 4.9.1' \
	'v1.25'; do
	grep -Fxq -- "$tool" <<<"$report" ||
		fail "Steam Deck builder tool changed: $tool"
done

printf '%s\n' "$report"
echo 'PASS qualified Steam Deck ASUS 5.4 kernel builder'
