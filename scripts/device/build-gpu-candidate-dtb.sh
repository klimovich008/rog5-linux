#!/bin/sh
set -eu

base=${1:?usage: build-gpu-candidate-dtb.sh RECOVERY_DTB GPU_OVERLAY OUTPUT}
overlay=${2:?missing GPU overlay}
output=${3:?missing output}

[ -s "$base" ] && [ -r "$overlay" ]
[ "$(grep -c '^&' "$overlay")" -eq 2 ]
[ "$(grep -c 'status = "okay";' "$overlay")" -eq 1 ]
grep -q '^&gpu {' "$overlay"
grep -q '^&gpu_zap_shader {' "$overlay"
grep -q 'firmware-name = "qcom/sm8350/a660_zap.mbn";' "$overlay"
! grep -q 'bootargs\|reg =\|supply =\|memory-region\|opp-\|usb_\|ufs_\|mdss' "$overlay"

stage=$(mktemp -d)
trap 'rm -rf "$stage"' EXIT
dtc -q -@ -I dts -O dtb -o "$stage/gpu.dtbo" "$overlay"
mkdir -p "$(dirname "$output")"
fdtoverlay -i "$base" -o "$output.tmp" "$stage/gpu.dtbo"
mv "$output.tmp" "$output"
dtc -q -I dtb -O dts -o /dev/null "$output"

[ "$(fdtget -t s "$output" /soc@0/gpu@3d00000 status)" = okay ]
[ "$(fdtget -t s "$output" /soc@0/gpu@3d00000/zap-shader firmware-name)" = \
	qcom/sm8350/a660_zap.mbn ]
[ "$(fdtget -t s "$output" /soc@0/display-subsystem@ae00000 status)" = disabled ]
[ "$(fdtget -t s "$output" /soc@0/usb@a8f8800 status)" = disabled ]
for node in \
	/soc@0/ufshc@1d84000 \
	/soc@0/phy@1d87000 \
	/soc@0/usb@a6f8800 \
	/soc@0/phy@88e3000 \
	/soc@0/phy@88e8000
do
	[ "$(fdtget -t s "$output" "$node" status)" = okay ]
done

sha256sum "$output"
echo 'PASS compile-only A660 tier; recovery UFS/USB preserved, display and USB2 disabled'
