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
broker_source=$repo/packaging/host/rog5-recovery-host-broker.py
client_source=$repo/scripts/host/rog5-recovery-host-client.py
socket_unit_template=$repo/packaging/host/rog5-recovery-host.socket.in
service_unit_source=$repo/packaging/host/rog5-recovery-host@.service
destination=/usr/libexec/rog5-recovery-host
controller_destination=/usr/libexec/rog5-recovery-bundle-controller
bundle_root=/var/lib/rog5-recovery-bundles
export_storage_root=/home/rog5-linux
export_parent=$export_storage_root/exports
configuration_directory=/etc/rog5-recovery-host
configuration_destination=$configuration_directory/control.conf
unit_directory=/etc/systemd/system
socket_unit_destination=$unit_directory/rog5-recovery-host.socket
service_unit_destination=$unit_directory/rog5-recovery-host@.service
socket_path=/run/rog5-recovery-host.sock

for command in awk chmod chown getent grep install mktemp mv rm sha256sum \
	stat systemctl; do
	command -v "$command" >/dev/null ||
		fail "missing installer command: $command"
done
for source in "$controller_source" "$server_source" "$network_server_source" \
	"$headless_verifier_source" "$persistent_root_tool_source" \
	"$deployment_export_installer_source" "$broker_source" "$client_source" \
	"$socket_unit_template" "$service_unit_source"; do
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
caller_name=$(awk -F: -v uid="$PKEXEC_UID" '
	NF == 7 && $3 == uid { count++; name=$1 }
	END { if (count == 1) print name }
' <<<"$caller_record")
[[ $caller_name =~ ^[a-z_][a-z0-9_-]{0,30}$ ]] ||
	fail 'unsafe PolicyKit caller name'
caller_group_record=$(getent group "$caller_gid") ||
	fail 'PolicyKit caller primary group is absent'
caller_group=$(awk -F: -v gid="$caller_gid" '
	NF == 4 && $3 == gid { count++; name=$1 }
	END { if (count == 1) print name }
' <<<"$caller_group_record")
[[ $caller_group =~ ^[a-z_][a-z0-9_-]{0,30}$ ]] ||
	fail 'unsafe PolicyKit caller group'
[[ -d /home && ! -L /home &&
	$(stat -Lc '%u:%g:%F' -- /home) == '0:0:directory' ]] ||
	fail 'unsafe host home filesystem root'
home_mode=$(stat -Lc %a -- /home)
[[ $home_mode =~ ^[0-7]{3,4}$ ]] ||
	fail 'invalid host home filesystem mode'
(( (8#$home_mode & 8#022) == 0 )) ||
	fail 'host home filesystem root is writable by non-root'
for export_directory in "$export_storage_root" "$export_parent"; do
	if [[ -e $export_directory || -L $export_directory ]]; then
		[[ -d $export_directory && ! -L $export_directory &&
			$(stat -Lc '%u:%g:%a:%F' -- "$export_directory") == \
			'0:0:700:directory' ]] ||
			fail 'unsafe existing deployment export storage'
	fi
done
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
for trusted_directory in /etc /etc/systemd "$unit_directory"; do
	[[ -d $trusted_directory && ! -L $trusted_directory &&
		$(stat -Lc '%u:%g:%a:%F' -- "$trusted_directory") == \
		'0:0:755:directory' ]] ||
		fail 'unsafe systemd unit ancestry'
done
if [[ -e $configuration_directory || -L $configuration_directory ]]; then
	[[ -d $configuration_directory && ! -L $configuration_directory &&
		$(stat -Lc '%u:%g:%a:%F' -- "$configuration_directory") == \
		'0:0:755:directory' ]] ||
		fail 'unsafe host-control configuration directory'
fi
if [[ -e $configuration_destination || -L $configuration_destination ]]; then
	[[ -f $configuration_destination && ! -L $configuration_destination &&
		$(stat -Lc '%u:%g:%a:%F' -- "$configuration_destination") == \
		'0:0:444:regular file' ]] ||
		fail 'unsafe existing host-control configuration'
fi
for installed_unit in "$socket_unit_destination" \
	"$service_unit_destination"; do
	if [[ -e $installed_unit || -L $installed_unit ]]; then
		[[ -f $installed_unit && ! -L $installed_unit &&
			$(stat -Lc '%u:%g:%a:%F' -- "$installed_unit") == \
			'0:0:644:regular file' ]] ||
			fail 'unsafe existing host-control systemd unit'
	fi
done

controller_temporary=
server_temporary=
network_server_temporary=
headless_verifier_temporary=
persistent_root_tool_temporary=
deployment_export_installer_temporary=
broker_temporary=
client_temporary=
configuration_temporary=
socket_unit_temporary=
service_unit_temporary=
steamos_readonly=/usr/bin/steamos-readonly
steamos_readonly_fd=
steamos_readonly_fd_path=
restore_steamos_readonly=0
readonly_restore_reported=0
cleanup_signal_received=0
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
	if [[ -n $broker_temporary ]]; then
		rm -f -- "$broker_temporary"
	fi
	if [[ -n $client_temporary ]]; then
		rm -f -- "$client_temporary"
	fi
	if [[ -n $configuration_temporary ]]; then
		rm -f -- "$configuration_temporary"
	fi
	if [[ -n $socket_unit_temporary ]]; then
		rm -f -- "$socket_unit_temporary"
	fi
	if [[ -n $service_unit_temporary ]]; then
		rm -f -- "$service_unit_temporary"
	fi
}
run_steamos_readonly() {
	[[ $steamos_readonly_fd =~ ^[1-9][0-9]*$ &&
		$steamos_readonly_fd_path == "/proc/self/fd/$steamos_readonly_fd" ]] ||
		return 127
	LC_ALL=C "$BASH" "$steamos_readonly_fd_path" "$@"
}
read_steamos_readonly_state() {
	local command_status output
	if output=$(run_steamos_readonly status); then
		command_status=0
	else
		command_status=$?
	fi
	case $command_status:$output in
		0:enabled) printf '%s\n' enabled ;;
		1:disabled) printf '%s\n' disabled ;;
		*) return 1 ;;
	esac
}
restore_original_steamos_readonly() {
	local enable_status observed_state
	(( restore_steamos_readonly == 1 )) || return 0
	if run_steamos_readonly enable; then
		enable_status=0
	else
		enable_status=$?
	fi
	if ! observed_state=$(read_steamos_readonly_state); then
		observed_state=unknown
	fi
	if [[ $observed_state == enabled ]]; then
		restore_steamos_readonly=0
	fi
	(( enable_status == 0 )) && [[ $observed_state == enabled ]]
}
close_steamos_readonly() {
	if [[ $steamos_readonly_fd =~ ^[1-9][0-9]*$ ]]; then
		exec {steamos_readonly_fd}<&-
		steamos_readonly_fd=
		steamos_readonly_fd_path=
	fi
}
cleanup_and_restore_readonly() {
	local exit_status=$?
	trap 'cleanup_signal_received=1' HUP INT TERM
	trap - EXIT
	set +e
	cleanup
	if (( restore_steamos_readonly == 1 )); then
		if ! restore_original_steamos_readonly; then
			if (( readonly_restore_reported == 0 )); then
				echo 'FAIL could not restore SteamOS read-only mode' >&2
			fi
			if (( exit_status == 0 )); then
				exit_status=1
			fi
		fi
	fi
	close_steamos_readonly
	if (( cleanup_signal_received == 1 && exit_status == 0 )); then
		exit_status=130
	fi
	exit "$exit_status"
}
trap cleanup_and_restore_readonly EXIT
trap 'exit 130' HUP INT TERM

if [[ -e $steamos_readonly || -L $steamos_readonly ]]; then
	for trusted_directory in / /usr /usr/bin; do
		[[ -d $trusted_directory && ! -L $trusted_directory &&
			$(stat -Lc '%u:%g:%a:%F' -- "$trusted_directory") == \
			'0:0:755:directory' ]] ||
			fail 'unsafe SteamOS read-only controller ancestry'
	done
	[[ -f $steamos_readonly && ! -L $steamos_readonly &&
		-x $steamos_readonly &&
		$(stat -Lc '%u:%g:%a:%F' -- "$steamos_readonly") == \
		'0:0:755:regular file' ]] ||
		fail 'unsafe SteamOS read-only controller'
	readonly_path_identity=$(stat -Lc '%d:%i:%u:%g:%a:%F' -- \
		"$steamos_readonly")
	exec {steamos_readonly_fd}<"$steamos_readonly"
	steamos_readonly_fd_path=/proc/self/fd/$steamos_readonly_fd
	readonly_fd_identity=$(stat -Lc '%d:%i:%u:%g:%a:%F' -- \
		"$steamos_readonly_fd_path")
	[[ $readonly_fd_identity == "$readonly_path_identity" ]] ||
		fail 'SteamOS read-only controller changed while opening it'
	if ! readonly_state=$(read_steamos_readonly_state); then
		fail 'cannot inspect SteamOS read-only state'
	fi
	case $readonly_state in
		enabled)
			restore_steamos_readonly=1
			run_steamos_readonly disable
			[[ $(read_steamos_readonly_state) == disabled ]] ||
				fail 'SteamOS read-only mode did not disable'
			;;
		disabled) ;;
		*) fail 'unexpected SteamOS read-only state' ;;
	esac
fi

if [[ -e $socket_unit_destination ]]; then
	systemctl stop rog5-recovery-host.socket
	! systemctl is-active --quiet rog5-recovery-host.socket ||
		fail 'existing recovery host-control socket did not stop'
fi
install -d -o root -g root -m 0755 "$destination"
install -d -o "$PKEXEC_UID" -g "$caller_gid" -m 0700 "$bundle_root"
install -d -o root -g root -m 0700 \
	"$export_storage_root" "$export_parent"
install -d -o root -g root -m 0755 "$configuration_directory"
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
broker_temporary=$(mktemp --tmpdir="$destination" \
	.rog5-recovery-host-broker.py.XXXXXX)
client_temporary=$(mktemp --tmpdir="$destination" \
	.rog5-recovery-host-client.py.XXXXXX)
configuration_temporary=$(mktemp --tmpdir="$configuration_directory" \
	.control.conf.XXXXXX)
socket_unit_temporary=$(mktemp --tmpdir="$unit_directory" \
	.rog5-recovery-host.socket.XXXXXX)
service_unit_temporary=$(mktemp --tmpdir="$unit_directory" \
	.rog5-recovery-host@.service.XXXXXX)
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
install -o root -g root -m 0555 \
	"$broker_source" "$broker_temporary"
install -o root -g root -m 0555 \
	"$client_source" "$client_temporary"
printf '%s\n' \
	"operator_uid=$PKEXEC_UID" \
	"bundle_controller_sha256=$(sha256sum "$controller_source" |
		awk '{ print $1 }')" \
	"network_server_sha256=$(sha256sum "$network_server_source" |
		awk '{ print $1 }')" >"$configuration_temporary"
chown root:root "$configuration_temporary"
chmod 0444 "$configuration_temporary"
[[ $(grep -Foc '@ROG5_OPERATOR_USER@' "$socket_unit_template") == 1 &&
	$(grep -Foc '@ROG5_OPERATOR_GROUP@' "$socket_unit_template") == 1 ]] ||
	fail 'host-control socket template substitutions changed'
awk -v user="$caller_name" -v group="$caller_group" '
	{
		gsub(/@ROG5_OPERATOR_USER@/, user)
		gsub(/@ROG5_OPERATOR_GROUP@/, group)
		print
	}
' "$socket_unit_template" >"$socket_unit_temporary"
chown root:root "$socket_unit_temporary"
chmod 0644 "$socket_unit_temporary"
install -o root -g root -m 0644 \
	"$service_unit_source" "$service_unit_temporary"
mv -fT -- "$service_unit_temporary" "$service_unit_destination"
service_unit_temporary=
mv -fT -- "$socket_unit_temporary" "$socket_unit_destination"
socket_unit_temporary=
mv -fT -- "$configuration_temporary" "$configuration_destination"
configuration_temporary=
mv -fT -- "$client_temporary" \
	"$destination/rog5-recovery-host-client.py"
client_temporary=
mv -fT -- "$broker_temporary" \
	"$destination/rog5-recovery-host-broker.py"
broker_temporary=
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

if ! restore_original_steamos_readonly; then
	echo 'FAIL could not restore SteamOS read-only mode' >&2
	readonly_restore_reported=1
	exit 1
fi
close_steamos_readonly

systemctl daemon-reload
systemctl enable --now rog5-recovery-host.socket
systemctl is-active --quiet rog5-recovery-host.socket ||
	fail 'fixed recovery host-control socket is not active'
[[ -S $socket_path && ! -L $socket_path &&
	$(stat -Lc '%u:%g:%a:%F' -- "$socket_path") == \
	"$PKEXEC_UID:$caller_gid:600:socket" ]] ||
	fail 'fixed recovery host-control socket metadata is unsafe'
trap - EXIT HUP INT TERM

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
echo "INFO broker_sha256=$(sha256sum \
	"$destination/rog5-recovery-host-broker.py" | awk '{ print $1 }')"
echo "INFO client_sha256=$(sha256sum \
	"$destination/rog5-recovery-host-client.py" | awk '{ print $1 }')"
echo "INFO host_control_socket=$socket_path"
echo "INFO export_parent=$export_parent"
