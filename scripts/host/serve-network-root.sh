#!/usr/bin/env bash
set -euo pipefail

fail() {
	echo "FAIL $*" >&2
	exit 1
}

repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
root=${1:-/var/lib/rog5-network-root-v1}
host_ip=169.254.77.1
phone_ip=169.254.77.2
host_cidr=$host_ip/30
firewall_zone=drop
export_mount=/run/rog5-network-root-export
mountd_port=32767
grace_time=10
lease_time=10
serve_timeout=${ROG5_NFS_TIMEOUT:-900}

[[ $EUID == 0 ]] || fail 'run through PolicyKit; do not share a sudo password'
[[ $serve_timeout =~ ^[0-9]+$ ]] &&
	((serve_timeout >= 60 && serve_timeout <= 86400)) ||
	fail 'ROG5_NFS_TIMEOUT must be between 60 and 86400 seconds'
for command in awk date exportfs firewall-cmd findmnt grep install ip mount \
	mkdir mountpoint nmcli pgrep realpath rpc.mountd rpc.nfsd ss sysctl udevadm \
	stat systemctl tr umount; do
	command -v "$command" >/dev/null || fail "missing host command: $command"
done
[[ -d $root && ! -L $root ]] || fail 'missing prepared export root'
root=$(realpath -e "$root")
case $root in
	/var/lib/rog5-network-root-v1)
		"$repo/scripts/host/verify-network-root-export.sh" "$root"
		;;
	/var/lib/rog5-network-root-a660-ucode-allocation-v5)
		[[ ${ALLOW_MAINLINE_A660_UCODE_ALLOCATION_NFS:-} == 1 ]] ||
			fail 'set ALLOW_MAINLINE_A660_UCODE_ALLOCATION_NFS=1 for the attended v5 window'
		"$repo/scripts/host/verify-a660-ucode-allocation-export.sh" \
			"$root" /var/lib/rog5-network-root-a660-registration-v3
		;;
	*)
		fail 'unexpected export root'
		;;
esac

etab=/var/lib/nfs/etab
[[ -e $etab ]] || install -m 0644 /dev/null "$etab"
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
mount --bind "$root" "$export_mount"
bind_mounted=1
mount -o remount,bind,ro,nodev,nosuid "$export_mount"
findmnt -n -o OPTIONS --target "$export_mount" |
	grep -Eq '(^|,)ro(,|$)'
findmnt -n -o OPTIONS --target "$export_mount" |
	grep -Eq '(^|,)nodev(,|$)'
findmnt -n -o OPTIONS --target "$export_mount" |
	grep -Eq '(^|,)nosuid(,|$)'

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
