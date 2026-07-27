#!/bin/sh
set -eu

source_dir=${SOURCE_DIR:-/root/src/linux-7.1.4-discovery}
output_dir=${OUTPUT_DIR:-/root/build/rog5-linux-7.1.4-persistent-root}
base_fragment=${BASE_FRAGMENT:-/root/rog5-build/rog5-mainline.fragment}
discovery_fragment=${DISCOVERY_FRAGMENT:-/root/rog5-build/rog5-ufs-discovery.fragment}
root_fragment=${ROOT_FRAGMENT:-/root/rog5-build/rog5-persistent-root.fragment}
expected_base=7a5cef0db4795d9d453a12e0f61b5b7634fc4d40
expected_tree=d2f03d2055227b8b72ab41be949847a066924c5a
jobs=${JOBS:-1}
btf_jobs=1

[ -d "$source_dir/.git" ] || {
	echo "FAIL missing source tree $source_dir" >&2
	exit 1
}
for fragment in "$base_fragment" "$discovery_fragment" "$root_fragment"; do
	[ -r "$fragment" ] || {
		echo "FAIL missing kernel fragment: $fragment" >&2
		exit 1
	}
done
[ "$(git -C "$source_dir" rev-parse HEAD^)" = "$expected_base" ]
[ "$(git -C "$source_dir" rev-parse 'HEAD^{tree}')" = "$expected_tree" ]
[ -z "$(git -C "$source_dir" status --porcelain)" ]
[ ! -d "$output_dir" ] ||
	[ -z "$(find "$output_dir" -mindepth 1 -maxdepth 1 -print -quit)" ] || {
	echo 'FAIL output directory is not empty' >&2
	exit 1
}

export KBUILD_BUILD_USER=rog5-linux
export KBUILD_BUILD_HOST=rog5-builder
export KBUILD_BUILD_TIMESTAMP
KBUILD_BUILD_TIMESTAMP=$(git -C "$source_dir" show -s \
	--format=%cD "$expected_base")
export PYTHONHASHSEED=0

mkdir -p "$output_dir"
make -C "$source_dir" O="$output_dir" ARCH=arm64 LLVM=1 defconfig
"$source_dir/scripts/kconfig/merge_config.sh" -m -O "$output_dir" \
	"$output_dir/.config" "$base_fragment" "$discovery_fragment" \
	"$root_fragment"
make -C "$source_dir" O="$output_dir" ARCH=arm64 LLVM=1 olddefconfig
make -C "$source_dir" O="$output_dir" ARCH=arm64 LLVM=1 -j "$jobs" \
	JOBS="$btf_jobs" Image.gz

{
	printf 'base_commit=%s\n' "$expected_base"
	printf 'patched_commit=%s\n' "$(git -C "$source_dir" rev-parse HEAD)"
	printf 'patched_tree=%s\n' "$expected_tree"
	printf 'compiler=%s\n' "$(clang --version | head -1)"
	printf 'python_hash_seed=%s\n' "$PYTHONHASHSEED"
	printf 'pahole_jobs=%s\n' "$btf_jobs"
	sha256sum "$base_fragment" "$discovery_fragment" "$root_fragment" \
		"$output_dir/.config" \
		"$output_dir/arch/arm64/boot/Image" \
		"$output_dir/arch/arm64/boot/Image.gz"
} >"$output_dir/build-meta.txt"

cat "$output_dir/build-meta.txt"
echo 'PASS dedicated Linux 7.1.4 read-only persistent-root kernel build'
