#!/bin/sh
set -eu

repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)
fragment=$repo/configs/kernel/rog5-wifi.fragment
builder=$repo/scripts/device/build-mainline-wifi.sh
verifier=$repo/scripts/device/verify-mainline-wifi-build.sh
comparer=$repo/scripts/device/compare-mainline-wifi-builds.sh

[ -r "$fragment" ] || {
	echo 'FAIL missing Wi-Fi kernel fragment' >&2
	exit 1
}
for script in "$builder" "$verifier" "$comparer"; do
	[ -x "$script" ] || {
		echo "FAIL missing executable Wi-Fi kernel tool: $script" >&2
		exit 1
	}
	sh -n "$script"
done

for symbol in \
	CONFIG_PHY_QCOM_QMP_PCIE=m \
	CONFIG_PCIE_QCOM=y \
	CONFIG_PCI_PWRCTRL=y \
	CONFIG_PCI_PWRCTRL_PWRSEQ=m \
	CONFIG_POWER_SEQUENCING=y \
	CONFIG_POWER_SEQUENCING_QCOM_WCN=m \
	CONFIG_MHI_BUS=m \
	CONFIG_MHI_BUS_PCI_GENERIC=m \
	CONFIG_ATH11K=m \
	CONFIG_ATH11K_PCI=m
do
	grep -Fqx "$symbol" "$fragment" || {
		echo "FAIL Wi-Fi kernel fragment omits: $symbol" >&2
		exit 1
	}
done

for contract in \
	'7a5cef0db4795d9d453a12e0f61b5b7634fc4d40' \
	'rog5-mainline.fragment' \
	'rog5-network-root.fragment' \
	'rog5-wifi.fragment' \
	'merge_config.sh' \
	'Image.gz modules' \
	'modules.tar.gz' \
	'wifi_fragment_sha256'
do
	grep -Fq "$contract" "$builder" || {
		echo "FAIL Wi-Fi kernel builder omits: $contract" >&2
		exit 1
	}
done

for contract in \
	'verify-mainline-network-root-build.sh' \
	'CONFIG_PHY_QCOM_QMP_PCIE=m' \
	'CONFIG_PCI_PWRCTRL_PWRSEQ=m' \
	'CONFIG_POWER_SEQUENCING_QCOM_WCN=m' \
	'CONFIG_MHI_BUS_PCI_GENERIC=m' \
	'CONFIG_ATH11K_PCI=m' \
	'drivers/phy/qualcomm/phy-qcom-qmp-pcie.ko' \
	'drivers/pci/pwrctrl/pci-pwrctrl-pwrseq.ko' \
	'drivers/power/sequencing/pwrseq-qcom-wcn.ko' \
	'drivers/bus/mhi/host/mhi.ko' \
	'drivers/bus/mhi/host/mhi_pci_generic.ko' \
	'drivers/net/wireless/ath/ath11k/ath11k.ko' \
	'drivers/net/wireless/ath/ath11k/ath11k_pci.ko' \
	'pci:v000017CBd00001103' \
	'of:N*T*Cqcom,wcn6855-pmu' \
	'modules.tar.gz'
do
	grep -Fq "$contract" "$verifier" || {
		echo "FAIL Wi-Fi kernel verifier omits: $contract" >&2
		exit 1
	}
done

for artifact in \
	.config \
	arch/arm64/boot/Image \
	arch/arm64/boot/Image.gz \
	modules.tar.gz \
	build-meta.txt
do
	grep -Fq "$artifact" "$comparer" || {
		echo "FAIL Wi-Fi kernel comparer omits: $artifact" >&2
		exit 1
	}
done

if grep -Eq '^[[:space:]]*(fastboot|adb|ssh|mount|dd)([[:space:]]|$)' \
	"$builder" "$verifier" "$comparer"
then
	echo 'FAIL Wi-Fi kernel build path controls the phone or external storage' >&2
	exit 1
fi

if [ -n "${BUILD_A:-}" ] || [ -n "${BUILD_B:-}" ]; then
	[ -n "${BUILD_A:-}" ] && [ -n "${BUILD_B:-}" ]
	"$verifier" "$BUILD_A"
	"$verifier" "$BUILD_B"
	"$comparer" "$BUILD_A" "$BUILD_B"
fi

echo 'PASS Wi-Fi kernel build is source-pinned, storage-disabled, module-complete, and reproducible'
