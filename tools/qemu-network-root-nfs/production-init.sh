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

verify_sha256() {
	expected=$1
	path=$2
	record=$(sha256sum "$path") || return 1
	[ "${record%% *}" = "$expected" ]
}

grep -q ' /proc proc ' /proc/mounts 2>/dev/null ||
	mount -t proc proc /proc || fail mount-proc
grep -q ' /sys sysfs ' /proc/mounts 2>/dev/null ||
	mount -t sysfs sysfs /sys || fail mount-sysfs
grep -q ' /dev devtmpfs ' /proc/mounts 2>/dev/null ||
	mount -t devtmpfs devtmpfs /dev || fail mount-devtmpfs
grep -q ' /run tmpfs ' /proc/mounts 2>/dev/null ||
	mount -t tmpfs -o mode=0755,size=8m tmpfs /run || fail mount-run
mkdir -p /sys/fs/cgroup || fail cgroup-directory
grep -q ' /sys/fs/cgroup cgroup2 ' /proc/mounts 2>/dev/null ||
	mount -t cgroup2 cgroup2 /sys/fs/cgroup || fail mount-cgroup2

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

directory_delegations=$(cat /sys/module/nfsv4/parameters/directory_delegations) ||
	fail directory-delegations-read
[ "$directory_delegations" = N ] || fail directory-delegations-enabled
printf 'PASS QEMU disabled unsupported NFS directory delegations\n'
nfs4_disable_idmapping=$(cat /sys/module/nfs/parameters/nfs4_disable_idmapping) ||
	fail idmapping-read
[ "$nfs4_disable_idmapping" = Y ] || fail idmapping-enabled
printf 'PASS QEMU pinned numeric NFSv4 owner mapping\n'

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
[ -x "$network_newroot/usr/bin/rog5-qemu-diagnostic-handoff" ] ||
	fail systemd-proof-helper-missing
verify_sha256 dad2b1339d6b9178f83ef96791e5c020604e16ec7921e6eaf89d3b38eec478d0 \
	"$network_newroot/usr/lib/systemd/systemd" || fail systemd-hash
verify_sha256 b1f2738bdb51e6419d7062f96c8a44bd68853698dc5ac624fa6ca9f9b03d456d \
	"$network_newroot/usr/lib/ld-linux-aarch64.so.1" || fail loader-hash
verify_sha256 6ab264fb4e8df9942b0fb75b48fcd5c30b2f081d8dfaa6c25d7be1d3fce5b2ab \
	"$network_newroot/usr/lib/libc.so.6" || fail libc-hash

printf '%s\n' \
	'PASS production network-root shell assembled NFSv4.2 plus OverlayFS root'

diagnostic_mode=0
handoff_newroot=$network_newroot
handoff_root_ro=$network_root_ro
handoff_state=$network_root_state
handoff_dev=/dev
handoff_sys=/sys
handoff_proc=/proc
handoff_run=/run
prepare_shutdown_root || fail exitrd
handoff_network_root || fail handoff
exec switch_root "$handoff_newroot" /sbin/init
fail switch-root-returned
