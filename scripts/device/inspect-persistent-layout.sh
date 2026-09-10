#!/bin/sh
set -eu

fail() {
	echo "FAIL $*" >&2
	exit 1
}

case $# in
	0)
		mode=live
		sys=/sys/class/block
		mounts=/proc/mounts
		cmdline=/proc/cmdline
		root=/
		;;
	4)
		mode=fixture
		sys=$1
		mounts=$2
		cmdline=$3
		root=$4
		;;
	*)
		fail 'usage: inspect-persistent-layout.sh [SYS_BLOCK MOUNTS CMDLINE ROOT]'
		;;
esac

for command in awk df grep sed tr; do
	command -v "$command" >/dev/null ||
		fail "missing inspection command: $command"
done
case $sys:$mounts:$cmdline:$root in
	/*:/*:/*:/*) ;;
	*) fail 'inspection paths must be absolute' ;;
esac
[ -d "$sys" ] || fail 'block sysfs directory is absent'
[ -r "$mounts" ] || fail 'mount table is unreadable'
[ -r "$cmdline" ] || fail 'kernel command line is unreadable'
[ -d "$root" ] || fail 'fallback root is absent'
[ -f "$root/.rog5-linux-root" ] &&
	[ ! -L "$root/.rog5-linux-root" ] ||
	fail 'fallback root marker is absent or linked'

read_value() {
	file=$1
	label=$2
	[ -r "$file" ] || fail "$label is unreadable"
	value=$(sed -n '1p' "$file")
	case $value in
		''|*[!0-9]*) fail "$label is not an unsigned integer" ;;
	esac
	printf '%s\n' "$value"
}

check_partition() {
	name=$1
	number=$2
	start=$3
	sectors=$4
	label=$5
	path=$sys/$name
	[ -d "$path" ] || fail "missing measured partition: $name"
	[ "$(read_value "$path/partition" "$name partition number")" = "$number" ] ||
		fail "$name partition number changed"
	[ "$(read_value "$path/start" "$name start")" = "$start" ] ||
		fail "$name start changed"
	[ "$(read_value "$path/size" "$name size")" = "$sectors" ] ||
		fail "$name size changed"
	[ -r "$path/uevent" ] || fail "$name uevent is unreadable"
	[ "$(sed -n 's/^DEVNAME=//p' "$path/uevent")" = "$name" ] ||
		fail "$name device identity changed"
	[ "$(sed -n 's/^PARTNAME=//p' "$path/uevent")" = "$label" ] ||
		fail "$name partition label changed"
}

[ "$(read_value "$sys/sda/size" 'primary LUN size')" = 494927872 ] ||
	fail 'primary LUN size changed'
[ "$(read_value "$sys/sde/size" 'boot LUN size')" = 4718592 ] ||
	fail 'boot LUN size changed'
check_partition sda19 19 4108352 14680064 super
check_partition sda22 22 18788672 32768 metadata
check_partition sda23 23 18821440 476106392 userdata
check_partition sde11 11 688176 196608 boot_a
check_partition sde14 14 885200 128 vbmeta_a
check_partition sde23 23 1482168 196608 vendor_boot_a
check_partition sde35 35 2367416 196608 boot_b
check_partition sde38 38 2564440 128 vbmeta_b
check_partition sde47 47 3161408 196608 vendor_boot_b

root_record=$(awk -v root="$root" '
	$2 == root {
		count++
		source=$1
		filesystem=$3
		options=$4
	}
	END {
		if (count != 1)
			exit 1
		print source, filesystem, options
	}
' "$mounts") || fail 'fallback root entry is missing or duplicated'
IFS=' ' read -r root_source filesystem options <<EOF
$root_record
EOF
[ "$root_source" = /dev/sda23 ] ||
	fail 'fallback root is not the measured userdata partition'
[ "$filesystem" = ext4 ] || fail 'fallback root is not ext4'
case ,$options, in
	*,rw,*) ;;
	*) fail 'fallback root is not writable' ;;
esac

if awk '
	$1 == "/dev/sde11" || $1 == "/dev/sde14" ||
	$1 == "/dev/sde23" || $1 == "/dev/sde35" ||
	$1 == "/dev/sde38" || $1 == "/dev/sde47" {
		found=1
	}
	END { exit !found }
' "$mounts"
then
	fail 'a boot-critical partition is unexpectedly mounted'
fi

slot=$(tr ' ' '\n' <"$cmdline" |
	sed -n 's/^androidboot\.slot_suffix=//p')
case $slot in
	_a|_b) ;;
	*) fail 'fallback slot suffix is missing, duplicated, or invalid' ;;
esac

free_kib=$(df -Pk "$root" | awk 'NR == 2 { print $4 }')
case $free_kib in
	''|*[!0-9]*) fail 'fallback free-space value is invalid' ;;
esac
[ "$free_kib" -ge 16777216 ] ||
	fail 'less than 16 GiB is free on userdata'

userdata_bytes=$((476106392 * 512))
printf '%s\n' \
	"PASS persistent layout mode=$mode slot=$slot protected_slot=$slot root=$root_source filesystem=$filesystem userdata_bytes=$userdata_bytes free_kib=$free_kib plan=no-repartition"
