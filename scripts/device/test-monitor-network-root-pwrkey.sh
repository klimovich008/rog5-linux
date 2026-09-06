#!/bin/sh
set -eu

repo=$(CDPATH= cd -- "$(dirname "$0")/../.." && pwd)
monitor=$repo/scripts/device/monitor-network-root-pwrkey.sh

[ -x "$monitor" ]
sh -n "$monitor"

for contract in \
	'ALLOW_PWRKEY_MONITOR' \
	'timeout must be between 30 and 300 seconds' \
	'7.1.4-g7a5cef0db479' \
	'physical input acceptance requires normal unmasked mode' \
	'findmnt -n -o SOURCE /.rog5/root-ro' \
	'physical block device is present' \
	'block-backed mount is present' \
	'169.254.77.2/30' \
	'systemd has failed units' \
	'/run/rog5-network-root-watchdog.disarmed.pid' \
	'/soc@0/spmi@c440000/pmic@0/rtc@6100' \
	'/sys/module/rtc_pm8xxx' \
	'/sys/module/qcom_pon' \
	'pmic_pwrkey' \
	'pm8941-pwrkey' \
	'qcom,pmk8350-pwrkey' \
	'capabilities/key' \
	'0x10000000000000' \
	'systemd-inhibit' \
	'handle-power-key' \
	'event_struct.size != 24' \
	'event_type != 1 or code != 116' \
	'value == 1' \
	'value == 0 and pressed'; do
	grep -Fq "$contract" "$monitor" || {
		echo "FAIL power-key monitor contract missing: $contract" >&2
		exit 1
	}
done

if grep -Eq 'modprobe|hwclock.*--systohc|date[[:space:]]+(-s|--set)|devmem|fastboot[[:space:]]+flash|dd[[:space:]].*of=/dev/' \
	"$monitor"; then
	echo 'FAIL power-key monitor loads modules or writes device state' >&2
	exit 1
fi

set +e
"$monitor" >/dev/null 2>&1
missing_guard=$?
ALLOW_PWRKEY_MONITOR=1 "$monitor" invalid >/dev/null 2>&1
invalid_timeout=$?
set -e
[ "$missing_guard" -ne 0 ]
[ "$invalid_timeout" -ne 0 ]

echo 'PASS attended power-key monitor is explicit, storage-safe, normal-mode-only, and logind-inhibited'
