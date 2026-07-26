#!/bin/sh
set -eu

target=${TARGET:-/workspace/repo/scripts/device/vpn-hotspot.sh}
service=${SERVICE:-/workspace/repo/packaging/arch/rog5-vpn-hotspot.service}
old_ipv4=$(sysctl -n net.ipv4.ip_forward)
old_ipv6=$(sysctl -n net.ipv6.conf.all.forwarding)

for command in ip nft nsenter python3 sysctl unshare; do
	command -v "$command" >/dev/null
done

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

stage=$(mktemp -d)
client_pid=
vpn_pid=
wan_pid=
mkdir -p "$stage/bin"
cat >"$stage/bin/wg" <<'EOF'
#!/bin/sh
set -eu
[ "$1" = show ] && [ "$#" -eq 2 ]
ip link show dev "$2" >/dev/null
EOF
chmod 0755 "$stage/bin/wg"

run_target() {
	PATH="$stage/bin:$PATH" AP_IF=wlan0 VPN_IF=wg0 "$target" "$@"
}

server_pids=
cleanup() {
	run_target down >/dev/null 2>&1 || true
	for pid in $server_pids; do
		kill "$pid" >/dev/null 2>&1 || true
	done
	for pid in "$client_pid" "$vpn_pid" "$wan_pid"; do
		[ -z "$pid" ] || kill "$pid" >/dev/null 2>&1 || true
	done
	rm -rf "$stage"
}
trap cleanup EXIT INT TERM

unshare --net --fork --kill-child=KILL sleep 300 &
client_pid=$!
unshare --net --fork --kill-child=KILL sleep 300 &
vpn_pid=$!
unshare --net --fork --kill-child=KILL sleep 300 &
wan_pid=$!

ip link add wlan0 type veth peer name client0
ip link set client0 netns "$client_pid"
ip address add 10.42.0.1/24 dev wlan0
ip -6 address add fd42::1/64 dev wlan0 nodad
ip link set wlan0 up
nsenter -t "$client_pid" -n ip link set lo up
nsenter -t "$client_pid" -n ip address add 10.42.0.2/24 dev client0
nsenter -t "$client_pid" -n ip -6 address add fd42::2/64 dev client0 nodad
nsenter -t "$client_pid" -n ip link set client0 up
nsenter -t "$client_pid" -n ip route add default via 10.42.0.1
nsenter -t "$client_pid" -n ip -6 route add fd00::/64 via fd42::1

ip link add wg0 type veth peer name vpn0
ip link set vpn0 netns "$vpn_pid"
ip address add 10.99.0.1/24 dev wg0
ip link set wg0 up
nsenter -t "$vpn_pid" -n ip link set lo up
nsenter -t "$vpn_pid" -n ip address add 10.99.0.2/24 dev vpn0
nsenter -t "$vpn_pid" -n ip link set vpn0 up
nsenter -t "$vpn_pid" -n ip route add 10.42.0.0/24 via 10.99.0.1

ip link add uplink0 type veth peer name wan0
ip link set wan0 netns "$wan_pid"
ip address add 192.0.2.1/24 dev uplink0
ip -6 address add fd00::1/64 dev uplink0 nodad
ip link set uplink0 up
nsenter -t "$wan_pid" -n ip link set lo up
nsenter -t "$wan_pid" -n ip address add 192.0.2.2/24 dev wan0
nsenter -t "$wan_pid" -n ip -6 address add fd00::2/64 dev wan0 nodad
nsenter -t "$wan_pid" -n ip link set wan0 up

udp_echo='
import socket
import sys
family = socket.AF_INET6 if sys.argv[1] == "6" else socket.AF_INET
sock = socket.socket(family, socket.SOCK_DGRAM)
sock.bind((sys.argv[2], int(sys.argv[3])))
sock.settimeout(20)
data, peer = sock.recvfrom(1024)
if len(sys.argv) == 5:
    with open(sys.argv[4], "x", encoding="ascii") as marker:
        marker.write("received\n")
sock.sendto(data, peer)
'
udp_query='
import socket
import sys
family = socket.AF_INET6 if sys.argv[1] == "6" else socket.AF_INET
sock = socket.socket(family, socket.SOCK_DGRAM)
sock.settimeout(2)
payload = b"rog5-vpn-hotspot"
sock.sendto(payload, (sys.argv[2], int(sys.argv[3])))
data, unused = sock.recvfrom(1024)
raise SystemExit(0 if data == payload else 1)
'
udp_receive='
import socket
import sys
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((sys.argv[1], int(sys.argv[2])))
sock.settimeout(2)
try:
    sock.recvfrom(1024)
except TimeoutError:
    raise SystemExit(1)
'
udp_send='
import socket
import sys
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.sendto(b"unsolicited", (sys.argv[1], int(sys.argv[2])))
'

nsenter -t "$vpn_pid" -n python3 -c "$udp_echo" 4 10.99.0.2 9000 \
	>/dev/null 2>&1 &
server_pids="$server_pids $!"
nsenter -t "$wan_pid" -n python3 -c "$udp_echo" \
	4 192.0.2.2 9001 "$stage/wan4.received" \
	>/dev/null 2>&1 &
server_pids="$server_pids $!"
nsenter -t "$wan_pid" -n python3 -c "$udp_echo" \
	6 fd00::2 9002 "$stage/wan6.received" \
	>/dev/null 2>&1 &
server_pids="$server_pids $!"
sleep 1
for server_pid in $server_pids; do
	kill -0 "$server_pid"
done

run_target up
run_target check
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

nsenter -t "$client_pid" -n python3 -c "$udp_query" 4 10.99.0.2 9000
if nsenter -t "$client_pid" -n python3 -c "$udp_query" \
	4 192.0.2.2 9001 >/dev/null 2>&1; then
	echo 'FAIL hotspot client escaped through the ordinary uplink' >&2
	exit 1
fi
[ ! -e "$stage/wan4.received" ] || {
	echo 'FAIL hotspot client sent a datagram through the ordinary uplink' >&2
	exit 1
}
if nsenter -t "$client_pid" -n python3 -c "$udp_query" \
	6 fd00::2 9002 >/dev/null 2>&1; then
	echo 'FAIL hotspot client escaped through the IPv6 ordinary uplink' >&2
	exit 1
fi
[ ! -e "$stage/wan6.received" ] || {
	echo 'FAIL hotspot client sent a datagram through the IPv6 ordinary uplink' >&2
	exit 1
}

nsenter -t "$client_pid" -n python3 -c "$udp_receive" \
	10.42.0.2 9003 >/dev/null 2>&1 &
receiver_pid=$!
sleep 1
nsenter -t "$vpn_pid" -n python3 -c "$udp_send" 10.42.0.2 9003
if wait "$receiver_pid"; then
	echo 'FAIL unsolicited VPN traffic reached the hotspot client' >&2
	exit 1
fi

ip link delete wg0
if run_target check >/dev/null 2>&1; then
	echo 'FAIL health check accepted a missing VPN interface' >&2
	exit 1
fi
if nsenter -t "$client_pid" -n python3 -c "$udp_query" \
	4 192.0.2.2 9001 >/dev/null 2>&1; then
	echo 'FAIL VPN loss opened the ordinary uplink' >&2
	exit 1
fi
[ ! -e "$stage/wan4.received" ] || {
	echo 'FAIL VPN loss sent a datagram through the ordinary uplink' >&2
	exit 1
}

run_target down

! nft list table inet rog5_vpn_hotspot >/dev/null 2>&1
[ "$(sysctl -n net.ipv4.ip_forward)" = "$old_ipv4" ]
[ "$(sysctl -n net.ipv6.conf.all.forwarding)" = "$old_ipv6" ]

set +e
AP_IF='bad name' "$target" check >/dev/null 2>&1
status=$?
set -e
[ "$status" -eq 2 ]

echo 'PASS isolated VPN path, IPv4/IPv6 leak blocking, unsolicited isolation, VPN-loss fail-close, and cleanup'
