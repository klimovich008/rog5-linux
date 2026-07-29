#!/usr/bin/env bash
set -euo pipefail

fail() {
	echo "FAIL $*" >&2
	exit 1
}

repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
output=${1:?usage: build-a660-runtime-tools.sh OUTPUT_DIRECTORY}
static_image=${ROG5_A660_STATIC_BUILD_IMAGE:-localhost/rog5-persistent-root-verifier:alpine-3.24}
vulkan_image=${ROG5_A660_VULKAN_BUILD_IMAGE:-localhost/rog5-a660-runtime-builder:arch-2026.07.24}
expected_static_id=d5fb16636fadea937b74dc3e062617d74a12577fd3fcc3f61fec24d0f7364495
expected_vulkan_id=8c84a3b902803fafcc2d9ab4671e6ff9b3ca1b9297cee55cdc4caad34b895e91
publisher=$repo/scripts/host/a660-runtime-publish.py
epoch=1681862400

for command in cmp cut dirname id install mktemp podman readelf \
	python3 realpath rm sha256sum stat sync; do
	command -v "$command" >/dev/null ||
		fail "missing A660 runtime-tools command: $command"
done
[[ -f $publisher && ! -L $publisher && -x $publisher ]] ||
	fail 'A660 atomic publisher is absent or linked'
case $output in
	/*) ;;
	*) fail 'runtime-tools output must be absolute' ;;
esac
output_parent=$(dirname -- "$output")
output_name=$(basename -- "$output")
case $output_name in ''|.|..) fail 'runtime-tools output name is invalid' ;; esac
[[ -d $output_parent && ! -L $output_parent ]] ||
	fail 'runtime-tools output parent is absent or linked'
output_parent=$(realpath -e "$output_parent")
[[ $output == "$output_parent/$output_name" ]] ||
	fail 'runtime-tools output path is not canonical'
[[ $(stat -c %u "$output_parent") == "$EUID" ]] ||
	fail 'runtime-tools output parent is not caller-owned'
parent_mode=$(stat -c %a "$output_parent")
(( (8#$parent_mode & 8#022) == 0 )) ||
	fail 'runtime-tools output parent is group- or world-writable'
[[ ! -e $output && ! -L $output ]] ||
	fail 'runtime-tools output already exists'

for image in "$static_image" "$vulkan_image"; do
	podman image exists "$image" ||
		fail "required A660 build image is absent: $image"
	[[ $(podman image inspect "$image" --format '{{.Architecture}}') == arm64 ]] ||
		fail "A660 build image is not arm64: $image"
done
[[ $(podman image inspect "$static_image" --format '{{.Id}}') == \
	"$expected_static_id" ]] ||
	fail 'static A660 builder image identity changed'
[[ $(podman image inspect "$vulkan_image" --format '{{.Id}}') == \
	"$expected_vulkan_id" ]] ||
	fail 'Vulkan A660 builder image identity changed'
observed_packages=$(podman run --rm --network none \
	--entrypoint /bin/cat "$vulkan_image" \
	/usr/share/rog5-a660-builder-packages)
expected_packages=$'gcc 16.1.1+r12+g301eb08fa2c5-1\nlibisl 0.28-1\nlibmpc 1.4.1-1\npkgconf 3.0.4-1\nvulkan-headers 1:1.4.350.1-1\nvulkan-icd-loader 1.4.350.1-1'
[[ $observed_packages == "$expected_packages" ]] ||
	fail 'A660 Vulkan builder package identity changed'

first=$(mktemp -d "$output_parent/.a660-runtime-tools.first.XXXXXX")
second=$(mktemp -d "$output_parent/.a660-runtime-tools.second.XXXXXX")
succeeded=0
cleanup() {
	if [[ $succeeded != 1 ]]; then
		rm -rf -- "$first" "$second"
	fi
}
trap cleanup EXIT HUP INT TERM
chmod 0700 "$first" "$second"

build_set() {
	local directory=$1

	podman run --rm --network none \
		--mount "type=bind,source=$repo,target=/workspace,readonly" \
		--mount "type=bind,source=$directory,target=/output" \
		--env CC=gcc \
		"$static_image" \
		/workspace/scripts/device/build-a660-cgroup-exec.sh \
		/output/rog5-cgroup-exec
	podman run --rm --network none \
		--mount "type=bind,source=$repo,target=/workspace,readonly" \
		--mount "type=bind,source=$directory,target=/output" \
		--env CC=gcc \
		"$static_image" \
		/workspace/scripts/device/build-persistent-root-verifier-static.sh \
		/output/persistent-root-verify
	podman run --rm --network none \
		--mount "type=bind,source=$repo,target=/workspace,readonly" \
		--mount "type=bind,source=$directory,target=/output" \
		--env CC=gcc \
		--env EXPECTED_ELF_MACHINE=AArch64 \
		--env EXPECTED_INTERPRETER=/lib/ld-linux-aarch64.so.1 \
		--env EXPECTED_NEEDED=libvulkan.so.1 \
		"$vulkan_image" \
		/workspace/scripts/device/build-a660-vulkan-submit.sh \
		/output/rog5-vulkan-submit
}

build_set "$first"
build_set "$second"
for name in persistent-root-verify rog5-cgroup-exec rog5-vulkan-submit; do
	cmp "$first/$name" "$second/$name" ||
		fail "two complete A660 runtime-tool builds differ: $name"
	[[ $(stat -c '%u:%g:%a' "$first/$name") == "$EUID:$(id -g):755" ]] ||
		fail "A660 runtime-tool metadata changed: $name"
	readelf -h "$first/$name" | grep -q 'Machine:.*AArch64' ||
		fail "A660 runtime tool is not AArch64: $name"
done
for name in persistent-root-verify rog5-cgroup-exec; do
	if readelf -l "$first/$name" |
		grep -q 'Requesting program interpreter'; then
		fail "static A660 runtime tool has an interpreter: $name"
	fi
	if readelf -d "$first/$name" 2>/dev/null |
		grep -q 'Shared library:'; then
		fail "static A660 runtime tool has a dependency: $name"
	fi
done
readelf -l "$first/rog5-vulkan-submit" |
	grep -Fq 'Requesting program interpreter: /lib/ld-linux-aarch64.so.1' ||
	fail 'A660 Vulkan helper interpreter changed'
readelf -d "$first/rog5-vulkan-submit" |
	grep -Fq 'Shared library: [libvulkan.so.1]' ||
	fail 'A660 Vulkan helper loader dependency changed'

static_image_id=$(podman image inspect "$static_image" --format '{{.Id}}')
vulkan_image_id=$(podman image inspect "$vulkan_image" --format '{{.Id}}')
{
	printf 'format=rog5-a660-runtime-tools-v1\n'
	printf 'source_date_epoch=%s\n' "$epoch"
	printf 'static_builder_image_id=%s\n' "$static_image_id"
	printf 'vulkan_builder_image_id=%s\n' "$vulkan_image_id"
	printf 'builder_packages_sha256=%s\n' \
		"$(printf '%s\n' "$observed_packages" |
			sha256sum | cut -d ' ' -f 1)"
	for name in persistent-root-verify rog5-cgroup-exec \
		rog5-vulkan-submit; do
		printf '%s_size=%s\n' \
			"${name//-/_}" "$(stat -c %s "$first/$name")"
		printf '%s_sha256=%s\n' \
			"${name//-/_}" \
			"$(sha256sum "$first/$name" | cut -d ' ' -f 1)"
	done
} >"$first/manifest"
chmod 0400 "$first/manifest"
touch -d "@$epoch" "$first/manifest" "$first"/persistent-root-verify \
	"$first"/rog5-cgroup-exec "$first"/rog5-vulkan-submit
for name in manifest persistent-root-verify rog5-cgroup-exec \
	rog5-vulkan-submit; do
	sync -f "$first/$name"
done
sync -f "$first"
rm -rf -- "$second"
if ! python3 "$publisher" --stage "$first" --output "$output" >/dev/null; then
	fail 'A660 runtime-tools atomic publication failed'
fi
[[ ! -e $first && ! -L $first && -d $output ]] ||
	fail 'A660 runtime-tools publication identity is ambiguous'
succeeded=1
printf 'format=rog5-a660-runtime-tools-publication-v1\n'
printf 'directory=%s\n' "$output"
printf 'manifest_sha256=%s\n' \
	"$(sha256sum "$output/manifest" | cut -d ' ' -f 1)"
