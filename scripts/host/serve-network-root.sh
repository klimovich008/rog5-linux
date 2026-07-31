#!/usr/bin/env bash
# shellcheck disable=SC2329
set -euo pipefail
PATH=/usr/sbin:/usr/bin:/sbin:/bin
export PATH

fail() {
	echo "FAIL $*" >&2
	exit 1
}

installed_directory=/usr/libexec/rog5-recovery-host
installed_server=$installed_directory/serve-network-root.sh
script_path=$(/usr/bin/realpath -e -- "${BASH_SOURCE[0]}")
installed_mode=0
installed_action=
if [[ $script_path == "$installed_server" ]]; then
	installed_mode=1
	installed_action=${1:-}
	case $installed_action in
		preflight)
			[[ $# == 2 || $# == 3 ]] ||
				fail 'usage: serve-network-root.sh preflight ROOT [PACKAGE_SHA256]'
			root=$2
			expected_package_sha256=${3:-}
			handoff_token=
			serve_timeout=720
			;;
		serve)
			[[ $# == 4 || $# == 5 ]] ||
				fail 'usage: serve-network-root.sh serve ROOT [PACKAGE_SHA256] HANDOFF_TOKEN TIMEOUT'
			root=$2
			if [[ $# == 5 ]]; then
				expected_package_sha256=$3
				handoff_token=$4
				serve_timeout=$5
			else
				expected_package_sha256=
				handoff_token=$3
				serve_timeout=$4
			fi
			;;
		cancel)
			[[ $# == 2 ]] ||
				fail 'usage: serve-network-root.sh cancel HANDOFF_TOKEN'
			root=
			expected_package_sha256=
			handoff_token=$2
			serve_timeout=0
			;;
		*)
			fail 'usage: serve-network-root.sh preflight ROOT | serve ROOT HANDOFF_TOKEN TIMEOUT | cancel HANDOFF_TOKEN'
			;;
	esac
	[[ ${PKEXEC_UID:-} =~ ^[1-9][0-9]*$ ]] ||
		fail 'missing non-root PolicyKit caller identity'
	[[ ! -L $installed_server &&
		$(stat -Lc '%u:%g:%a:%F' -- "$installed_server") == \
		'0:0:555:regular file' ]] ||
		fail 'unsafe installed network-root server metadata'
	headless_verifier=$installed_directory/headless-network-root.py
	persistent_root_tool=$installed_directory/persistent-root-tool.py
	if [[ $installed_action != cancel ]]; then
		for installed_input in "$headless_verifier" \
			"$persistent_root_tool"; do
			[[ -f $installed_input && ! -L $installed_input &&
				$(stat -Lc '%u:%g:%a:%F' -- "$installed_input") == \
				'0:0:555:regular file' ]] ||
				fail 'unsafe installed network-root verifier metadata'
		done
	fi
else
	[[ $# -le 1 ]] ||
		fail 'usage: serve-network-root.sh [ROOT]'
	repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
	root=${1:-/var/lib/rog5-network-root-v1}
	serve_timeout=${ROG5_NFS_TIMEOUT:-900}
	handoff_token=${ROG5_NFS_HANDOFF_TOKEN:-}
	expected_package_sha256=
fi
host_ip=169.254.77.1
phone_ip=169.254.77.2
host_cidr=$host_ip/30
firewall_zone=drop
export_mount=/run/rog5-network-root-export
mountd_port=32767
grace_time=10
lease_time=10
handoff_marker=/run/rog5-network-root-nfs-ready
service_state=/run/rog5-network-root-server.state
deployment_export=/home/rog5-linux/exports/headless-ssh-network-root-v3
deployment_root=$deployment_export/root
deployment_manifest=$deployment_export/manifest

[[ $EUID == 0 ]] || fail 'run through PolicyKit; do not share a sudo password'
if [[ $installed_action != cancel ]]; then
	if [[ ! $serve_timeout =~ ^[0-9]+$ ]] ||
		((serve_timeout < 60 || serve_timeout > 86400)); then
		fail 'ROG5_NFS_TIMEOUT must be between 60 and 86400 seconds'
	fi
fi
if [[ -n $handoff_token ]]; then
	[[ $handoff_token =~ ^[0-9a-f]{64}$ &&
		$handoff_token != 0000000000000000000000000000000000000000000000000000000000000000 ]] ||
		fail 'ROG5_NFS_HANDOFF_TOKEN must be one nonzero 256-bit hex token'
fi
if [[ $installed_action != cancel && -n $handoff_token ]]; then
	[[ ! -e $handoff_marker && ! -L $handoff_marker ]] ||
		fail 'refusing an existing NFS handoff marker'
fi
process_identity() {
	local process=$1 record rest
	local -a fields

	IFS= read -r record <"/proc/$process/stat" 2>/dev/null || return 1
	rest=${record##*) }
	read -r -a fields <<<"$rest"
	[[ ${#fields[@]} -ge 20 &&
		${fields[2]} =~ ^[1-9][0-9]*$ &&
		${fields[3]} =~ ^[1-9][0-9]*$ &&
		${fields[19]} =~ ^[1-9][0-9]*$ ]] ||
		return 1
	printf '%s %s %s\n' \
		"${fields[2]}" "${fields[3]}" "${fields[19]}"
}

process_state() {
	local process=$1 record rest state

	IFS= read -r record <"/proc/$process/stat" 2>/dev/null || return 1
	rest=${record##*) }
	read -r state _ <<<"$rest"
	[[ $state =~ ^[A-Z]$ ]] || return 1
	printf '%s\n' "$state"
}

process_start_time() {
	local process=$1 group session start_time

	read -r group session start_time < <(process_identity "$process") ||
		return 1
	printf '%s\n' "$start_time"
}

cancel_network_root() {
	local -a fields
	local pid start_time caller_uid token group session current state
	local attempt

	[[ -f $service_state && ! -L $service_state &&
		$(stat -Lc '%u:%g:%a:%F:%h' -- "$service_state") == \
		'0:0:400:regular file:1' ]] ||
		fail 'network-root service identity is unavailable or unsafe'
	mapfile -t fields <"$service_state"
	[[ ${#fields[@]} == 5 &&
		${fields[0]} == 'format=rog5-network-root-server-v1' &&
		${fields[1]} =~ ^pid=([1-9][0-9]*)$ ]] ||
		fail 'network-root service identity is malformed'
	pid=${BASH_REMATCH[1]}
	[[ ${fields[2]} =~ ^start_time=([1-9][0-9]*)$ ]] ||
		fail 'network-root service start time is malformed'
	start_time=${BASH_REMATCH[1]}
	[[ ${fields[3]} =~ ^caller_uid=([1-9][0-9]*)$ ]] ||
		fail 'network-root service caller is malformed'
	caller_uid=${BASH_REMATCH[1]}
	[[ ${fields[4]} =~ ^token=([0-9a-f]{64})$ ]] ||
		fail 'network-root service token is malformed'
	token=${BASH_REMATCH[1]}
	[[ $caller_uid == "$PKEXEC_UID" &&
		$token == "$handoff_token" ]] ||
		fail 'network-root cancellation identity does not match'
	current=$(process_start_time "$pid" || true)
	if [[ $current != "$start_time" ]]; then
		if kill -0 -- "-$pid" 2>/dev/null; then
			fail 'stale service identity retains a live process group'
		fi
		rm -f -- "$service_state"
		echo 'PASS stale network-root service identity removed'
		return
	fi
	python3 -B - "$pid" "$start_time" <<'PY'
import os
from pathlib import Path
import signal
import sys
import time


def identity(pid: int) -> tuple[int, int, int]:
    record = Path(f"/proc/{pid}/stat").read_text(encoding="ascii")
    fields = record.rsplit(") ", 1)[1].split()
    if len(fields) < 20:
        raise RuntimeError("short process identity")
    uid = Path(f"/proc/{pid}/status").read_text(
        encoding="ascii"
    )
    uid_line = next(
        line for line in uid.splitlines() if line.startswith("Uid:")
    )
    if uid_line.split()[1:] != ["0", "0", "0", "0"]:
        raise RuntimeError("service is not root-owned")
    return int(fields[2]), int(fields[3]), int(fields[19])


pid = int(sys.argv[1])
expected_start = int(sys.argv[2])
pidfd = os.pidfd_open(pid, 0)
stopped = False
try:
    group, session, start = identity(pid)
    if (group, session, start) != (pid, pid, expected_start):
        raise RuntimeError("service process identity changed")
    signal.pidfd_send_signal(pidfd, signal.SIGSTOP)
    stopped = True
    deadline = time.monotonic() + 2
    while time.monotonic() < deadline:
        status = Path(f"/proc/{pid}/status").read_text(
            encoding="ascii"
        )
        state = next(
            line for line in status.splitlines() if line.startswith("State:")
        ).split()[1]
        if state in {"T", "t"}:
            break
        time.sleep(0.01)
    else:
        raise RuntimeError("service leader did not stop")
    if identity(pid) != (pid, pid, expected_start):
        raise RuntimeError("stopped service identity changed")
    os.killpg(pid, signal.SIGTERM)
finally:
    if stopped:
        try:
            os.killpg(pid, signal.SIGCONT)
        except ProcessLookupError:
            pass
    os.close(pidfd)
PY
	for attempt in {1..300}; do
		current=$(process_start_time "$pid" || true)
		state=$(process_state "$pid" || true)
		if [[ ($current != "$start_time" || $state == Z || $state == X) &&
			! -e $service_state && ! -L $service_state ]]; then
			echo 'PASS exact network-root service cancelled and cleaned'
			return
		fi
		sleep 0.1
	done
	fail 'network-root service did not clean after cancellation'
}

if [[ $installed_mode == 1 && $installed_action == cancel ]]; then
	for command in python3 rm sleep stat; do
		command -v "$command" >/dev/null ||
			fail "missing cancellation command: $command"
	done
	cancel_network_root
	exit 0
fi

for command in awk date exportfs firewall-cmd findmnt grep install ip mount \
	chmod ln mkdir mktemp mountpoint nmcli pgrep python3 realpath rm rpc.mountd \
	rpc.nfsd sha256sum sleep ss sysctl udevadm stat systemctl tr umount; do
	command -v "$command" >/dev/null || fail "missing host command: $command"
done

service_state_created=0
service_state_temp=
early_service_cleanup() {
	set +e
	if [[ $service_state_created == 1 ]]; then
		rm -f -- "$service_state"
	fi
	if [[ -n $service_state_temp ]]; then
		rm -f -- "$service_state_temp"
	fi
}
if [[ $installed_mode == 1 && $installed_action == serve ]]; then
	[[ ! -e $service_state && ! -L $service_state ]] ||
		fail 'refusing existing network-root service identity'
	trap early_service_cleanup EXIT
	trap 'exit 130' INT TERM HUP
	read -r service_group service_session service_start_time < <(
		process_identity "$$"
	) ||
		fail 'cannot capture network-root service identity'
	[[ $service_group == "$$" && $service_session == "$$" ]] ||
		fail 'network-root service requires an isolated process group'
	service_state_temp=$(mktemp \
		/run/.rog5-network-root-server.state.XXXXXX)
	printf '%s\n' \
		'format=rog5-network-root-server-v1' \
		"pid=$$" \
		"start_time=$service_start_time" \
		"caller_uid=$PKEXEC_UID" \
		"token=$handoff_token" >"$service_state_temp"
	chmod 0400 "$service_state_temp"
	ln "$service_state_temp" "$service_state"
	service_state_created=1
	rm -f -- "$service_state_temp"
	service_state_temp=
fi
if [[ $installed_action != serve ]]; then
	[[ ! -e $service_state && ! -L $service_state ]] ||
		fail 'refusing existing network-root service identity'
fi

verify_deployment_export() {
	[[ -n $expected_package_sha256 ]] || return
	python3 -B "$headless_verifier" verify-export-ancestry \
		"$deployment_export"
	[[ -f $deployment_manifest && ! -L $deployment_manifest &&
		$(stat -Lc '%u:%g:%a:%F' -- "$deployment_manifest") == \
		'0:0:444:regular file' ]] ||
		fail 'deployment package manifest metadata is unsafe'
	[[ $(sha256sum "$deployment_manifest" | awk '{ print $1 }') == \
		"$expected_package_sha256" ]] ||
		fail 'deployment package manifest identity changed'
}

verify_deployment_export
[[ -d $root && ! -L $root ]] || fail 'missing prepared export root'
root=$(realpath -e "$root")
if [[ -n $expected_package_sha256 &&
	$root != "$deployment_root" ]]; then
	fail 'only the deployment headless root accepts a package identity'
fi
case $root in
	/var/lib/rog5-network-root-v1)
		[[ $installed_mode == 0 ]] ||
			fail 'installed server accepts only the minimal headless root'
		"$repo/scripts/host/verify-network-root-export.sh" "$root"
		;;
	/var/lib/rog5-headless-network-root-v1/root)
		if [[ $installed_mode == 1 ]]; then
			python3 -B "$headless_verifier" verify-root "$root" \
				/var/lib/rog5-headless-network-root-v1/manifest
		else
			"$repo/scripts/host/verify-headless-network-root-export.sh" "$root"
		fi
		;;
	"$deployment_root")
		[[ $installed_mode == 1 ]] ||
			fail 'deployment headless root requires the fixed installed server'
		[[ $expected_package_sha256 =~ ^[0-9a-f]{64}$ &&
			$expected_package_sha256 != 0000000000000000000000000000000000000000000000000000000000000000 ]] ||
			fail 'deployment package identity must be one nonzero SHA-256'
		python3 -B "$headless_verifier" verify-root "$root" \
			"$deployment_manifest"
		;;
	/var/lib/rog5-network-root-a660-gmu-cx-runtime-pm-v10)
		[[ $installed_mode == 0 ]] ||
			fail 'installed server accepts only the minimal headless root'
		[[ ${ALLOW_MAINLINE_A660_GMU_CX_RUNTIME_PM_V10_NFS:-} == 1 ]] ||
			fail 'set ALLOW_MAINLINE_A660_GMU_CX_RUNTIME_PM_V10_NFS=1 for the attended v10 window'
		"$repo/scripts/host/verify-a660-gmu-cx-runtime-pm-v10-export.sh" \
			"$root" /var/lib/rog5-network-root-a660-gmu-resume-entry-v9
		;;
	/var/lib/rog5-network-root-arch-successor-v1)
		[[ $installed_mode == 0 ]] ||
			fail 'installed server accepts only the minimal headless root'
		[[ ${ALLOW_ARCH_SUCCESSOR_V1_NFS:-} == 1 ]] ||
			fail 'set ALLOW_ARCH_SUCCESSOR_V1_NFS=1 for the attended Arch successor v1 window'
		"$repo/scripts/host/verify-arch-successor-export.sh" "$root"
		;;
	*)
		fail 'unexpected export root'
		;;
esac

etab=/var/lib/nfs/etab
if [[ ! -e $etab ]]; then
	[[ $installed_mode == 1 && $installed_action == preflight ]] &&
		fail 'NFS export state file is absent'
	install -m 0644 /dev/null "$etab"
fi
[[ -f $etab && ! -L $etab ]] ||
	fail 'unexpected NFS export state file type'
case $(stat -c %u:%g:%a "$etab") in
	0:0:600|0:0:644) ;;
	*) fail 'unexpected NFS export state file metadata' ;;
esac
systemctl is-active --quiet firewalld.service ||
	fail 'firewalld must be active'
! systemctl is-active --quiet nfs-server.service ||
	fail 'refusing to share a host with an active NFS service'
! pgrep -x rpc.mountd >/dev/null ||
	fail 'refusing to share a host with an active mount daemon'
if mountpoint -q /proc/fs/nfsd &&
	[[ -r /proc/fs/nfsd/threads ]] &&
	[[ $(< /proc/fs/nfsd/threads) != 0 ]]; then
	fail 'refusing to share active kernel NFS threads'
fi
[[ -z $(exportfs -v) ]] || fail 'refusing existing NFS exports'
[[ ! -e $export_mount ]] || fail "refusing existing $export_mount"
[[ $(firewall-cmd --zone="$firewall_zone" --list-all |
	awk '$1 == "target:" { print $2 }') == DROP ]] ||
	fail "$firewall_zone firewall zone is not drop-by-default"
for query in --list-interfaces --list-sources --list-services --list-ports \
	--list-protocols --list-source-ports --list-forward-ports \
	--list-icmp-blocks --list-rich-rules; do
	[[ -z $(firewall-cmd --zone="$firewall_zone" "$query") ]] ||
		fail "$firewall_zone firewall zone is already in use"
done
if firewall-cmd --zone="$firewall_zone" --query-masquerade >/dev/null; then
	fail "$firewall_zone firewall zone has masquerading enabled"
fi

mapfile -t protected_zones < <(
	firewall-cmd --get-active-zones |
		awk '/^[^[:space:]]/ { print $1 }'
)
(( ${#protected_zones[@]} > 0 )) || fail 'no active firewall zone'

if [[ $installed_mode == 1 && $installed_action == preflight ]]; then
	echo 'PASS fixed headless network-root root and host state verified'
	exit 0
fi

nfs_drop_rule="rule family=\"ipv4\" priority=\"-300\" destination address=\"$host_ip/32\" port port=\"2049\" protocol=\"tcp\" drop"
mountd_tcp_drop_rule="rule family=\"ipv4\" priority=\"-300\" port port=\"$mountd_port\" protocol=\"tcp\" drop"
mountd_udp_drop_rule="rule family=\"ipv4\" priority=\"-300\" port port=\"$mountd_port\" protocol=\"udp\" drop"
nfs_allow_rule="rule family=\"ipv4\" priority=\"-300\" source address=\"$phone_ip/32\" destination address=\"$host_ip/32\" port port=\"2049\" protocol=\"tcp\" accept"

allow_rule_added=0
drop_rules_added=0
bind_mounted=0
nfsd_mounted=0
export_active=0
mountd_pid=
nfsd_started=0
nonlocal_original=
handoff_marker_created=0
handoff_marker_temp=
declare -a touched_interfaces=()

cleanup() {
	local interface zone
	set +e
	if [[ $export_active == 1 ]]; then
		exportfs -u "$phone_ip:$export_mount"
		exportfs -f
	fi
	if [[ $nfsd_started == 1 ]]; then
		rpc.nfsd 0
	fi
	if [[ $handoff_marker_created == 1 ]]; then
		rm -f -- "$handoff_marker"
	fi
	if [[ -n $handoff_marker_temp ]]; then
		rm -f -- "$handoff_marker_temp"
	fi
	if [[ $service_state_created == 1 ]]; then
		rm -f -- "$service_state"
	fi
	if [[ -n $service_state_temp ]]; then
		rm -f -- "$service_state_temp"
	fi
	if [[ -n $mountd_pid ]]; then
		kill "$mountd_pid" 2>/dev/null
		wait "$mountd_pid" 2>/dev/null
	fi
	if [[ $bind_mounted == 1 ]]; then
		umount "$export_mount"
	fi
	if [[ -d $export_mount ]]; then
		rmdir "$export_mount"
	fi
	if [[ $nfsd_mounted == 1 ]]; then
		umount /proc/fs/nfsd
	fi
	if [[ -n $nonlocal_original ]]; then
		sysctl -q -w "net.ipv4.ip_nonlocal_bind=$nonlocal_original"
	fi
	for interface in "${touched_interfaces[@]}"; do
		if [[ -e /sys/class/net/$interface ]]; then
			ip address del "$host_cidr" dev "$interface" 2>/dev/null
			nmcli device set "$interface" managed yes 2>/dev/null
		fi
		# The gadget can disappear before cleanup runs, but firewalld keeps
		# the runtime interface assignment until it is removed explicitly.
		firewall-cmd --zone="$firewall_zone" \
			--remove-interface="$interface" >/dev/null 2>&1
	done
	if [[ $allow_rule_added == 1 ]]; then
		firewall-cmd --zone="$firewall_zone" \
			--remove-rich-rule="$nfs_allow_rule" >/dev/null 2>&1
	fi
	if [[ $drop_rules_added == 1 ]]; then
		for zone in "${protected_zones[@]}"; do
			firewall-cmd --zone="$zone" \
				--remove-rich-rule="$nfs_drop_rule" >/dev/null 2>&1
			firewall-cmd --zone="$zone" \
				--remove-rich-rule="$mountd_tcp_drop_rule" >/dev/null 2>&1
			firewall-cmd --zone="$zone" \
				--remove-rich-rule="$mountd_udp_drop_rule" >/dev/null 2>&1
		done
	fi
	echo 'INFO network-root NFS and runtime firewall state removed'
}
trap cleanup EXIT
trap 'exit 130' INT TERM HUP

firewall-cmd --zone="$firewall_zone" \
	--add-rich-rule="$nfs_allow_rule" >/dev/null
allow_rule_added=1
drop_rules_added=1
for zone in "${protected_zones[@]}"; do
	firewall-cmd --zone="$zone" \
		--add-rich-rule="$nfs_drop_rule" >/dev/null
	firewall-cmd --zone="$zone" \
		--add-rich-rule="$mountd_tcp_drop_rule" >/dev/null
	firewall-cmd --zone="$zone" \
		--add-rich-rule="$mountd_udp_drop_rule" >/dev/null
done

install -d -m 0755 "$export_mount"
verify_deployment_export
mount --bind "$root" "$export_mount"
bind_mounted=1
mount -o remount,bind,ro,nodev,nosuid "$export_mount"
findmnt -n -o OPTIONS --target "$export_mount" |
	grep -Eq '(^|,)ro(,|$)'
findmnt -n -o OPTIONS --target "$export_mount" |
	grep -Eq '(^|,)nodev(,|$)'
findmnt -n -o OPTIONS --target "$export_mount" |
	grep -Eq '(^|,)nosuid(,|$)'
if [[ -n $expected_package_sha256 ]]; then
	verify_deployment_export
	python3 -B "$headless_verifier" verify-root "$export_mount" \
		"$deployment_manifest"
fi

if ! mountpoint -q /proc/fs/nfsd; then
	mkdir -p /proc/fs/nfsd
	mount -t nfsd nfsd /proc/fs/nfsd
	nfsd_mounted=1
fi
nonlocal_original=$(sysctl -n net.ipv4.ip_nonlocal_bind)
sysctl -q -w net.ipv4.ip_nonlocal_bind=1

rpc.mountd --foreground --no-nfs-version 2 --no-nfs-version 3 \
	--port "$mountd_port" --num-threads 1 &
mountd_pid=$!
sleep 1
kill -0 "$mountd_pid"

export_active=1
exportfs -i -o ro,fsid=0,sync,no_subtree_check,no_root_squash \
	"$phone_ip:$export_mount"
rpc.nfsd --host "$host_ip" --port 2049 --tcp --no-udp \
	--no-nfs-version 3 --no-nfs-version 4.0 --no-nfs-version 4.1 \
	--nfs-version 4.2 --grace-time "$grace_time" \
	--lease-time "$lease_time" 4
nfsd_started=1

grep -q -- '-3' /proc/fs/nfsd/versions
grep -q -- '+4.2' /proc/fs/nfsd/versions
[[ $(< /proc/fs/nfsd/nfsv4gracetime) == "$grace_time" ]]
[[ $(< /proc/fs/nfsd/nfsv4leasetime) == "$lease_time" ]]
[[ -r /proc/fs/nfsd/v4_end_grace ]]
grace_deadline=$(( $(date +%s) + grace_time + 5 ))
while [[ $(< /proc/fs/nfsd/v4_end_grace) != Y ]] &&
	(( $(date +%s) < grace_deadline )); do
	sleep 1
done
[[ $(< /proc/fs/nfsd/v4_end_grace) == Y ]] ||
	fail 'NFSv4 server grace period did not end'
mapfile -t nfs_listeners < <(
	ss -H -lnt4 'sport = :2049' | awk '{ print $4 }'
)
[[ ${#nfs_listeners[@]} == 1 &&
	${nfs_listeners[0]} == "$host_ip:2049" ]] ||
	fail 'NFS listener is not restricted to the USB host address'
export_listing=$(exportfs -v)
[[ $(grep -Fc "$export_mount" <<<"$export_listing") == 1 ]]
[[ $(grep -Fc "$phone_ip" <<<"$export_listing") == 1 ]]
grep -Fq 'fsid=0' <<<"$export_listing"
grep -Eq '(^|[,(])ro([,)]|$)' <<<"$export_listing"
grep -Fq 'no_root_squash' <<<"$export_listing"
# The target NCM gadget cannot exist until recovery commits kexec. This marker
# attests pre-COMMIT server/export readiness only; publishing it after target
# interface discovery would deadlock the transition. The post-COMMIT loop
# admits and configures only the exact target gadget, while the target's
# independent watchdog bounds an NFS-mount failure.
if [[ -n $handoff_token ]]; then
	handoff_marker_temp=$(mktemp \
		/run/.rog5-network-root-nfs-ready.XXXXXX)
	if [[ -n $expected_package_sha256 ]]; then
		[[ $(sha256sum "$deployment_manifest" | awk '{ print $1 }') == \
			"$expected_package_sha256" ]] ||
			fail 'deployment package changed before NFS handoff'
		printf '%s\n' \
			'format=rog5-nfs-handoff-v2' \
			'profile=headless-ssh-deployment-v3' \
			"token=$handoff_token" \
			"listener=$host_ip:2049" \
			'versions=4.2-only' \
			"export_root=$root" \
			"package_sha256=$expected_package_sha256" \
			>"$handoff_marker_temp"
	else
		printf '%s\n' \
			'format=rog5-nfs-handoff-v1' \
			"token=$handoff_token" \
			"listener=$host_ip:2049" \
			'versions=4.2-only' \
			"export_root=$root" >"$handoff_marker_temp"
	fi
	chmod 0444 "$handoff_marker_temp"
	ln "$handoff_marker_temp" "$handoff_marker"
	handoff_marker_created=1
	rm -f -- "$handoff_marker_temp"
	handoff_marker_temp=
fi

find_target_interface() {
	local interface properties
	for path in /sys/class/net/*; do
		[[ -e $path ]] || continue
		interface=${path##*/}
		properties=$(udevadm info --query=property --path="$path" 2>/dev/null ||
			true)
		grep -qx 'ID_VENDOR_ID=1d6b' <<<"$properties" || continue
		grep -qx 'ID_MODEL_ID=0104' <<<"$properties" || continue
		grep -qx 'ID_MODEL=ROG5_network_root' <<<"$properties" || continue
		grep -qx 'ID_NET_DRIVER=cdc_ncm' <<<"$properties" || continue
		printf '%s\n' "$interface"
		return
	done
}

configure_target_interface() {
	local interface=$1 current zone known=0
	for current in "${touched_interfaces[@]}"; do
		[[ $current != "$interface" ]] || known=1
	done
	((known == 1)) || touched_interfaces+=("$interface")
	nmcli device set "$interface" managed no 2>/dev/null || true
	ip link set "$interface" up
	if ! ip -4 -o address show dev "$interface" |
		awk -v cidr="$host_cidr" '$4 == cidr { found=1 }
			END { exit !found }'; then
		while read -r current; do
			[[ -n $current ]] || continue
			ip address del "$current" dev "$interface"
		done < <(
			ip -4 -o address show dev "$interface" |
				awk -v ip="$host_ip" '{
					split($4, part, "/")
					if (part[1] == ip) print $4
				}'
		)
		ip address add "$host_cidr" dev "$interface"
	fi
	zone=$(firewall-cmd --get-zone-of-interface="$interface" 2>/dev/null ||
		true)
	if [[ $zone != "$firewall_zone" ]]; then
		firewall-cmd --zone="$firewall_zone" \
			--change-interface="$interface" >/dev/null
	fi
}

echo "PASS restricted NFSv4.2 export ready; waiting for exact USB gadget"
deadline=$(( $(date +%s) + serve_timeout ))
target_seen=0
absent_since=0
while (( $(date +%s) < deadline )); do
	target_interface=$(find_target_interface || true)
	if [[ -n $target_interface ]]; then
		if [[ $target_seen == 0 ]]; then
			[[ -e /sys/class/net/$target_interface ]] || continue
			configure_target_interface "$target_interface"
			echo "PASS exact network-root USB link ready on $target_interface"
			target_seen=1
		fi
		absent_since=0
	elif [[ $target_seen == 1 ]]; then
		if [[ $absent_since == 0 ]]; then
			absent_since=$(date +%s)
		elif (( $(date +%s) - absent_since >= 15 )); then
			echo 'PASS network-root gadget departed; ending attended export'
			exit 0
		fi
	fi
	sleep 1
done

fail 'attended NFS window expired'
