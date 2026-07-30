#!/usr/bin/env bash
set -euo pipefail

fail() {
	echo "FAIL $*" >&2
	exit 1
}

repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
recipe=$repo/containers/kernel-builder/Dockerfile.historical-20260724
image=${1:-localhost/rog5-kernel-builder:historical-20260724}
expected_recipe=312fe54127b282fe6ece395b024b5ab9150e9e606d8b40d3ed5144dea8941556
expected_packages=9310a47eab66545b98d69d5522313d064bfad17c80e1716f73e01119b83d4e22
expected_original_id=34ecc17078b364df195ad61253520b1cac487dca05773dc4b2fc2bacb0941941
expected_original_digest=sha256:7b2e3415dc638ca4864912c9aa4905425561e21b9d08f1e60e4cfb0a3aa6ff8c

[[ $image =~ ^[a-zA-Z0-9._:/-]+$ && $image != -* ]] ||
	fail 'invalid historical builder image reference'
for command_name in cut podman sha256sum; do
	command -v "$command_name" >/dev/null ||
		fail "missing historical builder command: $command_name"
done
[[ -f $recipe && ! -L $recipe ]] ||
	fail 'missing regular historical builder recipe'
[[ $(sha256sum "$recipe" | cut -d ' ' -f 1) == "$expected_recipe" ]] ||
	fail 'historical builder recipe changed'
podman image exists "$image" ||
	fail "missing local historical builder image: $image"
[[ $(podman image inspect --format '{{.Architecture}}' "$image") == amd64 ]] ||
	fail 'historical builder image architecture changed'

label() {
	podman image inspect --format "{{ index .Config.Labels \"$1\" }}" "$image"
}
[[ $(label org.rog5.kernel-builder.profile) == \
	historical-network-root-v1 ]] ||
	fail 'historical builder profile label changed'
[[ $(label org.rog5.kernel-builder.snapshot) == 20260724T020000Z ]] ||
	fail 'historical builder snapshot label changed'
[[ $(label org.rog5.kernel-builder.original-image-id) == \
	"$expected_original_id" ]] ||
	fail 'historical builder original image identity changed'
[[ $(label org.rog5.kernel-builder.original-image-digest) == \
	"$expected_original_digest" ]] ||
	fail 'historical builder original digest changed'

report=$(podman run --rm --pull=never --network=none "$image" sh -ec '
	dpkg-query -W -f="\${binary:Package}\t\${Version}\n" |
		LC_ALL=C sort |
		sha256sum
	dpkg-query -W -f="\${binary:Package}\t\${Version}\n" \
		libc6 libc-bin libc-dev-bin libc6-dev |
		LC_ALL=C sort
	clang --version | head -n 1
	ld.lld --version
	pahole --version
')
[[ $(sed -n '1s/[[:space:]].*//p' <<<"$report") == \
	"$expected_packages" ]] ||
	fail 'historical builder package closure changed'
for expected in \
	$'libc-bin\t2.39-0ubuntu8.7' \
	$'libc-dev-bin\t2.39-0ubuntu8.7' \
	$'libc6-dev:amd64\t2.39-0ubuntu8.7' \
	$'libc6:amd64\t2.39-0ubuntu8.7' \
	'Ubuntu clang version 18.1.3 (1ubuntu1)' \
	'Ubuntu LLD 18.1.3 (compatible with GNU linkers)' \
	'v1.25'; do
	grep -Fxq -- "$expected" <<<"$report" ||
		fail "historical builder tool contract changed: $expected"
done

printf 'image=%s\n' "$image"
printf 'image_id=%s\n' \
	"$(podman image inspect --format '{{.Id}}' "$image")"
printf 'image_digest=%s\n' \
	"$(podman image inspect --format '{{.Digest}}' "$image")"
printf 'original_image_id=%s\n' "$expected_original_id"
printf 'original_image_digest=%s\n' "$expected_original_digest"
printf 'ubuntu_snapshot=20260724T020000Z\n'
printf 'package_closure_sha256=%s\n' "$expected_packages"
printf 'builder_recipe_sha256=%s\n' "$expected_recipe"
echo 'PASS reconstructed historical network-root builder environment'
