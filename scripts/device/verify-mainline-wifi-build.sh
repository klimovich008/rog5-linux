#!/bin/sh
set -eu

output_dir=${1:?usage: verify-mainline-wifi-build.sh BUILD_DIR}
repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)
network_verifier=$repo/scripts/device/verify-mainline-network-root-build.sh
meta=$output_dir/build-meta.txt
config=$output_dir/.config
archive=$output_dir/modules.tar.gz

[ -x "$network_verifier" ]
ALLOW_QMP_PCIE=m "$network_verifier" "$output_dir" >/dev/null
for file in "$meta" "$config" "$archive"; do
	[ -s "$file" ] || {
		echo "FAIL missing Wi-Fi build artifact: $file" >&2
		exit 1
	}
done

wifi_hash=$(sha256sum "$repo/configs/kernel/rog5-wifi.fragment" |
	cut -d ' ' -f 1)
[ "$(sed -n 's/^wifi_fragment_sha256=//p' "$meta")" = "$wifi_hash" ]

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
	grep -qx "$symbol" "$config" || {
		echo "FAIL final Wi-Fi config omits: $symbol" >&2
		exit 1
	}
done

stage=$(mktemp -d)
trap 'rm -rf "$stage"' EXIT INT TERM
tar -xzf "$archive" -C "$stage"
modules_root=$(find "$stage/lib/modules" -mindepth 1 -maxdepth 1 \
	-type d -print -quit)
[ -n "$modules_root" ]

module_path() {
	suffix=$1
	path=$(find "$modules_root/kernel" -type f -path "*/$suffix" -print)
	[ "$(printf '%s\n' "$path" | awk 'NF { count++ } END { print count + 0 }')" -eq 1 ]
	printf '%s\n' "$path"
}

qmp=$(module_path drivers/phy/qualcomm/phy-qcom-qmp-pcie.ko)
pwrctrl=$(module_path drivers/pci/pwrctrl/pci-pwrctrl-pwrseq.ko)
pwrseq=$(module_path drivers/power/sequencing/pwrseq-qcom-wcn.ko)
mhi=$(module_path drivers/bus/mhi/host/mhi.ko)
mhi_pci=$(module_path drivers/bus/mhi/host/mhi_pci_generic.ko)
ath11k=$(module_path drivers/net/wireless/ath/ath11k/ath11k.ko)
ath11k_pci=$(module_path drivers/net/wireless/ath/ath11k/ath11k_pci.ko)

[ "$(modinfo -F name "$qmp")" = phy_qcom_qmp_pcie ]
[ "$(modinfo -F name "$pwrctrl")" = pci_pwrctrl_pwrseq ]
[ "$(modinfo -F name "$pwrseq")" = pwrseq_qcom_wcn ]
[ "$(modinfo -F name "$mhi")" = mhi ]
[ "$(modinfo -F name "$mhi_pci")" = mhi_pci_generic ]
[ "$(modinfo -F name "$ath11k")" = ath11k ]
[ "$(modinfo -F name "$ath11k_pci")" = ath11k_pci ]

require_alias() {
	aliases=$(modinfo -F alias "$1")
	printf '%s\n' "$aliases" | grep -F "$2" >/dev/null || {
		echo "FAIL module alias missing from $1: $2" >&2
		exit 1
	}
}

require_alias "$pwrctrl" 'of:N*T*Cpci17cb,1103'
require_alias "$pwrseq" 'of:N*T*Cqcom,wcn6855-pmu'
require_alias "$ath11k_pci" 'pci:v000017CBd00001103'
for module in "$qmp" "$pwrctrl" "$pwrseq" "$mhi" "$mhi_pci" \
	"$ath11k" "$ath11k_pci"
do
	modinfo -F vermagic "$module" | grep -Eq '^7[.]1[.]4-g7a5cef0db479 '
done

for dependency in \
	phy-qcom-qmp-pcie.ko \
	pci-pwrctrl-pwrseq.ko \
	pwrseq-qcom-wcn.ko \
	mhi.ko \
	mhi_pci_generic.ko \
	ath11k.ko \
	ath11k_pci.ko
do
	grep -Fq "$dependency:" "$modules_root/modules.dep"
done

echo 'PASS Wi-Fi config, QMP PCIe PHY, WCN6855 power sequence, MHI, and ath11k module/alias contract'
