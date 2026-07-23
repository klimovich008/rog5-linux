#!/bin/sh
set -eu

base=${1:?usage: build-recovery-candidate-dtb.sh BASE_DTB OVERLAY_SOURCE OUTPUT}
overlay_source=${2:?missing overlay source}
output=${3:?missing output}
[ -s "$base" ] && [ -r "$overlay_source" ] || { echo 'FAIL missing DTB input' >&2; exit 1; }

[ "$(grep -c 'status = "okay";' "$overlay_source")" -eq 2 ]
[ "$(grep -c '^&' "$overlay_source")" -eq 3 ]
for label in usb_1 usb_1_dwc3 usb_1_hsphy; do
	grep -q "^&$label {" "$overlay_source"
done
! grep -q '^&ufs_mem_' "$overlay_source"
! grep -q '^&usb_1_qmpphy' "$overlay_source"
! grep -q '^&usb_2' "$overlay_source"
! grep -q 'bootargs\|reg =\|supply =\|memory-region' "$overlay_source"

stage=$(mktemp -d)
trap 'rm -rf "$stage"' EXIT
dtc -q -@ -I dts -O dtb -o "$stage/recovery.dtbo" "$overlay_source"
mkdir -p "$(dirname "$output")"
fdtoverlay -i "$base" -o "$output.tmp" "$stage/recovery.dtbo"
mv "$output.tmp" "$output"
dtc -q -I dtb -O dts -o /dev/null "$output"

for node in /soc@0/usb@a6f8800 /soc@0/phy@88e3000; do
	[ "$(fdtget -t s "$output" "$node" status)" = okay ]
done
[ "$(fdtget -t s "$output" /soc@0/ufshc@1d84000 status)" = disabled ]
[ "$(fdtget -t s "$output" /soc@0/phy@1d87000 status)" = disabled ]
[ "$(fdtget -t s "$output" /soc@0/phy@88e8000 status)" = disabled ]
[ "$(fdtget -t s "$output" /soc@0/usb@a8f8800 status)" = disabled ]
usb_dwc3=/soc@0/usb@a6f8800/usb@a600000
[ "$(fdtget -t s "$output" "$usb_dwc3" dr_mode)" = peripheral ]
[ "$(fdtget -t s "$output" "$usb_dwc3" maximum-speed)" = high-speed ]
[ "$(fdtget -t s "$output" "$usb_dwc3" phy-names)" = usb2-phy ]
[ "$(fdtget -t x "$output" "$usb_dwc3" phys | wc -w)" = 1 ]
fdtget "$output" /soc@0/usb@a6f8800 qcom,select-utmi-as-pipe-clk >/dev/null
[ "$(fdtget -t x "$output" /memory@80000000 reg)" = \
	'0 80000000 0 37100000 2 0 1 80000000 0 c0000000 1 40000000 0 b9500000 0 0' ]

sha256sum "$output"
echo 'PASS kexec-only USB2 recovery DTB; storage, SuperSpeed, and secondary USB disabled'
