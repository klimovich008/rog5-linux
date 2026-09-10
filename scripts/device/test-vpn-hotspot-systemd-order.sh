#!/bin/sh
# shellcheck disable=SC2016
set -eu

repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)
service=$repo/packaging/arch/rog5-vpn-hotspot.service
verifier=$repo/scripts/device/verify-staged-arch-rootfs.sh

[ -f "$service" ] && [ ! -L "$service" ] || {
	echo 'FAIL missing VPN-hotspot service' >&2
	exit 1
}
[ -f "$verifier" ] && [ ! -L "$verifier" ] || {
	echo 'FAIL missing staged Arch rootfs verifier' >&2
	exit 1
}
bash -n "$verifier"

if grep -Fxq 'Before=dnsmasq.service' "$service"; then
	echo 'FAIL VPN-hotspot unit cycles dnsmasq before network-online and itself after network-online' >&2
	exit 1
fi

for contract in \
	'After=network-online.target NetworkManager.service wg-quick@wg0.service' \
	'Requires=NetworkManager.service wg-quick@wg0.service' \
	'Wants=network-online.target dnsmasq.service' \
	'ExecStart=/usr/local/sbin/rog5-vpn-hotspot.sh up' \
	'ExecStartPost=/usr/bin/nmcli connection up rog5-hotspot' \
	'ExecStop=-/usr/bin/nmcli connection down rog5-hotspot' \
	'ExecStopPost=/usr/local/sbin/rog5-vpn-hotspot.sh down'
do
	grep -Fxq "$contract" "$service" || {
		echo "FAIL VPN-hotspot unit omits: $contract" >&2
		exit 1
	}
done

grep -Fq 'systemd-analyze verify' "$verifier"
grep -Fq '/etc/systemd/system/rog5-vpn-hotspot.service' "$verifier"

echo 'PASS VPN-hotspot systemd order is cycle-free by contract and covered by the staged-root verifier'
