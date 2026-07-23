#!/bin/sh
set -eu

target=${TARGET:-/workspace/repo/scripts/device/vpn-hotspot.sh}
service=${SERVICE:-/workspace/repo/packaging/arch/rog5-vpn-hotspot.service}
old_ipv4=$(sysctl -n net.ipv4.ip_forward)
old_ipv6=$(sysctl -n net.ipv6.conf.all.forwarding)

grep -qx 'Requires=NetworkManager.service wg-quick@wg0.service' "$service"
grep -qx 'Wants=network-online.target dnsmasq.service' "$service"
grep -qx 'Before=dnsmasq.service' "$service"
grep -qx 'ConditionPathExists=/etc/wireguard/wg0.conf' "$service"
grep -qx 'ConditionPathExists=/etc/dnsmasq.d/rog5-hotspot.conf' "$service"
grep -qx 'ExecStart=/usr/local/sbin/rog5-vpn-hotspot.sh up' "$service"
grep -qx 'ExecStartPost=/usr/bin/nmcli connection up rog5-hotspot' "$service"
grep -qx 'ExecStop=-/usr/bin/nmcli connection down rog5-hotspot' "$service"
grep -qx 'ExecStopPost=/usr/local/sbin/rog5-vpn-hotspot.sh down' "$service"
! grep -q hostapd "$service"

for interface in wlan0 wg0; do
	if ip link show dev "$interface" >/dev/null 2>&1; then
		echo "FAIL isolated test requires no existing $interface" >&2
		exit 1
	fi
done
if nft list table inet rog5_vpn_hotspot >/dev/null 2>&1; then
	echo 'FAIL isolated test requires no existing rog5_vpn_hotspot table' >&2
	exit 1
fi

cleanup() {
	"$target" down >/dev/null 2>&1 || true
	ip link delete wg0 >/dev/null 2>&1 || true
	ip link delete wlan0 >/dev/null 2>&1 || true
}
trap cleanup EXIT INT TERM

ip link add wlan0 type dummy
ip link set wlan0 up
ip link add wg0 type wireguard
ip link set wg0 up

"$target" up
"$target" check
rules=$(nft list table inet rog5_vpn_hotspot)
! printf '%s\n' "$rules" | grep -q 'policy drop'
printf '%s\n' "$rules" | grep -q 'iifname "wlan0" udp sport 68 udp dport 67 accept'
printf '%s\n' "$rules" | grep -q 'iifname "wlan0" ct state invalid drop'
printf '%s\n' "$rules" | grep -q 'oifname "wlan0" ct state invalid drop'
printf '%s\n' "$rules" | grep -q 'iifname "wlan0" oifname "wg0" accept'
printf '%s\n' "$rules" | grep -q 'iifname "wg0" oifname "wlan0" ct state established,related accept'
printf '%s\n' "$rules" | grep -q 'iifname "wlan0" drop'
printf '%s\n' "$rules" | grep -q 'oifname "wlan0" drop'
printf '%s\n' "$rules" | grep -q 'iifname "wlan0" oifname "wg0" masquerade'
"$target" down

! nft list table inet rog5_vpn_hotspot >/dev/null 2>&1
[ "$(sysctl -n net.ipv4.ip_forward)" = "$old_ipv4" ]
[ "$(sysctl -n net.ipv6.conf.all.forwarding)" = "$old_ipv6" ]

set +e
AP_IF='bad name' "$target" check >/dev/null 2>&1
status=$?
set -e
[ "$status" -eq 2 ]

echo 'PASS isolated fail-closed VPN hotspot test'
