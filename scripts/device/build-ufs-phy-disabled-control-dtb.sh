#!/bin/sh
set -eu

base=${1:?usage: build-ufs-phy-disabled-control-dtb.sh BASE_DTB OVERLAY OUTPUT}
overlay=${2:?missing fixed control overlay}
output=${3:?missing output}

fail() {
	echo "FAIL $*" >&2
	exit 1
}

[ -f "$base" ] && [ ! -L "$base" ] && [ -r "$base" ] ||
	fail 'unsafe base DTB'
[ -f "$overlay" ] && [ ! -L "$overlay" ] && [ -r "$overlay" ] ||
	fail 'unsafe control overlay'

ufs_hc=/soc@0/ufshc@1d84000
ufs_phy=/soc@0/phy@1d87000
[ "$(fdtget -t s "$base" "$ufs_hc" status)" = okay ] ||
	fail 'base UFS host is not enabled'
[ "$(fdtget -t s "$base" "$ufs_phy" status)" = okay ] ||
	fail 'base UFS PHY is not enabled'

[ "$(grep -c '^&ufs_mem_phy {' "$overlay")" -eq 1 ] ||
	fail 'control overlay must target the UFS PHY exactly once'
[ "$(grep -c '^&' "$overlay")" -eq 1 ] ||
	fail 'control overlay targets another node'
[ "$(grep -c 'status = "disabled";' "$overlay")" -eq 1 ] ||
	fail 'control overlay lacks one disabled status'
! grep -Eq '^&ufs_mem_hc|^&usb_|supply[[:space:]]*=|reg[[:space:]]*=|bootargs|/delete-' \
	"$overlay" || fail 'control overlay changes an unreviewed property'

stage=$(mktemp -d)
trap 'rm -rf -- "$stage"' EXIT HUP INT TERM
dtc -q -@ -I dts -O dtb -o "$stage/control.dtbo" "$overlay"
mkdir -p "$(dirname "$output")"
fdtoverlay -i "$base" -o "$output.tmp" "$stage/control.dtbo"
mv -T -- "$output.tmp" "$output"
dtc -q -I dtb -O dts -o /dev/null "$output"

[ "$(fdtget -t s "$output" "$ufs_hc" status)" = okay ] ||
	fail 'control changed the UFS host status'
[ "$(fdtget -t s "$output" "$ufs_phy" status)" = disabled ] ||
	fail 'control did not disable the UFS PHY'
for property in compatible reg clocks clock-names power-domains resets \
	reset-names vdda-phy-supply vdda-pll-supply; do
	[ "$(fdtget "$output" "$ufs_phy" "$property")" = \
		"$(fdtget "$base" "$ufs_phy" "$property")" ] ||
		fail "control changed UFS PHY property: $property"
done

sha256sum "$output"
echo 'PASS one-property UFS-PHY-disabled module-load control DTB'
