#!/bin/sh
set -eu

repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd -P)
executor=$repo/scripts/device/storage-layout-stage2

fail() {
	echo "FAIL $*" >&2
	exit 1
}

for command in awk chmod dumpe2fs mkdir mkfs.ext4 mktemp sed truncate; do
	command -v "$command" >/dev/null ||
		fail "missing Stage-2 fixture command: $command"
done
[ -x "$executor" ] || fail 'Stage-2 executor is absent'

work=$(mktemp -d)
cleanup() {
	rm -rf -- "$work"
}
trap cleanup EXIT HUP INT TERM
functions=$work/functions.sh
awk '/^if ! exec 3<>/{ exit } { print }' "$executor" >"$functions"
chmod 0600 "$functions"
fixture=$work/exact.ext4
uuid=598a876b-a8db-4859-a01a-1b864b0a87f4
truncate -s 64M "$fixture"
mkfs.ext4 -q -F -b 4096 -m 1 -L ROG5_ARCH_A -U "$uuid" "$fixture"

(
	. "$functions"
	verify_ext4 "$fixture" "$uuid" 16384 ROG5_ARCH_A "$work/exact.log"
) || fail 'exact clean ext4 fixture was rejected'
(
	. "$functions"
	verify_ext4 "$fixture" 00000000-0000-0000-0000-000000000000 \
		16384 ROG5_ARCH_A "$work/wrong-uuid.log"
) && fail 'wrong filesystem UUID was accepted'
(
	. "$functions"
	verify_ext4 "$fixture" "$uuid" 16383 ROG5_ARCH_A "$work/wrong-blocks.log"
) && fail 'wrong filesystem block count was accepted'
(
	. "$functions"
	verify_ext4 "$fixture" "$uuid" 16384 rog5-linux "$work/wrong-label.log"
) && fail 'wrong filesystem label was accepted'

empty_signature=$work/empty-signature.log
if (
	. "$functions"
	blkid() { return 0; }
	capture_bounded_signature /dev/null "$empty_signature"
); then
	fail 'zero-output successful blkid was accepted as a signature'
fi
[ -f "$empty_signature" ] && [ ! -s "$empty_signature" ] ||
	fail 'zero-output blkid fixture did not remain an empty bounded capture'

sysfs=$work/sys
mkdir -p "$sysfs/class/power_supply/vendor-battery" \
	"$sysfs/class/thermal/thermal_zone0"
printf 'Battery\n' >"$sysfs/class/power_supply/vendor-battery/type"
printf '320\n' >"$sysfs/class/power_supply/vendor-battery/temp"
printf '41000\n' >"$sysfs/class/thermal/thermal_zone0/temp"
(
	. "$functions"
	verify_safe_temperature "$sysfs"
) || fail 'safe type-discovered battery and thermal fixture was rejected'

mkdir -p "$sysfs/class/power_supply/second-battery"
printf 'Battery\n' >"$sysfs/class/power_supply/second-battery/type"
printf '330\n' >"$sysfs/class/power_supply/second-battery/temp"
(
	. "$functions"
	if verify_safe_temperature "$sysfs"; then
		exit 1
	fi
	[ "$temperature_reason" = battery_ambiguous ]
) || fail 'multiple Battery supplies were not classified exactly'
rm -rf "$sysfs/class/power_supply/second-battery"

printf '70000\n' >"$sysfs/class/thermal/thermal_zone0/temp"
(
	. "$functions"
	if verify_safe_temperature "$sysfs"; then
		exit 1
	fi
	[ "$temperature_reason" = thermal_unsafe ]
) || fail 'unsafe thermal fixture was not classified exactly'

echo 'PASS Stage-2 runtime covers zero-output blkid, exact ext4, and type-discovered temperature gates'
