#!/bin/bash
set -euo pipefail

fail() {
	echo "FAIL $*" >&2
	exit 1
}

bundle=${1:-}
manifest_hash=${2:-}
[[ $# == 2 ]] ||
	fail 'usage: run-recovery-bundle-server.sh BUNDLE MANIFEST_SHA256'
[[ $bundle =~ ^[a-z0-9][a-z0-9._-]{0,63}$ &&
	$bundle != *..* && $bundle != none ]] ||
	fail 'invalid bundle identity'
[[ $manifest_hash =~ ^[0-9a-f]{64}$ &&
	$manifest_hash != 0000000000000000000000000000000000000000000000000000000000000000 ]] ||
	fail 'invalid manifest SHA-256'

repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
controller_source=$repo/packaging/host/rog5-recovery-bundle-controller
server_source=$repo/tools/recovery_control/host_bundle_server.py
controller=/usr/libexec/rog5-recovery-bundle-controller
server=/usr/libexec/rog5-recovery-host/host_bundle_server.py

for command in awk pkexec sha256sum stat; do
	command -v "$command" >/dev/null ||
		fail "missing launcher command: $command"
done
[[ -f $controller && ! -L $controller &&
	$(stat -Lc '%u:%g:%a:%F' -- "$controller") == '0:0:555:regular file' ]] ||
	fail 'fixed controller is not safely installed'
[[ -f $server && ! -L $server &&
	$(stat -Lc '%u:%g:%a:%F' -- "$server") == '0:0:555:regular file' ]] ||
	fail 'fixed bundle server is not safely installed'
[[ $(sha256sum "$controller" | awk '{ print $1 }') == \
	$(sha256sum "$controller_source" | awk '{ print $1 }') ]] ||
	fail 'installed controller is stale; reinstall it first'
[[ $(sha256sum "$server" | awk '{ print $1 }') == \
	$(sha256sum "$server_source" | awk '{ print $1 }') ]] ||
	fail 'installed bundle server is stale; reinstall it first'

exec pkexec "$controller" "$bundle" "$manifest_hash"
