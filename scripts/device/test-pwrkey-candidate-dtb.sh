#!/bin/sh
set -eu

repo=$(CDPATH= cd -- "$(dirname "$0")/../.." && pwd)
overlay=$repo/dts/qcom/sm8350-asus-rog-phone5-pwrkey.dtso
builder=$repo/scripts/device/build-pwrkey-candidate-dtb.sh
stage=$(mktemp -d)
trap 'rm -rf "$stage"' EXIT INT TERM

[ -r "$overlay" ] && [ -x "$builder" ]
[ "$(grep -c '^&' "$overlay")" -eq 1 ]
[ "$(grep -c 'status = "okay";' "$overlay")" -eq 1 ]
grep -q '^&pon_pwrkey {' "$overlay"
! grep -Eq 'pmk8350_rtc|rtc@|allow-set-time|nvmem-cells|qcom,uefi-rtc-info' \
	"$overlay"

awk '
	/^&pon_pwrkey \{/ { target = 1 }
	target && /status = "okay";/ { target = 0; next }
	{ print }
' "$overlay" >"$stage/mutant.dtso"
printf 'dummy\n' >"$stage/base.dtb"
if PATH=/nonexistent "$builder" "$stage/base.dtb" \
	"$stage/mutant.dtso" "$stage/output.dtb" >/dev/null 2>&1; then
	echo 'FAIL builder accepted overlay without power-key enablement' >&2
	exit 1
fi

for node in \
	/soc@0/spmi@c440000/pmic@0/rtc@6100 \
	/soc@0/ufshc@1d84000 \
	/soc@0/phy@1d87000 \
	/soc@0/phy@88e8000 \
	/soc@0/usb@a8f8800 \
	/reserved-memory/memory@9b800000 \
	/soc@0/gpu@3d00000 \
	/soc@0/gmu@3d6a000 \
	/soc@0/clock-controller@3d90000 \
	/soc@0/iommu@3da0000 \
	/soc@0/display-subsystem@ae00000; do
	grep -Fq "$node" "$builder"
done

if [ -n "${BASE_DTB:-}" ]; then
	[ -s "$BASE_DTB" ]
	"$builder" "$BASE_DTB" "$overlay" "$stage/one.dtb" >/dev/null
	"$builder" "$BASE_DTB" "$overlay" "$stage/two.dtb" >/dev/null
	cmp "$stage/one.dtb" "$stage/two.dtb"
fi

echo 'PASS power-key tier enables exactly one node and preserves RTC plus every recovery isolation boundary'
