#!/bin/sh
set -eu

fail() {
	echo "FAIL $*" >&2
	exit 1
}

[ "${ALLOW_PWRKEY_PROBE:-}" = 1 ] ||
	fail 'set ALLOW_PWRKEY_PROBE=1 for one attended diagnostic boot'
phase=${1:-}
case $phase in
	pre|post) ;;
	*) fail 'phase must be pre or post' ;;
esac
[ "$(uname -r)" = 7.1.4-g7a5cef0db479 ] || fail 'unexpected kernel'
[ "$(cat /proc/1/comm)" = systemd ] || fail 'PID 1 is not systemd'
system_state=
for unused in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15; do
	system_state=$(systemctl is-system-running 2>/dev/null || true)
	[ "$system_state" != running ] || break
	case $system_state in
		starting|initializing) sleep 1 ;;
		*) break ;;
	esac
done
[ "$system_state" = running ] || fail 'systemd is not running'
for unit in systemd-udev-trigger.service systemd-modules-load.service; do
	state=$(systemctl is-enabled "$unit" 2>/dev/null || true)
	case $state in masked|masked-runtime) ;; *)
		fail "$unit is not diagnostic-masked" ;;
	esac
	[ "$(readlink -f "/run/systemd/generator.early/$unit")" = /dev/null ] ||
		fail "$unit has no runtime generator mask"
done
case $phase in
	pre)
		[ -s /run/rog5-network-root-watchdog.pid ] ||
			fail 'network-root rollback watchdog is not armed'
		[ ! -e /run/rog5-network-root-watchdog.disarmed.pid ] ||
			fail 'network-root rollback already has a disarm marker'
		[ ! -d /sys/module/qcom_pon ] ||
			fail 'qcom_pon loaded before the guarded probe'
		;;
	post)
		[ ! -e /run/rog5-network-root-watchdog.pid ] ||
			fail 'network-root rollback watchdog is still armed'
		[ -s /run/rog5-network-root-watchdog.disarmed.pid ] ||
			fail 'missing network-root watchdog disarm marker'
		[ -d /sys/module/qcom_pon ] ||
			fail 'qcom_pon did not remain loaded'
		;;
esac

[ "$(findmnt -n -o FSTYPE /)" = overlay ] || fail 'root is not OverlayFS'
[ "$(findmnt -n -o SOURCE /.rog5/root-ro)" = 169.254.77.1:/ ] ||
	fail 'unexpected NFS lower source'
[ "$(find /sys/class/block -mindepth 1 -maxdepth 1 -type l \
	-exec test -e {}/device \; -print 2>/dev/null | wc -l)" -eq 0 ] ||
	fail 'physical block device is present'
[ "$(findmnt -rn -o SOURCE |
	awk '/^\/dev\// { count++ } END { print count + 0 }')" -eq 0 ] ||
	fail 'block-backed mount is present'
[ "$(cat /sys/class/net/usb0/carrier)" = 1 ] ||
	fail 'USB network carrier is down'

dt=/sys/firmware/devicetree/base
rtc_node=$dt/soc@0/spmi@c440000/pmic@0/rtc@6100
pwrkey_node=$dt/soc@0/spmi@c440000/pmic@0/pon@1300/pwrkey
[ "$(tr -d '\000' <"$rtc_node/status")" = disabled ] ||
	fail 'RTC node is not disabled'
[ "$(tr -d '\000' <"$pwrkey_node/status")" = okay ] ||
	fail 'power-key node is not enabled'
for property in allow-set-time nvmem-cells qcom,uefi-rtc-info; do
	[ ! -e "$rtc_node/$property" ] ||
		fail "RTC node permits persistent writes through $property"
done

[ ! -d /sys/module/rtc_pm8xxx ] ||
	fail 'RTC module loaded before the guarded probe'
[ "$(find /sys/class/rtc -mindepth 1 -maxdepth 1 -name 'rtc*' 2>/dev/null |
	wc -l)" -eq 0 ] || fail 'RTC registered before the guarded probe'

pwrkey_events=0
for event in /sys/class/input/event*; do
	[ -r "$event/device/name" ] || continue
	device=$event/device/device
	[ -L "$device/driver" ] || continue
	[ "$(basename "$(readlink -f "$device/driver")")" = \
		pm8941-pwrkey ] || continue
	[ "$(cat "$event/device/name")" = pmic_pwrkey ] ||
		fail 'power key has an unexpected input name'
	[ -r "$device/of_node/compatible" ] ||
		fail 'power key has no device-tree identity'
	tr '\000' '\n' <"$device/of_node/compatible" |
		grep -qx 'qcom,pmk8350-pwrkey' ||
		fail 'power key bound to an unexpected device-tree node'
	[ -r "$event/device/capabilities/key" ] ||
		fail 'power key has no key-capability bitmap'
	# AArch64 sysfs prints 64-bit words high-to-low. KEY_POWER (116) is
	# bit 52 in the second word from the right.
	set -- $(cat "$event/device/capabilities/key")
	[ "$#" -ge 2 ] ||
		fail 'power-key capability bitmap is too short'
	while [ "$#" -gt 2 ]; do
		shift
	done
	key_power_word=$1
	case $key_power_word in
		*[!0-9a-fA-F]*|'') fail 'invalid power-key capability bitmap' ;;
	esac
	[ $((0x$key_power_word & 0x10000000000000)) -ne 0 ] ||
		fail 'input event does not advertise KEY_POWER'
	[ "$(cat "$device/power/wakeup")" = enabled ] ||
		fail 'power key wakeup is not enabled'
	pwrkey_events=$((pwrkey_events + 1))
done
case $phase in
	pre)
		[ "$pwrkey_events" -eq 0 ] ||
			fail 'power key registered before qcom_pon probe'
		;;
	post)
		[ "$pwrkey_events" -eq 1 ] ||
			fail 'power key did not register exactly one input event'
		;;
esac

fatal_pattern='Kernel panic|Oops:|BUG:|Unable to handle kernel|Synchronous External Abort|watchdog.*bite'
[ "$(dmesg | grep -Ec "$fatal_pattern" || true)" -eq 0 ] ||
	fail 'fatal kernel signature is present'
[ "$(systemctl --failed --no-legend --plain |
	awk 'NF { count++ } END { print count + 0 }')" -eq 0 ] ||
	fail 'systemd has failed units'

echo "PASS diagnostic power-key $phase gate: qcom_pon dependency, RTC/storage isolation, and rollback state are exact"
