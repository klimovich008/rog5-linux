#!/bin/sh
set -eu

repo=$(CDPATH= cd -- "$(dirname "$0")/../.." && pwd)
overlay=$repo/dts/qcom/sm8350-asus-rog-phone5-stock-reserved-memory.dtso
builder=$repo/scripts/device/build-stock-reserved-memory-candidate-dtb.sh
stage=$(mktemp -d)
trap 'rm -rf "$stage"' EXIT INT TERM

[ -r "$overlay" ] && [ -x "$builder" ]
[ "$(grep -c '^&reserved_memory {' "$overlay")" -eq 1 ]
[ "$(grep -c '^[[:space:]]*memory@' "$overlay")" -eq 3 ]
[ "$(grep -c '^[[:space:]]*no-map;' "$overlay")" -eq 1 ]

printf 'dummy\n' >"$stage/base.dtb"
sed 's/0x04400000/0x04500000/' "$overlay" >"$stage/size-mutant.dtso"
if PATH=/nonexistent "$builder" "$stage/base.dtb" \
	"$stage/size-mutant.dtso" "$stage/output.dtb" >/dev/null 2>&1; then
	echo 'FAIL builder accepted a changed low reservation size' >&2
	exit 1
fi

sed '/^[[:space:]]*no-map;/d' "$overlay" >"$stage/map-mutant.dtso"
if PATH=/nonexistent "$builder" "$stage/base.dtb" \
	"$stage/map-mutant.dtso" "$stage/output.dtb" >/dev/null 2>&1; then
	echo 'FAIL builder accepted a mapped memshare reservation' >&2
	exit 1
fi

sed '/memory@edc00000 {/a\\\t\tstatus = "okay";' \
	"$overlay" >"$stage/property-mutant.dtso"
if PATH=/nonexistent "$builder" "$stage/base.dtb" \
	"$stage/property-mutant.dtso" "$stage/output.dtb" >/dev/null 2>&1; then
	echo 'FAIL builder accepted an unrelated reservation property' >&2
	exit 1
fi

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
	/soc@0/display-subsystem@ae00000
do
	grep -Fq "$node" "$builder"
done

if [ -n "${BASE_DTB:-}" ]; then
	[ -s "$BASE_DTB" ]
	"$builder" "$BASE_DTB" "$overlay" "$stage/one.dtb" >/dev/null
	"$builder" "$BASE_DTB" "$overlay" "$stage/two.dtb" >/dev/null
	cmp "$stage/one.dtb" "$stage/two.dtb"
fi

echo 'PASS stock reserved-memory candidate is exact, deterministic, mutation-tested, and isolated from device enablement'
