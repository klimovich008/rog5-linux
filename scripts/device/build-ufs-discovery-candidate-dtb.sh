#!/bin/sh
set -eu

base=${1:?usage: build-ufs-discovery-candidate-dtb.sh BASE_DTB OVERLAY_SOURCE OUTPUT}
overlay=${2:?missing overlay source}
output=${3:?missing output}
[ -s "$base" ] && [ -r "$overlay" ] || { echo 'FAIL missing DTB input' >&2; exit 1; }

[ "$(grep -c 'status = "okay";' "$overlay")" -eq 4 ]
[ "$(grep -c '^&' "$overlay")" -eq 5 ]
for label in ufs_mem_hc ufs_mem_phy usb_1 usb_1_dwc3 usb_1_hsphy; do
	grep -q "^&$label {" "$overlay"
done
! grep -q '^&usb_1_qmpphy\|^&usb_2' "$overlay"
! grep -q 'bootargs\|reg =\|supply =\|memory-region\|reset-gpios\|iommus' "$overlay"

stage=$(mktemp -d)
trap 'rm -rf "$stage"' EXIT INT TERM
dtc -q -@ -I dts -O dtb -o "$stage/discovery.dtbo" "$overlay"
mkdir -p "$(dirname "$output")"
fdtoverlay -i "$base" -o "$output.tmp" "$stage/discovery.dtbo"
mv "$output.tmp" "$output"
dtc -q -I dtb -O dts -o /dev/null "$output"

ufs_hc=/soc@0/ufshc@1d84000
ufs_phy=/soc@0/phy@1d87000
for node in "$ufs_hc" "$ufs_phy" /soc@0/usb@a6f8800 /soc@0/phy@88e3000; do
	[ "$(fdtget -t s "$output" "$node" status)" = okay ]
done
for node in /soc@0/phy@88e8000 /soc@0/usb@a8f8800; do
	[ "$(fdtget -t s "$output" "$node" status)" = disabled ]
done

for property in reset-gpios vcc-supply vcc-max-microamp vccq-supply vccq-max-microamp; do
	[ "$(fdtget -t x "$output" "$ufs_hc" "$property")" = \
		"$(fdtget -t x "$base" "$ufs_hc" "$property")" ]
done
for property in vdda-phy-supply vdda-pll-supply; do
	[ "$(fdtget -t x "$output" "$ufs_phy" "$property")" = \
		"$(fdtget -t x "$base" "$ufs_phy" "$property")" ]
done

usb_dwc3=/soc@0/usb@a6f8800/usb@a600000
[ "$(fdtget -t s "$output" "$usb_dwc3" dr_mode)" = peripheral ]
[ "$(fdtget -t s "$output" "$usb_dwc3" maximum-speed)" = high-speed ]
[ "$(fdtget -t s "$output" "$usb_dwc3" phy-names)" = usb2-phy ]
[ "$(fdtget -t x "$output" "$usb_dwc3" phys | wc -w)" -eq 1 ]
fdtget "$output" /soc@0/usb@a6f8800 qcom,select-utmi-as-pipe-clk >/dev/null
[ "$(fdtget -t x "$output" /memory@80000000 reg)" = \
	'0 80000000 0 37100000 2 0 1 80000000 0 c0000000 1 40000000 0 b9500000 0 0' ]

sha256sum "$output"
echo 'PASS kexec-only UFS discovery DTB; reviewed UFS plus USB2 recovery only'
