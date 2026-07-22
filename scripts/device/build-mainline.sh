#!/bin/sh
set -eu

source_dir=${SOURCE_DIR:-/root/src/linux-7.1.4}
output_dir=${OUTPUT_DIR:-/root/build/rog5-linux-7.1.4}
fragment=${FRAGMENT:-/root/rog5-build/rog5-mainline.fragment}
expected_commit=${LINUX_COMMIT:-7a5cef0db4795d9d453a12e0f61b5b7634fc4d40}
jobs=${JOBS:-1}

[ -d "$source_dir/.git" ] || { echo "ERROR missing source tree $source_dir" >&2; exit 1; }
[ -r "$fragment" ] || { echo "ERROR missing config fragment $fragment" >&2; exit 1; }
[ "$(git -C "$source_dir" rev-parse HEAD)" = "$expected_commit" ] || {
    echo 'ERROR source revision does not match the pinned commit' >&2
    exit 1
}

export KBUILD_BUILD_USER=rog5-linux
export KBUILD_BUILD_HOST=rog5-builder
export KBUILD_BUILD_TIMESTAMP="$(git -C "$source_dir" show -s --format=%cD HEAD)"

mkdir -p "$output_dir"
make -C "$source_dir" O="$output_dir" ARCH=arm64 LLVM=1 defconfig
"$source_dir/scripts/kconfig/merge_config.sh" -m -O "$output_dir" "$output_dir/.config" "$fragment"
make -C "$source_dir" O="$output_dir" ARCH=arm64 LLVM=1 olddefconfig
make -C "$source_dir" O="$output_dir" ARCH=arm64 LLVM=1 -j "$jobs" \
    Image.gz \
    qcom/sm8350-hdk.dtb \
    qcom/sm8350-mtp.dtb \
    qcom/sm8350-microsoft-surface-duo2.dtb \
    qcom/sm8350-sony-xperia-sagami-pdx214.dtb \
    qcom/sm8350-sony-xperia-sagami-pdx215.dtb

{
    printf 'kernel_commit=%s\n' "$expected_commit"
    printf 'compiler=%s\n' "$(clang --version | head -1)"
    sha256sum \
        "$output_dir/.config" \
        "$output_dir/arch/arm64/boot/Image.gz" \
        "$output_dir"/arch/arm64/boot/dts/qcom/sm8350-*.dtb
} > "$output_dir/build-meta.txt"

cat "$output_dir/build-meta.txt"
echo 'PASS compile-only upstream SM8350 baseline; these DTBs are not for booting on the ASUS phone'
