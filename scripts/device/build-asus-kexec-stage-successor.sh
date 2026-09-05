#!/bin/sh
set -eu

source_dir=${SOURCE_DIR:-/root/src/msm-5.4}
output_dir=${OUTPUT_DIR:-/root/build/asus-kexec-stage}
reference_config=${REFERENCE_CONFIG:?missing REFERENCE_CONFIG}
reference_config_profile=${REFERENCE_CONFIG_PROFILE:-accepted-wrapper-v18-v1}
jobs=${JOBS:-1}
kexec_file=${KEXEC_FILE:-0}
initramfs_source=${INITRAMFS_SOURCE:-}
initramfs_sha256=${INITRAMFS_SHA256:-}

case $reference_config_profile in
accepted-wrapper-v18-v1)
	expected_config=df28224e6e8d2dfc825ac49dc9f6bdeb12bbcdae2dff92cbbf14a8a94177578f
	;;
*)
	echo "FAIL unsupported ASUS reference-config profile: $reference_config_profile" >&2
	exit 1
	;;
esac

[ "$kexec_file" = 0 ] || [ "$kexec_file" = 1 ]
[ -n "$initramfs_source" ] || [ -z "$initramfs_sha256" ] || {
	echo 'FAIL initramfs hash supplied without an initramfs' >&2
	exit 1
}
[ -z "$initramfs_source" ] || {
	[ -r "$initramfs_source" ]
	[ "${#initramfs_sha256}" -eq 64 ]
	case $initramfs_sha256 in *[!0-9a-f]*) exit 1 ;; esac
	[ "$(sha256sum "$initramfs_source" | cut -d ' ' -f 1)" = "$initramfs_sha256" ]
}
[ -r "$source_dir/.rog5-kexec-source" ] || { echo 'FAIL unverified source tree' >&2; exit 1; }
[ "$(sha256sum "$reference_config" | cut -d ' ' -f 1)" = "$expected_config" ] || {
	echo 'FAIL reference config hash mismatch' >&2
	exit 1
}

[ ! -d "$output_dir" ] || [ -z "$(find "$output_dir" -mindepth 1 -maxdepth 1 -print -quit)" ] || {
	echo 'FAIL refusing nonempty output directory; use a fresh build directory' >&2
	exit 1
}
mkdir -p "$output_dir"
if [ -n "$initramfs_source" ]; then
	staged_initramfs=/root/build/rog5-kexec-stage-initramfs.cpio.gz
	if [ "$initramfs_source" != "$staged_initramfs" ]; then
		install -m 0644 "$initramfs_source" "$staged_initramfs"
	fi
	initramfs_source=$staged_initramfs
fi
install -m 0644 "$reference_config" "$output_dir/.config"
"$source_dir/scripts/config" --file "$output_dir/.config" \
	--enable KEXEC \
	--disable UAPI_HEADER_TEST \
	--disable LOCALVERSION_AUTO
if [ "$kexec_file" = 1 ]; then
	"$source_dir/scripts/config" --file "$output_dir/.config" \
		--enable KEXEC_FILE \
		--disable KEXEC_SIG \
		--disable KEXEC_IMAGE_VERIFY_SIG
	localversion=-qgki-perf-kexec-file-stage
else
	"$source_dir/scripts/config" --file "$output_dir/.config" \
		--disable KEXEC_FILE
	localversion=-qgki-perf-kexec-stage
fi
if [ -n "$initramfs_source" ]; then
	localversion=$localversion-builtin-recovery
	"$source_dir/scripts/config" --file "$output_dir/.config" \
		--set-str INITRAMFS_SOURCE "$initramfs_source"
else
	"$source_dir/scripts/config" --file "$output_dir/.config" \
		--set-str INITRAMFS_SOURCE ""
fi
"$source_dir/scripts/config" --file "$output_dir/.config" \
	--set-str LOCALVERSION "$localversion"
release_pattern="Linux version 5.4.210.*$localversion"

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
debug_prefix_map=-fdebug-prefix-map=$output_dir=/rog5-build
export KCFLAGS="-Wno-error=strict-prototypes $debug_prefix_map"
export KAFLAGS=$debug_prefix_map

make -C "$source_dir" O="$output_dir" olddefconfig
grep -qx 'CONFIG_KEXEC=y' "$output_dir/.config"
if [ "$kexec_file" = 1 ]; then
	grep -qx 'CONFIG_KEXEC_FILE=y' "$output_dir/.config"
	grep -qx '# CONFIG_KEXEC_SIG is not set' "$output_dir/.config"
else
	grep -qx '# CONFIG_KEXEC_FILE is not set' "$output_dir/.config"
fi
grep -Fqx "CONFIG_INITRAMFS_SOURCE=\"$initramfs_source\"" "$output_dir/.config"
make -C "$source_dir" O="$output_dir" -j "$jobs" Image

image=$output_dir/arch/arm64/boot/Image
[ -s "$image" ] || { echo 'FAIL missing kexec-stage Image' >&2; exit 1; }
strings "$image" | grep -q "$release_pattern"
{
	printf 'source_sha256=%s\n' "$(sed -n 's/^source_sha256=//p' "$source_dir/.rog5-kexec-source")"
	printf 'reference_config_profile=%s\n' "$reference_config_profile"
	printf 'kexec_file=%s\n' "$kexec_file"
	printf 'initramfs_sha256=%s\n' "${initramfs_sha256:-none}"
	printf 'compiler=%s\n' "$(clang --version | head -n 1)"
	printf 'config_sha256=%s\n' "$(sha256sum "$output_dir/.config" | cut -d ' ' -f 1)"
	printf 'image_sha256=%s\n' "$(sha256sum "$image" | cut -d ' ' -f 1)"
} > "$output_dir/build-meta.txt"
cat "$output_dir/build-meta.txt"
echo "PASS vendor-compatible 5.4.210 kexec-stage successor Image; reference_config_profile=$reference_config_profile; kexec_file=$kexec_file; builtin_initramfs=$([ -n "$initramfs_source" ] && echo yes || echo no); compile-only"
