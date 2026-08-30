#!/bin/sh
set -eu

repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)
helper=$repo/initramfs/persistent-tailscale-runtime
init=$repo/initramfs/persistent-root-init

[ -f "$helper" ] && [ ! -L "$helper" ] && [ -x "$helper" ]
sh -n "$helper" "$init"

for contract in \
	'/persist/opt/tailscale/1.102.3/dist' \
	'a0fa1b154af8c61f862a2259f559f7396d96c0225f4a863eae2333e1546bbe25' \
	'a14b94589c2630eb68ba7f7651ede226d2976708760ef3460556a00cf1aa4bab' \
	'dda710b5bed9fbf87efc0126b614ed8f0e9f4a43b2265486bc6ad7eb0570f226' \
	'service_address=10.77.0.2/30' \
	'service_gateway=10.77.0.1' \
	"[ \"\$(stat -c '%t:%T:%a' /dev/net/tun)\" = a:c8:666 ]" \
	'findmnt -n -o OPTIONS --target /persist' \
	'ip -4 route replace default via "$service_gateway" dev "$interface"' \
	'format=rog5-persistent-tailscale-runtime-v1'
do
	grep -Fq "$contract" "$helper"
done

for contract in \
	'cp -p /usr/local/sbin/rog5-persistent-tailscale' \
	'ExecStartPre=/run/rog5-persistent-tailscale prepare' \
	'ExecStart=/run/rog5-tailscale/tailscaled --state=/persist/var/lib/tailscale/tailscaled.state' \
	'ExecStopPost=/run/rog5-persistent-tailscale cleanup' \
	'RuntimeDirectoryMode=0700' \
	'Environment=TS_DEBUG_FIREWALL_MODE=nftables' \
	'sysinit.target.wants/rog5-tailscaled.service'
do
	grep -Fq "$contract" "$init"
done

! grep -Eq 'ROG5_.*OVERRIDE|TAILSCALE_(ROOT|PATH|STATE)=' "$helper"
[ "$(grep -c '^exact_file ' "$helper")" -eq 5 ]

echo 'PASS persistent Tailscale runtime is p23-bound, hash-pinned, tmpfs-executed, and fixed-network'
