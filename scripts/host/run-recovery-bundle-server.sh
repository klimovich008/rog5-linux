#!/bin/bash
set -euo pipefail

fail() {
	echo "FAIL $*" >&2
	exit 1
}

action=serve
case ${1:-} in
	preflight|serve-deferred|restore-fallback)
		action=$1
		shift
		;;
esac
if [[ $action == restore-fallback ]]; then
	anchor=${1:-}
	restore_timeout=${2:-}
	[[ $# == 2 ]] ||
		fail 'usage: run-recovery-bundle-server.sh restore-fallback ANCHOR TIMEOUT'
	[[ $anchor =~ ^/[A-Za-z0-9._/+-]{1,399}$ &&
		$anchor != */ && $anchor != *//* ]] ||
		fail 'invalid recovery anchor path'
	IFS=/ read -r -a anchor_parts <<<"$anchor"
	for anchor_part in "${anchor_parts[@]}"; do
		[[ -z $anchor_part || $anchor_part != .. ]] ||
			fail 'invalid recovery anchor path'
	done
	[[ $restore_timeout =~ ^[1-9][0-9]*$ &&
		$restore_timeout -le 900 ]] ||
		fail 'invalid fallback-profile timeout'
else
	bundle=${1:-}
	manifest_hash=${2:-}
	[[ $# == 2 ]] ||
		fail 'usage: run-recovery-bundle-server.sh [preflight|serve-deferred] BUNDLE MANIFEST_SHA256'
	[[ $bundle =~ ^[a-z0-9][a-z0-9._-]{0,63}$ &&
		$bundle != *..* && $bundle != none ]] ||
		fail 'invalid bundle identity'
	[[ $manifest_hash =~ ^[0-9a-f]{64}$ &&
		$manifest_hash != 0000000000000000000000000000000000000000000000000000000000000000 ]] ||
		fail 'invalid manifest SHA-256'
fi

repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
controller_source=$repo/packaging/host/rog5-recovery-bundle-controller
server_source=$repo/tools/recovery_control/host_bundle_server.py
client_source=$repo/scripts/host/rog5-recovery-host-client.py
controller=/usr/libexec/rog5-recovery-bundle-controller
server=/usr/libexec/rog5-recovery-host/host_bundle_server.py
client=/usr/libexec/rog5-recovery-host/rog5-recovery-host-client.py

for command in awk python3 sha256sum stat; do
	command -v "$command" >/dev/null ||
		fail "missing launcher command: $command"
done
[[ -f $controller && ! -L $controller &&
	$(stat -Lc '%u:%g:%a:%F' -- "$controller") == '0:0:555:regular file' ]] ||
	fail 'fixed controller is not safely installed'
[[ -f $server && ! -L $server &&
	$(stat -Lc '%u:%g:%a:%F' -- "$server") == '0:0:555:regular file' ]] ||
	fail 'fixed bundle server is not safely installed'
[[ -f $client && ! -L $client &&
	$(stat -Lc '%u:%g:%a:%F' -- "$client") == '0:0:555:regular file' ]] ||
	fail 'fixed host-control client is not safely installed'
[[ $(sha256sum "$controller" | awk '{ print $1 }') == \
	$(sha256sum "$controller_source" | awk '{ print $1 }') ]] ||
	fail 'installed controller is stale; reinstall it first'
[[ $(sha256sum "$server" | awk '{ print $1 }') == \
	$(sha256sum "$server_source" | awk '{ print $1 }') ]] ||
	fail 'installed bundle server is stale; reinstall it first'
[[ $(sha256sum "$client" | awk '{ print $1 }') == \
	$(sha256sum "$client_source" | awk '{ print $1 }') ]] ||
	fail 'installed host-control client is stale; reinstall it first'

if [[ $action == preflight ]]; then
	exec python3 -B "$server" --preflight "$bundle" "$manifest_hash"
fi
if [[ $action == serve-deferred ]]; then
	exec python3 -B "$client" bundle-deferred "$bundle" "$manifest_hash"
fi
if [[ $action == restore-fallback ]]; then
	exec python3 -B "$client" fallback-profile-restore \
		"$anchor" "$restore_timeout"
fi
exec python3 -B "$client" bundle "$bundle" "$manifest_hash"
