#!/bin/sh
set -eu

fail() {
	echo "FAIL $*" >&2
	exit 1
}

base=${1:?usage: build-recovery-candidate-dtb.sh BASE OVERLAY OUTPUT}
overlay_source=${2:?missing overlay source}
output=${3:?missing output}
script_dir=$(CDPATH= cd -- "$(dirname "$0")" && pwd)
delta_verifier=$script_dir/verify-recovery-dtb-delta.py
if [ ! -s "$base" ] || [ ! -r "$overlay_source" ]; then
	fail 'missing DTB input'
fi
[ -f "$delta_verifier" ] && [ ! -L "$delta_verifier" ] &&
	[ -x "$delta_verifier" ] ||
	fail 'missing recovery DTB delta verifier'

[ "$(grep -c 'status = "okay";' "$overlay_source" || true)" -eq 2 ] ||
	fail 'recovery overlay must contain exactly two okay statuses'
[ "$(grep -c 'status = "disabled";' "$overlay_source" || true)" -eq 5 ] ||
	fail 'recovery overlay must contain exactly five disabled statuses'
[ "$(grep -c '^&' "$overlay_source" || true)" -eq 8 ] ||
	fail 'recovery overlay must contain exactly eight target labels'
for label in \
	rmtfs_mem \
	gpu \
	gmu \
	gpucc \
	adreno_smmu \
	usb_1 \
	usb_1_dwc3 \
	usb_1_hsphy
do
	grep -q "^&$label {" "$overlay_source" ||
		fail "recovery overlay lacks required target label: $label"
done
for forbidden in '^&ufs_mem_' '^&usb_1_qmpphy' '^&usb_2'; do
	if grep -q "$forbidden" "$overlay_source"; then
		fail "recovery overlay contains forbidden target: $forbidden"
	fi
done
if grep -q 'bootargs\|reg =\|supply =\|memory-region' "$overlay_source"; then
	fail 'recovery overlay contains a forbidden high-risk property'
fi

stage=$(mktemp -d)
publish_stage=
cleanup() {
	rm -rf "$stage"
	if [ -n "$publish_stage" ]; then
		rm -rf "$publish_stage"
	fi
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
dtc -q -@ -I dts -O dtb -o "$stage/recovery.dtbo" "$overlay_source"
output_parent=$(dirname "$output")
mkdir -p "$output_parent"
publish_stage=$(mktemp -d "$output_parent/.rog5-recovery-dtb.XXXXXX")
candidate=$publish_stage/candidate.dtb
fdtoverlay -i "$base" -o "$candidate" "$stage/recovery.dtbo"
dtc -q -I dtb -O dts -o /dev/null "$candidate"
"$delta_verifier" "$base" "$candidate"

for node in /soc@0/usb@a6f8800 /soc@0/phy@88e3000; do
	[ "$(fdtget -t s "$candidate" "$node" status)" = okay ]
done
[ "$(fdtget -t s "$candidate" /soc@0/ufshc@1d84000 status)" = disabled ]
[ "$(fdtget -t s "$candidate" /soc@0/phy@1d87000 status)" = disabled ]
[ "$(fdtget -t s "$candidate" /soc@0/phy@88e8000 status)" = disabled ]
[ "$(fdtget -t s "$candidate" /soc@0/usb@a8f8800 status)" = disabled ]
for node in \
	/reserved-memory/memory@9b800000 \
	/soc@0/gpu@3d00000 \
	/soc@0/gmu@3d6a000 \
	/soc@0/clock-controller@3d90000 \
	/soc@0/iommu@3da0000
do
	[ "$(fdtget -t s "$candidate" "$node" status)" = disabled ]
done
usb_dwc3=/soc@0/usb@a6f8800/usb@a600000
[ "$(fdtget -t s "$candidate" "$usb_dwc3" dr_mode)" = peripheral ]
[ "$(fdtget -t s "$candidate" "$usb_dwc3" maximum-speed)" = high-speed ]
[ "$(fdtget -t s "$candidate" "$usb_dwc3" phy-names)" = usb2-phy ]
[ "$(fdtget -t x "$candidate" "$usb_dwc3" phys | wc -w)" = 1 ]
fdtget "$candidate" /soc@0/usb@a6f8800 \
	qcom,select-utmi-as-pipe-clk >/dev/null
[ "$(fdtget -t x "$candidate" /memory@80000000 reg)" = \
	'0 80000000 0 37100000 2 0 1 80000000 0 c0000000 1 40000000 0 b9500000 0 0' ]

mv "$candidate" "$output"
rm -rf "$publish_stage"
publish_stage=
sha256sum "$output"
echo 'PASS exact USB2 recovery DTB isolation contract'
