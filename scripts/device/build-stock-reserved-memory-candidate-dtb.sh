#!/bin/sh
set -eu

base=${1:?usage: build-stock-reserved-memory-candidate-dtb.sh BASE_DTB OVERLAY OUTPUT}
overlay=${2:?missing stock reserved-memory overlay}
output=${3:?missing output}

[ -s "$base" ] && [ -r "$overlay" ] || {
	echo 'FAIL missing DTB input' >&2
	exit 1
}

[ "$(grep -c '^&reserved_memory {' "$overlay")" -eq 1 ]
[ "$(grep -c '^[[:space:]]*memory@' "$overlay")" -eq 3 ]
[ "$(grep -c '^[[:space:]]*reg = ' "$overlay")" -eq 3 ]
[ "$(grep -c '^[[:space:]]*no-map;' "$overlay")" -eq 1 ]
grep -Fq 'reg = <0x0 0xcbc00000 0x0 0x04400000>;' "$overlay"
grep -Fq 'reg = <0x0 0xd8000000 0x0 0x00800000>;' "$overlay"
grep -Fq 'reg = <0x0 0xedc00000 0x0 0x12000000>;' "$overlay"
! grep -Eq 'reusable|compatible[[:space:]]*=|status[[:space:]]*=|/delete-|bootargs|supply|memory-region|ufs_|usb_|gpu|gmu|rmtfs|mdss|dsi|panel|touch' \
	"$overlay"

stage=$(mktemp -d)
trap 'rm -rf "$stage"' EXIT INT TERM
dtc -q -@ -I dts -O dtb -o "$stage/stock-reserved-memory.dtbo" \
	"$overlay"
mkdir -p "$(dirname "$output")"
fdtoverlay -i "$base" -o "$output.tmp" \
	"$stage/stock-reserved-memory.dtbo"
mv "$output.tmp" "$output"
dtc -q -I dtb -O dts -o /dev/null "$output"

low=/reserved-memory/memory@cbc00000
memshare=/reserved-memory/memory@d8000000
high=/reserved-memory/memory@edc00000
[ "$(fdtget -t x "$output" "$low" reg)" = '0 cbc00000 0 4400000' ]
[ "$(fdtget -t x "$output" "$memshare" reg)" = '0 d8000000 0 800000' ]
[ "$(fdtget -t x "$output" "$high" reg)" = '0 edc00000 0 12000000' ]
! fdtget "$output" "$low" no-map >/dev/null 2>&1
fdtget "$output" "$memshare" no-map >/dev/null
! fdtget "$output" "$high" no-map >/dev/null 2>&1

fdtget -l "$base" /reserved-memory | sort >"$stage/base-children"
fdtget -l "$output" /reserved-memory | sort >"$stage/output-children"
comm -13 "$stage/base-children" "$stage/output-children" \
	>"$stage/added-children"
[ "$(cat "$stage/added-children")" = 'memory@cbc00000
memory@d8000000
memory@edc00000' ]
[ "$(comm -23 "$stage/base-children" "$stage/output-children" | wc -l)" -eq 0 ]

[ "$(fdtget -t x "$output" /memory@80000000 reg)" = \
	'0 80000000 0 37100000 2 0 1 80000000 0 c0000000 1 40000000 0 b9500000 0 0' ]
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
	[ "$(fdtget -t s "$output" "$node" status)" = disabled ]
done
for node in /soc@0/usb@a6f8800 /soc@0/phy@88e3000; do
	[ "$(fdtget -t s "$output" "$node" status)" = okay ]
done

sha256sum "$output"
echo 'PASS stock reserved-memory candidate adds only the three recovered board spans and preserves every recovery boundary'
