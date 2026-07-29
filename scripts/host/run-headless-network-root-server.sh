#!/usr/bin/env bash
set -euo pipefail

fail() {
	echo "FAIL $*" >&2
	exit 1
}

action=${1:-}
case $action in
	preflight)
		[[ $# == 1 ]] ||
			fail 'usage: run-headless-network-root-server.sh preflight'
		handoff_token=
		;;
	serve)
		[[ ${ALLOW_HEADLESS_NETWORK_ROOT_SERVER:-} == 1 ]] ||
			fail 'set ALLOW_HEADLESS_NETWORK_ROOT_SERVER=1 for one attended export'
		[[ $# == 2 ]] ||
			fail 'usage: run-headless-network-root-server.sh serve HANDOFF_TOKEN'
		handoff_token=$2
		[[ $handoff_token =~ ^[0-9a-f]{64}$ &&
			$handoff_token != 0000000000000000000000000000000000000000000000000000000000000000 ]] ||
			fail 'HANDOFF_TOKEN must be one fresh nonzero 256-bit hex token'
		;;
	*)
		fail 'usage: run-headless-network-root-server.sh preflight | serve HANDOFF_TOKEN'
		;;
esac

repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
installed_root=/usr/libexec/rog5-recovery-host
installed_server=$installed_root/serve-network-root.sh
installed_verifier=$installed_root/headless-network-root.py
installed_root_tool=$installed_root/persistent-root-tool.py
source_server=$repo/scripts/host/serve-network-root.sh
source_verifier=$repo/scripts/host/headless-network-root.py
source_root_tool=$repo/scripts/device/persistent-root-tool.py
serve_timeout=${ROG5_NFS_TIMEOUT:-720}

[[ $serve_timeout =~ ^[0-9]+$ &&
	$serve_timeout -ge 600 && $serve_timeout -le 900 ]] ||
	fail 'ROG5_NFS_TIMEOUT must be between 600 and 900 seconds'
for command in awk pkexec sha256sum stat; do
	command -v "$command" >/dev/null ||
		fail "missing network-root launcher command: $command"
done
for installed_input in "$installed_server" "$installed_verifier" \
	"$installed_root_tool"; do
	[[ -f $installed_input && ! -L $installed_input &&
		$(stat -Lc '%u:%g:%a:%F' -- "$installed_input") == \
		'0:0:555:regular file' ]] ||
		fail 'fixed network-root host component is not safely installed'
done
for pair in \
	"$installed_server:$source_server" \
	"$installed_verifier:$source_verifier" \
	"$installed_root_tool:$source_root_tool"; do
	installed_input=${pair%%:*}
	source_input=${pair#*:}
	[[ $(sha256sum "$installed_input" | awk '{ print $1 }') == \
		$(sha256sum "$source_input" | awk '{ print $1 }') ]] ||
		fail 'installed network-root host component is stale; reinstall it first'
done

if [[ $action == preflight ]]; then
	exec pkexec "$installed_server" preflight \
		/var/lib/rog5-headless-network-root-v1/root
fi
exec pkexec "$installed_server" serve \
	/var/lib/rog5-headless-network-root-v1/root \
	"$handoff_token" "$serve_timeout"
