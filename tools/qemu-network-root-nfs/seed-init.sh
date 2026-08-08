#!/bin/sh
set -eu

fail() {
	printf 'FAIL QEMU NFS fixture seed stage=%s\n' "$1" >&2
	poweroff -f
	while :; do sleep 60; done
}

mount -t sysfs sysfs /sys || fail sys
mkdir -p /mnt/seed
mount -t nfs4 \
	-o vers=4.2,proto=tcp,port=2049,rw,nolock,soft,timeo=10,retrans=1 \
	169.254.77.1:/ /mnt/seed || fail mount
mkdir -p /mnt/seed/sbin || fail mkdir
printf '#!/bin/sh\nexit 127\n' >/mnt/seed/sbin/init || fail write
chmod 0755 /mnt/seed/sbin/init || fail chmod
sync
umount /mnt/seed || fail umount
printf '%s\n' 'PASS QEMU NFS fixture seeded over NFSv4.2'
poweroff -f
while :; do sleep 60; done
