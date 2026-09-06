#!/usr/bin/env bash
set -euo pipefail

repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)
rootfs_url=${ROOTFS_URL:-https://ca.us.mirror.archlinuxarm.org/os/ArchLinuxARM-aarch64-latest.tar.gz}
keyring_repository=${KEYRING_REPOSITORY:-https://github.com/archlinuxarm/archlinuxarm-keyring.git}
keyring_commit=${KEYRING_COMMIT:-91e6b11698f8df66042d56aaa56fbe9c9263847d}
cache_dir=${CACHE_DIRECTORY:-$repo/artifacts/arch}
builder_image=${BUILDER_IMAGE:-localhost/rog5-kernel-builder:ubuntu-24.04}

for command in curl git podman realpath sha256sum stat; do
	command -v "$command" >/dev/null
done

name=${rootfs_url##*/}
[[ $name == ArchLinuxARM-aarch64-latest.tar.gz ]] || {
	echo "FAIL refusing unexpected rootfs filename: $name" >&2
	exit 1
}

mkdir -p "$cache_dir"
cache_dir=$(realpath "$cache_dir")
rootfs=$cache_dir/$name
signature=$rootfs.sig
rootfs_part=$rootfs.part
signature_part=$signature.part
keyring_dir=$cache_dir/keyring-$keyring_commit

if [[ ! -d $keyring_dir/.git ]]; then
	[[ ! -e $keyring_dir ]] || {
		echo "FAIL incomplete keyring path: $keyring_dir" >&2
		exit 1
	}
	keyring_part=$(mktemp -d "$cache_dir/keyring-part.XXXXXX")
	git -C "$keyring_part" init
	git -C "$keyring_part" remote add origin "$keyring_repository"
	git -C "$keyring_part" fetch --depth=1 origin "$keyring_commit"
	git -C "$keyring_part" checkout --detach FETCH_HEAD
	[[ $(git -C "$keyring_part" rev-parse HEAD) == "$keyring_commit" ]]
	mv "$keyring_part" "$keyring_dir"
fi
[[ $(git -C "$keyring_dir" rev-parse HEAD) == "$keyring_commit" ]]
[[ -z $(git -C "$keyring_dir" status --porcelain) ]]
[[ -s $keyring_dir/archlinuxarm.gpg ]]

verify_rootfs() {
	local archive=$1
	local detached_signature=$2
	podman run --rm --network none \
		--mount "type=bind,source=$cache_dir,target=/input,readonly" \
		--mount "type=bind,source=$repo,target=/workspace/repo,readonly" \
		"$builder_image" \
		sh /workspace/repo/scripts/device/verify-arch-rootfs.sh \
		"/input/$(basename "$archive")" \
		"/input/$(basename "$detached_signature")" \
		"/input/$(basename "$keyring_dir")/archlinuxarm.gpg"
}

if [[ -e $rootfs || -e $signature ]]; then
	[[ -s $rootfs && -s $signature ]] || {
		echo 'FAIL only one final Arch input exists; refusing an implicit overwrite' >&2
		exit 1
	}
	verify_rootfs "$rootfs" "$signature"
else
	curl --fail --location --retry 3 --continue-at - \
		--output "$rootfs_part" "$rootfs_url"
	curl --fail --location --retry 3 \
		--output "$signature_part" "$rootfs_url.sig"
	verify_rootfs "$rootfs_part" "$signature_part"
	mv "$rootfs_part" "$rootfs"
	mv "$signature_part" "$signature"
fi

hash=$(sha256sum "$rootfs" | cut -d ' ' -f 1)
size=$(stat -c %s "$rootfs")
printf 'PASS signed Arch rootfs size=%s sha256=%s\n' "$size" "$hash"
