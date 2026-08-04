#!/bin/bash
set -euo pipefail

fail() {
	echo "FAIL $*" >&2
	exit 1
}

action=serve
case ${1:-} in
	preflight|serve-deferred|serve-progress-deferred|restore-fallback)
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
elif [[ $action == serve-progress-deferred ]]; then
	bundle=${1:-}
	manifest_hash=${2:-}
	output_directory=${3:-}
	[[ $# == 3 ]] ||
		fail 'usage: run-recovery-bundle-server.sh serve-progress-deferred BUNDLE MANIFEST_SHA256 OUTPUT_DIRECTORY'
	[[ $bundle =~ ^[a-z0-9][a-z0-9._-]{0,63}$ &&
		$bundle != *..* && $bundle != none ]] ||
		fail 'invalid bundle identity'
	[[ $manifest_hash =~ ^[0-9a-f]{64}$ &&
		$manifest_hash != 0000000000000000000000000000000000000000000000000000000000000000 ]] ||
		fail 'invalid manifest SHA-256'
	[[ $output_directory =~ ^/[A-Za-z0-9._/+-]{1,399}$ &&
		$output_directory != */ && $output_directory != *//* ]] ||
		fail 'invalid progress output directory'
	IFS=/ read -r -a output_parts <<<"$output_directory"
	for output_part in "${output_parts[@]}"; do
		[[ -z $output_part || $output_part != .. ]] ||
			fail 'invalid progress output directory'
	done
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
progress_collector_source=$repo/packaging/host/rog5-recovery-progress-collector.py
progress_package_init_source=$repo/tools/recovery_control/__init__.py
progress_reference_source=$repo/tools/recovery_control/reference.py
progress_module_source=$repo/tools/recovery_control/host_progress_collector.py
client_source=$repo/scripts/host/rog5-recovery-host-client.py
controller=/usr/libexec/rog5-recovery-bundle-controller
server=/usr/libexec/rog5-recovery-host/host_bundle_server.py
progress_collector=/usr/libexec/rog5-recovery-host/rog5-recovery-progress-collector.py
progress_package_root=/usr/libexec/rog5-recovery-host/python/tools/recovery_control
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
if [[ $action == serve-progress-deferred ]]; then
	[[ -f $progress_collector && ! -L $progress_collector &&
		$(stat -Lc '%u:%g:%a:%F' -- "$progress_collector") == \
		'0:0:555:regular file' ]] ||
		fail 'fixed progress collector is not safely installed'
	for progress_directory in /usr/libexec/rog5-recovery-host/python \
		/usr/libexec/rog5-recovery-host/python/tools "$progress_package_root"; do
		[[ -d $progress_directory && ! -L $progress_directory &&
			$(stat -Lc '%u:%g:%a:%F' -- "$progress_directory") == \
			'0:0:755:directory' ]] ||
			fail 'fixed progress-module directory is not safely installed'
	done
	for progress_file in "$progress_package_root/__init__.py" \
		"$progress_package_root/reference.py" \
		"$progress_package_root/host_progress_collector.py"; do
		[[ -f $progress_file && ! -L $progress_file &&
			$(stat -Lc '%u:%g:%a:%F' -- "$progress_file") == \
			'0:0:444:regular file' ]] ||
			fail 'fixed progress module is not safely installed'
	done
fi
[[ $(sha256sum "$controller" | awk '{ print $1 }') == \
	$(sha256sum "$controller_source" | awk '{ print $1 }') ]] ||
	fail 'installed controller is stale; reinstall it first'
[[ $(sha256sum "$server" | awk '{ print $1 }') == \
	$(sha256sum "$server_source" | awk '{ print $1 }') ]] ||
	fail 'installed bundle server is stale; reinstall it first'
[[ $(sha256sum "$client" | awk '{ print $1 }') == \
	$(sha256sum "$client_source" | awk '{ print $1 }') ]] ||
	fail 'installed host-control client is stale; reinstall it first'
if [[ $action == serve-progress-deferred ]]; then
	for installed_and_source in \
		"$progress_collector:$progress_collector_source" \
		"$progress_package_root/__init__.py:$progress_package_init_source" \
		"$progress_package_root/reference.py:$progress_reference_source" \
		"$progress_package_root/host_progress_collector.py:$progress_module_source"; do
		installed_progress=${installed_and_source%%:*}
		progress_source=${installed_and_source#*:}
		[[ $(sha256sum "$installed_progress" | awk '{ print $1 }') == \
			$(sha256sum "$progress_source" | awk '{ print $1 }') ]] ||
			fail 'installed progress collector module set is stale; reinstall it first'
	done
fi

if [[ $action == preflight ]]; then
	exec python3 -B "$server" --preflight "$bundle" "$manifest_hash"
fi
if [[ $action == serve-deferred ]]; then
	exec python3 -B "$client" bundle-deferred "$bundle" "$manifest_hash"
fi
if [[ $action == serve-progress-deferred ]]; then
	exec python3 -B "$client" bundle-progress-deferred \
		"$bundle" "$manifest_hash" "$output_directory"
fi
if [[ $action == restore-fallback ]]; then
	exec python3 -B "$client" fallback-profile-restore \
		"$anchor" "$restore_timeout"
fi
exec python3 -B "$client" bundle "$bundle" "$manifest_hash"
