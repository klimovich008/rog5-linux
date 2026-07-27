#!/bin/sh
set -eu

base=${1:?usage: build-wifi-candidate-dtb.sh NETWORK_ROOT_V8_DTB OVERLAY OUTPUT}
overlay=${2:?missing WCN6855 overlay}
output=${3:?missing output}
expected_base=0fb6d415597630508779263693803af40f35496adee17e82995b0189b2aa9c78

if [ ! -s "$base" ] || [ ! -r "$overlay" ]; then
	echo 'FAIL missing Wi-Fi candidate DT input' >&2
	exit 1
fi

require_line() {
	grep -Fqx "$1" "$overlay" || {
		echo "FAIL Wi-Fi overlay omits: $1" >&2
		exit 1
	}
}

[ "$(grep -c '^&' "$overlay")" -eq 7 ]
for node in '{/}' apps_rsc vreg_s11b_0p95 vreg_s1c_1p86 tlmm pcie0 pcie0_phy; do
	[ "$(grep -c "^&$node {" "$overlay")" -eq 1 ]
done
for line in \
	'		compatible = "qcom,wcn6855-pmu";' \
	'		wlan-enable-gpios = <&tlmm 64 0>;' \
	'		bt-enable-gpios = <&tlmm 65 0>;' \
	'		swctrl-gpios = <&tlmm 153 0>;' \
	'		vddio-supply = <&vreg_s10b_1p8>;' \
	'		vddaon-supply = <&vreg_s11b_0p95>;' \
	'		vddpmu-supply = <&vreg_s12b_1p35>;' \
	'		vddpmumx-supply = <&vreg_s2e_0p976>;' \
	'		vddpmucx-supply = <&vreg_s11b_0p95>;' \
	'		vddrfa0p95-supply = <&vreg_s11b_0p95>;' \
	'		vddrfa1p3-supply = <&vreg_s12b_1p35>;' \
	'		vddrfa1p9-supply = <&vreg_s1c_1p86>;' \
	'		vddpcie1p3-supply = <&vreg_s12b_1p35>;' \
	'		vddpcie1p9-supply = <&vreg_s1c_1p86>;' \
	'	perst-gpios = <&tlmm 94 1>;' \
	'	wake-gpios = <&tlmm 96 0>;' \
	'			compatible = "pci17cb,1103";' \
	'			vddrfacmn-supply = <&pmu_ldo0>;' \
	'			vddaon-supply = <&pmu_ldo1>;' \
	'			vddwlcx-supply = <&pmu_ldo2>;' \
	'			vddwlmx-supply = <&pmu_ldo3>;' \
	'			vddpcie1p8-supply = <&pmu_ldo5>;' \
	'			vddpcie0p9-supply = <&pmu_ldo6>;' \
	'			vddrfa0p8-supply = <&pmu_ldo7>;' \
	'			vddrfa1p2-supply = <&pmu_ldo8>;' \
	'			vddrfa1p8-supply = <&pmu_ldo9>;'
do
	require_line "$line"
done
[ "$(grep -Ec '^[[:space:]]*pmu_ldo[0-9]+: ldo[0-9]+ {' "$overlay")" -eq 10 ]
[ "$(grep -c 'status = "okay";' "$overlay")" -eq 2 ]

if grep -Eq 'max-link-speed|qcom,.*calibration-variant|^[[:space:]]*/delete-|bootargs|fastboot|adb|(^|[[:space:]])mount[[:space:]]|(^|[[:space:]])dd[[:space:]]' \
	"$overlay"
then
	echo 'FAIL Wi-Fi overlay contains an unverified or unsafe operation' >&2
	exit 1
fi

for tool in sha256sum readlink dtc fdtoverlay fdtget install mv awk; do
	command -v "$tool" >/dev/null
done
[ "$(sha256sum "$base" | cut -d ' ' -f 1)" = "$expected_base" ] || {
	echo 'FAIL Wi-Fi candidate base is not the accepted network-root v8 DTB' >&2
	exit 1
}
base_real=$(readlink -f -- "$base")
overlay_real=$(readlink -f -- "$overlay")
output_real=$(readlink -m -- "$output")
if [ "$output_real" = "$base_real" ] || [ "$output_real" = "$overlay_real" ]; then
	echo 'FAIL output aliases a Wi-Fi candidate input' >&2
	exit 1
fi

stage=$(mktemp -d)
trap 'rm -rf "$stage"' EXIT INT TERM
dtbo=$stage/wifi.dtbo
candidate=$stage/wifi.dtb
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

same_phandle() {
	node=$1
	property=$2
	provider=$3
	[ "$(fdtget -t x "$candidate" "$node" "$property")" = \
		"$(fdtget -t x "$candidate" "$provider" phandle)" ]
}

gpio_contract() {
	node=$1
	property=$2
	number=$3
	flags=$4
	cells=$(fdtget -t u "$candidate" "$node" "$property")
	[ "$(printf '%s\n' "$cells" | awk '{ print NF }')" -eq 3 ]
	[ "$(printf '%s\n' "$cells" | awk '{ print $2 }')" -eq "$number" ]
	[ "$(printf '%s\n' "$cells" | awk '{ print $3 }')" -eq "$flags" ]
}

pmu=/wcn6855-pmu
apps_rsc=/soc@0/rsc@18200000
regulators_b=$apps_rsc/regulators-0
regulators_c=$apps_rsc/regulators-1
regulators_e=$apps_rsc/regulators-2
s10b=$regulators_b/smps10
s11b=$regulators_b/smps11
s12b=$regulators_b/smps12
s1c=$regulators_c/smps1
s2e=$regulators_e/smps2
pcie=/soc@0/pcie@1c00000
pcie_phy=/soc@0/phy@1c06000
wifi=/soc@0/pcie@1c00000/pcie@0/wifi@0
tlmm=/soc@0/pinctrl@f100000

[ "$(fdtget -t s "$candidate" "$pmu" compatible)" = qcom,wcn6855-pmu ]
gpio_contract "$pmu" wlan-enable-gpios 64 0
gpio_contract "$pmu" bt-enable-gpios 65 0
gpio_contract "$pmu" swctrl-gpios 153 0
for contract in \
	"vddio-supply $s10b" \
	"vddaon-supply $s11b" \
	"vddpmu-supply $s12b" \
	"vddpmumx-supply $s2e" \
	"vddpmucx-supply $s11b" \
	"vddrfa0p95-supply $s11b" \
	"vddrfa1p3-supply $s12b" \
	"vddrfa1p9-supply $s1c" \
	"vddpcie1p3-supply $s12b" \
	"vddpcie1p9-supply $s1c"
do
	property=${contract%% *}
	provider=${contract#* }
	same_phandle "$pmu" "$property" "$provider"
done

[ "$(fdtget -t u "$candidate" "$s10b" regulator-min-microvolt)" -eq 1800000 ]
[ "$(fdtget -t u "$candidate" "$s10b" regulator-max-microvolt)" -eq 1800000 ]
[ "$(fdtget -t u "$candidate" "$s11b" regulator-min-microvolt)" -eq 952000 ]
[ "$(fdtget -t u "$candidate" "$s11b" regulator-max-microvolt)" -eq 952000 ]
[ "$(fdtget -t u "$candidate" "$s12b" regulator-min-microvolt)" -eq 1350000 ]
[ "$(fdtget -t u "$candidate" "$s12b" regulator-max-microvolt)" -eq 1350000 ]
[ "$(fdtget -t u "$candidate" "$s1c" regulator-min-microvolt)" -eq 1880000 ]
[ "$(fdtget -t u "$candidate" "$s1c" regulator-max-microvolt)" -eq 1880000 ]
[ "$(fdtget -t u "$candidate" "$s2e" regulator-min-microvolt)" -eq 976000 ]
[ "$(fdtget -t u "$candidate" "$s2e" regulator-max-microvolt)" -eq 976000 ]

[ "$(fdtget -l "$candidate" "$pmu/regulators" | grep -Ec '^ldo[0-9]$')" -eq 10 ]
[ "$(fdtget -t s "$candidate" "$wifi" compatible)" = pci17cb,1103 ]
[ "$(fdtget -t x "$candidate" "$wifi" reg)" = '10000 0 0 0 0' ]
for contract in \
	'vddrfacmn-supply ldo0' \
	'vddaon-supply ldo1' \
	'vddwlcx-supply ldo2' \
	'vddwlmx-supply ldo3' \
	'vddpcie1p8-supply ldo5' \
	'vddpcie0p9-supply ldo6' \
	'vddrfa0p8-supply ldo7' \
	'vddrfa1p2-supply ldo8' \
	'vddrfa1p8-supply ldo9'
do
	property=${contract%% *}
	provider=${contract#* }
	same_phandle "$wifi" "$property" "$pmu/regulators/$provider"
done

[ "$(fdtget -t s "$candidate" "$pcie" status)" = okay ]
[ "$(fdtget -t s "$candidate" "$pcie_phy" status)" = okay ]
gpio_contract "$pcie" perst-gpios 94 1
gpio_contract "$pcie" wake-gpios 96 0
same_phandle "$pcie_phy" vdda-phy-supply "$regulators_b/ldo5"
same_phandle "$pcie_phy" vdda-pll-supply "$regulators_b/ldo6"
for property_type in \
	'compatible s' 'reg x' 'reg-names s' 'clocks x' 'clock-names s' \
	'iommu-map x' 'resets x' 'power-domains x' 'phys x'
do
	property=${property_type% *}
	type=${property_type##* }
	same_property "$pcie" "$property" "$type"
done
for property_type in \
	'compatible s' 'reg x' 'clocks x' 'clock-names s' 'resets x' \
	'assigned-clocks x' 'assigned-clock-rates x'
do
	property=${property_type% *}
	type=${property_type##* }
	same_property "$pcie_phy" "$property" "$type"
done

[ "$(fdtget -t s "$candidate" "$tlmm/wlan-en-state" pins)" = gpio64 ]
[ "$(fdtget -t s "$candidate" "$tlmm/bt-en-state" pins)" = gpio65 ]
[ "$(fdtget -t s "$candidate" "$tlmm/wlan-antenna-state" pins)" = \
	'gpio141 gpio142 gpio144' ]
fdtget -p "$candidate" "$tlmm/wlan-en-state" | grep -qx output-low
fdtget -p "$candidate" "$tlmm/bt-en-state" | grep -qx output-low
fdtget -p "$candidate" "$tlmm/wlan-antenna-state" | grep -qx output-high
[ "$(fdtget -t s "$candidate" "$tlmm/pcie0-default-state/clkreq-pins" function)" = \
	pcie0_clkreqn ]

for node in \
	/soc@0/ufshc@1d84000 \
	/soc@0/phy@1d87000 \
	/soc@0/phy@88e8000 \
	/soc@0/usb@a8f8800 \
	/soc@0/pcie@1c08000 \
	/soc@0/gpu@3d00000 \
	/soc@0/gmu@3d6a000 \
	/soc@0/clock-controller@3d90000 \
	/soc@0/iommu@3da0000 \
	/soc@0/display-subsystem@ae00000
do
	[ "$(fdtget -t s "$candidate" "$node" status)" = disabled ]
done
[ "$(fdtget -t s "$candidate" /soc@0/remoteproc@3000000 status)" = okay ]
[ "$(fdtget -t s "$candidate" /soc@0/spmi@c440000/pmic@0/pon@1300/pwrkey status)" = okay ]
for node in /soc@0/usb@a6f8800 /soc@0/phy@88e3000; do
	[ "$(fdtget -t s "$candidate" "$node" status)" = okay ]
done
[ "$(fdtget -t x "$candidate" /memory@80000000 reg)" = \
	'0 80000000 0 37100000 2 0 1 80000000 0 c0000000 1 40000000 0 b9500000 0 0' ]

mkdir -p "$(dirname "$output_real")"
install -m 0644 "$candidate" "$output_real.tmp"
mv "$output_real.tmp" "$output_real"
sha256sum "$output_real"
echo 'PASS exact network-root-v8-derived SM8350 PCIe0/WCN6855 DTB; storage, display, GPU, PCIe1, and unneeded USB remain disabled'
