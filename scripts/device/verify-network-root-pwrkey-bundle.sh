#!/bin/sh
set -eu

artifact_dir=${1:?usage: verify-network-root-pwrkey-bundle.sh ARTIFACT_DIR MKBOOTIMG_DIR AVBTOOL EXPECTED_SHA256}
mkbootimg_dir=${2:?missing mkbootimg directory}
avbtool=${3:?missing avbtool}
expected_sums=${4:?missing SHA-256 manifest}
repo=$(CDPATH= cd -- "$(dirname "$0")/../.." && pwd)

"$repo/scripts/device/verify-network-root-bundle.sh" \
	"$artifact_dir" "$mkbootimg_dir" "$avbtool" "$expected_sums"

dtb=$artifact_dir/sm8350-asus-rog-phone5-recovery.dtb
config=$artifact_dir/config-7.1.4-network-root
rtc=/soc@0/spmi@c440000/pmic@0/rtc@6100
pwrkey=/soc@0/spmi@c440000/pmic@0/pon@1300/pwrkey

[ "$(fdtget -t s "$dtb" "$rtc" status)" = disabled ]
[ "$(fdtget -t s "$dtb" "$pwrkey" status)" = okay ]
[ "$(fdtget -t s "$dtb" "$pwrkey" compatible)" = qcom,pmk8350-pwrkey ]
[ "$(fdtget -t x "$dtb" "$pwrkey" linux,code)" = 74 ]
grep -qx 'CONFIG_INPUT_PM8941_PWRKEY=y' "$config"

echo 'PASS isolated power-key bundle; RTC and every recovery boundary remain disabled'
