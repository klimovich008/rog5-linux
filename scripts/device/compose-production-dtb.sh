#!/bin/sh
# Compose the default production board.dtb from the installed V9 headless DTB:
# the display/GPU composition (compose-production-display-dtb.sh), the SID 5
# PMIC disabled (display-dtb-r2), then the platform overlay (PMK8350 RTC and
# ramoops). Checks the r2 intermediate byte for byte before adding anything.
set -eu
base=${1:?usage: compose-production-dtb.sh BASE_DTB KERNEL_SOURCE OUTPUT}
source=${2:?missing kernel source}
output=${3:?missing output}
expected_r2=08d41d4dbb7e16984d0b45f776a9654e38ba9c9553fa1f3a315a0882a9850b66
repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)
[ ! -e "$output" ] || { echo 'FAIL output exists' >&2; exit 1; }
work=$(mktemp -d)
trap 'rm -rf -- "$work"' EXIT HUP INT TERM

sh "$repo/scripts/device/compose-production-display-dtb.sh" "$base" "$source" "$work/display.dtb" >/dev/null
cp "$work/display.dtb" "$work/r2.dtb"
fdtput -t s "$work/r2.dtb" /soc@0/spmi@c440000/pmic@5 status disabled
[ "$(sha256sum "$work/r2.dtb" | cut -d ' ' -f 1)" = "$expected_r2" ] ||
	{ echo 'FAIL display-dtb-r2 is not reproduced' >&2; exit 1; }

cpp -nostdinc -undef -D__DTS__ -x assembler-with-cpp \
	-I "$source/scripts/dtc/include-prefixes" \
	-o "$work/platform.pp" "$repo/dts/qcom/sm8350-asus-rog-phone5-platform.dtso"
dtc -@ -q -I dts -O dtb -o "$work/platform.dtbo" "$work/platform.pp"
fdtoverlay -i "$work/r2.dtb" -o "$work/composed.dtb" "$work/platform.dtbo"

rtc=/soc@0/spmi@c440000/pmic@0/rtc@6100
[ "$(fdtget "$work/composed.dtb" "$rtc" status)" = okay ] || { echo 'FAIL RTC not enabled' >&2; exit 1; }
[ "$(fdtget "$work/composed.dtb" /reserved-memory/ramoops@9b800000 compatible)" = ramoops ]
[ "$(fdtget -tx "$work/composed.dtb" /reserved-memory/ramoops@9b800000 reg)" = '0 9b800000 0 400000' ]
# The overlapping rmtfs node must stay disabled, or the two reservations clash.
[ "$(fdtget "$work/composed.dtb" /reserved-memory/memory@9b800000 status)" = disabled ]
[ "$(fdtget "$work/composed.dtb" /soc@0/spmi@c440000/pmic@5 status)" = disabled ]
cp "$work/composed.dtb" "$output"
sha256sum "$output"
