#!/bin/sh
set -eu

repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)
target=${TARGET:-$repo/scripts/device/vpn-hotspot-v2.sh}

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
	[ -z "$server_pid" ] || kill -KILL "$server_pid" >/dev/null 2>&1
	[ -z "$server_pid" ] || wait "$server_pid" >/dev/null 2>&1
	ip link delete wlan0 >/dev/null 2>&1
	ip link delete wg0 >/dev/null 2>&1
	ip link delete vpn-underlay0 >/dev/null 2>&1
	[ -z "$client_pid" ] || kill -KILL "$client_pid" >/dev/null 2>&1
	[ -z "$client_pid" ] || wait "$client_pid" >/dev/null 2>&1
	[ -z "$peer_pid" ] || kill -KILL "$peer_pid" >/dev/null 2>&1
	[ -z "$peer_pid" ] || wait "$peer_pid" >/dev/null 2>&1
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

dns_server='
import select
import socket
import struct

def read_exact(sock, length):
    data = b""
    while len(data) < length:
        part = sock.recv(length - len(data))
        if not part:
            raise SystemExit(1)
        data += part
    return data

def answer(query):
    if len(query) < 12:
        raise SystemExit(1)
    return (
        query[:2] + b"\x81\x80" + query[4:6] +
        b"\x00\x00\x00\x00\x00\x00" + query[12:]
    )

udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
udp.bind(("10.99.0.2", 53))
tcp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
tcp.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
tcp.bind(("10.99.0.2", 53))
tcp.listen(1)
served = 0
while served < 2:
    ready, unused, exceptional = select.select([udp, tcp], [], [], 20)
    if not ready:
        raise SystemExit(1)
    for current in ready:
        if current is udp:
            query, peer = udp.recvfrom(4096)
            udp.sendto(answer(query), peer)
        else:
            connection, peer = tcp.accept()
            with connection:
                length = struct.unpack("!H", read_exact(connection, 2))[0]
                response = answer(read_exact(connection, length))
                connection.sendall(struct.pack("!H", len(response)) + response)
        served += 1
'
dns_query='
import socket
import struct
import sys

def read_exact(sock, length):
    data = b""
    while len(data) < length:
        part = sock.recv(length - len(data))
        if not part:
            raise SystemExit(1)
        data += part
    return data

name = b"\x03vpn\x04test\x00"
query = (
    b"\x52\x35\x01\x00\x00\x01\x00\x00\x00\x00\x00\x00" +
    name + b"\x00\x01\x00\x01"
)
protocol = sys.argv[1]
timeout = float(sys.argv[2])
kind = socket.SOCK_DGRAM if protocol == "udp" else socket.SOCK_STREAM
sock = socket.socket(socket.AF_INET, kind)
sock.settimeout(timeout)
if protocol == "udp":
    sock.sendto(query, ("10.99.0.2", 53))
    response, unused = sock.recvfrom(4096)
else:
    sock.connect(("10.99.0.2", 53))
    sock.sendall(struct.pack("!H", len(query)) + query)
    length = struct.unpack("!H", read_exact(sock, 2))[0]
    response = read_exact(sock, length)
valid = (
    len(response) >= 12 and response[:2] == query[:2] and
    struct.unpack("!H", response[2:4])[0] & 0x8000
)
raise SystemExit(0 if valid else 1)
'

start_dns_server() {
	nsenter -t "$peer_pid" -n python3 -c "$dns_server" \
		>/dev/null 2>&1 &
	server_pid=$!
	sleep 1
	kill -0 "$server_pid"
}

query_dns() {
	nsenter -t "$client_pid" -n python3 -c "$dns_query" "$1" "$2"
}

start_dns_server
run_target up
run_target check
query_dns udp 8
query_dns tcp 8
wait "$server_pid"
server_pid=

phone_handshake_before=$(wg show wg0 latest-handshakes |
	awk 'NF == 2 { print $2; exit }')
peer_handshake_before=$(nsenter -t "$peer_pid" -n \
	wg show peerwg0 latest-handshakes |
	awk 'NF == 2 { print $2; exit }')
[ "${phone_handshake_before:-0}" -gt 0 ]
[ "${peer_handshake_before:-0}" -gt 0 ]

transfer_before=$(wg show wg0 transfer |
	awk 'NF == 3 { print $2 ":" $3; exit }')
case $transfer_before in
	*:*);;
	*) fail 'WireGuard transfer counters are absent' ;;
esac
[ "${transfer_before%%:*}" -gt 0 ]
[ "${transfer_before#*:}" -gt 0 ]

nsenter -t "$peer_pid" -n ip link set peer-underlay0 down
sleep 2
run_target check
if query_dns udp 2 >/dev/null 2>&1; then
	fail 'UDP DNS crossed a failed WireGuard endpoint'
fi
if query_dns tcp 2 >/dev/null 2>&1; then
	fail 'TCP DNS crossed a failed WireGuard endpoint'
fi

nsenter -t "$peer_pid" -n ip link set peer-underlay0 up
start_dns_server
query_dns udp 10
query_dns tcp 10
wait "$server_pid"
server_pid=

phone_handshake_after=$(wg show wg0 latest-handshakes |
	awk 'NF == 2 { print $2; exit }')
peer_handshake_after=$(nsenter -t "$peer_pid" -n \
	wg show peerwg0 latest-handshakes |
	awk 'NF == 2 { print $2; exit }')
[ "${phone_handshake_after:-0}" -ge "$phone_handshake_before" ]
[ "${peer_handshake_after:-0}" -ge "$peer_handshake_before" ]

transfer_after=$(wg show wg0 transfer |
	awk 'NF == 3 { print $2 ":" $3; exit }')
case $transfer_after in
	*:*);;
	*) fail 'WireGuard recovery counters are absent' ;;
esac
[ "${transfer_after%%:*}" -gt "${transfer_before%%:*}" ]
[ "${transfer_after#*:}" -gt "${transfer_before#*:}" ]

run_target down
if nft list table inet rog5_vpn_hotspot >/dev/null 2>&1; then
	fail 'production nftables table remains after teardown'
fi
[ "$(sysctl -n net.ipv4.ip_forward)" = "$old_ipv4" ]
[ "$(sysctl -n net.ipv6.conf.all.forwarding)" = "$old_ipv6" ]

rm -f "$stage/phone.key" "$stage/peer.key"
[ ! -e "$stage/phone.key" ]
[ ! -e "$stage/peer.key" ]

echo 'PASS real WireGuard DNS UDP/TCP, endpoint loss/recovery, and cleanup'
