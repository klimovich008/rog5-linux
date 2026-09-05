#!/bin/sh
set -eu

base=${1:?usage: build-rtc-pwrkey-candidate-dtb.sh RECOVERY_DTB OVERLAY OUTPUT}
overlay=${2:?missing RTC/power-key overlay}
output=${3:?missing output}

[ -s "$base" ] && [ -r "$overlay" ] || {
	echo 'FAIL missing DTB input' >&2
	exit 1
}
[ "$(grep -c '^&' "$overlay")" -eq 2 ]
[ "$(grep -c 'status = "okay";' "$overlay")" -eq 2 ]
for label in pmk8350_rtc pon_pwrkey; do
	grep -q "^&$label {" "$overlay"
done
! grep -Eq 'status = "disabled"|/delete-|bootargs|reg[[:space:]]*=|supply|memory-region|usb_|ufs_|gpu|gmu|rmtfs|mdss|dsi|panel|touch' \
	"$overlay"

stage=$(mktemp -d)
trap 'rm -rf "$stage"' EXIT INT TERM
dtc -q -@ -I dts -O dtb -o "$stage/rtc-pwrkey.dtbo" "$overlay"
mkdir -p "$(dirname "$output")"
fdtoverlay -i "$base" -o "$output.tmp" "$stage/rtc-pwrkey.dtbo"
mv "$output.tmp" "$output"
dtc -q -I dtb -O dts -o /dev/null "$output"

rtc=/soc@0/spmi@c440000/pmic@0/rtc@6100
pwrkey=/soc@0/spmi@c440000/pmic@0/pon@1300/pwrkey
[ "$(fdtget -t s "$output" "$rtc" status)" = okay ]
[ "$(fdtget -t s "$output" "$pwrkey" status)" = okay ]
[ "$(fdtget -t s "$output" "$rtc" compatible)" = qcom,pmk8350-rtc ]
[ "$(fdtget -t s "$output" "$pwrkey" compatible)" = qcom,pmk8350-pwrkey ]
[ "$(fdtget -t x "$output" "$pwrkey" linux,code)" = 74 ]

for node in \
	/soc@0/ufshc@1d84000 \
	/soc@0/phy@1d87000 \
	/soc@0/phy@88e8000 \
	/soc@0/usb@a8f8800 \
	/reserved-memory/memory@9b800000 \
	/soc@0/gpu@3d00000 \
	/soc@0/gmu@3d6a000 \
	/soc@0/clock-controller@3d90000 \
	/soc@0/iommu@3da0000 \
	/soc@0/display-subsystem@ae00000
do
	[ "$(fdtget -t s "$output" "$node" status)" = disabled ]
done
for node in /soc@0/usb@a6f8800 /soc@0/phy@88e3000; do
	[ "$(fdtget -t s "$output" "$node" status)" = okay ]
done
usb_dwc3=/soc@0/usb@a6f8800/usb@a600000
[ "$(fdtget -t s "$output" "$usb_dwc3" maximum-speed)" = high-speed ]
[ "$(fdtget -t s "$output" "$usb_dwc3" phy-names)" = usb2-phy ]
[ "$(fdtget -t x "$output" "$usb_dwc3" phys | wc -w)" = 1 ]
[ "$(fdtget -t x "$output" /memory@80000000 reg)" = \
	'0 80000000 0 37100000 2 0 1 80000000 0 c0000000 1 40000000 0 b9500000 0 0' ]

sha256sum "$output"
echo 'PASS isolated RTC/power-key DTB; storage, GPU, RMTFS, display, SuperSpeed, and secondary USB remain disabled'
