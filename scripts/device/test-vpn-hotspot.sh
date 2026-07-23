#!/bin/sh
set -eu

target=${TARGET:-/workspace/repo/scripts/device/vpn-hotspot.sh}
old_ipv4=$(sysctl -n net.ipv4.ip_forward)
old_ipv6=$(sysctl -n net.ipv6.conf.all.forwarding)

cleanup() {
	"$target" down >/dev/null 2>&1 || true
	ip link delete wg0 >/dev/null 2>&1 || true
	ip link delete ap0 >/dev/null 2>&1 || true
}
trap cleanup EXIT INT TERM

ip link add ap0 type dummy
ip link set ap0 up
ip link add wg0 type wireguard
ip link set wg0 up

"$target" up
"$target" check
rules=$(nft list table inet rog5_vpn_hotspot)
printf '%s\n' "$rules" | grep -q 'policy drop'
printf '%s\n' "$rules" | grep -q 'iifname "ap0" oifname "wg0" accept'
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
