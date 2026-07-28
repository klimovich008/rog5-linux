#!/bin/sh
set -eu

source_dir=${SOURCE_DIR:-/root/src/msm-5.4}
output_dir=${OUTPUT_DIR:-/root/build/asus-kexec-stage}
accepted_config=${ACCEPTED_CONFIG:?missing accepted UFS wrapper config}
initramfs_source=${INITRAMFS_SOURCE:-/root/build/rog5-kexec-stage-initramfs.cpio.gz}
jobs=${JOBS:-1}
source_sha=3bfe58a00bfdd3839f9b626c2d34f0cc6778945458f1eef93cbfdea90bf2e5a8
marker_sha=54ea162415b31227ae50d98806d59179ac2b1acca53d71be1a3f036f9eb92069
config_sha=df28224e6e8d2dfc825ac49dc9f6bdeb12bbcdae2dff92cbbf14a8a94177578f
initramfs_sha=3360abb8b47cdc5ffd5be59664b979fad186611442bd8224ced225084a4ecc73

[ "$initramfs_source" = /root/build/rog5-kexec-stage-initramfs.cpio.gz ]
[ -r "$source_dir/.rog5-kexec-source" ]
[ "$(sha256sum "$source_dir/.rog5-kexec-source" | cut -d ' ' -f 1)" = \
	"$marker_sha" ]
grep -qx "source_sha256=$source_sha" "$source_dir/.rog5-kexec-source"
[ -f "$accepted_config" ] && [ ! -L "$accepted_config" ]
[ "$(sha256sum "$accepted_config" | cut -d ' ' -f 1)" = "$config_sha" ]
[ -f "$initramfs_source" ] && [ ! -L "$initramfs_source" ]
[ "$(sha256sum "$initramfs_source" | cut -d ' ' -f 1)" = \
	"$initramfs_sha" ]
gzip -t "$initramfs_source"

case $jobs in *[!0-9]*|'') exit 1 ;; esac
[ "$jobs" -ge 1 ] && [ "$jobs" -le 64 ]
[ ! -d "$output_dir" ] ||
	[ -z "$(find "$output_dir" -mindepth 1 -maxdepth 1 \
	-print -quit)" ] || {
	echo 'FAIL refusing nonempty P2 entry wrapper output directory' >&2
	exit 1
}
mkdir -p "$output_dir"
install -m 0644 "$accepted_config" "$output_dir/.config"

for setting in \
	'CONFIG_KEXEC=y' \
	'# CONFIG_KEXEC_FILE is not set' \
	'CONFIG_INITRAMFS_SOURCE="/root/build/rog5-kexec-stage-initramfs.cpio.gz"' \
	'CONFIG_INITRAMFS_COMPRESSION=".gz"' \
	'CONFIG_LOCALVERSION="-qgki-perf-kexec-stage-builtin-recovery"'; do
	grep -Fqx "$setting" "$output_dir/.config"
done

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
[ "$(sha256sum "$output_dir/.config" | cut -d ' ' -f 1)" = "$config_sha" ]
make -C "$source_dir" O="$output_dir" -j "$jobs" Image

image=$output_dir/arch/arm64/boot/Image
[ -s "$image" ] || {
	echo 'FAIL missing ASUS P2 entry kexec-stage Image' >&2
	exit 1
}
strings "$image" |
	grep -q 'Linux version 5.4.210.*-qgki-perf-kexec-stage-builtin-recovery'
python3 - "$image" "$initramfs_source" <<'PY'
import sys

image = open(sys.argv[1], "rb").read()
initramfs = open(sys.argv[2], "rb").read()
if image.count(initramfs) != 1:
    raise SystemExit("embedded P2 entry initramfs count is not one")
PY

{
	printf 'source_sha256=%s\n' "$source_sha"
	printf 'kexec_file=0\n'
	printf 'initramfs_sha256=%s\n' "$initramfs_sha"
	printf 'compiler=%s\n' "$(clang --version | head -n 1)"
	sha256sum "$output_dir/.config" "$image"
} >"$output_dir/build-meta.txt"
cat "$output_dir/build-meta.txt"
echo 'PASS ASUS 5.4.210 wrapper with built-in P2 early-entry stage; compile-only'
