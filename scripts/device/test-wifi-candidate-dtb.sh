#!/bin/sh
set -eu

repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)
overlay=$repo/dts/qcom/sm8350-asus-rog-phone5-wifi.dtso
fragment=$repo/configs/kernel/rog5-wifi.fragment
builder=$repo/scripts/device/build-wifi-candidate-dtb.sh
default_base=$repo/artifacts/network-root-v8-telemetry/sm8350-asus-rog-phone5-recovery.dtb
base=${BASE_DTB:-$default_base}
expected_base=0fb6d415597630508779263693803af40f35496adee17e82995b0189b2aa9c78
stage=$(mktemp -d)
trap 'rm -rf "$stage"' EXIT INT TERM

for input in "$overlay" "$fragment"; do
	[ -r "$input" ] || {
		echo "FAIL missing Wi-Fi candidate input: $input" >&2
		exit 1
	}
done
[ -x "$builder" ] || {
	echo 'FAIL missing executable Wi-Fi candidate DT builder' >&2
	exit 1
}
sh -n "$builder"

for contract in \
	'/plugin/;' \
	'compatible = "qcom,wcn6855-pmu";' \
	'wlan-enable-gpios = <&tlmm 64 0>;' \
	'bt-enable-gpios = <&tlmm 65 0>;' \
	'swctrl-gpios = <&tlmm 153 0>;' \
	'perst-gpios = <&tlmm 94 1>;' \
	'wake-gpios = <&tlmm 96 0>;' \
	'compatible = "pci17cb,1103";' \
	'vddio-supply = <&vreg_s10b_1p8>;' \
	'vddaon-supply = <&vreg_s11b_0p95>;' \
	'vddpmu-supply = <&vreg_s12b_1p35>;' \
	'vddpmumx-supply = <&vreg_s2e_0p976>;' \
	'vddpmucx-supply = <&vreg_s11b_0p95>;' \
	'vddrfa0p95-supply = <&vreg_s11b_0p95>;' \
	'vddrfa1p3-supply = <&vreg_s12b_1p35>;' \
	'vddrfa1p9-supply = <&vreg_s1c_1p86>;' \
	'vddpcie1p3-supply = <&vreg_s12b_1p35>;' \
	'vddpcie1p9-supply = <&vreg_s1c_1p86>;' \
	'vddrfacmn-supply = <&pmu_ldo0>;' \
	'vddaon-supply = <&pmu_ldo1>;' \
	'vddwlcx-supply = <&pmu_ldo2>;' \
	'vddwlmx-supply = <&pmu_ldo3>;' \
	'vddpcie1p8-supply = <&pmu_ldo5>;' \
	'vddpcie0p9-supply = <&pmu_ldo6>;' \
	'vddrfa0p8-supply = <&pmu_ldo7>;' \
	'vddrfa1p2-supply = <&pmu_ldo8>;' \
	'vddrfa1p8-supply = <&pmu_ldo9>;'
do
	grep -Fq "$contract" "$overlay" || {
		echo "FAIL Wi-Fi overlay omits: $contract" >&2
		exit 1
	}
done

for contract in \
	'CONFIG_PHY_QCOM_QMP_PCIE=m' \
	'CONFIG_PCIE_QCOM=y' \
	'CONFIG_PCI_PWRCTRL=y' \
	'CONFIG_PCI_PWRCTRL_PWRSEQ=m' \
	'CONFIG_POWER_SEQUENCING=y' \
	'CONFIG_POWER_SEQUENCING_QCOM_WCN=m' \
	'CONFIG_MHI_BUS=m' \
	'CONFIG_MHI_BUS_PCI_GENERIC=m' \
	'CONFIG_ATH11K=m' \
	'CONFIG_ATH11K_PCI=m'
do
	grep -Fqx "$contract" "$fragment" || {
		echo "FAIL Wi-Fi kernel fragment omits: $contract" >&2
		exit 1
	}
done

if grep -Eq 'max-link-speed|qcom,.*calibration-variant' "$overlay" "$fragment"
then
	echo 'FAIL Wi-Fi candidate invents an unverified property' >&2
	exit 1
fi
if grep -Eq '^[[:space:]]*(fastboot|adb|mount|dd)([[:space:]]|$)' \
	"$overlay" "$fragment" "$builder"
then
	echo 'FAIL Wi-Fi candidate controls or writes to the phone' >&2
	exit 1
fi

for contract in \
	"$expected_base" \
	'/soc@0/pcie@1c00000' \
	'/soc@0/phy@1c06000' \
	'/soc@0/pcie@1c00000/pcie@0/wifi@0' \
	'qcom,wcn6855-pmu' \
	'pci17cb,1103' \
	'/soc@0/ufshc@1d84000' \
	'/soc@0/display-subsystem@ae00000'
do
	grep -Fq "$contract" "$builder" || {
		echo "FAIL Wi-Fi DT builder omits: $contract" >&2
		exit 1
	}
done

printf 'dummy\n' >"$stage/base.dtb"
sed '/vddpmumx-supply = <&vreg_s2e_0p976>;/d' \
	"$overlay" >"$stage/no-pmu-mx.dtso"
if PATH=/nonexistent "$builder" "$stage/base.dtb" \
	"$stage/no-pmu-mx.dtso" "$stage/output.dtb" >/dev/null 2>&1
then
	echo 'FAIL builder accepted an incomplete WCN6855 host-rail map' >&2
	exit 1
fi

sed '/vddpcie0p9-supply = <&pmu_ldo6>;/d' \
	"$overlay" >"$stage/no-endpoint-rail.dtso"
if PATH=/nonexistent "$builder" "$stage/base.dtb" \
	"$stage/no-endpoint-rail.dtso" "$stage/output.dtb" >/dev/null 2>&1
then
	echo 'FAIL builder accepted an incomplete WCN6855 endpoint-rail map' >&2
	exit 1
fi

if [ -s "$base" ]; then
	[ "$(sha256sum "$base" | cut -d ' ' -f 1)" = "$expected_base" ]
	base_hash=$(sha256sum "$base" | cut -d ' ' -f 1)
	"$builder" "$base" "$overlay" "$stage/one.dtb" >/dev/null
	"$builder" "$base" "$overlay" "$stage/two.dtb" >/dev/null
	cmp "$stage/one.dtb" "$stage/two.dtb"
	[ "$(sha256sum "$base" | cut -d ' ' -f 1)" = "$base_hash" ]

	cp "$base" "$stage/base-mutant.dtb"
	truncate -s +1 "$stage/base-mutant.dtb"
	if "$builder" "$stage/base-mutant.dtb" "$overlay" \
		"$stage/mutant-output.dtb" >/dev/null 2>&1
	then
		echo 'FAIL builder accepted a modified network-root v8 base' >&2
		exit 1
	fi

	if "$builder" "$base" "$overlay" "$base" >/dev/null 2>&1
	then
		echo 'FAIL builder accepted an output aliasing its base' >&2
		exit 1
	fi
fi

echo 'PASS Wi-Fi DT candidate is deterministic, mutation-tested, and preserves the accepted base'
