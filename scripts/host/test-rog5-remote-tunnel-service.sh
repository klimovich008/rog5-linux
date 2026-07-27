#!/bin/sh
set -eu

repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)
unit=$repo/packaging/host-systemd-user/rog5-remote-tunnel.service

[ -r "$unit" ] || {
	echo 'FAIL missing Linux host remote-tunnel user service' >&2
	exit 1
}

for contract in \
	'ExecStart=/usr/bin/ssh -N -T' \
	'-o BatchMode=yes' \
	'-o ExitOnForwardFailure=yes' \
	'-o ServerAliveInterval=15' \
	'-o ServerAliveCountMax=3' \
	'-L 127.0.0.1:6080:127.0.0.1:6080' \
	'-L 127.0.0.1:7681:127.0.0.1:7681' \
	'-L 127.0.0.1:9222:127.0.0.1:9222' \
	'-L 127.0.0.1:13389:127.0.0.1:3389' \
	'rog5-fallback' \
	'ExecStartPost=/usr/bin/ssh' \
	'/usr/local/sbin/rog5-desktop-supervisor' \
	'start' \
	'Restart=always' \
	'RestartSec=5s' \
	'NoNewPrivileges=yes' \
	'RestrictAddressFamilies=AF_UNIX AF_INET AF_INET6'
do
	grep -Fq -- "$contract" "$unit" || {
		echo "FAIL remote-tunnel service omits: $contract" >&2
		exit 1
	}
done

[ "$(grep -c -- '-L 127.0.0.1:' "$unit")" -eq 4 ] || {
	echo 'FAIL remote-tunnel service does not have exactly four loopback forwards' >&2
	exit 1
}

if grep -Eq \
	'0[.]0[.]0[.]0:|GatewayPorts=yes|StrictHostKeyChecking=(no|accept-new)|PasswordAuthentication=yes|IdentityFile=|/home/' \
	"$unit"
then
	echo 'FAIL remote-tunnel service weakens host identity or exposes private input' >&2
	exit 1
fi

if grep -Eq '^ExecStart=.*rog5-desktop-supervisor' "$unit"; then
	echo 'FAIL remote supervisor is tied to the forwarding SSH process' >&2
	exit 1
fi

if grep -Fq 'PrivateTmp=yes' "$unit"; then
	echo 'FAIL PrivateTmp breaks OpenSSH system-config ownership checks in user services' >&2
	exit 1
fi

if command -v systemd-analyze >/dev/null 2>&1; then
	systemd-analyze --user verify "$unit"
fi

echo 'PASS Linux host remote-tunnel service is loopback-only, identity-pinned, reconnecting, and desktop-supervising'
