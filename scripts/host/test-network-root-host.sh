#!/bin/sh
set -eu

repo=$(CDPATH= cd -- "$(dirname "$0")/../.." && pwd)
prepare=$repo/scripts/host/prepare-network-root-export.sh
verify=$repo/scripts/host/verify-network-root-export.sh
serve=$repo/scripts/host/serve-network-root.sh

for script in "$prepare" "$verify" "$serve"; do
	[ -x "$script" ] || {
		echo "FAIL missing executable network-root host tool: $script" >&2
		exit 1
	}
	bash -n "$script"
done

grep -Fq 'rog5-arch-plasma-network-root-7.1.4.tar.gz' "$prepare"
grep -Fq 'bsdtar --acls --xattrs --fflags -xpf' "$prepare"
grep -Fq 'refusing existing export root' "$prepare"
grep -Fq 'verify-network-root-export.sh' "$prepare"

grep -Fq '7.1.4-g7a5cef0db479' "$verify"
grep -Fq 'modules-7.1.4-network-root.tar.gz' "$verify"
grep -Fq 'unmanaged-devices=interface-name:usb0' "$verify"
grep -Fq 'nfs_export_all_ro' "$verify"
grep -Fq 'ssh_host_ed25519_key' "$verify"
grep -Fq 'ssh-keygen -y' "$verify"
grep -Fq '10-rog5-sshd.conf' "$verify"
grep -Fq 'PASS prepared network-root export' "$verify"
grep -Fq "ssh-keygen -q -t ed25519 -N ''" "$prepare"
grep -Fq '10-rog5-sshd.conf' "$prepare"
grep -Fqx 'HostKey /etc/ssh/ssh_host_ed25519_key' \
	"$repo/packaging/arch/10-rog5-sshd.conf"

for contract in \
	'169.254.77.1' \
	'169.254.77.2' \
	'ROG5_network_root' \
	'ID_NET_DRIVER=cdc_ncm' \
	'--host "$host_ip"' \
	'--no-nfs-version 3' \
	'--nfs-version 4.2' \
	'--grace-time "$grace_time"' \
	'--lease-time "$lease_time"' \
	'ROG5_NFS_TIMEOUT:-900' \
	'serve_timeout <= 86400' \
	'/var/lib/rog5-network-root-v1)' \
	'/var/lib/rog5-network-root-a660-firmware-request-only-v4)' \
	'verify-a660-firmware-request-only-export.sh' \
	'/proc/fs/nfsd/v4_end_grace' \
	'ro,fsid=0,sync,no_subtree_check,no_root_squash' \
	'mount --bind "$root" "$export_mount"' \
	'remount,bind,ro,nodev,nosuid' \
	'etab=/var/lib/nfs/etab' \
	'mkdir -p /proc/fs/nfsd' \
	'trap cleanup EXIT' \
	'firewall_zone=drop' \
	'$1 == "target:"' \
	'--add-rich-rule="$nfs_allow_rule"' \
	'--remove-rich-rule="$nfs_allow_rule"' \
	'export_listing=$(exportfs -v)' \
	'grep -Fc "$export_mount"' \
	'grep -Fc "$phone_ip"'; do
	grep -Fq -- "$contract" "$serve" || {
		echo "FAIL network-root host contract missing: $contract" >&2
		exit 1
	}
done

for consumed in \
	/var/lib/rog5-network-root-adreno-smmu-v20 \
	/var/lib/rog5-network-root-adreno-smmu-v21 \
	/var/lib/rog5-network-root-a660-registration \
	/var/lib/rog5-network-root-a660-registration-v2 \
	/var/lib/rog5-network-root-a660-registration-v3
do
	if grep -Fq "$consumed)" "$serve"; then
		echo "FAIL network-root host still allowlists consumed root: $consumed" >&2
		exit 1
	fi
done

export_flag_line=$(grep -n '^export_active=1$' "$serve" |
	cut -d: -f1)
export_line=$(grep -n '^exportfs -i -o ' "$serve" |
	cut -d: -f1)
[ "$export_flag_line" -lt "$export_line" ]
grep -Fq 'exportfs -u "$phone_ip:$export_mount"' "$serve"
target_seen_line=$(grep -n 'if \[\[ \$target_seen == 0 \]\]; then' "$serve" |
	tail -n1 | cut -d: -f1)
configure_line=$(grep -n 'configure_target_interface "$target_interface"' "$serve" |
	tail -n1 | cut -d: -f1)
target_mark_line=$(grep -n 'target_seen=1' "$serve" | tail -n1 | cut -d: -f1)
[ "$target_seen_line" -lt "$configure_line" ]
[ "$configure_line" -lt "$target_mark_line" ]

cleanup_guard_line=$(grep -n \
	'if \[\[ -e /sys/class/net/\$interface \]\]; then' "$serve" |
	head -n1 | cut -d: -f1)
cleanup_guard_end_line=$(awk -v start="$cleanup_guard_line" \
	'NR > start && /^[[:space:]]*fi$/ { print NR; exit }' "$serve")
cleanup_remove_line=$(grep -n -- '--remove-interface="$interface"' "$serve" |
	head -n1 | cut -d: -f1)
[ "$cleanup_guard_line" -lt "$cleanup_guard_end_line" ]
[ "$cleanup_guard_end_line" -lt "$cleanup_remove_line" ]

if grep -Eq -- '--permanent|--new-zone|/etc/exports|(^|[[:space:]])\*\(|no_root_squash.*\*' \
	"$prepare" "$verify" "$serve"; then
	echo 'FAIL network-root host tools contain a persistent or broad export' >&2
	exit 1
fi
if grep -Eq '(^|[[:space:]])fastboot[[:space:]]+flash|(^|[[:space:]])dd[[:space:]].*of=/dev/' \
	"$prepare" "$verify" "$serve"; then
	echo 'FAIL network-root host tools contain a phone-storage write command' >&2
	exit 1
fi

echo 'PASS host gate is exact-peer, runtime-only, read-only, and fail-closed'
