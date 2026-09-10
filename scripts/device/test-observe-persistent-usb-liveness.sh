#!/bin/sh
set -eu

repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)
script=$repo/scripts/device/observe-persistent-usb-liveness.sh

fail() { echo "FAIL $*" >&2; exit 1; }

[ -x "$script" ]
sh -n "$script"

for contract in \
	'state_mount=/persist' \
	'log_dir=$state_mount/var/log/rog5-usb-observer' \
	'udc=/sys/class/udc/a600000.usb' \
	'net=/sys/class/net/usb0' \
	'max_samples=7200' \
	'sync_interval=10' \
	'format=rog5-persistent-usb-liveness-v1' \
	'numeric_or_state() {' \
	'dwc_runtime=$(numeric_or_state "$udc/device/power/runtime_status")' \
	'sync -f "$log"'; do
	grep -Fq "$contract" "$script" || fail "missing observer contract: $contract"
done

for forbidden in fastboot adb sgdisk parted fdisk mkfs blkdiscard wipefs \
	blockdev losetup '/dev/sd' 'rm -rf' 'usbreset' 'modprobe' 'insmod'; do
	! grep -Fq "$forbidden" "$script" || fail "forbidden observer surface: $forbidden"
done

[ "$(grep -Fc 'sync -f "$log"' "$script")" -eq 3 ]
[ "$(grep -Fc 'sleep 1' "$script")" -eq 1 ]
! grep -Eq '^[[:space:]]*\[ .* =$' "$script"

if "$script" invalid >/dev/null 2>&1; then
	fail 'observer accepted an invalid action'
fi
if "$script" >/dev/null 2>&1; then
	fail 'observer accepted missing arguments'
fi

echo 'PASS persistent USB liveness observer is exact-path, bounded, optional-field tolerant, and write-contained'
