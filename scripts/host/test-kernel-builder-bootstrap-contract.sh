#!/usr/bin/env bash
set -euo pipefail

fail() {
	echo "FAIL $*" >&2
	exit 1
}

repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
dockerfile=$repo/containers/kernel-builder/Dockerfile
bootstrap=$repo/scripts/host/bootstrap-kernel-builder.sh
prepare=$repo/scripts/device/prepare-mainline.sh
package_lock=$repo/manifests/kernel-builder-packages.tsv

for path in "$dockerfile" "$bootstrap" "$prepare" "$package_lock"; do
	[[ -f $path && ! -L $path ]] ||
		fail "missing regular bootstrap input: ${path#"$repo"/}"
done
[[ -x $bootstrap ]] ||
	fail 'Linux kernel builder bootstrap is not executable'

grep -Fq \
	'fedora:44@sha256:89f61a124414261868224666aa7fb8df1b78397a53623774bdfb105d1612b48b' \
	"$dockerfile" ||
	fail 'kernel builder does not pin the amd64 CA bootstrap image'
grep -Fq \
	'ubuntu:24.04@sha256:4fbb8e6a8395de5a7550b33509421a2bafbc0aab6c06ba2cef9ebffbc7092d90' \
	"$dockerfile" ||
	fail 'kernel builder does not pin the amd64 Ubuntu base image'
grep -Fq '20260728T000000Z' "$dockerfile" ||
	fail 'kernel builder does not pin the Ubuntu snapshot'
grep -Fq 'Check-Valid-Until: no' "$dockerfile" ||
	fail 'historical Ubuntu snapshot will expire at its original Valid-Until'
if grep -Eq '^ARG (UBUNTU_SNAPSHOT|PACKAGE_LOCK_SHA256)=' "$dockerfile"; then
	fail 'accepted kernel builder identities remain caller-overridable'
fi
grep -Fq 'kernel-builder-packages.tsv' "$dockerfile" ||
	fail 'kernel builder does not consume the complete package lock'
grep -Fq 'sha256sum -c' "$dockerfile" ||
	fail 'kernel builder does not verify its bootstrap inputs'
grep -Fq 'cmp ' "$dockerfile" ||
	fail 'kernel builder does not compare the installed package closure'
grep -Fq 'type=cache' "$dockerfile" ||
	fail 'kernel builder does not reuse verified snapshot downloads'
grep -Fq 'find /var/log -type f -delete' "$dockerfile" ||
	fail 'kernel builder does not remove volatile package logs'
grep -Fq '/var/cache/apt/*.bin' "$dockerfile" ||
	fail 'kernel builder does not remove generated APT binary caches'
grep -Fq "\${db:Status-Abbrev}" "$dockerfile" ||
	fail 'kernel builder package closure includes non-installed dpkg states'

[[ $(head -n 1 "$package_lock") == $'package\tversion' ]] ||
	fail 'kernel builder package lock has no canonical header'
sorted_lock=$(tail -n +2 "$package_lock" | LC_ALL=C sort)
current_lock=$(tail -n +2 "$package_lock")
[[ $sorted_lock == "$current_lock" ]] ||
	fail 'kernel builder package lock is not sorted'
[[ -z $(cut -f1 "$package_lock" | LC_ALL=C sort | uniq -d) ]] ||
	fail 'kernel builder package lock contains duplicate package names'
[[ $(wc -l <"$package_lock") -gt 150 ]] ||
	fail 'kernel builder package lock is implausibly short'

grep -Fq 'podman info' "$bootstrap" ||
	fail 'Linux bootstrap does not verify Podman'
grep -Fq 'rootless' "$bootstrap" ||
	fail 'Linux bootstrap does not require rootless Podman'
grep -Fq -- '--no-cache' "$bootstrap" ||
	fail 'Linux bootstrap does not support an independent image build'
grep -Fq -- '--timestamp' "$bootstrap" ||
	fail 'Linux bootstrap does not normalize the image timestamp'
grep -Fq -- '--network none' "$bootstrap" ||
	fail 'Linux bootstrap does not verify the finished image offline'
grep -Fq 'rootfs_identity' "$bootstrap" ||
	fail 'Linux bootstrap does not compare normalized root filesystems'
grep -Fq 'APT_CACHE_NAMESPACE' "$bootstrap" ||
	fail 'reproduction builds do not isolate their APT download caches'
grep -Fq 'distinct cache namespaces are recorded in image history' "$bootstrap" ||
	fail 'reproduction does not explain its expected OCI metadata difference'
if grep -Fq "first_id == \"\$second_id\"" "$bootstrap"; then
	fail 'reproduction incorrectly equates cache-history metadata with rootfs identity'
fi
if grep -Eq '\bsudo\b|fastboot|adb|/dev/(sd|nvme|ufs)' "$bootstrap"; then
	fail 'kernel builder bootstrap contains privilege or phone/storage actions'
fi
if "$bootstrap" verify localhost/untagged >/dev/null 2>&1; then
	fail 'kernel builder accepted an image reference without an explicit tag'
fi

for identity in \
	114456a9c542d933387517bb22561668c25a5b59 \
	7a5cef0db4795d9d453a12e0f61b5b7634fc4d40 \
	2ea2be38c5e4dc9aafffbbc0db5aae0f6513a1d9; do
	grep -Fq "$identity" "$prepare" ||
		fail "source bootstrap does not pin $identity"
done

test_root=$(mktemp -d)
trap 'rm -rf -- "$test_root"' EXIT HUP INT TERM
upstream=$test_root/upstream
source_root=$test_root/source
git init -q "$upstream"
git -C "$upstream" -c user.name=Test -c user.email=test@example.invalid \
	commit --allow-empty -m baseline >/dev/null
git -C "$upstream" -c user.name=Test -c user.email=test@example.invalid \
	tag -a v-test -m v-test
tag_object=$(git -C "$upstream" rev-parse refs/tags/v-test)
commit=$(git -C "$upstream" rev-parse 'refs/tags/v-test^{}')
tree=$(git -C "$upstream" rev-parse 'refs/tags/v-test^{tree}')

LINUX_REPOSITORY=$upstream \
	LINUX_TAG=v-test \
	LINUX_TAG_OBJECT=$tag_object \
	LINUX_COMMIT=$commit \
	LINUX_TREE=$tree \
	sh "$prepare" "$source_root" >/dev/null
[[ $(git -C "$source_root" rev-parse HEAD) == "$commit" ]] ||
	fail 'source bootstrap did not check out the verified commit'

wrong_tag=0000000000000000000000000000000000000000
rejected=$test_root/wrong-tag
if LINUX_REPOSITORY=$upstream \
	LINUX_TAG=v-test \
	LINUX_TAG_OBJECT=$wrong_tag \
	LINUX_COMMIT=$commit \
	LINUX_TREE=$tree \
	sh "$prepare" "$rejected" >/dev/null 2>&1; then
	fail 'source bootstrap accepted a changed tag object'
fi
if git -C "$rejected" rev-parse --verify HEAD >/dev/null 2>&1; then
	fail 'source bootstrap checked out an unverified tag'
fi

rejected=$test_root/wrong-commit
if LINUX_REPOSITORY=$upstream \
	LINUX_TAG=v-test \
	LINUX_TAG_OBJECT=$tag_object \
	LINUX_COMMIT=$wrong_tag \
	LINUX_TREE=$tree \
	sh "$prepare" "$rejected" >/dev/null 2>&1; then
	fail 'source bootstrap accepted a changed commit'
fi

rejected=$test_root/wrong-tree
if LINUX_REPOSITORY=$upstream \
	LINUX_TAG=v-test \
	LINUX_TAG_OBJECT=$tag_object \
	LINUX_COMMIT=$commit \
	LINUX_TREE=$wrong_tag \
	sh "$prepare" "$rejected" >/dev/null 2>&1; then
	fail 'source bootstrap accepted a changed source tree'
fi

git -C "$upstream" tag lightweight "$commit"
rejected=$test_root/lightweight
if LINUX_REPOSITORY=$upstream \
	LINUX_TAG=lightweight \
	LINUX_TAG_OBJECT=$commit \
	LINUX_COMMIT=$commit \
	LINUX_TREE=$tree \
	sh "$prepare" "$rejected" >/dev/null 2>&1; then
	fail 'source bootstrap accepted a lightweight tag'
fi

rejected=$test_root/wrong-remote
git init -q "$rejected"
git -C "$rejected" remote add origin "$test_root/not-upstream"
if LINUX_REPOSITORY=$upstream \
	LINUX_TAG=v-test \
	LINUX_TAG_OBJECT=$tag_object \
	LINUX_COMMIT=$commit \
	LINUX_TREE=$tree \
	sh "$prepare" "$rejected" >/dev/null 2>&1; then
	fail 'source bootstrap accepted an unexpected existing remote'
fi

touch "$source_root/untracked"
if LINUX_REPOSITORY=$upstream \
	LINUX_TAG=v-test \
	LINUX_TAG_OBJECT=$tag_object \
	LINUX_COMMIT=$commit \
	LINUX_TREE=$tree \
	sh "$prepare" "$source_root" >/dev/null 2>&1; then
	fail 'source bootstrap replaced a dirty source tree'
fi

echo 'PASS pinned rootless kernel builder and source bootstrap contract'
