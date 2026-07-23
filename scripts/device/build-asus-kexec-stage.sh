#!/bin/sh
set -eu

source_dir=${SOURCE_DIR:-/root/src/msm-5.4}
output_dir=${OUTPUT_DIR:-/root/build/asus-kexec-stage}
reference_config=${REFERENCE_CONFIG:?missing REFERENCE_CONFIG}
jobs=${JOBS:-1}
kexec_file=${KEXEC_FILE:-0}
expected_config=e8605b42cd27d372cea195811c3ff064346390a235572a0018c9dc8d048b5da4

[ "$kexec_file" = 0 ] || [ "$kexec_file" = 1 ]
[ -r "$source_dir/.rog5-kexec-source" ] || { echo 'FAIL unverified source tree' >&2; exit 1; }
[ "$(sha256sum "$reference_config" | cut -d ' ' -f 1)" = "$expected_config" ] || {
	echo 'FAIL reference config hash mismatch' >&2
	exit 1
}

mkdir -p "$output_dir"
install -m 0644 "$reference_config" "$output_dir/.config"
"$source_dir/scripts/config" --file "$output_dir/.config" \
	--enable KEXEC \
	--disable UAPI_HEADER_TEST \
	--disable LOCALVERSION_AUTO
if [ "$kexec_file" = 1 ]; then
	"$source_dir/scripts/config" --file "$output_dir/.config" \
		--enable KEXEC_FILE \
		--disable KEXEC_SIG \
		--disable KEXEC_IMAGE_VERIFY_SIG \
		--set-str LOCALVERSION -qgki-perf-kexec-file-stage
	release_pattern='Linux version 5.4.210.*-kexec-file-stage'
else
	"$source_dir/scripts/config" --file "$output_dir/.config" \
		--disable KEXEC_FILE \
		--set-str LOCALVERSION -qgki-perf-kexec-stage
	release_pattern='Linux version 5.4.210.*-kexec-stage'
fi

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
if [ "$kexec_file" = 1 ]; then
	grep -qx 'CONFIG_KEXEC_FILE=y' "$output_dir/.config"
	grep -qx '# CONFIG_KEXEC_SIG is not set' "$output_dir/.config"
else
	grep -qx '# CONFIG_KEXEC_FILE is not set' "$output_dir/.config"
fi
make -C "$source_dir" O="$output_dir" -j "$jobs" Image

image=$output_dir/arch/arm64/boot/Image
[ -s "$image" ] || { echo 'FAIL missing kexec-stage Image' >&2; exit 1; }
strings "$image" | grep -q "$release_pattern"
{
	printf 'source_sha256=%s\n' "$(sed -n 's/^source_sha256=//p' "$source_dir/.rog5-kexec-source")"
	printf 'kexec_file=%s\n' "$kexec_file"
	printf 'compiler=%s\n' "$(clang --version | head -n 1)"
	sha256sum "$output_dir/.config" "$image"
} > "$output_dir/build-meta.txt"
cat "$output_dir/build-meta.txt"
echo "PASS vendor-compatible 5.4.210 kexec-stage Image; kexec_file=$kexec_file; compile-only"
