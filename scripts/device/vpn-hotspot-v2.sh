#!/bin/sh
set -eu

action=${1:-check}
ap_if=${AP_IF:-wlan0}
vpn_if=${VPN_IF:-wg0}
runtime=${ROG5_VPN_HOTSPOT_RUNTIME:-/run/rog5-vpn-hotspot}
state=$runtime/sysctl.state
rules=$runtime/rules.nft
table=rog5_vpn_hotspot

for interface in "$ap_if" "$vpn_if"; do
	case $interface in
		''|*[!A-Za-z0-9_.:-]*)
			echo "ERROR invalid interface name: $interface" >&2
			exit 2
			;;
	esac
done
case $runtime in
	/*) [ "$runtime" != / ] ;;
	*) false ;;
esac || {
	echo "ERROR invalid runtime directory: $runtime" >&2
	exit 2
}

restore_forwarding() {
	[ -r "$state" ] || return 0
	read -r old_ipv4 old_ipv6 <"$state"
	case $old_ipv4:$old_ipv6 in
		[01]:[01]) ;;
		*)
			echo 'ERROR invalid saved forwarding state' >&2
			return 1
			;;
	esac
	restore_status=0
	sysctl -qw net.ipv4.ip_forward="$old_ipv4" || restore_status=1
	sysctl -qw net.ipv6.conf.all.forwarding="$old_ipv6" ||
		restore_status=1
	[ "$restore_status" -ne 0 ] || rm -f "$state"
	return "$restore_status"
}

case $action in
	up)
		for command in ip nft sysctl wg; do
			command -v "$command" >/dev/null || {
				echo "ERROR missing $command" >&2
				exit 1
			}
		done
		ip link show dev "$ap_if" >/dev/null
		wg show "$vpn_if" >/dev/null
		if nft list table inet "$table" >/dev/null 2>&1; then
			echo "ERROR refusing existing nftables table: $table" >&2
			exit 1
		fi
		[ ! -e "$state" ] && [ ! -e "$rules" ] || {
			echo "ERROR refusing stale runtime state: $runtime" >&2
			exit 1
		}
		umask 077
		mkdir -p "$runtime"
		printf '%s %s\n' \
			"$(sysctl -n net.ipv4.ip_forward)" \
			"$(sysctl -n net.ipv6.conf.all.forwarding)" >"$state"
		cat >"$rules" <<EOF
table inet $table {
	chain input {
		type filter hook input priority filter; policy accept;
		iifname "$ap_if" udp sport 68 udp dport 67 accept
		iifname "$ap_if" drop
	}
	chain forward {
		type filter hook forward priority filter; policy accept;
		iifname "$ap_if" ct state invalid drop
		oifname "$ap_if" ct state invalid drop
		iifname "$ap_if" oifname "$vpn_if" accept
		iifname "$vpn_if" oifname "$ap_if" ct state established,related accept
		iifname "$ap_if" drop
		oifname "$ap_if" drop
	}
	chain postrouting {
		type nat hook postrouting priority srcnat; policy accept;
		iifname "$ap_if" oifname "$vpn_if" masquerade
	}
}
EOF
		table_loaded=0
		rollback_up() {
			rollback_status=$?
			trap - EXIT HUP INT TERM
			if restore_forwarding; then
				if [ "$table_loaded" -eq 1 ]; then
					nft delete table inet "$table" >/dev/null 2>&1 ||
						rollback_status=1
				fi
				rm -f "$rules"
			else
				echo 'ERROR forwarding rollback failed; kill-switch retained' >&2
				rollback_status=1
			fi
			exit "$rollback_status"
		}
		trap rollback_up EXIT
		trap 'exit 1' HUP INT TERM
		nft -f "$rules"
		table_loaded=1
		sysctl -qw net.ipv4.ip_forward=1
		sysctl -qw net.ipv6.conf.all.forwarding=1
		trap - EXIT HUP INT TERM
		;;
	down)
		restore_forwarding
		nft delete table inet "$table" 2>/dev/null || true
		rm -f "$rules"
		;;
	check)
		ip link show dev "$ap_if" >/dev/null
		wg show "$vpn_if" >/dev/null
		[ -r "$state" ]
		[ "$(sysctl -n net.ipv4.ip_forward)" = 1 ]
		[ "$(sysctl -n net.ipv6.conf.all.forwarding)" = 1 ]
		nft list table inet "$table" >/dev/null
		;;
	*)
		echo 'usage: vpn-hotspot-v2.sh up|down|check' >&2
		exit 2
		;;
esac

echo "PASS vpn-hotspot-v2 $action ap=$ap_if vpn=$vpn_if"
