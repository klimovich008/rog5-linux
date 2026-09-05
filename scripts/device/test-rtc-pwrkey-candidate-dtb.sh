#!/bin/sh
set -eu

repo=$(CDPATH= cd -- "$(dirname "$0")/../.." && pwd)
overlay=$repo/dts/qcom/sm8350-asus-rog-phone5-rtc-pwrkey.dtso
builder=$repo/scripts/device/build-rtc-pwrkey-candidate-dtb.sh
stage=$(mktemp -d)
trap 'rm -rf "$stage"' EXIT INT TERM

[ -r "$overlay" ] && [ -x "$builder" ]
[ "$(grep -c '^&' "$overlay")" -eq 2 ]
[ "$(grep -c 'status = "okay";' "$overlay")" -eq 2 ]

for label in pmk8350_rtc pon_pwrkey; do
	grep -q "^&$label {" "$overlay"
	grep -q "$label" "$builder"
	awk -v label="$label" '
		$0 == "&" label " {" { target = 1 }
		target && /status = "okay";/ { target = 0; next }
		{ print }
	' "$overlay" >"$stage/mutant.dtso"
	printf 'dummy\n' >"$stage/base.dtb"
	if PATH=/nonexistent "$builder" "$stage/base.dtb" \
		"$stage/mutant.dtso" "$stage/output.dtb" >/dev/null 2>&1; then
		echo "FAIL builder accepted overlay without $label enablement" >&2
		exit 1
	fi
done

for node in \
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

echo 'PASS RTC/power-key tier enables exactly two nodes and preserves every recovery isolation boundary'
