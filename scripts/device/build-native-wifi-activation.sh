#!/bin/sh
# Module-only: retain the exact kernel/config/ABI and base Wi-Fi module kit.
set -eu
[ "$#" = 3 ] || { echo 'usage: build-native-wifi-activation.sh SOURCE KIT NEW_OUTPUT' >&2; exit 1; }
source_dir=$(realpath "$1")
kit=$(realpath "$2")
output=$3
repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)
export GIT_OPTIONAL_LOCKS=0
[ "$(git -C "$source_dir" rev-parse HEAD)" = "$(sed -n 's/^patched_commit=//p' "$kit/build-meta.txt")" ]
[ -z "$(git -C "$source_dir" status --porcelain)" ]
[ "$(sha256sum "$kit/.config" | cut -d ' ' -f1)" = "$(awk '$2 == "/.config" {print $1}' "$kit/build-meta.txt")" ]
[ -x "$kit/tools/bpf/resolve_btfids/resolve_btfids" ]
before=$(sha256sum "$kit/.config" "$kit/vmlinux" "$kit/Module.symvers")
mkdir "$output"
output=$(realpath "$output")
cp "$repo/tools/s12_ufs_vote/rog5-s12-ufs-vote.c" "$repo/tools/wifi_activate/rog5-wifi-activate.c" "$output/"
for directory in drivers/pci/pwrctrl drivers/power/sequencing; do mkdir -p "$output/$directory"; done
cp "$source_dir/drivers/pci/pwrctrl/pci-pwrctrl-pwrseq.c" "$output/drivers/pci/pwrctrl/"
cp "$source_dir/drivers/power/sequencing/pwrseq-qcom-wcn.c" "$output/drivers/power/sequencing/"
for patch_name in pwrseq-qcom-wcn-serial-observation pci-pwrctrl-pwrseq-observation; do
	patch --batch --fuzz=0 -p1 -d "$output" -i "$repo/patches/linux/diagnostic/$patch_name.patch"
done
printf 'obj-m += rog5-s12-ufs-vote.o rog5-wifi-activate.o drivers/pci/pwrctrl/ drivers/power/sequencing/\n' >"$output/Makefile"
printf 'obj-m += pci-pwrctrl-pwrseq.o\n' >"$output/drivers/pci/pwrctrl/Makefile"
printf 'obj-m += pwrseq-qcom-wcn.o\n' >"$output/drivers/power/sequencing/Makefile"
export KBUILD_BUILD_USER=rog5-linux KBUILD_BUILD_HOST=rog5-builder KBUILD_BUILD_VERSION=1
KBUILD_BUILD_TIMESTAMP=$(git -C "$source_dir" show -s --format=%cD "$(sed -n 's/^base_commit=//p' "$kit/build-meta.txt")")
export KBUILD_BUILD_TIMESTAMP
export KCFLAGS="-fdebug-prefix-map=$source_dir=/usr/src/rog5-linux -fdebug-prefix-map=$output=/usr/src/rog5-wifi-activation -fdebug-compilation-dir=/usr/src/rog5-linux-build"
export KAFLAGS=$KCFLAGS
make -C "$source_dir" O="$kit" M="$output" ARCH=arm64 LLVM=1 -j2 JOBS=1 modules
[ "$(sha256sum "$kit/.config" "$kit/vmlinux" "$kit/Module.symvers")" = "$before" ]
[ -z "$(git -C "$source_dir" status --porcelain)" ]
find "$output" -type f -name '*.ko' | sort | while IFS= read -r module; do
	[ "$(modinfo -F vermagic "$module" | awk '{print $1}')" = "$(cat "$kit/include/config/kernel.release")" ]
	readelf -h "$module" | grep -q 'Machine:.*AArch64'
	readelf -SW "$module" | grep -q '[.]BTF[[:space:]]'
	sha256sum "$module"
done
echo 'PASS fixed Wi-Fi activation modules; kernel and kit unchanged'
