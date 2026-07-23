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
[ "$(grep -c 'status = "disabled";' "$dts")" -eq 2 ]
grep -q '^&ufs_mem_hc {' "$dts"
grep -q '^&ufs_mem_phy {' "$dts"
! grep -q '^&usb_[12]' "$dts"

mkdir -p "$output_dir"
cpp -nostdinc \
	-I "$source_dir/scripts/dtc/include-prefixes" \
	-I "$source_dir/arch/arm64/boot/dts/qcom" \
	-undef -D__DTS__ -x assembler-with-cpp "$dts" "$preprocessed"
dtc -q -@ -I dts -O dtb -o "$dtb" "$preprocessed"
dtc -q -I dtb -O dts -o /dev/null "$dtb"

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

sha256sum "$dtb"
echo 'PASS compile-only ASUS serial skeleton; not a boot candidate'
