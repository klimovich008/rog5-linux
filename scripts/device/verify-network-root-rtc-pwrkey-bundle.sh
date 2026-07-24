#!/bin/sh
set -eu

artifact_dir=${1:?usage: verify-network-root-rtc-pwrkey-bundle.sh ARTIFACT_DIR MKBOOTIMG_DIR AVBTOOL EXPECTED_SHA256}
mkbootimg_dir=${2:?missing mkbootimg directory}
avbtool=${3:?missing avbtool}
expected_sums=${4:?missing expected SHA-256 manifest}
repo=$(CDPATH= cd -- "$(dirname "$0")/../.." && pwd)

"$repo/scripts/device/verify-network-root-bundle.sh" \
	"$artifact_dir" "$mkbootimg_dir" "$avbtool" "$expected_sums"

dtb=$artifact_dir/sm8350-asus-rog-phone5-recovery.dtb
config=$artifact_dir/config-7.1.4-network-root
modules=$artifact_dir/modules-7.1.4-network-root.tar.gz
rtc=/soc@0/spmi@c440000/pmic@0/rtc@6100
pwrkey=/soc@0/spmi@c440000/pmic@0/pon@1300/pwrkey

[ "$(fdtget -t s "$dtb" "$rtc" status)" = okay ]
[ "$(fdtget -t s "$dtb" "$pwrkey" status)" = okay ]
[ "$(fdtget -t s "$dtb" "$rtc" compatible)" = qcom,pmk8350-rtc ]
[ "$(fdtget -t s "$dtb" "$pwrkey" compatible)" = qcom,pmk8350-pwrkey ]
[ "$(fdtget -t x "$dtb" "$pwrkey" linux,code)" = 74 ]
for property in allow-set-time nvmem-cells qcom,uefi-rtc-info; do
	if fdtget "$dtb" "$rtc" "$property" >/dev/null 2>&1; then
		echo "FAIL RTC tier permits persistent time writes through $property" >&2
		exit 1
	fi
done

grep -qx 'CONFIG_RTC_CLASS=y' "$config"
grep -qx 'CONFIG_RTC_HCTOSYS=y' "$config"
grep -qx 'CONFIG_RTC_HCTOSYS_DEVICE="rtc0"' "$config"
grep -qx 'CONFIG_RTC_DRV_PM8XXX=m' "$config"
grep -qx 'CONFIG_INPUT_PM8941_PWRKEY=y' "$config"
tar -tzf "$modules" |
	grep -qx 'lib/modules/7.1.4-g7a5cef0db479/kernel/drivers/rtc/rtc-pm8xxx.ko'

echo 'PASS isolated RTC/power-key bundle; RTC has no persistent-write/offset property and every recovery boundary remains intact'
