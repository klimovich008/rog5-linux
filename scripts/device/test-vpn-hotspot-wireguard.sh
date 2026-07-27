#!/bin/sh
set -eu

repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)
target=${TARGET:-$repo/scripts/device/vpn-hotspot.sh}

fail() {
	echo "FAIL $*" >&2
	exit 1
}

[ "$(id -u)" -eq 0 ] ||
	fail 'run in a privileged network-disabled test container'
for command in awk grep ip mktemp nft nsenter python3 rm stat sysctl \
	unshare wg; do
	command -v "$command" >/dev/null ||
		fail "missing test command: $command"
done
[ -x "$target" ] || fail 'missing production VPN-hotspot control'

non_loopback=$(ip -o link show |
	awk -F ': ' '$2 !~ /^lo(@|$)/ { print $2 }')
[ -z "$non_loopback" ] ||
	fail 'test namespace is not network-disabled'
! nft list table inet rog5_vpn_hotspot >/dev/null 2>&1 ||
	fail 'test namespace already has the production nftables table'

old_ipv4=$(sysctl -n net.ipv4.ip_forward)
old_ipv6=$(sysctl -n net.ipv6.conf.all.forwarding)
umask 077
stage=$(mktemp -d)
client_pid=
peer_pid=
server_pid=

run_target() {
	AP_IF=wlan0 VPN_IF=wg0 "$target" "$@"
}

cleanup() {
	set +e
	run_target down >/dev/null 2>&1
	[ -z "$server_pid" ] || kill "$server_pid" >/dev/null 2>&1
	ip link delete wlan0 >/dev/null 2>&1
	ip link delete wg0 >/dev/null 2>&1
	ip link delete vpn-underlay0 >/dev/null 2>&1
	[ -z "$client_pid" ] || kill "$client_pid" >/dev/null 2>&1
	[ -z "$peer_pid" ] || kill "$peer_pid" >/dev/null 2>&1
	sysctl -qw net.ipv4.ip_forward="$old_ipv4"
	sysctl -qw net.ipv6.conf.all.forwarding="$old_ipv6"
	rm -rf "$stage"
}
trap cleanup EXIT INT TERM

unshare --net --fork --kill-child=KILL sleep 300 &
client_pid=$!
unshare --net --fork --kill-child=KILL sleep 300 &
peer_pid=$!

ip link add wlan0 type veth peer name client0
ip link set client0 netns "$client_pid"
ip address add 10.42.0.1/24 dev wlan0
ip link set wlan0 up
nsenter -t "$client_pid" -n ip link set lo up
nsenter -t "$client_pid" -n ip address add 10.42.0.2/24 dev client0
nsenter -t "$client_pid" -n ip link set client0 up
nsenter -t "$client_pid" -n ip route add 10.99.0.0/24 via 10.42.0.1

ip link add vpn-underlay0 type veth peer name peer-underlay0
ip link set peer-underlay0 netns "$peer_pid"
ip address add 198.51.100.1/30 dev vpn-underlay0
ip link set vpn-underlay0 up
nsenter -t "$peer_pid" -n ip link set lo up
nsenter -t "$peer_pid" -n \
	ip address add 198.51.100.2/30 dev peer-underlay0
nsenter -t "$peer_pid" -n ip link set peer-underlay0 up

wg genkey >"$stage/phone.key"
wg genkey >"$stage/peer.key"
[ "$(stat -c %a "$stage/phone.key")" = 600 ]
[ "$(stat -c %a "$stage/peer.key")" = 600 ]
phone_public=$(wg pubkey <"$stage/phone.key")
peer_public=$(wg pubkey <"$stage/peer.key")

ip link add wg0 type wireguard
ip address add 10.99.0.1/24 dev wg0
wg set wg0 private-key "$stage/phone.key" listen-port 51820 \
	peer "$peer_public" allowed-ips 10.99.0.2/32 \
	endpoint 198.51.100.2:51821 persistent-keepalive 1
ip link set wg0 up

nsenter -t "$peer_pid" -n ip link add peerwg0 type wireguard
nsenter -t "$peer_pid" -n ip address add 10.99.0.2/24 dev peerwg0
nsenter -t "$peer_pid" -n wg set peerwg0 \
	private-key "$stage/peer.key" listen-port 51821 \
	peer "$phone_public" allowed-ips 10.99.0.1/32 \
	endpoint 198.51.100.1:51820 persistent-keepalive 1
nsenter -t "$peer_pid" -n ip link set peerwg0 up

udp_echo='
import socket
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(("10.99.0.2", 9000))
sock.settimeout(20)
data, peer = sock.recvfrom(1024)
sock.sendto(data, peer)
'
udp_query='
import socket
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.settimeout(8)
payload = b"rog5-real-wireguard"
sock.sendto(payload, ("10.99.0.2", 9000))
data, unused = sock.recvfrom(1024)
raise SystemExit(0 if data == payload else 1)
'

nsenter -t "$peer_pid" -n python3 -c "$udp_echo" >/dev/null 2>&1 &
server_pid=$!
sleep 1
kill -0 "$server_pid"

run_target up
run_target check
nsenter -t "$client_pid" -n python3 -c "$udp_query"
wait "$server_pid"
server_pid=

phone_handshake=$(wg show wg0 latest-handshakes |
	awk 'NF == 2 { print $2; exit }')
peer_handshake=$(nsenter -t "$peer_pid" -n \
	wg show peerwg0 latest-handshakes |
	awk 'NF == 2 { print $2; exit }')
[ "${phone_handshake:-0}" -gt 0 ]
[ "${peer_handshake:-0}" -gt 0 ]

transfer=$(wg show wg0 transfer |
	awk 'NF == 3 { print $2 ":" $3; exit }')
case $transfer in
	*:*);;
	*) fail 'WireGuard transfer counters are absent' ;;
esac
[ "${transfer%%:*}" -gt 0 ]
[ "${transfer#*:}" -gt 0 ]

run_target down
if nft list table inet rog5_vpn_hotspot >/dev/null 2>&1; then
	fail 'production nftables table remains after teardown'
fi
[ "$(sysctl -n net.ipv4.ip_forward)" = "$old_ipv4" ]
[ "$(sysctl -n net.ipv6.conf.all.forwarding)" = "$old_ipv6" ]

rm -f "$stage/phone.key" "$stage/peer.key"
[ ! -e "$stage/phone.key" ]
[ ! -e "$stage/peer.key" ]

echo 'PASS real WireGuard handshake, encrypted hotspot packet, and cleanup'
