#!/bin/sh
set -eu

repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)
builder=$repo/scripts/device/build-ufs-phy-disabled-control-dtb.sh
enable_builder=$repo/scripts/device/build-ufs-discovery-candidate-dtb.sh
base=$repo/artifacts/buttons-indicator-v1/sm8350-asus-rog-phone5-buttons-indicator.dtb
enable_overlay=$repo/dts/qcom/sm8350-asus-rog-phone5-ufs-discovery.dtso
control_overlay=$repo/dts/qcom/sm8350-asus-rog-phone5-ufs-phy-disabled-control.dtso
stage=$(mktemp -d)
trap 'rm -rf -- "$stage"' EXIT HUP INT TERM

[ -x "$builder" ] && [ -x "$enable_builder" ]
"$enable_builder" "$base" "$enable_overlay" "$stage/enabled.dtb" >/dev/null
"$builder" "$stage/enabled.dtb" "$control_overlay" "$stage/control.dtb" \
	>/dev/null

[ "$(fdtget -t s "$stage/control.dtb" /soc@0/ufshc@1d84000 status)" = okay ]
[ "$(fdtget -t s "$stage/control.dtb" /soc@0/phy@1d87000 status)" = disabled ]
[ "$(fdtget -t s "$stage/control.dtb" /soc@0/usb@a6f8800 status)" = okay ]
[ "$(fdtget -t s "$stage/control.dtb" /gpio-keys/key-volume-up label)" = volume_up ]

cp "$control_overlay" "$stage/hostile.dtso"
cat >>"$stage/hostile.dtso" <<'EOF'
&ufs_mem_hc {
	status = "disabled";
};
EOF
if "$builder" "$stage/enabled.dtb" "$stage/hostile.dtso" \
	"$stage/rejected.dtb" >"$stage/rejected.log" 2>&1; then
	echo 'FAIL control builder accepted a second node mutation' >&2
	exit 1
fi
grep -Fxq 'FAIL control overlay targets another node' "$stage/rejected.log"

echo 'PASS hostile one-property UFS-PHY-disabled control DTB contract'
