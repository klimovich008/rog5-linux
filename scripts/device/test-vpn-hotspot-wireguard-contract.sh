#!/bin/sh
# shellcheck disable=SC2016
set -eu

repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)
test=$repo/scripts/device/test-vpn-hotspot-wireguard.sh

[ -x "$test" ] || {
	echo 'FAIL missing real-WireGuard hotspot packet test' >&2
	exit 1
}
sh -n "$test"

for contract in \
	'target=${TARGET:-$repo/scripts/device/vpn-hotspot-v2.sh}' \
	'umask 077' \
	'unshare --net --fork --kill-child=KILL' \
	'ip link add wg0 type wireguard' \
	'wg genkey' \
	'wg pubkey' \
	'allowed-ips 10.99.0.2/32' \
	'allowed-ips 10.99.0.1/32' \
	'198.51.100.1/30' \
	'198.51.100.2/30' \
	'wg show wg0 latest-handshakes' \
	'wg show wg0 transfer' \
	'dns_server=' \
	'dns_query=' \
	'socket.SOCK_DGRAM' \
	'socket.SOCK_STREAM' \
	'ip link set peer-underlay0 down' \
	'ip link set peer-underlay0 up' \
	'transfer_before=' \
	'transfer_after=' \
	'AP_IF=wlan0 VPN_IF=wg0 "$target" "$@"' \
	'trap cleanup EXIT INT TERM' \
	'rm -rf "$stage"' \
	'PASS real WireGuard DNS UDP/TCP, endpoint loss/recovery, and cleanup'
do
	grep -Fq "$contract" "$test" || {
		echo "FAIL real-WireGuard hotspot test omits: $contract" >&2
		exit 1
	}
done

if grep -Eqi \
	'(^|[;&|[:space:]])(curl|wget|nc|netcat|socat|ssh|scp)([[:space:]]|$)|https?://|[[:alnum:]-]+[.](com|net|org)' \
	"$test"
then
	echo 'FAIL real-WireGuard hotspot test can contact an external endpoint' >&2
	exit 1
fi

echo 'PASS real-WireGuard hotspot test is ephemeral, network-isolated, packet-based, and production-path-bound'
