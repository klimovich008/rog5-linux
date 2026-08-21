#!/bin/sh
set -eu

dtb=${1:?usage: verify-persistent-root-power-usb-dtb.sh BOARD_DTB}
repo=$(CDPATH='' cd -- "$(dirname -- "$0")/../.." && pwd -P)

"$repo/scripts/device/verify-power-usb-active-dtb.sh" "$dtb" >/dev/null

for node in /soc@0/ufshc@1d84000 /soc@0/phy@1d87000 \
	/soc@0/usb@a6f8800 /soc@0/phy@88e3000; do
	[ "$(fdtget -t s "$dtb" "$node" status 2>/dev/null)" = okay ] || {
		echo "FAIL composed DTB does not enable $node" >&2
		exit 1
	}
done
for node in /soc@0/phy@88e8000 /soc@0/usb@a8f8800; do
	[ "$(fdtget -t s "$dtb" "$node" status 2>/dev/null)" = disabled ] || {
		echo "FAIL composed DTB unexpectedly enables $node" >&2
		exit 1
	}
done

dwc3=/soc@0/usb@a6f8800/usb@a600000
[ "$(fdtget -t s "$dtb" "$dwc3" dr_mode)" = peripheral ]
[ "$(fdtget -t s "$dtb" "$dwc3" maximum-speed)" = high-speed ]
[ "$(fdtget -t s "$dtb" "$dwc3" phy-names)" = usb2-phy ]
[ "$(fdtget -t x "$dtb" "$dwc3" phys | wc -w)" -eq 1 ]

echo 'PASS composed DTB preserves power/UCSI memory and enables read-only UFS plus side USB2 only'
