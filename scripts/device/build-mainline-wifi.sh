#!/bin/sh
set -eu

source_dir=${SOURCE_DIR:-/root/src/linux-7.1.4}
output_dir=${OUTPUT_DIR:-/root/build/rog5-linux-7.1.4-wifi}
base_fragment=${BASE_FRAGMENT:-/workspace/repo/configs/kernel/rog5-mainline.fragment}
network_fragment=${NETWORK_FRAGMENT:-/workspace/repo/configs/kernel/rog5-network-root.fragment}
wifi_fragment=${WIFI_FRAGMENT:-/workspace/repo/configs/kernel/rog5-wifi.fragment}
expected_commit=7a5cef0db4795d9d453a12e0f61b5b7634fc4d40
jobs=${JOBS:-1}
btf_jobs=1

[ -d "$source_dir/.git" ] || {
	echo 'FAIL missing pinned Linux source' >&2
	exit 1
}
for fragment in "$base_fragment" "$network_fragment" "$wifi_fragment"; do
	[ -r "$fragment" ] || {
		echo "FAIL missing kernel fragment: $fragment" >&2
		exit 1
	}
done
[ "$(git -C "$source_dir" rev-parse HEAD)" = "$expected_commit" ]
[ -z "$(git -C "$source_dir" status --porcelain)" ]
[ ! -d "$output_dir" ] ||
	[ -z "$(find "$output_dir" -mindepth 1 -maxdepth 1 -print -quit)" ] || {
		echo 'FAIL output directory is not empty' >&2
		exit 1
	}

export KBUILD_BUILD_USER=rog5-linux
export KBUILD_BUILD_HOST=rog5-builder
KBUILD_BUILD_TIMESTAMP=$(git -C "$source_dir" show -s --format=%cD HEAD)
export KBUILD_BUILD_TIMESTAMP
export PYTHONHASHSEED=0

mkdir -p "$output_dir"
make -C "$source_dir" O="$output_dir" ARCH=arm64 LLVM=1 defconfig
"$source_dir/scripts/kconfig/merge_config.sh" -m -O "$output_dir" \
	"$output_dir/.config" "$base_fragment" "$network_fragment" \
	"$wifi_fragment"
make -C "$source_dir" O="$output_dir" ARCH=arm64 LLVM=1 olddefconfig
make -C "$source_dir" O="$output_dir" ARCH=arm64 LLVM=1 -j "$jobs" \
	JOBS="$btf_jobs" Image.gz modules

modules_stage=$output_dir/modules-staging
make -C "$source_dir" O="$output_dir" ARCH=arm64 LLVM=1 \
	INSTALL_MOD_PATH="$modules_stage" modules_install
source_date_epoch=$(git -C "$source_dir" show -s --format=%ct HEAD)
tar --sort=name --mtime="@$source_date_epoch" --owner=0 --group=0 \
	--numeric-owner -C "$modules_stage" -cf - lib/modules |
	gzip -n >"$output_dir/modules.tar.gz.tmp"
mv "$output_dir/modules.tar.gz.tmp" "$output_dir/modules.tar.gz"

{
	printf 'kernel_commit=%s\n' "$expected_commit"
	printf 'compiler=%s\n' "$(clang --version | head -1)"
	printf 'python_hash_seed=%s\n' "$PYTHONHASHSEED"
	printf 'build_jobs=%s\n' "$jobs"
	printf 'pahole_jobs=%s\n' "$btf_jobs"
	printf 'base_fragment_sha256=%s\n' \
		"$(sha256sum "$base_fragment" | cut -d ' ' -f 1)"
	printf 'network_fragment_sha256=%s\n' \
		"$(sha256sum "$network_fragment" | cut -d ' ' -f 1)"
	printf 'wifi_fragment_sha256=%s\n' \
		"$(sha256sum "$wifi_fragment" | cut -d ' ' -f 1)"
	printf 'config_sha256=%s\n' \
		"$(sha256sum "$output_dir/.config" | cut -d ' ' -f 1)"
	printf 'image_sha256=%s\n' \
		"$(sha256sum "$output_dir/arch/arm64/boot/Image" | cut -d ' ' -f 1)"
	printf 'image_gz_sha256=%s\n' \
		"$(sha256sum "$output_dir/arch/arm64/boot/Image.gz" | cut -d ' ' -f 1)"
	printf 'modules_sha256=%s\n' \
		"$(sha256sum "$output_dir/modules.tar.gz" | cut -d ' ' -f 1)"
} >"$output_dir/build-meta.txt"

cat "$output_dir/build-meta.txt"
echo 'PASS dedicated Linux 7.1.4 UFS-disabled network-root Wi-Fi build'
