#!/bin/sh
set -eu

source_dir=${SOURCE_DIR:-/root/src/linux-7.1.4}
dts=${DTS:-/workspace/repo/dts/qcom/sm8350-asus-rog-phone5.dts}
output_dir=${OUTPUT_DIR:-/root/build/rog5-linux-7.1.4/asus-dt}
dtb=$output_dir/sm8350-asus-rog-phone5.dtb
preprocessed=$output_dir/sm8350-asus-rog-phone5.preprocessed.dts

[ -r "$dts" ] || { echo "FAIL missing $dts" >&2; exit 1; }
grep -q 'compatible = "asus,rog-phone5", "qcom,sm8350";' "$dts"
! grep -q 'qcom,sm8350-mtp\|qcom,lahaina-mtp\|bootargs' "$dts"
[ "$(grep -c 'status = "okay";' "$dts")" -eq 2 ] || {
	echo 'FAIL serial-only skeleton enabled an unexpected subsystem' >&2
	exit 1
}
[ "$(grep -c 'status = "disabled";' "$dts")" -eq 5 ]
grep -q '^&ufs_mem_hc {' "$dts"
grep -q '^&ufs_mem_phy {' "$dts"
grep -q '^&usb_1 {' "$dts"
grep -q '^&usb_1_dwc3 {' "$dts"
grep -q '^&usb_1_hsphy {' "$dts"
grep -q '^&usb_1_qmpphy {' "$dts"
! grep -q '^&usb_2' "$dts"

mkdir -p "$output_dir"
cpp -nostdinc \
	-I "$source_dir/scripts/dtc/include-prefixes" \
	-I "$source_dir/arch/arm64/boot/dts/qcom" \
	-undef -D__DTS__ -x assembler-with-cpp "$dts" "$preprocessed"
dtc -q -@ -I dts -O dtb -o "$dtb" "$preprocessed"
dtc -q -I dtb -O dts -o /dev/null "$dtb"

memory=/memory@80000000
[ "$(fdtget -t s "$dtb" "$memory" device_type)" = memory ]
[ "$(fdtget -t x "$dtb" "$memory" reg)" = \
	'0 80000000 0 37100000 2 0 1 80000000 0 c0000000 1 40000000 0 b9500000 0 0' ]
[ "$(fdtget -t x "$dtb" /reserved-memory/memory@9b800000 reg)" = \
	'0 9b800000 0 400000' ]
[ "$(fdtget -t x "$dtb" /reserved-memory/memory@d8800000 reg)" = \
	'0 d8800000 0 a800000' ]
for node in /reserved-memory/memory@e5000000 /reserved-memory/memory@e7400000; do
	fdtget "$dtb" "$node" no-map >/dev/null
done

ufs_hc=/soc@0/ufshc@1d84000
ufs_phy=/soc@0/phy@1d87000
[ "$(fdtget -t s "$dtb" "$ufs_hc" status)" = disabled ]
[ "$(fdtget -t s "$dtb" "$ufs_phy" status)" = disabled ]
set -- $(fdtget -t x "$dtb" "$ufs_hc" reset-gpios)
[ "$2" = cb ] && [ "$3" = 1 ]
for property in vcc-supply vccq-supply; do
	fdtget "$dtb" "$ufs_hc" "$property" >/dev/null
done
for property in vdda-phy-supply vdda-pll-supply; do
	fdtget "$dtb" "$ufs_phy" "$property" >/dev/null
done

usb_controller=/soc@0/usb@a6f8800
usb_dwc3=$usb_controller/usb@a600000
usb_hs_phy=/soc@0/phy@88e3000
usb_qmp_phy=/soc@0/phy@88e8000
usb_2_controller=/soc@0/usb@a8f8800
for node in "$usb_controller" "$usb_hs_phy" "$usb_qmp_phy" "$usb_2_controller"; do
	[ "$(fdtget -t s "$dtb" "$node" status)" = disabled ]
done
[ "$(fdtget -t s "$dtb" "$usb_dwc3" dr_mode)" = peripheral ]
for property in vdda-pll-supply vdda18-supply vdda33-supply; do
	fdtget "$dtb" "$usb_hs_phy" "$property" >/dev/null
done
for property in vdda-phy-supply vdda-pll-supply; do
	fdtget "$dtb" "$usb_qmp_phy" "$property" >/dev/null
done

sha256sum "$dtb"
echo 'PASS compile-only ASUS recovery contract; UFS and USB remain disabled'
