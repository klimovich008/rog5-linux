#!/bin/sh
set -eu

repo=$(CDPATH= cd -- "$(dirname "$0")/../.." && pwd)
probe=$repo/scripts/device/probe-network-root-pwrkey.sh

[ -x "$probe" ]
sh -n "$probe"

for contract in \
	'ALLOW_PWRKEY_PROBE' \
	'phase must be pre or post' \
	'7.1.4-g7a5cef0db479' \
	'systemd-udev-trigger.service' \
	'systemd-modules-load.service' \
	'/run/systemd/generator.early/$unit' \
	'/run/rog5-network-root-watchdog.pid' \
	'/run/rog5-network-root-watchdog.disarmed.pid' \
	'/sys/module/qcom_pon' \
	'findmnt -n -o SOURCE /.rog5/root-ro' \
	'physical block device is present' \
	'block-backed mount is present' \
	'/sys/class/net/usb0/carrier' \
	'/soc@0/spmi@c440000/pmic@0/rtc@6100' \
	'/soc@0/spmi@c440000/pmic@0/pon@1300/pwrkey' \
	'allow-set-time' \
	'nvmem-cells' \
	'qcom,uefi-rtc-info' \
	'/sys/module/rtc_pm8xxx' \
	'pmic_pwrkey' \
	'/device/device' \
	'pm8941-pwrkey' \
	'qcom,pmk8350-pwrkey' \
	'capabilities/key' \
	'0x10000000000000' \
	'power/wakeup' \
	'Kernel panic|Oops:|BUG:'; do
	grep -Fq "$contract" "$probe" || {
		echo "FAIL power-key probe contract missing: $contract" >&2
		exit 1
	}
done

if grep -Eq 'modprobe|hwclock.*--systohc|date[[:space:]]+(-s|--set)|devmem|fastboot[[:space:]]+flash|dd[[:space:]].*of=/dev/' \
	"$probe"; then
	echo 'FAIL diagnostic power-key probe loads RTC or writes device state' >&2
	exit 1
fi

set +e
"$probe" >/dev/null 2>&1
missing_guard=$?
ALLOW_PWRKEY_PROBE=1 "$probe" invalid >/dev/null 2>&1
invalid_phase=$?
set -e
[ "$missing_guard" -ne 0 ]
[ "$invalid_phase" -ne 0 ]

echo 'PASS diagnostic power-key pre/post probe is explicit, storage-safe, and requires RTC to remain disabled'
