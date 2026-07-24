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
grep -Fq 'PASS prepared network-root export' "$verify"

for contract in \
	'169.254.77.1' \
	'169.254.77.2' \
	'ROG5_network_root' \
	'ID_NET_DRIVER=cdc_ncm' \
	'--host "$host_ip"' \
	'--no-nfs-version 3' \
	'--nfs-version 4.2' \
	'ro,fsid=0,sync,no_subtree_check,no_root_squash' \
	'mount --bind "$root" "$export_mount"' \
	'remount,bind,ro,nodev,nosuid' \
	'trap cleanup EXIT' \
	'--new-zone="$firewall_zone"' \
	'--delete-zone="$firewall_zone"'; do
	grep -Fq -- "$contract" "$serve" || {
		echo "FAIL network-root host contract missing: $contract" >&2
		exit 1
	}
done

if grep -Eq -- '--permanent|/etc/exports|(^|[[:space:]])\*\(|no_root_squash.*\*' \
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
