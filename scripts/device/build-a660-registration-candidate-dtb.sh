#!/bin/sh
set -eu

base=${1:?usage: build-a660-registration-candidate-dtb.sh V18_SMMU_DTB OVERLAY OUTPUT}
overlay=${2:?missing A660 registration overlay}
output=${3:?missing output}
expected_base=da471966073cfb26581b4a5224218904162c5925155b0aa8c24a2b3e4ad0526f

[ -s "$base" ] && [ -r "$overlay" ] || {
	echo 'FAIL missing A660 registration DT input' >&2
	exit 1
}

[ "$(grep -c '^&' "$overlay")" -eq 5 ]
for node in gpucc adreno_smmu gpu gmu gpu_zap_shader; do
	[ "$(grep -c "^&$node {" "$overlay")" -eq 1 ]
done
[ "$(grep -c 'status = "okay";' "$overlay")" -eq 4 ]
[ "$(grep -Ec '^[[:space:]]*[[:alnum:]_,#-]+[[:space:]]*=' \
	"$overlay")" -eq 6 ]
grep -Fqx '	compatible = "asus,rog-phone5", "qcom,sm8350";' "$overlay"
for node in gpucc adreno_smmu gpu gmu; do
	sed -n "/^&$node {/,/^};/p" "$overlay" |
		grep -Fqx '	status = "okay";'
done
sed -n '/^&gpu_zap_shader {/,/^};/p' "$overlay" |
	grep -Fqx '	firmware-name = "qcom/sm8350/a660_zap.mbn";'

if grep -Eq '^[[:space:]]*/delete-|^[[:space:]]*(bootargs|reg|reg-names|interrupts|interrupt-names|iommus|clocks|clock-names|resets|power-domains|power-domain-names|operating-points-v2|interconnect[^[:space:]]*|memory-region|qcom,gmu|[^[:space:]]*supply)[[:space:]]*=' \
	"$overlay"
then
	echo 'FAIL A660 registration overlay overrides a pinned hardware property' >&2
	exit 1
fi

for tool in sha256sum readlink dtc fdtoverlay fdtget install mv; do
	command -v "$tool" >/dev/null
done
[ "$(sha256sum "$base" | cut -d ' ' -f 1)" = "$expected_base" ] || {
	echo 'FAIL A660 registration base is not the accepted v18 SMMU DTB' >&2
	exit 1
}
base_real=$(readlink -f -- "$base")
overlay_real=$(readlink -f -- "$overlay")
output_real=$(readlink -m -- "$output")
[ "$output_real" != "$base_real" ] && [ "$output_real" != "$overlay_real" ] || {
	echo 'FAIL output aliases an A660 registration input' >&2
	exit 1
}

stage=$(mktemp -d)
trap 'rm -rf "$stage"' EXIT INT TERM
dtbo=$stage/a660-registration.dtbo
candidate=$stage/a660-registration.dtb
dtc -q -@ -I dts -O dtb -o "$dtbo" "$overlay"
fdtoverlay -i "$base" -o "$candidate" "$dtbo"
dtc -q -I dtb -O dts -o /dev/null "$candidate"

same_property() {
	node=$1
	property=$2
	type=$3
	[ "$(fdtget -t "$type" "$candidate" "$node" "$property")" = \
		"$(fdtget -t "$type" "$base" "$node" "$property")" ]
}

gpucc=/soc@0/clock-controller@3d90000
smmu=/soc@0/iommu@3da0000
gpu=/soc@0/gpu@3d00000
gmu=/soc@0/gmu@3d6a000
zap=/soc@0/gpu@3d00000/zap-shader
zap_memory=/reserved-memory/memory@8b51a000

[ "$(fdtget -t s "$candidate" "$gpucc" status)" = okay ]
[ "$(fdtget -t s "$candidate" "$gpucc" compatible)" = qcom,sm8350-gpucc ]
for property_type in \
	'reg x' 'clocks x' 'clock-names s' '#clock-cells x' \
	'#reset-cells x' '#power-domain-cells x' 'phandle x'
do
	property=${property_type% *}
	type=${property_type##* }
	same_property "$gpucc" "$property" "$type"
done

[ "$(fdtget -t s "$candidate" "$smmu" status)" = okay ]
[ "$(fdtget -t s "$candidate" "$smmu" compatible)" = \
	'qcom,sm8350-smmu-500 qcom,adreno-smmu qcom,smmu-500 arm,mmu-500' ]
for property_type in \
	'reg x' '#iommu-cells x' '#global-interrupts x' 'interrupts x' \
	'clocks x' 'clock-names s' 'power-domains x' 'phandle x'
do
	property=${property_type% *}
	type=${property_type##* }
	same_property "$smmu" "$property" "$type"
done
fdtget -p "$candidate" "$smmu" | grep -qx dma-coherent

[ "$(fdtget -t s "$candidate" "$gpu" status)" = okay ]
[ "$(fdtget -t s "$candidate" "$gpu" compatible)" = \
	'qcom,adreno-660.1 qcom,adreno' ]
for property_type in \
	'reg x' 'reg-names s' 'interrupts x' 'iommus x' \
	'operating-points-v2 x' 'qcom,gmu x' '#cooling-cells x' 'phandle x'
do
	property=${property_type% *}
	type=${property_type##* }
	same_property "$gpu" "$property" "$type"
done

[ "$(fdtget -t s "$candidate" "$gmu" status)" = okay ]
[ "$(fdtget -t s "$candidate" "$gmu" compatible)" = \
	'qcom,adreno-gmu-660.1 qcom,adreno-gmu' ]
for property_type in \
	'reg x' 'reg-names s' 'interrupts x' 'interrupt-names s' \
	'clocks x' 'clock-names s' 'power-domains x' \
	'power-domain-names s' 'iommus x' 'operating-points-v2 x' \
	'phandle x'
do
	property=${property_type% *}
	type=${property_type##* }
	same_property "$gmu" "$property" "$type"
done

[ "$(fdtget -t s "$candidate" "$zap" firmware-name)" = \
	qcom/sm8350/a660_zap.mbn ]
same_property "$zap" memory-region x
[ "$(fdtget -t x "$candidate" "$zap" memory-region)" = \
	"$(fdtget -t x "$candidate" "$zap_memory" phandle)" ]
[ "$(fdtget -t x "$candidate" "$zap_memory" reg)" = \
	'0 8b51a000 0 2000' ]
fdtget -p "$candidate" "$zap_memory" | grep -qx no-map
[ "$(fdtget -l "$candidate" "$gpu" | grep -c '^opp-table$')" -eq 1 ]
[ "$(fdtget -l "$candidate" "$gmu" | grep -c '^opp-table$')" -eq 1 ]

for node in \
	/reserved-memory/memory@9b800000 \
	/soc@0/ufshc@1d84000 \
	/soc@0/phy@1d87000 \
	/soc@0/phy@88e8000 \
	/soc@0/usb@a8f8800 \
	/soc@0/display-subsystem@ae00000 \
	/soc@0/remoteproc@3000000 \
	/soc@0/remoteproc@4080000 \
	/soc@0/remoteproc@5c00000 \
	/soc@0/remoteproc@a300000 \
	/soc@0/spmi@c440000/pmic@0/rtc@6100 \
	/soc@0/spmi@c440000/pmic@0/pon@1300/pwrkey
do
	[ "$(fdtget -t s "$candidate" "$node" status)" = disabled ]
done

for node in /soc@0/usb@a6f8800 /soc@0/phy@88e3000; do
	[ "$(fdtget -t s "$candidate" "$node" status)" = okay ]
done
usb_dwc3=/soc@0/usb@a6f8800/usb@a600000
[ "$(fdtget -t s "$candidate" "$usb_dwc3" maximum-speed)" = high-speed ]
[ "$(fdtget -t s "$candidate" "$usb_dwc3" phy-names)" = usb2-phy ]
[ "$(fdtget -t x "$candidate" "$usb_dwc3" phys | wc -w)" -eq 1 ]
[ "$(fdtget -t x "$candidate" /memory@80000000 reg)" = \
	'0 80000000 0 37100000 2 0 1 80000000 0 c0000000 1 40000000 0 b9500000 0 0' ]

mkdir -p "$(dirname "$output_real")"
install -m 0644 "$candidate" "$output_real.tmp"
mv "$output_real.tmp" "$output_real"
sha256sum "$output_real"
echo 'PASS exact v18-derived GPUCC, Adreno SMMU, A660, GMU, and ZAP registration DTB; storage, display, remote processors, RTC, and unneeded USB remain disabled'
