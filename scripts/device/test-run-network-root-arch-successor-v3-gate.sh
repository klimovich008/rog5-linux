#!/bin/sh
# shellcheck disable=SC2016
set -eu

repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)
gate=$repo/scripts/device/run-network-root-arch-successor-v3-gate.sh

[ -x "$gate" ] || {
	echo 'FAIL missing Arch successor v3 target gate' >&2
	exit 1
}
sh -n "$gate"

for contract in \
	'ALLOW_ARCH_SUCCESSOR_V3_GATE' \
	'ALLOW_ARCH_SUCCESSOR_V3_REBOOT' \
	'7.1.4-g7a5cef0db479' \
	'/.rog5/root-ro/etc/rog5/arch-successor-v3-export' \
	'26b4fcd8f21c5974d281d4b39386f82965265a31728c3a54877ab6717e98f2a7' \
	'a7c286491d2fde97e17024b36f514d595196975da1988c986f70819c964eb8d7' \
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
	'/usr/local/libexec/rog5-power-buttond' \
	'66b3a8bfc32434e450d10ea707e21481b991e6fc728cd7afa618664331b4298a' \
	'rog5-power-button.service' \
	'c617188753e17482328f69abc55c3d2b6da62dd543ecb3a14f551c4f17fb72c7' \
	'pmic_pwrkey' \
	'rog5-ttyd.service' \
	'rog5-agent:x:961:961::/var/lib/rog5-agent:/usr/bin/nologin' \
	'package_count=655' \
	'/etc/machine-id' \
	'/.rog5/root-ro/etc/machine-id' \
	'/sys/class/backlight/*/brightness' \
	'/run/rog5-network-root-watchdog.pid' \
	'/run/rog5-network-root-watchdog.disarmed.pid' \
	'rog5-collect-baseline.sh' \
	'/run/rog5-arch-successor-v3-control/disarm-network-root-watchdog.sh' \
	'power-button=active-input-present' \
	'transition_watchdog=armed reboot=requested' \
	'systemctl reboot --no-block'
do
	grep -Fq "$contract" "$gate" || {
		echo "FAIL Arch successor v3 target gate omits: $contract" >&2
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

if grep -Eq 'arch-successor-v[12]([^0-9]|$)' "$gate"; then
	echo 'FAIL Arch successor v3 target gate references a predecessor' >&2
	exit 1
fi
if grep -Eq \
	'(^|[[:space:]])(fastboot|adb|ssh|scp)([[:space:]]|$)|dd[[:space:]].*of=/dev/|mount[[:space:]].*/dev/|hwclock.*--systohc' \
	"$gate"
then
	echo 'FAIL Arch successor v3 target gate controls host transport or storage' >&2
	exit 1
fi

set +e
"$gate" >/dev/null 2>&1
missing_guard=$?
set -e
[ "$missing_guard" -ne 0 ]

echo 'PASS Arch successor v3 target gate is first-boot, screen-off, storage-free, power-input-pinned, fail-closed-hotspot-pinned, watchdog-handed-off, and one-reboot'
