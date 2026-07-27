#!/bin/sh
set -eu

repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)
builder=$repo/scripts/device/build-wifi-root-overlay.sh
verifier=$repo/scripts/device/verify-wifi-root-overlay.sh
probe=$repo/scripts/device/probe-network-root-wifi.sh
blacklist=$repo/packaging/arch/20-rog5-wifi-probe-blacklist.conf
unmanaged=$repo/packaging/arch/20-rog5-wifi-unmanaged.conf

for file in "$builder" "$verifier" "$probe" "$blacklist" "$unmanaged"; do
	[ -f "$file" ] && [ ! -L "$file" ] || {
		echo "FAIL missing Wi-Fi root-overlay input: $file" >&2
		exit 1
	}
done
for script in "$builder" "$verifier" "$probe"; do
	[ -x "$script" ] || {
		echo "FAIL Wi-Fi root-overlay script is not executable: $script" >&2
		exit 1
	}
	sh -n "$script"
done

for module in \
	phy_qcom_qmp_pcie \
	pwrseq_qcom_wcn \
	pci_pwrctrl_pwrseq \
	mhi \
	mhi_pci_generic \
	ath11k \
	ath11k_pci
do
	grep -Fqx "blacklist $module" "$blacklist" || {
		echo "FAIL Wi-Fi automatic-probe blacklist omits: $module" >&2
		exit 1
	}
done
[ "$(awk 'NF { count++ } END { print count + 0 }' "$blacklist")" -eq 7 ]
grep -Fqx '[keyfile]' "$unmanaged"
grep -Fqx 'unmanaged-devices=interface-name:wlan0' "$unmanaged"

for contract in \
	a7c286491d2fde97e17024b36f514d595196975da1988c986f70819c964eb8d7 \
	5be71d86eafbb43086b901897d812ef3efa6c806a80101fc3194749866cb4fa9 \
	e7a2eed91e20742012cc0a1fb893545fc61870ec94ca0ca4add3ee6c41e5300d \
	7.1.4-g7a5cef0db479 \
	'phy-qcom-qmp-pcie.ko' \
	'comm -23' \
	'usr/lib/modules' \
	'20-rog5-wifi-probe-blacklist.conf' \
	'20-rog5-wifi-unmanaged.conf' \
	'probe-network-root-wifi.sh' \
	'--sort=name' \
	'gzip -n'
do
	grep -Fq -- "$contract" "$builder" || {
		echo "FAIL Wi-Fi root-overlay builder omits: $contract" >&2
		exit 1
	}
done

for contract in \
	'verify-wifi-root-overlay.sh' \
	'usr/lib/modules/7.1.4-g7a5cef0db479' \
	'etc/modprobe.d/20-rog5-wifi-probe-blacklist.conf' \
	'etc/NetworkManager/conf.d/20-rog5-wifi-unmanaged.conf' \
	'usr/local/sbin/rog5-wifi-enumeration-probe' \
	'usr/lib/firmware/ath11k/WCN6855/hw2.0/amss.bin' \
	'usr/lib/firmware/ath11k/WCN6855/hw2.0/board-2.bin' \
	'usr/lib/firmware/ath11k/WCN6855/hw2.0/m3.bin' \
	'usr/lib/firmware/ath11k/WCN6855/hw2.0/regdb.bin' \
	e12b23ddc4b8d2d2a10a651a5d6fdcd00f60fcae884d2cf5dad17627211fcdfd \
	9287fa8d14d915892666b03e9403135875d08371fd1438d2c6d9fe96ae71cf68 \
	0c590881870d0e6e98fc7d393ce05690e09287933b1b535e935bf5d98b77713f \
	e1b774b1feda4cab01f5a26089124059539fc31544ac34129dce45c8ff26d645 \
	'BEGIN .*PRIVATE KEY' \
	'NetworkManager/system-connections' \
	'wireguard/wg0.conf'
do
	grep -Fq -- "$contract" "$verifier" || {
		echo "FAIL Wi-Fi root-overlay verifier omits: $contract" >&2
		exit 1
	}
done

if grep -Eq \
	'(^|[;&|[:space:]])(fastboot|adb|ssh|scp|nmcli|hostapd|wpa_supplicant)([[:space:]]|$)|dd[[:space:]].*of=/dev/|mount[[:space:]].*/dev/' \
	"$builder" "$verifier"
then
	echo 'FAIL Wi-Fi root-overlay path controls the phone, radio, or storage' >&2
	exit 1
fi

if [ -n "${BASE_ROOTFS:-}" ] || [ -n "${OLD_MODULES:-}" ] ||
	[ -n "${WIFI_MODULES:-}" ]
then
	[ -s "${BASE_ROOTFS:-}" ]
	[ -s "${OLD_MODULES:-}" ]
	[ -s "${WIFI_MODULES:-}" ]
	stage=$(mktemp -d)
	trap 'rm -rf "$stage"' EXIT INT TERM
	"$builder" "$BASE_ROOTFS" "$OLD_MODULES" "$WIFI_MODULES" \
		"$stage/one.tar.gz" >/dev/null
	"$builder" "$BASE_ROOTFS" "$OLD_MODULES" "$WIFI_MODULES" \
		"$stage/two.tar.gz" >/dev/null
	cmp "$stage/one.tar.gz" "$stage/two.tar.gz"
	"$verifier" "$BASE_ROOTFS" "$WIFI_MODULES" "$stage/one.tar.gz"

	reject_mutation() {
		label=$1
		mutant_root=$stage/mutations/$label
		mutant_archive=$stage/mutations/$label.tar.gz
		install -d "$mutant_root"
		tar -xzf "$stage/one.tar.gz" -C "$mutant_root"
		case $label in
		module-byte)
			printf '\000' >>"$mutant_root/usr/lib/modules/7.1.4-g7a5cef0db479/kernel/drivers/phy/qualcomm/phy-qcom-qmp-pcie.ko"
			;;
		seal-byte)
			chmod 0644 "$mutant_root/etc/rog5/wifi-enumeration-v1"
			printf 'mutation=1\n' >>"$mutant_root/etc/rog5/wifi-enumeration-v1"
			chmod 0444 "$mutant_root/etc/rog5/wifi-enumeration-v1"
			;;
		probe-mode)
			chmod 0644 \
				"$mutant_root/usr/local/sbin/rog5-wifi-enumeration-probe"
			;;
		credential-path)
			install -d \
				"$mutant_root/etc/NetworkManager/system-connections"
			printf '[connection]\nid=forbidden\n' \
				>"$mutant_root/etc/NetworkManager/system-connections/forbidden.nmconnection"
			;;
		esac
		tar --sort=name --mtime='@1681862400' --owner=0 --group=0 \
			--numeric-owner -C "$mutant_root" -cf - . |
			gzip -n >"$mutant_archive"
		if "$verifier" "$BASE_ROOTFS" "$WIFI_MODULES" \
			"$mutant_archive" \
			>"$stage/mutations/$label.log" 2>&1
		then
			echo "FAIL Wi-Fi root-overlay verifier accepts mutation: $label" >&2
			exit 1
		fi
	}
	install -d "$stage/mutations"
	reject_mutation module-byte
	reject_mutation seal-byte
	reject_mutation probe-mode
	reject_mutation credential-path
fi

echo 'PASS Wi-Fi root overlay is predecessor-pinned, deterministic, module-complete, auto-probe-locked, credential-clean, mutation-tested, and offline-only'
