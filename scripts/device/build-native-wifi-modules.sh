#!/bin/sh
set -eu

source_dir=${1:?usage: build-native-wifi-modules.sh SOURCE MATCHING_KERNEL_KIT OUTPUT}
kernel_kit=${2:?missing matching kernel build kit}
output=${3:?missing new output directory}
repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)
module_roots=$repo/configs/kernel/rog5-native-wifi-module-roots
[ -f "$module_roots" ] && [ ! -L "$module_roots" ]
jobs=${JOBS:-4}
case $jobs in 1|2|3|4|5|6|7|8) ;; *) echo 'FAIL unsafe JOBS' >&2; exit 1 ;; esac
source_dir=$(realpath "$source_dir")
kernel_kit=$(realpath "$kernel_kit")
expected_commit=$(sed -n 's/^patched_commit=//p' "$kernel_kit/build-meta.txt")
expected_config=$(awk '$2 == "/.config" { print $1 }' "$kernel_kit/build-meta.txt")
[ -x "$kernel_kit/tools/bpf/resolve_btfids/resolve_btfids" ] || {
	echo 'FAIL kernel module kit lacks resolve_btfids; refusing compilation' >&2
	exit 1
}
[ "$(git -C "$source_dir" rev-parse HEAD)" = "$expected_commit" ]
[ -z "$(git -C "$source_dir" status --porcelain)" ]
[ "$(sha256sum "$kernel_kit/.config" | cut -d ' ' -f 1)" = "$expected_config" ]
release=$(cat "$kernel_kit/include/config/kernel.release")
for symbol in PCI GENERIC_PHY PCI_PWRCTRL POWER_SEQUENCING QCOM_QMI_HELPERS; do
	grep -qx "CONFIG_$symbol=y" "$kernel_kit/.config"
done
for symbol in ATH11K ATH11K_PCI CFG80211 MAC80211 RFKILL MHI_BUS QRTR_MHI CRYPTO_SHA256 \
	CRYPTO_AES CRYPTO_CTR CRYPTO_CCM CRYPTO_GCM CRYPTO_LIB_GF128HASH \
	PCI_PWRCTRL_PWRSEQ POWER_SEQUENCING_QCOM_WCN; do
	grep -qx "CONFIG_$symbol=m" "$kernel_kit/.config"
done
# New output creation is the exclusive writer lock. Never edit the sealed kit.
mkdir "$output"
output=$(realpath "$output")
work=$output/source
mkdir "$work"
before=$(sha256sum "$kernel_kit/.config" "$kernel_kit/vmlinux")
for directory in drivers/bus/mhi/host drivers/net/wireless/ath/ath11k \
	net/rfkill net/wireless net/mac80211; do
	mkdir -p "$work/$directory"
	cp -a "$source_dir/$directory/." "$work/$directory/"
done
cp "$source_dir/drivers/bus/mhi/common.h" "$work/drivers/bus/mhi/"
cp "$source_dir"/drivers/net/wireless/ath/*.[ch] "$work/drivers/net/wireless/ath/"
for directory in drivers/phy/qualcomm drivers/pci/pwrctrl \
	drivers/power/sequencing crypto lib/crypto net/qrtr; do
	mkdir -p "$work/$directory"
done
cp "$source_dir"/drivers/phy/qualcomm/phy-qcom-qmp*.h "$work/drivers/phy/qualcomm/"
cp "$source_dir/drivers/phy/qualcomm/phy-qcom-qmp-pcie.c" "$work/drivers/phy/qualcomm/"
cp "$source_dir/drivers/pci/pwrctrl/pci-pwrctrl-pwrseq.c" "$work/drivers/pci/pwrctrl/"
cp "$source_dir/drivers/power/sequencing/pwrseq-qcom-wcn.c" "$work/drivers/power/sequencing/"
cp "$source_dir/lib/crypto/arc4.c" "$work/lib/crypto/"
cp "$source_dir/lib/crypto/gf128hash.c" "$work/lib/crypto/"
mkdir "$work/lib/crypto/arm64"
for name in gf128hash.h ghash-neon-core.S polyval-ce-core.S; do
	cp "$source_dir/lib/crypto/arm64/$name" "$work/lib/crypto/arm64/"
done
cp "$source_dir/crypto/cmac.c" "$work/crypto/"
cp "$source_dir/crypto/sha256.c" "$work/crypto/"
for algorithm in aes ctr ccm gcm; do
	cp "$source_dir/crypto/$algorithm.c" "$work/crypto/"
done
cp "$source_dir/net/qrtr/mhi.c" "$work/net/qrtr/"
cp "$source_dir/net/qrtr/qrtr.h" "$work/net/qrtr/"

# QMP PCIe is a self-contained upstream module: its CONFIG symbol is used only
# by Kbuild, not by any C/header consumer. Select that object externally without
# changing the running kernel configuration, headers, Image or built-in ABI.
printf 'obj-m += phy-qcom-qmp-pcie.o\n' >"$work/drivers/phy/qualcomm/Makefile"
printf 'obj-m += pci-pwrctrl-pwrseq.o\n' >"$work/drivers/pci/pwrctrl/Makefile"
printf 'obj-m += pwrseq-qcom-wcn.o\n' >"$work/drivers/power/sequencing/Makefile"
printf '%s\n' 'obj-m += libarc4.o libgf128hash.o' 'libarc4-y := arc4.o' \
	'libgf128hash-y := gf128hash.o arm64/ghash-neon-core.o arm64/polyval-ce-core.o' \
	'CFLAGS_gf128hash.o += -I$(src)/$(SRCARCH)' >"$work/lib/crypto/Makefile"
printf 'obj-m += cmac.o sha256.o aes.o ctr.o ccm.o gcm.o\n' >"$work/crypto/Makefile"
printf 'obj-m += qrtr-mhi.o\nqrtr-mhi-y := mhi.o\n' >"$work/net/qrtr/Makefile"
{
	printf 'obj-m += ath.o ath11k/\n'
	sed -n '/^ath-objs/,$p' "$source_dir/drivers/net/wireless/ath/Makefile"
} >"$work/drivers/net/wireless/ath/Makefile"
printf '%s\n' 'obj-m += drivers/phy/qualcomm/ drivers/pci/pwrctrl/ drivers/power/sequencing/ drivers/bus/mhi/host/ drivers/net/wireless/ath/ net/rfkill/ net/wireless/ net/mac80211/ net/qrtr/ crypto/ lib/crypto/' >"$work/Makefile"

export KBUILD_BUILD_USER=rog5-linux KBUILD_BUILD_HOST=rog5-builder KBUILD_BUILD_VERSION=1
KBUILD_BUILD_TIMESTAMP=$(git -C "$source_dir" show -s --format=%cD \
	"$(sed -n 's/^base_commit=//p' "$kernel_kit/build-meta.txt")")
export KBUILD_BUILD_TIMESTAMP
export KCFLAGS="-fdebug-prefix-map=$source_dir=/usr/src/rog5-linux -fdebug-prefix-map=$work=/usr/src/rog5-linux -fdebug-compilation-dir=/usr/src/rog5-linux-build"
export KAFLAGS=$KCFLAGS
make -C "$source_dir" O="$kernel_kit" M="$work" ARCH=arm64 LLVM=1 \
	-j "$jobs" JOBS=1 modules
[ "$(sha256sum "$kernel_kit/.config" "$kernel_kit/vmlinux")" = "$before" ]

root=$output/module-root
mkdir "$root"
cp -a "$kernel_kit/power-usb-modules/lib" "$root/"
find "$work" -type f -name '*.ko' | sort | while IFS= read -r module; do
	[ "$(modinfo -F vermagic "$module" | awk '{print $1}')" = "$release" ]
	readelf -SW "$module" | grep -q '[.]BTF[[:space:]]'
	install -D -m 0644 "$module" "$root/lib/modules/$release/kernel/${module#"$work/"}"
done
for metadata in modules.builtin modules.builtin.modinfo; do
	cp "$kernel_kit/$metadata" "$root/lib/modules/$release/"
done
(cd "$root/lib/modules/$release" && find kernel -type f -name '*.ko' | sort) \
	>"$root/lib/modules/$release/modules.order"
depmod -b "$root" "$release"
cp "$module_roots" "$output/load-roots.txt"
: >"$output/load-closure.tmp"
while IFS= read -r module; do
	case $module in ''|*[!A-Za-z0-9_-]*) echo 'FAIL invalid module root' >&2; exit 1 ;; esac
	modprobe -d "$root" -S "$release" --show-depends "$module" >>"$output/load-closure.tmp" || exit 1
done <"$module_roots"
sort -u "$output/load-closure.tmp" >"$output/load-closure.txt"
rm "$output/load-closure.tmp"
find "$root" -type f -print0 | sort -z | xargs -0 sha256sum >"$output/module-sha256.txt"
printf 'PASS matching native Wi-Fi modules; kernel config and vmlinux unchanged\n'
