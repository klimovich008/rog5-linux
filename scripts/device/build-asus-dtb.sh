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

mkdir -p "$output_dir"
cpp -nostdinc \
	-I "$source_dir/scripts/dtc/include-prefixes" \
	-I "$source_dir/arch/arm64/boot/dts/qcom" \
	-undef -D__DTS__ -x assembler-with-cpp "$dts" "$preprocessed"
dtc -q -@ -I dts -O dtb -o "$dtb" "$preprocessed"
dtc -q -I dtb -O dts -o /dev/null "$dtb"

sha256sum "$dtb"
echo 'PASS compile-only ASUS serial skeleton; not a boot candidate'
