#!/bin/sh
set -eu

source_dir=${SOURCE_DIR:-/root/src/linux-7.1.4}
output_dir=${OUTPUT_DIR:-/root/build/rog5-linux-7.1.4}
fragment=${FRAGMENT:-/root/rog5-build/rog5-mainline.fragment}
expected_commit=${LINUX_COMMIT:-7a5cef0db4795d9d453a12e0f61b5b7634fc4d40}
jobs=${JOBS:-1}
btf_jobs=1
script_dir=$(CDPATH='' cd -- "$(dirname "$0")" && pwd)
kernel_contract=$script_dir/kernel-build-contract.sh

[ -d "$source_dir/.git" ] || { echo "ERROR missing source tree $source_dir" >&2; exit 1; }
[ -r "$fragment" ] || { echo "ERROR missing config fragment $fragment" >&2; exit 1; }
[ -f "$kernel_contract" ] && [ ! -L "$kernel_contract" ] &&
	[ "$(stat -c '%u' "$kernel_contract")" = "$(id -u)" ] &&
	[ "$(stat -c '%a' "$kernel_contract")" = 755 ] || {
	echo "ERROR unsafe kernel build contract $kernel_contract" >&2
	exit 1
}
kernel_contract_sha256=$(sha256sum "$kernel_contract" | cut -d ' ' -f 1)
# shellcheck disable=SC1090,SC1091
. "$kernel_contract"
[ -d "$source_dir" ] && [ ! -L "$source_dir" ] || {
	echo 'ERROR kernel source must be a regular directory' >&2
	exit 1
}
source_dir=$(realpath -e -- "$source_dir")
output_dir=$(realpath -m -- "$output_dir")
case $output_dir in
	"$source_dir"|"$source_dir"/*)
		echo 'ERROR kernel output must be outside the source tree' >&2
		exit 1
		;;
esac
[ "$(git -C "$source_dir" rev-parse HEAD)" = "$expected_commit" ] || {
    echo 'ERROR source revision does not match the pinned commit' >&2
    exit 1
}
[ -z "$(git -C "$source_dir" status --porcelain)" ] || {
	echo 'ERROR source tree has uncommitted changes' >&2
	exit 1
}

export KBUILD_BUILD_USER=rog5-linux
export KBUILD_BUILD_HOST=rog5-builder
KBUILD_BUILD_TIMESTAMP=$(git -C "$source_dir" show -s --format=%cD HEAD)
export KBUILD_BUILD_TIMESTAMP
export PYTHONHASHSEED=0

source_tree=$(git -C "$source_dir" rev-parse 'HEAD^{tree}')
fragment_sha256=$(sha256sum "$fragment" | cut -d ' ' -f 1)
cache_identity=$(rog5_kernel_cache_identity)
toolchain_identity=$(rog5_kernel_toolchain_identity \
	make clang clang++ ld.lld llvm-ar llvm-nm llvm-objcopy llvm-strip \
	llvm-readelf pahole python3 bc bison flex openssl perl depmod tar gzip)
build_state=$(
	printf 'format=rog5-kbuild-inputs-v1\n'
	printf 'source_path=%s\n' "$source_dir"
	printf 'output_path=%s\n' "$output_dir"
	printf 'source_commit=%s\n' "$expected_commit"
	printf 'source_tree=%s\n' "$source_tree"
	printf 'fragment_sha256=%s\n' "$fragment_sha256"
	printf 'builder_sha256=%s\n' \
		"$(sha256sum "$0" | cut -d ' ' -f 1)"
	printf 'contract_sha256=%s\n' "$kernel_contract_sha256"
	printf 'arch=arm64\nllvm=1\n'
	printf 'kbuild_user=%s\n' "$KBUILD_BUILD_USER"
	printf 'kbuild_host=%s\n' "$KBUILD_BUILD_HOST"
	printf 'kbuild_timestamp=%s\n' "$KBUILD_BUILD_TIMESTAMP"
	printf 'python_hash_seed=%s\n' "$PYTHONHASHSEED"
	printf 'pahole_jobs=%s\n' "$btf_jobs"
	printf '%s\n' "$cache_identity" "$toolchain_identity"
)
rog5_kernel_prepare_output "$output_dir" "$build_state"
rog5_kernel_cache_stats

rog5_kernel_make -C "$source_dir" O="$output_dir" ARCH=arm64 LLVM=1 defconfig
"$source_dir/scripts/kconfig/merge_config.sh" -m -O "$output_dir" "$output_dir/.config" "$fragment"
rog5_kernel_make -C "$source_dir" O="$output_dir" ARCH=arm64 LLVM=1 olddefconfig
rog5_kernel_make -C "$source_dir" O="$output_dir" ARCH=arm64 LLVM=1 -j "$jobs" \
    JOBS="$btf_jobs" \
    Image.gz \
    modules \
    qcom/sm8350-hdk.dtb \
    qcom/sm8350-mtp.dtb \
    qcom/sm8350-microsoft-surface-duo2.dtb \
    qcom/sm8350-sony-xperia-sagami-pdx214.dtb \
    qcom/sm8350-sony-xperia-sagami-pdx215.dtb

modules_stage=$output_dir/modules-staging
rm -rf "$modules_stage"
rog5_kernel_make -C "$source_dir" O="$output_dir" ARCH=arm64 LLVM=1 \
    INSTALL_MOD_PATH="$modules_stage" modules_install
source_date_epoch=$(git -C "$source_dir" show -s --format=%ct "$expected_commit")
tar --sort=name --mtime="@$source_date_epoch" --owner=0 --group=0 --numeric-owner \
	-C "$modules_stage" -cf - lib/modules | gzip -n > "$output_dir/modules.tar.gz.tmp"
mv "$output_dir/modules.tar.gz.tmp" "$output_dir/modules.tar.gz"
rog5_kernel_cache_stats

{
    printf 'kernel_commit=%s\n' "$expected_commit"
    printf 'compiler=%s\n' "$(clang --version | head -1)"
    printf 'python_hash_seed=%s\n' "$PYTHONHASHSEED"
    printf 'pahole_jobs=%s\n' "$btf_jobs"
    printf 'incremental_output=%s\n' "${INCREMENTAL_BUILD:-0}"
    printf '%s\n' "$cache_identity"
    sha256sum \
        "$output_dir/.config" \
        "$output_dir/arch/arm64/boot/Image" \
        "$output_dir/arch/arm64/boot/Image.gz" \
        "$output_dir/modules.tar.gz" \
        "$output_dir"/arch/arm64/boot/dts/qcom/sm8350-*.dtb
} > "$output_dir/build-meta.txt"

cat "$output_dir/build-meta.txt"
echo 'PASS compile-only upstream SM8350 baseline; these DTBs are not for booting on the ASUS phone'
