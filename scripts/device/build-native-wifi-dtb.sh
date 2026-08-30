#!/bin/sh
set -eu
base=${1:?usage: build-native-wifi-dtb.sh BASE_DTB NEW_OUTPUT}
output=${2:?missing output}
repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)
[ ! -e "$output" ] && [ ! -L "$output" ]
"$repo/scripts/device/verify-persistent-root-power-usb-dtb.sh" "$base" >/dev/null
work=$(mktemp -d)
trap 'rm -rf -- "$work"' EXIT HUP INT TERM
dtc -q -@ -I dts -O dtb -o "$work/wifi.dtbo" \
	"$repo/dts/qcom/sm8350-asus-rog-phone5-wifi-ww33.dtso"
fdtoverlay -i "$base" -o "$work/candidate.dtb" "$work/wifi.dtbo"
"$repo/scripts/device/verify-persistent-root-power-usb-dtb.sh" "$work/candidate.dtb"
python3 "$repo/scripts/device/verify-native-wifi-dtb.py" "$base" "$work/candidate.dtb"
install -m 0644 "$work/candidate.dtb" "$output"
sha256sum "$output"
