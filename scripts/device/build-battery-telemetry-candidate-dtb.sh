#!/bin/sh
set -eu

base=${1:?usage: build-battery-telemetry-candidate-dtb.sh BASE_DTB ADSP_OVERLAY PMIC_GLINK_OVERLAY OUTPUT adsp|telemetry}
adsp_overlay=${2:?missing ADSP overlay}
pmic_overlay=${3:?missing PMIC GLINK overlay}
output=${4:?missing output}
mode=${5:?missing candidate mode}

case $mode in
	adsp|telemetry) ;;
	*) echo 'FAIL mode must be adsp or telemetry' >&2; exit 1 ;;
esac

for input in "$base" "$adsp_overlay" "$pmic_overlay"; do
	[ -s "$input" ] && [ -r "$input" ] || {
		echo "FAIL missing DT input: $input" >&2
		exit 1
	}
done

[ "$(grep -c '^&adsp {' "$adsp_overlay")" -eq 1 ]
[ "$(grep -c 'status = "okay";' "$adsp_overlay")" -eq 1 ]
! grep -Eq 'pmic-glink|charger|battery|connector|orientation|nvmem|/delete-|bootargs|reg[[:space:]]*=|supply|ufs_|usb_|gpu|gmu|rmtfs|mdss|dsi|panel|touch' \
	"$adsp_overlay"

[ "$(grep -c '^&{/} {' "$pmic_overlay")" -eq 1 ]
[ "$(grep -c '^[[:space:]]*pmic-glink {' "$pmic_overlay")" -eq 1 ]
[ "$(grep -c 'qcom,sm8350-pmic-glink' "$pmic_overlay")" -eq 1 ]
[ "$(grep -c 'qcom,pmic-glink' "$pmic_overlay")" -eq 1 ]
! grep -Eq '&adsp|status[[:space:]]*=|connector|orientation|gpio|nvmem|charge_limit|/delete-|bootargs|reg[[:space:]]*=|supply|memory-region|ufs_|usb_|gpu|gmu|rmtfs|mdss|dsi|panel|touch' \
	"$pmic_overlay"

stage=$(mktemp -d)
trap 'rm -rf "$stage"' EXIT INT TERM
dtc -q -@ -I dts -O dtb -o "$stage/adsp.dtbo" "$adsp_overlay"
dtc -q -@ -I dts -O dtb -o "$stage/pmic-glink.dtbo" "$pmic_overlay"
mkdir -p "$(dirname "$output")"
case $mode in
	adsp)
		fdtoverlay -i "$base" -o "$output.tmp" "$stage/adsp.dtbo"
		;;
	telemetry)
		fdtoverlay -i "$base" -o "$output.tmp" \
			"$stage/adsp.dtbo" "$stage/pmic-glink.dtbo"
		;;
esac
mv "$output.tmp" "$output"
dtc -q -I dtb -O dts -o /dev/null "$output"

adsp=/soc@0/remoteproc@3000000
pmic_glink=/pmic-glink
rtc=/soc@0/spmi@c440000/pmic@0/rtc@6100
pwrkey=/soc@0/spmi@c440000/pmic@0/pon@1300/pwrkey
stock_low=/reserved-memory/memory@cbc00000
stock_memshare=/reserved-memory/memory@d8000000
stock_high=/reserved-memory/memory@edc00000

[ "$(fdtget -t s "$output" "$adsp" status)" = okay ]
[ "$(fdtget -t s "$output" "$rtc" status)" = disabled ]
[ "$(fdtget -t s "$output" "$pwrkey" status)" = okay ]
[ "$(fdtget -t x "$output" "$stock_low" reg)" = '0 cbc00000 0 4400000' ]
[ "$(fdtget -t x "$output" "$stock_memshare" reg)" = \
	'0 d8000000 0 800000' ]
[ "$(fdtget -t x "$output" "$stock_high" reg)" = \
	'0 edc00000 0 12000000' ]
! fdtget "$output" "$stock_low" no-map >/dev/null 2>&1
fdtget "$output" "$stock_memshare" no-map >/dev/null
! fdtget "$output" "$stock_high" no-map >/dev/null 2>&1

case $mode in
	adsp)
		! fdtget -p "$output" "$pmic_glink" >/dev/null 2>&1
		;;
	telemetry)
		[ "$(fdtget -t s "$output" "$pmic_glink" compatible)" = \
			'qcom,sm8350-pmic-glink qcom,pmic-glink' ]
		[ "$(fdtget -p "$output" "$pmic_glink")" = compatible ]
		[ -z "$(fdtget -l "$output" "$pmic_glink")" ]
		;;
esac

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
[ "$(fdtget -t x "$output" "$usb_dwc3" phys | wc -w)" -eq 1 ]
[ "$(fdtget -t x "$output" /memory@80000000 reg)" = \
	'0 80000000 0 37100000 2 0 1 80000000 0 c0000000 1 40000000 0 b9500000 0 0' ]

sha256sum "$output"
echo "PASS $mode battery-telemetry DTB preserves stock-owned RAM, storage, RTC, GPU, display, SuperSpeed, radio-memory, and secondary-USB isolation"
