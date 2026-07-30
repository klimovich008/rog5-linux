#!/bin/sh
set -eu

source_dir=${SOURCE_DIR:-/root/src/msm-5.4}
output_dir=${OUTPUT_DIR:-/root/build/asus-kexec-stage-slim}
reference_config=${REFERENCE_CONFIG:?missing experimental slim REFERENCE_CONFIG}
baseline_config=${BASELINE_CONFIG:?missing accepted BASELINE_CONFIG}
initramfs_source=${INITRAMFS_SOURCE:?missing stable-recovery initramfs}
initramfs_sha256=${INITRAMFS_SHA256:?missing stable-recovery initramfs SHA-256}
jobs=${JOBS:-1}
repo=${REPOSITORY_ROOT:-/workspace}
profile=$repo/configs/kernel/rog5-stable-wrapper-slim-v1.json
auditor=$repo/scripts/host/verify-stable-wrapper-slim-config.py
seal_tool=$repo/scripts/host/kernel-source-seal.py
expected_config=bee39a247b4eef5f5282bad7e09b75853b851ed8b9161981803a08d53b4ac8fb
expected_baseline=df28224e6e8d2dfc825ac49dc9f6bdeb12bbcdae2dff92cbbf14a8a94177578f
expected_profile=3fb9eaf91f32cf01c09cc8653feb4a52c421f4a95bdd8e022576211ad7cff9f0
expected_auditor=6d988b18c3ae70f5bd91be8e6051119911886be0b4eaeb3759eddf3f5a8ac744
expected_seal_tool=b5ed3261a858680b05a3a7247e2d7948e722f71be812fcdc66972594d22c097a
expected_source_tree=592aefb37589f9f9483b43677e29702ed927fc56a251616e33e81f2645e9c35a
localversion=-qgki-perf-kexec-stage-builtin-recovery-slim-v1

case $jobs in
	''|*[!0-9]*|0) echo 'FAIL JOBS must be a positive integer' >&2; exit 1 ;;
esac
for input in "$reference_config" "$baseline_config" "$initramfs_source" \
	"$profile" "$auditor" "$seal_tool"; do
	[ -f "$input" ] && [ ! -L "$input" ] ||
		{ echo "FAIL missing regular nonsymlink input: $input" >&2; exit 1; }
done
for pair in \
	"$reference_config:$expected_config" \
	"$baseline_config:$expected_baseline" \
	"$profile:$expected_profile" \
	"$auditor:$expected_auditor" \
	"$seal_tool:$expected_seal_tool"
do
	input=${pair%:*}
	expected=${pair##*:}
	[ "$(sha256sum "$input" | cut -d ' ' -f 1)" = "$expected" ] ||
		{ echo "FAIL slim-wrapper input hash changed: $input" >&2; exit 1; }
done
[ "${#initramfs_sha256}" -eq 64 ] ||
	{ echo 'FAIL malformed initramfs hash' >&2; exit 1; }
case $initramfs_sha256 in
	*[!0-9a-f]*) echo 'FAIL malformed initramfs hash' >&2; exit 1 ;;
esac
[ "$(sha256sum "$initramfs_source" | cut -d ' ' -f 1)" = \
	"$initramfs_sha256" ] ||
	{ echo 'FAIL stable-recovery initramfs hash changed' >&2; exit 1; }
[ -r "$source_dir/.rog5-kexec-source" ] ||
	{ echo 'FAIL unverified source tree' >&2; exit 1; }
source_seal=$(mktemp)
trap 'rm -f "$source_seal"' EXIT HUP INT TERM
python3 "$seal_tool" "$source_dir" >"$source_seal"
grep -qx 'tree_format=rog5-kernel-source-tree-v1' "$source_seal"
grep -qx "tree_sha256=$expected_source_tree" "$source_seal"
python3 "$auditor" \
	--profile "$profile" \
	--baseline "$baseline_config" \
	--candidate "$reference_config" >/dev/null

[ ! -d "$output_dir" ] ||
	[ -z "$(find "$output_dir" -mindepth 1 -maxdepth 1 -print -quit)" ] ||
	{ echo 'FAIL refusing nonempty slim-wrapper output' >&2; exit 1; }
mkdir -p "$output_dir"
staged_initramfs=/root/build/rog5-kexec-stage-initramfs.cpio.gz
if [ "$initramfs_source" != "$staged_initramfs" ]; then
	install -m 0644 "$initramfs_source" "$staged_initramfs"
fi
staged_initramfs_sha256=$(sha256sum "$staged_initramfs" | cut -d ' ' -f 1)
[ "$staged_initramfs_sha256" = "$initramfs_sha256" ] ||
	{ echo 'FAIL staged stable-recovery initramfs hash changed' >&2; exit 1; }
install -m 0644 "$reference_config" "$output_dir/.config"

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
[ "$(sha256sum "$output_dir/.config" | cut -d ' ' -f 1)" = \
	"$expected_config" ] ||
	{ echo 'FAIL slim wrapper config changed after olddefconfig' >&2; exit 1; }
grep -Fqx "CONFIG_LOCALVERSION=\"$localversion\"" "$output_dir/.config"
grep -Fqx \
	'CONFIG_INITRAMFS_SOURCE="/root/build/rog5-kexec-stage-initramfs.cpio.gz"' \
	"$output_dir/.config"
grep -qx 'CONFIG_KEXEC=y' "$output_dir/.config"
grep -qx '# CONFIG_KEXEC_FILE is not set' "$output_dir/.config"
grep -qx 'CONFIG_USB_DWC3_GADGET=y' "$output_dir/.config"
grep -qx '# CONFIG_MODULES is not set' "$output_dir/.config"

make -C "$source_dir" O="$output_dir" -j "$jobs" Image
image=$output_dir/arch/arm64/boot/Image
[ -s "$image" ] || { echo 'FAIL missing slim-wrapper Image' >&2; exit 1; }
strings "$image" |
	grep -Fq "Linux version 5.4.210$localversion ("
{
	printf 'format=rog5-stable-wrapper-slim-build-v1\n'
	printf 'status=experiment\n'
	printf 'authority=none\n'
	printf 'source_sha256=%s\n' \
		"$(sed -n 's/^source_sha256=//p' "$source_dir/.rog5-kexec-source")"
	printf 'source_tree_sha256=%s\n' "$expected_source_tree"
	printf 'profile_sha256=%s\n' "$expected_profile"
	printf 'baseline_config_sha256=%s\n' "$expected_baseline"
	printf 'candidate_config_sha256=%s\n' "$expected_config"
	printf 'initramfs_sha256=%s\n' "$staged_initramfs_sha256"
	printf 'compiler=%s\n' "$(clang --version | head -n 1)"
	sha256sum "$output_dir/.config" "$image"
} >"$output_dir/build-meta.txt"
cat "$output_dir/build-meta.txt"
echo 'PASS experimental slim ASUS 5.4 stable-recovery wrapper Image; compile-only and not boot-authorized'
