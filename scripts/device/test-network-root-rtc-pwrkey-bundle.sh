#!/bin/sh
set -eu

repo=$(CDPATH= cd -- "$(dirname "$0")/../.." && pwd)
verifier=$repo/scripts/device/verify-network-root-rtc-pwrkey-bundle.sh
builder=$repo/scripts/device/build-rtc-pwrkey-candidate-dtb.sh

[ -x "$verifier" ] && [ -x "$builder" ]
sh -n "$verifier"

for contract in \
	'verify-network-root-bundle.sh' \
	'/soc@0/spmi@c440000/pmic@0/rtc@6100' \
	'/soc@0/spmi@c440000/pmic@0/pon@1300/pwrkey' \
	'allow-set-time' \
	'nvmem-cells' \
	'qcom,uefi-rtc-info' \
	'CONFIG_RTC_DRV_PM8XXX=m' \
	'CONFIG_INPUT_PM8941_PWRKEY=y' \
	'rtc-pm8xxx.ko'; do
	grep -Fq "$contract" "$verifier" || {
		echo "FAIL RTC/power-key bundle verifier omits: $contract" >&2
		exit 1
	}
done

if grep -Eq 'fastboot[[:space:]]+flash|dd[[:space:]].*of=/dev/|hwclock.*--systohc' \
	"$verifier" "$builder"; then
	echo 'FAIL RTC/power-key offline tools contain a persistent-write command' >&2
	exit 1
fi

echo 'PASS RTC/power-key bundle contract is storage-safe, non-writing, and layered over the full network-root verifier'
