#!/bin/sh
# shellcheck disable=SC2016
set -eu

repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)
gate=$repo/scripts/device/run-network-root-a660-ucode-allocation-gate.sh

[ -x "$gate" ] || {
	echo 'FAIL missing compound A660 ucode-allocation gate' >&2
	exit 1
}
sh -n "$gate"

for contract in \
	'ALLOW_MAINLINE_A660_UCODE_ALLOCATION_GATE' \
	'ALLOW_MAINLINE_A660_UCODE_ALLOCATION_REBOOT' \
	'7.1.4-rog5-a660reg1' \
	'/run/rog5-network-root-watchdog.pid' \
	'/run/rog5-network-root-watchdog.disarmed.pid' \
	'/.rog5/root-ro/usr/local/sbin/rog5-a660-ucode-allocation-baseline' \
	'/.rog5/root-ro/usr/local/sbin/rog5-a660-ucode-allocation-probe' \
	'/run/rog5-a660-ucode-allocation-control/disarm-network-root-a660-watchdog.sh' \
	4f2e50fd492c9fff06198396c1fd80fa877b1447f18920d9895ad82c4034e041 \
	63adc85bdd3b4f5b08130722d30615fad1a439eb3aa2a43a4b161e826c36c3ef \
	733a2ba85e192e982883de1afee04e9fee0d137d737a611ad0914f185885fbbc \
	'transition_timeout=240' \
	'/run/rog5-a660-ucode-allocation-transition.' \
	'exec 9>/proc/sysrq-trigger' \
	'echo b >&9' \
	'setsid sh -c' \
	'expected=OPEN_ERRNO=117' \
	'ALLOW_A660_NETWORK_ROOT_WATCHDOG_DISARM=1 "$disarm"' \
	'ALLOW_MAINLINE_A660_UCODE_ALLOCATION=1 "$probe"' \
	'systemctl reboot --no-block' \
	'maps=3 unmaps=3 closes=3 gem_frees=3 gem_snapshot=equal' \
	'transition_watchdog=armed reboot=requested'
do
	grep -Fq "$contract" "$gate" || {
		echo "FAIL compound ucode-allocation gate omits: $contract" >&2
		exit 1
	}
done

baseline_line=$(grep -n '^"\$baseline"$' "$gate" | cut -d: -f1)
arm_line=$(grep -n '^transition_pid=\$!$' "$gate" | cut -d: -f1)
disarm_line=$(grep -n \
	'^ALLOW_A660_NETWORK_ROOT_WATCHDOG_DISARM=1 "\$disarm"$' "$gate" |
	cut -d: -f1)
probe_line=$(grep -n \
	'^ALLOW_MAINLINE_A660_UCODE_ALLOCATION=1 "\$probe"$' "$gate" |
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
[ "$(grep -Fc 'ALLOW_MAINLINE_A660_UCODE_ALLOCATION=1 "$probe"' \
	"$gate")" -eq 1 ]
[ "$(grep -Fxc 'systemctl reboot --no-block' "$gate")" -eq 1 ]

if grep -Eq \
	'fastboot|adb|rmmod|modprobe[[:space:]].*(-r|--remove)|dd[[:space:]].*of=/dev/|mount[[:space:]].*/dev/' \
	"$gate"
then
	echo 'FAIL compound ucode-allocation gate controls host or writes storage' >&2
	exit 1
fi

set +e
"$gate" >/dev/null 2>&1
missing_guards=$?
ALLOW_MAINLINE_A660_UCODE_ALLOCATION_GATE=1 \
	ALLOW_MAINLINE_A660_UCODE_ALLOCATION_REBOOT=unsafe \
	"$gate" >/dev/null 2>&1
invalid_reboot_guard=$?
set -e
[ "$missing_guards" -ne 0 ]
[ "$invalid_reboot_guard" -ne 0 ]

echo 'PASS compound A660 ucode-allocation gate overlaps watchdogs, invokes one trace-backed probe, and immediately reboots'
