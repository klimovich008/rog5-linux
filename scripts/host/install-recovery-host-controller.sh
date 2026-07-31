#!/bin/bash
set -euo pipefail
umask 077

fail() {
	echo "FAIL $*" >&2
	exit 1
}

[[ $# == 0 ]] ||
	fail 'usage: install-recovery-host-controller.sh'
((EUID == 0)) || fail 'run this installer through PolicyKit'
[[ ${PKEXEC_UID:-} =~ ^[1-9][0-9]*$ ]] ||
	fail 'missing non-root PolicyKit caller identity'

repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
controller_source=$repo/packaging/host/rog5-recovery-bundle-controller
server_source=$repo/tools/recovery_control/host_bundle_server.py
network_server_source=$repo/scripts/host/serve-network-root.sh
headless_verifier_source=$repo/scripts/host/headless-network-root.py
persistent_root_tool_source=$repo/scripts/device/persistent-root-tool.py
deployment_export_installer_source=$repo/scripts/host/install-headless-ssh-deployment-export.py
destination=/usr/libexec/rog5-recovery-host
controller_destination=/usr/libexec/rog5-recovery-bundle-controller
bundle_root=/var/lib/rog5-recovery-bundles

for command in awk getent install mktemp mv rm sha256sum stat; do
	command -v "$command" >/dev/null ||
		fail "missing installer command: $command"
done
for source in "$controller_source" "$server_source" "$network_server_source" \
	"$headless_verifier_source" "$persistent_root_tool_source" \
	"$deployment_export_installer_source"; do
	[[ -f $source && ! -L $source ]] ||
		fail "unsafe installation source: $source"
done
server_hash=$(sha256sum "$server_source" | awk '{ print $1 }')
controller_pin=$(awk -F= '
	$1 == "server_sha256" { count++; value=$2 }
	END { if (count == 1) print value }
' "$controller_source")
[[ $controller_pin == "$server_hash" ]] ||
	fail 'controller source does not pin this bundle-server source'
[[ ! -L /usr/libexec ]] ||
	fail 'refusing symlinked /usr/libexec'
caller_record=$(getent passwd "$PKEXEC_UID") ||
	fail 'PolicyKit caller has no passwd record'
caller_gid=$(awk -F: -v uid="$PKEXEC_UID" '
	NF == 7 && $3 == uid { count++; gid=$4 }
	END { if (count == 1) print gid }
' <<<"$caller_record")
[[ $caller_gid =~ ^[0-9]+$ ]] ||
	fail 'invalid or ambiguous PolicyKit caller record'
if [[ -e $bundle_root ]]; then
	[[ -d $bundle_root && ! -L $bundle_root &&
		$(stat -Lc '%u:%g:%a:%F' -- "$bundle_root") == "$PKEXEC_UID:$caller_gid:700:directory" ]] ||
		fail 'unsafe existing recovery bundle root'
fi
if [[ -e $destination ]]; then
	[[ -d $destination && ! -L $destination &&
		$(stat -Lc '%u:%g:%a:%F' -- "$destination") == '0:0:755:directory' ]] ||
		fail 'unsafe existing recovery-host installation directory'
fi
if [[ -e $controller_destination ]]; then
	[[ -f $controller_destination && ! -L $controller_destination &&
		$(stat -Lc '%u:%g:%a:%F' -- "$controller_destination") == '0:0:555:regular file' ]] ||
		fail 'unsafe existing installed controller'
fi

install -d -o root -g root -m 0755 "$destination"
install -d -o "$PKEXEC_UID" -g "$caller_gid" -m 0700 "$bundle_root"
controller_temporary=
server_temporary=
network_server_temporary=
headless_verifier_temporary=
persistent_root_tool_temporary=
deployment_export_installer_temporary=
cleanup() {
	if [[ -n $controller_temporary ]]; then
		rm -f -- "$controller_temporary"
	fi
	if [[ -n $server_temporary ]]; then
		rm -f -- "$server_temporary"
	fi
	if [[ -n $network_server_temporary ]]; then
		rm -f -- "$network_server_temporary"
	fi
	if [[ -n $headless_verifier_temporary ]]; then
		rm -f -- "$headless_verifier_temporary"
	fi
	if [[ -n $persistent_root_tool_temporary ]]; then
		rm -f -- "$persistent_root_tool_temporary"
	fi
	if [[ -n $deployment_export_installer_temporary ]]; then
		rm -f -- "$deployment_export_installer_temporary"
	fi
}
trap cleanup EXIT
trap 'exit 130' HUP INT TERM
controller_temporary=$(mktemp --tmpdir=/usr/libexec \
	.rog5-recovery-bundle-controller.XXXXXX)
server_temporary=$(mktemp --tmpdir="$destination" \
	.host_bundle_server.py.XXXXXX)
network_server_temporary=$(mktemp --tmpdir="$destination" \
	.serve-network-root.sh.XXXXXX)
headless_verifier_temporary=$(mktemp --tmpdir="$destination" \
	.headless-network-root.py.XXXXXX)
persistent_root_tool_temporary=$(mktemp --tmpdir="$destination" \
	.persistent-root-tool.py.XXXXXX)
deployment_export_installer_temporary=$(mktemp --tmpdir="$destination" \
	.install-headless-ssh-deployment-export.py.XXXXXX)
install -o root -g root -m 0555 \
	"$controller_source" "$controller_temporary"
install -o root -g root -m 0555 \
	"$server_source" "$server_temporary"
install -o root -g root -m 0555 \
	"$network_server_source" "$network_server_temporary"
install -o root -g root -m 0555 \
	"$headless_verifier_source" "$headless_verifier_temporary"
install -o root -g root -m 0555 \
	"$persistent_root_tool_source" "$persistent_root_tool_temporary"
install -o root -g root -m 0555 \
	"$deployment_export_installer_source" \
	"$deployment_export_installer_temporary"
mv -fT -- "$deployment_export_installer_temporary" \
	"$destination/install-headless-ssh-deployment-export.py"
deployment_export_installer_temporary=
mv -fT -- "$persistent_root_tool_temporary" \
	"$destination/persistent-root-tool.py"
persistent_root_tool_temporary=
mv -fT -- "$headless_verifier_temporary" \
	"$destination/headless-network-root.py"
headless_verifier_temporary=
mv -fT -- "$network_server_temporary" \
	"$destination/serve-network-root.sh"
network_server_temporary=
mv -fT -- "$server_temporary" "$destination/host_bundle_server.py"
server_temporary=
mv -fT -- "$controller_temporary" "$controller_destination"
controller_temporary=

echo "PASS installed fixed recovery host controller"
echo "INFO controller_sha256=$(sha256sum "$controller_destination" |
	awk '{ print $1 }')"
echo "INFO server_sha256=$(sha256sum "$destination/host_bundle_server.py" |
	awk '{ print $1 }')"
echo "INFO network_server_sha256=$(sha256sum \
	"$destination/serve-network-root.sh" | awk '{ print $1 }')"
echo "INFO headless_verifier_sha256=$(sha256sum \
	"$destination/headless-network-root.py" | awk '{ print $1 }')"
echo "INFO persistent_root_tool_sha256=$(sha256sum \
	"$destination/persistent-root-tool.py" | awk '{ print $1 }')"
echo "INFO deployment_export_installer_sha256=$(sha256sum \
	"$destination/install-headless-ssh-deployment-export.py" |
	awk '{ print $1 }')"
