#!/bin/sh
# Rebuild the ABI-coupled ath11k family against a sealed running-kernel kit only.
set -eu
[ "$#" = 4 ] || {
	echo 'usage: build-native-ath11k-modules.sh SOURCE KERNEL_KIT BASE_WIFI_SYMVERS NEW_OUTPUT' >&2
	exit 1
}
source_dir=$(realpath "$1")
kernel_kit=$(realpath "$2")
base_symbols=$(realpath "$3")
output=$4
repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)
patch=$repo/patches/linux/device/ath11k-wcn6851-hw11.patch
jobs=${JOBS:-4}
case $jobs in 1|2|3|4|5|6|7|8) ;; *) echo 'FAIL unsafe JOBS' >&2; exit 1 ;; esac
[ -x "$kernel_kit/tools/bpf/resolve_btfids/resolve_btfids" ] || {
	echo 'FAIL kernel module kit lacks resolve_btfids' >&2
	exit 1
}
[ -s "$base_symbols" ] && [ ! -L "$base_symbols" ]
[ -f "$patch" ] && [ ! -L "$patch" ]
export GIT_OPTIONAL_LOCKS=0
expected_commit=$(sed -n 's/^patched_commit=//p' "$kernel_kit/build-meta.txt")
expected_config=$(awk '$2 == "/.config" {print $1}' "$kernel_kit/build-meta.txt")
[ "$(git -C "$source_dir" rev-parse HEAD)" = "$expected_commit" ]
[ -z "$(git -C "$source_dir" status --porcelain)" ]
[ "$(sha256sum "$kernel_kit/.config" | cut -d ' ' -f1)" = "$expected_config" ]
for symbol in ATH11K ATH11K_PCI CFG80211 MAC80211; do
	grep -qx "CONFIG_$symbol=m" "$kernel_kit/.config"
done
release=$(cat "$kernel_kit/include/config/kernel.release")
before=$(sha256sum "$kernel_kit/.config" "$kernel_kit/vmlinux" "$patch" "$base_symbols")
mkdir "$output" # Exclusive output ownership; never overwrite a prior build.
output=$(realpath "$output")
work=$output/source
ath=$work/drivers/net/wireless/ath
mkdir -p "$ath/ath11k"
cp -a "$source_dir/drivers/net/wireless/ath/ath11k/." "$ath/ath11k/"
cp "$source_dir"/drivers/net/wireless/ath/*.[ch] "$ath/"
{
	printf 'obj-m += ath.o ath11k/\n'
	sed -n '/^ath-objs/,$p' "$source_dir/drivers/net/wireless/ath/Makefile"
} >"$ath/Makefile"
# The source checkout and kernel kit stay unchanged; patch the private copy.
git -C "$work" apply --check "$patch"
git -C "$work" apply "$patch"
python3 "$repo/scripts/device/test-native-ath11k-hw11.py" --selector-source "$ath/ath11k"
# Keep dependencies from the matching Wi-Fi build, excluding exports rebuilt here.
awk '$3 !~ /(^|\/)(ath|ath11k|ath11k_pci|ath11k_ahb)$/ {print}' "$base_symbols" >"$output/dependencies.symvers"
export KBUILD_BUILD_USER=rog5-linux KBUILD_BUILD_HOST=rog5-builder KBUILD_BUILD_VERSION=1
KBUILD_BUILD_TIMESTAMP=$(git -C "$source_dir" show -s --format=%cD \
	"$(sed -n 's/^base_commit=//p' "$kernel_kit/build-meta.txt")")
export KBUILD_BUILD_TIMESTAMP
export KCFLAGS="-fdebug-prefix-map=$source_dir=/usr/src/rog5-linux -fdebug-prefix-map=$work=/usr/src/rog5-linux -fdebug-compilation-dir=/usr/src/rog5-linux-build"
export KAFLAGS=$KCFLAGS
# Kbuild JOBS controls pahole workers, separately from make -j compilation.
# Parallel BTF encoding otherwise changes type ordering between clean twins.
make -C "$source_dir" O="$kernel_kit" M="$ath" ARCH=arm64 LLVM=1 \
	KBUILD_EXTRA_SYMBOLS="$output/dependencies.symvers" -j "$jobs" JOBS=1 modules
[ "$(sha256sum "$kernel_kit/.config" "$kernel_kit/vmlinux" "$patch" "$base_symbols")" = "$before" ]
[ -z "$(git -C "$source_dir" status --porcelain)" ]
# Include AHB when selected: its use of the shared hardware enum changes too.
modules='ath.ko ath11k/ath11k.ko ath11k/ath11k_pci.ko'
if grep -qx CONFIG_ATH11K_AHB=m "$kernel_kit/.config"; then
	modules="$modules ath11k/ath11k_ahb.ko"
fi
for name in $modules; do
	module=$ath/$name
	[ "$(modinfo -F vermagic "$module" | awk '{print $1}')" = "$release" ]
	readelf -h "$module" | grep -q 'Machine:.*AArch64'
	readelf -SW "$module" | grep -q '[.]BTF[[:space:]]'
	sha256sum "$module"
done
printf 'PASS native ath11k family; source, config and vmlinux unchanged\n'
