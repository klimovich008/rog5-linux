#!/bin/sh
set -eu

repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)
gate=$repo/scripts/device/run-network-root-a660-registration-gate.sh

[ -x "$gate" ] || {
	echo 'FAIL missing compound A660 registration gate' >&2
	exit 1
}
sh -n "$gate"

for contract in \
	'ALLOW_MAINLINE_A660_REGISTRATION_GATE' \
	'ALLOW_MAINLINE_A660_REGISTRATION_REBOOT' \
	'7.1.4-rog5-a660reg1' \
	'/run/rog5-network-root-watchdog.pid' \
	'/run/rog5-network-root-watchdog.disarmed.pid' \
	'/.rog5/root-ro/usr/local/sbin/rog5-a660-registration-baseline' \
	'/.rog5/root-ro/usr/local/sbin/rog5-a660-registration-probe' \
	'/run/rog5-a660-registration-control/disarm-network-root-a660-watchdog.sh' \
	6e6f7ba046c7db642bdd18905396877a68fd042a92d5ea9383f5be52701c76e8 \
	0e0d8894b1a54d070458483d3752ee2d1a0a167b2bfe3992853284e91d7607e6 \
	733a2ba85e192e982883de1afee04e9fee0d137d737a611ad0914f185885fbbc \
	'transition_timeout=180' \
	'/run/rog5-a660-registration-transition.' \
	'exec 9>/proc/sysrq-trigger' \
	'echo b >&9' \
	'setsid sh -c' \
	'ALLOW_A660_NETWORK_ROOT_WATCHDOG_DISARM=1 "$disarm"' \
	'ALLOW_MAINLINE_A660_REGISTRATION=1 "$probe"' \
	'systemctl reboot --no-block' \
	'transition_watchdog=armed reboot=requested'
do
	grep -Fq "$contract" "$gate" || {
		echo "FAIL compound A660 registration gate omits: $contract" >&2
		exit 1
	}
done

baseline_line=$(grep -n '^"\$baseline"$' "$gate" | cut -d: -f1)
arm_line=$(grep -n '^transition_pid=\$!$' "$gate" | cut -d: -f1)
disarm_line=$(grep -n \
	'^ALLOW_A660_NETWORK_ROOT_WATCHDOG_DISARM=1 "\$disarm"$' "$gate" |
	cut -d: -f1)
probe_line=$(grep -n \
	'^ALLOW_MAINLINE_A660_REGISTRATION=1 "\$probe"$' "$gate" |
	cut -d: -f1)
reboot_line=$(grep -n '^systemctl reboot --no-block$' "$gate" |
	cut -d: -f1)
[ "$baseline_line" -lt "$arm_line" ]
[ "$arm_line" -lt "$disarm_line" ]
[ "$disarm_line" -lt "$probe_line" ]
[ "$probe_line" -lt "$reboot_line" ]
[ "$(grep -Fxc '"$baseline"' "$gate")" -eq 1 ]
[ "$(grep -Fc 'ALLOW_A660_NETWORK_ROOT_WATCHDOG_DISARM=1 "$disarm"' \
	"$gate")" -eq 1 ]
[ "$(grep -Fc 'ALLOW_MAINLINE_A660_REGISTRATION=1 "$probe"' \
	"$gate")" -eq 1 ]

if grep -Eq \
	'fastboot|adb|rmmod|modprobe[[:space:]].*(-r|--remove)|dd[[:space:]].*of=/dev/|mount[[:space:]].*/dev/' \
	"$gate"
then
	echo 'FAIL compound A660 gate controls the host or writes storage' >&2
	exit 1
fi

set +e
"$gate" >/dev/null 2>&1
missing_guards=$?
ALLOW_MAINLINE_A660_REGISTRATION_GATE=1 \
	ALLOW_MAINLINE_A660_REGISTRATION_REBOOT=unsafe \
	"$gate" >/dev/null 2>&1
invalid_reboot_guard=$?
set -e
[ "$missing_guards" -ne 0 ]
[ "$invalid_reboot_guard" -ne 0 ]

echo 'PASS compound A660 gate overlaps rollback watchdogs, probes once, and reboots'
