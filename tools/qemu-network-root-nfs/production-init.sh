#!/bin/sh
set -u

PATH=/sbin:/bin:/usr/sbin:/usr/bin
export PATH

fail() {
	printf 'FAIL production network-root QEMU stage=%s fault=%s\n' \
		"$1" "${diagnostic_fault:-unset}" >&2
	poweroff -f
	while :; do sleep 60; done
}

grep -q ' /proc proc ' /proc/mounts 2>/dev/null ||
	mount -t proc proc /proc || fail mount-proc
grep -q ' /sys sysfs ' /proc/mounts 2>/dev/null ||
	mount -t sysfs sysfs /sys || fail mount-sysfs

interface=
interface_count=0
for candidate in /sys/class/net/*; do
	if [ ! -e "$candidate" ]; then
		printf 'ROG5_QEMU_INTERFACE_CANDIDATE missing %s\n' "$candidate"
		continue
	fi
	candidate=${candidate##*/}
	[ "$candidate" = lo ] && continue
	[ -e "/sys/class/net/$candidate/device" ] || continue
	interface=$candidate
	interface_count=$((interface_count + 1))
done
[ "$interface_count" -eq 1 ] || fail interface-count

ip link set "$interface" down || fail interface-down
ip -4 address flush dev "$interface" || fail address-flush
if [ "$interface" != usb0 ]; then
	ip link set "$interface" name usb0 || fail interface-rename
fi
ip link set usb0 up || fail interface-up
ip address add 169.254.77.2/30 dev usb0 || fail address-add

udc_class_dir=/run/qemu-udc
expected_udc=a600000.dwc3
gadget=/run/qemu-gadget
net_class_dir=/sys/class/net
network_root_ro=/mnt/root-ro
network_root_state=/mnt/state
network_newroot=/newroot
network_mounts=/proc/mounts
diagnostic_mode=1
diagnostic_fault=none
stages=

mkdir -p "$udc_class_dir/$expected_udc" "$gadget" \
	"$network_root_ro" "$network_root_state" "$network_newroot" ||
	fail fixture-directories
printf '%s\n' "$expected_udc" >"$gadget/UDC" || fail fixture-udc

diagnostic_emit() {
	stages="${stages}${stages:+ }$1"
	printf 'ROG5_QEMU_PRODUCTION_STAGE %s\n' "$1"
}

verify_network_root_identity() {
	return 0
}

# This file is generated verbatim from initramfs/network-root-init by the host
# runner. It is data from the production script, not a QEMU implementation.
. /network-functions.sh

if ! mount_network_root; then
	if ! awk -v root="$network_newroot" \
		'$2 == root && $3 == "overlay" { found=1 }
		 END { exit !found }' "$network_mounts"; then
		fail overlay-mount
	fi
	[ -e "$network_root_ro/sbin/init" ] || fail lower-init-missing
	[ -x "$network_root_ro/sbin/init" ] || fail lower-init-not-executable
	[ -e "$network_newroot/sbin/init" ] || fail overlay-init-missing
	[ -x "$network_newroot/sbin/init" ] || fail overlay-init-not-executable
	fail incomplete-root
fi
[ "$stages" = '70 75 80 90 100' ] || fail mount-function-stages
awk -v root="$network_root_ro" \
	'$2 == root && $3 == "nfs4" && $4 ~ /(^|,)ro(,|$)/ { found=1 }
	 END { exit !found }' "$network_mounts" || fail root-not-read-only
if touch "$network_root_ro/must-not-exist" 2>/dev/null; then
	fail read-only-create-succeeded
fi
awk -v root="$network_newroot" \
	'$2 == root && $3 == "overlay" { found=1 }
	 END { exit !found }' "$network_mounts" || fail merged-root-not-overlay
[ -x "$network_newroot/sbin/init" ] || fail merged-root-init-missing
touch "$network_newroot/overlay-write" || fail merged-root-write
[ -e "$network_root_state/upper/overlay-write" ] || fail upper-write-missing
[ ! -e "$network_root_ro/overlay-write" ] || fail lower-root-was-modified

printf '%s\n' \
	'PASS production network-root shell assembled NFSv4.2 plus OverlayFS root'
poweroff -f
while :; do sleep 60; done
