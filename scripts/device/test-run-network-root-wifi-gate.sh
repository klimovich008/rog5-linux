#!/bin/sh
# shellcheck disable=SC2016
set -eu

repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)
gate=$repo/scripts/device/run-network-root-wifi-gate.sh

[ -x "$gate" ] || {
	echo 'FAIL missing executable Wi-Fi target gate' >&2
	exit 1
}
sh -n "$gate"

for contract in \
	'ALLOW_MAINLINE_WCN6855_GATE' \
	'ALLOW_MAINLINE_WCN6855_REBOOT' \
	'7.1.4-g7a5cef0db479' \
	'/.rog5/root-ro/etc/rog5/wifi-enumeration-v1' \
	'/run/rog5-network-root-watchdog.pid' \
	'/run/rog5-network-root-watchdog.disarmed.pid' \
	'disarm-network-root-watchdog.sh' \
	'rog5-wifi-enumeration-probe' \
	'transition_timeout=240' \
	'setsid sh -c' \
	'ALLOW_NETWORK_ROOT_WATCHDOG_DISARM=1' \
	'ALLOW_MAINLINE_WCN6855_ENUMERATION_PROBE=1' \
	'systemctl reboot --no-block' \
	'PASS compound WCN6855 enumeration-only gate'
do
	grep -Fq "$contract" "$gate" || {
		echo "FAIL Wi-Fi target gate omits: $contract" >&2
		exit 1
	}
done

transition_line=$(grep -n '^setsid sh -c' "$gate" | cut -d: -f1)
disarm_line=$(grep -n \
	'ALLOW_NETWORK_ROOT_WATCHDOG_DISARM=1' "$gate" | cut -d: -f1)
probe_line=$(grep -n \
	'ALLOW_MAINLINE_WCN6855_ENUMERATION_PROBE=1' "$gate" | cut -d: -f1)
reboot_line=$(grep -n '^systemctl reboot --no-block$' "$gate" |
	cut -d: -f1)
[ "$transition_line" -lt "$disarm_line" ]
[ "$disarm_line" -lt "$probe_line" ]
[ "$probe_line" -lt "$reboot_line" ]
[ "$(grep -Fxc 'systemctl reboot --no-block' "$gate")" -eq 1 ]
[ "$(grep -Fc 'ALLOW_MAINLINE_WCN6855_ENUMERATION_PROBE=1' "$gate")" -eq 1 ]

if grep -Eq \
	'(^|[;&|[:space:]])(fastboot|adb|ssh|scp|nmcli|hostapd|wpa_supplicant)([[:space:]]|$)|dd[[:space:]].*of=/dev/|mount[[:space:]].*/dev/' \
	"$gate"
then
	echo 'FAIL Wi-Fi target gate controls host transport, association, hotspot, or storage' >&2
	exit 1
fi

set +e
"$gate" >/dev/null 2>&1
missing_guards=$?
set -e
[ "$missing_guards" -ne 0 ]

echo 'PASS Wi-Fi target gate is explicit, watchdog-handed-off, enumeration-only, one-probe, one-reboot, and no-retry'
