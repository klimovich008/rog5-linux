#!/bin/sh
# shellcheck disable=SC2016
set -eu

repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)
target=$repo/scripts/device/inspect-persistent-layout.sh

[ -x "$target" ] || {
	echo 'FAIL missing persistent layout inspector' >&2
	exit 1
}

stage=$(mktemp -d)
trap 'rm -rf "$stage"' EXIT HUP INT TERM
sys=$stage/sys/class/block
mounts=$stage/proc/mounts
cmdline=$stage/proc/cmdline
root=$stage/root
mkdir -p "$sys/sda" "$sys/sde" "$stage/proc" "$root" "$stage/bin"
printf '%s\n' 494927872 >"$sys/sda/size"
printf '%s\n' 4718592 >"$sys/sde/size"
printf '%s\n' marker >"$root/.rog5-linux-root"
printf '/dev/sda23 %s ext4 rw,relatime 0 0\n' "$root" >"$mounts"
printf '%s\n' 'console=tty0 androidboot.slot_suffix=_b quiet' >"$cmdline"

partition() {
	name=$1 number=$2 start=$3 size=$4 label=$5
	path=$sys/$name
	mkdir -p "$path"
	printf '%s\n' "$number" >"$path/partition"
	printf '%s\n' "$start" >"$path/start"
	printf '%s\n' "$size" >"$path/size"
	printf 'DEVNAME=%s\nPARTNAME=%s\n' "$name" "$label" >"$path/uevent"
}

partition sda19 19 4108352 14680064 super
partition sda22 22 18788672 32768 metadata
partition sda23 23 18821440 476106392 userdata
partition sde11 11 688176 196608 boot_a
partition sde14 14 885200 128 vbmeta_a
partition sde23 23 1482168 196608 vendor_boot_a
partition sde35 35 2367416 196608 boot_b
partition sde38 38 2564440 128 vbmeta_b
partition sde47 47 3161408 196608 vendor_boot_b

printf '%s\n' \
	'#!/bin/sh' \
	'set -eu' \
	'printf "%s\n" "Filesystem 1024-blocks Used Available Capacity Mounted on"' \
	'printf "/dev/sda23 250000000 50000000 %s 20%% %s\n" "${MOCK_FREE_KIB:?}" "${1:?}"' \
	>"$stage/bin/df"
chmod 0755 "$stage/bin/df"

run_inspector() {
	PATH="$stage/bin:$PATH" MOCK_FREE_KIB=${MOCK_FREE_KIB:-200000000} \
		"$target" "$sys" "$mounts" "$cmdline" "$root"
}

expect_fail() {
	label=$1
	shift
	if "$@" >/dev/null 2>&1; then
		echo "FAIL accepted persistent layout mutation: $label" >&2
		exit 1
	fi
}

output=$(run_inspector)
printf '%s\n' "$output" | grep -Fxq \
	'PASS persistent layout mode=fixture slot=_b protected_slot=_b root=/dev/sda23 filesystem=ext4 userdata_bytes=243766472704 free_kib=200000000 plan=no-repartition'

printf '%s\n' 476106391 >"$sys/sda23/size"
expect_fail userdata-size run_inspector
printf '%s\n' 476106392 >"$sys/sda23/size"

printf 'DEVNAME=sda23\nPARTNAME=data\n' >"$sys/sda23/uevent"
expect_fail userdata-label run_inspector
printf 'DEVNAME=sda23\nPARTNAME=userdata\n' >"$sys/sda23/uevent"

printf '/dev/sda22 %s ext4 rw,relatime 0 0\n' "$root" >"$mounts"
expect_fail wrong-root run_inspector
printf '/dev/sda23 %s ext4 rw,relatime 0 0\n' "$root" >"$mounts"

printf '%s\n' 'console=tty0 androidboot.slot_suffix=_c quiet' >"$cmdline"
expect_fail wrong-slot run_inspector
printf '%s\n' 'console=tty0 androidboot.slot_suffix=_b quiet' >"$cmdline"

printf '/dev/sda23 %s ext4 rw,relatime 0 0\n/dev/sde35 /boot ext4 ro 0 0\n' \
	"$root" >"$mounts"
expect_fail mounted-active-boot run_inspector
printf '/dev/sda23 %s ext4 rw,relatime 0 0\n' "$root" >"$mounts"

MOCK_FREE_KIB=16777215 expect_fail low-free-space run_inspector

rm "$root/.rog5-linux-root"
expect_fail missing-fallback-marker run_inspector
printf '%s\n' marker >"$root/.rog5-linux-root"

printf 'DEVNAME=sde35\nPARTNAME=boot_a\n' >"$sys/sde35/uevent"
expect_fail changed-boot-label run_inspector

if grep -Eq \
	'(^|[;&|[:space:]])(mount|umount|mkfs|mke2fs|resize2fs|wipefs|sgdisk|parted|fdisk|dd|fastboot|adb|reboot|kexec)([;&|[:space:]]|$)|/proc/sysrq-trigger' \
	"$target"
then
	echo 'FAIL persistent layout inspector contains a mutation command' >&2
	exit 1
fi

echo 'PASS persistent layout inspector is exact-map, no-repartition, slot-aware, mutation-tested, and read-only'
