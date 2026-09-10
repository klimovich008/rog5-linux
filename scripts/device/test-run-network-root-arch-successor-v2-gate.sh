#!/bin/sh
# shellcheck disable=SC2016
set -eu

repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)
gate=$repo/scripts/device/run-network-root-arch-successor-v2-gate.sh

[ -x "$gate" ] || {
	echo 'FAIL missing Arch successor v2 target gate' >&2
	exit 1
}
sh -n "$gate"

for contract in \
	'ALLOW_ARCH_SUCCESSOR_V2_GATE' \
	'ALLOW_ARCH_SUCCESSOR_V2_REBOOT' \
	'7.1.4-g7a5cef0db479' \
	'/.rog5/root-ro/etc/rog5/arch-successor-v2-export' \
	'f7c39890f2777d9d95f963bf802a09fe3cbfdb863ac9f80392a61d01867796c4' \
	'169.254.77.1:/' \
	'169.254.77.2/30' \
	'systemd-udev-trigger.service' \
	'systemd-modules-load.service' \
	'systemd-sysusers.service' \
	'systemd-tmpfiles-setup.service' \
	'rog5-server-inhibit.service' \
	'rog5-chromium-headless.service' \
	'/usr/local/sbin/rog5-vpn-hotspot.sh' \
	'5e2b4af39227f3afd37a494474faf982f1a87f3e8807406e47196d92b3bb079d' \
	'rog5-vpn-hotspot.service' \
	'8ea3d2509bb220d200816571f379c2992c5281771be22d1b84d49d4a716cd814' \
	'rog5-ttyd.service' \
	'rog5-agent:x:961:961::/var/lib/rog5-agent:/usr/bin/nologin' \
	'package_count=655' \
	'/etc/machine-id' \
	'/.rog5/root-ro/etc/machine-id' \
	'/sys/class/backlight/*/brightness' \
	'/run/rog5-network-root-watchdog.pid' \
	'/run/rog5-network-root-watchdog.disarmed.pid' \
	'rog5-collect-baseline.sh' \
	'/run/rog5-arch-successor-v2-control/disarm-network-root-watchdog.sh' \
	'transition_watchdog=armed reboot=requested' \
	'systemctl reboot --no-block'
do
	grep -Fq "$contract" "$gate" || {
		echo "FAIL Arch successor v2 target gate omits: $contract" >&2
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

if grep -Fq 'arch-successor-v1' "$gate"; then
	echo 'FAIL Arch successor v2 target gate references v1' >&2
	exit 1
fi
if grep -Eq \
	'(^|[[:space:]])(fastboot|adb|ssh|scp)([[:space:]]|$)|dd[[:space:]].*of=/dev/|mount[[:space:]].*/dev/|hwclock.*--systohc' \
	"$gate"
then
	echo 'FAIL Arch successor v2 target gate controls host transport or storage' >&2
	exit 1
fi

set +e
"$gate" >/dev/null 2>&1
missing_guard=$?
set -e
[ "$missing_guard" -ne 0 ]

echo 'PASS Arch successor v2 target gate is first-boot, screen-off, storage-free, fail-closed-hotspot-pinned, watchdog-handed-off, and one-reboot'
