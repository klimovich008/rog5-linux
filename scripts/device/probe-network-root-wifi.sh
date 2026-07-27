#!/bin/sh
set -eu

fail() {
	echo "FAIL $*" >&2
	exit 1
}

[ "${ALLOW_MAINLINE_WCN6855_ENUMERATION_PROBE:-}" = 1 ] ||
	fail 'set ALLOW_MAINLINE_WCN6855_ENUMERATION_PROBE=1 for one attended probe'
[ "$(id -u)" -eq 0 ] || fail 'WCN6855 enumeration probe requires root'

for command in awk cat dmesg find findmnt grep id ip iw mktemp modprobe \
	nmcli readlink sha256sum sleep stat systemctl tail tr uname wc; do
	command -v "$command" >/dev/null || fail "missing command: $command"
done

release=7.1.4-g7a5cef0db479
[ "$(uname -r)" = "$release" ] || fail 'unexpected kernel'
[ "$(cat /proc/1/comm)" = systemd ] || fail 'PID 1 is not systemd'
[ "$(systemctl is-system-running 2>/dev/null || true)" = running ] ||
	fail 'systemd is not running'
[ "$(findmnt -n -o FSTYPE /)" = overlay ] || fail 'root is not OverlayFS'
[ "$(findmnt -n -o SOURCE /.rog5/root-ro)" = 169.254.77.1:/ ] ||
	fail 'unexpected NFS lower source'
findmnt -n -o OPTIONS /.rog5/root-ro | tr ',' '\n' | grep -qx ro ||
	fail 'NFS lower is not read-only'
[ "$(find /sys/class/block -mindepth 1 -maxdepth 1 -type l \
	-exec test -e {}/device \; -print 2>/dev/null | wc -l)" -eq 0 ] ||
	fail 'physical block device is present'
[ "$(findmnt -rn -o SOURCE |
	awk '/^\/dev\// { count++ } END { print count + 0 }')" -eq 0 ] ||
	fail 'block-backed mount is present'
[ "$(cat /sys/class/net/usb0/carrier)" = 1 ] ||
	fail 'USB network carrier is down'
[ "$(ip -4 -o address show dev usb0 |
	awk '$4 == "169.254.77.2/30" { count++ }
		END { print count + 0 }')" -eq 1 ] ||
	fail 'USB network address is not exact'

pid_file=/run/rog5-network-root-watchdog.pid
marker=/run/rog5-network-root-watchdog.disarmed.pid
[ ! -e "$pid_file" ] || fail 'initial network-root watchdog is still active'
[ -s "$marker" ] || fail 'initial network-root watchdog lacks its disarm marker'

blacklist=/etc/modprobe.d/20-rog5-wifi-probe-blacklist.conf
unmanaged=/etc/NetworkManager/conf.d/20-rog5-wifi-unmanaged.conf
[ -f "$blacklist" ] && [ ! -L "$blacklist" ] ||
	fail 'automatic Wi-Fi probe blacklist is absent or linked'
[ -f "$unmanaged" ] && [ ! -L "$unmanaged" ] ||
	fail 'NetworkManager Wi-Fi hold is absent or linked'
for module in phy_qcom_qmp_pcie pwrseq_qcom_wcn pci_pwrctrl_pwrseq \
	mhi mhi_pci_generic ath11k ath11k_pci
do
	grep -Fqx "blacklist $module" "$blacklist" ||
		fail "automatic Wi-Fi probe blacklist omits $module"
	[ ! -d "/sys/module/$module" ] ||
		fail "Wi-Fi module loaded before the attended probe: $module"
done
grep -Fqx '[keyfile]' "$unmanaged"
grep -Fqx 'unmanaged-devices=interface-name:wlan0' "$unmanaged"
[ -z "$(find /etc/NetworkManager/system-connections -type f \
	-print -quit 2>/dev/null)" ] ||
	fail 'a NetworkManager connection profile is present'
[ ! -e /etc/wireguard/wg0.conf ] ||
	fail 'a WireGuard provider profile is present'
[ ! -e /sys/bus/pci/devices/0000:01:00.0 ] ||
	fail 'WLAN PCI endpoint exists before the attended probe'
[ ! -e /sys/class/net/wlan0 ] ||
	fail 'wlan0 exists before the attended probe'

attempt=/run/rog5-wifi-enumeration-probe.attempted
[ ! -e "$attempt" ] || fail 'WCN6855 enumeration probe was already attempted'
umask 077
: >"$attempt"

fatal_pattern='Kernel panic|Oops:|BUG:|Unable to handle kernel|Synchronous External Abort'
radio_failure_pattern='RDDM|firmware crashed|failed to start core'
[ "$(dmesg | grep -Eic "$fatal_pattern|$radio_failure_pattern" || true)" -eq 0 ] ||
	fail 'fatal or WLAN crash signature exists before the probe'
dmesg_start=$(( $(dmesg | wc -l) + 1 ))
pstore_before=$(find /sys/fs/pstore -mindepth 1 -maxdepth 1 -type f \
	2>/dev/null | wc -l)

modprobe pwrseq_qcom_wcn
modprobe pci_pwrctrl_pwrseq
modprobe phy_qcom_qmp_pcie

pci=/sys/bus/pci/devices/0000:01:00.0
pci_ready=0
for _ in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 \
	21 22 23 24 25 26 27 28 29 30; do
	if [ -r "$pci/vendor" ] && [ -r "$pci/device" ] &&
		[ -r "$pci/subsystem_device" ]; then
		pci_ready=1
		break
	fi
	sleep 1
done
[ "$pci_ready" -eq 1 ] || fail 'WLAN PCI endpoint did not enumerate'
[ "$(cat "$pci/vendor")" = 0x17cb ] || fail 'unexpected WLAN PCI vendor'
[ "$(cat "$pci/device")" = 0x1103 ] || fail 'unexpected WLAN PCI device'
[ "$(cat "$pci/subsystem_vendor")" = 0x17cb ] ||
	fail 'unexpected WLAN PCI subsystem vendor'
[ "$(cat "$pci/subsystem_device")" = 0x0108 ] ||
	fail 'unexpected WLAN PCI subsystem device'
[ ! -e "$pci/driver" ] ||
	fail 'WLAN PCI endpoint bound before explicit ath11k load'

modprobe ath11k_pci

wlan_ready=0
for _ in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 \
	21 22 23 24 25 26 27 28 29 30 31 32 33 34 35 36 37 38 39 40 \
	41 42 43 44 45 46 47 48 49 50 51 52 53 54 55 56 57 58 59 60; do
	if [ -d /sys/class/net/wlan0 ] && [ -L "$pci/driver" ]; then
		wlan_ready=1
		break
	fi
	sleep 1
done
[ "$wlan_ready" -eq 1 ] || fail 'ath11k did not expose wlan0'
[ "$(basename "$(readlink -f "$pci/driver")")" = ath11k_pci ] ||
	fail 'WLAN PCI endpoint did not bind ath11k_pci'
for module in phy_qcom_qmp_pcie pwrseq_qcom_wcn pci_pwrctrl_pwrseq \
	ath11k ath11k_pci
do
	[ -d "/sys/module/$module" ] ||
		fail "required Wi-Fi module did not load: $module"
done

iw dev wlan0 info | grep -Eq '^[[:space:]]*type managed$' ||
	fail 'wlan0 is not a managed/client interface'
[ "$(iw dev wlan0 link)" = 'Not connected.' ] ||
	fail 'wlan0 associated during enumeration-only probe'
nm_state=$(nmcli -g GENERAL.STATE device show wlan0 2>/dev/null || true)
printf '%s\n' "$nm_state" | grep -Fqi unmanaged ||
	fail 'NetworkManager does not report wlan0 unmanaged'
[ "$(cat /sys/class/net/wlan0/operstate)" = down ] ||
	fail 'wlan0 is up during enumeration-only probe'
[ "$(cat /sys/class/net/wlan0/carrier)" = 0 ] ||
	fail 'wlan0 has carrier during enumeration-only probe'
[ -z "$(ip -o address show dev wlan0)" ] ||
	fail 'wlan0 gained an address during enumeration-only probe'
[ -z "$(ip route show dev wlan0)" ] ||
	fail 'wlan0 gained an IPv4 route during enumeration-only probe'
[ -z "$(ip -6 route show dev wlan0)" ] ||
	fail 'wlan0 gained an IPv6 route during enumeration-only probe'

hci_count=0
for hci in /sys/class/bluetooth/hci*; do
	[ -e "$hci" ] || continue
	hci_count=$((hci_count + 1))
done
[ "$hci_count" -eq 0 ] || fail 'Bluetooth activated during Wi-Fi probe'

sleep 10
new_log=$(dmesg | tail -n +"$dmesg_start")
if printf '%s\n' "$new_log" |
	grep -Ei "$fatal_pattern|$radio_failure_pattern|Call trace:|IOMMU.*fault"
then
	fail 'kernel or WLAN log regressed during enumeration probe'
fi
[ "$(printf '%s\n' "$new_log" |
	grep -Eic 'ath11k_pci.*0000:01:00.0')" -ge 1 ] ||
	fail 'ath11k emitted no endpoint evidence'
[ "$(find /sys/fs/pstore -mindepth 1 -maxdepth 1 -type f \
	2>/dev/null | wc -l)" -eq "$pstore_before" ] ||
	fail 'pstore changed during enumeration probe'
[ "$(systemctl --failed --no-legend --plain 2>/dev/null |
	awk 'NF { count++ } END { print count + 0 }')" -eq 0 ] ||
	fail 'systemd gained a failed unit'
[ "$(find /sys/class/block -mindepth 1 -maxdepth 1 -type l \
	-exec test -e {}/device \; -print 2>/dev/null | wc -l)" -eq 0 ] ||
	fail 'physical storage appeared during enumeration probe'
[ "$(findmnt -rn -o SOURCE |
	awk '/^\/dev\// { count++ } END { print count + 0 }')" -eq 0 ] ||
	fail 'block-backed mount appeared during enumeration probe'

thermal_count=0
thermal_max=-1000000
for temperature in /sys/class/thermal/thermal_zone*/temp; do
	[ -r "$temperature" ] || continue
	value=$(cat "$temperature" 2>/dev/null || true)
	case $value in -[0-9]*|[0-9]*) ;; *) continue ;; esac
	thermal_count=$((thermal_count + 1))
	[ "$value" -le "$thermal_max" ] || thermal_max=$value
done
[ "$thermal_count" -ge 20 ] && [ "$thermal_max" -lt 50000 ] ||
	fail 'thermal state is not safe after WLAN enumeration'

printf 'PASS WCN6855 enumeration-only probe pci=17cb:1103 subsystem=17cb:0108 driver=ath11k_pci wlan=wlan0 type=managed link=not-connected nm=unmanaged addresses=0 routes=0 hci=0 storage=0 mounts=0 failed_units=0 thermal_zones=%s thermal_max_mC=%s pstore_records=%s watchdog=disarmed\n' \
	"$thermal_count" "$thermal_max" "$pstore_before"
