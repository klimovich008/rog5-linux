#!/bin/sh
# shellcheck disable=SC2016
set -eu

repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)
gate=$repo/scripts/device/run-network-root-arch-successor-v1-gate.sh

[ -x "$gate" ] || {
	echo 'FAIL missing Arch successor v1 target gate' >&2
	exit 1
}
sh -n "$gate"

for contract in \
	'ALLOW_ARCH_SUCCESSOR_V1_GATE' \
	'ALLOW_ARCH_SUCCESSOR_V1_REBOOT' \
	'7.1.4-g7a5cef0db479' \
	'/.rog5/root-ro/etc/rog5/arch-successor-v1-export' \
	'6b5fa1b8e93b7e9f1ad41788ca524d5be6b4195c28ce85f70a28143360109eb4' \
	'169.254.77.1:/' \
	'169.254.77.2/30' \
	'systemd-udev-trigger.service' \
	'systemd-modules-load.service' \
	'systemd-sysusers.service' \
	'systemd-tmpfiles-setup.service' \
	'rog5-server-inhibit.service' \
	'rog5-chromium-headless.service' \
	'rog5-vpn-hotspot.service' \
	'rog5-ttyd.service' \
	'rog5-agent:x:961:961::/var/lib/rog5-agent:/usr/bin/nologin' \
	'package_count=655' \
	'/etc/machine-id' \
	'/.rog5/root-ro/etc/machine-id' \
	'/sys/class/backlight/*/brightness' \
	'/run/rog5-network-root-watchdog.pid' \
	'/run/rog5-network-root-watchdog.disarmed.pid' \
	'rog5-collect-baseline.sh' \
	'disarm-network-root-watchdog.sh' \
	'transition_watchdog=armed reboot=requested' \
	'systemctl reboot --no-block'
do
	grep -Fq "$contract" "$gate" || {
		echo "FAIL Arch successor target gate omits: $contract" >&2
		exit 1
	}
done

transition_line=$(grep -n '^setsid sh -c' "$gate" | cut -d: -f1)
disarm_line=$(grep -n \
	'ALLOW_NETWORK_ROOT_WATCHDOG_DISARM=1 "\$disarm"' "$gate" |
	cut -d: -f1)
reboot_line=$(grep -n '^systemctl reboot --no-block$' "$gate" |
	cut -d: -f1)
[ "$transition_line" -lt "$disarm_line" ]
[ "$disarm_line" -lt "$reboot_line" ]
[ "$(grep -Fxc 'systemctl reboot --no-block' "$gate")" -eq 1 ]

if grep -Eq \
	'(^|[[:space:]])(fastboot|adb|ssh|scp)([[:space:]]|$)|dd[[:space:]].*of=/dev/|mount[[:space:]].*/dev/|hwclock.*--systohc' \
	"$gate"
then
	echo 'FAIL Arch successor target gate controls host transport or storage' >&2
	exit 1
fi

set +e
"$gate" >/dev/null 2>&1
missing_guard=$?
set -e
[ "$missing_guard" -ne 0 ]

echo 'PASS Arch successor v1 target gate is first-boot, screen-off, storage-free, watchdog-handed-off, and one-reboot'
