#!/bin/sh
# Compose the first production display/GPU trial DTB from the installed V9
# headless board.dtb (UFS, USB, ADSP, pmic-glink and buttons on, all proven on
# the phone) plus the reviewed display and GPU overlays. Two documented
# deviations from the reviewed overlays, both from the 2026-09-23 review:
#  - the panel TE pad gpio82 is muxed as mdp_vsync (the DPU's default vsync
#    source) instead of plain gpio, and te-gpios, which no driver reads, is dropped;
#  - the zap shader is the stock ASUS-signed split image a660_zap.mdt.
# GMU, GPUCC and the GPU SMMU, disabled by V9's headless isolation, are enabled.
set -eu
base=${1:?usage: compose-production-display-dtb.sh BASE_DTB KERNEL_SOURCE OUTPUT}
source=${2:?missing kernel source}
output=${3:?missing output}
expected_base=eca5c2c343fc4cd5511490be0c17501d69f4027941e268ff3f95da4672c214f4
repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)
[ "$(sha256sum "$base" | cut -d ' ' -f 1)" = "$expected_base" ] || { echo 'FAIL unexpected base DTB' >&2; exit 1; }
[ -d "$source/scripts/dtc/include-prefixes" ] || { echo 'FAIL kernel source lacks DT include prefixes' >&2; exit 1; }
[ ! -e "$output" ] || { echo 'FAIL output exists' >&2; exit 1; }
work=$(mktemp -d)
trap 'rm -rf -- "$work"' EXIT HUP INT TERM

display=$repo/dts/qcom/sm8350-asus-rog-phone5-display-60hz-reviewed.dtso
gpu=$repo/dts/qcom/sm8350-asus-rog-phone5-gpu.dtso
awk '
	/^\t\tte-pins \{/ { in_te = 1 }
	in_te && /function = "gpio";/ { sub(/"gpio"/, "\"mdp_vsync\"") }
	in_te && /output-disable;/ { next }
	in_te && /^\t\t\};/ { in_te = 0 }
	/te-gpios = / { next }
	{ print }
' "$display" >"$work/display.dtso"
sed 's#qcom/sm8350/a660_zap.mbn#qcom/sm8350/a660_zap.mdt#' "$gpu" >"$work/gpu.dtso"
grep -q 'function = "mdp_vsync";' "$work/display.dtso"
! grep -q 'te-gpios' "$work/display.dtso"
grep -q 'a660_zap.mdt' "$work/gpu.dtso"
for name in display gpu; do
	cpp -nostdinc -undef -D__DTS__ -x assembler-with-cpp \
		-I "$source/scripts/dtc/include-prefixes" \
		-o "$work/$name.pp" "$work/$name.dtso"
	dtc -@ -q -I dts -O dtb -o "$work/$name.dtbo" "$work/$name.pp"
done
fdtoverlay -i "$base" -o "$work/composed.dtb" "$work/display.dtbo" "$work/gpu.dtbo"
for node in /soc@0/gmu@3d6a000 /soc@0/clock-controller@3d90000 /soc@0/iommu@3da0000; do
	fdtput -t s "$work/composed.dtb" "$node" status okay
done
for node in /soc@0/display-subsystem@ae00000 /soc@0/display-subsystem@ae00000/dsi@ae94000 \
	/soc@0/display-subsystem@ae00000/phy@ae94400 /soc@0/gpu@3d00000 /soc@0/gmu@3d6a000 \
	/soc@0/clock-controller@3d90000 /soc@0/iommu@3da0000 /soc@0/ufshc@1d84000 \
	/soc@0/usb@a6f8800 /soc@0/remoteproc@3000000; do
	[ "$(fdtget "$work/composed.dtb" "$node" status)" = okay ] || { echo "FAIL $node not okay" >&2; exit 1; }
done
[ "$(fdtget "$work/composed.dtb" /soc@0/gpu@3d00000/zap-shader firmware-name)" = qcom/sm8350/a660_zap.mdt ]
[ "$(fdtget "$work/composed.dtb" /soc@0/display-subsystem@ae00000/dsi@ae94000/panel@0 compatible)" = asus,rog5-ams678-er2 ]
cp "$work/composed.dtb" "$output"
sha256sum "$output"
