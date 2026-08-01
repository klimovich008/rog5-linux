#!/usr/bin/env bash
set -euo pipefail

fail() {
	echo "FAIL $*" >&2
	exit 1
}

action=${1:-}
case $action in
	preflight)
		case $# in
			1)
				profile=historical-headless-network-root-v1
				root=/var/lib/rog5-headless-network-root-v1/root
				package_sha256=
				;;
			3)
				profile=$2
				package_sha256=$3
				[[ $profile == headless-ssh-deployment-v3 ]] ||
					fail 'unsupported headless network-root profile'
				[[ $package_sha256 =~ ^[0-9a-f]{64}$ &&
					$package_sha256 != 0000000000000000000000000000000000000000000000000000000000000000 ]] ||
					fail 'deployment package identity must be one nonzero SHA-256'
				root=/home/rog5-linux/exports/headless-ssh-network-root-v3/root
				;;
			*)
				fail 'usage: run-headless-network-root-server.sh preflight [PROFILE PACKAGE_SHA256]'
				;;
		esac
		handoff_token=
		;;
	serve)
		[[ ${ALLOW_HEADLESS_NETWORK_ROOT_SERVER:-} == 1 ]] ||
			fail 'set ALLOW_HEADLESS_NETWORK_ROOT_SERVER=1 for one attended export'
		case $# in
			2)
				profile=historical-headless-network-root-v1
				root=/var/lib/rog5-headless-network-root-v1/root
				package_sha256=
				handoff_token=$2
				;;
			4)
				profile=$2
				package_sha256=$3
				handoff_token=$4
				[[ $profile == headless-ssh-deployment-v3 ]] ||
					fail 'unsupported headless network-root profile'
				[[ $package_sha256 =~ ^[0-9a-f]{64}$ &&
					$package_sha256 != 0000000000000000000000000000000000000000000000000000000000000000 ]] ||
					fail 'deployment package identity must be one nonzero SHA-256'
				root=/home/rog5-linux/exports/headless-ssh-network-root-v3/root
				;;
			*)
				fail 'usage: run-headless-network-root-server.sh serve [PROFILE PACKAGE_SHA256] HANDOFF_TOKEN'
				;;
		esac
		[[ $handoff_token =~ ^[0-9a-f]{64}$ &&
			$handoff_token != 0000000000000000000000000000000000000000000000000000000000000000 ]] ||
			fail 'HANDOFF_TOKEN must be one fresh nonzero 256-bit hex token'
		;;
	cancel)
		[[ ${ALLOW_HEADLESS_NETWORK_ROOT_CANCEL:-} == 1 ]] ||
			fail 'set ALLOW_HEADLESS_NETWORK_ROOT_CANCEL=1 for exact export cancellation'
		[[ $# == 2 ]] ||
			fail 'usage: run-headless-network-root-server.sh cancel HANDOFF_TOKEN'
		profile=
		root=
		package_sha256=
		handoff_token=$2
		[[ $handoff_token =~ ^[0-9a-f]{64}$ &&
			$handoff_token != 0000000000000000000000000000000000000000000000000000000000000000 ]] ||
			fail 'HANDOFF_TOKEN must be one fresh nonzero 256-bit hex token'
		;;
	*)
		fail 'usage: run-headless-network-root-server.sh preflight | serve HANDOFF_TOKEN | cancel HANDOFF_TOKEN'
		;;
esac

repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
installed_root=/usr/libexec/rog5-recovery-host
installed_server=$installed_root/serve-network-root.sh
installed_verifier=$installed_root/headless-network-root.py
installed_root_tool=$installed_root/persistent-root-tool.py
installed_client=$installed_root/rog5-recovery-host-client.py
source_server=$repo/scripts/host/serve-network-root.sh
source_verifier=$repo/scripts/host/headless-network-root.py
source_root_tool=$repo/scripts/device/persistent-root-tool.py
source_client=$repo/scripts/host/rog5-recovery-host-client.py
serve_timeout=${ROG5_NFS_TIMEOUT:-720}

for command in awk python3 sha256sum stat; do
	command -v "$command" >/dev/null ||
		fail "missing network-root launcher command: $command"
done
if [[ $action == cancel ]]; then
	[[ -f $installed_client && ! -L $installed_client &&
		$(stat -Lc '%u:%g:%a:%F' -- "$installed_client") == \
		'0:0:555:regular file' ]] ||
		fail 'fixed host-control client is not safely installed'
	[[ $(sha256sum "$installed_client" | awk '{ print $1 }') == \
		$(sha256sum "$source_client" | awk '{ print $1 }') ]] ||
		fail 'installed host-control client is stale; reinstall it first'
	exec python3 -B "$installed_client" network-cancel "$handoff_token"
fi
[[ $serve_timeout =~ ^[0-9]+$ &&
	$serve_timeout -ge 600 && $serve_timeout -le 900 ]] ||
	fail 'ROG5_NFS_TIMEOUT must be between 600 and 900 seconds'
for installed_input in "$installed_server" "$installed_verifier" \
	"$installed_root_tool" "$installed_client"; do
	[[ -f $installed_input && ! -L $installed_input &&
		$(stat -Lc '%u:%g:%a:%F' -- "$installed_input") == \
		'0:0:555:regular file' ]] ||
		fail 'fixed network-root host component is not safely installed'
done
for pair in \
	"$installed_server:$source_server" \
	"$installed_verifier:$source_verifier" \
	"$installed_root_tool:$source_root_tool" \
	"$installed_client:$source_client"; do
	installed_input=${pair%%:*}
	source_input=${pair#*:}
	[[ $(sha256sum "$installed_input" | awk '{ print $1 }') == \
		$(sha256sum "$source_input" | awk '{ print $1 }') ]] ||
		fail 'installed network-root host component is stale; reinstall it first'
done

if [[ $action == preflight ]]; then
	if [[ -n $package_sha256 ]]; then
		exec python3 -B "$installed_client" \
			network-preflight-v3 "$package_sha256"
	fi
	exec python3 -B "$installed_client" network-preflight-v1
fi
if [[ -n $package_sha256 ]]; then
	exec python3 -B "$installed_client" network-serve-v3 \
		"$package_sha256" "$handoff_token" "$serve_timeout"
fi
exec python3 -B "$installed_client" network-serve-v1 \
	"$handoff_token" "$serve_timeout"
