#!/bin/sh
set -eu

dtb=${1:?usage: inspect-vendor-usb-contract.sh VENDOR_DTB}
[ -s "$dtb" ] || { echo 'FAIL missing vendor DTB' >&2; exit 1; }

script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
resolver=$script_dir/resolve-dtb-phandles.sh
[ -x "$resolver" ] || { echo 'FAIL missing phandle resolver' >&2; exit 1; }

handles=
for node in \
	/soc/ssusb@a600000 \
	/soc/ssusb@a600000/dwc3@a600000 \
	/soc/ssusb@a600000/port \
	/soc/ssusb@a600000/port/endpoint \
	/soc/ssusb@a800000 \
	/soc/ssusb@a800000/dwc3@a800000 \
	/soc/extcon_usb1 \
	/soc/hsphy@88e3000 \
	/soc/ssphy@88e8000 \
	/soc/hsphy@88e4000 \
	/soc/ssphy@88eb000
do
	echo "NODE=$node"
	for property in \
		status dr_mode maximum-speed phy-names phys usb-phy usb-role-switch \
		extcon adsp-usb2-switch qcom,usb-charger vcc_redriver-supply \
		vdd-supply vdda18-supply vdda33-supply core-supply \
		mode-switch orientation-switch remote-endpoint
	do
		fdtget "$dtb" "$node" "$property" >/dev/null 2>&1 || continue
		case $property in
			phys|usb-phy|extcon|qcom,usb-charger|vcc_redriver-supply|vdd-supply|vdda18-supply|vdda33-supply|core-supply|remote-endpoint)
				value=$(fdtget -t x "$dtb" "$node" "$property")
				handles="$handles $value"
				echo "$property=phandle-cells:$value"
				;;
			*)
				value=$(fdtget -t s "$dtb" "$node" "$property" 2>/dev/null || true)
				[ -n "$value" ] || value=present
				echo "$property=$value"
				;;
		esac
	done
done

echo RESOLVED_REFERENCES
# Non-phandle argument cells are harmless: the resolver prints matching nodes only.
# shellcheck disable=SC2086
"$resolver" "$dtb" $handles
