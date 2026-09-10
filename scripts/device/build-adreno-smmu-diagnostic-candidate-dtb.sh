#!/bin/sh
set -eu

base=${1:?usage: build-adreno-smmu-diagnostic-candidate-dtb.sh RECOVERY_DTB OVERLAY OUTPUT}
overlay=${2:?missing Adreno SMMU diagnostic overlay}
output=${3:?missing output}

[ -s "$base" ] && [ -r "$overlay" ] || {
	echo 'FAIL missing Adreno SMMU DT input' >&2
	exit 1
}
[ "$(grep -c '^&' "$overlay")" -eq 2 ]
[ "$(grep -c '^&gpucc {' "$overlay")" -eq 1 ]
[ "$(grep -c '^&adreno_smmu {' "$overlay")" -eq 1 ]
[ "$(grep -c 'status = "okay";' "$overlay")" -eq 2 ]
[ "$(grep -Ec '^[[:space:]]*[[:alnum:]_,#-]+[[:space:]]*=' "$overlay")" -eq 3 ]
grep -Fqx '	compatible = "asus,rog-phone5", "qcom,sm8350";' "$overlay"
sed -n '/^&gpucc {/,/^};/p' "$overlay" |
	grep -Fqx '	status = "okay";'
sed -n '/^&adreno_smmu {/,/^};/p' "$overlay" |
	grep -Fqx '	status = "okay";'
if grep -Eq '^&(gpu|gmu|rmtfs_mem|ufs_[[:alnum:]_]*|usb_[[:alnum:]_]*|mdss|adsp|cdsp|mpss|slpi)[[:space:]]*\{|^[[:space:]]*/delete-|^[[:space:]]*(bootargs|firmware[^[:space:]]*|memory-region|reg|clocks|resets|power-domains|interconnect[^[:space:]]*|[^[:space:]]*supply)[[:space:]]*=' \
	"$overlay"
then
	echo 'FAIL Adreno SMMU overlay contains an unreviewed consumer or property' >&2
	exit 1
fi

stage=$(mktemp -d)
trap 'rm -rf "$stage"' EXIT INT TERM
dtc -q -@ -I dts -O dtb -o "$stage/adreno-smmu-diagnostic.dtbo" "$overlay"
mkdir -p "$(dirname "$output")"
fdtoverlay -i "$base" -o "$output.tmp" \
	"$stage/adreno-smmu-diagnostic.dtbo"
mv "$output.tmp" "$output"
dtc -q -I dtb -O dts -o /dev/null "$output"

gpucc=/soc@0/clock-controller@3d90000
[ "$(fdtget -t s "$output" "$gpucc" status)" = okay ]
[ "$(fdtget -t s "$output" "$gpucc" compatible)" = qcom,sm8350-gpucc ]
[ "$(fdtget -t x "$output" "$gpucc" reg)" = '0 3d90000 0 9000' ]
[ "$(fdtget -t s "$output" "$gpucc" clock-names)" = \
	'bi_tcxo gcc_gpu_gpll0_clk_src gcc_gpu_gpll0_div_clk_src' ]
[ "$(fdtget -t x "$output" "$gpucc" '#clock-cells')" = 1 ]
[ "$(fdtget -t x "$output" "$gpucc" '#reset-cells')" = 1 ]
[ "$(fdtget -t x "$output" "$gpucc" '#power-domain-cells')" = 1 ]

smmu=/soc@0/iommu@3da0000
[ "$(fdtget -t s "$output" "$smmu" status)" = okay ]
[ "$(fdtget -t s "$output" "$smmu" compatible)" = \
	'qcom,sm8350-smmu-500 qcom,adreno-smmu qcom,smmu-500 arm,mmu-500' ]
[ "$(fdtget -t x "$output" "$smmu" reg)" = '0 3da0000 0 20000' ]
[ "$(fdtget -t x "$output" "$smmu" '#iommu-cells')" = 2 ]
[ "$(fdtget -t x "$output" "$smmu" '#global-interrupts')" = 2 ]
[ "$(fdtget -t s "$output" "$smmu" clock-names)" = \
	'bus iface ahb hlos1_vote_gpu_smmu cx_gmu hub_cx_int hub_aon' ]
[ "$(fdtget -t x "$output" "$smmu" clocks | wc -w)" -eq 14 ]
[ "$(fdtget -t x "$output" "$smmu" power-domains | wc -w)" -eq 2 ]
[ "$(fdtget -t x "$output" "$smmu" interrupts | wc -w)" -eq 36 ]
fdtget -p "$output" "$smmu" | grep -qx dma-coherent
for property in firmware-name memory-region interconnects interconnect-names; do
	if fdtget -p "$output" "$smmu" | grep -qx "$property"; then
		echo "FAIL Adreno SMMU acquired property: $property" >&2
		exit 1
	fi
done
if fdtget -p "$output" "$smmu" | grep -Eq '(^|-)supply$'; then
	echo 'FAIL Adreno SMMU acquired a supply property' >&2
	exit 1
fi

for node in \
	/soc@0/gpu@3d00000 \
	/soc@0/gmu@3d6a000 \
	/soc@0/ufshc@1d84000 \
	/soc@0/phy@1d87000 \
	/soc@0/phy@88e8000 \
	/soc@0/usb@a8f8800 \
	/reserved-memory/memory@9b800000 \
	/soc@0/display-subsystem@ae00000 \
	/soc@0/remoteproc@3000000 \
	/soc@0/remoteproc@4080000 \
	/soc@0/remoteproc@5c00000 \
	/soc@0/remoteproc@a300000 \
	/soc@0/spmi@c440000/pmic@0/rtc@6100 \
	/soc@0/spmi@c440000/pmic@0/pon@1300/pwrkey
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
echo 'PASS GPUCC plus Adreno SMMU DTB; GPU, GMU, firmware clients, storage, display, remote processors, RTC, and unneeded USB remain disabled'
