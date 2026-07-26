#!/usr/bin/env bash
set -euo pipefail

repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
stage=$repo/scripts/device/stage-arch-rootfs.sh
verify=$repo/scripts/device/verify-staged-arch-rootfs.sh
service=$repo/packaging/arch/rog5-chromium-headless.service

for file in "$stage" "$verify" "$service"; do
	[[ -f $file && ! -L $file ]]
done
bash -n "$stage"
bash -n "$verify"

for contract in \
	'User=rog5-agent' \
	'Group=rog5-agent' \
	'HOME=/var/lib/rog5-agent' \
	'WorkingDirectory=/var/lib/rog5-agent' \
	'--remote-debugging-address=127.0.0.1' \
	'--user-data-dir=/var/lib/rog5-agent/chromium' \
	'UMask=0077' \
	'NoNewPrivileges=yes' \
	'PrivateDevices=yes' \
	'PrivateTmp=yes' \
	'ProtectHome=yes' \
	'ProtectSystem=strict' \
	'ReadWritePaths=/var/lib/rog5-agent' \
	'CapabilityBoundingSet=' \
	'RestrictAddressFamilies=AF_UNIX AF_INET AF_INET6 AF_NETLINK' \
	'systemd-analyze verify' \
	'useradd --system --user-group' \
	'--home-dir /var/lib/rog5-agent' \
	'--no-create-home' \
	'--shell /usr/bin/nologin' \
	'rog5-agent' \
	'/var/lib/rog5-agent/private' \
	'stat -c %U:%G:%a /var/lib/rog5-agent' \
	'stat -c %U:%G:%a /var/lib/rog5-agent/private' \
	'getent passwd rog5-agent' \
	'id -nG rog5-agent' \
	'User=rog5-agent' \
	'[[ ! -e /var/lib/rog5-agent/.ssh ]]'
do
	grep -Fq -- "$contract" "$stage" "$verify" "$service" || {
		echo "FAIL agent-isolation contract omits: $contract" >&2
		exit 1
	}
done

if grep -Eq '^User=rog5$|^Group=rog5$|/home/rog5/[.]config/chromium-server' \
	"$service"; then
	echo 'FAIL automation service reuses the desktop account' >&2
	exit 1
fi
if grep -Eq \
	'BEGIN .*PRIVATE KEY|OPENROUTER_API_KEY|ANTHROPIC_API_KEY|OPENAI_API_KEY' \
	"$stage" "$service"; then
	echo 'FAIL automation rootfs input embeds a secret' >&2
	exit 1
fi

echo 'PASS browser automation is locked, isolated from the desktop account, loopback-only, credential-free, and on-demand'
