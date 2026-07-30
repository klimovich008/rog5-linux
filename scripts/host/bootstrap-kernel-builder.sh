#!/usr/bin/env bash
set -euo pipefail

fail() {
	echo "FAIL $*" >&2
	exit 1
}

repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
dockerfile=$repo/containers/kernel-builder/Dockerfile
package_lock=$repo/manifests/kernel-builder-packages.tsv
rootfs_manifest_script=$repo/scripts/host/kernel-builder-rootfs-manifest.sh
action=${1:-verify}
image=${2:-localhost/rog5-kernel-builder:ubuntu-24.04}
snapshot=20260728T000000Z
image_timestamp=1785196800
expected_lock_sha256=9dce7979f2b55e0f56c6dd803986d127107e5a7ead15cd69e780aebaccacc101
expected_rootfs_manifest_sha256=3a2644f7a128fac3a3c8bd44d9a58cd00304e3459f2aee81d8930a4659919c84

[[ $image =~ ^[a-zA-Z0-9._:/-]+$ && $image != -* ]] ||
	fail 'invalid local image reference'
image_name=${image##*/}
[[ $image_name =~ ^[a-zA-Z0-9._-]+:[a-zA-Z0-9_][a-zA-Z0-9._-]*$ ]] ||
	fail 'local image reference requires an explicit tag'
image_repository=${image%:*}
for command in podman sha256sum uname; do
	command -v "$command" >/dev/null ||
		fail "missing host command: $command"
done
[[ $(uname -m) == x86_64 ]] ||
	fail 'kernel builder currently requires an x86_64 Linux host'
[[ $(podman info --format '{{.Host.Security.Rootless}}') == true ]] ||
	fail 'kernel builder requires rootless Podman'
actual_lock_sha256=$(sha256sum "$package_lock" | cut -d ' ' -f 1)
[[ $actual_lock_sha256 == "$expected_lock_sha256" ]] ||
	fail 'tracked kernel builder package lock changed'
[[ -f $rootfs_manifest_script && ! -L $rootfs_manifest_script ]] ||
	fail 'missing regular kernel builder rootfs manifest implementation'
[[ $(sha256sum "$rootfs_manifest_script" | cut -d ' ' -f 1) == \
	"$expected_rootfs_manifest_sha256" ]] ||
	fail 'kernel builder rootfs manifest implementation changed'

build_image() {
	local target=$1
	local cache_namespace=${2:-default}
	podman build \
		--build-arg "APT_CACHE_NAMESPACE=$cache_namespace" \
		--file "$dockerfile" \
		--tag "$target" \
		--platform linux/amd64 \
		--pull=missing \
		--no-cache \
		--timestamp "$image_timestamp" \
		"$repo"
}

rootfs_manifest() {
	local target=$1
	podman run --rm --interactive --pull=never --network none \
		"$target" sh -s <"$rootfs_manifest_script"
}

rootfs_identity() {
	rootfs_manifest "$1" | sha256sum | cut -d ' ' -f 1
}

verify_image() {
	local target=$1
	podman image exists "$target" ||
		fail "missing local kernel builder image: $target"
	local architecture
	architecture=$(podman image inspect --format '{{.Architecture}}' "$target")
	[[ $architecture == amd64 ]] ||
		fail 'kernel builder image has the wrong architecture'
	[[ $(podman image inspect --format \
		'{{ index .Config.Labels "org.rog5.kernel-builder.snapshot" }}' \
		"$target") == "$snapshot" ]] ||
		fail 'kernel builder image has the wrong Ubuntu snapshot'
		[[ $(podman image inspect --format \
			'{{ index .Config.Labels "org.rog5.kernel-builder.package-lock-sha256" }}' \
			"$target") == "$expected_lock_sha256" ]] ||
			fail 'kernel builder image has the wrong package lock'
		podman run --rm --pull=never --network none "$target" sh -ec '
			printf "package\tversion\n" > /tmp/installed-packages.tsv
			dpkg-query -W \
				-f="\${db:Status-Abbrev}\t\${binary:Package}\t\${Version}\n" |
				awk -F "\t" "\$1 == \"ii \" { print \$2 \"\\t\" \$3 }" |
				LC_ALL=C sort >> /tmp/installed-packages.tsv
		cmp /usr/share/rog5/kernel-builder-packages.tsv \
			/tmp/installed-packages.tsv
		clang --version | head -n 1
		ld.lld --version | head -n 1
		ccache --version | head -n 1
		pahole --version
	'
	printf 'image=%s\n' "$target"
	printf 'image_id=%s\n' \
		"$(podman image inspect --format '{{.Id}}' "$target")"
	printf 'image_digest=%s\n' \
		"$(podman image inspect --format '{{.Digest}}' "$target")"
	printf 'ubuntu_snapshot=%s\n' "$snapshot"
	printf 'package_lock_sha256=%s\n' "$expected_lock_sha256"
	printf 'rootfs_identity=%s\n' "$(rootfs_identity "$target")"
	printf 'builder_recipe_sha256=%s\n' \
		"$(sha256sum "$dockerfile" | cut -d ' ' -f 1)"
	printf 'rootfs_manifest_script_sha256=%s\n' \
		"$expected_rootfs_manifest_sha256"
}

case $action in
	build)
		build_image "$image"
		verify_image "$image"
		;;
	verify)
		verify_image "$image"
		;;
	reproduce)
		first=$image_repository:${image_name#*:}-repro-a
		second=$image_repository:${image_name#*:}-repro-b
		cache_run=repro-$$-$RANDOM
		build_image "$first" "$cache_run-a"
		build_image "$second" "$cache_run-b"
		verify_image "$first"
		verify_image "$second"
		first_id=$(podman image inspect --format '{{.Id}}' "$first")
		second_id=$(podman image inspect --format '{{.Id}}' "$second")
		first_digest=$(podman image inspect --format '{{.Digest}}' "$first")
		second_digest=$(podman image inspect --format '{{.Digest}}' "$second")
		first_rootfs=$(rootfs_identity "$first")
		second_rootfs=$(rootfs_identity "$second")
		[[ $first_rootfs == "$second_rootfs" ]] ||
			fail 'independent kernel builder root filesystems differ'
		printf 'first_image_id=%s\n' "$first_id"
		printf 'second_image_id=%s\n' "$second_id"
		printf 'first_image_digest=%s\n' "$first_digest"
		printf 'second_image_digest=%s\n' "$second_digest"
		printf 'reproduced_rootfs_identity=%s\n' "$first_rootfs"
		echo 'oci_identity_note=informational; distinct cache namespaces are recorded in image history'
		echo 'PASS independently fetched rootless kernel builder root filesystems match'
		;;
	manifest)
		podman image exists "$image" ||
			fail "missing local kernel builder image: $image"
		rootfs_manifest "$image"
		;;
	*)
		fail 'usage: bootstrap-kernel-builder.sh [build|verify|reproduce|manifest] [IMAGE]'
		;;
esac
