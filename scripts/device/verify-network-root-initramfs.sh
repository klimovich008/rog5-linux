#!/bin/sh
set -eu

archive=${1:?usage: verify-network-root-initramfs.sh INITRAMFS}
repo=$(CDPATH= cd -- "$(dirname "$0")/../.." && pwd)
[ -s "$archive" ] || { echo 'FAIL missing network-root initramfs' >&2; exit 1; }
gzip -t "$archive"

stage=$(mktemp -d)
trap 'rm -rf "$stage"' EXIT INT TERM
gzip -dc "$archive" |
	(cd "$stage" && cpio -idm --quiet --no-absolute-filenames)

cmp "$stage/init" "$repo/initramfs/network-root-init"
sh -n "$stage/init"

for path in \
	bin/sh \
	bin/mount \
	bin/mountpoint \
	bin/sleep \
	sbin/ip \
	sbin/mdev \
	sbin/reboot \
	sbin/switch_root \
	usr/bin/awk \
	usr/bin/find \
	usr/bin/readlink \
	usr/bin/setsid; do
	[ -e "$stage/$path" ] || [ -L "$stage/$path" ] || {
		echo "FAIL initramfs command missing: /$path" >&2
		exit 1
	}
done

[ ! -e "$stage/root/.ssh/authorized_keys" ]
[ -z "$(find "$stage/etc/ssh" -maxdepth 1 -type f -name 'ssh_host_*' \
	-print -quit 2>/dev/null)" ]
[ ! -s "$stage/etc/machine-id" ]
[ ! -s "$stage/var/lib/dbus/machine-id" ]
! find "$stage" -type f -exec grep -Il 'BEGIN .*PRIVATE KEY' {} + |
	grep -q .

echo 'PASS credential-free network-root initramfs and required BusyBox applets'
