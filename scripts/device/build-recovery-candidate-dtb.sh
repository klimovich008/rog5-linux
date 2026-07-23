#!/bin/sh
set -eu

base=${1:?usage: build-recovery-candidate-dtb.sh BASE_DTB OVERLAY_SOURCE OUTPUT}
overlay_source=${2:?missing overlay source}
output=${3:?missing output}
[ -s "$base" ] && [ -r "$overlay_source" ] || { echo 'FAIL missing DTB input' >&2; exit 1; }

[ "$(grep -c 'status = "okay";' "$overlay_source")" -eq 5 ]
[ "$(grep -c '^&' "$overlay_source")" -eq 5 ]
for label in ufs_mem_hc ufs_mem_phy usb_1 usb_1_hsphy usb_1_qmpphy; do
	grep -q "^&$label {" "$overlay_source"
done
! grep -q '^&usb_2' "$overlay_source"
! grep -q 'bootargs\|reg =\|supply =\|memory-region' "$overlay_source"

stage=$(mktemp -d)
trap 'rm -rf "$stage"' EXIT
dtc -q -@ -I dts -O dtb -o "$stage/recovery.dtbo" "$overlay_source"
mkdir -p "$(dirname "$output")"
fdtoverlay -i "$base" -o "$output.tmp" "$stage/recovery.dtbo"
mv "$output.tmp" "$output"
dtc -q -I dtb -O dts -o /dev/null "$output"

for node in \
	/soc@0/ufshc@1d84000 \
	/soc@0/phy@1d87000 \
	/soc@0/usb@a6f8800 \
	/soc@0/phy@88e3000 \
	/soc@0/phy@88e8000
do
	[ "$(fdtget -t s "$output" "$node" status)" = okay ]
done
[ "$(fdtget -t s "$output" /soc@0/usb@a8f8800 status)" = disabled ]
[ "$(fdtget -t s "$output" /soc@0/usb@a6f8800/usb@a600000 dr_mode)" = peripheral ]
[ "$(fdtget -t x "$output" /memory@80000000 reg)" = \
	'0 80000000 0 37100000 2 0 1 80000000 0 c0000000 1 40000000 0 b9500000 0 0' ]

sha256sum "$output"
echo 'PASS kexec-only recovery DTB; UFS and left-side USB enabled, USB2 disabled'
