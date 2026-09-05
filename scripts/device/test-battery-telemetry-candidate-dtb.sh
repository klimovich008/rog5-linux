#!/bin/sh
set -eu

repo=$(CDPATH= cd -- "$(dirname "$0")/../.." && pwd)
adsp_overlay=$repo/dts/qcom/sm8350-asus-rog-phone5-adsp.dtso
pmic_overlay=$repo/dts/qcom/sm8350-asus-rog-phone5-pmic-glink.dtso
builder=$repo/scripts/device/build-battery-telemetry-candidate-dtb.sh
stage=$(mktemp -d)
trap 'rm -rf "$stage"' EXIT INT TERM

[ -r "$adsp_overlay" ] && [ -r "$pmic_overlay" ] && [ -x "$builder" ]
[ "$(grep -c '^&adsp {' "$adsp_overlay")" -eq 1 ]
[ "$(grep -c 'status = "okay";' "$adsp_overlay")" -eq 1 ]
[ "$(grep -c '^&{/} {' "$pmic_overlay")" -eq 1 ]
[ "$(grep -c '^[[:space:]]*pmic-glink {' "$pmic_overlay")" -eq 1 ]
! grep -Eq 'connector|orientation|gpio|nvmem|charge_limit' "$pmic_overlay"

awk '
	/^&adsp \{/ { target = 1 }
	target && /status = "okay";/ { target = 0; next }
	{ print }
' "$adsp_overlay" >"$stage/adsp-mutant.dtso"
printf 'dummy\n' >"$stage/base.dtb"
if PATH=/nonexistent "$builder" "$stage/base.dtb" \
	"$stage/adsp-mutant.dtso" "$pmic_overlay" "$stage/output.dtb" adsp \
	>/dev/null 2>&1; then
	echo 'FAIL builder accepted ADSP overlay without enablement' >&2
	exit 1
fi

sed '/qcom,pmic-glink/a\\\t\torientation-gpios = <1>;' \
	"$pmic_overlay" >"$stage/pmic-mutant.dtso"
if PATH=/nonexistent "$builder" "$stage/base.dtb" \
	"$adsp_overlay" "$stage/pmic-mutant.dtso" "$stage/output.dtb" telemetry \
	>/dev/null 2>&1; then
	echo 'FAIL builder accepted a USB-C orientation control' >&2
	exit 1
fi

for node in \
	/soc@0/spmi@c440000/pmic@0/rtc@6100 \
	/soc@0/ufshc@1d84000 \
	/soc@0/phy@1d87000 \
	/soc@0/phy@88e8000 \
	/soc@0/usb@a8f8800 \
	/reserved-memory/memory@9b800000 \
	/reserved-memory/memory@cbc00000 \
	/reserved-memory/memory@d8000000 \
	/reserved-memory/memory@edc00000 \
	/soc@0/gpu@3d00000 \
	/soc@0/gmu@3d6a000 \
	/soc@0/clock-controller@3d90000 \
	/soc@0/iommu@3da0000 \
	/soc@0/display-subsystem@ae00000
do
	grep -Fq "$node" "$builder"
done

if [ -n "${BASE_DTB:-}" ]; then
	[ -s "$BASE_DTB" ]
	for mode in adsp telemetry; do
		"$builder" "$BASE_DTB" "$adsp_overlay" "$pmic_overlay" \
			"$stage/$mode-one.dtb" "$mode" >/dev/null
		"$builder" "$BASE_DTB" "$adsp_overlay" "$pmic_overlay" \
			"$stage/$mode-two.dtb" "$mode" >/dev/null
		cmp "$stage/$mode-one.dtb" "$stage/$mode-two.dtb"
	done
fi

echo 'PASS battery-telemetry DT tiers are deterministic, minimal, and preserve every accepted recovery boundary'
