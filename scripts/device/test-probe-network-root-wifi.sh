#!/bin/sh
set -eu

repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)
probe=$repo/scripts/device/probe-network-root-wifi.sh

[ -x "$probe" ] || {
	echo 'FAIL missing executable Wi-Fi enumeration probe' >&2
	exit 1
}
sh -n "$probe"

for contract in \
	'ALLOW_MAINLINE_WCN6855_ENUMERATION_PROBE' \
	'7.1.4-g7a5cef0db479' \
	'169.254.77.1:/' \
	'findmnt -n -o FSTYPE /' \
	'/sys/class/block' \
	'/run/rog5-network-root-watchdog.pid' \
	'/run/rog5-network-root-watchdog.disarmed.pid' \
	'20-rog5-wifi-probe-blacklist.conf' \
	'20-rog5-wifi-unmanaged.conf' \
	'phy_qcom_qmp_pcie' \
	'pwrseq_qcom_wcn' \
	'pci_pwrctrl_pwrseq' \
	'ath11k_pci' \
	'/sys/bus/pci/devices/0000:01:00.0' \
	'0x17cb' \
	'0x1103' \
	'0x0108' \
	'/sys/class/net/wlan0' \
	'iw dev wlan0 link' \
	'Not connected.' \
	'GENERAL.STATE' \
	'unmanaged' \
	'Kernel panic|Oops:|BUG:|Unable to handle kernel|Synchronous External Abort' \
	'RDDM|firmware crashed|failed to start core' \
	'/sys/class/bluetooth/hci*' \
	'PASS WCN6855 enumeration-only probe'
do
	grep -Fq "$contract" "$probe" || {
		echo "FAIL Wi-Fi enumeration probe omits: $contract" >&2
		exit 1
	}
done

qmp_line=$(grep -n 'modprobe phy_qcom_qmp_pcie' "$probe" | cut -d: -f1)
pwrseq_line=$(grep -n 'modprobe pwrseq_qcom_wcn' "$probe" | cut -d: -f1)
pwrctrl_line=$(grep -n 'modprobe pci_pwrctrl_pwrseq' "$probe" | cut -d: -f1)
ath11k_line=$(grep -n 'modprobe ath11k_pci' "$probe" | cut -d: -f1)
[ "$pwrseq_line" -lt "$pwrctrl_line" ]
[ "$pwrctrl_line" -lt "$qmp_line" ]
[ "$qmp_line" -lt "$ath11k_line" ]

if grep -Eq \
	'(^|[;&|[:space:]])(fastboot|adb|ssh|scp|hostapd|wpa_supplicant)([[:space:]]|$)|nmcli[[:space:]]+connection[[:space:]]+(up|add|modify)|iw[[:space:]].*[[:space:]]scan([[:space:]]|$)|rfkill[[:space:]]+unblock|modprobe[[:space:]]+-r|dd[[:space:]].*of=/dev/|mount[[:space:]].*/dev/' \
	"$probe"
then
	echo 'FAIL Wi-Fi enumeration probe associates, scans, controls transport, unloads modules, or writes storage' >&2
	exit 1
fi

set +e
"$probe" >/dev/null 2>&1
missing_guard=$?
set -e
[ "$missing_guard" -ne 0 ]

echo 'PASS WCN6855 probe is explicit, enumeration-only, storage-free, unmanaged, unassociated, crash-checked, and watchdog-guarded'
