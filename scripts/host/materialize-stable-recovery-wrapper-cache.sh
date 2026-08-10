#!/usr/bin/env bash
set -euo pipefail

fail() {
	echo "FAIL $*" >&2
	exit 1
}

repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
initramfs=${1:?usage: materialize-stable-recovery-wrapper-cache.sh INITRAMFS CACHE_ROOT EXPECTED_ENTRY_ID OUTPUT_ROOT}
cache_root=${2:?missing stable-recovery wrapper cache root}
expected_entry_id=${3:?missing expected stable-recovery cache entry ID}
output_root=${4:?missing ignored materialization output root}

profile=$repo/configs/recovery-wrapper-cache/asus-5.4-stable-recovery-v1.json
cache_tool=$repo/scripts/host/stable-recovery-wrapper-cache.py
source_tree_tool=$repo/scripts/host/kernel-source-seal.py
build_script=$repo/scripts/device/build-asus-kexec-stage.sh
repack_script=$repo/scripts/device/repack-android-boot-v3.sh
source_volume=rog5-asus-v12a-source
builder_image=localhost/rog5-kernel-builder:ubuntu-24.04
reference_config=$repo/../work/linux-server/kernel-33.0210.0210.200/config-5.4.210-qgki-perf
template=$repo/artifacts/recovery-stage-v18/boot-5.4.210-kexec-stage-builtin-recovery.raw.img
mkbootimg=$repo/../work/linux-server/mkbootimg/mkbootimg.py
gki_certificate=$repo/artifacts/android-boot-tools-v1/gki/generate_gki_certificate.py
unpack_bootimg=$repo/../work/linux-server/mkbootimg/unpack_bootimg.py
avbtool=$repo/../work/linux-server/avb/avbtool.py
expected_builder_id=c5b80647ddd7fb29464b4735abbe27012ee4dc89be559b44b25c9b1ff59c9cec
expected_builder_digest=sha256:8513960144bb1ca77878a1364c03fb100c8b87fffb8440fd37a6cc4fc0043b41

for command in git podman python3 realpath; do
	command -v "$command" >/dev/null ||
		fail "missing wrapper-cache command: $command"
done
for path in "$initramfs" "$profile" "$cache_tool" "$source_tree_tool" \
	"$build_script" "$repack_script" "$reference_config" "$template" \
	"$mkbootimg" "$gki_certificate" "$unpack_bootimg" "$avbtool"; do
	[[ -f $path && ! -L $path ]] ||
		fail "missing regular nonsymlink wrapper-cache input: $path"
done
[[ $expected_entry_id =~ ^[0-9a-f]{64}$ ]] ||
	fail 'expected wrapper-cache entry ID is malformed'

initramfs=$(realpath -e "$initramfs")
cache_root=$(realpath -e "$cache_root")
output_root=$(realpath -m "$output_root")
case $cache_root in
	"$repo"/build/*) ;;
	*) fail 'wrapper cache must be below the ignored repository build directory' ;;
esac
case $output_root in
	"$repo"/build/*) ;;
	*) fail 'materialized wrapper must be below the ignored repository build directory' ;;
esac
git -C "$repo" check-ignore -q "$cache_root" ||
	fail 'wrapper cache is not ignored by Git'
git -C "$repo" check-ignore -q "$output_root" ||
	fail 'materialized wrapper output is not ignored by Git'
case $output_root in
	"$cache_root"|"$cache_root"/*)
		fail 'materialized wrapper output overlaps the cache'
		;;
esac
case $cache_root in
	"$output_root"|"$output_root"/*)
		fail 'wrapper cache overlaps the materialized output'
		;;
esac
[[ ! -e $output_root && ! -L $output_root ]] ||
	fail 'refusing existing wrapper-cache materialization output'

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

podman run --rm --network=none --security-opt label=disable \
	-v "$source_volume:/root/src:ro" \
	-v "$repo:/workspace:ro" \
	"$builder_image" \
	python3 /workspace/scripts/host/kernel-source-seal.py \
	/root/src/msm-5.4 |
	python3 "$cache_tool" materialize \
		--profile "$profile" \
		--source-seal - \
		--source-tree-tool "$source_tree_tool" \
		--reference-config "$reference_config" \
		--initramfs "$initramfs" \
		--build-script "$build_script" \
		--repack-script "$repack_script" \
		--boot-template "$template" \
		--mkbootimg "$mkbootimg" \
		--gki-certificate "$gki_certificate" \
		--unpack-bootimg "$unpack_bootimg" \
		--avbtool "$avbtool" \
		--cache-root "$cache_root" \
		--expected-entry-id "$expected_entry_id" \
		--output-root "$output_root"

printf 'wrapper_image=%s\n' "$output_root/wrapper.Image"
printf 'raw_wrapper=%s\n' "$output_root/stable-recovery.raw.img"
printf 'avb_wrapper=%s\n' "$output_root/stable-recovery.avb.img"
echo 'authority=none'
echo 'PASS pinned stable-recovery wrapper materialized without a kernel build'
