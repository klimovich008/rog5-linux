#!/bin/sh
# Compose the default production board.dtb from the installed V9 headless DTB:
# the display/GPU composition (compose-production-display-dtb.sh), the SID 5
# PMIC disabled (display-dtb-r2), then the platform overlay (PMK8350 RTC) and
# ramoops in the 0x9b800000 reservation. Checks the r2 intermediate byte for byte before adding anything.
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
# ramoops takes over the 4 MiB stock debug region in place (same node, same reg).
node=/reserved-memory/memory@9b800000
[ "$(fdtget "$work/composed.dtb" "$node" status)" = disabled ] &&
	[ "$(fdtget "$work/composed.dtb" "$node" compatible)" = qcom,rmtfs-mem ] ||
	{ echo 'FAIL unexpected 0x9b800000 reservation' >&2; exit 1; }
for property in qcom,client-id qcom,vmid no-map; do
	fdtput -d "$work/composed.dtb" "$node" "$property"
done
fdtput -t s "$work/composed.dtb" "$node" compatible ramoops
fdtput -t s "$work/composed.dtb" "$node" status okay
fdtput -t u "$work/composed.dtb" "$node" record-size 262144
fdtput -t u "$work/composed.dtb" "$node" console-size 1048576
fdtput -t u "$work/composed.dtb" "$node" pmsg-size 262144
fdtput -t u "$work/composed.dtb" "$node" ftrace-size 0
fdtput -t u "$work/composed.dtb" "$node" ecc-size 16

rtc=/soc@0/spmi@c440000/pmic@0/rtc@6100
[ "$(fdtget "$work/composed.dtb" "$rtc" status)" = okay ] || { echo 'FAIL RTC not enabled' >&2; exit 1; }
[ "$(fdtget "$work/composed.dtb" "$node" compatible)" = ramoops ]
[ "$(fdtget -tx "$work/composed.dtb" "$node" reg)" = '0 9b800000 0 400000' ]
[ "$(fdtget -l "$work/composed.dtb" /reserved-memory | grep -c 9b8)" = 1 ]
[ "$(fdtget "$work/composed.dtb" /soc@0/spmi@c440000/pmic@5 status)" = disabled ]
cp "$work/composed.dtb" "$output"
sha256sum "$output"
