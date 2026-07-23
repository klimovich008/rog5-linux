#!/bin/sh
set -eu

source_dir=${SOURCE_DIR:-/root/src/msm-5.4}
output_dir=${OUTPUT_DIR:-/root/build/asus-kexec-stage}
reference_config=${REFERENCE_CONFIG:?missing REFERENCE_CONFIG}
jobs=${JOBS:-1}
expected_config=e8605b42cd27d372cea195811c3ff064346390a235572a0018c9dc8d048b5da4

[ -r "$source_dir/.rog5-kexec-source" ] || { echo 'FAIL unverified source tree' >&2; exit 1; }
[ "$(sha256sum "$reference_config" | cut -d ' ' -f 1)" = "$expected_config" ] || {
	echo 'FAIL reference config hash mismatch' >&2
	exit 1
}

mkdir -p "$output_dir"
install -m 0644 "$reference_config" "$output_dir/.config"
"$source_dir/scripts/config" --file "$output_dir/.config" \
	--enable KEXEC \
	--disable KEXEC_FILE \
	--disable UAPI_HEADER_TEST \
	--disable LOCALVERSION_AUTO \
	--set-str LOCALVERSION -qgki-perf-kexec-stage

export ARCH=arm64
export CROSS_COMPILE=aarch64-linux-gnu-
export LLVM=1
export LLVM_IAS=1
export DISABLE_WRAPPER=1
export ASUS_BUILD_PROJECT=ZS673KS
export KBUILD_BUILD_USER=rog5-linux
export KBUILD_BUILD_HOST=rog5-builder
export KBUILD_BUILD_VERSION=1
export KBUILD_BUILD_TIMESTAMP='Wed Apr 19 00:00:00 UTC 2023'
export KCFLAGS=-Wno-error=strict-prototypes

make -C "$source_dir" O="$output_dir" olddefconfig
grep -qx 'CONFIG_KEXEC=y' "$output_dir/.config"
grep -qx '# CONFIG_KEXEC_FILE is not set' "$output_dir/.config"
make -C "$source_dir" O="$output_dir" -j "$jobs" Image

image=$output_dir/arch/arm64/boot/Image
[ -s "$image" ] || { echo 'FAIL missing kexec-stage Image' >&2; exit 1; }
strings "$image" | grep -q 'Linux version 5.4.210.*-kexec-stage'
{
	printf 'source_sha256=%s\n' "$(sed -n 's/^source_sha256=//p' "$source_dir/.rog5-kexec-source")"
	printf 'compiler=%s\n' "$(clang --version | head -n 1)"
	sha256sum "$output_dir/.config" "$image"
} > "$output_dir/build-meta.txt"
cat "$output_dir/build-meta.txt"
echo 'PASS vendor-compatible 5.4.210 kexec-stage Image; compile-only'
