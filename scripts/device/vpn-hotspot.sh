#!/bin/sh
set -eu

action=${1:-check}
ap_if=${AP_IF:-ap0}
vpn_if=${VPN_IF:-wg0}
runtime=/run/rog5-vpn-hotspot
state=$runtime/sysctl.state
rules=$runtime/rules.nft
table=rog5_vpn_hotspot

for interface in "$ap_if" "$vpn_if"; do
	case $interface in
		''|*[!A-Za-z0-9_.:-]*) echo "ERROR invalid interface name: $interface" >&2; exit 2 ;;
	esac
done

restore_forwarding() {
	if [ -r "$state" ]; then
		read -r old_ipv4 old_ipv6 < "$state"
		sysctl -qw net.ipv4.ip_forward="$old_ipv4"
		sysctl -qw net.ipv6.conf.all.forwarding="$old_ipv6"
		rm -f "$state"
	fi
}

case $action in
	up)
		for command in ip nft sysctl wg; do
			command -v "$command" >/dev/null || { echo "ERROR missing $command" >&2; exit 1; }
		done
		ip link show dev "$ap_if" >/dev/null
		wg show "$vpn_if" >/dev/null
		mkdir -p "$runtime"
		if [ ! -r "$state" ]; then
			printf '%s %s\n' \
				"$(sysctl -n net.ipv4.ip_forward)" \
				"$(sysctl -n net.ipv6.conf.all.forwarding)" > "$state"
		fi
		cat > "$rules" <<EOF
table inet $table {
	chain forward {
		type filter hook forward priority filter; policy drop;
		ct state invalid drop
		ct state established,related accept
		iifname "$ap_if" oifname "$vpn_if" accept
	}
	chain postrouting {
		type nat hook postrouting priority srcnat; policy accept;
		iifname "$ap_if" oifname "$vpn_if" masquerade
	}
}
EOF
		nft delete table inet "$table" 2>/dev/null || true
		sysctl -qw net.ipv4.ip_forward=1
		sysctl -qw net.ipv6.conf.all.forwarding=1
		if ! nft -f "$rules"; then
			restore_forwarding
			exit 1
		fi
		;;
	down)
		nft delete table inet "$table" 2>/dev/null || true
		restore_forwarding
		rm -f "$rules"
		;;
	check)
		ip link show dev "$ap_if" >/dev/null
		wg show "$vpn_if" >/dev/null
		[ "$(sysctl -n net.ipv4.ip_forward)" = 1 ]
		[ "$(sysctl -n net.ipv6.conf.all.forwarding)" = 1 ]
		nft list table inet "$table" >/dev/null
		;;
	*)
		echo 'usage: vpn-hotspot.sh up|down|check' >&2
		exit 2
		;;
esac

echo "PASS vpn-hotspot $action ap=$ap_if vpn=$vpn_if"
